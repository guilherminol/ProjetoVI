"""Add rating column to conversation_logs

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE feedback_rating AS ENUM ('useful', 'not_useful')")
    op.add_column(
        "conversation_logs",
        sa.Column(
            "rating",
            sa.Enum("useful", "not_useful", name="feedback_rating"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversation_logs", "rating")
    op.execute("DROP TYPE IF EXISTS feedback_rating")
