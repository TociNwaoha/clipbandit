import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.clip import Clip
from app.models.export import Export, ExportStatus
from app.models.job import Job, JobStatus
from app.models.user import User
from app.models.video import Video
from app.schemas.export import ExportCreate, ExportResponse
from app.services.r2 import r2_client

router = APIRouter()
logger = logging.getLogger(__name__)

ACTIVE_EXPORT_STATUSES = (ExportStatus.queued, ExportStatus.rendering)


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _derived_download_url(storage_key: str | None) -> str | None:
    if not storage_key:
        return None
    try:
        if not r2_client.file_exists(storage_key):
            return None
        return r2_client.get_presigned_download_url(storage_key)
    except Exception as exc:
        logger.warning("[exports] failed to derive download URL for key=%s: %s", storage_key, exc)
        return None


def _to_response(export: Export, reused: bool = False) -> ExportResponse:
    download_url = None
    srt_download_url = None
    if export.status == ExportStatus.ready:
        download_url = _derived_download_url(export.storage_key)
        srt_download_url = _derived_download_url(export.srt_key)

    return ExportResponse(
        id=export.id,
        clip_id=export.clip_id,
        user_id=export.user_id,
        aspect_ratio=export.aspect_ratio,
        caption_style=export.caption_style,
        caption_format=export.caption_format,
        storage_key=export.storage_key,
        srt_key=export.srt_key,
        download_url=download_url,
        srt_download_url=srt_download_url,
        url_expires_at=export.url_expires_at,
        status=export.status,
        error_message=export.error_message,
        render_time_sec=export.render_time_sec,
        reused=reused,
        created_at=export.created_at,
        updated_at=export.updated_at,
    )


@router.get("/exports", response_model=list[ExportResponse])
async def list_exports(
    clip_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Export).where(Export.user_id == current_user.id)
    if clip_id:
        query = query.where(Export.clip_id == clip_id)
    result = await db.execute(query.order_by(Export.created_at.desc()))
    exports = result.scalars().all()
    return [_to_response(export) for export in exports]


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Export).where(Export.id == export_id, Export.user_id == current_user.id)
    )
    export = result.scalar_one_or_none()
    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    return _to_response(export)


@router.post("/exports", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "[exports] create requested user_id=%s clip_id=%s aspect_ratio=%s caption_style=%s caption_format=%s",
        current_user.id,
        body.clip_id,
        body.aspect_ratio,
        body.caption_style,
        body.caption_format,
    )

    clip_result = await db.execute(
        select(Clip)
        .join(Video, Clip.video_id == Video.id)
        .where(Clip.id == body.clip_id, Video.user_id == current_user.id)
    )
    clip = clip_result.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")

    dedupe_result = await db.execute(
        select(Export)
        .where(
            Export.user_id == current_user.id,
            Export.clip_id == body.clip_id,
            Export.aspect_ratio == body.aspect_ratio,
            Export.caption_style == body.caption_style,
            Export.caption_format == body.caption_format,
            Export.status.in_(ACTIVE_EXPORT_STATUSES),
        )
        .order_by(Export.created_at.desc())
    )
    existing = dedupe_result.scalars().first()
    if existing:
        logger.info(
            "[exports] dedupe reused existing export_id=%s clip_id=%s status=%s",
            existing.id,
            existing.clip_id,
            existing.status,
        )
        payload = _to_response(existing, reused=True).model_dump(mode="json")
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)

    export = Export(
        clip_id=body.clip_id,
        user_id=current_user.id,
        aspect_ratio=body.aspect_ratio,
        caption_style=body.caption_style,
        caption_format=body.caption_format,
    )
    db.add(export)
    await db.flush()

    render_job = Job(
        video_id=clip.video_id,
        type="render",
        status=JobStatus.queued,
        payload={
            "export_id": str(export.id),
            "clip_id": str(body.clip_id),
            "aspect_ratio": _enum_value(body.aspect_ratio),
            "caption_style": _enum_value(body.caption_style) if body.caption_style else None,
            "caption_format": _enum_value(body.caption_format),
        },
    )
    db.add(render_job)
    await db.flush()
    await db.commit()
    await db.refresh(export)
    await db.refresh(render_job)

    try:
        from app.worker.tasks.render import render_export

        task = render_export.apply_async(
            args=[str(export.id), str(render_job.id)],
            countdown=1,
            queue="render",
        )
        render_job.celery_task_id = task.id
        await db.commit()
        logger.info(
            "[exports] export enqueued export_id=%s job_id=%s task_id=%s",
            export.id,
            render_job.id,
            task.id,
        )
    except Exception as exc:
        export.status = ExportStatus.error
        export.error_message = f"Failed to enqueue render job: {exc}"
        render_job.status = JobStatus.failed
        render_job.error = str(exc)[:500]
        await db.commit()
        logger.exception("[exports] enqueue failed export_id=%s job_id=%s", export.id, render_job.id)

    await db.refresh(export)
    return _to_response(export, reused=False)
