# Rug Munch Intelligence — Backend

> **⚠️ PROPRIETARY SOFTWARE — ALL RIGHTS RESERVED**
>
> (c) 2026 Rug Munch Media LLC. Confidential and proprietary.
> Unauthorized access, distribution, or use is strictly prohibited.
> See [LICENSE](LICENSE) for full terms.

---

## What This Is

Rug Munch Intelligence (RMI) is the proprietary crypto scam detection platform. This repository contains the core backend — the detection engine, data pipeline, and API infrastructure powering the entire RMI ecosystem.

**This is NOT open-source.**

📡 **Telegram**: [@CryptoRugMunch](https://t.me/CryptoRugMunch) • [@cryptorugmuncher](https://t.me/cryptorugmuncher)
🐦 **X/Twitter**: [@cryptorugmunch](https://x.com/cryptorugmunch)
🌐 **Website**: [rugmunch.io](https://rugmunch.io)

---
 Maintained exclusively by Rug Munch Media LLC.

### Capabilities
- Real-time rug-pull detection across 7 chains
- On-chain behavioral analysis engines
- x402 Protocol v2 — pay-per-tool API access via crypto micropayments
- 97+ intelligence tools via MCP (Model Context Protocol) catalog
- Multi-source news aggregation (15+ feeds: RSS, Reddit, API)
- Wallet clustering, Sybil detection, scam pattern databases
- Gamification, payments, content syndication
- Telegram bot integration

---

## Products Under RMI

| Product | Repo | Description |
|---------|------|-------------|
| **RMI Backend** | `rugmuncher-backend` | Core API, detection, data pipeline |
| **RMI Frontend** | `rmi-frontend` | React/TypeScript web application |
| **RugCharts** | `rugcharts` | Real-time token charting, TA analysis |
| **RugMaps** | `rugmaps` | Visual blockchain threat mapping |
| **Telegram Bot** | `rugmuncher-telegram` | Community interface, scans, alerts |

---

## x402 Payment Protocol

The platform exposes 97+ tools via x402 HTTP 402 Payment Required protocol:

| Chain | Verification | Status |
|-------|-------------|--------|
| Solana | Facilitator (Cloudflare Worker) | Live |
| Base | Facilitator (Cloudflare Worker) | Live |
| ETH, BSC, ARB, OPT, POL | Self-verify (on-chain) | Live |

**Discovery:** `/.well-known/x402`  
**MCP Catalog:** `/api/v1/x402/tools-catalog`  
**OpenAPI:** `/openapi.json`

---

## Architecture

```
RMI Frontend (rmi-frontend)
    |
    v
RMI Backend (this repo) --- Redis (rmi-redis)
    |                           |
    +-- API Layer (FastAPI)     +-- RAG Vector Store
    +-- Detection Engine        +-- Session Cache
    +-- x402 Payment Gate       +-- Job Queue
    +-- News Aggregator (15+)
    +-- Content Syndicate
    |
    +-- Orchestrator (rmi-orchestrator) — 9 AI agents
    +-- Telegram Bot (rmi-telegram-bot) — Community interface
    +-- n8n (rmi-n8n) — Workflow automation
    +-- Supabase — Database, Auth, Storage
```

---

## Development

### Canonical Paths (READ BEFORE WORKING):
- Backend code: `/root/backend/` (this repo)
- Docker compose: `/srv/rugmuncher-backend/docker-compose.yml`
- Frontend source: `/srv/rugmuncher-backend/rmi-frontend/`
- Dev guide: `/root/DEVELOPERS.md`
- Standards: `/root/backend/STANDARDS.md`
- Pre-commit check: `bash /root/backend/scripts/pre-commit.sh`

### Quick Start:
```bash
# Live dev (volume mount, instant):
docker restart rmi-backend

# Full rebuild:
cd /srv/rugmuncher-backend
docker compose build backend --no-cache
docker compose up -d backend

# Setup env:
python3 /root/backend/generate_env.py --force
```

### API Reference:
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- News: http://localhost:8000/api/v1/news/headlines
- Tools catalog: http://localhost:8000/api/v1/x402/tools-catalog

---

## Licensing & Enterprise Access

### Institutional Clients:
Full API access, bulk historical data, custom model training, white-label embedding, SLA.  
Contact: **biz@rugmunch.io**

### Developers:
This is proprietary software. No public contribution model. Authorized developers only.

---

## Security

Vulnerability disclosure: **security@cryptorugmunch.com**  
90-day remediation window before any public disclosure.

---

*(c) 2026 Rug Munch Media LLC — Proprietary & Confidential*
