import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routers import admin_router, auth_router, chat_router, users_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.rag import setup_rag_graph
    app.state.rag_graph = await setup_rag_graph()
    logger.info("RAG graph ready")
    yield


app = FastAPI(
    title="Cancella RAG Support API",
    version="0.2.0",
    description="Level 1 technical support RAG chatbot — Cancella Informática",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


app.include_router(admin_router, prefix="/admin")
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/admin")
app.include_router(chat_router, prefix="/chat")
