<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-6E40C9?logo=modelcontextprotocol&logoColor=white" alt="MCP Compatible" />
  <img src="https://img.shields.io/badge/Tools-221-00D4AA" alt="210 Tools" />
  <img src="https://img.shields.io/badge/Chains-13-F7931A" alt="13 Chains" />
  <img src="https://img.shields.io/badge/x402-Payments-FF6900" alt="x402 Payments" />
  <img src="https://img.shields.io/badge/Price-Free_Trials-22C55E" alt="Free Trials" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-Proprietary-red" alt="Proprietary" />
</p>

<h1 align="center">🛡️ Rug Munch Intelligence — MCP Server</h1>
<h3 align="center">210 AI-Powered Crypto Intelligence Tools · 13 Blockchains · Don't Get Rugged.</h3>

<p align="center">
  <strong>Crypto scam detection • Rug pull prevention • Wallet forensics • Whale tracking • Market intelligence • Sentiment analysis</strong><br/>
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

## 📊 210 Tools Across 13 Blockchains

| Category | Count | Top Tools |
|----------|-------|-----------|
| 🔒 Security | 29 + 9 SENTINEL | `audit`, `rugshield`, `honeypot_check`, `sentinel_scan`, `holder_analysis`, `flash_loan_detect`, `governance_attack` |
| 🧠 Intelligence | 27 | `smartmoney`, `whale_scan`, `cluster`, `insider`, `cross_chain_whale`, `degen_score`, `wallet_label_registry` |
| 📊 Market | 15 | `pulse`, `market_overview`, `chain_health`, `funding_rate`, `options_flow`, `liquidation_heatmap`, `volatility_surface` |
| 🔬 Analysis | 14 | `wallet`, `wallet_pnl`, `portfolio_tracker`, `forensics`, `correlation_matrix`, `drawdown_analyzer`, `volume_profile` |
| 💬 Social | 11 | `sentiment`, `social_signal`, `tw_profile`, `meme_vibe_score`, `telegram_pump_detect`, `discord_alpha`, `reddit_sentiment` |
| 🚀 Launch | 7 | `launch_intel`, `airdrop_finder`, `presale_scanner`, `ido_tracker`, `fair_launch_detect` |
| 🔎 Premium | 7 | `forensic_valuation`, `osint_identity_hunt`, `deep_forensics`, `whale_network_map`, `full_wallet_dossier` |
| 💎 DeFi | 4 | `defi_yield_scanner`, `yield_aggregator`, `impermanent_loss`, `protocol_risk` |
| 🖼 NFT | 2 | `nft_wash_detector`, `nft_floor_analytics` |
| 📦 Bundles | 4 | `security_pack`, `intelligence_pack`, `all_in_one`, `forensic_pack` |
| 🔌 API | 3 | `catalog`, `mcp-proxy`, `human-execute` |
| 🔄 Variants | 80 | Per-chain overrides: Solana, Base, Ethereum, BSC, Arbitrum, Optimism, Polygon, Avalanche, Fantom, Gnosis, TRON, Bitcoin |

**Total: 210 tools · 13 chains**

---

## 🔗 Direct API Access (No Install)

```bash
# OpenAI function calling
curl https://rugmunch.io/api/v1/x402-tools/openai-tools

# Anthropic Claude
curl https://rugmunch.io/api/v1/x402-tools/anthropic-tools

# Google Gemini
curl https://rugmunch.io/api/v1/x402-tools/gemini-tools

# LangChain
curl https://rugmunch.io/api/v1/x402-tools/langchain-tools

# MCP endpoint
curl -X POST https://rugmunch.io/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## 💰 Payment (x402 Protocol)

| Tier | Calls | Requirement |
|------|-------|-------------|
| Free Trial | 1–5 per tool | Device fingerprint |
| Wallet Connected | +3 per tool | MetaMask/Phantom |
| Paid | Unlimited | USDC via x402 |

**13 chains**: Solana, Base, Ethereum, BSC, Arbitrum, Optimism, Polygon, Avalanche, Fantom, Gnosis, TRON, Bitcoin, SEPA/EUR

**8 facilitators**: Coinbase CDP, PayAI, Cloudflare x402, EIP-7702, TRON Self-Verify, Bitcoin Self-Verify, AsterPay, x402-rs

**Refund**: Full refund if tool returns no data

**Discovery**: `/.well-known/x402` · `rugmunch.io/.well-known/mcp.json`

---

## 🏗️ Architecture

This is a thin MCP wrapper around the Rug Munch Intelligence x402 API. All 210 tools are served from our backend — this package translates MCP protocol into HTTP calls.

```
AI Agent → this MCP server → x402 API → RMI Backend (210 tools)
```

---

## 📡 Links

| Resource | URL |
|----------|-----|
| Website | https://rugmunch.io |
| MCP Docs | https://rugmunch.io/docs/mcp |
| x402 Discovery | https://rugmunch.io/.well-known/x402 |
| Smithery | https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence |
  <a href="https://glama.ai/mcp/servers?q=rug+munch"><img src="https://img.shields.io/badge/Listed-Glama-7C3AED" alt="Glama"/></a>
  <a href="https://mcp.so/server/rug-munch-intelligence"><img src="https://img.shields.io/badge/Listed-mcp.so-06D6A0" alt="mcp.so"/></a>
| Backend Repo | https://github.com/Rug-Munch-Media-LLC/rugmuncher-backend |
| x402 Gateway (Base) | https://github.com/Rug-Munch-Media-LLC/x402-gateway-base |
| x402 Gateway (Solana) | https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana |
| RugCharts | https://github.com/Rug-Munch-Media-LLC/rugcharts |
| Twitter/X | https://x.com/cryptorugmunch |
| Telegram | https://t.me/cryptorugmuncher |

---

## 🔑 Keywords

`mcp-server` `crypto-security` `scam-detection` `rug-pull` `blockchain-forensics` `wallet-analysis` `smart-money` `whale-tracking` `defi-security` `token-analysis` `sentiment-analysis` `x402` `model-context-protocol` `ai-agents` `claude-tools` `web3-security` `solana` `ethereum` `base` `arbitrum` `optimism` `polygon` `bsc` `avalanche` `fantom` `gnosis` `tron` `bitcoin` `usdc-payments` `honeypot-detection` `wash-trading` `mev-protection` `portfolio-tracking` `kol-tracking` `token-launch` `mcp` `cryptocurrency` `defi` `nft` `ai`

---

<p align="center">
  <sub>© 2026 Rug Munch Media LLC — Proprietary. All Rights Reserved. Wyoming DAO LLC transition pending. Follow the build.</sub>
</p>
