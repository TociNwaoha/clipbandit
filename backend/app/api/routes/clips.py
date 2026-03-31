from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.user import User
from app.models.clip import Clip
from app.models.video import Video
from app.schemas.clip import ClipResponse
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/clips", response_model=list[ClipResponse])
async def list_clips(
    video_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Clip)
        .join(Video, Clip.video_id == Video.id)
        .where(Video.user_id == current_user.id)
        .order_by(Clip.score.desc())
    )
    if video_id:
        query = query.where(Clip.video_id == uuid.UUID(video_id))

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Clip)
        .join(Video, Clip.video_id == Video.id)
        .where(Clip.id == uuid.UUID(clip_id), Video.user_id == current_user.id)
    )
    clip = result.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")
    return clip
