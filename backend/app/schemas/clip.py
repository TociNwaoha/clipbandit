import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.clip import ClipStatus


class ClipUpdateRequest(BaseModel):
    video_id: uuid.UUID
    start_time: float
    end_time: float


class ClipResponse(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    start_time: float
    end_time: float
    duration_sec: float | None
    score: float | None
    hook_score: float | None
    energy_score: float | None
    title: str | None
    hashtags: list[str] | None
    title_options: list[str] | None
    hashtag_options: list[list[str]] | None
    copy_generation_status: str | None
    copy_generation_error: str | None
    thumbnail_key: str | None
    thumbnail_url: str | None = None
    transcript_text: str | None
    status: ClipStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
