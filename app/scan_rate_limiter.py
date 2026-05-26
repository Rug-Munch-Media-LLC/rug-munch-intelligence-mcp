"""
RMI Freemium Scan Rate Limiter
===============================
- 5 free token/wallet scans per day per identity (IP for anonymous, user ID for auth)
- Premium users: unlimited or per-tier limits
- Internal/cron API key: unlimited bypass
- x402 paid calls: bypass (already paid)
- Returns clear upsell messaging when limit is hit
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

import redis

logger = logging.getLogger(__name__)

# ── Configuration ──

FREE_DAILY_LIMIT = int(os.getenv("FREE_SCAN_LIMIT", "5"))
PRO_DAILY_LIMIT = int(os.getenv("PRO_SCAN_LIMIT", "100"))
ELITE_DAILY_LIMIT = int(os.getenv("ELITE_SCAN_LIMIT", "0"))  # 0 = unlimited

INTERNAL_API_KEY = os.getenv("RMI_INTERNAL_KEY", "rmi-internal-2026")

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = os.getenv("REDIS_USAGE_DB", "2")  # Separate DB for usage tracking

# Pricing
SCAN_PACKS = {
    "starter": {"scans": 25, "price_usd": 4.99, "price_atoms": "4990000", "description": "25 token/wallet scans"},
    "pro_monthly": {"scans": 0, "price_usd": 29.99, "price_atoms": "29990000", "description": "Unlimited scans for 30 days (PRO tier)"},
    "elite_monthly": {"scans": 0, "price_usd": 99.99, "price_atoms": "99990000", "description": "Unlimited scans for 30 days + SENTINEL deep modules"},
}

PREMIUM_UPSELL = {
    "free_limit_reached": {
        "message": f"You've used your {FREE_DAILY_LIMIT} free scans for today. Upgrade to PRO for 100 scans/day or unlimited with ELITE.",
        "upgrade_url": "https://rugmunch.io/pricing",
        "tiers": {
            "free": {"daily_limit": FREE_DAILY_LIMIT, "price": "$0", "features": ["5 scans/day", "Basic safety score", "DexScreener data"]},
            "pro": {"daily_limit": PRO_DAILY_LIMIT, "price": "$29.99/mo", "features": ["100 scans/day", "Full risk analysis", "Mint/freeze authority", "Honeypot detection", "LP verification"]},
            "elite": {"daily_limit": "unlimited", "price": "$99.99/mo", "features": ["Unlimited scans", "All 12 SENTINEL modules", "Bundle detection", "MEV analysis", "Whale tracking", "Dev reputation"]},
            "scan_packs": {k: {"price": v["price_usd"], "scans": v["scans"] or "unlimited", "description": v["description"]} for k, v in SCAN_PACKS.items()},
        },
    }
}


def _get_redis() -> redis.Redis:
    """Get Redis connection for usage tracking."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=int(REDIS_DB),
        decode_responses=True,
    )


def _today_key() -> str:
    """Return today's date key for Redis."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _identity_key(identity_type: str, identity: str) -> str:
    """Build Redis key for an identity's daily usage."""
    return f"rmi:scan_usage:{_today_key()}:{identity_type}:{identity}"


def check_scan_limit(
    identity: str,
    identity_type: str = "ip",
    tier: str = "free",
    is_internal: bool = False,
    is_x402_paid: bool = False,
) -> Dict[str, Any]:
    """
    Check if a scan request is within limits.
    
    Args:
        identity: IP address or user ID
        identity_type: "ip" or "user"
        tier: "free", "pro", "elite"
        is_internal: True for internal/cron calls (bypass all limits)
        is_x402_paid: True for x402 paid calls (bypass all limits)
    
    Returns:
        {"allowed": bool, "remaining": int, "limit": int, "upsell": dict|None}
    """
    # Internal calls and x402 paid calls always pass
    if is_internal or is_x402_paid:
        return {"allowed": True, "remaining": -1, "limit": -1, "upsell": None}

    # Determine daily limit
    if tier == "elite":
        daily_limit = ELITE_DAILY_LIMIT  # 0 = unlimited
    elif tier == "pro":
        daily_limit = PRO_DAILY_LIMIT  # 100
    else:
        daily_limit = FREE_DAILY_LIMIT  # 5

    # Unlimited (elite)
    if daily_limit == 0:
        return {"allowed": True, "remaining": -1, "limit": 0, "upsell": None}

    # Check Redis for today's usage
    try:
        r = _get_redis()
        key = _identity_key(identity_type, identity)
        current = int(r.get(key) or "0")

        if current >= daily_limit:
            upsell = PREMIUM_UPSELL["free_limit_reached"]
            # Add usage stats to upsell
            upsell_with_stats = {
                **upsell,
                "scans_used": current,
                "daily_limit": daily_limit,
                "resets_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z"),
            }
            return {
                "allowed": False,
                "remaining": 0,
                "limit": daily_limit,
                "upsell": upsell_with_stats,
            }

        return {
            "allowed": True,
            "remaining": daily_limit - current,
            "limit": daily_limit,
            "upsell": None,
        }

    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # On Redis failure, allow the scan (fail open, not closed)
        return {"allowed": True, "remaining": FREE_DAILY_LIMIT, "limit": FREE_DAILY_LIMIT, "upsell": None}


def increment_scan_usage(
    identity: str,
    identity_type: str = "ip",
    tier: str = "free",
    is_internal: bool = False,
    is_x402_paid: bool = False,
) -> Dict[str, Any]:
    """
    Record a scan usage. Call AFTER a successful scan.
    
    Returns:
        {"recorded": bool, "total_today": int, "remaining": int}
    """
    # Don't track internal or x402 paid calls
    if is_internal or is_x402_paid:
        return {"recorded": False, "total_today": 0, "remaining": -1}

    daily_limit = ELITE_DAILY_LIMIT if tier == "elite" else (PRO_DAILY_LIMIT if tier == "pro" else FREE_DAILY_LIMIT)

    try:
        r = _get_redis()
        key = _identity_key(identity_type, identity)
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400 * 2)  # Expire after 2 days
        results = pipe.execute()
        total = results[0]
        remaining = (daily_limit - total) if daily_limit > 0 else -1

        return {"recorded": True, "total_today": total, "remaining": max(0, remaining)}

    except Exception as e:
        logger.error(f"Usage recording failed: {e}")
        return {"recorded": False, "total_today": 0, "remaining": -1}


def get_usage_stats(identity: str, identity_type: str = "ip") -> Dict[str, Any]:
    """Get today's usage stats for an identity."""
    try:
        r = _get_redis()
        key = _identity_key(identity_type, identity)
        current = int(r.get(key) or "0")
        return {
            "identity": identity,
            "identity_type": identity_type,
            "scans_today": current,
            "free_limit": FREE_DAILY_LIMIT,
            "pro_limit": PRO_DAILY_LIMIT,
            "elite_limit": "unlimited",
            "remaining_free": max(0, FREE_DAILY_LIMIT - current),
            "resets_at": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z"),
        }
    except Exception as e:
        logger.error(f"Usage stats failed: {e}")
        return {"identity": identity, "scans_today": 0, "error": str(e)}


def is_internal_request(request) -> bool:
    """Check if request is from internal/cron (API key header or internal IP)."""
    # Check internal API key header
    api_key = request.headers.get("X-RMI-Key", "") if hasattr(request, "headers") else ""
    if api_key == INTERNAL_API_KEY:
        return True

    # Check for x402 payment (already paid)
    x402_version = request.headers.get("X-Payment-Version", "") if hasattr(request, "headers") else ""
    if x402_version:
        return False  # x402 is not internal, but it's paid — handled separately

    # Check for authenticated user (Authorization header)
    auth = request.headers.get("Authorization", "") if hasattr(request, "headers") else ""
    if auth.startswith("Bearer "):
        return False  # Authenticated user — check their tier

    return False


def get_identity(request) -> Tuple[str, str]:
    """
    Extract identity from request. Returns (identity, identity_type).
    
    Authenticated users: user ID from JWT
    Anonymous: IP address
    """
    # Try JWT auth first
    auth = request.headers.get("Authorization", "") if hasattr(request, "headers") else ""
    if auth.startswith("Bearer "):
        try:
            from app.auth import _verify_jwt
            payload = _verify_jwt(auth[7:])
            if payload:
                return payload.get("id", auth[7:][:32]), "user"
        except Exception:
            pass

    # Fall back to IP
    client_ip = request.client.host if hasattr(request, "client") and request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For", "") if hasattr(request, "headers") else ""
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    return client_ip, "ip"


def is_x402_paid_request(request) -> bool:
    """Check if request has a valid x402 payment (handled by enforcement middleware)."""
    # x402 middleware sets this header after successful payment verification
    x402_paid = request.headers.get("X-Payment-Verified", "") if hasattr(request, "headers") else ""
    return x402_paid.lower() == "true"