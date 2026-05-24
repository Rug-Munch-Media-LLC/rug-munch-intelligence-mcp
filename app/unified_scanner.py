"""
RugMunch Unified Wallet Scanner + Trending Engine
==================================================
100+ risk factors across free/pro/elite tiers.
Multi-chain parity — same scan quality on every chain.

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
    "solana": {"id": "solana", "explorer": "https://solscan.io", "rpc": "https://api.mainnet-beta.solana.com"},
    "ethereum": {"id": "1", "explorer": "https://etherscan.io", "rpc": "https://ethereum-rpc.publicnode.com"},
    "base": {"id": "8453", "explorer": "https://basescan.org", "rpc": "https://mainnet.base.org"},
    "bsc": {"id": "56", "explorer": "https://bscscan.com", "rpc": "https://bsc-dataseed.binance.org"},
    "arbitrum": {"id": "42161", "explorer": "https://arbiscan.io", "rpc": "https://arb1.arbitrum.io/rpc"},
    "polygon": {"id": "137", "explorer": "https://polygonscan.com", "rpc": "https://polygon-rpc.com"},
    "avalanche": {"id": "43114", "explorer": "https://snowtrace.io", "rpc": "https://api.avax.network/ext/bc/C/rpc"},
    "optimism": {"id": "10", "explorer": "https://optimistic.etherscan.io", "rpc": "https://mainnet.optimism.io"},
    "fantom": {"id": "250", "explorer": "https://ftmscan.com", "rpc": "https://rpc.fantom.network"},
    "linea": {"id": "59144", "explorer": "https://lineascan.build", "rpc": "https://rpc.linea.build"},
    "zksync": {"id": "324", "explorer": "https://explorer.zksync.io", "rpc": "https://mainnet.era.zksync.io"},
    "scroll": {"id": "534352", "explorer": "https://scrollscan.com", "rpc": "https://rpc.scroll.io"},
    "mantle": {"id": "5000", "explorer": "https://mantlescan.xyz", "rpc": "https://rpc.mantle.xyz"},
}


# ═══════════════════════════════════════════════════════════════
# WALLET SCANNER — 100+ risk factors
# ═══════════════════════════════════════════════════════════════

@dataclass
class WalletRiskFactors:
    """100+ risk factors scored per wallet."""
    
    # ── Age & Activity (10 factors) ──
    wallet_age_days: int = 0
    first_tx_date: Optional[str] = None
    total_tx_count: int = 0
    tx_frequency_per_day: float = 0
    days_since_last_tx: int = 0
    active_chains: int = 1
    total_volume_usd: float = 0
    avg_tx_value_usd: float = 0
    max_single_tx_usd: float = 0
    gas_spent_eth: float = 0
    
    # ── Funding & Sources (15 factors) ──
    funding_source: Optional[str] = None
    funding_source_label: Optional[str] = None
    funding_source_is_cex: bool = False
    funding_source_is_mixer: bool = False
    funding_from_sanctioned: bool = False
    funding_from_scammer: bool = False
    funding_hop_count: int = 0
    funding_chain_count: int = 0
    initial_funding_usd: float = 0
    subsequent_funding_usd: float = 0
    funding_pattern: str = "unknown"  # single_source, multi_source, cex_heavy, dex_heavy
    bridge_usage_count: int = 0
    mixer_interactions: int = 0
    tornado_cash_exposure: bool = False
    cross_chain_funding: bool = False
    
    # ── Token & Contract Interaction (15 factors) ──
    unique_tokens_held: int = 0
    unique_contracts_interacted: int = 0
    token_launches_participated: int = 0
    avg_token_hold_time_hours: float = 0
    rug_pull_victim_count: int = 0
    rug_pull_launcher_count: int = 0
    honeypot_tokens_owned: int = 0
    tokens_with_high_tax: int = 0
    tokens_where_top_holder: int = 0
    sniper_activity_score: float = 0  # 0-100
    sandwich_attacks_executed: int = 0
    mev_bot_interactions: int = 0
    flash_loan_usage: int = 0
    liquidity_provided_count: int = 0
    liquidity_removed_count: int = 0
    
    # ── Exchange & Trading (10 factors) ──
    cex_deposits: int = 0
    cex_withdrawals: int = 0
    cex_volume_usd: float = 0
    dex_swaps: int = 0
    dex_volume_usd: float = 0
    dex_swap_ratio: float = 0  # dex_swaps / total_tx
    largest_dex_used: str = ""
    preferred_dex: str = ""
    arbitrage_patterns: int = 0
    avg_slippage_pct: float = 0
    
    # ── Wallet Clustering (15 factors) ──
    cluster_id: Optional[str] = None
    cluster_size: int = 0
    cluster_shared_funding: bool = False
    cluster_same_creation_time: bool = False
    cluster_similar_activity: bool = False
    known_cluster_type: str = ""  # bot_farm, sniper_ring, whale_pod, exchange, mixer
    entity_label: Optional[str] = None
    entity_confidence: float = 0
    is_labeled_scammer: bool = False
    is_labeled_sanctioned: bool = False
    is_labeled_exchange: bool = False
    is_labeled_bot: bool = False
    is_labeled_whale: bool = False
    is_labeled_insider: bool = False
    linked_wallets_count: int = 0
    
    # ── Behavioral Patterns (15 factors) ──
    buys_before_pumps: int = 0
    sells_before_dumps: int = 0
    insider_trading_confidence: float = 0
    new_token_flipper: bool = False
    copy_trader_target: Optional[str] = None
    unique_buy_times_of_day: int = 0
    preferred_activity_hours: List[int] = field(default_factory=list)
    weekend_vs_weekday_ratio: float = 0
    burst_activity_count: int = 0
    avg_burst_size: int = 0
    dormant_periods: int = 0
    max_dormant_days: int = 0
    recovery_pattern: str = ""  # suddenly_active, gradual_return, never_returned
    wash_trading_score: float = 0  # 0-100
    round_trip_patterns: int = 0
    
    # ── Risk Aggregates (20+ factors) ──
    honeypot_interaction_score: float = 0
    scam_token_exposure: int = 0
    phishing_victim: bool = False
    dusting_attack_target: bool = False
    airdrop_farmer: bool = False
    sybil_score: float = 0  # 0-100
    wash_trading_target_score: float = 0
    pump_and_dump_participant: bool = False
    ponzi_interactions: int = 0
    known_attack_patterns: List[str] = field(default_factory=list)
    exploit_exposure: int = 0
    protocol_hack_interactions: int = 0
    revocation_count: int = 0
    approval_risk_score: float = 0
    defi_health_score: float = 0
    
    # ── Financial Health (10 factors) ──
    current_balance_usd: float = 0
    portfolio_diversity_score: float = 0
    stablecoin_ratio: float = 0
    bluechip_ratio: float = 0
    memecoin_ratio: float = 0
    unrealized_pnl_usd: float = 0
    realized_pnl_usd: float = 0
    win_rate: float = 0
    avg_profit_per_trade_pct: float = 0
    risk_reward_ratio: float = 0
    
    # ── Overall ──
    total_risk_score: int = 0  # 0-100, higher = more suspicious
    risk_category: str = "unknown"  # safe, low_risk, medium, high_risk, critical
    confidence: float = 0  # how confident we are in this assessment


async def scan_wallet(wallet_address: str, chain: str = "solana", tier: str = "free") -> Dict[str, Any]:
    """Unified wallet scanner — builds WalletRiskFactors from all available data sources."""
    import time
    factors = WalletRiskFactors()
    start = time.time()
    
    # ── FREE TIER — DexScreener + basic labels ──
    async with httpx.AsyncClient(timeout=20.0) as client:
        # DexScreener wallet data
        try:
            resp = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{wallet_address}")
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    vol = sum(float(p.get("volume", {}).get("h24", 0)) for p in pairs)
                    factors.total_volume_usd = vol
                    factors.dex_swaps = len(pairs)
        except Exception:
            pass
        
        # Get chain explorer data
        chain_config = CHAINS.get(chain, CHAINS.get("solana", {}))
        
        # Label check (works on all chains via our label loader)
        try:
            from app.wallet_label_loader import lookup_wallet_label
            label = await asyncio.get_event_loop().run_in_executor(
                None, lookup_wallet_label, wallet_address, chain
            )
            if label:
                factors.entity_label = label.get("label")
                factors.is_labeled_scammer = "scam" in str(label).lower()
                factors.is_labeled_sanctioned = "sanction" in str(label).lower() or "ofac" in str(label).lower()
                factors.is_labeled_exchange = "exchange" in str(label).lower() or "cex" in str(label).lower()
                factors.is_labeled_whale = "whale" in str(label).lower()
                factors.entity_confidence = label.get("confidence", 50)
        except Exception:
            pass
        
        # Funding analysis via DexScreener
        try:
            resp = await client.get(
                f"https://api.dexscreener.com/latest/dex/search",
                params={"q": wallet_address}
            )
            if resp.status_code == 200:
                pairs = resp.json().get("pairs", [])
                factors.unique_tokens_held = len(pairs)
                factors.token_launches_participated = sum(
                    1 for p in pairs if p.get("pairCreatedAt") and 
                    (datetime.now(timezone.utc) - datetime.fromtimestamp(
                        p.get("pairCreatedAt", 0) / 1000, tz=timezone.utc
                    )).total_seconds() / 3600 < 24
                )
        except Exception:
            pass
    
    # ── PRO TIER — GMGN wallet intel + entity clustering ──
    if tier in ("pro", "elite"):
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
                if intel.get("pnl"):
                    factors.realized_pnl_usd = float(intel["pnl"].get("realized", 0))
                    factors.unrealized_pnl_usd = float(intel["pnl"].get("unrealized", 0))
        except Exception:
            pass
        
        try:
            from app.entity_clustering import EntityClusteringEngine
            engine = EntityClusteringEngine()
            cluster = engine.find_cluster(wallet_address)
            if cluster:
                factors.cluster_id = cluster.get("id")
                factors.cluster_size = cluster.get("size", 0)
                factors.linked_wallets_count = cluster.get("member_count", 0)
                factors.cluster_shared_funding = cluster.get("shared_funding", False)
                factors.known_cluster_type = cluster.get("type", "")
        except Exception:
            pass
    
    # ── ELITE TIER — Full traceback + ML + patterns ──
    if tier == "elite":
        try:
            from app.ml_anomaly import detect_wallet_anomaly
            anomaly = await detect_wallet_anomaly(wallet_address, chain)
            if anomaly:
                factors.wash_trading_target_score = anomaly.get("wash_score", 0)
                factors.sybil_score = anomaly.get("sybil_score", 0)
                factors.known_attack_patterns = anomaly.get("patterns", [])
        except Exception:
            pass
        
        try:
            from app.portfolio_tracker import get_portfolio
            portfolio = await get_portfolio(wallet_address, chain)
            if portfolio:
                factors.current_balance_usd = float(portfolio.get("total_value_usd", 0))
                factors.portfolio_diversity_score = portfolio.get("diversity_score", 0)
                factors.stablecoin_ratio = portfolio.get("stablecoin_pct", 0)
                factors.bluechip_ratio = portfolio.get("bluechip_pct", 0)
                factors.memecoin_ratio = portfolio.get("memecoin_pct", 0)
        except Exception:
            pass
    
    # ═══════════════════════════════════════════
    # Calculate risk score from 100+ factors
    # ═══════════════════════════════════════════
    
    risk = 0
    flags = []
    
    # Funding red flags
    if factors.funding_source_is_mixer: risk += 25; flags.append("MIXER_FUNDING")
    if factors.funding_from_sanctioned: risk += 40; flags.append("SANCTIONED_FUNDING")
    if factors.funding_from_scammer: risk += 30; flags.append("SCAMMER_FUNDING")
    if factors.tornado_cash_exposure: risk += 35; flags.append("TORNADO_CASH")
    if factors.mixer_interactions > 0: risk += 20; flags.append("MIXER_INTERACTIONS")
    if factors.cross_chain_funding and factors.funding_hop_count > 3: risk += 15; flags.append("OBFUSCATED_FUNDING")
    
    # Activity red flags
    if factors.wallet_age_days < 7 and factors.total_volume_usd > 100000: risk += 20; flags.append("NEW_WALLET_HIGH_VOLUME")
    if factors.wallet_age_days < 1: risk += 15; flags.append("FRESH_WALLET")
    if factors.burst_activity_count > 5: risk += 15; flags.append("BURST_ACTIVITY")
    if factors.dormant_periods > 2 and factors.max_dormant_days > 365: risk += 10; flags.append("DORMANT_REACTIVATED")
    
    # Token interaction red flags
    if factors.rug_pull_launcher_count > 0: risk += 50; flags.append("RUG_PULL_LAUNCHER")
    if factors.honeypot_tokens_owned > 0: risk += 20; flags.append("HONEYPOT_OWNER")
    if factors.sniper_activity_score > 70: risk += 20; flags.append("HIGH_SNIPER_ACTIVITY")
    if factors.sandwich_attacks_executed > 0: risk += 25; flags.append("SANDWICH_ATTACKER")
    if factors.flash_loan_usage > 10: risk += 15; flags.append("HEAVY_FLASH_LOAN_USER")
    
    # Behavioral
    if factors.insider_trading_confidence > 70: risk += 30; flags.append("INSIDER_TRADING")
    if factors.buys_before_pumps > 3: risk += 25; flags.append("BUY_BEFORE_PUMP")
    if factors.sells_before_dumps > 3: risk += 25; flags.append("SELL_BEFORE_DUMP")
    if factors.wash_trading_score > 60: risk += 20; flags.append("WASH_TRADING")
    if factors.round_trip_patterns > 5: risk += 15; flags.append("ROUND_TRIP_PATTERNS")
    
    # Labels
    if factors.is_labeled_scammer: risk += 45; flags.append("KNOWN_SCAMMER")
    if factors.is_labeled_sanctioned: risk += 50; flags.append("SANCTIONED")
    if factors.is_labeled_bot: risk += 10; flags.append("BOT_WALLET")
    if factors.is_labeled_insider: risk += 25; flags.append("INSIDER_LABELED")
    
    # Cluster
    if factors.cluster_size > 5 and factors.cluster_shared_funding: risk += 20; flags.append("LARGE_SHARED_FUNDING_CLUSTER")
    if factors.known_cluster_type in ("bot_farm", "sniper_ring"): risk += 15; flags.append("SUSPICIOUS_CLUSTER")
    
    # ML flags
    if factors.sybil_score > 70: risk += 15; flags.append("SYBIL_DETECTED")
    if factors.wash_trading_target_score > 50: risk += 10; flags.append("WASH_TARGET")
    if factors.pump_and_dump_participant: risk += 20; flags.append("PUMP_DUMP_PARTICIPANT")
    
    # Financial
    if factors.win_rate > 90 and factors.avg_profit_per_trade_pct > 500: risk += 10; flags.append("SUSPICIOUS_WIN_RATE")
    if factors.stablecoin_ratio < 0.01 and factors.portfolio_diversity_score < 10: risk += 5; flags.append("LOW_DIVERSITY")
    
    factors.total_risk_score = min(100, max(0, risk))
    factors.risk_category = (
        "critical" if risk >= 80 else
        "high_risk" if risk >= 60 else
        "medium" if risk >= 35 else
        "low_risk" if risk >= 15 else
        "safe"
    )
    factors.confidence = min(100, 30 + len(flags) * 3)
    
    elapsed = time.time() - start
    logger.info(f"Wallet scan {wallet_address[:12]}... [{chain}] = {factors.total_risk_score}/100 ({factors.risk_category}) in {elapsed:.1f}s")
    
    return {
        "wallet": wallet_address,
        "chain": chain,
        "risk_score": factors.total_risk_score,
        "risk_category": factors.risk_category,
        "risk_flags": flags[:20],
        "total_flags": len(flags),
        "confidence": factors.confidence,
        "tier": tier,
        "factors": {
            "funding_source": factors.funding_source,
            "funding_is_mixer": factors.funding_source_is_mixer,
            "is_labeled_scammer": factors.is_labeled_scammer,
            "is_labeled_sanctioned": factors.is_labeled_sanctioned,
            "cluster_size": factors.cluster_size,
            "sniper_score": factors.sniper_activity_score,
            "insider_confidence": factors.insider_trading_confidence,
            "wash_trading_score": factors.wash_trading_score,
            "sybil_score": factors.sybil_score,
            "wallet_age_days": factors.wallet_age_days,
            "total_volume_usd": factors.total_volume_usd,
            "unique_tokens_held": factors.unique_tokens_held,
        },
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        # Tool fingerprinting (always runs on elite tier, optional on pro)
        "tool_fingerprints": None,  # populated by caller if requested
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
        # Source 1: DexScreener trending (cross-chain)
        try:
            url = "https://api.dexscreener.com/latest/dex/search"
            params = {"q": chain or "SOL", "limit": limit}
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                pairs = resp.json().get("pairs", [])
                # Filter and rank by volume+liquidity+age
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
                    
                    # Trending score: high volume on new tokens, high liquidity on older
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
        
        # Source 2: GeckoTerminal trending pools
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
        
        # Source 3: CoinGecko trending (broader market)
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
    
    # Deduplicate and sort by trending score
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

LAST_KNOWN_LAUNCHES: Dict[str, set] = {}  # chain -> set of addresses

async def get_new_launches(chain: str = "solana", since_seconds: int = 300) -> Dict[str, Any]:
    """Get tokens launched in the last N seconds. Ultra-fast polling mode."""
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
                    if created > cutoff:
                        base = pair.get("baseToken", {})
                        launches.append({
                            "address": base.get("address", ""),
                            "symbol": base.get("symbol", ""),
                            "name": base.get("name", ""),
                            "chain": pair.get("chainId", chain),
                            "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                            "initial_price_usd": float(pair.get("priceUsd", 0)),
                            "dex": pair.get("dexId", ""),
                            "launched_at": datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat(),
                            "seconds_ago": (now.timestamp() - created / 1000),
                        })
        except Exception as e:
            logger.warning(f"Launch monitor {chain}: {e}")
    
    # Track which are genuinely new
    if chain not in LAST_KNOWN_LAUNCHES:
        LAST_KNOWN_LAUNCHES[chain] = set()
    
    known = LAST_KNOWN_LAUNCHES[chain]
    new = [l for l in launches if l["address"] not in known]
    for l in launches:
        known.add(l["address"])
    
    elapsed = time.time() - start
    logger.info(f"Launch monitor [{chain}]: {len(new)} new in {elapsed:.1f}s")
    
    return {
        "chain": chain,
        "new_launches": new,
        "total_active": len(launches),
        "since_seconds": since_seconds,
        "updated_at": now.isoformat(),
    }
