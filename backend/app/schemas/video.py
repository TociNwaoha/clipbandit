import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.video import VideoImportMode, VideoImportState, VideoSourceType, VideoStatus


class VideoResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    source_type: VideoSourceType
    source_url: str | None
    source_video_id: str | None
    source_playlist_id: str | None
    source_playlist_title: str | None
    playlist_index: int | None
    import_parent_id: uuid.UUID | None
    embed_url: str | None
    thumbnail_url: str | None
    import_state: VideoImportState
    import_state_ui: str | None = None
    import_mode: VideoImportMode
    is_download_blocked: bool
    error_code: str | None
    debug_error_message: str | None
    external_metadata_json: dict
    storage_key: str | None
    source_download_url: str | None = None
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


class VideoUploadUrlRequest(BaseModel):
    filename: str
    file_size: int
    content_type: str


class VideoUploadUrlResponse(BaseModel):
    video_id: uuid.UUID
    upload_url: str
    upload_fields: dict[str, str]
    storage_key: str
    use_local: bool


class VideoConfirmUploadRequest(BaseModel):
    video_id: uuid.UUID


class VideoConfirmUploadResponse(BaseModel):
    video_id: uuid.UUID
    status: VideoStatus


class VideoImportYoutubeRequest(BaseModel):
    url: str


class VideoImportYoutubeResponse(BaseModel):
    video_id: uuid.UUID | None = None
    playlist_import_id: uuid.UUID | None = None
    import_kind: str
    status: VideoStatus | str
    message: str


class VideoListItem(BaseModel):
    id: uuid.UUID
    title: str | None
    status: VideoStatus
    duration_sec: int | None
    clip_count: int
    created_at: datetime
    thumbnail_url: str | None
    source_type: VideoSourceType
    source_url: str | None
    source_video_id: str | None
    source_playlist_id: str | None
    source_playlist_title: str | None
    playlist_index: int | None
    import_parent_id: uuid.UUID | None
    embed_url: str | None
    import_state: VideoImportState
    import_state_ui: str | None = None
    import_mode: VideoImportMode
    is_download_blocked: bool
    error_code: str | None
    error_message: str | None


class VideoStatusResponse(BaseModel):
    video_id: uuid.UUID
    status: VideoStatus
    import_state: VideoImportState | None = None
    import_state_ui: str | None = None
    title: str | None
    clip_count: int
    error_message: str | None


class TranscriptWordSegment(BaseModel):
    word: str | None
    start: float
    end: float
    confidence: float | None = None
    segment_index: int | None = None


class VideoTranscriptResponse(BaseModel):
    video_id: uuid.UUID
    word_count: int
    duration: float
    language: str | None
    full_text: str
    segments: list[dict]
