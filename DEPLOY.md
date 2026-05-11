# Deploy Runbook — Cancella RAG Support

Cold-start deployment on a clean on-premise Linux machine (Ubuntu 22.04 recommended).

---

## 1. Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| Docker Engine | 24.x | https://docs.docker.com/engine/install/ |
| Docker Compose plugin | 2.x | bundled with Docker Engine |
| Git | any | `apt install git` |

---

## 2. Clone the repository

```bash
git clone <repo-url> /opt/cancella-rag
cd /opt/cancella-rag
```

---

## 3. Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in these required values:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_USER` | DB user | `rag` |
| `POSTGRES_PASSWORD` | DB password | choose a strong password |
| `POSTGRES_DB` | DB name | `ragdb` |
| `DATABASE_URL` | SQLAlchemy async URL | `postgresql+asyncpg://rag:<password>@db:5432/ragdb` |
| `ADMIN_API_KEY` | Legacy admin key (kept for compat) | any random string |
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-...` |
| `JWT_SECRET_KEY` | JWT signing secret (32+ bytes) | `openssl rand -hex 32` |

**Generate JWT secret:**
```bash
openssl rand -hex 32
```

---

## 4. Build and start containers

```bash
docker compose up -d --build
```

Expected output: `db`, `api`, and `frontend` containers all healthy.

Verify:
```bash
docker compose ps
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.2.0","db":"ok"}
```

---

## 5. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

Expected: migrations 0001, 0002, 0003 applied.

---

## 6. Create the first admin user

```bash
docker compose exec api python - <<'EOF'
import asyncio
from app.db.session import AsyncSessionFactory
from app.models.user import User, UserRole
from app.core.security import hash_password

async def create_admin():
    async with AsyncSessionFactory() as session:
        user = User(
            email="admin@cancella.com.br",
            hashed_password=hash_password("change-this-password"),
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        print(f"Admin created: {user.email}")

asyncio.run(create_admin())
EOF
```

Then log in at `http://<server-ip>:3000` and change the password via the admin panel.

---

## 7. Upload the first PDF manual

Via the web UI:
1. Log in as admin at `http://<server-ip>:3000`
2. Click **Painel Admin → Upload**
3. Select a PDF and click **Fazer Upload**
4. Monitor ingestion status in the **Documentos** tab until status = `ready`

Via API:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin@cancella.com.br&password=change-this-password" \
  | jq -r .access_token)

curl -X POST http://localhost:8000/admin/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/manual.pdf"
```

---

## 8. Smoke test

```bash
# Health
curl http://localhost:8000/health

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin@cancella.com.br&password=change-this-password" \
  | jq -r .access_token)

# Chat (streaming)
curl -N -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Como configurar a rede?"}'
```

---

## 9. P95 latency validation

After at least one document is indexed:

```bash
pip install httpx
python scripts/load_test.py \
  --url http://localhost:8000 \
  --email admin@cancella.com.br \
  --password change-this-password \
  --concurrency 4 \
  --requests 20
```

Target: **P95 < 5 seconds**. If it fails, check OpenRouter latency and vector index health.

---

## 10. Container restart validation

```bash
# Kill the API container hard
docker kill cancella-rag-api-1

# Verify it restarts automatically (restart: unless-stopped)
sleep 5
docker compose ps

# Verify health
curl http://localhost:8000/health
```

---

## 11. Logs

```bash
# All services
docker compose logs -f

# API only (structured JSON)
docker compose logs -f api | jq .
```

---

## 12. Updates

```bash
git pull
docker compose up -d --build
docker compose exec api alembic upgrade head
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `db` container unhealthy | Check `POSTGRES_USER/PASSWORD/DB` in `.env` |
| `api` exits on start | Check `DATABASE_URL` format; run `docker compose logs api` |
| Ingestion stuck in `processing` | Check `OPENROUTER_API_KEY`; run `docker compose logs api` |
| Chat returns not_found always | No documents indexed yet, or `status != ready` |
| P95 > 5s | OpenRouter latency spike — retry; or reduce `TOP_K` in `retrieval.py` |
