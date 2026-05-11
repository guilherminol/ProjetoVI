import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.core.logging_config import configure_logging
from app.db.session import AsyncSessionFactory
from app.routers import admin_router, auth_router, chat_router, users_router

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.rag import setup_rag_graph
    app.state.rag_graph = await setup_rag_graph()
    logger.info("RAG graph ready", extra={"event": "startup"})
    yield


app = FastAPI(
    title="Cancella RAG Support API",
    version="0.2.0",
    description="Level 1 technical support RAG chatbot — Cancella Informática",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    db_status = "ok"
    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    status = "ok" if db_status == "ok" else "degraded"
    return {"status": status, "version": "0.2.0", "db": db_status}


app.include_router(admin_router, prefix="/admin")
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/admin")
app.include_router(chat_router, prefix="/chat")
