# RMI Platform — Frequently Asked Questions

## General

**What is Rug Munch Intelligence?**
A unified crypto intelligence platform with 234 tools for token security, wallet forensics, whale tracking, market data, and blockchain queries. Free tools available, paid tools via x402 micropayments.

**How many tools are free?**
98 tools are completely free — 13 caching shield tools + 85 local MCP tools. Plus every paid tool includes 1-5 free trial calls.

**What chains are supported?**
Solana, Ethereum, Base, BSC, Polygon, Arbitrum, Optimism, Avalanche, Fantom, Gnosis, TRON, Bitcoin, and 80+ EVM networks via local MCP servers.

## Pricing & Payments

**How does x402 pricing work?**
You pay per tool call in USDC. Prices range from $0.01 (basic lookups) to $0.40 (comprehensive audits). Payment happens automatically via the x402 protocol — no accounts, no subscriptions, no prepayment.

**Which chains can I pay on?**
Base, Solana, Ethereum, BSC, TRON, Bitcoin, Polygon, and Arbitrum. Base and Solana offer instant settlement.

**What if a paid tool returns no data?**
Full automatic refund within 48 hours. You're never charged for empty results.

**Do free trials reset?**
Yes — monthly or when a tool is updated. Anti-abuse fingerprinting ensures fair usage.

## Free Tools

**What can I do for free?**
- Trace wallet funding sources across 10 chains
- Get real-time token prices with multi-provider consensus
- Run security risk scans with 4 fallback layers
- Check wallet balances
- View GMGN token security analysis
- Check Ethereum gas prices
- Access CoinGecko market data
- Use all 85 local MCP tools (Solana RPC + EVM queries)
- Use Boar's 50 free blockchain tools

**Are there rate limits on free tools?**
For external API-based tools, yes — all limits are documented in the architecture. Local MCP tools and internal caching shield tools have no rate limits.

**How do I access free tools?**
Via the REST API at `/api/v1/investigate/*` or directly through the MCP endpoint at `/mcp/*`. No API key required for free tools.

## Technical

**Where is the MCP endpoint?**
`https://mcp.rugmunch.io/mcp` — supports Streamable HTTP transport (MCP 2024-11-05 protocol).

**How do I discover available tools?**
`GET https://mcp.rugmunch.io/mcp/tools` or `GET https://mcp.rugmunch.io/.well-known/mcp`

**What's the caching architecture?**
Every data call hits L1 memory cache first (sub-millisecond), then rate limiter, then provider chain with automatic fallback. No external API is ever called raw.

**How many API keys do you manage?**
15 API providers, 27 total keys, all stored in GPG-encrypted vault with zero plaintext on disk. 71 age-encrypted files for Docker runtime injection.

**What happens if a provider goes down?**
Automatic fallback to the next provider in the chain. Every data type has 3-4 fallback providers. No single-point-of-failure.

## Development

**Can I self-host the MCP servers?**
The Solana SVM MCP and EVM MCP servers are open-source and can be self-hosted. Our implementations are at GitHub.

**How do I report a bug or request a tool?**
Open an issue on GitHub or email mcp@rugmunch.io.

**Do you have an SDK?**
The REST API follows standard OpenAPI patterns. MCP clients can use any MCP SDK. We're listed on Smithery, Glama, mcp.so, and Open WebUI.
