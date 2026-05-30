"""
Unified Token Scanner — RugMunch Intelligence
==============================================
Now powered by SENTINEL (21-module pipeline) + DexScreener/GoPlus market data.

FREE tier:   SENTINEL Tier 1 (12 core modules) + DexScreener + GoPlus
PRO tier:    SENTINEL Tier 1+2 (17 modules) + wallet intelligence  
ELITE tier:  SENTINEL Tier 1+2+3+4 (all 21+ modules) + deep analysis
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    token_address: str
    chain: str
    symbol: str = ""
    name: str = ""
    scanned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # FREE tier
    free: Dict[str, Any] = field(default_factory=dict)
    # PRO tier
    pro: Dict[str, Any] = field(default_factory=dict)
    # ELITE tier
    elite: Dict[str, Any] = field(default_factory=dict)
    
    safety_score: int = 50  # 0-100, higher = safer (starts at 50 = unknown)
    risk_flags: List[str] = field(default_factory=list)
    tier_required: str = "free"
    confidence: int = 0  # 0-100, how much data backs this score


CHAIN_IDS = {
    "solana": "solana",
    "ethereum": "1", "base": "8453", "bsc": "56",
    "arbitrum": "42161", "polygon": "137", "avalanche": "43114",
    "optimism": "10", "fantom": "250", "linea": "59144",
    "zksync": "324", "scroll": "534352", "mantle": "5000",
}

SOLANA_RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.syndica.io/access-token/free",
]


# ═══════════════════════════════════════════
# MARKET DATA (DexScreener + GoPlus + Solana RPC)
# ═══════════════════════════════════════════

async def _solana_get_mint_info(token_address: str) -> Dict[str, Any]:
    result = {"mint_authority": "unknown", "freeze_authority": "unknown", "decimals": None, "supply": None}
    for rpc_url in SOLANA_RPC_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(rpc_url, json={
                    "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
                    "params": [token_address, {"encoding": "jsonParsed"}],
                })
                if resp.status_code == 200:
                    data = resp.json()
                    val = (data.get("result") or {}).get("value")
                    if val:
                        parsed = (val.get("data") or {}).get("parsed", {})
                        if parsed.get("type") == "mint":
                            info = parsed.get("info", {})
                            result["mint_authority"] = info.get("mintAuthority", "unknown")
                            result["freeze_authority"] = info.get("freezeAuthority", "unknown")
                            result["decimals"] = info.get("decimals")
                            result["supply"] = info.get("supply")
                            return result
        except Exception:
            continue
    return result


async def _dexscreener_lookup(token_address: str, chain: str, client: httpx.AsyncClient) -> Optional[list]:
    try:
        resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}")
        if resp.status_code == 200:
            pairs = resp.json().get("pairs", []) or []
            if pairs:
                return pairs
    except Exception:
        pass
    try:
        resp = await client.get("https://api.dexscreener.com/latest/dex/search", params={"q": token_address})
        if resp.status_code == 200:
            pairs = resp.json().get("pairs", []) or []
            matching = [p for p in pairs
                if p.get("baseToken", {}).get("address", "").lower() == token_address.lower()
                or p.get("quoteToken", {}).get("address", "").lower() == token_address.lower()]
            if matching:
                return matching
    except Exception:
        pass
    return None


async def fetch_market_data(token_address: str, chain: str) -> Dict[str, Any]:
    """Fetch DexScreener + GoPlus + Solana RPC market data."""
    result = {
        "symbol": "", "name": "", "liquidity_usd": 0, "volume_24h": 0,
        "price_usd": 0, "age_hours": None, "created_at": None, "fdv": 0,
        "holders": None, "honeypot_risk": "unknown", "buy_tax": 0, "sell_tax": 0,
        "mint_authority": "unknown", "freeze_authority": "unknown",
        "lp_burned": "unknown", "dex": "", "pair_address": "",
        "price_change_5m": None, "price_change_1h": None,
        "price_change_6h": None, "price_change_24h": None,
        "data_sources": [],
    }

    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "RMI-TokenScanner/3.0"}) as client:
        pairs = await _dexscreener_lookup(token_address, chain, client)
        if pairs:
            pair = pairs[0]
            result["dex"] = pair.get("dexId", "")
            result["pair_address"] = pair.get("pairAddress", "")
            result["liquidity_usd"] = float((pair.get("liquidity") or {}).get("usd", 0) or 0)
            result["volume_24h"] = float((pair.get("volume") or {}).get("h24", 0) or 0)
            result["price_usd"] = float(pair.get("priceUsd", 0) or 0)
            result["fdv"] = float(pair.get("fdv", 0) or 0)
            result["symbol"] = pair.get("baseToken", {}).get("symbol", "")
            result["name"] = pair.get("baseToken", {}).get("name", "")
            # Price changes
            pc = pair.get("priceChange", {})
            result["price_change_5m"] = pc.get("m5")
            result["price_change_1h"] = pc.get("h1")
            result["price_change_6h"] = pc.get("h6")
            result["price_change_24h"] = pc.get("h24")
            created = pair.get("pairCreatedAt")
            if created:
                try:
                    age = (datetime.now(timezone.utc) - datetime.fromtimestamp(created / 1000, tz=timezone.utc)).total_seconds() / 3600
                    result["age_hours"] = round(age, 1)
                    result["created_at"] = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat()
                except Exception:
                    pass
            result["data_sources"].append("dexscreener")

        if chain == "solana":
            mint_info = await _solana_get_mint_info(token_address)
            if mint_info.get("mint_authority") != "unknown":
                result["mint_authority"] = mint_info["mint_authority"]
                result["freeze_authority"] = mint_info["freeze_authority"]
                result["data_sources"].append("solana_rpc")
                if mint_info["mint_authority"] in ("11111111111111111111111111111111", None):
                    result["mint_authority"] = "renounced"
                if mint_info["freeze_authority"] in ("11111111111111111111111111111111", None):
                    result["freeze_authority"] = "renounced"

        chain_id = CHAIN_IDS.get(chain, chain)
        try:
            resp = await client.get(
                f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}",
                params={"contract_addresses": token_address},
            )
            if resp.status_code == 200:
                json_data = resp.json()
                goplus_result = json_data.get("result")
                if goplus_result and isinstance(goplus_result, dict):
                    data = goplus_result.get(token_address.lower(), {})
                    if not data and len(goplus_result) == 1:
                        data = list(goplus_result.values())[0]
                    if data and isinstance(data, dict):
                        result["honeypot_risk"] = "high" if data.get("is_honeypot") == "1" else "low"
                        result["buy_tax"] = float(data.get("buy_tax", "0") or 0)
                        result["sell_tax"] = float(data.get("sell_tax", "0") or 0)
                        if chain != "solana":
                            result["mint_authority"] = "active" if data.get("is_mintable") == "1" else "renounced"
                        result["data_sources"].append("goplus")
        except Exception:
            pass

    return result


# ═══════════════════════════════════════════
# RICH ENRICHMENT (all FREE — degrade gracefully)
# ═══════════════════════════════════════════


async def _simulate_trade(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Simulate buy/sell via Jupiter (Solana) or eth_call (EVM).
    
    Returns honeypot status, effective tax rate, and risk assessment.
    Cost: $0 (Jupiter free API + public EVM RPCs).
    """
    try:
        from app.tx_simulator import simulate_transaction
        result = await simulate_transaction(token_address, chain)
        return {
            "can_sell": result.can_sell,
            "can_buy": result.can_buy,
            "sell_tax_pct": result.sell_tax_pct,
            "buy_tax_pct": result.buy_tax_pct,
            "risk": result.risk,
            "is_honeypot": result.is_honeypot,
            "warnings": result.warnings,
            "expected_output": result.expected_output,
            "expected_output_token": result.expected_output_token,
        }
    except Exception as e:
        logger.warning(f"Trade simulation failed for {token_address[:8]}...: {e}")
        return None


async def _get_holder_data(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Get holder count + top-10 concentration.
    
    Cascades: Helius → Birdeye → Solscan → DexScreener.
    Cost: $0 (all free tiers).
    """
    try:
        from app.unified_provider import get_unified_provider
        provider = get_unified_provider()
        holders = await provider.get_token_holders(token_address, limit=50)
        if not holders:
            return None

        total = len(holders)
        # Filter out holders with valid amounts
        valid = [h for h in holders if h.get("amount", 0) > 0]
        if not valid:
            return {"total_holders": total, "holder_count_valid": 0, "concentration_risk": "unknown"}

        total_amount = sum(h.get("amount", 0) for h in valid)
        if total_amount <= 0:
            return {"total_holders": total, "concentration_risk": "unknown"}

        sorted_holders = sorted(valid, key=lambda h: h.get("amount", 0), reverse=True)
        top1_share = (sorted_holders[0]["amount"] / total_amount * 100) if sorted_holders else 0
        top10_amount = sum(h["amount"] for h in sorted_holders[:10])
        top10_share = top10_amount / total_amount * 100

        if top10_share > 80:
            risk = "high"
        elif top10_share > 50:
            risk = "medium"
        else:
            risk = "low"

        return {
            "total_holders": total,
            "holder_count_valid": len(valid),
            "top1_pct": round(top1_share, 1),
            "top10_pct": round(top10_share, 1),
            "concentration_risk": risk,
            "data_source": holders[0].get("source", "unknown") if holders else "unknown",
        }
    except Exception as e:
        logger.warning(f"Holder data failed for {token_address[:8]}...: {e}")
        return None


async def _get_deployer_info(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Get deployer wallet address and basic info.
    
    For Solana: uses FreeSolscanClient to find first transaction signer.
    For EVM: uses Etherscan-family free API for contract creator.
    Cost: $0.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            if chain == "solana":
                try:
                    from app.free_solscan_client import FreeSolscanClient
                    solscan = FreeSolscanClient()
                    # Get token holder/transfer info — first tx = deployer activity
                    if hasattr(solscan, 'get_token_holders'):
                        # Try getting info via account endpoint
                        r = await client.get(
                            f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}",
                            timeout=10.0
                        )
                        if r.status_code == 200:
                            meta = r.json()
                            owner = meta.get("owner", meta.get("tokenAuthority", ""))
                            if owner:
                                return {"deployer": owner, "source": "solscan_token_meta"}
                    return None
                except Exception:
                    return None
            else:
                # EVM: Etherscan family free API
                chain_id = CHAIN_IDS.get(chain, "1")
                base_urls = {
                    "1": "https://api.etherscan.io/api",
                    "56": "https://api.bscscan.com/api", 
                    "137": "https://api.polygonscan.com/api",
                    "8453": "https://api.basescan.org/api",
                    "42161": "https://api.arbiscan.io/api",
                    "10": "https://api-optimistic.etherscan.io/api",
                    "43114": "https://api.snowtrace.io/api",
                }
                api_url = base_urls.get(str(chain_id))
                if not api_url:
                    return None
                r = await client.get(api_url, params={
                    "module": "contract",
                    "action": "getcontractcreation",
                    "contractaddresses": token_address,
                    "apikey": "YourApiKeyToken",  # Free tier no-auth for creation endpoint
                })
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("result", [])
                    if results and isinstance(results, list) and len(results) > 0:
                        creator = results[0].get("contractCreator", "")
                        tx_hash = results[0].get("txHash", "")
                        if creator:
                            return {
                                "deployer": creator,
                                "tx_hash": tx_hash,
                                "source": "etherscan_family",
                            }
                return None
    except Exception as e:
        logger.warning(f"Deployer info failed for {token_address[:8]}...: {e}")
        return None


async def _rag_scam_check(
    token_address: str, chain: str, deployer: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Query known_scams RAG collection for token/deployer match.
    
    Checks both token address and deployer against 67K+ documented scams.
    Cost: $0 (local BGE-small embeddings + FAISS ANN search).
    """
    try:
        from app.rag_service import search_similar
        import asyncio as _a

        queries = []
        # Always check token address
        queries.append(
            _a.wait_for(
                search_similar(
                    f"scam honeypot rug token {token_address} {chain}",
                    "known_scams",
                    limit=5,
                    min_similarity=0.25,
                ),
                timeout=8.0,
            )
        )

        # Check deployer if known
        if deployer:
            queries.append(
                _a.wait_for(
                    search_similar(
                        f"scammer wallet deployer {deployer} {chain}",
                        "known_scams",
                        limit=3,
                        min_similarity=0.25,
                    ),
                    timeout=5.0,
                )
            )

        results = await _a.gather(*queries, return_exceptions=True)

        token_matches = results[0] if isinstance(results[0], list) else []
        deployer_matches = (
            results[1] if len(results) > 1 and isinstance(results[1], list) else []
        )

        all_matches = token_matches + deployer_matches
        if not all_matches:
            return None

        # Deduplicate by content prefix
        seen = set()
        unique = []
        for m in all_matches:
            key = (m.get("content", "") or "")[:80]
            if key not in seen:
                seen.add(key)
                unique.append(m)

        match_snippets = [m.get("content", "")[:200] for m in unique[:3]]

        return {
            "scam_matches": len(unique),
            "top_snippets": match_snippets,
            "is_known_scam": len(unique) >= 2,
            "matched_collections": list({m.get("collection", "known_scams") for m in unique}),
        }
    except Exception as e:
        logger.warning(f"RAG scam check failed for {token_address[:8]}...: {e}")
        return None


# ═══════════════════════════════════════════
# UNIFIED SCAN — Powered by SENTINEL
# ═══════════════════════════════════════════

async def scan_token(
    token_address: str,
    chain: str = "solana",
    tier: str = "free",
    user_id: Optional[str] = None,
) -> ScanResult:
    """Unified token scan using SENTINEL pipeline + market data."""
    
    scan = ScanResult(token_address=token_address, chain=chain)
    
    # Fetch market data (always runs)
    market = await fetch_market_data(token_address, chain)
    scan.symbol = market.get("symbol", "")
    scan.name = market.get("name", "")
    
    # ── Run all FREE enrichments in parallel ──
    sim_result, holder_data, deployer_info = None, None, None
    try:
        sim_result, holder_data, deployer_info = await asyncio.gather(
            _simulate_trade(token_address, chain),
            _get_holder_data(token_address, chain),
            _get_deployer_info(token_address, chain),
            return_exceptions=True,
        )
        # unwrap exceptions
        if isinstance(sim_result, BaseException):
            sim_result = None
        if isinstance(holder_data, BaseException):
            holder_data = None
        if isinstance(deployer_info, BaseException):
            deployer_info = None
    except Exception as e:
        logger.warning(f"Enrichment gather failed: {e}")
    
    # ── RAG scam check (after deployer lookup) ──
    rag_result = None
    deployer_addr = None
    if isinstance(deployer_info, dict):
        deployer_addr = deployer_info.get("deployer")
    if token_address:
        try:
            rag_result = await _rag_scam_check(token_address, chain, deployer_addr)
        except Exception:
            pass
    
    # Run SENTINEL pipeline
    try:
        from app.scanners.sentinel_pipeline import run_sentinel_scan, dataclass_to_dict
        sentinel = await run_sentinel_scan(token_address, chain)
        sentinel_dict = dataclass_to_dict(sentinel)
    except Exception as e:
        logger.error(f"SENTINEL pipeline failed: {e}")
        sentinel = None
        sentinel_dict = None
    
    # ── Compute safety score from SENTINEL composite ──
    if sentinel:
        # SENTINEL composite_risk_score is 0-100 (higher = more risky)
        # Invert to safety_score (higher = safer)
        safety = 100 - int(sentinel.composite_risk_score)
        scan.risk_flags = sentinel.red_flags or []
        
        # Confidence based on how many modules ran
        modules_run = len(sentinel.modules_run)
        if modules_run >= 15:
            scan.confidence = 90
        elif modules_run >= 10:
            scan.confidence = 75
        elif modules_run >= 5:
            scan.confidence = 60
        else:
            scan.confidence = 40
    else:
        safety = 50  # unknown
        scan.confidence = 30
    
    # Adjust from market data
    if market.get("honeypot_risk") == "high":
        safety = max(0, safety - 40)
        scan.risk_flags.append("HONEYPOT_DETECTED")
    elif market.get("honeypot_risk") == "low":
        scan.confidence = min(100, scan.confidence + 5)
    
    if market.get("mint_authority") == "active":
        safety = max(0, safety - 10)
        if "MINTABLE" not in scan.risk_flags:
            scan.risk_flags.append("MINTABLE")
    
    if market.get("freeze_authority") == "active":
        safety = max(0, safety - 8)
        if "FREEZABLE" not in scan.risk_flags:
            scan.risk_flags.append("FREEZABLE")
    
    if market.get("buy_tax", 0) > 10:
        safety = max(0, safety - 10)
        scan.risk_flags.append(f"HIGH_BUY_TAX_{market['buy_tax']:.0f}%")
    
    if market.get("sell_tax", 0) > 10:
        safety = max(0, safety - 10)
        scan.risk_flags.append(f"HIGH_SELL_TAX_{market['sell_tax']:.0f}%")
    
    if market.get("lp_burned") == "no":
        safety = max(0, safety - 10)
        if "LP_NOT_BURNED" not in scan.risk_flags:
            scan.risk_flags.append("LP_NOT_BURNED")
    
    if market.get("liquidity_usd", 0) < 1000:
        safety = max(0, safety - 10)
        scan.risk_flags.append("LOW_LIQUIDITY")
    
    age = market.get("age_hours")
    if age is not None and age < 1:
        safety = max(0, safety - 8)
        scan.risk_flags.append("VERY_NEW")
    
    # ── Adjust from enrichment data (simulation + holders + RAG) ──
    # Trade simulation
    if isinstance(sim_result, dict):
        if sim_result.get("is_honeypot"):
            safety = max(0, safety - 50)
            scan.risk_flags.append("HONEYPOT_SIMULATED")
            scan.confidence = min(100, scan.confidence + 20)
        elif sim_result.get("risk") == "critical":
            safety = max(0, safety - 25)
            scan.risk_flags.append("TRADE_SIM_CRITICAL")
            scan.confidence = min(100, scan.confidence + 10)
        elif sim_result.get("sell_tax_pct", 0) > 20:
            safety = max(0, safety - 10)
            scan.risk_flags.append(f"SIM_TAX_{sim_result['sell_tax_pct']:.0f}%")
    
    # Holder concentration
    if isinstance(holder_data, dict):
        if holder_data.get("concentration_risk") == "high":
            safety = max(0, safety - 15)
            scan.risk_flags.append("HOLDER_CONCENTRATION_HIGH")
            scan.confidence = min(100, scan.confidence + 5)
        elif holder_data.get("concentration_risk") == "medium":
            safety = max(0, safety - 5)
            if "top10_pct" in holder_data:
                scan.risk_flags.append(f"HOLDER_TOP10_{holder_data['top10_pct']:.0f}%")
    
    # Deployer info
    if isinstance(deployer_info, dict):
        scan.confidence = min(100, scan.confidence + 3)
    
    # RAG scam check
    if isinstance(rag_result, dict):
        if rag_result.get("is_known_scam"):
            safety = max(0, safety - 40)
            scan.risk_flags.append("KNOWN_SCAM_MATCH")
            scan.confidence = min(100, scan.confidence + 25)
        elif rag_result.get("scam_matches", 0) > 0:
            safety = max(0, safety - 15)
            scan.risk_flags.append("SCAM_PATTERN_SIMILARITY")
            scan.confidence = min(100, scan.confidence + 10)
    
    # ── Boost confidence from data sources ──
    ds = market.get("data_sources", [])
    if "dexscreener" in ds:
        scan.confidence = min(100, scan.confidence + 5)
    if "solana_rpc" in ds:
        scan.confidence = min(100, scan.confidence + 5)
    if "goplus" in ds:
        scan.confidence = min(100, scan.confidence + 5)
    
    scan.safety_score = max(0, min(100, safety))
    
    # ── Build tier data ──
    # FREE: market data + SENTINEL risk summary + enrichments
    scan.free = {
        **market,
        "modules_run": sentinel.modules_run if sentinel else [],
        "risk_level": sentinel.risk_level if sentinel else "unknown",
    }
    # Add enrichment data if available
    if isinstance(sim_result, dict):
        scan.free["simulation"] = sim_result
    if isinstance(holder_data, dict):
        scan.free["holders"] = holder_data
    if isinstance(deployer_info, dict):
        scan.free["deployer"] = deployer_info
    if isinstance(rag_result, dict):
        scan.free["rag_scam_check"] = rag_result
    
    # PRO: Tier 1+2 module results
    if tier in ("pro", "elite"):
        scan.tier_required = "pro"
        if sentinel:
            scan.pro = {
                "holder_analysis": sentinel_dict.get("holder_analysis"),
                "bundle_detection": sentinel_dict.get("bundle_detection"),
                "exchange_funding": sentinel_dict.get("exchange_funding"),
                "liquidity_verification": sentinel_dict.get("liquidity_verification"),
                "dev_reputation": sentinel_dict.get("dev_reputation"),
                "wash_trading": sentinel_dict.get("wash_trading"),
                "honeypot_detection": sentinel_dict.get("honeypot_detection"),
                "contract_authority": sentinel_dict.get("contract_authority"),
                "mev_detection": sentinel_dict.get("mev_detection"),
                "flash_loan_detection": sentinel_dict.get("flash_loan_detection"),
                "pump_dump_detection": sentinel_dict.get("pump_dump_detection"),
                "oracle_manipulation": sentinel_dict.get("oracle_manipulation"),
                "governance_attack": sentinel_dict.get("governance_attack"),
                "proxy_detection": sentinel_dict.get("proxy_detection"),
                "module_risk_scores": sentinel.module_risk_scores if sentinel else {},
            }
    
    # ELITE: All modules + deep analysis
    if tier == "elite":
        scan.tier_required = "elite"
        if sentinel:
            scan.elite = {
                **scan.pro,  # inherit pro data
                "static_analysis": sentinel_dict.get("static_analysis"),
                "decompiler_analysis": sentinel_dict.get("decompiler_analysis"),
                "address_labels": sentinel_dict.get("address_labels"),
                "wallet_intel": sentinel_dict.get("wallet_intel"),
                "fund_flow": sentinel_dict.get("fund_flow"),
                "contract_diff": sentinel_dict.get("contract_diff"),
                "composite_risk_score": sentinel.composite_risk_score,
            }
    
    return scan


# ═══════════════════════════════════════════
# QUICK SCAN (Telegram-friendly text)
# ═══════════════════════════════════════════

async def quick_scan_text(token_address: str, chain: str = "solana") -> str:
    scan = await scan_token(token_address, chain, tier="free")
    f = scan.free
    safety = scan.safety_score
    
    if safety >= 80: emoji = "🟢"
    elif safety >= 50: emoji = "🟡"
    elif safety >= 25: emoji = "🟠"
    else: emoji = "🔴"
    
    name = scan.symbol or scan.name or "???"
    
    lines = [
        f"{emoji} *SENTINEL Scan: {name}*",
        f"",
        f"📍 Chain: {chain.upper()}",
        f"💰 Price: ${f.get('price_usd', 0):.8f}",
        f"💧 Liquidity: ${f.get('liquidity_usd', 0):,.0f}",
        f"📊 Volume 24h: ${f.get('volume_24h', 0):,.0f}",
    ]
    
    if f.get("age_hours") is not None:
        lines.append(f"⏰ Age: {f['age_hours']}h")
    
    # Price changes
    changes = []
    if f.get("price_change_5m") is not None: changes.append(f"5m: {f['price_change_5m']:+.1f}%")
    if f.get("price_change_1h") is not None: changes.append(f"1h: {f['price_change_1h']:+.1f}%")
    if f.get("price_change_24h") is not None: changes.append(f"24h: {f['price_change_24h']:+.1f}%")
    if changes:
        lines.append(f"📈 Changes: {' | '.join(changes)}")
    
    lines.append(f"")
    modules = len(f.get("modules_run", []))
    lines.append(f"🛡️ *Safety: {safety}/100* (confidence: {scan.confidence}%)")
    lines.append(f"🔬 {modules} SENTINEL modules analyzed")
    
    if scan.risk_flags:
        lines.append(f"⚠️ Flags: {', '.join(scan.risk_flags[:5])}")
    
    lines.extend([
        f"",
        f"🔒 Honeypot: {f.get('honeypot_risk', '?')}",
        f"💸 Tax: {f.get('buy_tax', 0)}% buy / {f.get('sell_tax', 0)}% sell",
        f"🔑 Mint: {f.get('mint_authority', '?')}",
        f"❄️ Freeze: {f.get('freeze_authority', '?')}",
        f"🔥 LP: {f.get('lp_burned', '?')}",
        f"📡 Sources: {', '.join(f.get('data_sources', []))}",
        f"",
        f"_Free scan. Upgrade to PRO for full SENTINEL analysis._",
        f"/upgrade for details",
    ])
    
    return "\n".join(lines)


from app.token_discovery import discover_tokens, MONITORED_CHAINS
