from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routers import admin_router, auth_router, users_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = get_settings()
    yield
    # Phase 2: RAG checkpointer teardown added in plan 02-03


app = FastAPI(
    title="Cancella RAG Support API",
    version="0.1.0",
    description="Level 1 technical support RAG chatbot — Cancella Informática",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(admin_router, prefix="/admin")
app.include_router(auth_router, prefix="/auth")
app.include_router(users_router, prefix="/admin")

# Phase 2 plan 02-04 will add:
# app.include_router(chat_router, prefix="/chat")
