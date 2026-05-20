<p align="center">
  <img src="https://raw.githubusercontent.com/Rug-Munch-Media-LLC/rug-munch-mcp/main/assets/banner.png" alt="Rug Munch Intelligence — MCP Server" width="800" />
</p>

<h1 align="center">Rug Munch Intelligence — MCP Server</h1>

<p align="center"><strong>The Bloomberg of Shitcoins Terminal Ultimate Edition</strong></p>

<p align="center">
  97 tools for scam detection, rug pull prevention, and crypto intelligence across 7 chains.<br/>
  Keeping retail investors safe.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-6E40C9?logo=modelcontextprotocol&logoColor=white" alt="MCP Compatible" />
  <img src="https://img.shields.io/pypi/v/rug-munch-mcp?color=3776AB&logo=pypi&logoColor=white" alt="PyPI" />
  <img src="https://img.shields.io/badge/Tools-97-00D4AA" alt="97 Tools" />
  <img src="https://img.shields.io/badge/Chains-7-F7931A" alt="7 Chains" />
  <img src="https://img.shields.io/badge/x402-Payment-FF6900?logo=coinbase&logoColor=white" alt="x402 Payment" />
  <img src="https://img.shields.io/badge/Tier-Free-22C55E" alt="Free Tier" />
  <img src="https://img.shields.io/badge/Smithery-Deploy-1a1a2e?logo=data:image/svg+xml;base64,&logoColor=white" alt="Smithery" />
  <img src="https://img.shields.io/badge/Glama-MCP-FF4081" alt="Glama" />
  <img src="https://img.shields.io/badge/Coinbase-x402-0052FF" alt="Coinbase x402" />
</p>

---

## Mission

We are building scam detection tools to keep retail investors and the broader crypto space safe from scams and scammers. **The Bloomberg of Shitcoins — terminal ultimate edition.**

---

## Quick Start

```bash
pip install rug-munch-mcp
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rug-munch": {
      "command": "uvx",
      "args": ["rug-munch-mcp"],
      "env": {
        "RUG_MUNCH_API_BASE": "https://cryptorugmunch.app/api/v1"
      }
    }
  }
}
```

> No API key required for the free tier. Set `RUG_MUNCH_API_KEY` for premium access.

---

## Supported Chains

| Chain | Symbol | Status |
|-------|--------|--------|
| Base | BASE | ✅ Live |
| Solana | SOL | ✅ Live |
| Ethereum | ETH | ✅ Live |
| BSC | BNB | ✅ Live |
| Arbitrum | ARB | ✅ Live |
| Optimism | OP | ✅ Live |
| Polygon | MATIC | ✅ Live |

---

## Tool Catalog — 97 Tools, 10 Categories

### Intelligence (28 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `whale_scan` | Track whale wallet movements and large transactions | All 7 |
| `smartmoney` | Identify smart money wallets and their positions | All 7 |
| `cluster` | Cluster related wallets by behavior patterns | All 7 |
| `airdrop_finder` | Find eligible airdrops for a wallet | All 7 |
| `whale_profile` | Deep profile of a whale wallet's history | All 7 |
| `insider` | Detect insider trading patterns before launches | All 7 |
| `smart_money_alpha` | Alpha signals from smart money activity | All 7 |
| `social_signal` | Social media signal aggregation for tokens | All 7 |
| `sentiment` | Market sentiment analysis across sources | All 7 |
| `copy_trade_finder` | Find wallets worth copy-trading | All 7 |
| `liquidity_flow` | Track liquidity inflows and outflows | All 7 |
| `risk_monitor` | Continuous risk monitoring for positions | All 7 |
| `rug_pull_predictor` | ML-based rug pull prediction scoring | All 7 |
| `meme_vibe_score` | Meme coin community vibe and virality scoring | All 7 |
| `nft_wash_detector` | Detect NFT wash trading patterns | ETH, SOL, Base |
| `gas_forecast` | Gas price forecasting and optimization | EVM chains |
| `bridge_security` | Cross-chain bridge risk assessment | All 7 |
| `defi_yield_scanner` | Scan DeFi yields and risk-adjusted returns | All 7 |
| `portfolio_tracker` | Track and analyze portfolio composition | All 7 |
| `token_deep_dive` | Deep fundamental analysis of any token | All 7 |
| `token_comparison` | Side-by-side token comparison analysis | All 7 |
| `forensic_valuation` | Forensic-based token valuation modeling | All 7 |
| `comprehensive_audit` | Full-scope audit of a token or contract | All 7 |
| `investigation_report` | Generate detailed investigation reports | All 7 |
| `market_overview` | Real-time market overview and metrics | All 7 |
| `chain_health` | Blockchain network health and congestion metrics | All 7 |
| `anomaly` | Detect anomalous on-chain behavior | All 7 |
| `honeypot_check` | Check if a token is a honeypot scam | All 7 |
| `mev_protection` | Assess MEV exposure and protection strategies | EVM chains |

### Security (17 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `urlcheck` | Check URLs for phishing and scam indicators | — |
| `rugshield` | Real-time rug pull shield and protection | All 7 |
| `clone_detect` | Detect cloned/fake tokens and contracts | All 7 |
| `fresh_pair` | Analyze freshly launched trading pairs | All 7 |
| `profile_flip` | Profile flip risk for token distributions | All 7 |
| `audit` | Smart contract security audit | All 7 |
| `honeypot_check` | Honeypot detection in security context | All 7 |
| `rug_pull_predictor` | Rug pull prediction (security focus) | All 7 |
| `bridge_security` | Bridge security assessment (security focus) | All 7 |
| `mev_protection` | MEV protection analysis (security focus) | EVM chains |
| `risk_monitor` | Risk monitoring (security focus) | All 7 |
| `anomaly` | Anomaly detection (security focus) | All 7 |
| `comprehensive_audit` | Comprehensive audit (security focus) | All 7 |
| `investigation_report` | Investigation report (security focus) | All 7 |
| `forensic_valuation` | Forensic valuation (security focus) | All 7 |
| `gas_forecast` | Gas forecast (security focus) | EVM chains |
| `chain_health` | Chain health (security focus) | All 7 |

### Market (14 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `pulse` | Real-time market pulse and momentum | All 7 |
| `coingecko_global` | Global market data from CoinGecko | All 7 |
| `coingecko_trending` | Trending tokens on CoinGecko | All 7 |
| `coingecko_markets` | Market cap and volume data | All 7 |
| `coingecko_categories` | CoinGecko category analysis | All 7 |
| `market_overview` | Market overview (macro focus) | All 7 |
| `sentiment` | Sentiment analysis (market focus) | All 7 |
| `social_signal` | Social signals (market focus) | All 7 |
| `smart_money_alpha` | Smart money alpha (market focus) | All 7 |
| `copy_trade_finder` | Copy trade finder (market focus) | All 7 |
| `defi_yield_scanner` | DeFi yield scanner (market focus) | All 7 |
| `liquidity_flow` | Liquidity flow (market focus) | All 7 |
| `gas_forecast` | Gas forecast (market focus) | EVM chains |
| `chain_health` | Chain health (market focus) | All 7 |

### Analysis (12 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `tx_decoder` | Decode and interpret transactions | All 7 |
| `wallet` | Comprehensive wallet analysis | All 7 |
| `contract_info` | Extract smart contract information | All 7 |
| `storage_reader` | Read contract storage slots | EVM chains |
| `meme_vibe_score` | Meme vibe analysis (analysis focus) | All 7 |
| `token_deep_dive` | Token deep dive (analysis focus) | All 7 |
| `token_comparison` | Token comparison (analysis focus) | All 7 |
| `forensic_valuation` | Forensic valuation (analysis focus) | All 7 |
| `portfolio_tracker` | Portfolio tracker (analysis focus) | All 7 |
| `comprehensive_audit` | Comprehensive audit (analysis focus) | All 7 |
| `investigation_report` | Investigation report (analysis focus) | All 7 |
| `risk_monitor` | Risk monitor (analysis focus) | All 7 |

### Forensics (7 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `forensics_threat_check` | Threat intelligence check for addresses | All 7 |
| `forensics_risk_report` | Detailed forensics risk report | All 7 |
| `forensics_deep_scan` | Deep forensic scan of wallet/activity | All 7 |
| `forensics_cross_chain` | Cross-chain forensic correlation | All 7 |
| `bundle_security_pack` | Bundle of security forensics tools | All 7 |
| `forensics_trace` | Trace funds through complex transaction graphs | All 7 |
| `forensics_entity` | Entity resolution from on-chain footprints | All 7 |

### Social (7 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `tw_profile` | Twitter/X profile analysis | — |
| `tw_timeline` | Twitter/X timeline analysis | — |
| `tw_search` | Twitter/X search for crypto mentions | — |
| `profile_get` | Get Rug Munch user profile | — |
| `profile_badges` | Get user badges and reputation | — |
| `social_signal` | Social signal aggregation | All 7 |
| `sentiment` | Sentiment from social channels | All 7 |

### OSINT (3 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `osint_search` | Open source intelligence search | — |
| `osint_identity_hunt` | Cross-reference identities across platforms | — |
| `osint_investigate` | Deep OSINT investigation | — |

### Launchpad (3 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `launch` | Track token launches in real-time | All 7 |
| `launch_intel` | Intelligence on upcoming launches | All 7 |
| `sniper_alert` | Snipe alerts for high-potential launches | All 7 |

### Meta (3 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `list_bundles` | List available tool bundles | — |
| `tools_discovery` | Discover all available tools | — |
| `framework_discovery` | Discover framework capabilities | — |

### News (3 Tools)

| Tool | Description | Chains |
|------|-------------|--------|
| `news_headlines` | Latest crypto news headlines | — |
| `news_twitter` | Crypto news from Twitter/X | — |
| `news_combined` | Combined news from all sources | — |

---

## x402 Payment Protocol

Rug Munch Intelligence uses the **Coinbase x402 payment protocol** for transparent, per-call API payments. No subscriptions — pay only for what you use.

### How It Works

1. Your MCP client makes a tool call
2. The request hits `https://cryptorugmunch.app/api/v1/x402-tools/{tool_name}`
3. If payment is required, the server returns a **402 Payment Required** with a payment faciliatation URL
4. The x402 client middleware handles payment automatically (via USDC on Base)
5. The request is replayed with payment proof and the result is returned

All payment handling is transparent — your MCP client never sees the 402 dance.

### Free Tier

| Method | Free Calls |
|--------|-----------|
| Fingerprint (browser/device) | 1 free call |
| Wallet signature | 3 free calls |

No API key needed. Just start using tools and the trial kicks in automatically.

### Per-Call Pricing

Each tool call costs a small amount of USDC on Base. Pricing varies by tool complexity:

- **Basic tools** (news, meta, social lookups): ~$0.001–$0.005
- **Standard tools** (whale_scan, sentiment, market): ~$0.01–$0.05
- **Premium tools** (forensics_deep_scan, comprehensive_audit): ~$0.05–$0.25

Visit [cryptorugmunch.app](https://cryptorugmunch.app) for full pricing details.

### x402 Discovery

```bash
curl https://cryptorugmunch.app/.well-known/x402
```

---

## RugCharts — The DexScreener Killer

**DexScreener killer** — live trades as they come in, TA bot analysis, beautiful charting, multichain coverage. Better product than DexScreener.

RugCharts delivers:

- **Live trade streaming** — see every trade as it happens, not delayed
- **TA bot analysis** — automated technical analysis overlays on every chart
- **Beautiful charting** — candlestick, volume, liquidity depth, all in one view
- **Multichain coverage** — Base, Solana, Ethereum, BSC, Arbitrum, Optimism, Polygon
- **Rug intelligence baked in** — every chart shows our rug pull risk score front and center

Coming soon at [rugmunch.io](https://rugmunch.io)

---

## Client Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "rug-munch": {
      "command": "uvx",
      "args": ["rug-munch-mcp"],
      "env": {
        "RUG_MUNCH_API_BASE": "https://cryptorugmunch.app/api/v1"
      }
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "rug-munch": {
      "command": "uvx",
      "args": ["rug-munch-mcp"],
      "env": {
        "RUG_MUNCH_API_BASE": "https://cryptorugmunch.app/api/v1"
      }
    }
  }
}
```

### Windsurf

```json
{
  "mcpServers": {
    "rug-munch": {
      "command": "uvx",
      "args": ["rug-munch-mcp"],
      "env": {
        "RUG_MUNCH_API_BASE": "https://cryptorugmunch.app/api/v1"
      }
    }
  }
}
```

---

## API Endpoint Reference

All tools are accessible via the public x402-gated API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/v1/x402-tools/{tool_name}` | POST | Execute any of the 97 tools |
| `GET /api/v1/x402-tools` | GET | List all available tools |
| `GET /.well-known/x402` | GET | x402 payment discovery |

**Base URL:** `https://cryptorugmunch.app`

Each tool call accepts a JSON body with at minimum a `chain` parameter:

```json
{
  "chain": "solana",
  "address": "TokenOrWalletAddress"
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RUG_MUNCH_API_BASE` | No | `https://cryptorugmunch.app/api/v1` | API base URL |
| `RUG_MUNCH_API_KEY` | No | — | API key for premium access (optional) |

> **No other environment variables are needed.** No secrets, no database strings, no internal endpoints.

---

## Installation

### From PyPI

```bash
pip install rug-munch-mcp
```

### From Source

```bash
git clone https://github.com/Rug-Munch-Media-LLC/rug-munch-mcp.git
cd rug-munch-mcp
pip install -e .
```

### Via Smithery

```bash
npx @smithery/cli install rug-munch-mcp
```

---

## Development

```bash
# Clone and setup
git clone https://github.com/Rug-Munch-Media-LLC/rug-munch-mcp.git
cd rug-munch-mcp
pip install -e ".[dev]"

# Run server locally
python -m rug_munch_mcp.server
```

---

## License

MIT License — Copyright 2026 Rug Munch Media LLC. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with 🍔 by Rug Munch Media LLC</strong><br/>
  <a href="https://cryptorugmunch.app">cryptorugmunch.app</a> · <a href="https://rugmunch.io">rugmunch.io</a> · <a href="https://github.com/Rug-Munch-Media-LLC">GitHub</a>
</p>