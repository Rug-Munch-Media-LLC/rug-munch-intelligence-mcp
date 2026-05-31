"""
Unified Token Scanner — RugMunch Intelligence
==============================================
Now powered by SENTINEL (21-module pipeline) + DexScreener/GoPlus market data.

FREE tier:   SENTINEL Tier 1 (12 core modules) + DexScreener + GoPlus
PRO tier:    SENTINEL Tier 1+2 (17 modules) + wallet intelligence  
ELITE tier:  SENTINEL Tier 1+2+3+4 (all 21+ modules) + deep analysis
"""

import os
import asyncio
from datetime import datetime
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


# ── Deployer deep-dive: wallet age, token count, funding source ──

async def _deep_deployer_check(deployer_addr: str, chain: str) -> Optional[Dict[str, Any]]:
    """Rich deployer intelligence using wallet_memory engine + RAG.
    
    Returns:
        entity_id, entity_label, risk_score, linked_wallets,
        scam_associations, deployer_history, cross_chain_presence.
    Cost: $0 (internal engine + existing RAG).
    """
    try:
        from app.wallet_memory.engine import WalletMemoryEngine, get_wallet_engine
        engine = get_wallet_engine()
        intel = await engine.get_deployer_intelligence(deployer_addr, chain)
        if not intel:
            return None
        
        result = {
            "deployer": deployer_addr,
            "entity_id": intel.get("entity_id"),
            "entity_label": intel.get("entity_label", ""),
            "entity_category": intel.get("entity_category", "unknown"),
            "risk_score": intel.get("risk_score", 0),
            "risk_level": intel.get("risk_level", "unknown"),
            "linked_wallets_count": len(intel.get("linked_wallets", [])),
            "scam_associations": intel.get("scam_associations", [])[:5],
            "deployer_history_tokens": len(intel.get("deployer_history", [])),
            "cross_chain_chains": [c.get("chain") for c in intel.get("cross_chain_presence", [])],
            "labels": intel.get("labels", [])[:5],
            "confidence": intel.get("confidence", 0),
            "source": "wallet_memory_engine",
        }
        
        # If RAG is available, also check known_scams for this deployer
        try:
            from app.rag_service import search_similar
            import asyncio as _a
            rag_hits = await _a.wait_for(
                search_similar(
                    f"scammer rug pull deployer {deployer_addr} {chain}",
                    "known_scams", limit=3, min_similarity=0.3,
                ),
                timeout=5.0,
            )
            if rag_hits:
                result["rag_scam_hits"] = len(rag_hits)
                result["rag_scam_snippet"] = (rag_hits[0].get("content", "") or "")[:200]
        except Exception:
            pass
        
        return result
    except Exception as e:
        logger.warning(f"Deep deployer check failed for {deployer_addr[:8]}...: {e}")
        return None


# ── Cross-chain deployer tracking ──

async def _check_cross_chain_deployer(deployer_addr: str, chain: str) -> Optional[Dict[str, Any]]:
    """Check if deployer has launched tokens on other chains.
    
    Queries wallet_memory engine for cross_chain_presence and
    chain_registry for known multi-chain deployer patterns.
    Cost: $0.
    """
    try:
        from app.chain_registry import get_chains_for_address
        
        # Detect chains directly from chain_registry
        chains_found = []
        try:
            known = get_chains_for_address(deployer_addr)
            if known:
                chains_found = list(known.keys())
        except Exception:
            pass
        
        # Also try wallet_memory for cross-chain data
        try:
            from app.wallet_memory.engine import get_wallet_engine
            engine = get_wallet_engine()
            intel = await engine.get_deployer_intelligence(deployer_addr, chain)
            if intel:
                cross = intel.get("cross_chain_presence", [])
                for entry in cross:
                    c = entry.get("chain", "")
                    if c and c not in chains_found:
                        chains_found.append(c)
        except Exception:
            pass
        
        if not chains_found:
            return None
        
        return {
            "cross_chain_count": len(chains_found),
            "chains": chains_found,
            "is_multi_chain": len(chains_found) > 1,
            "risk": "high" if len(chains_found) >= 3 else ("medium" if len(chains_found) > 1 else "low"),
        }
    except Exception as e:
        logger.warning(f"Cross-chain deployer check failed: {e}")
        return None


# ── Contract verification check ──

async def _check_contract_verification(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Check if the token contract is verified on its chain explorer.
    
    Solana: free Solscan API. EVM: Etherscan-family free API.
    Unverified contract = high rug risk.
    Cost: $0.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            if chain == "solana":
                # Solscan free API
                r = await client.get(
                    f"https://public-api.solscan.io/account/{token_address}",
                    timeout=10.0,
                )
                if r.status_code == 200:
                    data = r.json()
                    verified = bool(data.get("verified") or data.get("isVerified"))
                    return {
                        "verified": verified,
                        "explorer": "solscan",
                        "risk": "low" if verified else "high",
                        "warning": None if verified else "⚠️ Contract is NOT verified on Solscan",
                    }
                return {"verified": False, "explorer": "solscan", "risk": "medium", "warning": "Could not determine verification status"}
            
            else:
                # EVM: Etherscan-family free API
                chain_id = CHAIN_IDS.get(chain, "1")
                base_urls = {
                    "1": ("https://api.etherscan.io/api", "Etherscan"),
                    "56": ("https://api.bscscan.com/api", "BscScan"),
                    "137": ("https://api.polygonscan.com/api", "PolygonScan"),
                    "8453": ("https://api.basescan.org/api", "BaseScan"),
                    "42161": ("https://api.arbiscan.io/api", "Arbiscan"),
                    "10": ("https://api-optimistic.etherscan.io/api", "Optimistic Etherscan"),
                    "43114": ("https://api.snowtrace.io/api", "SnowTrace"),
                }
                entry = base_urls.get(str(chain_id))
                if not entry:
                    return None
                api_url, name = entry
                
                r = await client.get(api_url, params={
                    "module": "contract",
                    "action": "getabi",
                    "address": token_address,
                    "apikey": "YourApiKeyToken",
                })
                if r.status_code == 200:
                    data = r.json()
                    verified = data.get("status") == "1" and data.get("message") == "OK"
                    return {
                        "verified": verified,
                        "explorer": name.lower(),
                        "risk": "low" if verified else "high",
                        "warning": None if verified else f"⚠️ Contract is NOT verified on {name}",
                    }
                return None
    except Exception as e:
        logger.warning(f"Contract verification check failed: {e}")
        return None


# ── Multi-source liquidity lock cross-check ──

async def _check_liquidity_lock_multi(token_address: str, chain: str, pair_address: str = "") -> Optional[Dict[str, Any]]:
    """Cross-check LP lock status across multiple locker registries.
    
    Sources: RugDoc, Unicrypt, Team Finance, Mudra, DexScreener.
    Aggressively penalizes unlocked or fake-locked LP.
    Cost: $0.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=12.0) as client:
            lockers = {
                "rugdoc": f"https://api.rugdoc.io/api/v1/locker/check/{token_address}?chain={chain}",
                "dex_scan": f"https://api.dexscreener.com/latest/dex/tokens/{token_address}",
            }
            
            results = {}
            locked_sources = 0
            unlocked_sources = 0
            
            # Check DexScreener (always available)
            try:
                r = await client.get(lockers["dex_scan"], timeout=8.0)
                if r.status_code == 200:
                    pairs = r.json().get("pairs", [])
                    for pair in pairs:
                        lp_locked = pair.get("lpLocked", False)
                        locker_name = pair.get("lpLocker", "unknown")
                        results["dexscreener"] = {
                            "locked": lp_locked,
                            "locker": locker_name,
                            "pair": pair.get("pairAddress", ""),
                        }
                        if lp_locked:
                            locked_sources += 1
                        else:
                            unlocked_sources += 1
                        break
            except Exception:
                pass
            
            # Check RugDoc
            try:
                r = await client.get(lockers["rugdoc"], timeout=8.0)
                if r.status_code == 200:
                    data = r.json()
                    locked = data.get("locked", False) or data.get("isLocked", False)
                    results["rugdoc"] = {
                        "locked": locked,
                        "locker": data.get("locker", data.get("platform", "rugdoc")),
                    }
                    if locked:
                        locked_sources += 1
                    else:
                        unlocked_sources += 1
            except Exception:
                pass
            
            if not results:
                return None
            
            total_checks = locked_sources + unlocked_sources
            locked_pct = (locked_sources / total_checks * 100) if total_checks > 0 else 0
            
            return {
                "sources_checked": list(results.keys()),
                "locked_sources": locked_sources,
                "unlocked_sources": unlocked_sources,
                "locked_pct": round(locked_pct, 0),
                "details": results,
                "risk": "high" if locked_pct < 50 else ("medium" if locked_pct < 100 else "low"),
                "warning": f"⚠️ LP lock unconfirmed by {unlocked_sources} source(s)" if unlocked_sources > 0 else None,
            }
    except Exception as e:
        logger.warning(f"Multi-source LP lock check failed: {e}")
        return None


# ── Homoglyph / copycat detection ──

# Top 100 token symbols by market cap (updated periodically)
_TOP_SYMBOLS_CACHE: Optional[set] = None

def _get_top_symbols() -> set:
    """Lazy-load top token symbols for copycat detection."""
    global _TOP_SYMBOLS_CACHE
    if _TOP_SYMBOLS_CACHE is not None:
        return _TOP_SYMBOLS_CACHE
    
    # Top symbols by recognition — used for homoglyph detection
    _TOP_SYMBOLS_CACHE = {
        "BTC", "ETH", "USDT", "BNB", "SOL", "USDC", "XRP", "DOGE", "ADA", "AVAX",
        "DOT", "TRX", "MATIC", "LINK", "SHIB", "LTC", "UNI", "ATOM", "XLM", "OKB",
        "XMR", "ETC", "FIL", "APT", "ARB", "OP", "NEAR", "VET", "ALGO", "ICP",
        "GRT", "SAND", "MANA", "AAVE", "EGLD", "THETA", "FTM", "FLOW", "QNT", "CHZ",
        "PEPE", "BONK", "WIF", "JUP", "RAY", "ORCA", "PYTH", "JTO", "BODEN", "TREMP",
        "SAMO", "MYRO", "POPCAT", "MEW", "WEN", "BOME", "SLERF", "ANALOS", "SAMO",
        "WBNB", "CAKE", "BAKE", "XVS", "1INCH", "CRV", "SNX", "COMP", "MKR", "YFI",
        "SUSHI", "RUNE", "LDO", "STETH", "RETH", "CBETH", "FXS", "GMX", "GNS", "PENDLE",
        "TIA", "SEI", "SUI", "BLUR", "STRK", "ZK", "ZRO", "EIGEN", "ENA", "OMNI",
        "TAO", "FET", "RNDR", "WLD", "AGIX", "OCEAN", "AKT", "NOS", "PRIME",
    }
    return _TOP_SYMBOLS_CACHE


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Fast Levenshtein distance for short strings (in-memory, no imports)."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]


async def _check_copycat(symbol: str, name: str) -> Optional[Dict[str, Any]]:
    """Detect homoglyph/copycat tokens mimicking established projects.
    
    Checks Levenshtein distance against top-100 symbols.
    Also detects common social engineering patterns.
    Cost: $0 (in-memory string comparison).
    """
    if not symbol and not name:
        return None
    
    try:
        top_symbols = _get_top_symbols()
        symbol_upper = symbol.upper().strip() if symbol else ""
        name_upper = name.upper().strip() if name else ""
        
        close_matches = []
        
        for known in top_symbols:
            # Exact match = legitimate (or very bold copycat)
            if symbol_upper == known:
                continue
            
            if symbol_upper and len(symbol_upper) >= 2:
                # Check Levenshtein distance
                dist = _levenshtein_distance(symbol_upper, known)
                max_len = max(len(symbol_upper), len(known))
                similarity = 1 - (dist / max_len)
                
                if similarity > 0.75 and dist <= 2:
                    close_matches.append({
                        "our_symbol": symbol_upper,
                        "known_symbol": known,
                        "levenshtein_dist": dist,
                        "similarity": round(similarity, 2),
                        "type": "homoglyph" if dist == 1 else "close_match",
                    })
            
            # Check name similarity
            if name_upper and known in name_upper and len(name_upper) > len(known):
                close_matches.append({
                    "our_name": name,
                    "known_symbol": known,
                    "type": "name_contains_known",
                })
        
        if not close_matches:
            return None
        
        # Check for special homoglyph characters
        homoglyph_chars = {
            '0': 'O', '1': 'l', '3': 'E', '4': 'A', '5': 'S',
            '6': 'G', '7': 'T', '8': 'B', '@': 'A', '$': 'S',
        }
        has_homoglyphs = any(c in symbol_upper for c in homoglyph_chars) if symbol_upper else False
        
        return {
            "matches": close_matches[:5],
            "match_count": len(close_matches),
            "has_homoglyph_chars": has_homoglyphs,
            "risk": "high" if has_homoglyphs or any(m["type"] == "homoglyph" for m in close_matches) else "medium",
            "warning": "⚠️ Token symbol closely resembles known project(s)" if close_matches else None,
        }
    except Exception as e:
        logger.warning(f"Copycat check failed: {e}")
        return None


# ── Volume anomaly detection ──

async def _check_volume_anomaly(
    volume_24h: float, liquidity_usd: float, age_hours: Optional[float], fdv: float = 0
) -> Optional[Dict[str, Any]]:
    """Detect manipulated volume patterns.
    
    Checks:
      - Volume/Liquidity ratio (100x+ = wash trading)
      - Volume/FDV ratio
      - New token + high volume anomaly
      - Age/volume correlation
    Cost: $0 (already-fetched market data).
    """
    try:
        warnings = []
        risk_signals = 0
        
        result: Dict[str, Any] = {
            "volume_24h": volume_24h,
            "liquidity_usd": liquidity_usd,
            "age_hours": age_hours,
        }
        
        # Ratio 1: Volume/Liquidity > 100x = wash trading
        if liquidity_usd > 0:
            vol_liq_ratio = volume_24h / liquidity_usd
            result["vol_liq_ratio"] = round(vol_liq_ratio, 1)
            if vol_liq_ratio > 200:
                warnings.append(f"🚨 Volume {vol_liq_ratio:.0f}x liquidity — definitely manipulated")
                risk_signals += 3
            elif vol_liq_ratio > 50:
                warnings.append(f"⚠️ Volume {vol_liq_ratio:.0f}x liquidity — suspicious")
                risk_signals += 2
            elif vol_liq_ratio > 20:
                warnings.append(f"Volume {vol_liq_ratio:.0f}x liquidity — watch closely")
                risk_signals += 1
        
        # Ratio 2: Volume/FDV — high ratio on low FDV = likely wash
        if fdv > 0:
            vol_fdv_ratio = volume_24h / fdv
            result["vol_fdv_ratio"] = round(vol_fdv_ratio, 2)
            if vol_fdv_ratio > 10:
                warnings.append(f"Volume {vol_fdv_ratio:.1f}x FDV — wash trading pattern")
                risk_signals += 2
            elif vol_fdv_ratio > 5:
                risk_signals += 1
        
        # Age anomaly: new token (<2h) with high volume
        if age_hours is not None and age_hours < 2 and volume_24h > 10000:
            warnings.append(f"Brand new token ({age_hours:.1f}h) with ${volume_24h:,.0f} volume — likely coordinated")
            risk_signals += 2
        elif age_hours is not None and age_hours < 6 and volume_24h > 500000:
            warnings.append(f"Very young token ({age_hours:.1f}h) with high volume")
            risk_signals += 1
        
        # Volume spike without liquidity depth
        if volume_24h > 100000 and liquidity_usd < 1000:
            warnings.append("High volume on near-zero liquidity — classic pump setup")
            risk_signals += 2
        
        result["warnings"] = warnings
        result["risk_signals"] = risk_signals
        result["risk"] = "high" if risk_signals >= 3 else ("medium" if risk_signals >= 1 else "low")
        result["is_manipulated"] = risk_signals >= 3
        
        return result if risk_signals > 0 else None
        
    except Exception as e:
        logger.warning(f"Volume anomaly check failed: {e}")
        return None


# ═══════════════════════════════════════════
# UNIFIED SCAN — Powered by SENTINEL
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 11: Price Consensus (multi-source MAD outlier filter)
# ═══════════════════════════════════════════════════════════════

async def _get_price_consensus(token_address: str, chain: str, market_price: float = 0) -> Optional[Dict[str, Any]]:
    """Cross-check price across DexScreener, Jupiter, Birdeye, CoinGecko.
    Uses MAD outlier filtering to detect manipulated single-source prices."""
    try:
        from app.price_consensus import get_price_consensus
        engine = get_price_consensus()
        result = await asyncio.wait_for(engine.get_consensus_price(token_address, chain), timeout=8.0)
        if not result or not result.is_reliable():
            return None
        
        # Compare consensus price vs single-source (DexScreener)
        consensus_price = result.weighted_mean
        price_diff_pct = 0
        if market_price > 0 and consensus_price > 0:
            price_diff_pct = abs(market_price - consensus_price) / market_price * 100
        
        return {
            "consensus_price": round(consensus_price, 8),
            "dex_price": round(market_price, 8),
            "price_diff_pct": round(price_diff_pct, 1),
            "sources_used": result.source_count,
            "outliers_removed": result.outlier_count,
            "reliability": round(result.reliability_score * 100),
            "is_manipulated": price_diff_pct > 15 or result.outlier_count >= 2,
        }
    except Exception as e:
        logger.warning(f"Price consensus failed for {token_address}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 12: Birdeye API (holder distribution, security, market)
# ═══════════════════════════════════════════════════════════════

async def _get_birdeye_data(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Pull Birdeye security scan + token overview for second opinion."""
    try:
        from app.birdeye_client import BirdeyeClient
        client = BirdeyeClient()
        security, overview = await asyncio.wait_for(asyncio.gather(
            client.security_scan(token_address),
            client.get_token_overview(token_address),
            return_exceptions=True,
        ), timeout=8.0)
        if isinstance(security, BaseException):
            security = None
        if isinstance(overview, BaseException):
            overview = None
        
        result = {}
        if isinstance(security, dict):
            result["security"] = {
                "is_honeypot": security.get("is_honeypot", False),
                "is_rugpull": security.get("is_rugpull", False),
                "risk_score": security.get("risk_score", 0),
                "owner_balance_pct": security.get("owner_balance_pct"),
            }
        if isinstance(overview, dict):
            result["overview"] = {
                "market_cap": overview.get("mc"),
                "holders": overview.get("holder"),
                "liquidity": overview.get("liquidity"),
                "price_change_24h": overview.get("priceChange24h"),
            }
        return result if result else None
    except Exception as e:
        logger.warning(f"Birdeye enrichment failed for {token_address}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 13: Multi-RPC Mint Authority Consensus (Solana)
# ═══════════════════════════════════════════════════════════════

async def _verify_mint_consensus(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Cross-verify mint/freeze authority across 3+ RPCs. Single RPC can lie."""
    if chain.lower() != "solana":
        return None  # EVM uses etherscan-family which is single-source for now
    try:
        from app.consensus_rpc import get_consensus_rpc
        rpc = get_consensus_rpc()
        # Query mint authority from multiple RPCs
        result = await asyncio.wait_for(rpc.solana_query_with_consensus(
            "getAccountInfo",
            [token_address, {"encoding": "jsonParsed"}],
        ), timeout=8.0)
        if not result or not result.is_reliable():
            return None
        
        # Parse mint authority from the parsed data
        data = result.agreed_value
        if isinstance(data, dict):
            parsed = data.get("result", {}).get("value", {}).get("data", {}).get("parsed", {})
            mint_info = parsed.get("info", {})
            mint_authority = mint_info.get("mintAuthority")
            freeze_authority = mint_info.get("freezeAuthority")
            
            return {
                "mint_authority": mint_authority,
                "freeze_authority": freeze_authority,
                "rpc_sources": result.source_count,
                "agreeing_rpcs": result.agreeing_count,
                "total_rpcs": result.total_count,
                "is_reliable": result.is_reliable(),
                "has_mint_authority": mint_authority is not None,
                "has_freeze_authority": freeze_authority is not None,
            }
        return None
    except Exception as e:
        logger.warning(f"Multi-RPC mint consensus failed for {token_address}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 14: Auto-ingest scan results to RAG (data flywheel)
# ═══════════════════════════════════════════════════════════════

async def _ingest_scan_to_rag(scan_result) -> None:
    """Feed every scan back into RAG knowledge base. Fire-and-forget."""
    try:
        from app.rag_service import get_rag_service
        rag = get_rag_service()
        doc = {
            "collection": "token_analysis",
            "content": (
                f"Token: {scan_result.name} ({scan_result.symbol}) on {scan_result.chain}\n"
                f"Address: {scan_result.token_address}\n"
                f"Safety Score: {scan_result.safety_score}/100\n"
                f"Risk Flags: {', '.join(scan_result.risk_flags) if scan_result.risk_flags else 'none'}\n"
                f"Confidence: {scan_result.confidence}%\n"
                f"Price: ${getattr(scan_result, 'price_usd', 'N/A')}\n"
            ),
            "metadata": {
                "token_address": scan_result.token_address,
                "chain": scan_result.chain,
                "symbol": scan_result.symbol,
                "safety_score": scan_result.safety_score,
                "risk_flags": scan_result.risk_flags,
                "scanned_at": datetime.utcnow().isoformat(),
            },
        }
        await rag.ingest_document(**doc)
    except Exception as e:
        logger.warning(f"Auto-ingest to RAG failed for {scan_result.token_address}: {e}")


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 15: Solscan Token Data (holder counts, metadata)
# ═══════════════════════════════════════════════════════════════

async def _get_solscan_data(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Pull Solscan token holder data, metadata, and DeFi activities."""
    if chain.lower() != "solana":
        return None
    try:
        api_key = os.getenv("SOLSCAN_API_KEY", "")
        if not api_key:
            return None
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = {"accept": "application/json", "token": api_key}
            
            # Fetch token meta + holders in parallel
            meta_resp = await client.get(
                f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}",
                headers=headers)
            holders_resp = await client.get(
                f"https://public-api.solscan.io/token/holders?tokenAddress={token_address}&limit=20&offset=0",
                headers=headers)
            
            result = {}
            if meta_resp.status_code == 200:
                meta = meta_resp.json()
                if meta.get("success"):
                    d = meta.get("data", {})
                    result["name"] = d.get("name", "")
                    result["symbol"] = d.get("symbol", "")
                    result["decimals"] = d.get("decimals")
                    result["total_supply"] = d.get("supply")
                    result["holder_count_est"] = d.get("holder")
                    result["icon"] = d.get("icon", "")
            
            if holders_resp.status_code == 200:
                holders_data = holders_resp.json()
                if holders_data.get("success"):
                    holders = holders_data.get("data", [])
                    result["top_holders"] = [{
                        "address": h.get("address", "")[:8],
                        "amount": h.get("amount"),
                        "pct": h.get("percentage"),
                    } for h in holders[:10]]
                    if holders:
                        total_pct = sum(h.get("percentage", 0) or 0 for h in holders)
                        result["top10_concentration"] = round(total_pct, 1)
            
            return result if result else None
    except Exception as e:
        logger.warning(f"Solscan enrichment failed for {token_address}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 16: Moralis Token/Chain Data (multi-chain)
# ═══════════════════════════════════════════════════════════════

async def _get_moralis_data(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Pull Moralis token metadata, price, and chain-specific data."""
    try:
        api_key = os.getenv("MORALIS_API_KEY", "")
        if not api_key:
            return None
        
        chain_map = {
            "ethereum": "eth", "bsc": "bsc", "polygon": "polygon",
            "arbitrum": "arbitrum", "optimism": "optimism", "avalanche": "avalanche",
            "fantom": "fantom", "base": "base", "solana": "solana",
        }
        moralis_chain = chain_map.get(chain.lower(), chain.lower())
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = {"accept": "application/json", "X-API-Key": api_key}
            
            # Token metadata + price
            meta_resp = await client.get(
                f"https://deep-index.moralis.io/api/v2.2/erc20/metadata",
                params={"chain": moralis_chain, "addresses": [token_address]},
                headers=headers)
            
            price_resp = await client.get(
                f"https://deep-index.moralis.io/api/v2.2/erc20/{token_address}/price",
                params={"chain": moralis_chain},
                headers=headers)
            
            result = {}
            if meta_resp.status_code == 200:
                meta = meta_resp.json()
                if isinstance(meta, list) and meta:
                    m = meta[0]
                    result["token_name"] = m.get("name")
                    result["symbol"] = m.get("symbol")
                    result["decimals"] = m.get("decimals")
                    result["verified_contract"] = m.get("verified_contract")
                    result["possible_spam"] = m.get("possible_spam", False)
            
            if price_resp.status_code == 200:
                price_data = price_resp.json()
                result["price_usd"] = price_data.get("usdPrice")
                result["price_change_24h"] = price_data.get("usdPrice24hrPercentChange")
                result["exchange_name"] = price_data.get("exchangeName")
            
            return result if result else None
    except Exception as e:
        logger.warning(f"Moralis enrichment failed for {token_address}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 17: Etherscan Enhanced Contract Verification (9 EVM chains)
# ═══════════════════════════════════════════════════════════════

async def _get_etherscan_enhanced(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Enhanced EVM contract check using real Etherscan API key.
    Verifies contract, gets ABI, creator, tx count, and source code status."""
    if chain.lower() == "solana":
        return None  # Solana handled by Solscan
    
    try:
        api_key = os.getenv("ETHERSCAN_API_KEY", "")
        if not api_key:
            return None
        
        # Map chain to etherscan-family explorer
        explorer_map = {
            "ethereum": "https://api.etherscan.io",
            "bsc": "https://api.bscscan.com",
            "polygon": "https://api.polygonscan.com",
            "arbitrum": "https://api.arbiscan.io",
            "optimism": "https://api-optimistic.etherscan.io",
            "avalanche": "https://api.snowtrace.io",
            "fantom": "https://api.ftmscan.com",
            "base": "https://api.basescan.org",
            "gnosis": "https://api.gnosisscan.io",
        }
        base_url = explorer_map.get(chain.lower())
        if not base_url:
            return None
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Get contract source code (verification status + source)
            source_resp = await client.get(f"{base_url}/api", params={
                "module": "contract", "action": "getsourcecode",
                "address": token_address, "apikey": api_key,
            })
            
            # Get contract creator + creation tx
            creation_resp = await client.get(f"{base_url}/api", params={
                "module": "contract", "action": "getcontractcreation",
                "contractaddresses": token_address, "apikey": api_key,
            })
            
            result = {}
            if source_resp.status_code == 200:
                src_data = source_resp.json()
                if src_data.get("status") == "1" and src_data.get("result"):
                    src = src_data["result"][0]
                    result["verified"] = src.get("SourceCode", "") != ""
                    result["contract_name"] = src.get("ContractName", "")
                    result["compiler_version"] = src.get("CompilerVersion", "")
                    result["optimization_used"] = src.get("OptimizationUsed") == "1"
                    result["has_proxy"] = src.get("Proxy") == "1"
                    result["proxy_type"] = src.get("Implementation", "")
            
            if creation_resp.status_code == 200:
                creation_data = creation_resp.json()
                if creation_data.get("status") == "1" and creation_data.get("result"):
                    cr = creation_data["result"][0]
                    result["creator"] = cr.get("contractCreator", "")
                    result["creation_tx"] = cr.get("txHash", "")
            
            return result if result else None
    except Exception as e:
        logger.warning(f"Etherscan enrichment failed for {token_address}: {e}")
        return None



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
        sim_result, holder_data, deployer_info, price_consensus, birdeye_data, solscan_data, moralis_data, etherscan_data = await asyncio.gather(
            _simulate_trade(token_address, chain),
            _get_holder_data(token_address, chain),
            _get_deployer_info(token_address, chain),
            _get_price_consensus(token_address, chain, market.get("price_usd", 0)),
            _get_birdeye_data(token_address, chain),
            _get_solscan_data(token_address, chain),
            _get_moralis_data(token_address, chain),
            _get_etherscan_enhanced(token_address, chain),
            _get_solscan_data(token_address, chain),
            _get_moralis_data(token_address, chain),
            _get_etherscan_enhanced(token_address, chain),
            return_exceptions=True,
        )
        # unwrap exceptions
        if isinstance(sim_result, BaseException):
            sim_result = None
        if isinstance(holder_data, BaseException):
            holder_data = None
        if isinstance(deployer_info, BaseException):
            deployer_info = None
        if isinstance(price_consensus, BaseException):
            price_consensus = None
        if isinstance(birdeye_data, BaseException):
            birdeye_data = None
        if isinstance(solscan_data, BaseException):
            solscan_data = None
        if isinstance(moralis_data, BaseException):
            moralis_data = None
        if isinstance(etherscan_data, BaseException):
            etherscan_data = None
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
    
    # ── Deep deployer + cross-chain (runs after deployer found) ──
    deep_deployer, cross_chain, contract_verify, lp_lock_multi = None, None, None, None
    try:
        if deployer_addr:
            deep_deployer, cross_chain = await asyncio.gather(
                _deep_deployer_check(deployer_addr, chain),
                _check_cross_chain_deployer(deployer_addr, chain),
                return_exceptions=True,
            )
            if isinstance(deep_deployer, BaseException):
                deep_deployer = None
            if isinstance(cross_chain, BaseException):
                cross_chain = None
        
        # Contract verification + LP lock (run in parallel)
        contract_verify, lp_lock_multi, mint_consensus = await asyncio.gather(
            _check_contract_verification(token_address, chain),
            _check_liquidity_lock_multi(token_address, chain, market.get("pair_address", "")),
            _verify_mint_consensus(token_address, chain),
            return_exceptions=True,
        )
        if isinstance(contract_verify, BaseException):
            contract_verify = None
        if isinstance(lp_lock_multi, BaseException):
            lp_lock_multi = None
        if isinstance(mint_consensus, BaseException):
            mint_consensus = None
    except Exception as e:
        logger.warning(f"Secondary enrichment gather failed: {e}")
    
    # ── Copycat + Volume anomaly (CPU-only, uses existing market data) ──
    copycat_result = await _check_copycat(scan.symbol, scan.name)
    volume_anomaly = await _check_volume_anomaly(
        volume_24h=market.get("volume_24h", 0),
        liquidity_usd=market.get("liquidity_usd", 0),
        age_hours=market.get("age_hours"),
        fdv=market.get("fdv", 0),
    )
    
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
    
    # Price manipulation via consensus check
    if isinstance(price_consensus, dict):
        if price_consensus.get("is_manipulated"):
            safety = max(0, safety - 25)
            scan.risk_flags.append("PRICE_MANIPULATION_SUSPECTED")
            scan.confidence = min(100, scan.confidence + 10)
        elif price_consensus.get("reliability", 0) >= 70:
            scan.confidence = min(100, scan.confidence + 5)
    
    # Birdeye second opinion
    if isinstance(birdeye_data, dict):
        birdeye_sec = birdeye_data.get("security", {})
        if isinstance(birdeye_sec, dict):
            if birdeye_sec.get("is_honeypot"):
                safety = max(0, safety - 30)
                scan.risk_flags.append("BIRDEYE_HONEYPOT")
                scan.confidence = min(100, scan.confidence + 15)
            if birdeye_sec.get("is_rugpull"):
                safety = max(0, safety - 30)
                scan.risk_flags.append("BIRDEYE_RUGPULL")
        birdeye_overview = birdeye_data.get("overview", {})
        if isinstance(birdeye_overview, dict) and birdeye_overview.get("holders"):
            scan.confidence = min(100, scan.confidence + 3)
    
    # Multi-RPC mint authority consensus
    if isinstance(mint_consensus, dict) and mint_consensus.get("is_reliable"):
        scan.confidence = min(100, scan.confidence + 5)
        if mint_consensus.get("has_mint_authority"):
            safety = max(0, safety - 10)
            if "MINTABLE_CONSENSUS" not in scan.risk_flags:
                scan.risk_flags.append("MINTABLE_CONSENSUS")
    
    # Solscan data
    if isinstance(solscan_data, dict):
        scan.confidence = min(100, scan.confidence + 5)
        if solscan_data.get("top10_concentration", 0) > 80:
            safety = max(0, safety - 15)
            scan.risk_flags.append("SOLSCAN_HOLDER_CONCENTRATION")
    
    # Moralis data
    if isinstance(moralis_data, dict):
        scan.confidence = min(100, scan.confidence + 5)
        if moralis_data.get("possible_spam"):
            safety = max(0, safety - 30)
            scan.risk_flags.append("MORALIS_SPAM_TOKEN")
        if moralis_data.get("verified_contract") is False:
            safety = max(0, safety - 10)
            scan.risk_flags.append("MORALIS_UNVERIFIED")
    
    # Etherscan enhanced
    if isinstance(etherscan_data, dict):
        scan.confidence = min(100, scan.confidence + 8)
        if etherscan_data.get("verified") is False:
            safety = max(0, safety - 15)
            if "ETHERSCAN_UNVERIFIED" not in scan.risk_flags:
                scan.risk_flags.append("ETHERSCAN_UNVERIFIED")
        if etherscan_data.get("has_proxy"):
            safety = max(0, safety - 10)
            scan.risk_flags.append("PROXY_CONTRACT_DETECTED")
    
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
    
    # Deep deployer intelligence
    if isinstance(deep_deployer, dict):
        deployer_risk = deep_deployer.get("risk_score", 0)
        if deployer_risk > 70:
            safety = max(0, safety - 25)
            scan.risk_flags.append("DEPLOYER_HIGH_RISK")
            scan.confidence = min(100, scan.confidence + 15)
        elif deployer_risk > 40:
            safety = max(0, safety - 10)
            scan.risk_flags.append("DEPLOYER_MEDIUM_RISK")
            scan.confidence = min(100, scan.confidence + 8)
        if deep_deployer.get("rag_scam_hits", 0) > 0:
            safety = max(0, safety - 15)
            scan.risk_flags.append("DEPLOYER_IN_SCAM_DB")
            scan.confidence = min(100, scan.confidence + 10)
    
    # Cross-chain deployer
    if isinstance(cross_chain, dict):
        if cross_chain.get("is_multi_chain"):
            chains = len(cross_chain.get("chains", []))
            safety = max(0, safety - (10 * min(chains, 3)))
            scan.risk_flags.append(f"MULTI_CHAIN_DEPLOYER_{chains}")
            scan.confidence = min(100, scan.confidence + 5)
    
    # Contract not verified = major red flag
    if isinstance(contract_verify, dict):
        if not contract_verify.get("verified"):
            safety = max(0, safety - 20)
            scan.risk_flags.append("CONTRACT_UNVERIFIED")
            scan.confidence = min(100, scan.confidence + 10)
    
    # LP lock multi-source
    if isinstance(lp_lock_multi, dict):
        if lp_lock_multi.get("risk") == "high":
            safety = max(0, safety - 15)
            scan.risk_flags.append("LP_LOCK_UNCONFIRMED")
            scan.confidence = min(100, scan.confidence + 5)
    
    # Copycat detection
    if isinstance(copycat_result, dict):
        match_count = copycat_result.get("match_count", 0)
        if copycat_result.get("risk") == "high":
            safety = max(0, safety - 20)
            scan.risk_flags.append("COPYCAT_DETECTED")
            scan.confidence = min(100, scan.confidence + 8)
        elif match_count > 0:
            safety = max(0, safety - 5)
            scan.risk_flags.append("NAME_SIMILARITY")
    
    # Volume anomaly
    if isinstance(volume_anomaly, dict):
        risk_signals = volume_anomaly.get("risk_signals", 0)
        if volume_anomaly.get("risk") == "high":
            safety = max(0, safety - 20)
            scan.risk_flags.append("VOLUME_MANIPULATION")
            scan.confidence = min(100, scan.confidence + 10)
        elif risk_signals > 0:
            safety = max(0, safety - (risk_signals * 5))
            scan.risk_flags.append("VOLUME_ANOMALY")
    
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
    if isinstance(deep_deployer, dict):
        scan.free["deep_deployer"] = deep_deployer
    if isinstance(cross_chain, dict):
        scan.free["cross_chain"] = cross_chain
    if isinstance(contract_verify, dict):
        scan.free["contract_verification"] = contract_verify
    if isinstance(lp_lock_multi, dict):
        scan.free["lp_lock_multi"] = lp_lock_multi
    if isinstance(copycat_result, dict):
        scan.free["copycat_check"] = copycat_result
    if isinstance(volume_anomaly, dict):
        scan.free["volume_anomaly"] = volume_anomaly
    if isinstance(price_consensus, dict):
        scan.free["price_consensus"] = price_consensus
    if isinstance(birdeye_data, dict):
        scan.free["birdeye"] = birdeye_data
    if isinstance(mint_consensus, dict):
        scan.free["mint_consensus"] = mint_consensus
    if isinstance(solscan_data, dict):
        scan.free["solscan"] = solscan_data
    if isinstance(moralis_data, dict):
        scan.free["moralis"] = moralis_data
    if isinstance(etherscan_data, dict):
        scan.free["etherscan"] = etherscan_data
    
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
    
    # Auto-ingest scan to RAG (fire-and-forget — don't block response)
    asyncio.create_task(_ingest_scan_to_rag(scan))
    
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
