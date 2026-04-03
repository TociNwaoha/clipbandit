import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User
from app.models.export import Export, ExportStatus
from app.models.clip import Clip
from app.models.video import Video
from app.models.job import Job, JobStatus
from app.schemas.export import ExportCreate, ExportResponse
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


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
    return result.scalars().all()


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
    return export


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
            "aspect_ratio": body.aspect_ratio.value,
            "caption_style": body.caption_style.value if body.caption_style else None,
            "caption_format": body.caption_format.value,
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
    return export
