"""add card-required beta variant fields

Revision ID: 0040
Revises: 0039
Create Date: 2026-08-23 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("beta_variant", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("beta_card_walkthrough_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "beta_card_walkthrough_completed_at")
    op.drop_column("users", "beta_variant")
