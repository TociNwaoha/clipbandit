import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class ExcludeZoneSource(str, enum.Enum):
    manual = "manual"
    auto_detected = "auto_detected"


class ExcludeZone(Base):
    __tablename__ = "exclude_zones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[ExcludeZoneSource] = mapped_column(
        SAEnum(ExcludeZoneSource, name="exclude_zone_source"),
        default=ExcludeZoneSource.manual,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    video: Mapped["Video"] = relationship("Video", back_populates="exclude_zones")
