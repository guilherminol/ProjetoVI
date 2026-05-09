# Sistema RAG de Suporte Técnico — Cancella Informática

## Project Overview

RAG-based Level 1 technical support chatbot for Cancella Informática LTDA. B2B clients ask technical questions; the system answers exclusively from indexed PDF manuals using a LangGraph RAG pipeline — no hallucinations, no human wait time.

**Core value:** Respond to repetitive technical questions instantly, freeing the single Level 1 technician for high-complexity infrastructure work.

**Stack:** Python 3.11 + FastAPI + LangGraph 1.1.x + PostgreSQL 16 + pgvector 0.8.x + React 18 + Docker Compose. LLM via OpenRouter. On-premise deployment.

## GSD Workflow

This project uses the GSD (Get Shit Done) planning system.

**Key commands:**
- `/gsd-plan-phase 1` — plan Phase 1 (Foundation)
- `/gsd-discuss-phase N` — discuss and clarify approach before planning a phase
- `/gsd-execute-phase N` — execute all plans in a phase
- `/gsd-progress` — check current status

**Planning artifacts** (local only, not in git):
- `.planning/PROJECT.md` — project context and requirements
- `.planning/REQUIREMENTS.md` — scoped v1 requirements with REQ-IDs
- `.planning/ROADMAP.md` — 4-phase roadmap
- `.planning/research/` — domain research (stack, features, architecture, pitfalls)

## Architecture Decisions (locked)

| Decision | Rationale |
|----------|-----------|
| text-embedding-3-small (1536d) | Replaces ada-002 — 5x cheaper, higher quality. Dimension locked before first migration. |
| PostgresSaver (not MemorySaver) | Session state must survive container restarts. Use from Phase 2 onward. |
| HNSW index in Alembic migration | Required for <5s latency. Create at `vector(1536)` column creation time. |
| pgvector/pgvector:pg16 Docker image | `postgres:16` does NOT include pgvector extension. |
| pymupdf4llm + Docling (dual parser) | pymupdf4llm for digital PDFs; Docling as OCR fallback for legacy/scanned docs. |
| SSE streaming (not WebSockets) | Unidirectional LLM token streaming — simpler and native to OpenRouter/Anthropic. |
| FastAPI BackgroundTasks (not Celery) | PDF ingestion async — no broker needed at this scale. |
| No Redis | PostgresSaver handles sessions; no dedicated cache needed for 3-4 concurrent users. |

## Phase Roadmap

| # | Phase | Goal | Status |
|---|-------|------|--------|
| 1 | Foundation | Docker infra + DB schema (HNSW) + PDF ingestion pipeline | Not started |
| 2 | Core RAG + Auth + Chat API | LangGraph RAG graph + JWT auth + PostgresSaver sessions + SSE streaming | Not started |
| 3 | React Frontend | Login UI + chat widget + admin panels (upload, docs, feedback) | Not started |
| 4 | Hardening + Deploy Validation | P95 latency test + health checks + structured logging + deploy runbook | Not started |

## Critical Constraints

- **Embedding dimension must be locked in Phase 1** before any vector data is written — changing it requires full re-ingestion
- **LangGraph hallucination guard node is non-negotiable** — IT infrastructure wrong answers cause real downtime
- **PostgresSaver required before any user testing** — MemorySaver wipes sessions on container restart
- **Pin all Docker image versions from Phase 1** — floating versions cause silent breaks on production server
- **Data sovereignty:** Confirm with Cancella whether document text can leave the on-premise server via OpenRouter/OpenAI API before Phase 2

## Non-Functional Requirements

- Max 5s P95 response latency
- 24/7 availability (Docker restart policies)
- 3-4 concurrent users
- 100% on-premise execution (Docker Compose, no cloud storage for documents)

## Team

- Guilhermino Lucas Chaves Araújo (guilhermino.araujo@groupsoftware.com.br)
- Luis Fernando da Rocha Cancella (luisfernando@cancella.com.br)
- André Luiz Santos Moreira da Silva (andremoreiradasilva95@gmail.com)

**Stakeholder:** Danton Cancella (founder, Cancella Informática LTDA)
**Context:** PUC Minas — Projeto VI (Práticas Extensionistas), Feb–Jul 2026
