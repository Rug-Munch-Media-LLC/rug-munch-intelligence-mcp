"""Stub crypto_guard - wallet reputation and auth"""
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException

def check_wallet_reputation(address: str, chain: str = "base") -> Dict[str, Any]:
    """Check wallet reputation."""
    return {
        "address": address,
        "chain": chain,
        "reputation": "neither_good_nor_bad",
        "risk_score": 0,
        "flags": [],
    }

def rate_limit_by_tier(user_tier: str, endpoint: str) -> Dict[str, Any]:
    """Apply rate limiting based on user tier."""
    limits = {
        "FREE": {"requests_per_hour": 10, "daily_limit": 100},
        "BASIC": {"requests_per_hour": 50, "daily_limit": 500},
        "PREMIUM": {"requests_per_hour": 200, "daily_limit": 2000},
    }
    return {"tier": user_tier, "endpoint": endpoint, **limits.get(user_tier, limits["FREE"])}

async def require_crypto_auth(request: Request) -> Dict[str, Any]:
    """Require crypto authentication."""
    auth = request.headers.get("Authorization", "")
    if not auth:
        raise HTTPException(status_code=401, detail="Crypto auth required")
    return {"authenticated": True, "wallet": "unknown"}
