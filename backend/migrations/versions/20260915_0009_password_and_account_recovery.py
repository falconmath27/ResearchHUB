"""Add password reset and manual account recovery.

Revision ID: 20260915_0009
Revises: 20260915_0008
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260915_0009"
down_revision: Union[str, Sequence[str], None] = "20260915_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))

    op.create_table(
        "password_reset_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_attempts_email_fingerprint", "password_reset_attempts", ["email_fingerprint"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "account_recovery_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("remembered_email", sa.String(length=255), nullable=True),
        sa.Column("details", sa.String(length=2_000), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_code"),
    )
    op.create_index("ix_account_recovery_requests_contact_email", "account_recovery_requests", ["contact_email"])


def downgrade() -> None:
    op.drop_index("ix_account_recovery_requests_contact_email", table_name="account_recovery_requests")
    op.drop_table("account_recovery_requests")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_password_reset_attempts_email_fingerprint", table_name="password_reset_attempts")
    op.drop_table("password_reset_attempts")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
