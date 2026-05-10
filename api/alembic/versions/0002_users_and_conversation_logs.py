"""Add users and conversation_logs tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="user_role"),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "conversation_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("source_document_id", sa.String(36), nullable=True),
        sa.Column("source_filename", sa.String(512), nullable=True),
        sa.Column("not_found", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_conversation_logs_session_id", "conversation_logs", ["session_id"])
    op.create_index("ix_conversation_logs_user_id", "conversation_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_conversation_logs_user_id", table_name="conversation_logs")
    op.drop_index("ix_conversation_logs_session_id", table_name="conversation_logs")
    op.drop_table("conversation_logs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
