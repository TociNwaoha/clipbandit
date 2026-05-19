import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.carousel_export import CarouselExport
from app.models.user import User
from app.schemas.carousel import (
    CarouselExportCreateRequest,
    CarouselExportResponse,
    CarouselGenerateRequest,
    CarouselGenerateResponse,
    CarouselRenderRequest,
    CarouselRenderResponse,
    CarouselTemplateResponse,
)
from app.services.carousel import CarouselError, generate_config, list_templates, render_config
from app.services.r2 import r2_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/carousels/templates", response_model=list[CarouselTemplateResponse])
async def get_carousel_templates(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return [CarouselTemplateResponse(**item) for item in list_templates()]


@router.post("/carousels/generate", response_model=CarouselGenerateResponse)
async def generate_carousel_config(
    body: CarouselGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        config, provider_used = generate_config(body.template_id, body.topic, current_user)
        return CarouselGenerateResponse(config=config, provider_used=provider_used)
    except CarouselError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("[carousels] generate failed user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Carousel generation is currently unavailable. Please retry shortly.",
        ) from exc


@router.post("/carousels/render", response_model=CarouselRenderResponse)
async def render_carousel(
    body: CarouselRenderRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = render_config(
            template_id=body.template_id,
            config=body.config.model_dump(mode="json"),
            user_id=current_user.id,
            reference_images=body.reference_images,
        )
        return CarouselRenderResponse(
            workspace_id=result["workspace_id"],
            slides=result["slides"],
            zip=result["zip"],
        )
    except CarouselError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[carousels] render failed user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Carousel rendering failed unexpectedly.",
        ) from exc


def _with_signed_urls(row: CarouselExport) -> CarouselExportResponse:
    zip_url = None
    preview_url = None
    try:
        if row.zip_key:
            zip_url = r2_client.get_presigned_download_url(row.zip_key)
        if row.preview_key:
            preview_url = r2_client.get_presigned_download_url(row.preview_key)
    except Exception as exc:
        logger.warning("[carousels] failed to generate signed urls export_id=%s error=%s", row.id, exc)

    return CarouselExportResponse(
        id=row.id,
        user_id=row.user_id,
        template_id=row.template_id,
        title=row.title,
        config_json=row.config_json or {},
        slide_keys_json=list(row.slide_keys_json or []),
        zip_key=row.zip_key,
        preview_key=row.preview_key,
        slide_count=row.slide_count,
        zip_url=zip_url,
        preview_url=preview_url,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/carousels/exports", response_model=CarouselExportResponse)
async def save_carousel_export(
    body: CarouselExportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.slide_keys:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slide_keys are required")
    if body.preview_key not in body.slide_keys:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="preview_key must exist in slide_keys")
    owned_prefix = f"carousels/{current_user.id}/"
    if not body.zip_key.startswith(owned_prefix):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid zip key scope")
    if not body.preview_key.startswith(owned_prefix):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid preview key scope")
    if any(not key.startswith(owned_prefix) for key in body.slide_keys):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid slide key scope")

    title = body.config.title.strip() if body.config.title else None
    row = CarouselExport(
        id=uuid.uuid4(),
        user_id=current_user.id,
        template_id=body.template_id,
        title=title,
        config_json=body.config.model_dump(mode="json"),
        slide_keys_json=body.slide_keys,
        zip_key=body.zip_key,
        preview_key=body.preview_key,
        slide_count=len(body.slide_keys),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _with_signed_urls(row)


@router.get("/carousels/exports", response_model=list[CarouselExportResponse])
async def list_carousel_exports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CarouselExport)
        .where(CarouselExport.user_id == current_user.id)
        .order_by(CarouselExport.created_at.desc())
    )
    rows = result.scalars().all()
    return [_with_signed_urls(row) for row in rows]
