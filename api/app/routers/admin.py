"""
Admin API router — document management endpoints.

Auth: JWT Bearer token with admin role (Phase 2 replacement for X-Admin-Key).

Endpoints:
  POST   /admin/documents/upload       — Upload PDF, trigger ingestion
  GET    /admin/documents              — List all documents
  GET    /admin/documents/{id}         — Get single document status
  DELETE /admin/documents/{id}         — Delete document + all chunks
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import require_admin
from app.db.session import get_session
from app.models.conversation_log import ConversationLog, FeedbackRating
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.ingestion import ingest_document

settings = get_settings()
router = APIRouter(tags=["admin"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str
    message: str


class DocumentListItem(BaseModel):
    document_id: str
    filename: str
    status: str
    error_message: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


@router.post(
    "/documents/upload",
    status_code=202,
    response_model=DocumentUploadResponse,
    summary="Upload a PDF for ingestion",
)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> DocumentUploadResponse:
    """Upload a PDF file. Returns 202 immediately; ingestion runs asynchronously."""
    filename = file.filename or ""
    if not (
        file.content_type in ("application/pdf", "application/octet-stream")
        or filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF files are accepted. "
                f"Received content_type={file.content_type}, filename={filename}"
            ),
        )

    if not filename:
        filename = "unknown.pdf"
    document_id = str(uuid.uuid4())

    storage_path = Path(settings.pdf_storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = str(storage_path / f"{document_id}.pdf")

    file_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    document = Document(
        id=document_id,
        filename=filename,
        original_path=file_path,
        status=DocumentStatus.pending,
    )
    session.add(document)
    await session.flush()

    background_tasks.add_task(ingest_document, document_id, file_path)

    return DocumentUploadResponse(
        document_id=document_id,
        status="pending",
        message=(
            f"Document '{filename}' accepted for ingestion. "
            f"Poll GET /admin/documents/{document_id} to track status."
        ),
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
)
async def list_documents(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> DocumentListResponse:
    """Return all documents in the knowledge base, ordered by creation date descending."""
    result = await session.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentListItem(
                document_id=doc.id,
                filename=doc.filename,
                status=doc.status.value,
                error_message=doc.error_message,
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentListItem,
    summary="Get document status by ID",
)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> DocumentListItem:
    """Return a single document's current status. Use to poll ingestion progress."""
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    return DocumentListItem(
        document_id=document.id,
        filename=document.filename,
        status=document.status.value,
        error_message=document.error_message,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )


@router.delete(
    "/documents/{document_id}",
    status_code=204,
    summary="Delete a document and all its chunks",
)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
) -> None:
    """
    Delete a document from the knowledge base.

    Chunks are removed via CASCADE (defined in migration 0001).
    PDF file on disk is also deleted.
    Returns 204 No Content on success, 404 if document not found.
    """
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    file_path = Path(document.original_path)
    if file_path.exists():
        file_path.unlink()

    await session.delete(document)


class FeedbackLogItem(BaseModel):
    log_id: int
    session_id: str
    question: str
    answer: str
    rating: str | None
    created_at: str


class FeedbackStatsResponse(BaseModel):
    total_rated: int
    useful_count: int
    not_useful_count: int
    satisfaction_rate: float
    worst_responses: list[FeedbackLogItem]


@router.get("/feedback/stats", response_model=FeedbackStatsResponse, summary="Feedback dashboard stats")
async def feedback_stats(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> FeedbackStatsResponse:
    useful_count_result = await session.execute(
        select(func.count()).where(ConversationLog.rating == FeedbackRating.useful)
    )
    useful = useful_count_result.scalar_one()

    not_useful_count_result = await session.execute(
        select(func.count()).where(ConversationLog.rating == FeedbackRating.not_useful)
    )
    not_useful = not_useful_count_result.scalar_one()

    total = useful + not_useful
    rate = round(useful / total, 4) if total > 0 else 0.0

    worst_result = await session.execute(
        select(ConversationLog)
        .where(ConversationLog.rating == FeedbackRating.not_useful)
        .order_by(ConversationLog.created_at.desc())
        .limit(20)
    )
    worst = worst_result.scalars().all()

    return FeedbackStatsResponse(
        total_rated=total,
        useful_count=useful,
        not_useful_count=not_useful,
        satisfaction_rate=rate,
        worst_responses=[
            FeedbackLogItem(
                log_id=log.id,
                session_id=log.session_id,
                question=log.question,
                answer=log.answer,
                rating=log.rating.value if log.rating else None,
                created_at=log.created_at.isoformat(),
            )
            for log in worst
        ],
    )
