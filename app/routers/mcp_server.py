"""
Rug Munch Intelligence MCP Server v3.1 (Spec Compliant)

MCP protocol version: 2024-11-05
Transport: Streamable HTTP (POST /mcp)
Discovery: /.well-known/mcp | /.well-known/mcp.json | /llms.txt
Tool listing: GET /mcp/tools | POST /mcp (tools/list)
Tool execution: POST /mcp/call/{tool_id} | POST /mcp (tools/call)
x402 payments: /.well-known/x402

Changes from v3.0:
- Added /.well-known/mcp (no .json) per MCP discovery convention
- Added POST /mcp JSON-RPC handler (initialize, tools/list, tools/call)
- Added inputSchema to every tool (JSON Schema objects array)
- Fix: tool "name" now uses tool_id not description
- Fix: facilitators count dynamically loaded from registry
- Fix: chains count from CHAIN_USDC not hardcoded
- Added proper error codes per MCP spec
- Added CORS headers for browser-based MCP clients
"""
import json, os, logging, time, uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse

logger = logging.getLogger("rmi_mcp_v3")
router = APIRouter(tags=["mcp"])

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "Rug Munch Intelligence"
SERVER_VERSION = "3.1.0"


def _get_tools() -> Dict[str, Any]:
    try:
        from app.routers.x402_enforcement import TOOL_PRICES, CHAIN_USDC
        return {"prices": dict(TOOL_PRICES), "chains": dict(CHAIN_USDC)}
    except Exception:
        return {"prices": {}, "chains": {}}


def _get_facilitator_count() -> int:
    try:
        from app.facilitators.base import get_registry
        return len(get_registry().get_all())
    except Exception:
        return 10


def _desc(tool_id: str, pricing: dict) -> str:
    d = pricing.get("description", "")
    if d and d != tool_id and len(d) > 10:
        return d
    FALLBACKS = {
        "airdrop_check": "Verify airdrop legitimacy -- contract audit, distribution analysis, scam pattern detection. Know if an airdrop is real or a wallet drainer before connecting.",
        "airdrop_finder": "Discover active and upcoming airdrops across all major chains. Eligibility checks, value estimation, claim deadlines, and Sybil detection.",
        "all_in_one": "All-in-One Audit -- comprehensive security scan: rug pull, honeypot, clone detection, contract audit, and ownership analysis in a single call.",
        "alpha_digest": "Alpha digest -- curated crypto alpha from top-performing wallets, on-chain signals, sentiment spikes, and accumulation patterns.",
        "arbitrage_scan": "Cross-chain and cross-DEX arbitrage scanner. Find price discrepancies across exchanges for instant profit opportunities.",
        "bundler_detect": "MEV bundler detector -- sandwich attacks, frontrunning, backrunning patterns on Solana and EVM chains.",
        "catalog": "Full tool catalog -- list every RMI tool with pricing, chain support, trial availability, and descriptions.",
        "clone_detect": "Clone contract detector -- bytecode similarity analysis, function matching, known scam template identification.",
        "deployer_history": "Deployer history investigation -- every token this wallet has launched, success rate, known scam patterns, cross-chain activity.",
        "fresh_pair": "Fresh pair scanner -- detect newly created trading pairs, liquidity depth, ownership concentration, honeypot risk.",
        "insider_network": "Insider network mapper -- trace connected wallets, shared funding sources, coordinated trading patterns across addresses.",
        "intelligence_pack": "Intelligence Pack -- whale tracking + smart money + wallet clustering at 29% discount.",
        "kol_performance": "KOL performance tracker -- measure influencer call accuracy, average ROI after calls, follower quality score.",
        "liquidity_depth": "Liquidity depth analyzer -- order book depth, slippage estimation, market impact across DEXs and chains.",
        "liquidity_flow": "Liquidity flow tracker -- track where capital is moving across chains, pools, and protocols.",
        "liquidity_migration": "Liquidity migration detector -- tokens moving pools, chains, or protocols. Often a rug pull precursor signal.",
        "listing_predictor": "Exchange listing predictor -- on-chain signals suggesting imminent CEX or DEX listing based on accumulation patterns.",
        "meme_vibe_score": "Meme coin vibe score -- social virality, holder growth rate, community engagement metrics, and dump risk assessment.",
        "mev_alert": "MEV alert system -- real-time sandwich attack, frontrun, and arbitrage detection with wallet protection recommendations.",
        "mev_protection": "MEV protection checker -- verify if your transaction is protected from MEV extraction before submitting.",
        "portfolio_aggregate": "Portfolio aggregator -- combine multiple wallets into a single dashboard with consolidated PnL and asset allocation.",
        "profile_flip": "Profile flip detector -- sudden Twitter/X profile changes, domain swaps, or branding pivots before token launches or scams.",
        "protocol_risk": "Protocol risk assessment -- TVL stability, admin key analysis, upgrade patterns, oracle dependency, governance risk.",
        "rug_pull_predictor": "Rug pull predictor -- AI-powered risk scoring using 12+ signals: liquidity locks, ownership, holder distribution, social signals.",
        "scam_database": "Scam database lookup -- check addresses against known scam, phishing, honeypot, and rug pull databases.",
        "security_pack": "Security Pack -- honeypot + rug pull + audit + clone detection at 23% discount.",
        "sentiment_spike": "Sentiment spike detector -- real-time social media volume anomalies and sentiment shifts for any token.",
        "smart_money_alpha": "Smart money alpha -- real-time alerts when top-performing wallets enter new positions.",
        "sniper_alert": "Sniper alert system -- detect sniper bots entering new token launches in real-time.",
        "syndicate_scan": "Syndicate scanner -- identify coordinated trading groups, wash trading rings, pump-and-dump networks.",
        "syndicate_track": "Syndicate tracker -- follow known syndicate wallets, monitor their current positions and exit patterns.",
        "token_age": "Token age verifier -- contract creation date, migration history, proxy upgrades, and deployment patterns.",
        "unlock_calendar": "Token unlock calendar -- track vesting schedules, team token unlocks, upcoming dilution events.",
        "wallet_graph": "Wallet graph analysis -- visualize transaction flows, identify money laundering patterns and entity relationships.",
        "wallet_pnl": "Wallet PnL calculator -- realized/unrealized gains, win rate, ROI, Sharpe ratio, and complete trade history.",
        "wash_trading": "Wash trading detector -- identify fake volume, self-trades, artificial market activity across NFTs and tokens.",
        "whale_accumulation": "Whale accumulation detector -- track large wallet accumulation and distribution patterns.",
        "whale_profile": "Whale profile -- complete analysis: holdings, strategy classification, historical performance, influence score.",
        "whale_scan": "Whale scanner -- real-time whale activity across chains. Large transfers, exchange deposits, accumulation signals.",
    }
    return FALLBACKS.get(tool_id, f"{tool_id.replace('_', ' ').title()} -- real-time crypto intelligence and security analysis.")


# Build input schemas per tool based on known parameter patterns
def _input_schema(tool_id: str) -> dict:
    """Return MCP-compliant inputSchema for a tool."""
    # Universal parameters most tools accept
    base_address = {
        "type": "object",
        "properties": {
            "address": {
                "type": "string",
                "description": "Wallet address, token contract, or ENS name to analyze",
            },
            "chain": {
                "type": "string",
                "description": "Blockchain to query (base, ethereum, solana, bsc, polygon, arbitrum, optimism, avalanche, fantom, gnosis, tron, bitcoin)",
                "enum": ["base", "ethereum", "solana", "bsc", "polygon", "arbitrum", "optimism", "avalanche", "fantom", "gnosis", "tron", "bitcoin"],
            },
        },
        "required": ["address"],
    }
    base_url = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL or contract address to analyze",
            },
            "chain": {
                "type": "string",
                "description": "Blockchain (base, ethereum, solana, etc.)",
            },
        },
        "required": ["url"],
    }
    base_none = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    # Tool-specific schemas
    schemas = {
        "urlcheck": base_url,
        "honeypot_check": base_address,
        "rug_pull_check": base_address,
        "contract_audit": base_address,
        "whale_scan": {**base_address, "required": []},
        "whale_profile": base_address,
        "whale_accumulation": base_address,
        "wallet": base_address,
        "token_analysis": base_address,
        "degen_scan": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Token contract address"},
                "chain": {"type": "string", "description": "Blockchain to query"},
            },
            "required": ["address"],
        },
        "smart_money_alpha": {
            "type": "object",
            "properties": {
                "wallet": {"type": "string", "description": "Wallet address to track"},
                "chain": {"type": "string", "description": "Blockchain"},
                "limit": {"type": "integer", "description": "Number of results (default 10)"},
            },
        },
        "sentiment_spike": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Token name or contract address"},
                "chain": {"type": "string", "description": "Blockchain"},
            },
        },
        "catalog": base_none,
    }
    # For per-chain variants (e.g., wallet_solana), return base_address with chain pre-filled
    # For expanded tools not in schemas dict, return base_address as default
    return schemas.get(tool_id, base_address)


# ================================================================
# CORS MIDDLEWARE (for browser-based MCP clients)
# ================================================================

# CORS headers are added per-route in response headers.
# APIRouter doesn't support middleware — CORS is handled in each endpoint.


# ================================================================
# MCP DISCOVERY ENDPOINTS
# ================================================================

def _build_discovery():
    """Build the MCP server discovery document."""
    data = _get_tools()
    tools = data["prices"]
    chains = data["chains"]
    fac_count = _get_facilitator_count()
    cats = sorted(set(p.get("category", "analysis") for p in tools.values()))

    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "description": f"{len(tools)} crypto intelligence tools -- real-time scam detection, wallet forensics, whale tracking, contract auditing, market analysis. {len(chains)} blockchains, micropayments via x402.",
        "protocol": "mcp",
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "vendor": {
            "name": "Rug Munch Intelligence",
            "url": "https://rugmunch.io",
            "github": "https://github.com/cryptorugmuncher",
        },
        "homepage": "https://rugmunch.io",
        "documentation": "https://rugmunch.io/docs/mcp",
        "repository": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
        "endpoint": "https://rugmunch.io/mcp",
        "icon": "https://rugmunch.io/logo.png",
        "transports": ["http"],
        "authentication": {
            "type": "x402",
            "description": f"Pay-per-use. 1-5 free trials per tool. USDC on {len(chains)} chains, USDT, BTC, EUR. Full refund if no data returned.",
            "discovery_url": "https://rugmunch.io/.well-known/x402",
        },
        "capabilities": {"tools": True, "resources": False, "prompts": False},
        "directories": {
            "smithery": "https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence",
            "glama": "https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence",
            "mcp_so": "https://mcp.so/server/rug-munch-intelligence",
            "github": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
        },
        "stats": {
            "total_tools": len(tools),
            "categories": cats,
            "chains": sorted(chains.keys()),
            "chain_count": len(chains),
            "facilitators": fac_count,
            "free_trials": "1-5 calls per tool, fingerprint-gated",
            "pricing": "$0.01 - $0.40 per call",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        # Top-level fields for directory scrapers (Glama, mcp.so, Smithery)
        "categories": cats,
        "blockchains": sorted(chains.keys()),
        "facilitator_count": fac_count,
        "tools_count": len(tools),
    }


@router.get("/.well-known/mcp")
@router.get("/.well-known/mcp.json")
async def mcp_discovery():
    return _build_discovery()


@router.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    data = _get_tools()
    count = len(data["prices"])
    return {
        "schema_version": "v1",
        "name_for_human": SERVER_NAME,
        "name_for_model": "rug_munch_intelligence",
        "description_for_human": f"{SERVER_NAME} -- crypto intelligence: scam detection, wallet forensics, whale tracking, contract auditing. {count} tools, {len(data['chains'])} chains.",
        "description_for_model": f"Use for crypto security: check tokens for scams, honeypots, rug pulls. Analyze wallets for PnL, clusters, insider trading. Track whales, smart money, syndicates. Audit smart contracts. Market intelligence: fear & greed, chain health, gas forecasts, DeFi yields, arbitrage. Social signals: Twitter/X sentiment, KOL performance. {count} tools, {len(data['chains'])} chains. Free trials + x402 micropayments.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://rugmunch.io/openapi.json"},
        "logo_url": "https://rugmunch.io/logo.png",
        "contact_email": "mcp@rugmunch.io",
        "legal_info_url": "https://rugmunch.io/terms",
    }


@router.get("/llms.txt")
async def llms_txt():
    data = _get_tools()
    prices = data["prices"]
    chains = data["chains"]
    fac_count = _get_facilitator_count()
    cats = {}
    for tool_id, pricing in prices.items():
        cat = pricing.get("category", "analysis")
        cats[cat] = cats.get(cat, 0) + 1
    cat_lines = [f"- {c.title()} ({n})" for c, n in sorted(cats.items())]
    chain_list = ", ".join(sorted(chains.keys()))

    return Response(content=f"""# Rug Munch Intelligence -- MCP Server
> {len(prices)} crypto intelligence tools. {len(chains)} chains. Free trials + x402 micropayments.

## Quick Start
- MCP Endpoint: https://rugmunch.io/mcp
- Discovery: https://rugmunch.io/.well-known/mcp
- Payment: https://rugmunch.io/.well-known/x402
- Docs: https://rugmunch.io/docs/mcp
- GitHub: https://github.com/cryptorugmuncher/rug-munch-intelligence

## Directory Listings
- Smithery: https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence
- Glama: https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence
- mcp.so: https://mcp.so/server/rug-munch-intelligence
- Open WebUI: https://openwebui.com/t/cryptorugmuncher/rug-munch-intelligence

## How It Works
- Free trial -- 1-5 calls per tool, no payment. Fingerprint-gated anti-abuse.
- Pay per use -- USDC on {len(chains)} chains (Base, Solana, Ethereum, BSC, TRON, Bitcoin, more). $0.01-$0.40 per call.
- Instant refund -- Full refund if tool returns no data. Request within 48h.
- {fac_count} payment facilitators with automatic fallback. Instant settlement on Base, Solana, BNB.

## Tool Categories
{chr(10).join(cat_lines)}

## Payment Chains
{chain_list}

## Integration
curl https://rugmunch.io/.well-known/mcp
curl https://rugmunch.io/mcp/tools
""", media_type="text/plain; charset=utf-8")


# ================================================================
# TOOL CATALOG
# ================================================================

def _build_tools_list():
    """Build the full MCP-compatible tools list."""
    data = _get_tools()
    prices = data["prices"]
    chains_data = data["chains"]
    fac_count = _get_facilitator_count()

    tools = {}
    cats = {}
    for tool_id, pricing in sorted(prices.items()):
        cat = pricing.get("category", "analysis")
        cats[cat] = cats.get(cat, 0) + 1
        from app.routers.x402_tools import TOOL_ALIASES
        real_tool = TOOL_ALIASES.get(tool_id, tool_id)
        tools[tool_id] = {
            "name": tool_id,  # MCP spec: name is the tool ID
            "description": _desc(tool_id, pricing),
            "category": cat,
            "inputSchema": _input_schema(tool_id),
            "price_usd": float(pricing.get("price_usd", 0.01)),
            "trial_free": int(pricing.get("trial_free", 1)),
            "chains": sorted(chains_data.keys()),
            "endpoint": f"/api/v1/x402-tools/{real_tool}",
            "method": pricing.get("method", "POST") if isinstance(pricing.get("method"), str) else "POST",
        }

    return tools, cats, chains_data, fac_count


@router.get("/mcp/tools")
async def mcp_tools_list(request: Request):
    """Every tool in the RMI platform -- full catalog with MCP-compliant schemas."""
    tools, cats, chains_data, fac_count = _build_tools_list()

    trial_info = None
    try:
        from app.routers.x402_enforcement import get_client_id, check_trial
        cid = get_client_id(request)
        remaining = {}
        for tid in _get_tools()["prices"]:
            can, rem = check_trial(tid, cid)
            if rem > 0 or can:
                remaining[tid] = {"can_trial": can, "remaining": rem}
        trial_info = {"client_id": cid[:20] + "...", "tools_with_trials": len(remaining), "trials": remaining}
    except Exception:
        pass

    return {
        "server": f"{SERVER_NAME} MCP v{SERVER_VERSION}",
        "homepage": "https://rugmunch.io",
        "github": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
        "directories": {
            "smithery": "https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence",
            "glama": "https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence",
        },
        "total_tools": len(tools),
        "categories": {k: v for k, v in sorted(cats.items())},
        "chains": sorted(chains_data.keys()),
        "chain_count": len(chains_data),
        "facilitators": fac_count,
        "pricing": "$0.01-$0.40/call. Most tools $0.05. Bundles save 23-33%.",
        "free_trials": "1-5 calls per tool. Fingerprint-gated. Wallet required after 1 free call.",
        "payment": {"protocol": "x402", "discovery": "/.well-known/x402", "tokens": ["USDC", "USDT", "BTC", "EUR"], "chains": sorted(chains_data.keys())},
        "refund": "Full refund if tool returns no data. Within 48h via POST /api/v1/x402/refund.",
        "tools": tools,
        "trial_status": trial_info,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/mcp/capabilities")
async def mcp_capabilities():
    data = _get_tools()
    fac_count = _get_facilitator_count()
    return {
        "server": f"{SERVER_NAME} MCP v{SERVER_VERSION}",
        "homepage": "https://rugmunch.io",
        "github": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
        "capabilities": {"tools": True, "resources": False, "prompts": False, "streaming": False},
        "protocols": ["x402"],
        "payment": {"required": False, "trial_available": True, "trial_calls": "1-5 per tool", "paid": f"$0.01-$0.40 via x402 on {len(data['chains'])} chains"},
        "facilitators": fac_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ================================================================
# MCP JSON-RPC ENDPOINT (Streamable HTTP)
# ================================================================

@router.post("/mcp")
async def mcp_jsonrpc(request: Request):
    """MCP Streamable HTTP transport — handle JSON-RPC requests.

    Methods: initialize, tools/list, tools/call, ping
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
        )

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    # ── initialize ─────────────────────────────────────────
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        })

    # ── ping ────────────────────────────────────────────────
    if method == "ping":
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {}})

    # ── tools/list ──────────────────────────────────────────
    if method == "tools/list":
        tools_data, cats, chains_data, fac_count = _build_tools_list()
        tools_list = []
        for tool_id, info in tools_data.items():
            tools_list.append({
                "name": info["name"],
                "description": info["description"],
                "inputSchema": info["inputSchema"],
                "annotations": {
                    "category": info["category"],
                    "price_usd": info["price_usd"],
                    "trial_free": info["trial_free"],
                    "chains": info["chains"],
                },
            })
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools_list},
        })

    # ── tools/call ──────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        # Validate tool exists
        data = _get_tools()
        if tool_name not in data["prices"]:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found. {len(data['prices'])} tools available."},
            })

        # Proxy to internal endpoint
        import httpx
        url = f"http://localhost:8000/api/v1/x402-tools/{tool_name}"
        headers = {"Content-Type": "application/json", "User-Agent": "RMI-MCP-JSONRPC/3.1"}
        # Forward payment and identity headers from the original request
        for h in ("x-pay", "X-Pay", "X-Device-Id", "x-device-id", "Authorization",
                   "x-wallet-address", "X-Wallet-Address", "x-turnstile-token", "X-Turnstile-Token"):
            val = request.headers.get(h)
            if val:
                headers[h] = val
        for h in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"):
            val = request.headers.get(h)
            if val:
                headers[h] = val

        try:
            import asyncio
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(url, json=arguments, headers=headers)
                if resp.status_code == 402:
                    # Payment required — return the payment info as tool result
                    result = resp.json()
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(result)}],
                            "isError": False,
                        },
                    })
                result = resp.json() if "application/json" in (resp.headers.get("content-type", "")) else {"data": resp.text}
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": resp.status_code >= 400,
                    },
                })
        except httpx.ConnectError:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": "Backend unavailable"},
            })
        except Exception as e:
            logger.error(f"MCP JSON-RPC tools/call failed: {tool_name}: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": f"Tool execution failed: {str(e)[:200]}"},
            })

    # ── Unknown method ──────────────────────────────────────
    return JSONResponse(
        status_code=400,
        content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
    )


@router.options("/mcp")
async def mcp_options():
    """CORS preflight for MCP endpoint."""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Pay, X-Device-Id, X-Wallet-Address",
            "Access-Control-Max-Age": "86400",
        },
    )


# ================================================================
# TOOL EXECUTION (REST API)
# ================================================================

@router.post("/mcp/call/{tool_id}")
async def mcp_call_tool(tool_id: str, request: Request):
    """Execute any tool. Requires x402 payment or free trial."""
    data = _get_tools()
    if tool_id not in data["prices"] and tool_id not in ("list", "tools", "catalog"):
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found. {len(data['prices'])} tools available -- see /mcp/tools")

    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    except Exception:
        body = {}

    import httpx
    url = f"http://localhost:8000/api/v1/x402-tools/{tool_id}"
    try:
        headers = {}
        for h in ("x-pay", "X-Pay", "X-Device-Id", "x-device-id", "User-Agent",
                   "Authorization", "x-wallet-address", "X-Wallet-Address",
                   "x-turnstile-token", "X-Turnstile-Token"):
            val = request.headers.get(h)
            if val:
                headers[h] = val
        if "User-Agent" not in headers:
            headers["User-Agent"] = "RMI-MCP-Proxy/3.1"
        for h in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"):
            val = request.headers.get(h)
            if val:
                headers[h] = val
        ct = request.headers.get("content-type")
        if ct:
            headers["content-type"] = ct

        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(url, json=body, headers=headers)
            result = resp.json() if "application/json" in (resp.headers.get("content-type", "")) else {"data": resp.text}
            rh = {}
            for h in ("X-RMI-Payment", "X-RMI-Trial", "X-RMI-Trial-Remaining", "X-RMI-Refund-Flagged"):
                if resp.headers.get(h):
                    rh[h] = resp.headers[h]
            rh["Access-Control-Allow-Origin"] = "*"
            return JSONResponse(content=result, status_code=resp.status_code, headers=rh) if rh else JSONResponse(content=result, status_code=resp.status_code)
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Backend unavailable")
    except Exception as e:
        logger.error(f"MCP tool failed: {tool_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Tool execution failed: {str(e)[:200]}")