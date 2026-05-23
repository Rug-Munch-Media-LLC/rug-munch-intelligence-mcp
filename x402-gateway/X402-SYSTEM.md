# Rug Munch Intelligence x402 System Documentation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                              │
│  MCP Clients (Claude, Cursor)  │  Bots  │  Humans (Web UI)  │
└────────────┬──────────────────────┬──────────────┬──────────┘
             │                      │              │
             ▼                      ▼              ▼
┌────────────────────────┐  ┌──────────────┐  ┌──────────────┐
│  sol.rugmunch.io       │  │base.rugmunch │  │ rugmunch.io  │
│  (Solana Gateway)      │  │  .io (Base)  │  │  (Web App)   │
│  Cloudflare Worker     │  │  CF Worker   │  │  Vercel/CF   │
└───────────┬────────────┘  └──────┬───────┘  └──────┬───────┘
            │                      │                  │
            ▼                      ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              PAYMENT VERIFICATION (x402)                     │
│  PayAI Facilitator — USDC on Solana & Base                   │
│  Wallet Connect — Phantom, MetaMask, WalletConnect, CB       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (rugmunch.io)                      │
│  FastAPI — 80+ modules                                       │
│  /api/v1/x402-tools/* — 64 RMI security tools                │
│  /api/v1/helius/* — Whale scan, syndicate, sniper detect     │
│  /api/v1/scam-finder/* — Clone detect, fresh pairs, flips    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA PROVIDERS (28 services)                    │
│  DexScreener, Jupiter, Helius, Birdeye, CoinGecko, Nansen,   │
│  Arkham, GMGN, Moralis, PumpFun, Raydium, DeFiLlama + 16    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start — MCP Client

### Smithery
```json
{
  "mcpServers": {
    "rugmunch-solana": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "https://sol.rugmunch.io/mcp"]
    }
  }
}
```

### Glama
```json
{
  "mcpServers": {
    "rugmunch-base": {
      "command": "npx", 
      "args": ["-y", "mcp-remote@latest", "https://base.rugmunch.io/mcp"]
    }
  }
}
```

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "rugmunch": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "https://sol.rugmunch.io/mcp"]
    }
  }
}
```

## API Endpoints

### Discovery
| Endpoint | Description |
|----------|-------------|
| `/.well-known/x402` | x402 payment discovery |
| `/llms.txt` | AI agent discovery (llms.txt standard) |
| `/openai-tools` | OpenAI function calling format |
| `/anthropic-tools` | Anthropic tool format |
| `/gemini-tools` | Gemini function declarations |
| `/langchain-tools` | LangChain tool format |
| `/mcp-tools` | MCP tool catalog |

### MCP Protocol
| Method | Description |
|--------|-------------|
| `tools/list` | List all 218 tools |
| `tools/call` | Execute any tool |
| `initialize` | Protocol handshake |
| `ping` | Health check |

### REST API
| Endpoint | Description |
|----------|-------------|
| `/tools/{name}` | Execute tool via REST |
| `/health` | Worker health + tool counts |
| `/about` | Organization + tool listing |
| `/api` | API endpoint directory |
| `/pricing` | HTML pricing page |

## Payment Flow

### x402 (Bot Payment)
1. Client requests tool → receives 402 Payment Required with `PAYMENT-REQUIRED` header
2. Client sends USDC tx on Solana or Base
3. Client includes `PAYMENT-SIGNATURE` header with base64-encoded payment proof
4. Gateway verifies via PayAI facilitator
5. Tool executes, result returned

### Human Payment (Web)
1. User connects wallet (Phantom, MetaMask, WalletConnect, Coinbase Wallet)
2. Selects tool and payment method (USDC-SOL, USDC-Base, SOL, ETH, USDT)
3. Signs transaction in wallet
4. Payment verified on-chain
5. Tool executes, result displayed

### Trial Mode
Each tool has 1-5 free trial calls. No payment needed for initial testing.

## Tool Categories

### Security (22 tools)
audit, rugshield, honeypot_check, mev_protection, bridge_security, rug_pull_predictor, urlcheck, risk_monitor, nft_wash_detector, anomaly, profile_flip, fresh_pair, clone_detect, deployer_history, token_age, scam_database, mev_alert, wash_trading, bundler_detect, liquidity_migration, sniper_alert, gas_forecast

### Intelligence (18 tools)
whale, whale_scan, whale_profile, smartmoney, cluster, insider, sniper_detect, syndicate_scan, syndicate_track, wallet_graph, launch_intel, copy_trade_finder, liquidity_flow, defi_yield_scanner, alpha_digest, insider_network, listing_predictor, kol_performance

### Market (8 tools)
pulse, market_overview, chain_health, token_deep_dive, liquidity_depth, unlock_calendar, arbitrage_scan, whale_accumulation

### Analysis (6 tools)
wallet, forensics, portfolio_tracker, token_comparison, portfolio_aggregate, wallet_pnl

### Social (5 tools)
sentiment, social_signal, tw_profile, tw_timeline, tw_search, sentiment_spike

### Launch (3 tools)
launch, sniper_alert, airdrop_finder, airdrop_check

### Data Providers (154 tools across 28 services)
DexScreener, Jupiter, PumpFun, Raydium, DeFiLlama, DexPaprika, CoinCap, CoinMarketCap, CryptoPanic, CryptoCompare, Blockchair, Blockchain.com, Mempool, Solana RPC, Helius, Birdeye, CoinGecko, CryptoIZ, Blockrun, AgentFi, Moralis, GMGN, Nansen, Arkham, Dune, Solscan, QuickNode, FreeUSDC

## Department Links

- **Solana Gateway**: https://sol.rugmunch.io
- **Base Gateway**: https://base.rugmunch.io
- **MCP Catalog**: https://sol.rugmunch.io/mcp
- **Smithery**: https://smithery.ai/server/rugmunch-solana
- **Glama**: https://glama.ai/mcp/servers/rugmunch-solana
- **GitHub**: https://github.com/Rug-Munch-Media-LLC/rugmuncher-backend
- **Website**: https://rugmunch.io
- **X/Twitter**: https://x.com/cryptorugmunch

## Pricing
All tools priced $0.01 - $0.15 USDC per call. Trial mode: 1-5 free calls per tool.

## Architecture Decisions
- **Cloudflare Workers at edge** — sub-50ms latency globally
- **No backend proxy for RMI tools** — execute directly in worker for speed
- **Backend proxy for chain-specific tools** — whale_scan, syndicate, clone_detect hit backend API
- **MCP external tools via mcp-router** — 154 tools from 28 providers, fetched on demand
- **5-layer social fallback** — fxtwitter → syndication → CryptoPanic → CoinGecko → LunarCrush
- **DexScreener as primary data source** — 8 market gap tools use DexScreener directly
