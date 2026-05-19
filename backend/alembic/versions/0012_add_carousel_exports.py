"""add carousel exports

Revision ID: 0012_add_carousel_exports
Revises: 0011_add_caption_color_variant
Create Date: 2026-05-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0012_add_carousel_exports"
down_revision: Union[str, None] = "0011_add_caption_color_variant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "carousel_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("slide_keys_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("zip_key", sa.Text(), nullable=False),
        sa.Column("preview_key", sa.Text(), nullable=False),
        sa.Column("slide_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_carousel_exports_user_id"), "carousel_exports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_carousel_exports_user_id"), table_name="carousel_exports")
    op.drop_table("carousel_exports")
