# Rug Munch Intelligence — Platform Documentation

## The Bloomberg Terminal of Shitcoins

Rug Munch Intelligence (RMI) is a unified crypto intelligence platform providing 234 tools for token security, wallet forensics, whale tracking, market data, and blockchain queries. Every data call routes through a multi-layer caching shield with automatic provider fallback across 20+ data sources.

**Access:** `https://mcp.rugmunch.io` | **Docs:** `https://rugmunch.io/docs`

---

## Quick Start

```bash
# Discover the platform
curl https://mcp.rugmunch.io/.well-known/mcp

# List all tools
curl https://mcp.rugmunch.io/mcp/tools

# Check platform health
curl https://mcp.rugmunch.io/mcp/health

# Get SDK examples
curl https://mcp.rugmunch.io/mcp/sdk
```

**MCP Native (Claude Desktop, Cursor, Windsurf):**
```json
{
  "mcpServers": {
    "rug-munch": {
      "url": "https://mcp.rugmunch.io/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Platform Capabilities

### Tool Categories (234 total)

| Category | Count | Description |
|----------|-------|-------------|
| Security Scanning | 45 | Rug pulls, honeypots, audits, clone detection, MEV protection |
| Wallet Intelligence | 38 | PnL, clustering, insider networks, whale tracking, forensics |
| Market Data | 32 | Prices, liquidity, volume, arbitrage, trends, OHLCV |
| Token Analytics | 28 | Holder distribution, sniper detection, deployer history |
| DeFi Analytics | 24 | TVL, yields, protocol risk, liquidity flow, bridges |
| Social Signals | 18 | Sentiment, KOL tracking, profile flips, meme scoring |
| Caching Shield | 13 | Internal multi-provider data access layer |
| Local MCP | 85 | Self-hosted Solana RPC (60) + EVM (25 tools, 86 networks) |
| Free Public MCP | 50 | Boar blockchain (ETH, ENS, contracts, keyless) |

### Supported Chains (13)
Solana, Ethereum, Base, BSC, Polygon, Arbitrum, Optimism, Avalanche, Fantom, Gnosis, TRON, Bitcoin, SEPA (fiat) + 86 EVM networks via local MCP

### Payment Facilitators (8)
Coinbase CDP, EIP-7702 Universal EVM, Cloudflare x402, PayAI, Asterpay (SEPA), TRON Self-Verify, Bitcoin Self-Verify, PrimeV

---

## Pricing & Access

### Free Trials
Every paid tool includes 1-5 free trial calls. No payment required until trials exhausted. Fingerprint-gated anti-abuse. Monthly reset.

### Individual Tools
$0.01 - $0.40 per call. Pay only for what you use. Full automatic refund within 48 hours if tool returns no data.

### Scan Packs (50-53% off)
| Pack | Tools | Price |
|------|-------|-------|
| Token Hunter Pack | Fresh pairs, snipers, security, deployer, clone detection | $0.09 |
| Whale Watcher Suite | Whale scan, accumulation, smart money, syndicates, PnL | $0.14 |
| Wallet Forensics | Funding trace, insider network, wash trading, wallet graph | $0.17 |
| Market Pulse | Prices, liquidity, arbitrage, sentiment, listings | $0.12 |

### Membership Tiers (60-90% discount)
| Tier | Price/mo | Daily Calls | Best For |
|------|----------|-------------|----------|
| Scout | $4.99 | 50 | Casual traders, hobby agents |
| Hunter | $14.99 | 200 | Active traders, alpha groups |
| Whale | $49.99 | 1,000 | Professional funds, market makers |
| Institution | $199.99 | 5,000 | Enterprises, high-frequency agents |

### Streaming Feeds
Real-time data via WebSocket + webhook delivery:
- New Token Firehose ($0.50/hr) — Every new token across all chains
- Whale Alert Stream ($0.75/hr) — Large transfers, positions, accumulation
- Multi-Chain Price Feed ($0.30/hr) — OHLCV, volume, arbitrage
- Security Alert Feed ($0.60/hr) — Rug pulls, exploits, suspicious activity

### Deep Research Reports
- Token Deep Dive ($0.75) — Full contract audit + deployer + holders + sentiment
- Wallet Intelligence Profile ($0.50) — PnL, style, associations, risk
- Chain Health Report ($0.25) — Gas, congestion, MEV, TVL, governance
- Cross-Chain Fund Trace ($1.50) — Follow money through bridges and mixers

### Batch Processing (75-90% off)
- Batch Token Scanner — 100 tokens, $0.05 per 10
- Batch Wallet Analysis — 50 wallets, $0.03 per 10
- Batch Pre-Buy Screen — 200 tokens, $0.02 per 50

### AI Data Feeds
- Market Context Feed ($9.99/mo) — LLM-optimized market summaries
- Alpha Signal Feed ($19.99/mo) — Scored trading signals
- Entity Relationship Graph ($14.99/mo) — Pre-computed wallet clusters

---

## Agent Skills (18 Workflows)

Every agent gets 18 guided workflows teaching best practices:

**Security & Vetting:** Pre-Buy Token Vetting, Scam Investigation, Post-Rug Forensics, Compliance Screening

**Trading & Execution:** Launch Day Playbook, MEV/Sandwich Avoidance, Market Making Intelligence, Portfolio Defense

**Alpha Discovery:** Alpha Discovery Pipeline, Whale Movement Tracking, CEX Listing Prediction, Insider Trading Detection

**DeFi & Yield:** Yield Farming Optimizer, Cross-Chain Bridge Monitor, DAO Governance Intelligence

**NFTs & Influencers:** NFT Mint Sniper, KOL Performance Tracker, Airdrop Hunting

Access at `GET /mcp/skills` — includes anti-abuse rules and 4 ready-to-use agent prompts.

---

## Technical Architecture

### Caching Shield
Every data call passes through three layers:
1. **L1 Memory Cache** — Sub-millisecond TTL lookup (8s-1hr depending on data type)
2. **Rate Limiter** — Token bucket per provider (prevents burning free tier quotas)
3. **Provider Chain** — Ordered fallback (3-4 providers per data type)

### Provider Fallback Chains
| Data Type | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|-----------|---------|------------|------------|------------|
| Token Price | Jupiter | Solana Tracker | DexScreener | Binance |
| Token Metadata | Helius DAS | Solana Tracker | Jupiter | DexScreener |
| Wallet Balance | Helius | QuickNode | Alchemy | PublicNode |
| Risk Scan | GoPlus | RugCheck | Honeypot | Local Labels |
| EVM Funding | Blockscout | Etherscan | Public RPC | Boar MCP |

### Infrastructure
- **Server:** Bare metal VPS, Docker Compose (30 containers)
- **Secrets:** GPG-encrypted vault (76 secrets), age-encrypted runtime injection
- **CI/CD:** GitHub Actions auto-deploy on push to main
- **Edge:** Cloudflare Workers for x402 payment gateway
- **Observability:** Langfuse cloud with smart sampling (20% normal, 100% errors)

### Local MCP Servers
Two self-hosted MCP servers run on our infrastructure:
- **Solana SVM MCP** (Rust, 32MB binary) — 60 RPC tools, WebSocket subscriptions, built-in x402
- **EVM MCP** (TypeScript, bun runtime) — 25 tools across 86 networks, ENS, contracts, gas

---

## API Reference

### MCP Protocol (Streamable HTTP)
```
POST /mcp                    JSON-RPC endpoint
GET  /mcp/tools              Tool catalog with input schemas
GET  /mcp/call/{tool_id}     Direct tool execution
GET  /.well-known/mcp        Server discovery
GET  /.well-known/x402       Payment protocol discovery
```

### Platform Endpoints
```
GET  /mcp/health             Uptime + response time
GET  /mcp/status             Cache stats, provider health
GET  /mcp/manifest           Auto-updating platform manifest
GET  /mcp/skills             18 agent workflow guides
GET  /mcp/membership         Plans, pricing, scan packs
GET  /mcp/sdk                Python/TS/curl quick-start
GET  /mcp/changelog          Version history
GET  /mcp/trials             Free trial status
GET  /mcp/earnings           Revenue dashboard
```

### REST API
```
POST /api/v1/investigate/trace    Wallet funding source tracing
POST /api/v1/investigate/scan     Full investigation
GET  /api/v1/investigate/chains   Supported chains
GET  /api/v1/cache/health         Caching shield status
```

### Dashboard Pages
```
/earnings          Revenue dashboard (auto-refreshing)
/investigate       Wallet investigation tool
```

---

## SDKs & Integration

**Python:** `pip install rmi-agent-sdk`
```python
from rmi_agent import RMIAgent
agent = RMIAgent()  # auto-discovers via /.well-known/mcp
result = agent.call("rug_pull_predictor", {"token": "So111..."})
```

**TypeScript:** `npm install @rugmunch/agent-sdk`
```typescript
import { RMIAgent } from "@rugmunch/agent-sdk";
const agent = new RMIAgent();
const result = await agent.call("rug_pull_predictor", { token: "So111..." });
```

---

## Directory Listings

- **Smithery:** `https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence`
- **Glama:** `https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence`
- **mcp.so:** `https://mcp.so/server/rug-munch-intelligence`
- **GitHub:** `https://github.com/Rug-Munch-Media-LLC/rug-munch-intelligence-mcp`
- **HuggingFace:** `https://huggingface.co/cryptorugmunch/rug-munch-intelligence`

---

## Version History

### v3.3.0 (2026-06-01)
- 18 agent skills with workflow guides and anti-abuse rules
- 4 membership tiers with daily call limits (60-90% discount)
- 4 scan packs at 50-53% off individual tools
- 4 real-time streaming feeds (WebSocket + webhook)
- 4 deep research report products
- 3 batch scanning products (75-90% off)
- 3 AI-optimized data feeds for LLM consumption
- 85 local MCP tools (Solana RPC + EVM 86 networks)
- 50 free Boar blockchain tools (ETH, ENS, contracts)
- Multi-provider caching shield on every data call
- Platform manifest — single source of truth, auto-syncing
- Earnings dashboard with wallet tracking
- Quality endpoints: health, status, SDK, changelog, trials

### v3.2.0 (2026-05-15)
- POST /mcp JSON-RPC handler
- inputSchema on every tool
- Dynamic facilitator count
- CORS headers for browser clients

### v3.1.0 (2026-04-01)
- /.well-known/mcp discovery
- llms.txt for AI agent discovery
- x402 payment protocol support
- 8 payment facilitators across 13 chains

---

**Contact:** mcp@rugmunch.io | **GitHub:** github.com/Rug-Munch-Media-LLC
