import uuid
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class AspectRatio(str, enum.Enum):
    vertical = "9:16"
    square = "1:1"


class CaptionStyle(str, enum.Enum):
    bold_boxed = "bold_boxed"
    sermon_quote = "sermon_quote"
    clean_minimal = "clean_minimal"


class CaptionFormat(str, enum.Enum):
    burned_in = "burned_in"
    srt = "srt"


class ExportStatus(str, enum.Enum):
    queued = "queued"
    rendering = "rendering"
    ready = "ready"
    error = "error"


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    aspect_ratio: Mapped[AspectRatio] = mapped_column(
        SAEnum(
            AspectRatio,
            name="aspect_ratio",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    caption_style: Mapped[CaptionStyle | None] = mapped_column(
        SAEnum(CaptionStyle, name="caption_style")
    )
    caption_format: Mapped[CaptionFormat] = mapped_column(
        SAEnum(CaptionFormat, name="caption_format"), nullable=False
    )
    storage_key: Mapped[str | None] = mapped_column(Text)
    srt_key: Mapped[str | None] = mapped_column(Text)
    download_url: Mapped[str | None] = mapped_column(Text)
    url_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ExportStatus] = mapped_column(
        SAEnum(ExportStatus, name="export_status"), default=ExportStatus.queued, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    render_time_sec: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    clip: Mapped["Clip"] = relationship("Clip", back_populates="exports")
    user: Mapped["User"] = relationship("User", back_populates="exports")
