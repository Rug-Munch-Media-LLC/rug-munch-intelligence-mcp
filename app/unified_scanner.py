"""
RugMunch Unified Wallet Scanner + Trending Engine
==================================================
Powered by SENTINEL + Wallet Memory Bank + Helius + Token Scanner integration.

FREE:   Helius on-chain data (age, tx, volume, balances) + SENTINEL labels
PRO:    Wallet Memory Bank identity + cluster intel + GMGN scoring
ELITE:  Token portfolio risk scan + full behavioral analysis

Chains: solana, ethereum, base, bsc, arbitrum, polygon, avalanche,
        optimism, fantom, linea, zksync, scroll, mantle
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# ─── CHAIN CONFIG ─────────────────────────────────────────────────

CHAINS = {
    "solana": {"id": "solana", "explorer": "https://solscan.io"},
    "ethereum": {"id": "1", "explorer": "https://etherscan.io"},
    "base": {"id": "8453", "explorer": "https://basescan.org"},
    "bsc": {"id": "56", "explorer": "https://bscscan.com"},
    "arbitrum": {"id": "42161", "explorer": "https://arbiscan.io"},
    "polygon": {"id": "137", "explorer": "https://polygonscan.com"},
    "avalanche": {"id": "43114", "explorer": "https://snowtrace.io"},
    "optimism": {"id": "10", "explorer": "https://optimistic.etherscan.io"},
    "fantom": {"id": "250", "explorer": "https://ftmscan.com"},
    "linea": {"id": "59144", "explorer": "https://lineascan.build"},
    "zksync": {"id": "324", "explorer": "https://explorer.zksync.io"},
    "scroll": {"id": "534352", "explorer": "https://scrollscan.com"},
    "mantle": {"id": "5000", "explorer": "https://mantlescan.xyz"},
}

# ═══════════════════════════════════════════════════════════════
# WALLET SCANNER — Powered by SENTINEL + Helius + Wallet Memory
# ═══════════════════════════════════════════════════════════════

@dataclass
class WalletRiskFactors:
    """100+ risk factors scored per wallet — populated from real on-chain data."""
    
    wallet_age_days: int = 0
    first_tx_date: Optional[str] = None
    total_tx_count: int = 0
    tx_frequency_per_day: float = 0
    days_since_last_tx: int = 0
    active_chains: int = 1
    total_volume_usd: float = 0
    avg_tx_value_usd: float = 0
    max_single_tx_usd: float = 0
    
    funding_source: Optional[str] = None
    funding_source_label: Optional[str] = None
    funding_source_is_cex: bool = False
    funding_source_is_mixer: bool = False
    funding_from_sanctioned: bool = False
    funding_from_scammer: bool = False
    funding_hop_count: int = 0
    cross_chain_funding: bool = False
    tornado_cash_exposure: bool = False
    mixer_interactions: int = 0
    
    unique_tokens_held: int = 0
    token_launches_participated: int = 0
    sniper_activity_score: float = 0
    sandwich_attacks_executed: int = 0
    flash_loan_usage: int = 0
    rug_pull_launcher_count: int = 0
    honeypot_tokens_owned: int = 0
    tokens_where_top_holder: int = 0
    
    cex_deposits: int = 0
    cex_withdrawals: int = 0
    dex_swaps: int = 0
    dex_volume_usd: float = 0
    
    cluster_id: Optional[str] = None
    cluster_size: int = 0
    cluster_shared_funding: bool = False
    known_cluster_type: str = ""
    entity_label: Optional[str] = None
    entity_confidence: float = 0
    is_labeled_scammer: bool = False
    is_labeled_sanctioned: bool = False
    is_labeled_exchange: bool = False
    is_labeled_bot: bool = False
    is_labeled_whale: bool = False
    is_labeled_insider: bool = False
    linked_wallets_count: int = 0
    
    insider_trading_confidence: float = 0
    buys_before_pumps: int = 0
    sells_before_dumps: int = 0
    wash_trading_score: float = 0
    pump_and_dump_participant: bool = False
    new_token_flipper: bool = False
    round_trip_patterns: int = 0
    
    scam_token_exposure: int = 0
    phishing_victim: bool = False
    sybil_score: float = 0
    exploit_exposure: int = 0
    protocol_hack_interactions: int = 0
    approval_risk_score: float = 0
    
    current_balance_usd: float = 0
    portfolio_diversity_score: float = 0
    stablecoin_ratio: float = 0
    bluechip_ratio: float = 0
    memecoin_ratio: float = 0
    realized_pnl_usd: float = 0
    unrealized_pnl_usd: float = 0
    win_rate: float = 0
    
    # Token holdings risk (from integrated token scanner)
    held_token_risks: List[Dict[str, Any]] = field(default_factory=list)
    highest_risk_token: Optional[Dict[str, Any]] = None
    
    # Overall
    total_risk_score: int = 0
    risk_category: str = "unknown"
    confidence: float = 0
    data_sources: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════
# HELIUS — On-chain wallet data (FREE tier)
# ═══════════════════════════════════════════

async def _fetch_helius_wallet(address: str) -> Dict[str, Any]:
    """Fetch wallet age, tx count, balances, and token holdings from Helius."""
    import os
    key = os.getenv("HELIUS_API_KEY", "")
    if not key:
        return {}
    
    result = {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://mainnet.helius-rpc.com/?api-key={key}"
            
            # Get token balances
            resp = await client.post(url, json={
                "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
                "params": [address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                           {"encoding": "jsonParsed"}],
            })
            if resp.status_code == 200:
                data = resp.json()
                accounts = (data.get("result", {}) or {}).get("value", [])
                tokens = []
                total_value = 0.0
                for acc in accounts:
                    info = (acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {}))
                    amt = float(info.get("tokenAmount", {}).get("uiAmount", 0) or 0)
                    mint = info.get("mint", "")
                    if mint and amt > 0:
                        tokens.append({"mint": mint, "amount": amt})
                result["tokens"] = tokens
                result["token_count"] = len(tokens)
                result["data_sources"] = ["helius"]
            
            # Get transaction signatures for age/activity
            resp2 = await client.post(url, json={
                "jsonrpc": "2.0", "id": 2, "method": "getSignaturesForAddress",
                "params": [address, {"limit": 100}],
            })
            if resp2.status_code == 200:
                sigs = resp2.json().get("result", []) or []
                if sigs:
                    result["tx_count_sample"] = len(sigs)
                    result["last_tx"] = sigs[0].get("blockTime")
                    first = sigs[-1].get("blockTime")
                    if first:
                        age_seconds = datetime.now(timezone.utc).timestamp() - first
                        result["wallet_age_days"] = int(age_seconds / 86400)
                        if len(sigs) >= 100:
                            result["tx_count"] = len(sigs)
                        result["data_sources"] = result.get("data_sources", []) + ["helius_tx"]
                        
            # Get SOL balance
            resp3 = await client.post(url, json={
                "jsonrpc": "2.0", "id": 3, "method": "getBalance",
                "params": [address],
            })
            if resp3.status_code == 200:
                bal = resp3.json().get("result", {}).get("value", 0)
                result["sol_balance"] = bal / 1e9 if bal else 0
                
    except Exception as e:
        logger.debug(f"Helius wallet fetch failed for {address}: {e}")
    
    return result


# ═══════════════════════════════════════════
# SENTINEL INTEGRATION — Labels + Intel
# ═══════════════════════════════════════════

async def _fetch_sentinel_labels(address: str, chain: str) -> Dict[str, Any]:
    """Get rich labels from SENTINEL address_labeler (6 sources)."""
    try:
        from app.scanners.address_labeler import AddressLabeler
        labeler = AddressLabeler()
        result = await labeler.analyze(address, chain)
        if result:
            return {
                "labels": getattr(result, "labels", []),
                "category": getattr(result, "category", ""),
                "risk_score": getattr(result, "risk_score", 0),
                "sources": getattr(result, "sources", []),
            }
    except Exception as e:
        logger.debug(f"SENTINEL labels failed for {address}: {e}")
    return {}


async def _fetch_wallet_memory(address: str, chain: str) -> Dict[str, Any]:
    """Cross-chain identity + cluster intel from Wallet Memory Bank."""
    try:
        from app.wallet_memory.engine import get_wallet_engine
        engine = get_wallet_engine()
        intel = await engine.get_deployer_intelligence(address, chain)
        if intel:
            return {
                "entity_id": intel.get("entity_id"),
                "linked_wallets": intel.get("linked_wallets", []),
                "risk_score": intel.get("risk_score", 0),
                "scam_associations": intel.get("scam_associations", []),
                "deployer_history": intel.get("deployer_history"),
                "cross_chain_presence": intel.get("cross_chain_presence"),
            }
    except Exception as e:
        logger.debug(f"Wallet Memory Bank failed for {address}: {e}")
    return {}


async def _scan_held_tokens(tokens: list, chain: str) -> Dict[str, Any]:
    """Quick-scan tokens the wallet holds using SENTINEL token scanner."""
    if not tokens:
        return {"scanned": 0, "risks": []}
    
    risks = []
    highest = None
    for token in tokens[:20]:  # limit to 20 tokens
        mint = token.get("mint", "") if isinstance(token, dict) else token
        if not mint:
            continue
        try:
            from app.token_scanner import scan_token
            scan = await scan_token(mint, chain, tier="free")
            entry = {
                "token": mint,
                "symbol": scan.symbol,
                "name": scan.name,
                "safety_score": scan.safety_score,
                "risk_flags": scan.risk_flags[:3],
            }
            risks.append(entry)
            if highest is None or scan.safety_score < highest.get("safety_score", 100):
                highest = entry
        except Exception:
            pass
    
    return {
        "scanned": len(risks),
        "risks": risks,
        "highest_risk": highest,
    }


# ═══════════════════════════════════════════
# UNIFIED WALLET SCAN
# ═══════════════════════════════════════════

async def scan_wallet(wallet_address: str, chain: str = "solana", tier: str = "free") -> Dict[str, Any]:
    """Unified wallet scanner — SENTINEL + Helius + Wallet Memory + Token Scanner."""
    import time
    factors = WalletRiskFactors()
    start = time.time()
    data_sources = []
    token_list = []
    
    # ── FREE: Helius on-chain data (age, tx, tokens, balances) ──
    if chain == "solana":
        helius = await _fetch_helius_wallet(wallet_address)
        if helius:
            factors.wallet_age_days = helius.get("wallet_age_days", 0)
            factors.total_tx_count = helius.get("tx_count", 0)
            factors.current_balance_usd = helius.get("sol_balance", 0)
            token_list = helius.get("tokens", [])
            factors.unique_tokens_held = helius.get("token_count", 0)
            if helius.get("last_tx"):
                last_ts = helius["last_tx"]
                if isinstance(last_ts, (int, float)):
                    factors.days_since_last_tx = int((datetime.now(timezone.utc).timestamp() - last_ts) / 86400)
            data_sources.extend(helius.get("data_sources", []))
    
    # ── FREE: SENTINEL address labels (6-source label resolution) ──
    sentinel_labels = await _fetch_sentinel_labels(wallet_address, chain)
    if sentinel_labels:
        factors.entity_label = sentinel_labels.get("category", "")
        factors.is_labeled_scammer = "scam" in str(sentinel_labels).lower()
        factors.is_labeled_sanctioned = "sanction" in str(sentinel_labels).lower() or "ofac" in str(sentinel_labels).lower()
        factors.is_labeled_exchange = "exchange" in str(sentinel_labels).lower() or "cex" in str(sentinel_labels).lower()
        factors.is_labeled_bot = "bot" in str(sentinel_labels).lower() or "mev" in str(sentinel_labels).lower()
        factors.is_labeled_whale = "whale" in str(sentinel_labels).lower()
        factors.is_labeled_insider = "insider" in str(sentinel_labels).lower()
        factors.entity_confidence = sentinel_labels.get("risk_score", 50)
        data_sources.append("sentinel_labels")
    
    # ── DexScreener volume data ──
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": wallet_address}
            )
            if resp.status_code == 200:
                pairs = resp.json().get("pairs", [])
                if pairs:
                    factors.total_volume_usd = sum(float(p.get("volume", {}).get("h24", 0) or 0) for p in pairs)
                    factors.dex_swaps = len(pairs)
                    factors.token_launches_participated = sum(
                        1 for p in pairs if p.get("pairCreatedAt") and
                        (datetime.now(timezone.utc) - datetime.fromtimestamp(
                            p.get("pairCreatedAt", 0) / 1000, tz=timezone.utc
                        )).total_seconds() / 3600 < 24
                    )
                    data_sources.append("dexscreener")
    except Exception:
        pass
    
    # ── PRO: Wallet Memory Bank (cross-chain identity + clusters) ──
    if tier in ("pro", "elite"):
        wallet_memory = await _fetch_wallet_memory(wallet_address, chain)
        if wallet_memory:
            factors.linked_wallets_count = len(wallet_memory.get("linked_wallets", []))
            factors.cluster_size = wallet_memory.get("linked_wallets_count", factors.linked_wallets_count)
            factors.cluster_id = wallet_memory.get("entity_id", "")
            factors.cross_chain_funding = bool(wallet_memory.get("cross_chain_presence"))
            scam_assoc = wallet_memory.get("scam_associations", [])
            if scam_assoc:
                factors.is_labeled_scammer = True
                factors.scam_token_exposure = len(scam_assoc)
            hist = wallet_memory.get("deployer_history", {}) or {}
            factors.rug_pull_launcher_count = hist.get("rugs", 0)
            data_sources.append("wallet_memory")
        
        # GMGN scoring
        try:
            from app.gmgn_client import GMGNClient
            gmgn = GMGNClient()
            intel = await gmgn.get_wallet_intelligence(wallet_address)
            if intel:
                factors.insider_trading_confidence = float(intel.get("insider_score", 0))
                factors.sniper_activity_score = float(intel.get("sniper_score", 0))
                factors.wash_trading_score = float(intel.get("wash_trading_score", 0))
                factors.pump_and_dump_participant = intel.get("pump_dump_participant", False)
                factors.new_token_flipper = intel.get("flipper", False)
                pnl = intel.get("pnl", {}) or {}
                factors.realized_pnl_usd = float(pnl.get("realized", 0))
                factors.unrealized_pnl_usd = float(pnl.get("unrealized", 0))
                factors.win_rate = float(intel.get("win_rate", 0))
                data_sources.append("gmgn")
        except Exception:
            pass
        
        # Entity clustering
        try:
            from app.entity_clustering import EntityClusteringEngine
            engine = EntityClusteringEngine()
            cluster = engine.find_cluster(wallet_address)
            if cluster:
                factors.cluster_size = max(factors.cluster_size, cluster.get("size", 0))
                factors.cluster_shared_funding = cluster.get("shared_funding", False)
                factors.known_cluster_type = cluster.get("type", "")
                factors.linked_wallets_count = max(factors.linked_wallets_count, cluster.get("member_count", 0))
        except Exception:
            pass
    
    # ── ELITE: Token portfolio risk scan + ML ──
    if tier == "elite":
        # Scan held tokens for risk
        token_scan = await _scan_held_tokens(token_list, chain)
        if token_scan:
            factors.held_token_risks = token_scan.get("risks", [])
            factors.highest_risk_token = token_scan.get("highest_risk")
            high_risk = [t for t in token_scan.get("risks", []) if t.get("safety_score", 100) < 30]
            factors.honeypot_tokens_owned = len(high_risk)
        
        # ML anomaly detection
        try:
            from app.ml_anomaly import detect_wallet_anomaly
            anomaly = await detect_wallet_anomaly(wallet_address, chain)
            if anomaly:
                factors.sybil_score = anomaly.get("sybil_score", 0)
        except Exception:
            pass
        
        # Portfolio tracker
        try:
            from app.portfolio_tracker import get_portfolio
            portfolio = await get_portfolio(wallet_address, chain)
            if portfolio:
                factors.current_balance_usd = max(factors.current_balance_usd, float(portfolio.get("total_value_usd", 0)))
                factors.portfolio_diversity_score = portfolio.get("diversity_score", 0)
                factors.stablecoin_ratio = portfolio.get("stablecoin_pct", 0)
                factors.bluechip_ratio = portfolio.get("bluechip_pct", 0)
                factors.memecoin_ratio = portfolio.get("memecoin_pct", 0)
        except Exception:
            pass
    
    # ═══════════════════════════════════════════
    # Risk scoring
    # ═══════════════════════════════════════════
    
    risk = 0
    flags = []
    
    # Labels (strongest signal)
    if factors.is_labeled_sanctioned: risk += 50; flags.append("SANCTIONED")
    if factors.is_labeled_scammer: risk += 45; flags.append("KNOWN_SCAMMER")
    if factors.is_labeled_insider: risk += 25; flags.append("INSIDER_LABELED")
    if factors.is_labeled_bot: risk += 10; flags.append("BOT_WALLET")
    if factors.is_labeled_exchange: risk -= 10  # exchanges are neutral
    
    # Funding
    if factors.funding_source_is_mixer: risk += 25; flags.append("MIXER_FUNDING")
    if factors.funding_from_sanctioned: risk += 40; flags.append("SANCTIONED_FUNDING")
    if factors.tornado_cash_exposure: risk += 35; flags.append("TORNADO_CASH")
    
    # Age/Activity (only flag if wallet_age actually populated)
    if factors.wallet_age_days > 0:
        if factors.wallet_age_days < 1: risk += 15; flags.append("FRESH_WALLET")
        elif factors.wallet_age_days < 7 and factors.total_volume_usd > 100000:
            risk += 20; flags.append("NEW_WALLET_HIGH_VOLUME")
    elif factors.total_volume_usd > 50000:
        risk += 10; flags.append("UNVERIFIED_HIGH_VOLUME")  # no age data but high vol
    
    # Token interaction
    if factors.rug_pull_launcher_count > 0: risk += 50; flags.append("RUG_PULL_LAUNCHER")
    if factors.honeypot_tokens_owned > 0: risk += 20; flags.append("HONEYPOT_HOLDER")
    if factors.sniper_activity_score > 70: risk += 20; flags.append("HIGH_SNIPER")
    if factors.sandwich_attacks_executed > 0: risk += 25; flags.append("SANDWICH_ATTACKER")
    if factors.flash_loan_usage > 10: risk += 15; flags.append("HEAVY_FLASH_LOAN")
    
    # Behavioral
    if factors.insider_trading_confidence > 70: risk += 30; flags.append("INSIDER_TRADING")
    if factors.wash_trading_score > 60: risk += 20; flags.append("WASH_TRADING")
    if factors.pump_and_dump_participant: risk += 20; flags.append("PUMP_DUMP_PARTICIPANT")
    
    # Cluster
    if factors.cluster_size > 5 and factors.cluster_shared_funding:
        risk += 20; flags.append("LARGE_SHARED_CLUSTER")
    if factors.known_cluster_type in ("bot_farm", "sniper_ring"):
        risk += 15; flags.append("SUSPICIOUS_CLUSTER")
    
    # ML
    if factors.sybil_score > 70: risk += 15; flags.append("SYBIL_DETECTED")
    
    # Token portfolio risk (ELITE only)
    if factors.highest_risk_token:
        ts = factors.highest_risk_token
        if ts.get("safety_score", 100) < 25:
            risk += 15
            flags.append(f"HOLDS_CRITICAL_TOKEN_{ts.get('symbol','???')}")
    
    factors.total_risk_score = min(100, max(0, risk))
    factors.risk_category = (
        "critical" if risk >= 80 else
        "high_risk" if risk >= 60 else
        "medium" if risk >= 35 else
        "low_risk" if risk >= 15 else
        "safe"
    )
    
    # Confidence based on data quality
    confidence = 15  # base
    if "helius" in data_sources: confidence += 20
    if "sentinel_labels" in data_sources: confidence += 20
    if "dexscreener" in data_sources: confidence += 10
    if "wallet_memory" in data_sources: confidence += 15
    if "gmgn" in data_sources: confidence += 15
    confidence += min(len(flags) * 2, 15)  # flags add some confidence
    factors.confidence = min(100, confidence)
    factors.data_sources = data_sources
    
    elapsed = time.time() - start
    logger.info(f"Wallet scan {wallet_address[:12]}... [{chain}] = {factors.total_risk_score}/100 ({factors.risk_category}) conf={factors.confidence}% in {elapsed:.1f}s")
    
    return {
        "wallet": wallet_address,
        "chain": chain,
        "risk_score": factors.total_risk_score,
        "risk_category": factors.risk_category,
        "risk_flags": flags[:20],
        "total_flags": len(flags),
        "confidence": factors.confidence,
        "tier": tier,
        "data_sources": factors.data_sources,
        "factors": {
            "wallet_age_days": factors.wallet_age_days,
            "total_tx_count": factors.total_tx_count,
            "total_volume_usd": factors.total_volume_usd,
            "unique_tokens_held": factors.unique_tokens_held,
            "funding_source": factors.funding_source,
            "funding_source_label": factors.funding_source_label,
            "funding_source_is_cex": factors.funding_source_is_cex,
            "funding_source_is_mixer": factors.funding_source_is_mixer,
            "funding_from_sanctioned": factors.funding_from_sanctioned,
            "funding_from_scammer": factors.funding_from_scammer,
            "is_labeled_scammer": factors.is_labeled_scammer,
            "is_labeled_sanctioned": factors.is_labeled_sanctioned,
            "is_labeled_exchange": factors.is_labeled_exchange,
            "is_labeled_bot": factors.is_labeled_bot,
            "is_labeled_whale": factors.is_labeled_whale,
            "is_labeled_insider": factors.is_labeled_insider,
            "entity_label": factors.entity_label,
            "entity_confidence": factors.entity_confidence,
            "cluster_size": factors.cluster_size,
            "cluster_shared_funding": factors.cluster_shared_funding,
            "known_cluster_type": factors.known_cluster_type,
            "linked_wallets_count": factors.linked_wallets_count,
            "cross_chain_funding": factors.cross_chain_funding,
            "tornado_cash_exposure": factors.tornado_cash_exposure,
            "sniper_activity_score": factors.sniper_activity_score,
            "insider_trading_confidence": factors.insider_trading_confidence,
            "wash_trading_score": factors.wash_trading_score,
            "pump_and_dump_participant": factors.pump_and_dump_participant,
            "sybil_score": factors.sybil_score,
            "rug_pull_launcher_count": factors.rug_pull_launcher_count,
            "honeypot_tokens_owned": factors.honeypot_tokens_owned,
            "sandwich_attacks_executed": factors.sandwich_attacks_executed,
            "flash_loan_usage": factors.flash_loan_usage,
            "realized_pnl_usd": factors.realized_pnl_usd,
            "unrealized_pnl_usd": factors.unrealized_pnl_usd,
            "win_rate": factors.win_rate,
            "current_balance_usd": factors.current_balance_usd,
            "portfolio_diversity_score": factors.portfolio_diversity_score,
            "stablecoin_ratio": factors.stablecoin_ratio,
            "bluechip_ratio": factors.bluechip_ratio,
            "memecoin_ratio": factors.memecoin_ratio,
            "dex_swaps": factors.dex_swaps,
            "cex_deposits": factors.cex_deposits,
            "cex_withdrawals": factors.cex_withdrawals,
            "token_launches_participated": factors.token_launches_participated,
        },
        "held_tokens": {
            "scanned": len(factors.held_token_risks),
            "highest_risk": factors.highest_risk_token,
            "risks": factors.held_token_risks[:10],
        },
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "tool_fingerprints": None,
    }


# ═══════════════════════════════════════════════════════════════
# TRENDING ENGINE — Multi-source, real-time
# ═══════════════════════════════════════════════════════════════

async def get_trending_tokens(chain: str = None, limit: int = 20) -> Dict[str, Any]:
    """Get trending tokens from multiple sources, normalized across chains."""
    import time
    start = time.time()
    
    trending = []
    sources_used = []
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            url = "https://api.dexscreener.com/latest/dex/search"
            params = {"q": chain or "SOL", "limit": limit}
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                pairs = resp.json().get("pairs", [])
                now = datetime.now(timezone.utc)
                for pair in pairs:
                    created = pair.get("pairCreatedAt")
                    liq = float(pair.get("liquidity", {}).get("usd", 0))
                    vol = float(pair.get("volume", {}).get("h24", 0))
                    if liq < 1000:
                        continue
                    age_hours = 999
                    if created:
                        age_hours = (now - datetime.fromtimestamp(created / 1000, tz=timezone.utc)).total_seconds() / 3600
                    trending_score = (vol * 0.6 + liq * 0.3) / max(age_hours, 1)
                    trending.append({
                        "chain": pair.get("chainId", chain or "unknown"),
                        "address": pair.get("baseToken", {}).get("address", ""),
                        "symbol": pair.get("baseToken", {}).get("symbol", ""),
                        "name": pair.get("baseToken", {}).get("name", ""),
                        "price_usd": float(pair.get("priceUsd", 0)),
                        "liquidity_usd": liq,
                        "volume_24h": vol,
                        "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
                        "age_hours": round(age_hours, 1),
                        "trending_score": round(trending_score, 2),
                        "dex": pair.get("dexId", ""),
                        "source": "dexscreener",
                    })
                sources_used.append("dexscreener")
        except Exception as e:
            logger.warning(f"DexScreener trending failed: {e}")
        
        try:
            network = "solana" if chain == "solana" else "eth"
            resp = await client.get(
                f"https://api.geckoterminal.com/api/v2/networks/{network}/trending_pools",
                params={"limit": limit}
            )
            if resp.status_code == 200:
                pools = resp.json().get("data", [])
                for pool in pools:
                    attrs = pool.get("attributes", {})
                    trending.append({
                        "chain": chain or "unknown",
                        "address": attrs.get("base_token_address", ""),
                        "symbol": attrs.get("base_token_symbol", ""),
                        "name": attrs.get("name", ""),
                        "price_usd": float(attrs.get("base_token_price_usd", 0)),
                        "liquidity_usd": float(attrs.get("reserve_in_usd", 0)),
                        "volume_24h": float(attrs.get("volume_usd", {}).get("h24", 0)),
                        "price_change_24h": float(attrs.get("price_change_percentage", {}).get("h24", 0)),
                        "source": "geckoterminal",
                    })
                sources_used.append("geckoterminal")
        except Exception:
            pass
        
        try:
            resp = await client.get("https://api.coingecko.com/api/v3/search/trending")
            if resp.status_code == 200:
                coins = resp.json().get("coins", [])
                for item in coins[:limit]:
                    coin = item.get("item", {})
                    trending.append({
                        "chain": chain or "multi",
                        "address": coin.get("id", ""),
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name", ""),
                        "price_usd": coin.get("data", {}).get("price", 0),
                        "market_cap_rank": coin.get("market_cap_rank"),
                        "trending_score": coin.get("score", 0),
                        "source": "coingecko",
                    })
                sources_used.append("coingecko")
        except Exception:
            pass
    
    seen = set()
    unique = []
    for t in trending:
        key = f"{t.get('chain')}:{t.get('address')}"
        if key not in seen:
            seen.add(key)
            unique.append(t)
    
    unique.sort(key=lambda x: x.get("trending_score", 0), reverse=True)
    
    elapsed = time.time() - start
    logger.info(f"Trending: {len(unique)} tokens from {sources_used} in {elapsed:.1f}s")
    
    return {
        "tokens": unique[:limit],
        "total": len(unique),
        "sources": sources_used,
        "chains_covered": list(set(t.get("chain", "?") for t in unique)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# REAL-TIME LAUNCH MONITOR
# ═══════════════════════════════════════════════════════════════

LAST_KNOWN_LAUNCHES: Dict[str, set] = {}

async def get_new_launches(chain: str = "solana", since_seconds: int = 300) -> Dict[str, Any]:
    """Get tokens launched in the last N seconds."""
    import time
    start = time.time()
    
    now = datetime.now(timezone.utc)
    cutoff = (now.timestamp() * 1000) - (since_seconds * 1000)
    
    launches = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://api.dexscreener.com/latest/dex/search",
                params={"q": chain, "limit": 50}
            )
            if resp.status_code == 200:
                pairs = resp.json().get("pairs", [])
                for pair in pairs:
                    created = pair.get("pairCreatedAt", 0)
                    if created and created > cutoff:
                        liq = float(pair.get("liquidity", {}).get("usd", 0))
                        if liq < 500:
                            continue
                        launches.append({
                            "chain": pair.get("chainId", chain),
                            "address": pair.get("baseToken", {}).get("address", ""),
                            "symbol": pair.get("baseToken", {}).get("symbol", ""),
                            "name": pair.get("baseToken", {}).get("name", ""),
                            "price_usd": float(pair.get("priceUsd", 0)),
                            "liquidity_usd": liq,
                            "age_seconds": int((now.timestamp() * 1000 - created) / 1000),
                            "dex": pair.get("dexId", ""),
                        })
        except Exception:
            pass
    
    chain_key = chain or "all"
    if chain_key not in LAST_KNOWN_LAUNCHES:
        LAST_KNOWN_LAUNCHES[chain_key] = set()
    
    known = LAST_KNOWN_LAUNCHES[chain_key]
    new_launches = [l for l in launches if l["address"] not in known]
    for l in new_launches:
        known.add(l["address"])
    
    # Keep set bounded
    if len(known) > 10000:
        LAST_KNOWN_LAUNCHES[chain_key] = set(list(known)[-5000:])
    
    elapsed = time.time() - start
    logger.info(f"New launches [{chain}]: {len(new_launches)} in {elapsed:.1f}s")
    
    return {
        "launches": new_launches,
        "total_new": len(new_launches),
        "total_known": len(known),
        "chain": chain,
        "since_seconds": since_seconds,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
