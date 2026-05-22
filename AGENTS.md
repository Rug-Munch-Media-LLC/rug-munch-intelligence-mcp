# /root/backend/ — RMI CANONICAL BACKEND

## ⚠️ THIS IS THE ONE AND ONLY BACKEND

All other copies are dead. If you find code at `/srv/rugmuncher-backend/main.py`,
`/root/rmi/backend/`, or anywhere else — it's STALE. Work here ONLY.

## Architecture

```
/root/backend/
├── main.py              # FastAPI app (5040 lines) — entry point
├── Dockerfile            # Backend container build
├── Dockerfile.worker     # Worker container build
├── requirements.txt      # Python dependencies
├── .env.example          # All required env vars documented
├── generate_env.py       # Auto-generate .env from Hermes config
├── app/                  # All application modules
│   ├── news_service.py   # 15+ source news aggregator
│   ├── rag_service.py    # Redis-based RAG vector store
│   ├── auth.py           # Authentication
│   ├── payments.py       # Payment processing
│   ├── content_syndicate.py  # Multi-platform content publishing
│   └── ... (80+ modules)
```

## How to Use

### Backend changes (Python):
```bash
# Edit files here. Volume mount means changes are LIVE:
docker restart rmi-backend

# Or for dependency changes, rebuild:
cd /srv/rugmuncher-backend
docker compose build backend --no-cache
docker compose up -d backend
```

### Environment setup:
```bash
python3 generate_env.py --force
# Then edit .env to fill in missing values
```

### API documentation:
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Docker Compose

Compose file: `/srv/rugmuncher-backend/docker-compose.yml`
Context: `context: /root/backend` (builds from here)
Mount: `/root/backend:/app` (live code, no rebuild needed)

All container names use hyphens: `rmi-backend`, `rmi-worker`, `rmi-n8n`, etc.

## Development Rules

1. **Never edit files outside this directory** for backend work
2. **Always `python3 generate_env.py`** after adding new env vars
3. **`.env` never committed** — use `.env.example` as template
4. **Test with `curl localhost:8000/health`** after changes
5. **Volume mount = live reload** — just restart the container

## Related Systems

| System | Location | Container |
|--------|----------|-----------|
| n8n workflows | /root/n8n-data/ | rmi-n8n |
| Orchestrator | /srv/rugmuncher-backend/orchestrator/ | rmi-orchestrator |
| Telegram bot | /srv/rugmuncher-backend/bots/telegram/ | rmi-telegram-bot |
| Frontend | /srv/rugmuncher-backend/rmi-frontend/ | Vercel/Cloudflare |
| Hermes AI | /root/.hermes/ | CLI process |  
| Langfuse | /srv/langfuse/ | Separate compose |
| Redis | Composed | rmi-redis |
