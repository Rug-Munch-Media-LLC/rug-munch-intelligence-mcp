#!/usr/bin/env python3
"""
RMI Supabase API Router — Exposes all platform tables via REST endpoints.
Frontend connects here for live, real-time data from Supabase.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.services.supabase_service import (
    get_alerts, create_alert, acknowledge_alert,
    get_wallets, get_wallet, upsert_wallet,
    get_wallet_intel, get_wallet_connections,
    get_syndicate_wallets,
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    get_tokens, get_token, upsert_token,
    get_entity_clusters, get_cluster_wallets,
    get_transactions,
    get_market_data, store_market_data,
    get_subscription,
    track_event, check_health,
)

router = APIRouter(prefix="/api/v1")

# ── Models ────────────────────────────────────────────────────

class WalletUpsert(BaseModel):
    address: str
    chain: str = "ethereum"
    label: Optional[str] = None
    risk_score: Optional[int] = None
    tags: Optional[List[str]] = None
    balance_usd: Optional[float] = None
    metadata: Optional[dict] = None

class WatchlistItem(BaseModel):
    user_id: str
    wallet_address: str
    chain: str = "ethereum"
    tags: Optional[List[str]] = None

class MarketDataIn(BaseModel):
    source: str
    data_type: str
    data: dict

# ═════════════════════════════════════════════════════════
# ALERTS
# ═════════════════════════════════════════════════════════

@router.get("/alerts")
async def alerts(
    severity: str = Query(None),
    user_id: str = Query(None),
    limit: int = Query(50, ge=1, le=500),
    unread: bool = Query(False)
):
    data = await get_alerts(severity=severity, user_id=user_id, limit=limit, unread_only=unread)
    return {"alerts": data, "total": len(data)}

@router.post("/alerts")
async def create_alert_endpoint(
    title: str, description: str, severity: str = "medium",
    alert_type: str = "security", chain: str = Query(None),
    token: str = Query(None), wallet: str = Query(None),
    amount_usd: float = Query(None), user_id: str = Query(None)
):
    result = await create_alert(
        title=title, description=description, severity=severity,
        alert_type=alert_type, chain=chain, token=token,
        wallet=wallet, amount_usd=amount_usd, user_id=user_id
    )
    if not result:
        raise HTTPException(status_code=500, detail="Create failed")
    return result

@router.post("/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str):
    ok = await acknowledge_alert(alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "acknowledged"}

# ═════════════════════════════════════════════════════════
# WALLETS
# ═════════════════════════════════════════════════════════

@router.get("/wallets")
async def wallets(
    chain: str = Query(None),
    risk_min: int = Query(None), risk_max: int = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    data = await get_wallets(chain=chain, risk_min=risk_min, risk_max=risk_max, limit=limit)
    return {"wallets": data, "total": len(data)}

@router.get("/wallets/{address}")
async def wallet_detail(address: str, chain: str = Query("ethereum")):
    wallet = await get_wallet(address, chain)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    # Enrich with intel and transactions
    intel = await get_wallet_intel(address=address, chain=chain, limit=1)
    txns = await get_transactions(wallet_address=address, chain=chain, limit=20)
    return {"wallet": wallet, "intel": intel[0] if intel else None, "transactions": txns}

@router.post("/wallets")
async def wallet_upsert(w: WalletUpsert):
    result = await upsert_wallet(
        w.address, w.chain,
        label=w.label, risk_score=w.risk_score,
        tags=w.tags, balance_usd=w.balance_usd, metadata=w.metadata
    )
    if not result:
        raise HTTPException(status_code=500, detail="Upsert failed")
    return result

@router.get("/wallets/{address}/connections")
async def wallet_connections(address: str):
    connections = await get_wallet_connections(address)
    return {"address": address, "connections": connections, "count": len(connections)}

# ═════════════════════════════════════════════════════════
# SYNDICATE WALLETS
# ═════════════════════════════════════════════════════════

@router.get("/syndicate")
async def syndicates(
    status: str = Query(None),
    chain: str = Query(None),
    limit: int = Query(200, ge=1, le=500)
):
    data = await get_syndicate_wallets(status=status, chain=chain, limit=limit)
    return {"syndicate_wallets": data, "total": len(data)}

# ═════════════════════════════════════════════════════════
# WATCHLIST
# ═════════════════════════════════════════════════════════

@router.get("/watchlist/{user_id}")
async def watchlist(user_id: str):
    data = await get_watchlist(user_id)
    return {"watchlist": data, "total": len(data)}

@router.post("/watchlist")
async def watchlist_add(item: WatchlistItem):
    result = await add_to_watchlist(item.user_id, item.wallet_address, item.chain, item.tags)
    if not result:
        raise HTTPException(status_code=500, detail="Add failed")
    return result

@router.delete("/watchlist/{user_id}/{wallet_address}")
async def watchlist_remove(user_id: str, wallet_address: str, chain: str = Query("ethereum")):
    ok = await remove_from_watchlist(user_id, wallet_address, chain)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "removed"}

# ═════════════════════════════════════════════════════════
# TOKENS
# ═════════════════════════════════════════════════════════

@router.get("/tokens")
async def tokens(
    chain: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    order: str = Query("volume_24h.desc")
):
    data = await get_tokens(chain=chain, limit=limit, order_by=order)
    return {"tokens": data, "total": len(data)}

@router.get("/tokens/discover")
async def token_discover(chains: str = Query("solana,ethereum,base,bsc")):
    """Discover new token launches across chains via DexScreener + GeckoTerminal."""
    chain_list = [c.strip() for c in chains.split(",") if c.strip()]
    from app.token_discovery import discover_tokens
    try:
        discovered = await discover_tokens(chains=chain_list)
        total = sum(len(tokens) for tokens in discovered.values())
        return {"chains": discovered, "total": total}
    except Exception as e:
        return {"error": str(e), "chains": {}, "total": 0}

@router.get("/tokens/{address}")
async def token_detail(address: str, chain: str = Query("ethereum")):
    token = await get_token(address, chain)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token

# ═════════════════════════════════════════════════════════
# ENTITY CLUSTERS
# ═════════════════════════════════════════════════════════

@router.get("/clusters")
async def clusters(limit: int = Query(50, ge=1, le=200)):
    data = await get_entity_clusters(limit=limit)
    return {"clusters": data, "total": len(data)}

@router.get("/clusters/{cluster_id}")
async def cluster_detail(cluster_id: str):
    addresses = await get_cluster_wallets(cluster_id)
    return {"cluster_id": cluster_id, "addresses": addresses, "count": len(addresses)}

# ═════════════════════════════════════════════════════════
# TRANSACTIONS
# ═════════════════════════════════════════════════════════

@router.get("/transactions/{wallet_address}")
async def transactions(wallet_address: str, chain: str = Query(None), limit: int = Query(50)):
    data = await get_transactions(wallet_address=wallet_address, chain=chain, limit=limit)
    return {"transactions": data, "total": len(data)}

# ═════════════════════════════════════════════════════════
# MARKET DATA
# ═════════════════════════════════════════════════════════

@router.get("/market-data/{data_type}")
async def market_data(data_type: str, limit: int = Query(10)):
    data = await get_market_data(data_type=data_type, limit=limit)
    return {"data": data, "total": len(data)}

@router.post("/market-data")
async def market_data_store(m: MarketDataIn):
    result = await store_market_data(m.source, m.data_type, m.data)
    if not result:
        raise HTTPException(status_code=500, detail="Store failed")
    return result

# ═════════════════════════════════════════════════════════
# SUBSCRIPTIONS
# ═════════════════════════════════════════════════════════

@router.get("/subscriptions/{user_id}")
async def subscription(user_id: str):
    sub = await get_subscription(user_id)
    if not sub:
        return {"plan": "FREE", "status": "none"}
    return sub

# ═════════════════════════════════════════════════════════
# ANALYTICS
# ═════════════════════════════════════════════════════════

@router.post("/analytics/event")
async def analytics_event(
    event_type: str, user_id: str = Query(None),
    event_data: str = Query("{}"), page: str = Query(None)
):
    import json
    try:
        data = json.loads(event_data)
    except:
        data = {"raw": event_data}
    result = await track_event(event_type=event_type, user_id=user_id, event_data=data, page=page)
    return {"status": "tracked", "id": result.get("id") if result else None}

# ═════════════════════════════════════════════════════════
# HEALTH
# ═════════════════════════════════════════════════════════

@router.get("/health/supabase")
async def supabase_health():
    return await check_health()

@router.get("/health")
async def full_health():
    sb = await check_health()
    tables = ["wallets", "alerts", "watchlist", "tokens", "bulletin_posts", "badges", "syndicate_wallets", "entity_clusters"]
    return {
        "supabase": sb,
        "timestamp": datetime.now().isoformat(),
        "tables_monitored": tables
    }
