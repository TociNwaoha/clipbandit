import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String as SAString
from app.database import Base
import enum


class ClipStatus(str, enum.Enum):
    pending = "pending"
    ready = "ready"
    exported = "exported"


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_sec: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float, index=True)
    hook_score: Mapped[float | None] = mapped_column(Float)
    energy_score: Mapped[float | None] = mapped_column(Float)
    title: Mapped[str | None] = mapped_column(String(500))
    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(SAString))
    thumbnail_key: Mapped[str | None] = mapped_column(Text)
    transcript_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ClipStatus] = mapped_column(
        SAEnum(ClipStatus, name="clip_status"), default=ClipStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    video: Mapped["Video"] = relationship("Video", back_populates="clips")
    exports: Mapped[list["Export"]] = relationship("Export", back_populates="clip", cascade="all, delete-orphan")
