from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routers import admin_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = get_settings()
    yield


app = FastAPI(
    title="Cancella RAG Support API",
    version="0.1.0",
    description="Level 1 technical support RAG chatbot — Cancella Informática",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# Admin router: document management (Phase 1)
# /admin/documents/upload  POST  202
# /admin/documents         GET
# /admin/documents/{id}    GET, DELETE
app.include_router(admin_router, prefix="/admin")

# Phase 2 will add:
# app.include_router(auth_router, prefix="/auth")
# app.include_router(chat_router, prefix="/chat")
