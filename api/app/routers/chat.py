import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.db.session import AsyncSessionFactory, get_session
from app.models.conversation_log import ConversationLog, FeedbackRating
from app.models.document import Document, DocumentStatus
from app.models.user import User

router = APIRouter(tags=["chat"])
settings = get_settings()
logger = logging.getLogger(__name__)


class FeedbackRequest(BaseModel):
    rating: str  # "useful" | "not_useful"


NOT_FOUND_MSG = (
    "Não encontrei informações nos manuais disponíveis para responder sua pergunta. "
    "Por favor, entre em contato com o suporte técnico da Cancella."
)


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


def _get_rag_graph(request: Request):
    return request.app.state.rag_graph


async def _sse_stream(
    question: str,
    session_id: str,
    user_id: str,
    graph,
) -> AsyncGenerator[str, None]:
    t_start = time.monotonic()
    logger.info(
        "Chat request started",
        extra={
            "event": "chat_start",
            "session_id": session_id,
            "user_id": user_id,
            "question_len": len(question),
        },
    )
    config = {"configurable": {"thread_id": session_id}}
    initial_state: dict = {
        "question": question,
        "messages": [HumanMessage(content=question)],
        "retrieved_chunks": [],
        "not_found": False,
    }

    full_answer = ""
    retrieved_chunks: list[dict] = []
    not_found = False

    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_chain_end" and name == "retrieve":
            output = event["data"].get("output") or {}
            retrieved_chunks = output.get("retrieved_chunks", [])

        elif kind == "on_chain_end" and name == "hallucination_guard":
            output = event["data"].get("output") or {}
            not_found = output.get("not_found", False)

        elif kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                full_answer += chunk.content
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

    if not_found:
        full_answer = NOT_FOUND_MSG
        yield f"data: {json.dumps({'type': 'token', 'content': NOT_FOUND_MSG})}\n\n"

    sources = [
        {
            "document_id": c["document_id"],
            "filename": c["filename"],
            "download_url": f"/chat/documents/{c['document_id']}/download",
        }
        for c in retrieved_chunks
    ]

    # Save log and get ID before emitting done so client can submit feedback
    src = retrieved_chunks[0] if retrieved_chunks else {}
    log_id: int | None = None
    async with AsyncSessionFactory() as db:
        log = ConversationLog(
            session_id=session_id,
            user_id=user_id,
            question=question,
            answer=full_answer,
            source_document_id=src.get("document_id"),
            source_filename=src.get("filename"),
            not_found=not_found,
        )
        db.add(log)
        await db.flush()
        log_id = log.id
        await db.commit()

    yield f"data: {json.dumps({'type': 'done', 'not_found': not_found, 'sources': sources, 'log_id': log_id})}\n\n"

    logger.info(
        "Chat request completed",
        extra={
            "event": "chat_done",
            "session_id": session_id,
            "user_id": user_id,
            "not_found": not_found,
            "chunks_retrieved": len(retrieved_chunks),
            "latency_s": round(time.monotonic() - t_start, 3),
        },
    )


@router.post("", status_code=200)
async def chat(
    body: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    graph=Depends(_get_rag_graph),
) -> StreamingResponse:
    session_id = body.session_id or str(uuid.uuid4())
    return StreamingResponse(
        _sse_stream(body.question, session_id, current_user.id, graph),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> FileResponse:
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.status == DocumentStatus.ready,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.original_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on server.")

    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type="application/pdf",
    )


@router.patch("/feedback/{log_id}", status_code=204)
async def submit_feedback(
    log_id: int,
    body: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    if body.rating not in ("useful", "not_useful"):
        raise HTTPException(status_code=422, detail="rating must be 'useful' or 'not_useful'")

    result = await session.execute(
        select(ConversationLog).where(
            ConversationLog.id == log_id,
            ConversationLog.user_id == current_user.id,
        )
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="Conversation log not found.")

    log.rating = FeedbackRating(body.rating)
