import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.export import AspectRatio, CaptionStyle, CaptionFormat, ExportStatus


class ExportCreate(BaseModel):
    clip_id: uuid.UUID
    aspect_ratio: AspectRatio
    caption_style: CaptionStyle | None = None
    caption_format: CaptionFormat


class ExportResponse(BaseModel):
    id: uuid.UUID
    clip_id: uuid.UUID
    user_id: uuid.UUID
    aspect_ratio: AspectRatio
    caption_style: CaptionStyle | None
    caption_format: CaptionFormat
    storage_key: str | None
    srt_key: str | None
    download_url: str | None
    srt_download_url: str | None = None
    url_expires_at: datetime | None
    status: ExportStatus
    error_message: str | None
    render_time_sec: int | None
    reused: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
