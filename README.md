<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-6E40C9?logo=modelcontextprotocol&logoColor=white" alt="MCP Compatible" />
  <img src="https://img.shields.io/badge/Tools-69-00D4AA" alt="69 Tools" />
  <img src="https://img.shields.io/badge/Chains-7-F7931A" alt="7 Chains" />
  <img src="https://img.shields.io/badge/x402-Payments-FF6900" alt="x402 Payments" />
  <img src="https://img.shields.io/badge/Price-Free_Trials-22C55E" alt="Free Trials" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-Proprietary-red" alt="Proprietary" />
</p>

<h1 align="center">🛡️ Rug Munch Intelligence — MCP Server</h1>
<h3 align="center">AI-Powered Crypto Security. 69 Tools. Don't Get Rugged.</h3>

<p align="center">
  <strong>Crypto scam detection • Rug pull prevention • Wallet forensics • Market intelligence • Social sentiment</strong><br/>
  Built for AI agents (Claude, Cursor, Windsurf, ChatGPT). Accessible via <code>pip install</code> or direct HTTP.
</p>

---

## 🚀 Quick Start

```bash
pip install rug-munch-intelligence-mcp
```

Add to Claude Desktop / Cursor / Windsurf:

```json
{
  "mcpServers": {
    "rug-munch-intelligence": {
      "command": "python3",
      "args": ["-m", "rug_munch_mcp"],
      "env": { "RUG_MUNCH_API_BASE": "https://rugmunch.io/api/v1" }
    }
  }
}
```

No API key needed. Free trials on every tool.

---

## 📊 69 Tools Across 7 Chains

### Security (20 tools)
`audit` `rugshield` `honeypot_check` `urlcheck` `clone_detect` `fresh_pair` `profile_flip` `sniper_detect` `deployer_history` `token_age` `protocol_risk` `scam_database` `mev_alert` `wash_trading` `bundler_detect` `liquidity_migration` `bridge_security` `rug_pull_predictor` `anomaly` `risk_monitor`

### Intelligence (20 tools)
`smartmoney` `whale` `whale_scan` `whale_profile` `cluster` `insider` `insider_network` `syndicate_scan` `syndicate_track` `wallet_graph` `copy_trade_finder` `kol_performance` `whale_accumulation` `alpha_digest` `listing_predictor` `social_signal` `smart_money_alpha` `gas_forecast` `mev_protection` `sniper_alert`

### Market (15 tools)
`pulse` `market_price` `market_sectors` `trending_tokens` `market_overview` `chain_health` `token_deep_dive` `liquidity_depth` `unlock_calendar` `airdrop_check` `arbitrage_scan` `protocol_research` `yield_scanner` `defi_yield_scanner` `dex_activity`

### Analysis (7 tools)
`wallet` `wallet_pnl` `portfolio_aggregate` `portfolio_tracker` `token_comparison` `forensics` `tx_decoder`

### Social (6 tools)
`sentiment` `sentiment_spike` `tw_profile` `tw_timeline` `tw_search` `meme_vibe_score`

### Launchpad (3 tools)
`launch` `launch_intel` `airdrop_finder`

### Forensic Bundles (3 tools)
`forensic_valuation` `osint_identity_hunt` `investigation_report`

---

## 🔗 Direct API Access (No Install)

Call any tool directly via HTTP — all formats supported:

```bash
# OpenAI function calling
curl https://rugmunch.io/api/v1/x402-tools/openai-tools

# Anthropic Claude
curl https://rugmunch.io/api/v1/x402-tools/anthropic-tools

# Google Gemini
curl https://rugmunch.io/api/v1/x402-tools/gemini-tools

# LangChain
curl https://rugmunch.io/api/v1/x402-tools/langchain-tools

# Call any tool
curl -X POST https://rugmunch.io/api/v1/x402-tools/deployer_history \
  -H "Content-Type: application/json" \
  -d '{"address":"0x...","chain":"ethereum"}'
```

---

## 💰 Payment (x402 Protocol)

| Tier | Calls | Requirement |
|------|-------|-------------|
| Free Trial | 1-5 per tool | Device fingerprint |
| Wallet Connected | +3 per tool | MetaMask/Phantom |
| Paid | Unlimited | USDC via x402 |

**7 chains**: Solana, Base, Ethereum, BSC, Arbitrum, Optimism, Polygon  
**Refund**: Full refund if tool returns no data  
**Discovery**: `/.well-known/x402`

---

## 🏗️ Architecture

This is a thin MCP wrapper around the Rug Munch Intelligence x402 API. All 69 tools are served from our backend — this package translates MCP protocol into HTTP calls.

```
AI Agent → this MCP server → x402 API → RMI Backend (69 tools)
```

---

## 📡 Links

| Resource | URL |
|----------|-----|
| Website | https://rugmunch.io |
| Backend Repo | https://github.com/Rug-Munch-Media-LLC/rugmuncher-backend |
| x402 Gateway (Base) | https://github.com/Rug-Munch-Media-LLC/x402-gateway-base |
| x402 Gateway (Solana) | https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana |
| RugCharts | https://github.com/Rug-Munch-Media-LLC/rugcharts |
| RugMaps | https://github.com/Rug-Munch-Media-LLC/rugmaps |
| Twitter/X | https://x.com/cryptorugmunch |
| Telegram | https://t.me/cryptorugmuncher |

---

## 🔑 Keywords

`mcp-server` `crypto-security` `scam-detection` `rug-pull` `blockchain-forensics` `wallet-analysis` `smart-money` `whale-tracking` `defi-security` `token-analysis` `sentiment-analysis` `x402` `model-context-protocol` `ai-agents` `claude-tools` `web3-security` `solana` `ethereum` `base` `arbitrum` `optimism` `polygon` `bsc` `usdc-payments` `honeypot-detection` `wash-trading` `mev-protection` `portfolio-tracking` `kol-tracking` `token-launch`

---

<p align="center">
  <sub>© 2026 Rug Munch Media LLC — Proprietary. All Rights Reserved. Wyoming DAO LLC transition pending. Follow the build.</sub>
</p>