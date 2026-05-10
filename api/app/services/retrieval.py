from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.services.embedding import embed_texts

TOP_K = 5


async def retrieve_similar_chunks(
    query: str, session: AsyncSession, k: int = TOP_K
) -> list[dict]:
    embeddings = await embed_texts([query])
    query_vec = embeddings[0]

    result = await session.execute(
        select(
            Chunk.content,
            Chunk.chunk_index,
            Document.id.label("document_id"),
            Document.filename,
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.status == DocumentStatus.ready)
        .order_by(Chunk.embedding.cosine_distance(query_vec))
        .limit(k)
    )

    return [
        {
            "content": row.content,
            "chunk_index": row.chunk_index,
            "document_id": row.document_id,
            "filename": row.filename,
        }
        for row in result.all()
    ]
