<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-6E40C9?logo=modelcontextprotocol&logoColor=white" alt="MCP Compatible" />
  <img src="https://img.shields.io/badge/Tools-97-00D4AA" alt="97 Tools" />
  <img src="https://img.shields.io/badge/Chains-7-F7931A" alt="7 Chains" />
  <img src="https://img.shields.io/badge/x402-Payment-FF6900" alt="x402 Payment" />
  <img src="https://img.shields.io/badge/Tier-Free-22C55E" alt="Free Tier" />
</p>

<h1 align="center">Rug Munch Intelligence — MCP Server</h1>

<p align="center"><strong>The Bloomberg of Shitcoins Terminal Ultimate Edition</strong></p>

<p align="center">
  97 tools for scam detection, rug pull prevention, and crypto intelligence across 7 chains.<br/>
  Keeping retail investors safe.
</p>

---

## Mission

We are building scam detection tools to keep retail investors and the broader crypto space safe from scams and scammers. **The Bloomberg of Shitcoins — terminal ultimate edition.**

## Architecture

This MCP server is a **client for the Rug Munch Intelligence x402 API**. It wraps all 97 tools into the Model Context Protocol so AI agents can use them natively.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AI Agent       │     │  x402 Gateway     │     │  RMI Backend    │
│  (Claude/Cursor)│     │  (Cloudflare)     │     │  (97 tools)     │
│                 │     │                   │     │                 │
│  this MCP ──────┼────►│  Base worker     ├────►│  intelligence   │
│  server         │     │  Solana worker    │     │  security       │
│                 │     │                   │     │  market         │
│  OR direct ─────┼────►│                   │     │  forensics      │
│  HTTP calls     │     │  payment check    │     │  analysis       │
│                 │     │  trial enforcement │     │  social         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Multiple ways to access the same 97 tools:**

1. **This MCP server** — `pip install rug-munch-intelligence-mcp` — for AI agents (Claude, Cursor, Windsurf)
2. **OpenAI function calling** — `GET /api/v1/x402-tools/openai-tools` — drop-in for any OpenAI-compatible agent
3. **Anthropic Claude API** — `GET /api/v1/x402-tools/anthropic-tools` — native Claude tool use format
4. **Google Gemini** — `GET /api/v1/x402-tools/gemini-tools` — Gemini function declarations
5. **LangChain** — `GET /api/v1/x402-tools/langchain-tools` — ready for `create_react_agent` or LangGraph
6. **Direct HTTP** — `POST https://rugmunch.io/api/v1/x402-tools/{tool}` — for apps, bots, scripts

All go through the same x402 payment gateway and hit the same backend. The MCP server just translates MCP protocol into HTTP calls.

The x402 gateways live here:
- [x402-gateway-base](https://github.com/Rug-Munch-Media-LLC/x402-gateway-base) — Base + EVM chains
- [x402-gateway-solana](https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana) — Solana

## Quick Start

```bash
pip install rug-munch-intelligence-mcp
```

### Claude Desktop / Cursor / Windsurf

```json
{
  "mcpServers": {
    "rug-munch-intelligence": {
      "command": "python3",
      "args": ["-m", "rug_munch_mcp"],
      "env": {
        "RUG_MUNCH_API_BASE": "https://rugmunch.io/api/v1"
      }
    }
  }
}
```

### OpenAI Agents / LangChain / Gemini

No install needed — fetch the tool schemas directly:

```bash
# OpenAI function calling format
curl https://rugmunch.io/api/v1/x402-tools/openai-tools

# Anthropic Claude API format
curl https://rugmunch.io/api/v1/x402-tools/anthropic-tools

# Google Gemini function declarations
curl https://rugmunch.io/api/v1/x402-tools/gemini-tools

# LangChain structured format
curl https://rugmunch.io/api/v1/x402-tools/langchain-tools
```

Then call tools via HTTP:

```bash
curl -X POST https://rugmunch.io/api/v1/x402-tools/whale_scan \
  -H "Content-Type: application/json" \
  -d '{"chain":"solana","token_address":"So11111111111111111111111111111111111111112"}'
```

## Payment

All tool calls go through the x402 micropayment system:

- **Free tier** — 1 call per tool (fingerprint-based), 3 with wallet verification
- **Per-call** — $0.01 to $0.50 per tool via USDC on any supported chain
- **Refund** — POST `/api/v1/x402/refund` if a call returns no data
- **Dashboard** — GET `/api/v1/x402/dashboard` for your usage stats
- **Discovery** — GET `/.well-known/x402` for the full x402 service manifest

**How payment works:**
- **Base + Solana** — verified via PayAI facilitator (fast, federated)
- **Ethereum, BSC, Arbitrum, Optimism, Polygon** — self-verified via local EIP-712 cryptographic verification (no external dependency, uses on-chain USDC receipt check via Etherscan)

The MCP server and framework clients don't handle payments — the x402 gateway does that transparently. You just make tool calls and they work.

## 97 Tools

### Intelligence (28)
| Tool | Price | Description |
|------|-------|-------------|
| whale_scan | $0.03 | Scan a token for whale concentration and large-holder risk |
| smartmoney | $0.05 | Track smart money wallets and whale movements across chains |
| cluster | $0.05 | Wallet cluster analysis — linked wallets, sybil networks, manipulation |
| insider | $0.10 | Insider trading detection — pre-launch accumulation, coordinated buying |
| whale_profile | $0.05 | Behavioral profile and influence score for any wallet |
| airdrop_finder | $0.05 | Find unclaimed airdrops for any wallet across chains |
| copy_trade_finder | $0.10 | Identify profitable wallets worth following |
| social_signal | $0.10 | Twitter + news + on-chain sentiment combined into one score |
| sentiment | $0.03 | Real-time social sentiment (0-100) across Twitter, Telegram, RSS |
| smart_money_alpha | $0.05 | What profitable wallets are buying now |
| liquidity_flow | $0.08 | Track liquidity inflows/outflows for any token or pool |
| risk_monitor | $0.05 | Real-time risk monitoring — rug pulls, liquidity removals, whale dumps |
| rug_pull_predictor | $0.10 | AI-powered rug pull prediction |
| meme_vibe_score | $0.01 | Meme token community vibe and virality score |
| nft_wash_detector | $0.10 | Detect fake NFT volume and floor price manipulation |
| gas_forecast | $0.05 | Predict optimal gas prices and cheapest transaction windows |
| bridge_security | $0.08 | Cross-chain bridge security — TVL, exploits, audit status |
| defi_yield_scanner | $0.08 | Find best DeFi yields, detect unsustainable APYs |
| portfolio_tracker | $0.10 | Multi-wallet portfolio tracker — PnL, allocation, gains |
| token_deep_dive | $0.10 | Deep token analysis across all data sources |
| token_comparison | $0.08 | Side-by-side token comparison |
| forensic_valuation | $0.25 | Forensic-level token valuation combining all signals |
| comprehensive_audit | $0.50 | Full audit: contract + holders + deployer + social + liquidity |
| investigation_report | $0.20 | Structured investigation report |
| market_overview | $0.05 | Full market overview — BTC, ETH, trending, TVL, sentiment |
| chain_health | $0.05 | Chain health metrics — TVL, gas, block times, protocols |
| anomaly | $0.08 | Market anomaly detection — volume spikes, manipulation, extremes |
| honeypot_check | $0.05 | Can you actually sell? Simulates buy/sell to detect traps |
| mev_protection | $0.08 | MEV exposure analysis — sandwich risk, front-running detection |

### Security (17)
| Tool | Price | Description |
|------|-------|-------------|
| urlcheck | $0.01 | URL safety — domain age, phishing patterns, risk score |
| rugshield | $0.02 | Quick pre-buy rug check — safe/unsafe verdict |
| clone_detect | $0.02 | Token clone detection — copies of legitimate projects |
| audit | $0.05 | Deep contract audit — mint, freeze, liquidity, holders |
| fresh_pair | $0.03 | Newly created pair detection and risk scoring |
| profile_flip | $0.03 | Wallet behavioral pattern change detection |
| sniper_detect | $0.08 | Bot ring and coordinated buy detection |
| slither_audit | $0.10 | Solidity static analysis — 60+ vulnerability types |
| + all shared security tools | | honeypot_check, rug_pull_predictor, bridge_security, mev_protection, risk_monitor, anomaly, comprehensive_audit, forensic_valuation, gas_forecast, chain_health |

### Market (14)
pulse, coingecko_global, coingecko_trending, coingecko_markets, coingecko_categories, market_overview, sentiment, social_signal, smart_money_alpha, copy_trade_finder, defi_yield_scanner, liquidity_flow, gas_forecast, chain_health

### Analysis (12)
tx_decoder, wallet, contract_info, storage_reader, meme_vibe_score, token_deep_dive, token_comparison, forensic_valuation, portfolio_tracker, comprehensive_audit, investigation_report, risk_monitor

### Forensics (7)
forensics_threat_check, forensics_risk_report, forensics_deep_scan, forensics_cross_chain, bundle_security_pack, honeypot_check, rug_pull_predictor

### Social (7)
tw_profile, tw_timeline, tw_search, profile_get, profile_badges, social_signal, sentiment

### OSINT (3)
osint_search, osint_identity_hunt, osint_investigate

### Launchpad (3)
launch, launch_intel, sniper_alert

### News (3)
news_headlines, news_twitter, news_combined

### Meta (3)
list_bundles, tools_discovery, framework_discovery

## Supported Chains

| Chain     | Symbol | Payment Verification |
|-----------|--------|---------------------|
| Solana    | SOL    | PayAI facilitator |
| Base      | BASE   | PayAI facilitator |
| Ethereum  | ETH    | Self-verified (EIP-712 + Etherscan) |
| BSC       | BSC    | Self-verified |
| Arbitrum  | ARB    | Self-verified |
| Optimism  | OP     | Self-verified |
| Polygon   | POL    | Self-verified |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUG_MUNCH_API_BASE` | `https://rugmunch.io/api/v1` | API base URL |
| `RUG_MUNCH_API_KEY` | (none) | Optional API key for authenticated access |

## Related Repos

- [x402-gateway-base](https://github.com/Rug-Munch-Media-LLC/x402-gateway-base) — x402 payment gateway for Base + EVM
- [x402-gateway-solana](https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana) — x402 payment gateway for Solana
- [rugcharts](https://github.com/Rug-Munch-Media-LLC/rugcharts) — Professional charting & TA analysis
- [rugmunch.io](https://rugmunch.io) — Web app

## License

Proprietary — Copyright 2026 Rug Munch Media LLC. All rights reserved.
Commercial access via x402 API at https://rugmunch.io/api/v1
For commercial licensing: dev@cryptorugmuncher@gmail.com