"""
Wallet Clustering API Router — Cluster detection, funding paths, risk analysis.
Connects to /api/v1/wallet-clusters/*
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple
import logging

router = APIRouter(prefix="/api/v1/wallet-clusters", tags=["wallet-clustering"])
logger = logging.getLogger(__name__)


class ClusterRequest(BaseModel):
    wallets: List[str]
    min_confidence: float = 0.3
    include_sleepers: bool = True


class FundingPathRequest(BaseModel):
    source: str
    target: str
    max_depth: int = 5


class BubblemapRequest(BaseModel):
    center_wallet: str
    depth: int = 2


class ContractScanRequest(BaseModel):
    contract_address: str
    chain: str = "solana"
    detect_clusters: bool = True
    detect_bundles: bool = True


def _get_detector():
    try:
        from app.cluster_detection import ClusterDetectionPro
        return ClusterDetectionPro()
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Module unavailable: {e}")


def _get_engine():
    try:
        from app.wallet_clustering import get_clustering_engine
        return get_clustering_engine()
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Module unavailable: {e}")


@router.post("/detect")
async def detect_clusters(req: ClusterRequest):
    """Detect wallet clusters from a list of addresses (7 methods)."""
    if len(req.wallets) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 wallets")
    if len(req.wallets) > 100:
        raise HTTPException(status_code=400, detail="Max 100 wallets per request")

    detector = _get_detector()
    clusters = await detector.detect_clusters(
        wallets=req.wallets,
        min_confidence=req.min_confidence,
        include_sleepers=req.include_sleepers
    )
    return {
        "total_wallets": len(req.wallets),
        "clusters_found": len(clusters),
        "clusters": [c.to_dict() for c in clusters]
    }


@router.post("/funding-path")
async def trace_funding_path(req: FundingPathRequest):
    """Trace the funding path between two wallets (BFS)."""
    detector = _get_detector()
    path = await detector.trace_funding_path(
        source=req.source,
        target=req.target,
        max_depth=req.max_depth
    )
    if path:
        return {"source": req.source, "target": req.target, "path": path.to_dict()}
    return {"source": req.source, "target": req.target, "path": None, "note": "No path found"}


@router.post("/scan")
async def scan_all():
    """Run all 4 clustering methods and return merged results."""
    engine = _get_engine()
    clusters = engine.find_all_clusters()
    return {
        "clusters": [c.to_dict() for c in clusters],
        "total_clusters": len(clusters)
    }


@router.get("/health")
async def clustering_health():
    cache_stats = {}
    gnn_status = {}
    spam_stats = {}
    try:
        from app.chain_cache import get_chain_cache
        cache_stats = await get_chain_cache().stats()
    except Exception:
        pass
    try:
        from app.fraud_gnn import get_fraud_gnn
        gnn_status = get_fraud_gnn().status()
    except Exception:
        gnn_status = {"error": "unavailable"}
    try:
        from app.spam_registry import get_spam_registry
        spam_stats = get_spam_registry().stats()
    except Exception:
        spam_stats = {"error": "unavailable"}
    return {
        "status": "ok",
        "service": "wallet-clustering-engine",
        "cache": cache_stats,
        "gnn": gnn_status,
        "spam_registry": spam_stats,
    }


@router.get("/report/{cluster_id}")
async def get_cluster_report(cluster_id: str):
    """Get detailed report for a specific cluster."""
    engine = _get_engine()
    report = engine.get_cluster_report(cluster_id)
    if not report:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return report


@router.post("/bubble-map-data")
async def get_bubble_map_data(req: BubblemapRequest):
    """Generate bubble map data for a wallet (2-hop by default)."""
    engine = _get_engine()
    data = engine.generate_bubble_map_data(
        center_wallet=req.center_wallet,
        depth=min(req.depth, 5)
    )
    return data


@router.post("/contract-scan")
async def scan_contract_clusters(req: ContractScanRequest):
    """Scan a contract for wallet clusters among its holders.
    Finds real holder wallets via Helius, then detects clusters."""
    engine = _get_engine()
    detector = _get_detector()

    # Step 1: Get real holders from chain (multi-source fallback)
    holders: List[str] = []
    try:
        from app.unified_provider import get_unified_provider
        provider = get_unified_provider()
        holder_data = await provider.get_token_holders(req.contract_address, limit=30)
        holders = [h.get("address") for h in holder_data if h.get("address")]

        # Filter out exchange/DeFi infrastructure
        excluded_entities = []
        try:
            from app.entity_registry import get_entity_registry
            registry = get_entity_registry()
            holders, excluded_entities = registry.filter_infrastructure(holders)
        except Exception as e:
            logger.debug(f"Entity filter skipped: {e}")

    except Exception as e:
        logger.warning(f"Provider failed: {e}")

    # Step 2: Feed transactions for holders into engine
    if holders and req.detect_clusters:
        try:
            from app.unified_provider import get_unified_provider
            provider = get_unified_provider()
            for h in holders[:5]:  # Limit API calls — feed top 5 holders
                txs = await provider.get_wallet_transactions(h, limit=10)
                from app.wallet_clustering import Transaction
                from datetime import datetime, timezone
                for t in txs:
                    ts = t.get("timestamp")
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
                    engine.add_transaction(Transaction(
                        signature=t.get("signature", ""),
                        timestamp=dt,
                        from_address=h,
                        to_address="unknown",
                        amount=0,
                        token="SOL",
                        program="system"
                    ))
        except Exception as e:
            logger.warning(f"Feed failed: {e}")

    result = {
        "contract": req.contract_address,
        "chain": req.chain,
        "total_holders": len(holders) + len(excluded_entities),
        "holders": holders[:10],
        "excluded_infrastructure": [
            {"address": e.address, "entity": e.entity_name, "type": e.entity_type}
            for e in excluded_entities
        ],
        "holders_labeled": sum(1 for h in holders if engine._get_known_scammer_wallets()),
        "spam_check": {},
    }

    # Spam/sanctions check
    try:
        from app.spam_registry import get_spam_registry
        sr = get_spam_registry()
        result["spam_check"] = sr.check_token(req.contract_address, req.chain)
    except Exception as e:
        logger.debug(f"Spam check skipped: {e}")

    # Step 3: Detect clusters
    if req.detect_clusters and len(holders) >= 2:
        clusters = await detector.detect_clusters(
            wallets=holders[:50],
            min_confidence=0.3,
            include_sleepers=True
        )
        result["clusters_found"] = len(clusters)
        result["clusters"] = [c.to_dict() for c in clusters]

        # GNN fraud scoring on cluster wallets
        if clusters:
            try:
                from app.fraud_gnn import get_fraud_gnn
                gnn = get_fraud_gnn()
                all_wallets = [w for c in clusters for w in c.wallets]
                fps = [{"address": w, "tx_count": 1} for w in all_wallets[:20]]
                gnn_scores = gnn.score_wallets(fps)
                high_risk = [s for s in gnn_scores if s.get("fraud_probability", 0) >= 0.5]
                result["gnn_scoring"] = {
                    "wallets_scored": len(gnn_scores),
                    "high_risk_count": len(high_risk),
                    "avg_fraud_probability": round(
                        sum(s.get("fraud_probability", 0) for s in gnn_scores) / max(len(gnn_scores), 1), 4
                    ),
                    "model": gnn.status().get("model_type", "unknown"),
                }
            except Exception as e:
                logger.debug(f"GNN scoring skipped: {e}")

    # Step 4: Bundle detection
    if req.detect_bundles and holders:
        try:
            from app.bundle_detector import get_bundle_detector
            bd = get_bundle_detector()
            bundle = await bd.detect(
                token_address=req.contract_address,
                chain=req.chain,
                holders=holder_data,
                transactions=None  # TODO: feed real tx data
            )
            result["bundle_detection"] = {
                "is_bundled": bundle.is_bundled,
                "confidence": bundle.confidence,
                "risk_label": bundle.risk_label,
                "signals": {
                    "atomic_block": bundle.atomic_block_score,
                    "common_funder": bundle.common_funder_score,
                    "temporal": bundle.temporal_score,
                    "distribution_anomaly": bundle.distribution_anomaly_score,
                    "concentration": bundle.concentration_score,
                },
                "details": {
                    "top10_pct": bundle.top10_holder_pct,
                    "top3_pct": bundle.top3_holder_pct,
                    "identical_amounts": bundle.identical_amount_count,
                    "round_amounts": bundle.round_amount_count,
                    "holder_count": bundle.holder_count,
                    "common_funder": bundle.common_funder_address,
                }
            }
        except Exception as e:
            logger.warning(f"Bundle detection failed: {e}")

    return result