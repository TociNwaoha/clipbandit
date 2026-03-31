from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.video import VideoResponse
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/videos", response_model=list[VideoResponse])
async def list_videos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Video).where(Video.user_id == current_user.id).order_by(Video.created_at.desc())
    )
    return result.scalars().all()


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException, status
    import uuid

    result = await db.execute(
        select(Video).where(Video.id == uuid.UUID(video_id), Video.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video
