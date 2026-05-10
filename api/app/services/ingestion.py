"""
Document ingestion orchestrator.

Entry point: ingest_document(document_id, file_path)

Called by FastAPI BackgroundTasks after the upload endpoint returns 202.
Creates its own DB session (not via FastAPI dependency injection).

Status lifecycle:
  pending → processing → ready
                      ↘ error (error_message populated)
"""
import logging

from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.services.chunker import chunk_text
from app.services.embedding import embed_texts
from app.services.parser import parse_pdf

logger = logging.getLogger(__name__)


async def ingest_document(document_id: str, file_path: str) -> None:
    """
    Full ingestion pipeline for a single document.

    Args:
        document_id: UUID string of the Document row (must already exist with status=pending).
        file_path: Absolute path to the PDF file saved on disk.
    """
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            logger.error("Document %s not found — ingestion aborted", document_id)
            return

        document.status = DocumentStatus.processing
        await session.commit()
        logger.info("Ingestion started for document %s (%s)", document_id, document.filename)

        try:
            text = parse_pdf(file_path)
            logger.info("Parsed %d characters from %s", len(text), document.filename)

            chunk_tuples = chunk_text(text)
            logger.info("Created %d chunks from %s", len(chunk_tuples), document.filename)

            if not chunk_tuples:
                raise RuntimeError(
                    "Chunking produced 0 valid chunks. "
                    "Document may be too short or contain only header/footer text."
                )

            chunk_texts_only = [c[0] for c in chunk_tuples]
            embeddings = await embed_texts(chunk_texts_only)

            for idx, ((chunk_content, token_count), embedding) in enumerate(
                zip(chunk_tuples, embeddings)
            ):
                chunk = Chunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk_content,
                    embedding=embedding,
                    token_count=token_count,
                )
                session.add(chunk)

            document.status = DocumentStatus.ready
            document.error_message = None
            await session.commit()
            logger.info(
                "Ingestion complete for %s — %d chunks indexed",
                document.filename,
                len(chunk_tuples),
            )

        except Exception as exc:
            await session.rollback()
            async with AsyncSessionFactory() as error_session:
                err_result = await error_session.execute(
                    select(Document).where(Document.id == document_id)
                )
                err_doc = err_result.scalar_one_or_none()
                if err_doc:
                    err_doc.status = DocumentStatus.error
                    err_doc.error_message = str(exc)[:2000]
                    await error_session.commit()
            logger.error(
                "Ingestion failed for document %s: %s", document_id, exc, exc_info=True
            )
