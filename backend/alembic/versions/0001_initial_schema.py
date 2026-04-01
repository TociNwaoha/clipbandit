"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("tier", sa.Enum("starter", "creator", "agency", name="user_tier"), nullable=False, server_default="starter"),
        sa.Column("videos_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # videos
    op.create_table(
        "videos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("source_type", sa.Enum("upload", "youtube", name="video_source_type"), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("storage_key", sa.Text),
        sa.Column("duration_sec", sa.Integer),
        sa.Column("resolution", sa.String(20)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("status", sa.Enum("queued", "downloading", "transcribing", "scoring", "ready", "error", name="video_status"), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text),
        sa.Column("clip_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_videos_user_id", "videos", ["user_id"])
    op.create_index("ix_videos_status", "videos", ["status"])

    # transcript_segments
    op.create_table(
        "transcript_segments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word", sa.String(200)),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float),
        sa.Column("segment_index", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_transcript_segments_video_id", "transcript_segments", ["video_id"])
    op.create_index("ix_transcript_segments_start_time", "transcript_segments", ["start_time"])

    # clips
    op.create_table(
        "clips",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("duration_sec", sa.Float),
        sa.Column("score", sa.Float),
        sa.Column("hook_score", sa.Float),
        sa.Column("energy_score", sa.Float),
        sa.Column("title", sa.String(500)),
        sa.Column("hashtags", ARRAY(sa.String)),
        sa.Column("thumbnail_key", sa.Text),
        sa.Column("transcript_text", sa.Text),
        sa.Column("status", sa.Enum("pending", "ready", "exported", name="clip_status"), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_clips_video_id", "clips", ["video_id"])
    op.create_index("ix_clips_score_desc", "clips", [sa.text("score DESC")])

    # exports
    op.create_table(
        "exports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clip_id", UUID(as_uuid=True), sa.ForeignKey("clips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aspect_ratio", sa.Enum("9:16", "1:1", name="aspect_ratio"), nullable=False),
        sa.Column("caption_style", sa.Enum("bold_boxed", "sermon_quote", "clean_minimal", name="caption_style")),
        sa.Column("caption_format", sa.Enum("burned_in", "srt", name="caption_format"), nullable=False),
        sa.Column("storage_key", sa.Text),
        sa.Column("srt_key", sa.Text),
        sa.Column("download_url", sa.Text),
        sa.Column("url_expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Enum("queued", "rendering", "ready", "error", name="export_status"), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text),
        sa.Column("render_time_sec", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_exports_clip_id", "exports", ["clip_id"])
    op.create_index("ix_exports_status", "exports", ["status"])

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.Enum("queued", "running", "done", "failed", name="job_status"), nullable=False, server_default="queued"),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_jobs_video_id", "jobs", ["video_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # exclude_zones
    op.create_table(
        "exclude_zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("label", sa.String(100)),
        sa.Column("source", sa.Enum("manual", "auto_detected", name="exclude_zone_source"), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("exclude_zones")
    op.drop_table("jobs")
    op.drop_table("exports")
    op.drop_table("clips")
    op.drop_table("transcript_segments")
    op.drop_table("videos")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS exclude_zone_source")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS export_status")
    op.execute("DROP TYPE IF EXISTS caption_format")
    op.execute("DROP TYPE IF EXISTS caption_style")
    op.execute("DROP TYPE IF EXISTS aspect_ratio")
    op.execute("DROP TYPE IF EXISTS clip_status")
    op.execute("DROP TYPE IF EXISTS video_status")
    op.execute("DROP TYPE IF EXISTS video_source_type")
    op.execute("DROP TYPE IF EXISTS user_tier")
