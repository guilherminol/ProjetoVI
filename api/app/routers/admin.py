"""
Admin API router — document management endpoints.

Auth: X-Admin-Key header validated against ADMIN_API_KEY env var.
TODO Phase 2: Replace X-Admin-Key with JWT-based admin role check.

Endpoints:
  POST   /admin/documents/upload       — Upload PDF, trigger ingestion
  GET    /admin/documents              — List all documents
  GET    /admin/documents/{id}         — Get single document status
  DELETE /admin/documents/{id}         — Delete document + all chunks
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security, UploadFile
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.models.document import Document, DocumentStatus
from app.services.ingestion import ingest_document

settings = get_settings()
router = APIRouter(tags=["admin"])

_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin_key(api_key: str | None = Security(_admin_key_header)) -> None:
    """
    FastAPI dependency that validates the X-Admin-Key header.
    TODO Phase 2: Replace with JWT role check (admin claim).
    """
    if api_key is None or api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing X-Admin-Key header.",
        )


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
    _: None = Depends(require_admin_key),
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
    _: None = Depends(require_admin_key),
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
    _: None = Depends(require_admin_key),
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
    _: None = Depends(require_admin_key),
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
