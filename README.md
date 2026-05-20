<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-6E40C9?logo=modelcontextprotocol&logoColor=white" alt="MCP Compatible" />
  <img src="https://img.shields.io/badge/Tools-97-00D4AA" alt="97 Tools" />
  <img src="https://img.shields.io/badge/Chains-7-F7931A" alt="7 Chains" />
  <img src="https://img.shields.io/badge/x402-Payment-FF6900?logo=coinbase&logoColor=white" alt="x402 Payment" />
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

This MCP server is a **client for the Rug Munch Intelligence x402 API**. It wraps all 97 tools into the Model Context Protocol so AI agents like Claude Desktop, Cursor, and Windsurf can use them natively.

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
│                 │     │  trial enforcement│     │  social         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Two ways to access the same 97 tools:**

1. **This MCP server** — `pip install rug-munch-intelligence-mcp` — for AI agents
2. **Direct HTTP** — `POST https://cryptorugmunch.app/api/v1/x402-tools/{tool}` — for apps, bots, scripts

Both go through the same x402 payment gateway and hit the same backend. The MCP server just translates MCP protocol into HTTP calls.

The x402 gateways live here:
- [x402-gateway-base](https://github.com/Rug-Munch-Media-LLC/x402-gateway-base) — Base + EVM chains
- [x402-gateway-solana](https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana) — Solana

## Quick Start

```bash
pip install rug-munch-intelligence-mcp
```

### Claude Desktop

```json
{
  "mcpServers": {
    "rug-munch-intelligence": {
      "command": "python3",
      "args": ["-m", "rug_munch_mcp"],
      "env": {
        "RUG_MUNCH_API_BASE": "https://cryptorugmunch.app/api/v1"
      }
    }
  }
}
```

### Cursor / Windsurf

Same config in your MCP settings file. Point the command at the installed module.

### Direct HTTP (no install needed)

```bash
curl -X POST https://cryptorugmunch.app/api/v1/x402-tools/whale_scan \
  -H "Content-Type: application/json" \
  -d '{"chain":"solana","token_address":"So11111111111111111111111111111111111111112"}'
```

First call is free (fingerprint trial). After that, x402 USDC micropayment required.

## Payment

All tool calls go through the x402 micropayment system:

- **Free tier** — 1 call per tool (fingerprint-based), 3 with wallet verification
- **Per-call** — $0.01 to $0.15 per tool via USDC on Base or Solana
- **Refund** — POST `/api/v1/x402/refund` if a call returns no data
- **Dashboard** — GET `/api/v1/x402/dashboard` for your usage stats

The MCP server doesn't handle payments itself — the x402 gateway does that transparently. You just make tool calls and they work.

## 97 Tools

### Intelligence (28)
| Tool | Description |
|------|-------------|
| whale_scan | Track top whale wallets — large buys/sells, exchange flows, accumulation |
| smartmoney | Real-time smart money tracking — top 100 wallets, patterns, alerts |
| cluster | Wallet cluster analysis — linked wallets, sybil networks, coordinated manipulation |
| insider | Insider trading detection — pre-launch accumulation, coordinated buying |
| whale_profile | Advanced whale decoder — balance, TX patterns, persona classification |
| airdrop_finder | Find unclaimed airdrops for any wallet across chains |
| copy_trade_finder | Identify profitable wallets worth following — win rates, best trades |
| social_signal | Twitter + news + on-chain sentiment combined into one score |
| sentiment | Real-time social sentiment (0-100) across Twitter, Telegram, RSS |
| smart_money_alpha | Smart money alpha signals — what profitable wallets are buying now |
| liquidity_flow | Track liquidity inflows/outflows for any token or pool |
| risk_monitor | Real-time risk monitoring — rug pulls, liquidity removals, whale dumps |
| rug_pull_predictor | AI-powered rug pull prediction before it happens |
| meme_vibe_score | Meme token community vibe and virality score |
| nft_wash_detector | Detect fake NFT volume and floor price manipulation |
| gas_forecast | Predict optimal gas prices and cheapest transaction windows |
| bridge_security | Cross-chain bridge security — TVL, exploits, audit status |
| defi_yield_scanner | Find best DeFi yields, detect unsustainable APYs |
| portfolio_tracker | Multi-wallet portfolio tracker — PnL, allocation, gains |
| token_deep_dive | Deep token analysis across all data sources |
| token_comparison | Side-by-side token comparison on metrics, risk, sentiment |
| forensic_valuation | Forensic-level token valuation combining all signals |
| comprehensive_audit | Full audit: contract + holders + deployer + social + liquidity |
| investigation_report | Structured investigation report for any token or wallet |
| market_overview | Full market overview — BTC, ETH, trending, TVL, sentiment |
| chain_health | Chain health metrics — TVL, gas, block times, protocols |
| anomaly | Market anomaly detection — volume spikes, manipulation, extremes |
| honeypot_check | Can you actually sell? Simulates buy/sell to detect traps |
| mev_protection | MEV exposure analysis — sandwich risk, front-running detection |

### Security (17)
| Tool | Description |
|------|-------------|
| urlcheck | URL safety analysis — domain age, scam patterns, risk score |
| rugshield | Quick pre-buy rug check — safe/unsafe verdict with factors |
| clone_detect | Token clone detection — copies of legitimate projects |
| audit | Deep contract audit — mint, freeze, liquidity, holders |
| fresh_pair | Newly created pair detection and risk scoring |
| profile_flip | Wallet behavioral pattern change detection |
| honeypot_check | Honeypot detection — can you sell? Transfer taxes, locks |
| rug_pull_predictor | AI rug pull prediction |
| bridge_security | Bridge security assessment |
| mev_protection | MEV exposure analysis |
| risk_monitor | Real-time risk monitoring |
| anomaly | Market anomaly detector |
| comprehensive_audit | Full token audit |
| investigation_report | Investigation report |
| forensic_valuation | Forensic valuation |
| gas_forecast | Gas price forecaster |
| chain_health | Chain health metrics |

### Market (14)
| Tool | Description |
|------|-------------|
| pulse | Market pulse — momentum, volume spikes, whale alerts, trending |
| coingecko_global | Global crypto market data from CoinGecko |
| coingecko_trending | Trending coins on CoinGecko |
| coingecko_markets | Top markets by cap, volume, change |
| coingecko_categories | Crypto categories and sector performance |
| market_overview | Aggregated market overview from 10+ sources |
| sentiment | Social sentiment score |
| social_signal | Combined social + on-chain signal |
| smart_money_alpha | Smart money buying signals |
| copy_trade_finder | Profitable wallet finder |
| defi_yield_scanner | DeFi yield scanner |
| liquidity_flow | Liquidity tracking |
| gas_forecast | Gas forecaster |
| chain_health | Chain health |

### Analysis (12)
| Tool | Description |
|------|-------------|
| tx_decoder | Decode any transaction — calls, transfers, swaps, traces |
| wallet | Comprehensive wallet analysis — balance, tokens, risk, behavior |
| contract_info | Contract metadata, verification, ABI, functions |
| storage_reader | Read on-chain contract storage slots |
| meme_vibe_score | Meme community virality score |
| token_deep_dive | Deep cross-source token analysis |
| token_comparison | Side-by-side token comparison |
| forensic_valuation | Forensic-level valuation |
| portfolio_tracker | Portfolio tracker |
| comprehensive_audit | Full audit |
| investigation_report | Investigation report |
| risk_monitor | Risk monitoring |

### Forensics (7)
| Tool | Description |
|------|-------------|
| forensics_threat_check | Threat assessment — known patterns, flags, history |
| forensics_risk_report | Structured risk report with evidence |
| forensics_deep_scan | Deep forensic scan — deployer, holders, social, contract |
| forensics_cross_chain | Cross-chain forensic correlation |
| bundle_security_pack | Security bundle — multiple checks in one call |
| honeypot_check | Honeypot detection |
| rug_pull_predictor | Rug pull prediction |

### Social (7)
| Tool | Description |
|------|-------------|
| tw_profile | Twitter/X user profile — followers, bio, verification |
| tw_timeline | User's recent tweets — text, engagement, timestamps |
| tw_search | Search Twitter/X for matching tweets |
| profile_get | RMI user profile data |
| profile_badges | User badge and reputation data |
| social_signal | Combined social + on-chain signal |
| sentiment | Real-time sentiment score |

### OSINT (3)
| Tool | Description |
|------|-------------|
| osint_search | Open-source intelligence search |
| osint_identity_hunt | Cross-reference identities across platforms |
| osint_investigate | Deep OSINT investigation for any entity |

### Launchpad (3)
| Tool | Description |
|------|-------------|
| launch | Token launch analysis — bonding curve, liquidity, holders |
| launch_intel | Launch intelligence — new tokens, trending pairs |
| sniper_alert | Sniper bot detection on new launches |

### News (3)
| Tool | Description |
|------|-------------|
| news_headlines | Latest crypto news headlines |
| news_twitter | Crypto Twitter/X news feed |
| news_combined | Combined news from all sources |

### Meta (3)
| Tool | Description |
|------|-------------|
| list_bundles | List available tool bundles |
| tools_discovery | Discover all available tools and their specs |
| framework_discovery | Framework integration guides (LangChain, OpenAI, etc.) |

## Supported Chains

| Chain     | Symbol | Payment |
|-----------|--------|---------|
| Solana    | SOL    | USDC via x402 facilitator |
| Base      | BASE   | USDC, self-verified |
| Ethereum  | ETH    | USDC, self-verified |
| BSC       | BSC    | USDC, self-verified |
| Arbitrum  | ARB    | USDC, self-verified |
| Optimism  | OP     | USDC, self-verified |
| Polygon   | POL    | USDC, self-verified |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUG_MUNCH_API_BASE` | `https://cryptorugmunch.app/api/v1` | API base URL |
| `RUG_MUNCH_API_KEY` | (none) | Optional API key for authenticated access |

## Framework Integrations

The tools work with any framework that supports MCP or HTTP:

- **Claude Desktop** — MCP stdio transport
- **Cursor** — MCP stdio transport
- **Windsurf** — MCP stdio transport
- **LangChain** — HTTP via `langchain-community` tools
- **OpenAI Agents** — HTTP function calling
- **CrewAI** — HTTP tool integration
- **AutoGen** — HTTP tool integration

## Related Repos

- [x402-gateway-base](https://github.com/Rug-Munch-Media-LLC/x402-gateway-base) — x402 payment gateway for Base + EVM
- [x402-gateway-solana](https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana) — x402 payment gateway for Solana
- [rugcharts](https://github.com/Rug-Munch-Media-LLC/rugcharts) — Professional charting & TA analysis

## License

Proprietary — Copyright 2026 Rug Munch Media LLC. All rights reserved.
Commercial access via x402 API at https://cryptorugmunch.app/api/v1
For commercial licensing: dev@cryptorugmunch.app