"""
Security Intelligence Router v2 — Complete Crypto Security Stack
===================================================================

All crypto security modules exposed via REST:
  • Contract: bytecode scan + deep scan (Slither + Mythril)
  • Wallet: reputation + threat intel + anomaly detection
  • Graph: clustering + fund flow + cross-chain correlation
  • Mempool: real-time attack detection + sentinel control
  • Threat: OFAC + local blocklist + batch lookup
  • Dashboard: alert aggregation + monitoring + scoring
  • ML: anomaly detection on wallets + token metrics
  • CrossChain: wallet linking across chains

Updated 2026-05-08 for world-class crypto intelligence.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.contract_deepscan import batch_deep_scan, deep_scan_contract
from app.cross_chain_correlator import ChainFingerprint, CrossChainCorrelator
from app.crypto_guard import (
    check_wallet_reputation,
    rate_limit_by_tier,
    require_crypto_auth,
)
from app.entity_labeler import EntityLabeler, batch_label_addresses as batch_label, get_entity_labeler as get_entity_db, label_address
from app.exchange_flow_analyzer import analyze_entity_flows, compare_flows, get_reserves
from app.mempool_sentinel import SentinelManager
from app.ml_anomaly import (
    TokenMetricAnomalyDetector,
    WalletAnomalyDetector,
)
from app.onchain_analyzer import analyze_contract, batch_analyze_contracts
from app.portfolio_tracker import (
    get_multi_wallet_portfolio,
    get_portfolio,
    get_portfolio_history,
)
from app.security_dashboard import (
    SecurityDashboard,
    create_alert_from_detection,
    get_dashboard,
)
from app.threat_intel import get_aggregator
from app.tx_graph_analyzer import TransactionGraph, build_graph_from_transactions
from app.wallet_monitor import WalletMonitorManager
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/security", tags=["security"])

# ─── SINGLETONS ────────────────────────────────────────────

_sentinel_manager: Optional[SentinelManager] = None
_wallet_detector: Optional[WalletAnomalyDetector] = None
_token_detector: Optional[TokenMetricAnomalyDetector] = None


async def get_sentinel() -> SentinelManager:
    global _sentinel_manager
    if _sentinel_manager is None:
        _sentinel_manager = SentinelManager()
    return _sentinel_manager


async def get_wallet_detector() -> WalletAnomalyDetector:
    global _wallet_detector
    if _wallet_detector is None:
        _wallet_detector = WalletAnomalyDetector(contamination=0.05)
    return _wallet_detector


async def get_token_detector() -> TokenMetricAnomalyDetector:
    global _token_detector
    if _token_detector is None:
        _token_detector = TokenMetricAnomalyDetector()
    return _token_detector


# ─── MODELS ────────────────────────────────────────────────


class ContractScanRequest(BaseModel):
    address: str = Field(..., min_length=32, max_length=44)
    chain: str = Field(default="ethereum")
    deep: bool = Field(default=False, description="Run Slither + Mythril deep scan")


class BatchContractRequest(BaseModel):
    addresses: List[str] = Field(..., min_length=1, max_length=50)
    chain: str = Field(default="ethereum")
    deep: bool = Field(default=False)


class WalletCheckRequest(BaseModel):
    address: str = Field(..., min_length=32, max_length=44)
    chain: str = Field(default="auto")


class WalletAnalyzeRequest(BaseModel):
    address: str = Field(..., min_length=32, max_length=44)
    transactions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Raw tx list for ML analysis"
    )
    chain: str = Field(default="auto")


class GraphAnalyzeRequest(BaseModel):
    transactions: List[Dict[str, Any]] = Field(..., min_length=2, max_length=1000)
    chain: str = Field(default="ethereum")
    analysis_types: List[str] = Field(default=["clusters", "flows", "anomalies"])


class ThreatBatchRequest(BaseModel):
    addresses: List[str] = Field(..., min_length=1, max_length=100)
    chain: str = Field(default="evm")


class CrossChainRequest(BaseModel):
    fingerprints: List[Dict[str, Any]] = Field(
        ..., min_length=2, description="Chain fingerprints"
    )
    chains: List[str] = Field(default=["ethereum", "base", "solana"])


class TokenMetricRequest(BaseModel):
    token: str = Field(...)
    metrics: Dict[str, float] = Field(..., description="Current metric values")


class AlertAckRequest(BaseModel):
    alert_id: str = Field(...)


# ─── CONTRACT ANALYSIS ─────────────────────────────────────


@router.get("/contract/{address}")
async def contract_analysis(address: str, chain: str = "ethereum", deep: bool = False):
    """Analyze contract — bytecode scan + optional Slither/Mythril deep scan."""

    # Fast bytecode scan
    result = await analyze_contract(address, chain)
    response = {
        "address": result.address,
        "chain": result.chain,
        "is_contract": result.is_contract,
        "is_proxy": result.is_proxy,
        "proxy_type": result.proxy_type,
        "proxy_implementation": result.proxy_implementation,
        "risk_score": result.risk_score,
        "risk_flags": result.risk_flags,
        "detected_interfaces": result.detected_interfaces,
        "has_selfdestruct": result.has_selfdestruct,
        "has_delegatecall": result.has_delegatecall,
        "has_mint": result.has_mint,
        "has_burn": result.has_burn,
        "has_renounce_ownership": result.has_renounce_ownership,
        "has_reentrancy_guard": result.has_reentrancy_guard,
        "uses_tx_origin": result.uses_tx_origin,
        "uses_timestamp": result.uses_timestamp,
        "honeypot_indicators": result.honeypot_indicators,
        "anti_bot_detected": result.anti_bot_detected,
        "uniswap_pair": result.uniswap_pair,
        "analysis_time": result.analysis_time,
    }

    # Deep scan (if requested)
    if deep:
        try:
            deep_result = await deep_scan_contract(address, chain, use_cache=True)
            response["deep_scan"] = deep_result.to_dict()
            # Merge scores
            response["risk_score"] = max(response["risk_score"], deep_result.risk_score)
            response["deep_vulnerabilities"] = len(deep_result.vulnerabilities)
        except Exception as e:
            response["deep_scan_error"] = str(e)

    return response


@router.post("/scan/batch")
async def batch_contract_scan(req: BatchContractRequest):
    """Batch contract scan — fast or deep."""
    if req.deep:
        results = await batch_deep_scan(req.addresses, req.chain)
        return {
            "scanned": len(results),
            "chain": req.chain,
            "high_risk": [r.address for r in results if r.risk_score >= 70],
            "critical": [r.address for r in results if r.risk_score >= 90],
            "results": [r.to_dict() for r in results],
        }
    else:
        results = await batch_analyze_contracts(req.addresses, req.chain)
        return {
            "scanned": len(results),
            "chain": req.chain,
            "high_risk": [r.address for r in results if r.risk_score >= 70],
            "proxies": [r.address for r in results if r.is_proxy],
            "honeypots": [r.address for r in results if r.honeypot_indicators],
            "results": [
                {
                    "address": r.address,
                    "risk_score": r.risk_score,
                    "risk_flags": r.risk_flags,
                    "is_proxy": r.is_proxy,
                    "honeypot": r.honeypot_indicators,
                }
                for r in results
            ],
        }


# ─── WALLET / THREAT INTEL ──────────────────────────────────


@router.get("/wallet/{address}")
async def wallet_security_check(address: str, chain: str = "auto"):
    """Full wallet security check: reputation + threat intel."""
    reputation = await check_wallet_reputation(address, chain)
    agg = await get_aggregator()
    threat_rep = await agg.check_address(address, chain)

    final_score = max(reputation.get("score", 0), threat_rep.risk_score)

    return {
        "address": address,
        "chain": chain,
        "risk_score": final_score,
        "blocked": reputation.get("blocked", False) or threat_rep.is_blocked,
        "sanctioned": threat_rep.is_sanctioned,
        "scam": threat_rep.is_scam,
        "mixer": threat_rep.is_mixer,
        "categories": list(threat_rep.categories),
        "tags": list(threat_rep.tags),
        "threat_reports": len(threat_rep.threat_reports),
        "reputation_flags": reputation.get("flags", []),
        "first_flagged": threat_rep.first_flagged,
        "last_flagged": threat_rep.last_flagged,
    }


@router.post("/wallet/analyze")
async def wallet_ml_analysis(req: WalletAnalyzeRequest):
    """ML behavioral analysis of wallet transactions."""
    from app.ml_anomaly import extract_wallet_features

    features = extract_wallet_features(req.transactions, req.address)
    detector = await get_wallet_detector()

    # Fit detector if we have comparison data
    if req.transactions and len(req.transactions) > 5:
        detector.fit([features])
        result = detector.predict(features)
    else:
        result = {"error": "Insufficient transactions for ML analysis (need >5)"}

    return {
        "address": req.address,
        "features": {
            "tx_count": features.tx_count,
            "avg_tx_value": features.avg_tx_value,
            "unique_counterparties": features.unique_counterparties,
            "dex_swaps": features.dex_swaps,
            "burst_ratio": features.burst_ratio,
            "night_ratio": features.night_tx_ratio,
        },
        "ml_result": result,
    }


@router.post("/threat/check")
async def batch_threat_check(req: ThreatBatchRequest):
    """Batch threat intel lookup."""
    agg = await get_aggregator()
    results = await agg.batch_check(req.addresses, req.chain)

    return {
        "checked": len(results),
        "blocked": [a for a, r in results.items() if r.is_blocked],
        "sanctioned": [a for a, r in results.items() if r.is_sanctioned],
        "scams": [a for a, r in results.items() if r.is_scam],
        "mixers": [a for a, r in results.items() if r.is_mixer],
        "results": {a: r.to_dict() for a, r in results.items()},
    }


# ─── GRAPH ANALYSIS ─────────────────────────────────────────


@router.post("/graph/analyze")
async def graph_analyze(req: GraphAnalyzeRequest):
    """Transaction graph: clusters, flows, anomalies."""
    graph = await build_graph_from_transactions(req.transactions, req.chain)

    response = {
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "wallets": list(graph.nodes.keys())[:50],
    }

    if "clusters" in req.analysis_types:
        clusters = graph.cluster_by_louvain()
        response["clusters"] = [
            {
                "id": c.id,
                "wallet_count": len(c.wallets),
                "total_volume": c.total_volume,
            }
            for c in clusters[:10]
        ]

    if "shared_funding" in req.analysis_types:
        shared = graph.cluster_by_shared_funding(min_common=2)
        response["shared_funding_clusters"] = [
            {
                "id": c.id,
                "wallet_count": len(c.wallets),
                "shared_funders": c.shared_funders[:5],
            }
            for c in shared[:10]
        ]

    if "flows" in req.analysis_types:
        cycles = graph.detect_circular_flows(max_cycle_len=4)
        response["circular_flows"] = len(cycles)
        response["wash_trading_suspected"] = len(cycles) > 2

    if "anomalies" in req.analysis_types:
        bursts = graph.detect_burst_transfers(min_count=15)
        sudden = graph.detect_sudden_wealth(multiplier=20.0)
        response["burst_activity"] = bursts[:5]
        response["sudden_wealth"] = sudden[:5]

    if "export" in req.analysis_types:
        import tempfile

        path = tempfile.mktemp(suffix=".gexf")
        graph.export_gexf(path)
        response["gexf_export_path"] = path

    return response


# ─── CROSS-CHAIN ────────────────────────────────────────────


@router.post("/crosschain/correlate")
async def crosschain_correlate(req: CrossChainRequest):
    """Find cross-chain wallet correlations."""
    correlator = CrossChainCorrelator(confidence_threshold=0.6)

    # Add fingerprints
    for fp_data in req.fingerprints:
        import numpy as np
        from app.cross_chain_correlator import ChainFingerprint

        fp = ChainFingerprint(
            address=fp_data["address"],
            chain=fp_data["chain"],
            feature_vector=np.array(fp_data.get("features", []), dtype=np.float64),
            first_active=fp_data.get("first_active"),
            last_active=fp_data.get("last_active"),
            total_txs=fp_data.get("total_txs", 0),
            total_volume=fp_data.get("total_volume", 0.0),
            known_tags=fp_data.get("tags", []),
        )
        correlator.add_fingerprint(fp)

    # Find links
    links = correlator.find_all_links(req.chains)

    return {
        "fingerprints_analyzed": len(req.fingerprints),
        "links_found": len(links),
        "high_confidence_links": [l.to_dict() for l in links if l.confidence >= 0.8],
        "all_links": [l.to_dict() for l in links[:20]],
    }


# ─── ML / ANOMALY ───────────────────────────────────────────


@router.post("/ml/token/anomaly")
async def token_metric_anomaly(req: TokenMetricRequest):
    """Detect token metric anomalies vs baseline."""
    detector = await get_token_detector()
    detector.update_baseline(req.token, req.metrics)
    result = detector.detect_anomaly(req.token, req.metrics)
    return result


# ─── MEMPOOL ────────────────────────────────────────────────


@router.get("/mempool/status")
async def mempool_status():
    """Mempool sentinel status + recent detections."""
    sentinel = await get_sentinel()
    stats = sentinel.get_stats()

    patterns = sentinel.sentinel.get_recent_patterns(20) if sentinel.sentinel else []

    return {
        **stats,
        "recent_patterns": patterns,
    }


@router.post("/mempool/start")
async def mempool_start(chain: str = "ethereum"):
    sentinel = await get_sentinel()
    await sentinel.start(chain)
    return {"status": "started", "chain": chain}


@router.post("/mempool/stop")
async def mempool_stop():
    sentinel = await get_sentinel()
    await sentinel.stop()
    return {"status": "stopped"}


# ─── DASHBOARD ──────────────────────────────────────────────


@router.get("/dashboard/stats")
async def dashboard_stats():
    """Security dashboard statistics."""
    dash = get_dashboard()
    return dash.get_stats()


@router.get("/dashboard/alerts")
async def dashboard_alerts(
    severity: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 100,
    unacknowledged: bool = False,
):
    """Query security alerts."""
    dash = get_dashboard()
    return dash.get_alerts(severity, source, limit, unacknowledged)


@router.post("/dashboard/acknowledge")
async def dashboard_acknowledge(req: AlertAckRequest):
    """Acknowledge an alert."""
    dash = get_dashboard()
    success = await dash.acknowledge(req.alert_id)
    return {"acknowledged": success}


@router.get("/dashboard/score")
async def dashboard_score(hours: int = 24):
    """Get rolling security score."""
    dash = get_dashboard()
    return {
        "security_score": dash.get_security_score(hours),
        "window_hours": hours,
        "max": 100,
    }


@router.get("/dashboard/timeline/{target}")
async def dashboard_timeline(target: str):
    """Get incident timeline for a target."""
    dash = get_dashboard()
    return {"timeline": dash.get_incident_timeline(target)}


# ─── ENTITY LABELING ─────────────────────────────────────────


@router.get("/entity/label/{address}")
async def entity_label(address: str):
    """Lookup entity label for an address."""
    entity = await label_address(address)
    if not entity:
        return {"address": address, "entity": None, "known": False}
    return {"address": address, "entity": entity.to_dict(), "known": True}


@router.post("/entity/batch")
async def entity_batch_label(addresses: List[str]):
    """Batch entity label lookup."""
    return await batch_label(addresses)


@router.get("/entity/search")
async def entity_search(q: str = "", category: Optional[str] = None, limit: int = 50):
    """Search entity database."""
    db = await get_entity_db()
    results = await db.search_entities(query=q, category=category, limit=limit)
    return {"results": [r.to_dict() for r in results], "count": len(results)}


@router.get("/entity/stats")
async def entity_stats():
    """Entity database statistics."""
    db = await get_entity_db()
    return await db.get_stats()


@router.get("/entity/{entity_id}")
async def entity_detail(entity_id: str):
    """Full entity graph with addresses and relationships."""
    db = await get_entity_db()
    return await db.get_entity_graph(entity_id)


# ─── PORTFOLIO TRACKER ──────────────────────────────────────


@router.get("/portfolio/{wallet}")
async def portfolio_single(wallet: str, chain: str = "ethereum"):
    """Get portfolio for a single wallet."""
    portfolio = await get_portfolio(wallet, chain)
    return portfolio.to_dict()


@router.post("/portfolio/multi")
async def portfolio_multi(wallets: List[Dict[str, str]]):
    """Aggregate portfolio across multiple wallets/chains."""
    result = await get_multi_wallet_portfolio(wallets)
    return result.to_dict()


@router.get("/portfolio/history/{wallet}")
async def portfolio_history(wallet: str, chain: str = "ethereum", hours: int = 24):
    """Historical net worth chart data."""
    history = await get_portfolio_history(wallet, chain, hours)
    return {
        "wallet": wallet,
        "chain": chain,
        "hours": hours,
        "data_points": len(history),
        "history": history,
    }


# ─── WALLET MONITOR ─────────────────────────────────────────


@router.post("/monitor/watch")
async def monitor_watch(address: str, chain: str = "ethereum", tags: str = ""):
    """Add a wallet to the watchlist."""
    manager = WalletMonitorManager()
    await manager.add_watch(address, chain, tags.split(",") if tags else [])
    return {"watched": True, "address": address, "chain": chain}


@router.post("/monitor/unwatch")
async def monitor_unwatch(address: str, chain: str = "ethereum"):
    """Remove a wallet from the watchlist."""
    manager = WalletMonitorManager()
    await manager.remove_watch(address, chain)
    return {"unwatched": True, "address": address, "chain": chain}


@router.get("/monitor/watches")
async def monitor_list():
    """List all watched wallets."""
    manager = WalletMonitorManager()
    watches = await manager.list_watches()
    return {"watches": watches, "count": len(watches)}


# ─── EXCHANGE FLOW ANALYZER ─────────────────────────────────


@router.post("/flows/analyze")
async def flows_analyze(
    entity_addresses: List[str],
    entity_name: str,
    entity_id: str,
    chain: str,
    transactions: List[Dict[str, Any]],
    hours: int = 24,
):
    """Analyze fund flows for an entity."""
    return await analyze_entity_flows(
        entity_addresses, entity_name, entity_id, chain, transactions, hours
    )


@router.post("/flows/reserves")
async def flows_reserves(
    entity_addresses: List[str],
    entity_name: str,
    entity_id: str,
    chain: str,
):
    """Get reserve snapshot for entity addresses."""
    return await get_reserves(entity_addresses, entity_name, entity_id, chain)


@router.post("/flows/compare")
async def flows_compare(
    entity_a: Dict[str, Any],
    entity_b: Dict[str, Any],
    transactions: List[Dict[str, Any]],
):
    """Compare fund flows between two entities."""
    return await compare_flows(entity_a, entity_b, transactions)


# ─── HEALTH ────────────────────────────────────────────────


@router.get("/health")
async def security_health():
    """Full subsystem health check."""

    # Check all modules
    modules = {}

    try:
        from app.onchain_analyzer import get_w3

        w3 = get_w3("ethereum")
        modules["onchain_analyzer"] = (
            "connected" if w3 and w3.is_connected() else "disconnected"
        )
    except Exception as e:
        modules["onchain_analyzer"] = f"error: {str(e)[:30]}"

    try:
        import sklearn

        modules["ml_anomaly"] = f"sklearn {sklearn.__version__}"
    except ImportError:
        modules["ml_anomaly"] = "sklearn not installed"

    try:
        import slither_analyzer

        modules["contract_deepscan"] = f"slither {slither_analyzer.__version__}"
    except ImportError:
        modules["contract_deepscan"] = "slither not installed"

    # Redis
    try:
        r = await _get_redis()
        modules["redis"] = "connected" if r and await r.ping() else "disconnected"
    except Exception:
        modules["redis"] = "disconnected"

    return {
        "status": "operational",
        "modules": modules,
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Redis helper for health check
async def _get_redis():
    try:
        import redis.asyncio as redis_async

        return redis_async.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
        )
    except Exception:
        return None
