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
from app.services.r2 import r2_client

router = APIRouter()


def _clip_to_response(clip: Clip) -> ClipResponse:
    thumbnail_url: str | None = None
    if clip.thumbnail_key:
        try:
            thumbnail_url = r2_client.get_presigned_download_url(clip.thumbnail_key)
        except Exception:
            thumbnail_url = None

    return ClipResponse(
        id=clip.id,
        video_id=clip.video_id,
        start_time=clip.start_time,
        end_time=clip.end_time,
        duration_sec=clip.duration_sec,
        score=clip.score,
        hook_score=clip.hook_score,
        energy_score=clip.energy_score,
        title=clip.title,
        hashtags=clip.hashtags,
        thumbnail_key=clip.thumbnail_key,
        thumbnail_url=thumbnail_url,
        transcript_text=clip.transcript_text,
        status=clip.status,
        created_at=clip.created_at,
        updated_at=clip.updated_at,
    )


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
        try:
            video_uuid = uuid.UUID(video_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video_id")
        query = query.where(Clip.video_id == video_uuid)

    result = await db.execute(query)
    clips = result.scalars().all()
    return [_clip_to_response(clip) for clip in clips]


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
    return _clip_to_response(clip)
