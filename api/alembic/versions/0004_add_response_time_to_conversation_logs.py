"""Add response_time_ms column to conversation_logs

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_logs",
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_logs", "response_time_ms")
