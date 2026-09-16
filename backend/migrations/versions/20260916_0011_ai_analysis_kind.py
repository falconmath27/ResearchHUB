"""Separate extraction and AI analysis jobs.

Revision ID: 20260916_0011
Revises: 20260915_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20260916_0011"
down_revision = "20260915_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("kind", sa.String(length=20), nullable=False, server_default="extraction"))


def downgrade() -> None:
    op.drop_column("analysis_jobs", "kind")
