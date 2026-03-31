from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User
from app.models.export import Export
from app.models.clip import Clip
from app.models.video import Video
from app.schemas.export import ExportCreate, ExportResponse
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/exports", response_model=list[ExportResponse])
async def list_exports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Export)
        .where(Export.user_id == current_user.id)
        .order_by(Export.created_at.desc())
    )
    return result.scalars().all()


@router.post("/exports", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    body: ExportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    await db.refresh(export)
    return export
