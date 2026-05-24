     1|"""
     2|Rug Munch Intelligence MCP Server v3.0
     3|
     4|225 tools. 13 chains. 10 payment facilitators.
     5|Crypto security, wallet intelligence, market analysis, forensics.
     6|Free trials + x402 micropayments. Fingerprint-gated anti-abuse.
     7|
     8|Discovery:  /.well-known/mcp.json | /llms.txt | /mcp/tools | /mcp/call/{id}
     9|Directories: Smithery | Glama | mcp.so | Open WebUI | GitHub
    10|"""
    11|import json, os, logging, time
    12|from datetime import datetime, timezone
    13|from typing import Dict, Any
    14|from fastapi import APIRouter, Request, HTTPException
    15|from fastapi.responses import JSONResponse, Response
    16|
    17|logger = logging.getLogger("rmi_mcp_v3")
    18|router = APIRouter(tags=["mcp"])
    19|
    20|def _get_tools() -> Dict[str, Any]:
    21|    try:
    22|        from app.routers.x402_enforcement import TOOL_PRICES, CHAIN_USDC
    23|        return {"prices": dict(TOOL_PRICES), "chains": dict(CHAIN_USDC)}
    24|    except Exception:
    25|        return {"prices": {}, "chains": {}}
    26|
    27|def _desc(tool_id: str, pricing: dict) -> str:
    28|    d = pricing.get("description", "")
    29|    if d and d != tool_id and len(d) > 10:
    30|        return d
    31|    fallbacks = {
    32|        "airdrop_check": "Verify airdrop legitimacy -- contract audit, distribution analysis, scam pattern detection. Know if an airdrop is real or a wallet drainer before connecting.",
    33|        "airdrop_finder": "Discover active and upcoming airdrops across all major chains. Eligibility checks, value estimation, claim deadlines, and Sybil detection.",
    34|        "all_in_one": "All-in-One Audit -- comprehensive security scan: rug pull, honeypot, clone detection, contract audit, and ownership analysis in a single call.",
    35|        "alpha_digest": "Alpha digest -- curated crypto alpha from top-performing wallets, on-chain signals, sentiment spikes, and accumulation patterns.",
    36|        "arbitrage_scan": "Cross-chain and cross-DEX arbitrage scanner. Find price discrepancies across exchanges for instant profit opportunities.",
    37|        "bundler_detect": "MEV bundler detector -- sandwich attacks, frontrunning, backrunning patterns on Solana and EVM chains.",
    38|        "catalog": "Full tool catalog -- list every RMI tool with pricing, chain support, trial availability, and descriptions.",
    39|        "clone_detect": "Clone contract detector -- bytecode similarity analysis, function matching, known scam template identification. Catches copycat scams before they rug.",
    40|        "deployer_history": "Deployer history investigation -- every token this wallet has launched, success rate, known scam patterns, cross-chain activity.",
    41|        "fresh_pair": "Fresh pair scanner -- detect newly created trading pairs, liquidity depth, ownership concentration, honeypot risk.",
    42|        "insider_network": "Insider network mapper -- trace connected wallets, shared funding sources, coordinated trading patterns across addresses.",
    43|        "intelligence_pack": "Intelligence Pack -- whale tracking + smart money + wallet clustering at 29% discount. Three tools, one price.",
    44|        "kol_performance": "KOL performance tracker -- measure influencer call accuracy, average ROI after calls, follower quality score.",
    45|        "liquidity_depth": "Liquidity depth analyzer -- order book depth, slippage estimation, market impact across DEXs and chains.",
    46|        "liquidity_flow": "Liquidity flow tracker -- track where capital is moving across chains, pools, and protocols. Front-run liquidity migrations.",
    47|        "liquidity_migration": "Liquidity migration detector -- tokens moving pools, chains, or protocols. Often a rug pull precursor signal.",
    48|        "listing_predictor": "Exchange listing predictor -- on-chain signals suggesting imminent CEX or DEX listing based on accumulation patterns.",
    49|        "meme_vibe_score": "Meme coin vibe score -- social virality, holder growth rate, community engagement metrics, and dump risk assessment.",
    50|        "mev_alert": "MEV alert system -- real-time sandwich attack, frontrun, and arbitrage detection with wallet protection recommendations.",
    51|        "mev_protection": "MEV protection checker -- verify if your transaction is protected from MEV extraction before submitting.",
    52|        "portfolio_aggregate": "Portfolio aggregator -- combine multiple wallets into a single dashboard with consolidated PnL and asset allocation.",
    53|        "profile_flip": "Profile flip detector -- sudden Twitter/X profile changes, domain swaps, or branding pivots before token launches or scams.",
    54|        "protocol_risk": "Protocol risk assessment -- TVL stability, admin key analysis, upgrade patterns, oracle dependency, governance risk.",
    55|        "rug_pull_predictor": "Rug pull predictor -- AI-powered risk scoring using 12+ signals: liquidity locks, ownership, holder distribution, social signals.",
    56|        "scam_database": "Scam database lookup -- check addresses against known scam, phishing, honeypot, and rug pull databases.",
    57|        "security_pack": "Security Pack -- honeypot + rug pull + audit + clone detection at 23% discount. Four tools, one price.",
    58|        "sentiment_spike": "Sentiment spike detector -- real-time social media volume anomalies and sentiment shifts for any token.",
    59|        "smart_money_alpha": "Smart money alpha -- real-time alerts when top-performing wallets enter new positions. Copy the best traders.",
    60|        "sniper_alert": "Sniper alert system -- detect sniper bots entering new token launches in real-time. Get in before or after the snipers.",
    61|        "syndicate_scan": "Syndicate scanner -- identify coordinated trading groups, wash trading rings, pump-and-dump networks.",
    62|        "syndicate_track": "Syndicate tracker -- follow known syndicate wallets, monitor their current positions and exit patterns.",
    63|        "token_age": "Token age verifier -- contract creation date, migration history, proxy upgrades, and deployment patterns.",
    64|        "unlock_calendar": "Token unlock calendar -- track vesting schedules, team token unlocks, upcoming dilution events that move prices.",
    65|        "wallet_graph": "Wallet graph analysis -- visualize transaction flows, identify money laundering patterns and entity relationships.",
    66|        "wallet_pnl": "Wallet PnL calculator -- realized/unrealized gains, win rate, ROI, Sharpe ratio, and complete trade history.",
    67|        "wash_trading": "Wash trading detector -- identify fake volume, self-trades, artificial market activity across NFTs and tokens.",
    68|        "whale_accumulation": "Whale accumulation detector -- track large wallet accumulation and distribution patterns. Know what whales are buying.",
    69|        "whale_profile": "Whale profile -- complete analysis: holdings, strategy classification, historical performance, influence score.",
    70|        "whale_scan": "Whale scanner -- real-time whale activity across chains. Large transfers, exchange deposits, accumulation signals.",
    71|    }
    72|    return fallbacks.get(tool_id, f"{tool_id.replace('_', ' ').title()} -- real-time crypto intelligence and security analysis.")
    73|
    74|
    75|# ================================================================
    76|# DISCOVERY
    77|# ================================================================
    78|
    79|@router.get("/.well-known/mcp.json")
    80|async def mcp_discovery():
    81|    data = _get_tools()
    82|    tools = data["prices"]
    83|    chains = data["chains"]
    84|    cats = sorted(set(p.get("category", "analysis") for p in tools.values()))
    85|
    86|    return {
    87|        "name": "Rug Munch Intelligence",
    88|        "version": "3.0.0",
    89|        "description": "225 crypto intelligence tools -- real-time scam detection, wallet forensics, whale tracking, contract auditing, market analysis. 13 blockchains, 10 payment facilitators, free trials + micropayments.",
    90|        "protocol": "mcp",
    91|        "protocol_version": "2024-11-05",
    92|        "vendor": {"name": "Rug Munch Intelligence", "url": "https://rugmunch.io", "github": "https://github.com/cryptorugmuncher"},
    93|        "homepage": "https://rugmunch.io",
    94|        "documentation": "https://rugmunch.io/docs/mcp",
    95|        "repository": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
    96|        "endpoint": "https://rugmunch.io/mcp",
    97|        "icon": "https://rugmunch.io/logo.png",
    98|        "transports": ["http"],
    99|        "authentication": {
   100|            "type": "x402",
   101|            "description": "Pay-per-use. 1-5 free trials per tool. USDC on 13 chains, USDT, BTC, EUR. Full refund if no data returned.",
   102|            "discovery_url": "https://rugmunch.io/.well-known/x402",
   103|        },
   104|        "capabilities": {"tools": True, "resources": False, "prompts": False},
   105|        "directories": {
   106|            "smithery": "https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence",
   107|            "glama": "https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence",
   108|            "mcp_so": "https://mcp.so/server/rug-munch-intelligence",
   109|            "github": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
   110|        },
   111|        "stats": {
   112|            "total_tools": len(tools) + 154,
   113|            "core_tools": len(tools),
   114|            "categories": cats,
   115|            "chains": sorted(chains.keys()),
   116|            "chain_count": len(chains),
   117|            "facilitators": 10,
   118|            "free_trials": "1-5 calls per tool, fingerprint-gated",
   119|            "pricing": "$0.01 - $0.40 per call",
   120|            "updated_at": datetime.now(timezone.utc).isoformat(),
   121|        },
   122|    }
   123|
   124|
   125|@router.get("/.well-known/ai-plugin.json")
   126|async def ai_plugin_manifest():
   127|    return {
   128|        "schema_version": "v1",
   129|        "name_for_human": "Rug Munch Intelligence",
   130|        "name_for_model": "rug_munch_intelligence",
   131|        "description_for_human": "Crypto intelligence -- scam detection, wallet forensics, whale tracking, contract auditing. 225 tools, 13 chains.",
   132|        "description_for_model": "Use for crypto security: check tokens for scams, honeypots, rug pulls. Analyze wallets for PnL, clusters, insider trading. Track whales, smart money, syndicates. Audit smart contracts. Market intelligence: fear & greed, chain health, gas forecasts, DeFi yields, arbitrage. Social signals: Twitter/X sentiment, KOL performance. 13 chains. Free trials + x402 micropayments.",
   133|        "auth": {"type": "none"},
   134|        "api": {"type": "openapi", "url": "https://rugmunch.io/openapi.json"},
   135|        "logo_url": "https://rugmunch.io/logo.png",
   136|        "contact_email": "mcp@rugmunch.io",
   137|        "legal_info_url": "https://rugmunch.io/terms",
   138|    }
   139|
   140|
   141|@router.get("/llms.txt")
   142|async def llms_txt():
   143|    return Response(content="""# Rug Munch Intelligence -- MCP Server
   144|> 225 crypto intelligence tools. 13 chains. 10 payment facilitators. Free trials + micropayments.
   145|
   146|## Quick Start
   147|- MCP Endpoint: https://rugmunch.io/mcp
   148|- Discovery: https://rugmunch.io/.well-known/mcp.json
   149|- Payment: https://rugmunch.io/.well-known/x402
   150|- Docs: https://rugmunch.io/docs/mcp
   151|- GitHub: https://github.com/cryptorugmuncher/rug-munch-intelligence
   152|
   153|## Directory Listings
   154|- Smithery: https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence
   155|- Glama: https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence
   156|- mcp.so: https://mcp.so/server/rug-munch-intelligence
   157|- Open WebUI: https://openwebui.com/t/cryptorugmuncher/rug-munch-intelligence
   158|
   159|## How It Works
   160|- Free trial -- 1-5 calls per tool, no payment. Fingerprint-gated anti-abuse.
   161|- Pay per use -- USDC on any of 13 chains. $0.01-$0.40 per call. Auto-routes to best facilitator.
   162|- Instant refund -- Full refund if tool returns no data. Request within 48h.
   163|
   164|## Tool Categories
   165|- Security (20): scam detection, honeypot checker, rug pull predictor, contract audit, clone detection, MEV protection, wash trading detection
   166|- Intelligence (18): whale tracking, smart money, wallet clustering, insider detection, sniper scan, syndicate analysis, deployer history
   167|- Market (9): market pulse, chain health, gas forecast, DeFi yields, arbitrage scan, liquidity depth, token unlock calendar
   168|- Analysis (8): wallet forensics, PnL tracking, portfolio aggregation, token deep dive, forensic valuation
   169|- Social (6): sentiment analysis, Twitter/X signals, KOL performance, social signal detection
   170|- Launchpad (3): new token discovery, launch intelligence, sniper alerts
   171|- Premium (3): OSINT identity hunt, investigation report, forensic pack
   172|- Bundles (4): security pack, intelligence pack, all-in-one audit, forensic pack
   173|
   174|## Payment Chains
   175|Base, Solana, Ethereum, BSC, Arbitrum, Optimism, Polygon, Avalanche, Fantom, Gnosis, TRON, Bitcoin, SEPA/EUR
   176|
   177|## Integration
   178|curl https://rugmunch.io/.well-known/mcp.json
   179|curl https://rugmunch.io/mcp/tools
   180|""", media_type="text/plain; charset=utf-8")
   181|
   182|
   183|# ================================================================
   184|# TOOL CATALOG
   185|# ================================================================
   186|
   187|@router.get("/mcp/tools")
   188|async def mcp_tools_list(request: Request):
   189|    """Every tool in the RMI platform -- full catalog with descriptions,
   190|    pricing, chain support, and trial availability."""
   191|    data = _get_tools()
   192|    prices = data["prices"]
   193|    chains_data = data["chains"]
   194|
   195|    tools = {}
   196|    cats = {}
   197|    for tool_id, pricing in sorted(prices.items()):
   198|        cat = pricing.get("category", "analysis")
   199|        cats[cat] = cats.get(cat, 0) + 1
   200|        tools[tool_id] = {
   201|            "name": pricing.get("description", tool_id.replace("_", " ").title()),
   202|            "description": _desc(tool_id, pricing),
   203|            "category": cat,
   204|            "price_usd": float(pricing.get("price_usd", 0.01)),
   205|            "trial_free": int(pricing.get("trial_free", 1)),
   206|            "chains": sorted(chains_data.keys()),
   207|            "endpoint": f"/api/v1/x402-tools/{tool_id}",
   208|            "method": pricing.get("method", "POST") if isinstance(pricing.get("method"), str) else "POST",
   209|        }
   210|
   211|    trial_info = None
   212|    try:
   213|        from app.routers.x402_enforcement import get_client_id, check_trial
   214|        cid = get_client_id(request)
   215|        remaining = {}
   216|        for tid in prices:
   217|            can, rem = check_trial(tid, cid)
   218|            if rem > 0 or can:
   219|                remaining[tid] = {"can_trial": can, "remaining": rem}
   220|        trial_info = {"client_id": cid[:20] + "...", "tools_with_trials": len(remaining), "trials": remaining}
   221|    except Exception:
   222|        pass
   223|
   224|    return {
   225|        "server": "Rug Munch Intelligence MCP v3.0",
   226|        "homepage": "https://rugmunch.io",
   227|        "github": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
   228|        "directories": {
   229|            "smithery": "https://smithery.ai/server/@cryptorugmuncher/rug-munch-intelligence",
   230|            "glama": "https://glama.ai/mcp/servers/@cryptorugmuncher/rug-munch-intelligence",
   231|        },
   232|        "total_tools": len(tools),
   233|        "categories": {k: v for k, v in sorted(cats.items())},
   234|        "chains": sorted(chains_data.keys()),
   235|        "chain_count": len(chains_data),
   236|        "facilitators": 10,
   237|        "pricing": "$0.01-$0.40/call. Most tools $0.05. Bundles save 23-33%.",
   238|        "free_trials": "1-5 calls per tool. Fingerprint-gated. Wallet required after 1 free call.",
   239|        "payment": {"protocol": "x402", "discovery": "/.well-known/x402", "tokens": ["USDC", "USDT", "BTC", "EUR"], "chains": sorted(chains_data.keys())},
   240|        "refund": "Full refund if tool returns no data. Within 48h via POST /api/v1/x402/refund.",
   241|        "tools": tools,
   242|        "trial_status": trial_info,
   243|        "updated_at": datetime.now(timezone.utc).isoformat(),
   244|    }
   245|
   246|
   247|@router.get("/mcp/capabilities")
   248|async def mcp_capabilities():
   249|    return {
   250|        "server": "Rug Munch Intelligence MCP v3.0",
   251|        "homepage": "https://rugmunch.io",
   252|        "github": "https://github.com/cryptorugmuncher/rug-munch-intelligence",
   253|        "capabilities": {"tools": True, "resources": False, "prompts": False, "streaming": False},
   254|        "protocols": ["x402"],
   255|        "payment": {"required": False, "trial_available": True, "trial_calls": "1-5 per tool", "paid": "$0.01-$0.40 via x402"},
   256|        "updated_at": datetime.now(timezone.utc).isoformat(),
   257|    }
   258|
   259|
   260|# ================================================================
   261|# TOOL EXECUTION
   262|# ================================================================
   263|
   264|@router.post("/mcp/call/{tool_id}")
   265|async def mcp_call_tool(tool_id: str, request: Request):
   266|    """Execute any tool. Requires x402 payment or free trial."""
   267|    data = _get_tools()
   268|    if tool_id not in data["prices"] and tool_id not in ("list", "tools", "catalog"):
   269|        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found. {len(data['prices'])} tools available -- see /mcp/tools")
   270|
   271|    try:
   272|        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
   273|    except Exception:
   274|        body = {}
   275|
   276|    import httpx
   277|    url = f"http://localhost:8000/api/v1/x402-tools/{tool_id}"
   278|    try:
   279|        headers = {}
   280|        for h in ("x-pay", "X-Pay", "X-Device-Id"):
   281|            if request.headers.get(h):
   282|                headers[h] = request.headers[h]
   283|        async with httpx.AsyncClient(timeout=45) as client:
   284|            resp = await client.post(url, json=body, headers=headers)
   285|            result = resp.json() if "application/json" in (resp.headers.get("content-type", "")) else {"data": resp.text}
   286|            rh = {}
   287|            for h in ("X-RMI-Payment", "X-RMI-Trial", "X-RMI-Trial-Remaining", "X-RMI-Refund-Flagged"):
   288|                if resp.headers.get(h):
   289|                    rh[h] = resp.headers[h]
   290|            return JSONResponse(content=result, headers=rh) if rh else result
   291|    except httpx.ConnectError:
   292|        raise HTTPException(status_code=502, detail="Backend unavailable")
   293|    except Exception as e:
   294|        logger.error(f"MCP tool failed: {tool_id}: {e}")
   295|        raise HTTPException(status_code=502, detail=f"Tool execution failed: {str(e)[:200]}")
   296|