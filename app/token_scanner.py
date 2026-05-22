"""
Unified Token Scanner — RugMunch Intelligence
==============================================
Ties together all existing infrastructure:
- Bundle detection (degen_scan_endpoint)
- Contract scanning (contract_deepscan — Slither/Mythril)
- Security audit (GoPlus + Birdeye)
- Wallet intelligence (GMGN, Helius, entity labeler)
- Cluster analysis (entity_clustering)
- Whale tracking (Helius whale watcher)
- Sniper detection (Helius sniper detector)
- Holder analysis (Helius syndicate tracker)

FREE tier: basic safety check, liquidity, age, taxes
PRO tier ($15/mo): full bundle analysis, wallet clustering, holder distribution
ELITE tier ($100/mo): ML anomaly detection, mempool monitoring, cross-chain tracing
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ─── SCAN TIERS ──────────────────────────────────────────────────

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
    
    # Overall scores
    safety_score: int = 0  # 0-100, higher = safer
    risk_flags: List[str] = field(default_factory=list)
    tier_required: str = "free"  # free, pro, elite


# ─── CHAIN CONFIG ─────────────────────────────────────────────────

CHAIN_IDS = {
    "solana": "solana",
    "ethereum": "1", "base": "8453", "bsc": "56",
    "arbitrum": "42161", "polygon": "137", "avalanche": "43114",
    "optimism": "10", "fantom": "250", "linea": "59144",
    "zksync": "324", "scroll": "534352", "mantle": "5000",
}


async def free_scan(token_address: str, chain: str) -> Dict[str, Any]:
    """FREE tier scan — basic safety + liquidity + age."""
    import httpx
    result = {
        "token": token_address,
        "chain": chain,
        "liquidity_usd": 0,
        "volume_24h": 0,
        "price_usd": 0,
        "age_hours": None,
        "created_at": None,
        "fdv": 0,
        "holders": None,
        "honeypot_risk": "unknown",
        "buy_tax": 0,
        "sell_tax": 0,
        "mint_authority": "unknown",
        "freeze_authority": "unknown",
        "lp_burned": "unknown",
        "dex": "",
        "pair_address": "",
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # DexScreener data
        try:
            resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}")
            if resp.status_code == 200:
                pairs = resp.json().get("pairs", [])
                if pairs:
                    pair = pairs[0]
                    result["dex"] = pair.get("dexId", "")
                    result["pair_address"] = pair.get("pairAddress", "")
                    result["liquidity_usd"] = float(pair.get("liquidity", {}).get("usd", 0))
                    result["volume_24h"] = float(pair.get("volume", {}).get("h24", 0))
                    result["price_usd"] = float(pair.get("priceUsd", 0))
                    result["fdv"] = float(pair.get("fdv", 0))
                    created = pair.get("pairCreatedAt")
                    if created:
                        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(created / 1000, tz=timezone.utc)).total_seconds() / 3600
                        result["age_hours"] = round(age, 1)
                        result["created_at"] = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat()
        except Exception as e:
            logger.warning(f"DexScreener failed for {token_address}: {e}")
        
        # GoPlus Security
        chain_id = CHAIN_IDS.get(chain, chain)
        try:
            resp = await client.get(
                f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}",
                params={"contract_addresses": token_address}
            )
            if resp.status_code == 200:
                data = resp.json().get("result", {}).get(token_address.lower(), {})
                if data:
                    result["honeypot_risk"] = "high" if data.get("is_honeypot") == "1" else "low"
                    result["buy_tax"] = float(data.get("buy_tax", "0"))
                    result["sell_tax"] = float(data.get("sell_tax", "0"))
                    result["mint_authority"] = "active" if data.get("is_mintable") == "1" else "renounced"
                    result["freeze_authority"] = "active" if data.get("transfer_pausable") == "1" else "none"
                    result["lp_burned"] = "yes" if data.get("lp_holders") and float(data.get("lp_holders", "0")) < 0.01 else "no"
        except Exception as e:
            logger.warning(f"GoPlus failed for {token_address}: {e}")
    
    return result


async def pro_scan(token_address: str, chain: str) -> Dict[str, Any]:
    """PRO tier — bundle detection + wallet clustering + holder analysis."""
    result = {
        "bundle_analysis": {"is_bundled": False, "bundle_wallets": [], "confidence": 0},
        "wallet_clusters": [],
        "holder_distribution": {"top10_pct": 0, "top50_pct": 0, "total_holders": 0},
        "dev_wallets": [],
        "sniper_activity": {"snipers_detected": 0, "sniper_wallets": []},
        "whale_activity": {"whales_detected": 0, "whale_wallets": []},
    }
    
    try:
        # Bundle detection from existing degen scanner
        from app.degen_scan_endpoint import check_bundler as bundle_check
        bundle_result = await bundle_check(token_address, chain)
        if bundle_result:
            result["bundle_analysis"] = {
                "is_bundled": bundle_result.get("is_bundled", False),
                "bundle_wallets": bundle_result.get("wallets", []),
                "confidence": bundle_result.get("confidence", 0),
            }
    except Exception as e:
        logger.warning(f"Bundle check failed: {e}")
    
    try:
        # Entity clustering
        from app.entity_clustering import EntityClusteringEngine
        engine = EntityClusteringEngine()
        clusters = engine.find_clusters(token_address)
        result["wallet_clusters"] = clusters or []
    except Exception as e:
        logger.warning(f"Clustering failed: {e}")
    
    try:
        # GMGN wallet intelligence
        from app.gmgn_client import GMGNClient
        gmgn = GMGNClient()
        wallet_data = await gmgn.get_wallet_intelligence(token_address)
        if wallet_data:
            result["dev_wallets"] = wallet_data.get("dev_wallets", [])
            result["sniper_activity"] = wallet_data.get("sniper_data", {})
            result["whale_activity"] = wallet_data.get("whale_data", {})
            result["holder_distribution"] = wallet_data.get("holder_distribution", {})
    except Exception as e:
        logger.warning(f"GMGN failed: {e}")
    
    return result


async def elite_scan(token_address: str, chain: str) -> Dict[str, Any]:
    """ELITE tier — ML anomaly detection + mempool + cross-chain."""
    result = {
        "ml_anomaly": {"anomaly_detected": False, "anomaly_score": 0, "patterns": []},
        "mempool_activity": {"pending_txs": 0, "sandwich_risk": "low"},
        "cross_chain": {"linked_wallets": [], "funding_source": None},
        "contract_deepscan": {"vulnerabilities": [], "risk_level": "unknown"},
        "exchange_flow": {"inflow_24h": 0, "outflow_24h": 0, "net_flow": 0},
    }
    
    try:
        from app.ml_anomaly import detect_token_anomaly
        anomaly = await detect_token_anomaly(token_address, chain)
        if anomaly:
            result["ml_anomaly"] = anomaly
    except Exception as e:
        logger.warning(f"ML anomaly failed: {e}")
    
    try:
        from app.contract_deepscan import deep_scan_contract
        scan = deep_scan_contract(token_address, chain)
        if scan:
            result["contract_deepscan"] = {
                "vulnerabilities": scan.get("findings", []),
                "risk_level": scan.get("risk_level", "unknown"),
            }
    except Exception as e:
        logger.warning(f"Contract deepscan failed: {e}")
    
    try:
        from app.mempool_sentinel import SentinelManager
        sentinel = SentinelManager()
        mempool = await sentinel.check_token(token_address, chain)
        if mempool:
            result["mempool_activity"] = mempool
    except Exception as e:
        logger.warning(f"Mempool check failed: {e}")
    
    try:
        from app.exchange_flow_analyzer import analyze_token_flows
        flows = await analyze_token_flows(token_address, chain)
        if flows:
            result["exchange_flow"] = flows
    except Exception as e:
        logger.warning(f"Flow analysis failed: {e}")
    
    return result


# ─── UNIFIED SCAN ─────────────────────────────────────────────────

async def scan_token(
    token_address: str,
    chain: str = "solana",
    tier: str = "free",
    user_id: Optional[str] = None,
) -> ScanResult:
    """Unified token scan — runs free tier always, pro/elite if subscribed."""
    
    scan = ScanResult(token_address=token_address, chain=chain)
    
    # FREE — always runs
    free_data = await free_scan(token_address, chain)
    scan.free = free_data
    
    # Calculate base safety score from free data
    risk_flags = []
    safety = 70  # start neutral
    
    if free_data.get("honeypot_risk") == "high":
        safety -= 50
        risk_flags.append("HONEYPOT_DETECTED")
    elif free_data.get("honeypot_risk") == "unknown":
        safety -= 10
    
    if free_data.get("buy_tax", 0) > 10:
        safety -= 15
        risk_flags.append(f"HIGH_BUY_TAX_{free_data['buy_tax']}%")
    if free_data.get("sell_tax", 0) > 10:
        safety -= 15
        risk_flags.append(f"HIGH_SELL_TAX_{free_data['sell_tax']}%")
    
    if free_data.get("mint_authority") == "active":
        safety -= 10
        risk_flags.append("MINTABLE")
    if free_data.get("lp_burned") == "no":
        safety -= 10
        risk_flags.append("LP_NOT_BURNED")
    
    if free_data.get("liquidity_usd", 0) < 1000:
        safety -= 15
        risk_flags.append("LOW_LIQUIDITY")
    if free_data.get("age_hours") and free_data["age_hours"] < 1:
        safety -= 5
        risk_flags.append("VERY_NEW")
    
    scan.safety_score = max(0, min(100, safety))
    scan.risk_flags = risk_flags
    
    # PRO tier
    if tier in ("pro", "elite"):
        pro_data = await pro_scan(token_address, chain)
        scan.pro = pro_data
        scan.tier_required = "pro"
        
        if pro_data.get("bundle_analysis", {}).get("is_bundled"):
            safety -= 20
            risk_flags.append("BUNDLED_SUPPLY")
        
        snipers = pro_data.get("sniper_activity", {}).get("snipers_detected", 0)
        if snipers > 3:
            safety -= 10
            risk_flags.append(f"SNIPER_ACTIVITY_{snipers}")
    
    # ELITE tier
    if tier == "elite":
        elite_data = await elite_scan(token_address, chain)
        scan.elite = elite_data
        scan.tier_required = "elite"
        
        if elite_data.get("ml_anomaly", {}).get("anomaly_detected"):
            safety -= 15
            risk_flags.append("ML_ANOMALY")
        
        vulns = elite_data.get("contract_deepscan", {}).get("vulnerabilities", [])
        high_sev = [v for v in vulns if v.get("severity") == "high"]
        if high_sev:
            safety -= len(high_sev) * 10
            risk_flags.append(f"CRITICAL_VULNS_{len(high_sev)}")
    
    scan.safety_score = max(0, min(100, safety))
    scan.risk_flags = risk_flags
    
    return scan


# ─── QUICK SCAN (Telegram-friendly) ───────────────────────────────

async def quick_scan_text(token_address: str, chain: str = "solana") -> str:
    """Quick scan returning formatted text for Telegram."""
    scan = await scan_token(token_address, chain, tier="free")
    f = scan.free
    
    safety = scan.safety_score
    emoji = "🟢" if safety > 70 else "🟡" if safety > 40 else "🔴"
    
    lines = [
        f"{emoji} *Token Scan: {f.get('symbol', '???') or '???'}*",
        f"",
        f"📍 Chain: {chain.upper()}",
        f"💰 Price: ${f.get('price_usd', 0):.8f}",
        f"💧 Liquidity: ${f.get('liquidity_usd', 0):,.0f}",
        f"📊 Volume 24h: ${f.get('volume_24h', 0):,.0f}",
        f"⏰ Age: {f.get('age_hours', '?')}h",
        f"",
        f"🛡️ *Safety: {safety}/100*",
    ]
    
    if scan.risk_flags:
        lines.append(f"⚠️ Flags: {', '.join(scan.risk_flags[:5])}")
    
    lines.extend([
        f"",
        f"🔒 Honeypot: {f.get('honeypot_risk', '?')}",
        f"💸 Tax: {f.get('buy_tax', 0)}% buy / {f.get('sell_tax', 0)}% sell",
        f"🔑 Mint: {f.get('mint_authority', '?')}",
        f"🔥 LP: {f.get('lp_burned', '?')}",
        f"",
        f"_Free scan. Upgrade to PRO for bundle detection, whale tracking & more._",
        f"/upgrade for details",
    ])
    
    return "\n".join(lines)


# ─── MULTI-CHAIN DISCOVERY (already in token_discovery.py) ────────
# Re-export for convenience

from app.token_discovery import discover_tokens, MONITORED_CHAINS
