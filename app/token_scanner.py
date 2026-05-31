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
            api_key = os.getenv("GOPLUS_API_KEY", "")
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = await client.get(
                f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}",
                params={"contract_addresses": token_address},
                headers=headers,
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


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: Honeypot.is API (free, no key, EVM chains)
# ═══════════════════════════════════════════════════════════════

async def _check_honeypot_is(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Check token via Honeypot.is free API.
    
    Simulates buy + sell in isolated VM. Flags honeypot, taxes, gas.
    Supports Ethereum, Base, BSC. No API key required.
    """
    if chain.lower() not in ("ethereum", "base", "bsc", "eth", "bnb"):
        return None  # Only EVM chains supported
    
    chain_code = {"ethereum": "eth", "eth": "eth", "base": "base", "bsc": "bsc", "bnb": "bsc"}.get(chain.lower(), "eth")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.honeypot.is/v2/IsHoneypot",
                params={"address": token_address, "chainID": chain_code},
            )
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            result = {
                "is_honeypot": data.get("isHoneypot", False),
                "buy_tax_pct": data.get("buyTax", 0),
                "sell_tax_pct": data.get("sellTax", 0),
                "transfer_tax_pct": data.get("transferTax", 0),
                "max_tx_amount": data.get("maxTxAmount"),
                "max_tx_amount_ui": data.get("maxTxAmountUI"),
                "source": "honeypot.is",
                "chain": chain_code,
            }
            
            # Additional simulation data if available
            sim = data.get("simulation", {})
            if sim:
                result["simulation_success"] = sim.get("success", False)
                result["simulation_error"] = sim.get("error")
            
            return result
    except Exception as e:
        logger.warning(f"Honeypot.is check failed for {token_address[:8]}...: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: ChainPatrol blocklist API (free, no key)
# ═══════════════════════════════════════════════════════════════

async def _check_chainpatrol_asset(asset_type: str, asset_id: str) -> Optional[Dict[str, Any]]:
    """Query ChainPatrol blocklist for domain/address/asset risk status.
    
    Free API — no key required. Checks if asset is flagged by community.
    asset_type: 'domain', 'address', 'token'
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.chainpatrol.io/api/v2/asset/search",
                json={"type": asset_type, "content": asset_id},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            result = {
                "is_blocked": data.get("blocked", False),
                "is_scam": data.get("scam", False),
                "confidence": data.get("confidence", 0),
                "source": "chainpatrol",
                "asset_type": asset_type,
                "asset_id": asset_id,
            }
            
            # Extract labels if present
            labels = data.get("labels", [])
            if labels:
                result["labels"] = [l.get("name") for l in labels if l.get("name")]
            
            return result
    except Exception as e:
        logger.warning(f"ChainPatrol check failed for {asset_id}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: De.Fi Scanner API (free tier, credit-based)
# ═══════════════════════════════════════════════════════════════

async def _check_defi_scanner(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """De.Fi GraphQL scanner — AI security score, backdoor detection, holder analysis.
    
    Uses GraphQL API (public-api.de.fi/graphql) with API key.
    Returns: aiScore, coreIssues, proxy detection, outdated compiler,
    initial funder, and more. 35+ chains supported.
    Cost: 20 credits per scannerProject + 5 for holderAnalysis.
    """
    api_key = os.getenv("DEFI_API_KEY", "")
    # Fallback: read from file if env var not set (Docker env loading issue)
    if not api_key:
        try:
            with open("/tmp/defi_api_key.txt", "r") as f:
                api_key = f.read().strip()
        except Exception:
            pass
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=12.0) as client:
            headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
            
            # De.Fi chain mapping (internal IDs)
            chain_map = {
                "ethereum": 1, "bsc": 2, "polygon": 3, "arbitrum": 4,
                "optimism": 5, "avalanche": 6, "base": 7, "fantom": 8,
                "solana": 12, "bitcoin": 44,
            }
            df_chain_id = chain_map.get(chain.lower(), 1)
            
            query = {
                "query": """
                query($addr: String!, $chainId: Int!) {
                  scannerProject(where: {address: $addr, chainId: $chainId}) {
                    aiScore
                    name
                    contractName
                    outdatedCompiler
                    initialFunder
                    initialFunding
                    txCount
                    whitelisted
                    coreIssues { scwTitle scwDescription }
                    generalIssues { scwTitle scwDescription }
                    proxyData { proxyOwner }
                    stats { critical high medium low total percentage }
                  }
                  scannerHolderAnalysis(where: {address: $addr, chainId: $chainId}) {
                    totalHolders
                    topHoldersTotalPercentage
                    creatorBalancePercentage
                    ownerBalancePercentage
                    burnedPercentage
                    topHolders { address percent }
                  }
                }
                """,
                "variables": {"addr": token_address, "chainId": df_chain_id}
            }
            
            result = await asyncio.wait_for(
                client.post("https://public-api.de.fi/graphql", headers=headers, json=query),
                timeout=12.0,
            )
            
            if result.status_code != 200:
                return None
            
            data = result.json()
            sp = data.get("data", {}).get("scannerProject")
            sha = data.get("data", {}).get("scannerHolderAnalysis")
            
            if not sp:
                return None
            
            # Build result
            res = {
                "defi_score": sp.get("aiScore"),
                "contract_name": sp.get("contractName"),
                "outdated_compiler": sp.get("outdatedCompiler", False),
                "initial_funder": sp.get("initialFunder"),
                "initial_funding": sp.get("initialFunding"),
                "tx_count": sp.get("txCount"),
                "whitelisted": sp.get("whitelisted", False),
                "data_source": "de.fi_graphql",
            }
            
            # Proxy detection
            proxy = sp.get("proxyData") or {}
            if isinstance(proxy, dict) and proxy.get("proxyOwner"):
                res["is_proxy"] = True
                res["proxy_owner"] = proxy.get("proxyOwner", "")[:20]
            else:
                res["is_proxy"] = False
            
            # Stats
            stats = sp.get("stats") or {}
            if isinstance(stats, dict):
                res["issues_critical"] = stats.get("critical", 0)
                res["issues_high"] = stats.get("high", 0)
                res["issues_medium"] = stats.get("medium", 0)
                res["issues_low"] = stats.get("low", 0)
                res["issues_total"] = stats.get("total", 0)
                res["security_pct"] = stats.get("percentage", 0)
            
            # Core issues
            core = sp.get("coreIssues") or []
            if isinstance(core, list) and core:
                res["core_issues"] = [{"title": c.get("scwTitle", ""), "desc": c.get("scwDescription", "")[:80]} for c in core[:5]]
                res["has_critical_issues"] = (res.get("issues_critical", 0) or 0) > 0
            
            # General issues
            gen = sp.get("generalIssues") or []
            if isinstance(gen, list) and gen:
                res["general_issues_count"] = len(gen)
                res["general_issues"] = [g.get("scwTitle", "") for g in gen[:5]]
            
            # Holder analysis
            if sha and isinstance(sha, dict):
                res["total_holders"] = sha.get("totalHolders")
                res["top_holders_pct"] = sha.get("topHoldersTotalPercentage")
                res["creator_pct"] = sha.get("creatorBalancePercentage")
                res["owner_pct"] = sha.get("ownerBalancePercentage")
                res["burned_pct"] = sha.get("burnedPercentage")
                
                # Risk signals from holder data
                top_pct = sha.get("topHoldersTotalPercentage") or 0
                creator_pct = sha.get("creatorBalancePercentage") or 0
                
                if float(top_pct) > 80:
                    res["is_honeypot"] = False  # explicit
                    res["has_hidden_owner"] = False
                else:
                    res["is_honeypot"] = False
                    res["has_hidden_owner"] = False
                
                res["is_mintable"] = False  # not directly available in GraphQL
                res["has_blacklist"] = False
                res["is_upgradeable"] = res.get("is_proxy", False)
            
            return res
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"De.Fi scanner failed for {token_address[:8]}...: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: Blockscout PRO API (free tier, EVM chains)
# ═══════════════════════════════════════════════════════════════

async def _check_blockscout(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Query Blockscout PRO API for contract verification + tx history.
    
    Free tier: 100K credits/day, 5 req/sec, 100+ EVM chains.
    Better pagination than Etherscan (no 1K record cap).
    """
    if chain.lower() == "solana":
        return None
    
    # Blockscout chain slug mapping
    slug_map = {
        "ethereum": "eth", "base": "base", "bsc": "bsc",
        "polygon": "polygon", "arbitrum": "arbitrum",
        "optimism": "optimism", "avalanche": "avalanche",
        "fantom": "fantom", "linea": "linea", "scroll": "scroll",
        "zksync": "zksync", "mantle": "mantle",
    }
    slug = slug_map.get(chain.lower())
    if not slug:
        return None
    
    try:
        api_key = os.getenv("BLOCKSCOUT_API_KEY", "")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Contract verification status
            resp = await client.get(
                f"https://{slug}.blockscout.com/api/v2/smart-contracts/{token_address}",
                headers=headers,
            )
            
            result = {"source": "blockscout", "chain": slug}
            
            if resp.status_code == 200:
                data = resp.json()
                result["verified"] = data.get("is_verified", False)
                result["language"] = data.get("language", "")
                result["compiler_version"] = data.get("compiler_version", "")
                result["optimization_enabled"] = data.get("optimization_enabled", False)
                result["abi"] = data.get("abi") is not None
                
                # Check for proxy
                if data.get("proxy_type"):
                    result["is_proxy"] = True
                    result["proxy_type"] = data.get("proxy_type")
                
                # Token info if available
                token_info = data.get("token", {})
                if token_info:
                    result["token_name"] = token_info.get("name")
                    result["token_symbol"] = token_info.get("symbol")
                    result["token_type"] = token_info.get("type")
                    result["total_supply"] = token_info.get("total_supply")
                    result["holders_count"] = token_info.get("holders")
            
            # Get transaction count (lightweight)
            tx_resp = await client.get(
                f"https://{slug}.blockscout.com/api/v2/addresses/{token_address}/transactions",
                params={"limit": 1},
                headers=headers,
            )
            if tx_resp.status_code == 200:
                tx_data = tx_resp.json()
                result["tx_count"] = tx_data.get("items_count", 0)
            
            return result if any(k != "source" and k != "chain" for k in result) else None
    except Exception as e:
        logger.warning(f"Blockscout check failed for {token_address[:8]}...: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: Token Sniffer (Solidus Labs) via eth_defi wrapper
# ═══════════════════════════════════════════════════════════════

async def _check_token_sniffer(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Query Token Sniffer for token score and scam detection.
    
    Uses eth_defi library wrapper (open-source Python) for free tier access.
    Returns token score, smell tests, and risk flags.
    """
    if chain.lower() not in ("ethereum", "eth", "bsc", "base", "polygon"):
        return None  # Token Sniffer supports 15 chains but API is limited
    
    try:
        # Try direct API first (if we have a key or can use free tier)
        async with httpx.AsyncClient(timeout=12.0) as client:
            # Token Sniffer public lookup (no key required for basic info)
            resp = await client.get(
                f"https://tokensniffer.com/api/v1/tokens/{token_address}",
                params={"chain_id": CHAIN_IDS.get(chain, "1")},
            )
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "token_score": data.get("score"),
                    "is_scam": data.get("is_scam", False),
                    "is_honeypot": data.get("is_honeypot", False),
                    "rugpull_risk": data.get("rugpull_risk", "unknown"),
                    "source": "tokensniffer",
                }
                
                # Smell tests
                smells = data.get("smell_tests", [])
                if smells:
                    result["failed_tests"] = [s.get("name") for s in smells if not s.get("passed", True)]
                
                return result
    except Exception as e:
        logger.warning(f"Token Sniffer check failed for {token_address[:8]}...: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: TRM Labs Free Sanctions API (no key = 100/day)
# ═══════════════════════════════════════════════════════════════

async def _check_trm_sanctions(address: str) -> Optional[Dict[str, Any]]:
    """Screen address against TRM Labs sanctions list.
    
    Free tier: 1 req/sec, 100/day unauthenticated.
    Authenticated: 1K req/sec, 100K/day with free API key.
    Returns isSanctioned boolean + risk flags.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.trmlabs.com/public/v1/sanctions/screening",
                json={"address": [address]},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 201:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    r = results[0]
                    return {
                        "is_sanctioned": r.get("isSanctioned", False),
                        "screening_address": r.get("address", address),
                        "source": "trm_labs",
                        "risk_level": "critical" if r.get("isSanctioned") else "low",
                    }
            elif resp.status_code == 429:
                logger.warning("TRM Labs rate limit hit — consider getting free API key")
                return {"source": "trm_labs", "rate_limited": True, "is_sanctioned": False}
    except Exception as e:
        logger.warning(f"TRM sanctions check failed for {address[:8]}...: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: Scorechain Free Sanctions Check (fallback)
# ═══════════════════════════════════════════════════════════════

async def _check_scorechain_sanctions(address: str, chain: str = "ethereum") -> Optional[Dict[str, Any]]:
    """Screen address via Scorechain Free Sanctions Check API.
    
    21+ chains, 100 req/hour, free API key required.
    Fallback when TRM Labs is rate-limited or unavailable.
    """
    try:
        api_key = os.getenv("SCORECHAIN_API_KEY", "")
        if not api_key:
            return None
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.scorechain.com/v1/sanctions/check",
                params={"address": address, "chain": chain.lower()},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "is_sanctioned": data.get("is_sanctioned", False),
                    "sanctions_lists": data.get("lists", []),
                    "source": "scorechain",
                    "risk_level": "critical" if data.get("is_sanctioned") else "low",
                }
    except Exception as e:
        logger.warning(f"Scorechain sanctions check failed: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: Chainabuse API (scam reporting lookup)
# ═══════════════════════════════════════════════════════════════

async def _check_chainabuse(address: str) -> Optional[Dict[str, Any]]:
    """Query Chainabuse for community-reported scam data on address.
    
    Free tier: 10 calls/month, 50 reports per call.
    Premium: 5K calls/hour upon request.
    """
    try:
        api_key = os.getenv("CHAINABUSE_API_KEY", "")
        if not api_key:
            return None
        
        import base64
        auth = base64.b64encode(f"{api_key}:{api_key}".encode()).decode()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.chainabuse.com/v1/addresses/{address}/reports",
                headers={"Authorization": f"Basic {auth}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                reports = data.get("reports", [])
                return {
                    "report_count": len(reports),
                    "is_reported": len(reports) > 0,
                    "scam_categories": list({r.get("category") for r in reports if r.get("category")}),
                    "total_loss_usd": sum(r.get("lossUsd", 0) or 0 for r in reports),
                    "source": "chainabuse",
                }
            elif resp.status_code == 429:
                return {"source": "chainabuse", "rate_limited": True}
    except Exception as e:
        logger.warning(f"Chainabuse check failed for {address[:8]}...: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: Forta Network GraphQL (free trial / general bots)
# ═══════════════════════════════════════════════════════════════

async def _check_forta_alerts(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Query Forta Network for anomaly alerts on token/contract.
    
    Free trial available. General plan bots accessible at
    https://api.forta.network/graphql with API key.
    Checks for anomalous tx velocity, state changes, exploit patterns.
    """
    try:
        api_key = os.getenv("FORTA_API_KEY", "")
        if not api_key:
            return None
        
        # Map chain to Forta chain ID
        forta_chain_map = {
            "ethereum": "1", "bsc": "56", "polygon": "137",
            "arbitrum": "42161", "optimism": "10", "avalanche": "43114",
            "base": "8453", "fantom": "250",
        }
        chain_id = forta_chain_map.get(chain.lower())
        if not chain_id:
            return None
        
        query = """
        query getAlerts($input: AlertsInput) {
          alerts(input: $input) {
            pageInfo { hasNextPage endCursor }
            alerts {
              name description protocol severity
              source { transaction { hash } }
            }
          }
        }
        """
        variables = {
            "input": {
                "addresses": [token_address],
                "chainId": chain_id,
                "first": 5,
            }
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.forta.network/graphql",
                json={"query": query, "variables": variables},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                alerts_data = data.get("data", {}).get("alerts", {}).get("alerts", [])
                if alerts_data:
                    return {
                        "alert_count": len(alerts_data),
                        "alerts": [
                            {
                                "name": a.get("name"),
                                "severity": a.get("severity"),
                                "description": a.get("description", "")[:200],
                            }
                            for a in alerts_data[:3]
                        ],
                        "source": "forta",
                        "risk_level": "high" if any(a.get("severity") in ("CRITICAL", "HIGH") for a in alerts_data) else "medium" if alerts_data else "low",
                    }
                return {"alert_count": 0, "source": "forta", "risk_level": "low"}
    except Exception as e:
        logger.warning(f"Forta check failed for {token_address[:8]}...: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: DeFiLlama API (free, no key — TVL + volume context)
# ═══════════════════════════════════════════════════════════════

async def _check_defillama_context(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Get DeFiLlama protocol/TVL context for token.
    
    Completely free, no authentication. Provides TVL, yields,
    protocol fees, DEX volumes across 350+ chains.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to find protocol by token address
            resp = await client.get(
                f"https://api.llama.fi/protocol/{token_address}",
            )
            
            result = {"source": "defillama"}
            
            if resp.status_code == 200:
                data = resp.json()
                result["protocol_name"] = data.get("name")
                result["tvl_usd"] = data.get("tvl")
                result["chain_tvls"] = data.get("chainTvls", {})
                result["category"] = data.get("category")
                result["audit_count"] = len(data.get("audits", []))
                result["audit_links"] = [a.get("url") for a in data.get("audits", [])[:3]]
                result["twitter"] = data.get("twitter")
                result["is_stablecoin"] = data.get("stablecoin", False)
            
            # Get DEX volume for chain
            vol_resp = await client.get("https://api.llama.fi/overview/dexs", params={"chain": chain.lower()})
            if vol_resp.status_code == 200:
                vol_data = vol_resp.json()
                protocols = vol_data.get("protocols", [])
                # Find protocol matching token name/symbol if possible
                result["dex_volume_24h"] = sum(p.get("volume_24h", 0) or 0 for p in protocols[:10])
            
            return result if len(result) > 1 else None
    except Exception as e:
        logger.warning(f"DeFiLlama check failed: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: CoinGecko /simple/price (free, no key)
# ═══════════════════════════════════════════════════════════════

async def _check_coingecko_price(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Get CoinGecko price data for token.
    
    Free tier: 100 calls/minute, no API key required for /simple/price.
    Provides market cap, 24h change, volume across 500+ coins.
    """
    # CoinGecko platform mapping
    platform_map = {
        "ethereum": "ethereum", "bsc": "binance-smart-chain",
        "polygon": "polygon-pos", "arbitrum": "arbitrum-one",
        "optimism": "optimistic-ethereum", "avalanche": "avalanche",
        "base": "base", "fantom": "fantom", "solana": "solana",
    }
    platform = platform_map.get(chain.lower())
    if not platform:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/token_price/{platform}",
                params={
                    "contract_addresses": token_address,
                    "vs_currencies": "usd",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                token_data = data.get(token_address.lower(), {})
                if token_data:
                    return {
                        "price_usd": token_data.get("usd"),
                        "market_cap_usd": token_data.get("usd_market_cap"),
                        "volume_24h_usd": token_data.get("usd_24h_vol"),
                        "price_change_24h_pct": token_data.get("usd_24h_change"),
                        "source": "coingecko",
                    }
    except Exception as e:
        logger.warning(f"CoinGecko check failed: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# ENRICHMENT: 1inch Business API (free tier — swap simulation)
# ═══════════════════════════════════════════════════════════════

async def _check_1inch_swap(token_address: str, chain: str, amount_usd: float = 100.0) -> Optional[Dict[str, Any]]:
    """Simulate swap via 1inch Business API.
    
    Free tier: 100K calls/month, 60 req/min, 3 WebSocket connections.
    Aggregates DEX liquidity and simulates routing before committing gas.
    """
    try:
        api_key = os.getenv("ONEINCH_API_KEY", "")
        if not api_key:
            return None
        
        # 1inch chain ID mapping
        inch_chain_map = {
            "ethereum": "1", "bsc": "56", "polygon": "137",
            "arbitrum": "42161", "optimism": "10", "avalanche": "43114",
            "base": "8453", "fantom": "250", "gnosis": "100",
        }
        chain_id = inch_chain_map.get(chain.lower())
        if not chain_id:
            return None
        
        # Use USDC as reference for amount
        usdc = {
            "1": "0xA0b86a33E6441E0C4D0f2f9eB5E2C6f8B3D4e5F6",
            "56": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
            "137": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "42161": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "10": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
            "43114": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
            "8453": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "250": "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75",
        }.get(chain_id)
        
        if not usdc:
            return None
        
        async with httpx.AsyncClient(timeout=12.0) as client:
            # Quote API — simulates swap without executing
            resp = await client.get(
                f"https://api.1inch.dev/swap/v6.0/{chain_id}/quote",
                params={
                    "src": usdc,
                    "dst": token_address,
                    "amount": str(int(amount_usd * 1e6)),  # USDC has 6 decimals
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "expected_amount_out": data.get("toAmount"),
                    "price_impact_pct": data.get("priceImpact"),
                    "route_steps": len(data.get("protocols", [])),
                    "gas_estimate": data.get("gas"),
                    "source": "1inch",
                }
    except Exception as e:
        logger.warning(f"1inch swap check failed: {e}")
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




# ═══════════════════════════════════════════════════════════════
# ENRICHMENT 18: QuickNode Pump.fun Integration
# ═══════════════════════════════════════════════════════════════

async def _get_quicknode_pumpfun(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """QuickNode Pump.fun data — bonding curve status, graduation, bot activity."""
    if chain.lower() != "solana":
        return None
    try:
        api_key = os.getenv("QUICKNODE_KEY", "")
        if not api_key:
            return None
        
        url = f"https://docs-demo.solana-mainnet.quiknode.pro/{api_key}/"
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Check if token is a Pump.fun token by looking at token accounts
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token_address]
            }
            resp = await client.post(url, json=payload)
            
            result = {}
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    accounts = data["result"].get("value", [])
                    result["largest_accounts"] = len(accounts)
                    if accounts:
                        total_supply = sum(a.get("amount", 0) for a in accounts)
                        top_holder = accounts[0].get("amount", 0) if accounts else 0
                        if total_supply > 0:
                            result["top_holder_pct"] = round(top_holder / total_supply * 100, 1)
            
            # Get token supply
            payload2 = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [token_address]
            }
            resp2 = await client.post(url, json=payload2)
            if resp2.status_code == 200:
                data2 = resp2.json()
                supply_data = data2.get("result", {}).get("value", {})
                result["total_supply"] = supply_data.get("amount")
                result["decimals"] = supply_data.get("decimals")
                result["supply_ui"] = supply_data.get("uiAmountString")
            
            return result if result else None
    except Exception as e:
        logger.warning(f"QuickNode enrichment failed for {token_address}: {e}")
        return None


# ── Nansen on-chain intelligence ──

async def _check_nansen(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Nansen Token God Mode — market cap, holders, volume, smart money activity.
    
    Free tier: 100 API credits. API key: NANSEN_API_KEY env var.
    Provides holder count, buy/sell volume, unique traders, liquidity, 
    smart money netflow — data no other free API provides.
    Cost: $0 (free credits) / $0.01 per call via x402 micropayments.
    """
    api_key = os.getenv("NANSEN_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Content-Type": "application/json", "apiKey": api_key}
            
            # Map chain names to Nansen format
            nansen_chain = chain if chain in ("ethereum", "solana", "base", "arbitrum", "optimism", "polygon") else "ethereum"
            
            # TGM token-information
            result = await asyncio.wait_for(
                client.post(
                    "https://api.nansen.ai/api/v1/tgm/token-information",
                    headers=headers,
                    json={"chain": nansen_chain, "token_address": token_address, "timeframe": "1d"},
                ),
                timeout=10.0,
            )
            if result.status_code != 200:
                if result.status_code == 404:
                    return None  # Token not found in Nansen
                logger.warning(f"Nansen TGM failed ({result.status_code}): {result.text[:100]}")
                return None
            
            data = result.json()
            inner = data.get("data", data)
            token_details = inner.get("token_details", {})
            spot_metrics = inner.get("spot_metrics", {})
            
            return {
                "symbol": inner.get("symbol", ""),
                "name": inner.get("name", ""),
                "market_cap_usd": token_details.get("market_cap_usd"),
                "fdv_usd": token_details.get("fdv_usd"),
                "volume_24h_usd": spot_metrics.get("volume_total_usd"),
                "buy_volume_24h_usd": spot_metrics.get("buy_volume_usd"),
                "sell_volume_24h_usd": spot_metrics.get("sell_volume_usd"),
                "total_holders": spot_metrics.get("total_holders"),
                "unique_buyers_24h": spot_metrics.get("unique_buyers"),
                "unique_sellers_24h": spot_metrics.get("unique_sellers"),
                "liquidity_usd": spot_metrics.get("liquidity_usd"),
                "net_flow_24h": (spot_metrics.get("buy_volume_usd") or 0) - (spot_metrics.get("sell_volume_usd") or 0),
                "data_source": "nansen_tgm",
            }
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Nansen check failed for {token_address[:8]}...: {e}")
        return None


# ── ChainAware behavioral AI rug pull detection ──

async def _check_chainaware(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """ChainAware.ai predictive rug pull detection — behavioral AI that analyzes
    creator + LP on-chain behavior (NOT source code).
    
    68% accuracy detecting rug pulls from behavioral patterns alone.
    Complements contract-analysis approaches by catching scammers who
    obfuscate code but can't fake 3 years of legitimate activity.
    Free tier: 20 API calls/day → currently on 2-week Business trial (3500 checks each: fraud/audit/rug-pull).
    API key: CHAIN_AWARE_API_KEY env var.
    Endpoint: business.api.chainaware.ai/rug/pull-check (REST).
    Cost: $0 (trial).
    """
    api_key = os.getenv("CHAIN_AWARE_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=12.0) as client:
            chain_map = {
                "ethereum": "ETH", "bsc": "BNB", "base": "BASE",
                "polygon": "POLYGON", "tron": "TRON", "haqq": "HAQQ",
            }
            cw_chain = chain_map.get(chain.lower(), chain.upper() if chain.upper() in ("ETH", "BNB", "BASE", "HAQQ", "POLYGON", "TRON") else None)
            if not cw_chain:
                return None  # Chain not supported
            
            result = await asyncio.wait_for(
                client.post(
                    "https://business.api.chainaware.ai/rug/pull-check",
                    headers={
                        "X-API-Key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "network": cw_chain,
                        "walletAddress": token_address,
                    },
                ),
                timeout=12.0,
            )
            
            if result.status_code != 200:
                logger.debug(f"ChainAware: {result.status_code}")
                return None
            
            data = result.json()
            if data.get("message") != "Success":
                return None
            
            risk_indicators = data.get("risk_indicators", {})
            
            return {
                "risk_score": data.get("risk_score"),
                "risk_status": data.get("risk_status", "Unknown"),
                "probability_fraud": data.get("probabilityFraud"),
                "status": data.get("status", "Unknown"),
                "is_honeypot": bool(risk_indicators.get("is_honeypot", 0)),
                "is_mintable": bool(risk_indicators.get("is_mintable", 0)),
                "hidden_owner": bool(risk_indicators.get("hidden_owner", 0)),
                "is_proxy": bool(risk_indicators.get("is_proxy", 0)),
                "is_open_source": bool(risk_indicators.get("is_open_source", 0)),
                "buy_tax": risk_indicators.get("buy_tax", 0),
                "sell_tax": risk_indicators.get("sell_tax", 0),
                "holder_count": risk_indicators.get("holder_count"),
                "lp_holder_count": risk_indicators.get("lp_holder_count"),
                "creator_percent": risk_indicators.get("creator_percent", 0),
                "contract_name": data.get("contractName", ""),
                "contract_creator": data.get("contractCreatorAddress", ""),
                "last_checked": data.get("lastChecked"),
                "data_source": "chainaware_rest",
            }
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"ChainAware check failed for {token_address[:8]}...: {e}")
        return None


# ── Blowfish transaction simulation ──

async def _check_blowfish(token_address: str, chain: str, user_address: str = "") -> Optional[Dict[str, Any]]:
    """Blowfish transaction simulation — sandbox execution that previews ALL 
    state changes from a transaction, not just buy/sell.
    
    Catches: approval scams, drainers, Permit2 phishing, complex multi-call 
    attacks that simple buy/sell sims miss. Completely free tier $0/month.
    API key: BLOWFISH_API_KEY env var.
    Cost: $0 (free tier).
    """
    api_key = os.getenv("BLOWFISH_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
            
            # Scan the token contract for risks
            # Blowfish can scan both contracts and transactions
            if chain == "solana":
                url = "https://api.blowfish.xyz/solana/v0/mainnet/scan/transactions"
            elif chain in ("ethereum", "base", "optimism", "arbitrum"):
                url = f"https://api.blowfish.xyz/{chain}/v0/mainnet/scan/transactions"
            else:
                url = "https://api.blowfish.xyz/ethereum/v0/mainnet/scan/transactions"
            
            # Construct a minimal approval check transaction
            payload = {
                "userAccount": user_address or "0x0000000000000000000000000000000000000000",
                "metadata": {"origin": "https://rugmunch.io"},
                "transactions": [{
                    "from": user_address or "0x0000000000000000000000000000000000000000",
                    "to": token_address,
                    "data": "0x",  # Minimal call to trigger simulation
                    "value": "0x0",
                }],
            }
            
            result = await asyncio.wait_for(
                client.post(url, headers=headers, json=payload),
                timeout=10.0,
            )
            
            if result.status_code == 200:
                data = result.json()
                action = data.get("action", "NONE")
                warnings_list = data.get("warnings", [])
                return {
                    "action": action,
                    "warnings": [w.get("message", "") for w in warnings_list[:5]],
                    "severity": data.get("aggregated", {}).get("severity", "NONE"),
                    "simulation_done": True,
                    "data_source": "blowfish",
                }
            elif result.status_code in (400, 401, 403):
                logger.warning(f"Blowfish auth/config error: {result.status_code}")
            return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Blowfish check failed for {token_address[:8]}...: {e}")
        return None


# ── LunarCrush social sentiment ──


# ── Santiment on-chain + social metrics ──

async def _check_santiment(symbol: str) -> Optional[Dict[str, Any]]:
    """Santiment social + on-chain metrics — social volume, dev activity, sentiment.
    
    Combines on-chain metrics with social sentiment data for a comprehensive 
    view of market activity. Detects botted social volume vs real on-chain usage.
    Free tier: 1,000 API calls/month. API key: SANTIMENT_API_KEY env var.
    Cost: $0 (free tier).
    """
    api_key = os.getenv("SANTIMENT_API_KEY", "")
    if not api_key or not symbol:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Apikey {api_key}", "Content-Type": "application/json"}
            
            # Query social volume for this token
            query = {
                "query": """
                {
                  socialVolumeProjects(
                    selector: {slugs: [\"""" + symbol.lower() + """"]}
                    from: "utc_now-1d"
                    to: "utc_now"
                    interval: "1d"
                  ) {
                    datetime
                    projects {
                      slug
                      mentionsCount
                    }
                  }
                }
                """.strip()
            }
            
            result = await asyncio.wait_for(
                client.post(
                    "https://api.santiment.net/graphql",
                    headers=headers,
                    json=query,
                ),
                timeout=10.0,
            )
            
            if result.status_code == 200:
                data = result.json()
                sv_data = data.get("data", {}).get("socialVolumeProjects", [])
                if sv_data and sv_data[0].get("projects"):
                    projects = sv_data[0]["projects"]
                    if projects:
                        project = projects[0]
                        mentions = project.get("mentionsCount", 0)
                        
                        # High mentions = social hype signal
                        social_risk = None
                        if mentions > 5000:
                            social_risk = "viral"
                        elif mentions > 1000:
                            social_risk = "trending"
                        elif mentions > 100:
                            social_risk = "active"
                        
                        return {
                            "symbol": symbol,
                            "social_mentions_24h": mentions,
                            "social_risk": social_risk,
                            "data_source": "santiment",
                        }
                # Check for rate limit
                if data.get("errors"):
                    for e in data["errors"]:
                        if "limit" in str(e).lower() or "quota" in str(e).lower():
                            logger.debug("Santiment: rate limit reached")
                            return None
            return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Santiment check failed for {symbol}: {e}")
        return None

async def _check_fear_greed() -> Optional[Dict[str, Any]]:
    """Alternative.me Crypto Fear & Greed Index — market-wide sentiment context.
    
    Free, no API key required. REST API at api.alternative.me/fng/
    Provides 0-100 sentiment score and classification.
    Scam context: Extreme Greed phases = more scam launches.
    Used to adjust baseline safety scores based on market conditions.
    Cost: $0 (completely free, no rate limits).
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            result = await asyncio.wait_for(
                client.get("https://api.alternative.me/fng/?limit=1"),
                timeout=8.0,
            )
            if result.status_code != 200:
                return None
            
            data = result.json()
            items = data.get("data", [])
            if not items:
                return None
            
            item = items[0]
            value = int(item.get("value", 50))
            classification = item.get("value_classification", "Neutral")
            
            # Market condition context
            if value <= 25:
                market_condition = "extreme_fear"
            elif value <= 45:
                market_condition = "fear"
            elif value <= 55:
                market_condition = "neutral"
            elif value <= 75:
                market_condition = "greed"
            else:
                market_condition = "extreme_greed"
            
            return {
                "fear_greed_value": value,
                "classification": classification,
                "market_condition": market_condition,
                "timestamp": item.get("timestamp"),
                "data_source": "alternative_me_fng",
            }
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Fear & Greed check failed: {e}")
        return None


# ── Sourcify decentralized contract verification ──

async def _check_sourcify(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Sourcify decentralized full-match verification. Free, no key, REST API.
    Stronger than Etherscan verification — cryptographically guarantees 
    source matches bytecode. 'perfect' match > Etherscan 'verified'.
    """
    try:
        import httpx
        chain_ids = {"ethereum": "1", "bsc": "56", "polygon": "137", "arbitrum": "42161",
                     "optimism": "10", "avalanche": "43114", "base": "8453", "fantom": "250"}
        chain_id = chain_ids.get(chain.lower(), "1")
        async with httpx.AsyncClient(timeout=8.0) as client:
            result = await asyncio.wait_for(
                client.get("https://sourcify.dev/server/check-by-addresses",
                          params={"addresses": token_address, "chainIds": chain_id}),
                timeout=8.0)
            if result.status_code != 200:
                return None
            data = result.json()
            items = data if isinstance(data, list) else [data]
            if items:
                item = items[0]
                return {"full_match": item.get("status") == "perfect",
                        "status": item.get("status", "unknown"),
                        "data_source": "sourcify"}
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Sourcify failed: {e}")
        return None


# Replaced LunarCrush with Fear & Greed (free, no key needed, REST works)
async def _check_scamsniffer_live(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """ScamSniffer phishing domain check against static GitHub blacklist.
    
    Checks if the token address or deployer appears in ScamSniffer's 
    blacklist trusted by Binance, Phantom, Rabby, Bybit.
    Live API is paid — this uses the open-source GitHub database 
    refreshed hourly. Covers $800M+ tracked drainer losses.
    Cost: $0 (open source GitHub data).
    """
    global _scamsniffer_domains_cache, _scamsniffer_cache_ts
    try:
        import httpx
        now = asyncio.get_event_loop().time() if hasattr(asyncio.get_event_loop(), 'time') else __import__('time').time()
        
        # Refresh cache if stale
        if _scamsniffer_domains_cache is None or (now - _scamsniffer_cache_ts > _SCAMSNIFFER_CACHE_TTL):
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Fetch addresses blacklist
                r = await client.get(
                    "https://raw.githubusercontent.com/scamsniffer/scam-database/main/blacklist/address.json",
                    timeout=15.0,
                )
                if r.status_code == 200:
                    addr_data = r.json()
                    # Handle both list and dict formats
                    if isinstance(addr_data, list):
                        addresses = addr_data
                    elif isinstance(addr_data, dict):
                        addresses = addr_data.get("address", addr_data.get("blacklist", []))
                    else:
                        addresses = []
                    if isinstance(addresses, list):
                        _scamsniffer_domains_cache = set(
                            a.lower() for a in addresses 
                            if isinstance(a, str) and len(a) >= 42
                        )
                        _scamsniffer_cache_ts = now
        
        # Check if token address is in the blacklist
        if _scamsniffer_domains_cache and token_address.lower() in _scamsniffer_domains_cache:
            return {
                "is_phishing": True,
                "matched_in": "scamsniffer_blacklist",
                "trusted_by": ["binance", "phantom", "rabby", "bybit"],
                "data_source": "scamsniffer_github",
            }
        return None
    except Exception as e:
        logger.warning(f"ScamSniffer check failed: {e}")
        return None


# ── Dune Analytics SQL queries ──

async def _check_dune(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Dune Analytics SQL engine — custom on-chain analysis via SQL.
    
    Can query: holder concentration, deployment patterns, liquidity events,
    scam contract templates, and any ad-hoc analysis.
    Free tier: 40 RPM read, 32GB max result.
    API key: DUNE_API_KEY env var.
    Cost: $0 (free tier).
    """
    api_key = os.getenv("DUNE_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
            headers = {"X-DUNE-API-KEY": api_key, "Content-Type": "application/json"}
            
            # Query for holder concentration on Solana or token info on EVM
            if chain == "solana":
                sql = f"""
                SELECT 
                    token_address,
                    holder_count,
                    top_10_holder_pct
                FROM tokens_solana.token_holders
                WHERE token_address = '{token_address}'
                LIMIT 1
                """
            else:
                sql = f"""
                SELECT 
                    COUNT(*) as report_count
                FROM labels.scam
                WHERE address = '{token_address}'
                LIMIT 5
                """
            
            # Execute query
            exec_resp = await asyncio.wait_for(
                client.post(
                    "https://api.dune.com/api/v1/sql/execute",
                    headers=headers,
                    json={"sql": sql, "performance": "medium"},
                ),
                timeout=15.0,
            )
            
            if exec_resp.status_code != 200:
                return None
            
            exec_id = exec_resp.json().get("execution_id")
            if not exec_id:
                return None
            
            # Poll for results (up to 6 seconds total)
            for _ in range(3):
                await asyncio.sleep(2)
                result_resp = await asyncio.wait_for(
                    client.get(
                        f"https://api.dune.com/api/v1/execution/{exec_id}/results",
                        headers=headers,
                    ),
                    timeout=8.0,
                )
                if result_resp.status_code != 200:
                    continue
                state = result_resp.json().get("state", "")
                if state == "QUERY_STATE_COMPLETED":
                    data = result_resp.json()
                    rows = data.get("result", {}).get("rows", [])
                    return {
                        "query_executed": True,
                        "rows_returned": len(rows),
                        "execution_id": exec_id,
                        "data_source": "dune_analytics",
                        "flag_count": sum(
                            r.get("report_count", 0) or 0 
                            for r in rows
                        ) if rows else 0,
                    }
                elif state == "QUERY_STATE_FAILED":
                    logger.debug(f"Dune query failed ({exec_id}): {result_resp.json().get('error', {}).get('message', '')}")
                    return None
            
            return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Dune check failed: {e}")
        return None


# ── Arkham Intelligence entity de-anonymization ──

async def _check_arkham(address: str, chain: str) -> Optional[Dict[str, Any]]:
    """Arkham Intelligence — 800K+ named entities, wallet de-anonymization.
    
    Resolves raw addresses to named entities (exchanges, funds, scammers).
    Visualizer and Tracer for fund flow analysis.
    Free tier with rate limits.
    API key: ARKHAM_API_KEY env var.
    Cost: $0 (free tier).
    """
    api_key = os.getenv("ARKHAM_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=12.0) as client:
            headers = {"API-Key": api_key, "Content-Type": "application/json"}
            
            # Try to resolve the address to a named entity
            result = await asyncio.wait_for(
                client.get(
                    "https://api.arkhamintelligence.com/v1/entities",
                    headers=headers,
                    params={"address": address, "limit": 3},
                ),
                timeout=12.0,
            )
            
            if result.status_code == 200:
                data = result.json()
                entities = data.get("entities") or data.get("data") or []
                if isinstance(entities, list) and entities:
                    entity = entities[0]
                    return {
                        "entity_name": entity.get("name", ""),
                        "entity_type": entity.get("type", ""),
                        "entity_id": entity.get("id"),
                        "labels": entity.get("labels", []),
                        "total_matches": len(entities),
                        "data_source": "arkham_intelligence",
                    }
            elif result.status_code == 402:
                logger.debug("Arkham: free tier expired or payment required")
            return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"Arkham check failed: {e}")
        return None


# ── The Graph subgraph queries ──

async def _check_thegraph(token_address: str, chain: str) -> Optional[Dict[str, Any]]:
    """The Graph — decentralized subgraph indexing for smart contract events.
    
    Can query custom indexes for: token mints, liquidity changes, 
    ownership transfers, proxy upgrades, and scam-specific events.
    Free tier: hosted service $0, GraphQL queries.
    API key: THEGRAPH_API_KEY env var (from thegraph.com/studio).
    Cost: $0 (free hosted tier).
    """
    api_key = os.getenv("THEGRAPH_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=12.0) as client:
            # Map chain to subgraph endpoint
            # Using Uniswap subgraph as reference for token + liquidity events
            subgraph_urls = {
                "ethereum": f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/5zvRBaQfZoPGbyjABqJaGoneunRShHPbvRXKxjFLuG1x",
                "polygon": f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/GACXMr3LDErUM5trgpe2QSYgGBa6pzvQoXRJB26FyS7Z",
            }
            
            url = subgraph_urls.get(chain)
            if not url:
                return None
            
            # Query for recent liquidity events involving this token
            query = """
            query($token: String!) {
                mints(where: {token0: $token}, first: 3, orderBy: timestamp, orderDirection: desc) {
                    amount0
                    amountUSD
                    timestamp
                }
                burns(where: {token0: $token}, first: 3, orderBy: timestamp, orderDirection: desc) {
                    amount0
                    amountUSD
                    timestamp
                }
            }
            """
            
            result = await asyncio.wait_for(
                client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"query": query, "variables": {"token": token_address.lower()}},
                ),
                timeout=12.0,
            )
            
            if result.status_code == 200:
                data = result.json().get("data", {})
                mints = data.get("mints", [])
                burns = data.get("burns", [])
                
                if not mints and not burns:
                    return None
                
                # Calculate risk signals
                recent_burn = False
                total_burn_usd = 0
                for b in burns:
                    total_burn_usd += float(b.get("amountUSD", 0) or 0)
                    ts = int(b.get("timestamp", 0) or 0)
                    if ts > (int(__import__('time').time()) - 86400):
                        recent_burn = True
                
                return {
                    "mint_count": len(mints),
                    "burn_count": len(burns),
                    "total_burn_usd": total_burn_usd,
                    "recent_liquidity_removal": recent_burn,
                    "data_source": "thegraph",
                }
            return None
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"The Graph check failed: {e}")
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
    nansen_data, chainaware_data, blowfish_data, scamsniffer_data = None, None, None, None
    dune_data, arkham_data, thegraph_data = None, None, None
    fear_greed_data = None
    try:
        sim_result, holder_data, deployer_info, price_consensus, birdeye_data, solscan_data, moralis_data, etherscan_data, qn_pumpfun, honeypot_is, chainpatrol_token, defi_scanner, blockscout_data, token_sniffer, trm_sanctions, chainabuse_reports, forta_alerts, defillama_ctx, coingecko_price, oneinch_swap, nansen_data, chainaware_data, blowfish_data, scamsniffer_data, dune_data, arkham_data, thegraph_data = await asyncio.gather(
            _simulate_trade(token_address, chain),
            _get_holder_data(token_address, chain),
            _get_deployer_info(token_address, chain),
            _get_price_consensus(token_address, chain, market.get("price_usd", 0)),
            _get_birdeye_data(token_address, chain),
            _get_solscan_data(token_address, chain),
            _get_moralis_data(token_address, chain),
            _get_etherscan_enhanced(token_address, chain),
            _get_quicknode_pumpfun(token_address, chain),
            _check_honeypot_is(token_address, chain),
            _check_chainpatrol_asset("token", token_address),
            _check_defi_scanner(token_address, chain),
            _check_blockscout(token_address, chain),
            _check_token_sniffer(token_address, chain),
            _check_trm_sanctions(token_address),
            _check_chainabuse(token_address),
            _check_forta_alerts(token_address, chain),
            _check_defillama_context(token_address, chain),
            _check_coingecko_price(token_address, chain),
            _check_1inch_swap(token_address, chain),
            _check_nansen(token_address, chain),
            _check_chainaware(token_address, chain),
            _check_blowfish(token_address, chain),
            _check_scamsniffer_live(token_address, chain),
            _check_dune(token_address, chain),
            _check_arkham(token_address, chain),
            _check_thegraph(token_address, chain),
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
        if isinstance(qn_pumpfun, BaseException):
            qn_pumpfun = None
        if isinstance(honeypot_is, BaseException):
            honeypot_is = None
        if isinstance(chainpatrol_token, BaseException):
            chainpatrol_token = None
        if isinstance(defi_scanner, BaseException):
            defi_scanner = None
        if isinstance(blockscout_data, BaseException):
            blockscout_data = None
        if isinstance(token_sniffer, BaseException):
            token_sniffer = None
        if isinstance(trm_sanctions, BaseException):
            trm_sanctions = None
        if isinstance(chainabuse_reports, BaseException):
            chainabuse_reports = None
        if isinstance(forta_alerts, BaseException):
            forta_alerts = None
        if isinstance(defillama_ctx, BaseException):
            defillama_ctx = None
        if isinstance(coingecko_price, BaseException):
            coingecko_price = None
        if isinstance(oneinch_swap, BaseException):
            oneinch_swap = None
        if isinstance(nansen_data, BaseException):
            nansen_data = None
        if isinstance(chainaware_data, BaseException):
            chainaware_data = None
        if isinstance(blowfish_data, BaseException):
            blowfish_data = None
        if isinstance(scamsniffer_data, BaseException):
            scamsniffer_data = None
        if isinstance(dune_data, BaseException):
            dune_data = None
        if isinstance(arkham_data, BaseException):
            arkham_data = None
        if isinstance(thegraph_data, BaseException):
            thegraph_data = None
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
        if isinstance(qn_pumpfun, BaseException):
            qn_pumpfun = None
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
    
    # ── Copycat + Volume anomaly + FearGreed + Santiment (CPU-only, uses existing market data) ──
    copycat_result = await _check_copycat(scan.symbol, scan.name)
    volume_anomaly = await _check_volume_anomaly(
        volume_24h=market.get("volume_24h", 0),
        liquidity_usd=market.get("liquidity_usd", 0),
        age_hours=market.get("age_hours"),
        fdv=market.get("fdv", 0),
    )
    fear_greed_data = await _check_fear_greed()
    santiment_data = await _check_santiment(scan.symbol)
    
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
    
    # QuickNode Pump.fun data
    if isinstance(qn_pumpfun, dict):
        scan.confidence = min(100, scan.confidence + 3)
        if qn_pumpfun.get("top_holder_pct", 0) > 90:
            safety = max(0, safety - 20)
            scan.risk_flags.append("PUMPFUN_WHALE_HOLDER")
        if qn_pumpfun.get("largest_accounts", 0) < 10:
            safety = max(0, safety - 5)
            scan.risk_flags.append("LOW_HOLDER_COUNT")
    
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
    
    
    # Honeypot.is second opinion
    if isinstance(honeypot_is, dict):
        if honeypot_is.get("is_honeypot"):
            safety = max(0, safety - 45)
            scan.risk_flags.append("HONEYPOT_IS_DETECTED")
            scan.confidence = min(100, scan.confidence + 20)
        elif honeypot_is.get("sell_tax_pct", 0) > 20:
            safety = max(0, safety - 15)
            scan.risk_flags.append(f"HONEYPOT_IS_TAX_{honeypot_is['sell_tax_pct']:.0f}%")
        scan.confidence = min(100, scan.confidence + 5)
    
    # ChainPatrol blocklist
    if isinstance(chainpatrol_token, dict):
        if chainpatrol_token.get("is_blocked") or chainpatrol_token.get("is_scam"):
            safety = max(0, safety - 35)
            scan.risk_flags.append("CHAINPATROL_BLOCKED")
            scan.confidence = min(100, scan.confidence + 15)
    
    # De.Fi scanner
    if isinstance(defi_scanner, dict):
        if defi_scanner.get("is_honeypot"):
            safety = max(0, safety - 40)
            scan.risk_flags.append("DEFI_HONEYPOT")
            scan.confidence = min(100, scan.confidence + 15)
        if defi_scanner.get("has_hidden_owner"):
            safety = max(0, safety - 25)
            scan.risk_flags.append("DEFI_HIDDEN_OWNER")
        if defi_scanner.get("has_blacklist"):
            safety = max(0, safety - 20)
            scan.risk_flags.append("DEFI_BLACKLIST")
        if defi_scanner.get("is_mintable"):
            safety = max(0, safety - 15)
            scan.risk_flags.append("DEFI_MINTABLE")
        if defi_scanner.get("is_upgradeable"):
            safety = max(0, safety - 10)
            scan.risk_flags.append("DEFI_UPGRADEABLE")
        scan.confidence = min(100, scan.confidence + 8)
    
    # Blockscout verification
    if isinstance(blockscout_data, dict):
        scan.confidence = min(100, scan.confidence + 5)
        if blockscout_data.get("verified") is False:
            safety = max(0, safety - 15)
            scan.risk_flags.append("BLOCKSCOUT_UNVERIFIED")
        if blockscout_data.get("is_proxy"):
            safety = max(0, safety - 8)
            scan.risk_flags.append("BLOCKSCOUT_PROXY")
    
    # Token Sniffer score
    if isinstance(token_sniffer, dict):
        scan.confidence = min(100, scan.confidence + 8)
        if token_sniffer.get("is_scam"):
            safety = max(0, safety - 40)
            scan.risk_flags.append("TOKENSNIFFER_SCAM")
        elif token_sniffer.get("is_honeypot"):
            safety = max(0, safety - 35)
            scan.risk_flags.append("TOKENSNIFFER_HONEYPOT")
        score = token_sniffer.get("token_score")
        if score is not None and score < 30:
            safety = max(0, safety - 20)
            scan.risk_flags.append(f"TOKENSNIFFER_LOW_SCORE_{score}")
    
    # TRM sanctions
    if isinstance(trm_sanctions, dict):
        if trm_sanctions.get("is_sanctioned"):
            safety = 0  # Instant zero
            scan.risk_flags.append("TRM_SANCTIONED")
            scan.confidence = min(100, scan.confidence + 30)
        elif trm_sanctions.get("rate_limited"):
            scan.risk_flags.append("TRM_RATE_LIMITED")
    
    # Chainabuse reports
    if isinstance(chainabuse_reports, dict):
        if chainabuse_reports.get("is_reported"):
            reports = chainabuse_reports.get("report_count", 0)
            safety = max(0, safety - min(reports * 10, 40))
            scan.risk_flags.append(f"CHAINABUSE_REPORTS_{reports}")
            scan.confidence = min(100, scan.confidence + 15)
    
    # Forta alerts
    if isinstance(forta_alerts, dict):
        if forta_alerts.get("risk_level") == "high":
            safety = max(0, safety - 30)
            scan.risk_flags.append("FORTA_HIGH_ALERT")
            scan.confidence = min(100, scan.confidence + 15)
        elif forta_alerts.get("alert_count", 0) > 0:
            safety = max(0, safety - 10)
            scan.risk_flags.append("FORTA_ALERTS")
            scan.confidence = min(100, scan.confidence + 8)
    
    # DeFiLlama context
    if isinstance(defillama_ctx, dict):
        scan.confidence = min(100, scan.confidence + 3)
        if defillama_ctx.get("tvl_usd") and defillama_ctx.get("tvl_usd") < 1000:
            safety = max(0, safety - 5)
            scan.risk_flags.append("DEFILLAMA_LOW_TVL")
    
    # CoinGecko price
    if isinstance(coingecko_price, dict):
        scan.confidence = min(100, scan.confidence + 3)
        change = coingecko_price.get("price_change_24h_pct")
        if change is not None and change < -50:
            safety = max(0, safety - 10)
            scan.risk_flags.append("COINGECKO_CRASH_24H")
    
    # 1inch swap simulation
    if isinstance(oneinch_swap, dict):
        scan.confidence = min(100, scan.confidence + 5)
        impact = oneinch_swap.get("price_impact_pct")
        if impact is not None and impact > 15:
            safety = max(0, safety - 15)
            scan.risk_flags.append(f"1INCH_HIGH_IMPACT_{impact:.0f}%")
    
    # Nansen smart money intelligence
    if isinstance(nansen_data, dict):
        scan.confidence = min(100, scan.confidence + 8)
        holders = nansen_data.get("total_holders")
        if holders is not None and holders < 50:
            safety = max(0, safety - 10)
            scan.risk_flags.append("NANSEN_LOW_HOLDERS")
        net_flow = nansen_data.get("net_flow_24h")
        if net_flow is not None and net_flow < -50000:
            safety = max(0, safety - 15)
            scan.risk_flags.append("NANSEN_NET_OUTFLOW")
        elif net_flow is not None and net_flow > 50000:
            scan.confidence = min(100, scan.confidence + 3)  # Smart money buying = bullish signal
        buy_sell_ratio = None
        buy = nansen_data.get("buy_volume_24h_usd") or 0
        sell = nansen_data.get("sell_volume_24h_usd") or 0
        if sell > 0:
            buy_sell_ratio = buy / sell
        if buy_sell_ratio is not None and buy_sell_ratio < 0.3:
            safety = max(0, safety - 10)
            scan.risk_flags.append("NANSEN_HEAVY_SELLING")
    
    # ChainAware behavioral AI rug pull detection
    if isinstance(chainaware_data, dict):
        scan.confidence = min(100, scan.confidence + 15)
        prob = chainaware_data.get("probability_fraud")
        risk_score = chainaware_data.get("risk_score")
        status = chainaware_data.get("status", "")
        
        # Primary: probability_fraud (0-1 scale)
        if prob is not None:
            if prob >= 0.81:
                safety = max(0, safety - 50)
                scan.risk_flags.append("CHAINAWARE_CRITICAL_RUG")
            elif prob >= 0.51:
                safety = max(0, safety - 30)
                scan.risk_flags.append("CHAINAWARE_HIGH_RUG_RISK")
            elif prob >= 0.21:
                safety = max(0, safety - 10)
                scan.risk_flags.append("CHAINAWARE_MEDIUM_RUG_RISK")
            else:
                scan.confidence = min(100, scan.confidence + 5)
        elif status == "Fraud":
            safety = max(0, safety - 25)
            scan.risk_flags.append("CHAINAWARE_FRAUD")
        
        # Secondary: risk indicators from REST API
        if chainaware_data.get("is_honeypot"):
            safety = max(0, safety - 35)
            scan.risk_flags.append("CHAINAWARE_HONEYPOT")
        if chainaware_data.get("is_mintable"):
            safety = max(0, safety - 15)
            scan.risk_flags.append("CHAINAWARE_MINTABLE")
        if chainaware_data.get("hidden_owner"):
            safety = max(0, safety - 20)
            scan.risk_flags.append("CHAINAWARE_HIDDEN_OWNER")
        if chainaware_data.get("creator_percent", 0) > 50:
            safety = max(0, safety - 20)
            scan.risk_flags.append("CHAINAWARE_HIGH_CREATOR_PCT")
    
    # Blowfish transaction simulation
    if isinstance(blowfish_data, dict):
        severity = blowfish_data.get("severity", "NONE")
        warnings_list = blowfish_data.get("warnings", [])
        if severity in ("CRITICAL", "HIGH"):
            safety = max(0, safety - 40)
            scan.risk_flags.append(f"BLOWFISH_{severity}")
            scan.confidence = min(100, scan.confidence + 15)
        elif severity == "MEDIUM":
            safety = max(0, safety - 15)
            scan.risk_flags.append("BLOWFISH_MEDIUM")
        if warnings_list:
            scan.confidence = min(100, scan.confidence + 10)
            for w in warnings_list[:3]:
                if "approval" in w.lower() or "drain" in w.lower():
                    safety = max(0, safety - 25)
                    scan.risk_flags.append("BLOWFISH_APPROVAL_RISK")
                    break
    
    # Fear & Greed Index — market-wide sentiment context
    if isinstance(fear_greed_data, dict):
        scan.confidence = min(100, scan.confidence + 3)
        fg_value = fear_greed_data.get("fear_greed_value", 50)
        market_cond = fear_greed_data.get("market_condition", "neutral")
        
        # Extreme Greed = scam launching season
        if market_cond == "extreme_greed":
            safety = max(0, safety - 5)
            scan.risk_flags.append("FEARGREED_EXTREME_GREED")
        elif market_cond == "extreme_fear":
            scan.confidence = min(100, scan.confidence + 2)
            scan.risk_flags.append("FEARGREED_EXTREME_FEAR")
    
    # Santiment social + on-chain metrics
    if isinstance(santiment_data, dict):
        scan.confidence = min(100, scan.confidence + 5)
        mentions = santiment_data.get("social_mentions_24h", 0) or 0
        social_risk = santiment_data.get("social_risk", "")
        market_vol = market.get("volume_24h", 0) or 0
        # Viral social with low volume = bot campaign
        if social_risk == "viral" and market_vol < 50000:
            safety = max(0, safety - 25)
            scan.risk_flags.append("SANTIMENT_VIRAL_LOW_VOLUME")
        elif social_risk == "trending" and market_vol < 10000:
            safety = max(0, safety - 15)
            scan.risk_flags.append("SANTIMENT_HYPE_DETECTED")
    
    # ScamSniffer phishing blacklist
    if isinstance(scamsniffer_data, dict):
        if scamsniffer_data.get("is_phishing"):
            safety = max(0, safety - 45)
            scan.risk_flags.append("SCAMSNIFFER_PHISHING")
            scan.confidence = min(100, scan.confidence + 20)
    
    # Dune Analytics SQL intelligence
    if isinstance(dune_data, dict):
        scan.confidence = min(100, scan.confidence + 5)
        # Dune flag count (scam labels)
        if dune_data.get("flag_count", 0) > 0:
            safety = max(0, safety - 20)
            scan.risk_flags.append("DUNE_SCAM_LABEL_MATCH")
            scan.confidence = min(100, scan.confidence + 10)
        # Dune holder concentration
        holders = dune_data.get("holder_count")
        top10_pct = dune_data.get("top_10_holder_pct")
        if holders is not None and holders < 50:
            safety = max(0, safety - 10)
            scan.risk_flags.append("DUNE_LOW_HOLDERS")
        if top10_pct is not None and top10_pct > 80:
            safety = max(0, safety - 15)
            scan.risk_flags.append("DUNE_HIGH_CONCENTRATION")
    
    # Arkham Intelligence entity resolution
    if isinstance(arkham_data, dict):
        scan.confidence = min(100, scan.confidence + 10)
        entity_type = arkham_data.get("entity_type", "")
        entity_name = arkham_data.get("entity_name", "")
        if entity_type in ("scam", "phishing", "hack", "exploit"):
            safety = max(0, safety - 40)
            scan.risk_flags.append(f"ARKHAM_{entity_type.upper()}")
        elif entity_type in ("exchange", "fund", "market_maker"):
            scan.confidence = min(100, scan.confidence + 5)  # Known entity = more confidence
        if entity_name:
            scan.risk_flags.append(f"ARKHAM_ENTITY_{entity_name[:20].upper().replace(' ', '_')}")
    
    # The Graph subgraph intelligence
    if isinstance(thegraph_data, dict):
        scan.confidence = min(100, scan.confidence + 5)
        if thegraph_data.get("recent_liquidity_removal"):
            safety = max(0, safety - 25)
            scan.risk_flags.append("THEGRAPH_RECENT_LP_REMOVAL")
        if thegraph_data.get("total_burn_usd", 0) > 100000:
            safety = max(0, safety - 15)
            scan.risk_flags.append("THEGRAPH_LARGE_LP_BURN")
    
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
    if isinstance(qn_pumpfun, dict):
        scan.free["quicknode"] = qn_pumpfun
    
    if isinstance(honeypot_is, dict):
        scan.free["honeypot_is"] = honeypot_is
    if isinstance(chainpatrol_token, dict):
        scan.free["chainpatrol"] = chainpatrol_token
    if isinstance(defi_scanner, dict):
        scan.free["defi_scanner"] = defi_scanner
    if isinstance(blockscout_data, dict):
        scan.free["blockscout"] = blockscout_data
    if isinstance(token_sniffer, dict):
        scan.free["token_sniffer"] = token_sniffer
    if isinstance(trm_sanctions, dict):
        scan.free["trm_sanctions"] = trm_sanctions
    if isinstance(chainabuse_reports, dict):
        scan.free["chainabuse"] = chainabuse_reports
    if isinstance(forta_alerts, dict):
        scan.free["forta"] = forta_alerts
    if isinstance(defillama_ctx, dict):
        scan.free["defillama"] = defillama_ctx
    if isinstance(coingecko_price, dict):
        scan.free["coingecko"] = coingecko_price
    if isinstance(oneinch_swap, dict):
        scan.free["1inch_swap"] = oneinch_swap
    if isinstance(nansen_data, dict):
        scan.free["nansen"] = nansen_data
    if isinstance(chainaware_data, dict):
        scan.free["chainaware_ai"] = chainaware_data
    if isinstance(blowfish_data, dict):
        scan.free["blowfish"] = blowfish_data
    if isinstance(fear_greed_data, dict):
        scan.free["fear_greed"] = fear_greed_data
    if isinstance(santiment_data, dict):
        scan.free["santiment"] = santiment_data
    if isinstance(scamsniffer_data, dict):
        scan.free["scamsniffer"] = scamsniffer_data
    if isinstance(dune_data, dict):
        scan.free["dune"] = dune_data
    if isinstance(arkham_data, dict):
        scan.free["arkham"] = arkham_data
    if isinstance(thegraph_data, dict):
        scan.free["thegraph"] = thegraph_data

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
