<p align="center">
  <img src="https://img.shields.io/badge/MCP-Compatible-6E40C9?logo=modelcontextprotocol&logoColor=white" alt="MCP Compatible" />
  <img src="https://img.shields.io/badge/Tools-59-00D4AA" alt="59 Tools" />
  <img src="https://img.shields.io/badge/Chains-7-F7931A" alt="7 Chains" />
  <img src="https://img.shields.io/badge/x402-Payment-FF6900" alt="x402 Payment" />
  <img src="https://img.shields.io/badge/Tier-Free_Trials-22C55E" alt="Free Trials" />
</p>

<h1 align="center">Rug Munch Intelligence — MCP Server</h1>

<p align="center"><strong>AI-Powered Crypto Security. Don't Get Rugged.</strong></p>

<p align="center">
  59 tools for scam detection, rug pull prevention, and crypto intelligence across 7 chains.<br/>
  x402 micropayments. Auto-discovered from live gateway. Keeping retail investors safe.
</p>

---

## Architecture

This is a **thin MCP wrapper** around the Rug Munch Intelligence x402 API. All tools are served from our backend — this package just translates MCP protocol into HTTP calls so AI agents (Claude, Cursor, Windsurf, etc.) can use them natively.

```
AI Agent (Claude/Cursor) → this MCP server → x402 API → RMI Backend (59 tools)
```

No separate server needed. The x402 API at `rugmunch.io` IS the source of truth.

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

### Direct API Access (no install needed)

```bash
# OpenAI function calling format
curl https://rugmunch.io/api/v1/x402-tools/openai-tools

# Anthropic Claude format
curl https://rugmunch.io/api/v1/x402-tools/anthropic-tools

# Google Gemini format
curl https://rugmunch.io/api/v1/x402-tools/gemini-tools

# LangChain format
curl https://rugmunch.io/api/v1/x402-tools/langchain-tools
```

Call any tool:

```bash
curl -X POST https://rugmunch.io/api/v1/x402-tools/trending_tokens \
  -H "Content-Type: application/json" \
  -d '{"chain":"solana"}'
```

## Payment (x402)

- **Free trials** — 1-5 calls per tool (fingerprint-based)
- **Per-call** — $0.01 to $0.50 via USDC on any supported chain
- **Refund** — if a call returns no data
- **Discovery** — `/.well-known/x402` for full protocol manifest

## Supported Chains

| Chain | Payment |
|-------|---------|
| Solana, Base | PayAI facilitator |
| Ethereum, BSC, Arbitrum, Optimism, Polygon | Self-verified |

## Related Repos

- [RMI Backend](https://github.com/Rug-Munch-Media-LLC/rugmuncher-backend) — Core API
- [x402 Gateway Base](https://github.com/Rug-Munch-Media-LLC/x402-gateway-base)
- [x402 Gateway Solana](https://github.com/Rug-Munch-Media-LLC/x402-gateway-solana)
- [RugCharts](https://github.com/Rug-Munch-Media-LLC/rugcharts)

## License

Proprietary — Copyright 2026 Rug Munch Media LLC. All rights reserved.
Access via x402 API at https://rugmunch.io/api/v1
