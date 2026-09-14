"""Add normalized DOI support to project sources.

Revision ID: 20260915_0008
Revises: 20260826_0007
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260915_0008"
down_revision: Union[str, Sequence[str], None] = "20260826_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sources") as batch_op:
        batch_op.add_column(sa.Column("doi", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint("uq_sources_project_doi", ["project_id", "doi"])


def downgrade() -> None:
    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_constraint("uq_sources_project_doi", type_="unique")
        batch_op.drop_column("doi")
