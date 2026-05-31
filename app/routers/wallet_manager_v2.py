"""
RMI Wallet Manager v2 API Router
===================================
Full REST API for enterprise wallet management.

Endpoints:
  POST /api/v1/wallets/v2/generate           — Generate new wallet
  POST /api/v1/wallets/v2/generate/hd        — Generate HD wallet
  POST /api/v1/wallets/v2/generate/batch     — Batch generate wallets
  GET  /api/v1/wallets/v2                    — List wallets
  GET  /api/v1/wallets/v2/{wallet_id}       — Get wallet details
  PUT  /api/v1/wallets/v2/{wallet_id}        — Update wallet
  DELETE /api/v1/wallets/v2/{wallet_id}      — Archive wallet
  POST /api/v1/wallets/v2/{wallet_id}/rotate — Rotate wallet
  POST /api/v1/wallets/v2/{wallet_id}/schedule — Schedule rotation
  POST /api/v1/wallets/v2/{wallet_id}/balance — Update balance
  POST /api/v1/wallets/v2/{wallet_id}/x402   — Enable x402 payments
  POST /api/v1/wallets/v2/{wallet_id}/subscription — Enable subscriptions
  GET  /api/v1/wallets/v2/stats              — Wallet statistics
  GET  /api/v1/wallets/v2/alerts             — Wallet alerts
  GET  /api/v1/wallets/v2/payments           — Payment history
  POST /api/v1/wallets/v2/payments           — Record payment
  GET  /api/v1/wallets/v2/export             — Export wallets
  GET  /api/v1/wallets/v2/rotations/due      — Check rotations due
  POST /api/v1/wallets/v2/rotations/process  — Process due rotations
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Body, Query
from pydantic import BaseModel, Field

from app.wallet_manager_v2 import (
    WalletManagerV2, WalletRecord, PaymentRecord,
    WalletPurpose, WalletTier, WalletStatus, PaymentType,
    WalletRotationSchedule, get_wallet_manager_v2,
)
from app.admin_backend import require_admin, AuditLogger

logger = logging.getLogger("wallet_api_v2")

router = APIRouter(prefix="/api/v1/wallets/v2", tags=["wallet-manager-v2"])

# ── Models ────────────────────────────────────────────────────

class GenerateWalletRequest(BaseModel):
    chain: str = Field(..., description="Chain key (eth, sol, trx, btc, etc.)")
    name: str = Field(default="", description="Wallet name")
    purpose: str = Field(default="operations", description="Wallet purpose")
    tier: str = Field(default="warm", description="Security tier: hot, warm, cold, vault")
    tags: List[str] = Field(default_factory=list)
    group: str = Field(default="default")

class GenerateHDRequest(BaseModel):
    chain: str = Field(...)
    name: str = Field(default="")
    purpose: str = Field(default="operations")
    tier: str = Field(default="warm")
    mnemonic: str = Field(default="", description="Optional mnemonic (auto-generated if empty)")
    account_index: int = Field(default=0)
    address_index: int = Field(default=0)

class BatchGenerateRequest(BaseModel):
    chains: List[str] = Field(..., description="List of chain keys")
    name_prefix: str = Field(default="")
    purpose: str = Field(default="operations")
    tier: str = Field(default="warm")

class UpdateWalletRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    tier: Optional[str] = None
    tags: Optional[List[str]] = None
    group: Optional[str] = None
    low_balance_threshold: Optional[float] = None
    alert_threshold_usd: Optional[float] = None
    notes: Optional[str] = None

class RotateRequest(BaseModel):
    transfer_balance: bool = Field(default=False)

class ScheduleRotationRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=365)
    auto_rotate: bool = Field(default=False)
    notify_before_days: int = Field(default=7)

class BalanceUpdateRequest(BaseModel):
    balance_raw: str = Field(default="0")
    balance_decimal: float = Field(default=0.0)
    balance_usd: float = Field(default=0.0)
    token_balances: Optional[Dict[str, Dict]] = None

class PaymentRecordRequest(BaseModel):
    wallet_id: str = Field(...)
    wallet_address: str = Field(...)
    chain: str = Field(...)
    payment_type: str = Field(...)
    amount: float = Field(default=0.0)
    amount_usd: float = Field(default=0.0)
    token: str = Field(default="")
    from_address: str = Field(default="")
    to_address: str = Field(default="")
    tx_hash: str = Field(default="")
    user_id: str = Field(default="")
    user_email: str = Field(default="")
    tool_id: str = Field(default="")
    tool_name: str = Field(default="")
    x402_resource: str = Field(default="")
    x402_facet: str = Field(default="")
    metadata: Optional[Dict[str, Any]] = None

class X402EnableRequest(BaseModel):
    price_usd: float = Field(default=0.01)

class SubscriptionEnableRequest(BaseModel):
    tiers: List[str] = Field(default_factory=lambda: ["free", "basic", "pro", "enterprise"])


# ── Helper ────────────────────────────────────────────────────

def _get_manager() -> WalletManagerV2:
    """Get wallet manager instance."""
    return get_wallet_manager_v2(os.getenv("WALLET_VAULT_PASSWORD", ""))


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/generate")
async def generate_wallet(request: Request, body: GenerateWalletRequest):
    """Generate a new wallet."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    wallet = manager.generate_wallet(
        chain=body.chain,
        name=body.name,
        purpose=body.purpose,
        tier=body.tier,
        tags=body.tags,
        group=body.group,
        created_by=admin["id"],
    )
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.generate",
        resource_type="wallet",
        resource_id=wallet.wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"chain": wallet.chain, "address": wallet.address, "purpose": wallet.purpose},
    )
    
    return {"success": True, "wallet": wallet.to_safe_dict()}


@router.post("/generate/hd")
async def generate_hd_wallet(request: Request, body: GenerateHDRequest):
    """Generate HD wallet from mnemonic."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    wallet = manager.generate_hd_wallet(
        chain=body.chain,
        mnemonic=body.mnemonic,
        account_index=body.account_index,
        address_index=body.address_index,
        name=body.name,
        purpose=body.purpose,
        tier=body.tier,
        created_by=admin["id"],
    )
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.generate_hd",
        resource_type="wallet",
        resource_id=wallet.wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"chain": wallet.chain, "address": wallet.address, "hd": True},
    )
    
    return {"success": True, "wallet": wallet.to_safe_dict()}


@router.post("/generate/batch")
async def batch_generate(request: Request, body: BatchGenerateRequest):
    """Batch generate wallets for multiple chains."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    wallets = []
    
    for chain in body.chains:
        wallet = manager.generate_wallet(
            chain=chain,
            name=f"{body.name_prefix} {chain.upper()}".strip(),
            purpose=body.purpose,
            tier=body.tier,
            created_by=admin["id"],
        )
        wallets.append(wallet.to_safe_dict())
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.generate_batch",
        resource_type="wallet",
        resource_id=f"batch_{len(wallets)}",
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"count": len(wallets), "chains": body.chains},
    )
    
    return {"success": True, "wallets": wallets, "count": len(wallets)}


@router.get("")
async def list_wallets(
    request: Request,
    chain: str = "",
    purpose: str = "",
    tier: str = "",
    status: str = "",
    group: str = "",
    x402_enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List wallets with filtering."""
    auth = await require_admin(request, "dashboard.read")
    
    manager = _get_manager()
    wallets = manager.list_wallets(
        chain=chain or None,
        purpose=purpose or None,
        tier=tier or None,
        status=status or None,
        group=group or None,
        x402_enabled=x402_enabled,
    )
    
    total = len(wallets)
    wallets = wallets[offset:offset + limit]
    
    return {
        "wallets": [w.to_safe_dict() for w in wallets],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{wallet_id}")
async def get_wallet(request: Request, wallet_id: str):
    """Get wallet details."""
    auth = await require_admin(request, "dashboard.read")
    
    manager = _get_manager()
    wallet = manager.get_wallet(wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return {"wallet": wallet.to_safe_dict()}


@router.put("/{wallet_id}")
async def update_wallet(request: Request, wallet_id: str, body: UpdateWalletRequest):
    """Update wallet metadata."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    
    wallet = manager.update_wallet(wallet_id, updates)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.update",
        resource_type="wallet",
        resource_id=wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state=updates,
    )
    
    return {"success": True, "wallet": wallet.to_safe_dict()}


@router.delete("/{wallet_id}")
async def delete_wallet(request: Request, wallet_id: str):
    """Archive a wallet."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    result = manager.delete_wallet(wallet_id)
    if not result:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.delete",
        resource_type="wallet",
        resource_id=wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    
    return {"success": True, "message": "Wallet archived"}


@router.post("/{wallet_id}/rotate")
async def rotate_wallet(request: Request, wallet_id: str, body: RotateRequest = Body(...)):
    """Rotate wallet to new address."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    new_wallet = manager.rotate_wallet(
        wallet_id=wallet_id,
        transfer_balance=body.transfer_balance,
        rotate_by=admin["id"],
    )
    if not new_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.rotate",
        resource_type="wallet",
        resource_id=wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"new_wallet_id": new_wallet.wallet_id, "new_address": new_wallet.address},
    )
    
    return {"success": True, "new_wallet": new_wallet.to_safe_dict()}


@router.post("/{wallet_id}/schedule")
async def schedule_rotation(request: Request, wallet_id: str, body: ScheduleRotationRequest):
    """Schedule automatic rotation."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    schedule = manager.schedule_rotation(
        wallet_id=wallet_id,
        days=body.days,
        auto=body.auto_rotate,
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.schedule_rotation",
        resource_type="wallet",
        resource_id=wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"days": body.days, "auto": body.auto_rotate},
    )
    
    return {"success": True, "schedule": schedule.to_dict()}


@router.post("/{wallet_id}/balance")
async def update_balance(request: Request, wallet_id: str, body: BalanceUpdateRequest):
    """Update wallet balance."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    
    manager = _get_manager()
    result = manager.update_balance(
        wallet_id=wallet_id,
        balance_raw=body.balance_raw,
        balance_decimal=body.balance_decimal,
        balance_usd=body.balance_usd,
        token_balances=body.token_balances,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return {"success": True}


@router.post("/{wallet_id}/x402")
async def enable_x402(request: Request, wallet_id: str, body: X402EnableRequest):
    """Enable x402 payment processing."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    result = manager.enable_x402(wallet_id, body.price_usd)
    if not result:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.enable_x402",
        resource_type="wallet",
        resource_id=wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"price_usd": body.price_usd},
    )
    
    return {"success": True, "x402_enabled": True, "price_usd": body.price_usd}


@router.post("/{wallet_id}/subscription")
async def enable_subscription(request: Request, wallet_id: str, body: SubscriptionEnableRequest):
    """Enable subscription payments."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    result = manager.enable_subscription(wallet_id, body.tiers)
    if not result:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.enable_subscription",
        resource_type="wallet",
        resource_id=wallet_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"tiers": body.tiers},
    )
    
    return {"success": True, "subscription_enabled": True, "tiers": body.tiers}


@router.get("/stats")
async def wallet_stats(request: Request):
    """Get wallet statistics."""
    auth = await require_admin(request, "dashboard.read")
    
    manager = _get_manager()
    stats = manager.get_stats()
    return {"stats": stats}


@router.get("/alerts")
async def wallet_alerts(request: Request):
    """Get wallet alerts."""
    auth = await require_admin(request, "dashboard.read")
    
    manager = _get_manager()
    alerts = manager.check_alerts()
    return {"alerts": alerts, "total": len(alerts)}


@router.get("/payments")
async def list_payments(
    request: Request,
    wallet_id: str = "",
    chain: str = "",
    payment_type: str = "",
    status: str = "",
    limit: int = 100,
):
    """List payment records."""
    auth = await require_admin(request, "financial.read", min_role="admin")
    
    manager = _get_manager()
    payments = manager.get_payments(
        wallet_id=wallet_id or None,
        chain=chain or None,
        payment_type=payment_type or None,
        status=status or None,
        limit=limit,
    )
    
    return {
        "payments": [p.to_dict() for p in payments],
        "total": len(payments),
    }


@router.post("/payments")
async def record_payment(request: Request, body: PaymentRecordRequest):
    """Record a payment."""
    auth = await require_admin(request, "financial.write", min_role="admin")
    admin = auth["admin"]
    
    payment = PaymentRecord(
        payment_id=f"pay_{int(time.time())}_{secrets.token_hex(4)}",
        wallet_id=body.wallet_id,
        wallet_address=body.wallet_address,
        chain=body.chain,
        payment_type=body.payment_type,
        amount=body.amount,
        amount_usd=body.amount_usd,
        token=body.token,
        from_address=body.from_address,
        to_address=body.to_address,
        tx_hash=body.tx_hash,
        user_id=body.user_id,
        user_email=body.user_email,
        tool_id=body.tool_id,
        tool_name=body.tool_name,
        x402_resource=body.x402_resource,
        x402_facet=body.x402_facet,
        created_at=datetime.now(timezone.utc).isoformat(),
        metadata=body.metadata or {},
    )
    
    manager = _get_manager()
    manager.record_payment(payment)
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="payment.record",
        resource_type="payment",
        resource_id=payment.payment_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"amount_usd": body.amount_usd, "type": body.payment_type},
    )
    
    return {"success": True, "payment": payment.to_dict()}


@router.get("/export")
async def export_wallets(request: Request, chain: str = ""):
    """Export wallet data (safe, no keys)."""
    auth = await require_admin(request, "dashboard.read")
    
    manager = _get_manager()
    if chain:
        data = manager.export_for_chain(chain)
    else:
        data = manager.export_safe()
    
    return {"export": data}


@router.get("/rotations/due")
async def rotations_due(request: Request):
    """Check wallets due for rotation."""
    auth = await require_admin(request, "token_deploy.read", min_role="admin")
    
    manager = _get_manager()
    due = manager.check_rotations_due()
    return {"rotations_due": [r.to_dict() for r in due], "count": len(due)}


@router.post("/rotations/process")
async def process_rotations(request: Request):
    """Process all due rotations."""
    auth = await require_admin(request, "token_deploy.write", min_role="admin")
    admin = auth["admin"]
    
    manager = _get_manager()
    due = manager.check_rotations_due()
    rotated = []
    
    for schedule in due:
        if schedule.auto_rotate:
            new_wallet = manager.rotate_wallet(
                wallet_id=schedule.wallet_id,
                rotate_by=admin["id"],
            )
            if new_wallet:
                rotated.append({
                    "old_wallet_id": schedule.wallet_id,
                    "new_wallet_id": new_wallet.wallet_id,
                    "new_address": new_wallet.address,
                })
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="wallet.process_rotations",
        resource_type="batch",
        resource_id="rotations",
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"processed": len(rotated), "due": len(due)},
    )
    
    return {"success": True, "rotated": rotated, "due_count": len(due), "processed_count": len(rotated)}
