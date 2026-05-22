"""
RugMaps API Router — RMI's interactive wallet visualization.
Self-contained engine, no BubbleMaps.com API dependency.
Connects to /api/v1/rugmaps/*
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter(prefix="/api/v1/rugmaps", tags=["rugmaps"])


class RugMapsRequest(BaseModel):
    center_wallet: str
    depth: int = 2
    min_strength: float = 0.1


def _get_rm():
    try:
        from app.bubble_maps import get_bubble_maps_pro
        return get_bubble_maps_pro()
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Module unavailable: {e}")


@router.post("/map")
async def generate_rug_map(req: RugMapsRequest):
    """Generate interactive RugMap for a wallet (2-hop default)."""
    rm = _get_rm()
    try:
        result = await rm.generate_map(
            center_wallet=req.center_wallet,
            depth=min(req.depth, 5),
            min_strength=req.min_strength
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:500])


@router.get("/analyze/{address}")
async def analyze_wallet(
    address: str,
    depth: int = Query(2, ge=1, le=5)
):
    """Quick wallet analysis with RugMaps data."""
    rm = _get_rm()
    result = await rm.generate_map(center_wallet=address, depth=depth)
    d = result.to_dict()
    return {
        "address": address,
        "node_count": len(d.get("nodes", [])),
        "link_count": len(d.get("links", [])),
        "risk_level": d.get("risk_level", "unknown"),
        "risk_score": d.get("risk_score", 0),
        "stats": d.get("stats", {}),
        "top_counterparties": [
            n["address"][:12] + "..." for n in d.get("nodes", []) if n.get("layer") == 1
        ][:10]
    }


@router.get("/entity/{address}")
async def get_entity_info(address: str):
    """Get entity information for an address."""
    rm = _get_rm()
    info = await rm._get_entity_info(address)
    risk, level = await rm._calculate_risk(address)
    return {"address": address, "entity": info, "risk_score": risk, "risk_level": level}


@router.get("/health")
async def rugmaps_health():
    return {"status": "ok", "service": "rugmaps-engine"}