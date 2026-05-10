"""Initial schema: documents + chunks tables with HNSW vector index

Revision ID: 0001
Revises:
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("original_path", sa.String(1024), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "ready", "error", name="document_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        # LOCKED: 1536 dimensions for text-embedding-3-small
        # DO NOT change this value — requires full table drop + re-ingestion
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
    )

    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # HNSW index for approximate nearest-neighbor search
    # Parameters per ROADMAP success criteria (LOCKED):
    #   vector_cosine_ops: cosine similarity (correct for text-embedding-3-small)
    #   m=16: max connections per HNSW graph node
    #   ef_construction=64: index build quality
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_hnsw
        ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")
    # Note: does NOT drop vector extension — other extensions may depend on it
