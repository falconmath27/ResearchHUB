"""Reserve daily AI-analysis capacity per project.

Revision ID: 20260916_0012
Revises: 20260916_0011
"""

from alembic import op
import sqlalchemy as sa


revision = "20260916_0012"
down_revision = "20260916_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_daily_quotas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("reserved_jobs", sa.Integer(), nullable=False),
        sa.UniqueConstraint("project_id", "day", name="uq_ai_daily_quotas_project_day"),
    )


def downgrade() -> None:
    op.drop_table("ai_daily_quotas")
