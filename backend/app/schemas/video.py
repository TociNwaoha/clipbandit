import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.video import VideoStatus, VideoSourceType


class VideoResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    source_type: VideoSourceType
    source_url: str | None
    storage_key: str | None
    duration_sec: int | None
    resolution: str | None
    file_size_bytes: int | None
    status: VideoStatus
    error_message: str | None
    clip_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoCreate(BaseModel):
    title: str | None = None
    source_type: VideoSourceType
    source_url: str | None = None
