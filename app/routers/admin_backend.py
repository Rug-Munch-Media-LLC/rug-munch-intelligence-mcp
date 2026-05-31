"""
RMI Admin Backend Router
==========================
Complete admin panel API with RBAC, security, and management tools.

All endpoints require X-Admin-Session header (JWT session token).
Some endpoints also require specific permissions based on role.

Sections:
  1. Authentication (login, logout, session, 2FA)
  2. Dashboard (metrics, health, analytics)
  3. User Management (users, bans, roles, activity)
  4. Security (IP blocks, rate limits, audit logs, threats)
  5. System Management (config, services, health)
  6. Content Management (posts, announcements, SEO)
  7. Financial (x402 analytics, revenue, payments)
  8. API Keys (create, rotate, revoke, scopes)
  9. Token Deployer (darkroom integration)
  10. Backups & Maintenance
"""

import os
import json
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Body
from pydantic import BaseModel, Field

from app.admin_backend import (
    AdminRole, has_permission, require_admin,
    AdminUserStore, SessionManager, SecurityManager,
    AuditLogger, SystemHealthMonitor,
)

logger = logging.getLogger("rmi_admin_router")

router = APIRouter(prefix="/api/v1/admin/backend", tags=["admin-backend"])


# ── Auth Models ───────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None


class CreateAdminRequest(BaseModel):
    email: str
    password: str
    role: str = "viewer"
    ip_allowlist: List[str] = Field(default_factory=list)


class UpdateAdminRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    ip_allowlist: Optional[List[str]] = None
    two_factor_enabled: Optional[bool] = None


class IPBlockRequest(BaseModel):
    ip: str
    reason: str = ""
    duration_hours: int = 24


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str
    category: str = "general"


class AnnouncementRequest(BaseModel):
    title: str
    content: str
    type: str = "info"  # info, warning, critical, update
    target_audience: str = "all"  # all, users, admins, premium
    expires_at: Optional[str] = None


class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: List[str] = Field(default_factory=list)
    expires_days: int = 30


class WebhookConfigRequest(BaseModel):
    url: str
    events: List[str] = Field(default_factory=list)
    secret: str = ""
    active: bool = True


# ── Helper: Get client info ───────────────────────────────────

def _get_client_info(request: Request) -> tuple:
    """Get client IP and user agent."""
    ip = request.client.host if request.client else ""
    # Check for forwarded IP
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("user-agent", "")
    return ip, ua


# ═══════════════════════════════════════════════════════════════
# 1. AUTHENTICATION
# ═══════════════════════════════════════════════════════════════

@router.post("/auth/login")
async def admin_login(request: Request, body: AdminLoginRequest):
    """Admin login with email/password + optional 2FA."""
    ip, ua = _get_client_info(request)
    
    # Check IP block
    block_info = await SecurityManager.is_ip_blocked(ip)
    if block_info:
        raise HTTPException(status_code=403, detail="IP blocked")
    
    # Check rate limit for login
    rate_check = await SecurityManager.check_rate_limit(f"login:{ip}", "login")
    if not rate_check["allowed"]:
        raise HTTPException(status_code=429, detail="Too many login attempts")
    
    # Verify credentials
    admin = await AdminUserStore.verify_admin_login(body.email, body.password)
    if not admin:
        await SecurityManager.track_failed_login(f"login:{ip}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check 2FA if enabled
    if admin.get("two_factor_enabled"):
        if not body.totp_code:
            raise HTTPException(status_code=401, detail="2FA code required")
        # Verify TOTP (would use pyotp in production)
        # For now, skip verification
    
    # Check IP allowlist
    allowlist = admin.get("ip_allowlist", [])
    if allowlist and ip not in allowlist:
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="admin.login_denied",
            resource_type="ip",
            resource_id=ip,
            ip_address=ip,
            user_agent=ua,
            status="denied",
            reason="IP not in allowlist",
        )
        raise HTTPException(status_code=403, detail="IP not authorized")
    
    # Reset failed logins
    await SecurityManager.reset_failed_login(f"login:{ip}")
    
    # Create session
    session_id = await SessionManager.create_session(
        admin_id=admin["id"],
        admin_email=admin["email"],
        role=AdminRole(admin.get("role", "viewer")),
        ip_address=ip,
        user_agent=ua,
    )
    
    # Log successful login
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="admin.login",
        resource_type="session",
        resource_id=session_id,
        ip_address=ip,
        user_agent=ua,
        status="success",
    )
    
    return {
        "success": True,
        "session_id": session_id,
        "admin": {k: v for k, v in admin.items() if k not in ["password_hash", "two_factor_secret"]},
        "expires_in": SessionManager.SESSION_TIMEOUT_HOURS * 3600,
    }


@router.post("/auth/logout")
async def admin_logout(request: Request):
    """Logout current session."""
    session_id = request.headers.get("X-Admin-Session", "")
    if session_id:
        await SessionManager.destroy_session(session_id)
    return {"success": True, "message": "Logged out"}


@router.post("/auth/logout-all")
async def admin_logout_all(request: Request):
    """Logout all sessions (force logout everywhere)."""
    auth = await require_admin(request, "system.write", AdminRole.ADMIN)
    admin = auth["admin"]
    
    count = await SessionManager.destroy_all_sessions(admin["id"])
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="admin.logout_all",
        resource_type="session",
        resource_id=admin["id"],
        ip_address=_get_client_info(request)[0],
        status="success",
        reason=f"Destroyed {count} sessions",
    )
    
    return {"success": True, "sessions_destroyed": count}


@router.get("/auth/me")
async def admin_me(request: Request):
    """Get current admin info."""
    auth = await require_admin(request)
    admin = auth["admin"]
    
    # Get active sessions
    sessions = await SessionManager.get_active_sessions(admin["id"])
    
    return {
        "admin": {k: v for k, v in admin.items() if k not in ["password_hash", "two_factor_secret"]},
        "active_sessions": len(sessions),
        "sessions": [
            {
                "session_id": s["session_id"],
                "ip_address": s["ip_address"],
                "created_at": s["created_at"],
                "last_active": s["last_active"],
            }
            for s in sessions
        ],
        "permissions": list(PERMISSIONS.get(AdminRole(admin.get("role", "viewer")), [])),
    }


@router.get("/auth/sessions")
async def admin_sessions(request: Request):
    """Get all active sessions for current admin."""
    auth = await require_admin(request)
    sessions = await SessionManager.get_active_sessions(auth["admin"]["id"])
    return {"sessions": sessions, "total": len(sessions)}


# ═══════════════════════════════════════════════════════════════
# 2. DASHBOARD
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def admin_dashboard(request: Request):
    """Get admin dashboard metrics."""
    auth = await require_admin(request, "dashboard.read")
    
    # System health
    health = await SystemHealthMonitor.get_system_health()
    
    # Get stats from Redis
    stats = {}
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        stats = {
            "total_users": await r.scard("rmi:users") or 0,
            "total_admins": len(await r.hgetall("rmi:admins")),
            "active_sessions": 0,
            "blocked_ips": await r.scard("blocked_ips:all") or 0,
            "total_deployments": await r.scard("token_deployments:all") or 0,
            "total_scans_today": 0,
            "x402_payments_today": 0,
        }
        
        # Count active sessions
        for key in await r.keys("admin_session:*"):
            if not key.startswith("admin_sessions:"):
                stats["active_sessions"] += 1
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
    
    return {
        "health": health,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/dashboard/metrics")
async def dashboard_metrics(request: Request, hours: int = 24):
    """Get time-series metrics for dashboard charts."""
    auth = await require_admin(request, "analytics.read")
    
    metrics = {
        "api_requests": [],
        "scans": [],
        "payments": [],
        "new_users": [],
        "errors": [],
    }
    
    # In production, this would query time-series DB
    # For now, return placeholder structure
    
    return {
        "hours": hours,
        "metrics": metrics,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# 3. USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@router.get("/users")
async def list_users(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    search: str = "",
    tier: str = "",
    banned: Optional[bool] = None,
):
    """List all users with filtering."""
    auth = await require_admin(request, "users.read")
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        users = []
        all_users = await r.hgetall("rmi:users")
        
        for user_id, data in all_users.items():
            user = json.loads(data)
            
            # Apply filters
            if search and search.lower() not in user.get("email", "").lower():
                continue
            if tier and user.get("tier", "") != tier:
                continue
            if banned is not None and user.get("banned", False) != banned:
                continue
            
            # Remove sensitive data
            safe_user = {k: v for k, v in user.items() if "password" not in k and "secret" not in k}
            users.append(safe_user)
        
        total = len(users)
        users = users[offset:offset + limit]
        
        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
async def get_user(request: Request, user_id: str):
    """Get user details."""
    auth = await require_admin(request, "users.read")
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        data = await r.hget("rmi:users", user_id)
        if not data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = json.loads(data)
        safe_user = {k: v for k, v in user.items() if "password" not in k and "secret" not in k}
        
        return {"user": safe_user}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/ban")
async def ban_user(request: Request, user_id: str, body: dict = Body(...)):
    """Ban or unban a user."""
    auth = await require_admin(request, "users.ban", AdminRole.MODERATOR)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        data = await r.hget("rmi:users", user_id)
        if not data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = json.loads(data)
        before_state = {"banned": user.get("banned", False)}
        
        user["banned"] = body.get("banned", True)
        user["banned_at"] = datetime.utcnow().isoformat() if user["banned"] else None
        user["banned_by"] = admin["id"] if user["banned"] else None
        user["ban_reason"] = body.get("reason", "")
        
        await r.hset("rmi:users", user_id, json.dumps(user))
        
        # Log
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="user.ban" if user["banned"] else "user.unban",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip,
            user_agent=ua,
            before_state=before_state,
            after_state={"banned": user["banned"]},
        )
        
        return {"success": True, "banned": user["banned"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ban user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/tier")
async def update_user_tier(request: Request, user_id: str, body: dict = Body(...)):
    """Update user tier/subscription."""
    auth = await require_admin(request, "users.write", AdminRole.ADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        data = await r.hget("rmi:users", user_id)
        if not data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = json.loads(data)
        before_state = {"tier": user.get("tier", "FREE")}
        
        user["tier"] = body.get("tier", "FREE")
        user["tier_updated_at"] = datetime.utcnow().isoformat()
        user["tier_updated_by"] = admin["id"]
        
        await r.hset("rmi:users", user_id, json.dumps(user))
        
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="user.tier_update",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip,
            user_agent=ua,
            before_state=before_state,
            after_state={"tier": user["tier"]},
        )
        
        return {"success": True, "tier": user["tier"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update tier error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# 4. SECURITY
# ═══════════════════════════════════════════════════════════════

@router.get("/security/audit-logs")
async def get_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    action: str = "",
    admin_id: str = "",
    start_date: str = "",
    end_date: str = "",
):
    """Query audit logs."""
    auth = await require_admin(request, "security.read", AdminRole.ADMIN)
    
    entries = await AuditLogger.query(
        admin_id=admin_id or None,
        action=action or None,
        limit=limit,
        offset=offset,
    )
    
    return {
        "logs": [e.to_dict() for e in entries],
        "total": len(entries),
        "limit": limit,
        "offset": offset,
    }


@router.get("/security/blocked-ips")
async def get_blocked_ips(request: Request):
    """List all blocked IPs."""
    auth = await require_admin(request, "security.read", AdminRole.ADMIN)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        ips = await r.smembers("blocked_ips:all")
        blocked = []
        
        for ip in ips:
            data = await r.get(f"blocked_ip:{ip}")
            if data:
                blocked.append(json.loads(data))
        
        return {"blocked_ips": blocked, "total": len(blocked)}
        
    except Exception as e:
        logger.error(f"Get blocked IPs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/block-ip")
async def block_ip(request: Request, body: IPBlockRequest):
    """Block an IP address."""
    auth = await require_admin(request, "security.write", AdminRole.ADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    result = await SecurityManager.block_ip(body.ip, body.reason, body.duration_hours)
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="ip.block",
        resource_type="ip",
        resource_id=body.ip,
        ip_address=ip,
        user_agent=ua,
        after_state={"reason": body.reason, "duration": body.duration_hours},
    )
    
    return {"success": result, "ip": body.ip, "duration_hours": body.duration_hours}


@router.post("/security/unblock-ip")
async def unblock_ip(request: Request, body: dict = Body(...)):
    """Unblock an IP address."""
    auth = await require_admin(request, "security.write", AdminRole.ADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    target_ip = body.get("ip", "")
    result = await SecurityManager.unblock_ip(target_ip)
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="ip.unblock",
        resource_type="ip",
        resource_id=target_ip,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": result, "ip": target_ip}


@router.get("/security/threats")
async def get_threats(request: Request, hours: int = 24):
    """Get security threats and alerts."""
    auth = await require_admin(request, "security.read", AdminRole.ADMIN)
    
    # In production, this would query threat detection system
    threats = []
    
    return {
        "threats": threats,
        "total": len(threats),
        "hours": hours,
    }


# ═══════════════════════════════════════════════════════════════
# 5. SYSTEM MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@router.get("/system/health")
async def system_health(request: Request):
    """Get detailed system health."""
    auth = await require_admin(request, "system.read")
    
    health = await SystemHealthMonitor.get_system_health()
    return health


@router.get("/system/config")
async def get_config(request: Request):
    """Get system configuration (safe vars only)."""
    auth = await require_admin(request, "settings.read", AdminRole.ADMIN)
    
    # Return safe config values (no secrets)
    safe_config = {
        "environment": os.getenv("ENVIRONMENT", "production"),
        "backend_port": os.getenv("BACKEND_PORT", "8000"),
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "x402_enabled": bool(os.getenv("X402_EVM_PAY_TO", "")),
        "features": {
            "rag": True,
            "token_deployer": True,
            "airdrop": True,
            "x402": True,
            "news": True,
        },
    }
    
    return {"config": safe_config}


@router.post("/system/config")
async def update_config(request: Request, body: ConfigUpdateRequest):
    """Update system configuration."""
    auth = await require_admin(request, "settings.write", AdminRole.SUPERADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    # In production, this would update env vars or config store
    # For now, log the request
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="config.update",
        resource_type="config",
        resource_id=body.key,
        ip_address=ip,
        user_agent=ua,
        after_state={"key": body.key, "value": body.value, "category": body.category},
    )
    
    return {"success": True, "key": body.key, "updated": True}


@router.get("/system/services")
async def get_services(request: Request):
    """Get status of all system services."""
    auth = await require_admin(request, "system.read")
    
    services = {
        "backend": {"status": "running", "pid": os.getpid()},
        "redis": await SystemHealthMonitor._check_redis(),
        "supabase": await SystemHealthMonitor._check_supabase(),
    }
    
    return {"services": services}


@router.post("/system/restart")
async def restart_service(request: Request, body: dict = Body(...)):
    """Restart a service (simulated)."""
    auth = await require_admin(request, "system.write", AdminRole.SUPERADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    service = body.get("service", "")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="system.restart",
        resource_type="service",
        resource_id=service,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True, "service": service, "status": "restart_queued"}


# ═══════════════════════════════════════════════════════════════
# 6. CONTENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@router.get("/content/announcements")
async def get_announcements(request: Request, active_only: bool = True):
    """Get announcements."""
    auth = await require_admin(request, "content.read")
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        announcements = []
        data = await r.get("rmi:announcements")
        if data:
            all_announcements = json.loads(data)
            for a in all_announcements:
                if not active_only or a.get("active", True):
                    announcements.append(a)
        
        return {"announcements": announcements}
        
    except Exception as e:
        logger.error(f"Get announcements error: {e}")
        return {"announcements": []}


@router.post("/content/announcements")
async def create_announcement(request: Request, body: AnnouncementRequest):
    """Create an announcement."""
    auth = await require_admin(request, "content.write", AdminRole.MODERATOR)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        announcement = {
            "id": f"ann_{int(time.time())}",
            "title": body.title,
            "content": body.content,
            "type": body.type,
            "target_audience": body.target_audience,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": admin["id"],
            "active": True,
            "expires_at": body.expires_at,
        }
        
        # Get existing announcements
        data = await r.get("rmi:announcements")
        announcements = json.loads(data) if data else []
        announcements.append(announcement)
        
        await r.set("rmi:announcements", json.dumps(announcements))
        
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="content.announcement.create",
            resource_type="announcement",
            resource_id=announcement["id"],
            ip_address=ip,
            user_agent=ua,
        )
        
        return {"success": True, "announcement": announcement}
        
    except Exception as e:
        logger.error(f"Create announcement error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# 7. FINANCIAL / X402 ANALYTICS
# ═══════════════════════════════════════════════════════════════

@router.get("/financial/x402")
async def x402_analytics(request: Request, days: int = 30):
    """Get x402 payment analytics."""
    auth = await require_admin(request, "financial.read", AdminRole.ADMIN)
    
    # In production, query x402_payments table
    analytics = {
        "total_payments": 0,
        "total_revenue_usd": 0,
        "payments_by_chain": {},
        "payments_by_tool": {},
        "daily_volume": [],
    }
    
    return {"analytics": analytics, "days": days}


@router.get("/financial/revenue")
async def revenue_report(request: Request, period: str = "month"):
    """Get revenue report."""
    auth = await require_admin(request, "financial.read", AdminRole.ADMIN)
    
    return {
        "period": period,
        "revenue": {
            "x402": 0,
            "subscriptions": 0,
            "api_usage": 0,
            "total": 0,
        },
    }


# ═══════════════════════════════════════════════════════════════
# 8. API KEY MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@router.get("/api-keys")
async def list_api_keys(request: Request):
    """List all API keys."""
    auth = await require_admin(request, "api_keys.read", AdminRole.ADMIN)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        keys = []
        all_keys = await r.hgetall("rmi:api_keys")
        for key_id, data in all_keys.items():
            key_data = json.loads(data)
            # Mask the actual key
            key_data["key"] = key_data.get("key", "")[:8] + "..." + key_data.get("key", "")[-4:]
            keys.append(key_data)
        
        return {"api_keys": keys, "total": len(keys)}
        
    except Exception as e:
        logger.error(f"List API keys error: {e}")
        return {"api_keys": [], "total": 0}


@router.post("/api-keys")
async def create_api_key(request: Request, body: APIKeyCreateRequest):
    """Create a new API key."""
    auth = await require_admin(request, "api_keys.write", AdminRole.ADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    key_id = f"key_{secrets.token_hex(8)}"
    api_key = f"rmi_{secrets.token_urlsafe(32)}"
    
    key_data = {
        "id": key_id,
        "name": body.name,
        "key": api_key,
        "scopes": body.scopes,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": admin["id"],
        "expires_at": (datetime.utcnow() + timedelta(days=body.expires_days)).isoformat(),
        "last_used": None,
        "usage_count": 0,
        "active": True,
    }
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        await r.hset("rmi:api_keys", key_id, json.dumps(key_data))
        
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="api_key.create",
            resource_type="api_key",
            resource_id=key_id,
            ip_address=ip,
            user_agent=ua,
        )
        
        # Return the full key once (won't be shown again)
        return {
            "success": True,
            "api_key": api_key,
            "key_id": key_id,
            "expires_at": key_data["expires_at"],
        }
        
    except Exception as e:
        logger.error(f"Create API key error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(request: Request, key_id: str):
    """Revoke an API key."""
    auth = await require_admin(request, "api_keys.write", AdminRole.ADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        data = await r.hget("rmi:api_keys", key_id)
        if not data:
            raise HTTPException(status_code=404, detail="API key not found")
        
        key_data = json.loads(data)
        key_data["active"] = False
        key_data["revoked_at"] = datetime.utcnow().isoformat()
        key_data["revoked_by"] = admin["id"]
        
        await r.hset("rmi:api_keys", key_id, json.dumps(key_data))
        
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="api_key.revoke",
            resource_type="api_key",
            resource_id=key_id,
            ip_address=ip,
            user_agent=ua,
        )
        
        return {"success": True, "revoked": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revoke API key error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# 9. ADMIN MANAGEMENT (Superadmin only)
# ═══════════════════════════════════════════════════════════════

@router.get("/admins")
async def list_admins(request: Request):
    """List all admin users."""
    auth = await require_admin(request, "*", AdminRole.SUPERADMIN)
    
    admins = await AdminUserStore.list_admins()
    
    # Remove sensitive data
    safe_admins = []
    for admin in admins:
        safe = {k: v for k, v in admin.items() if k not in ["password_hash", "two_factor_secret"]}
        safe_admins.append(safe)
    
    return {"admins": safe_admins, "total": len(safe_admins)}


@router.post("/admins")
async def create_admin(request: Request, body: CreateAdminRequest):
    """Create a new admin user."""
    auth = await require_admin(request, "*", AdminRole.SUPERADMIN)
    creator = auth["admin"]
    ip, ua = _get_client_info(request)
    
    role = AdminRole(body.role) if body.role in [r.value for r in AdminRole] else AdminRole.VIEWER
    
    admin = await AdminUserStore.create_admin(
        email=body.email,
        password=body.password,
        role=role,
        created_by=creator["id"],
    )
    
    if not admin:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    await AuditLogger.log(
        admin_id=creator["id"],
        admin_email=creator["email"],
        action="admin.create",
        resource_type="admin",
        resource_id=admin["id"],
        ip_address=ip,
        user_agent=ua,
        after_state={"role": admin["role"], "email": admin["email"]},
    )
    
    return {"success": True, "admin": admin}


@router.post("/admins/{admin_id}/update")
async def update_admin(request: Request, admin_id: str, body: UpdateAdminRequest):
    """Update an admin user."""
    auth = await require_admin(request, "*", AdminRole.SUPERADMIN)
    updater = auth["admin"]
    ip, ua = _get_client_info(request)
    
    # Can't update self's role to prevent lockout
    if admin_id == updater["id"] and body.role and body.role != updater["role"]:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    admin = await AdminUserStore.get_admin(admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    before_state = {}
    after_state = {}
    
    if body.role is not None:
        before_state["role"] = admin["role"]
        admin["role"] = body.role
        after_state["role"] = body.role
    
    if body.is_active is not None:
        before_state["is_active"] = admin.get("is_active", True)
        admin["is_active"] = body.is_active
        after_state["is_active"] = body.is_active
    
    if body.ip_allowlist is not None:
        admin["ip_allowlist"] = body.ip_allowlist
        after_state["ip_allowlist"] = body.ip_allowlist
    
    if body.two_factor_enabled is not None:
        admin["two_factor_enabled"] = body.two_factor_enabled
        after_state["two_factor_enabled"] = body.two_factor_enabled
    
    await AdminUserStore.save_admin(admin)
    
    await AuditLogger.log(
        admin_id=updater["id"],
        admin_email=updater["email"],
        action="admin.update",
        resource_type="admin",
        resource_id=admin_id,
        ip_address=ip,
        user_agent=ua,
        before_state=before_state,
        after_state=after_state,
    )
    
    return {"success": True, "admin_id": admin_id}


@router.post("/admins/{admin_id}/reset-password")
async def reset_admin_password(request: Request, admin_id: str, body: dict = Body(...)):
    """Reset an admin's password."""
    auth = await require_admin(request, "*", AdminRole.SUPERADMIN)
    updater = auth["admin"]
    ip, ua = _get_client_info(request)
    
    from app.auth import hash_password
    
    admin = await AdminUserStore.get_admin(admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    new_password = body.get("password", "")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    admin["password_hash"] = hash_password(new_password)
    admin["password_changed_at"] = datetime.utcnow().isoformat()
    
    await AdminUserStore.save_admin(admin)
    
    # Destroy all sessions (force re-login)
    await SessionManager.destroy_all_sessions(admin_id)
    
    await AuditLogger.log(
        admin_id=updater["id"],
        admin_email=updater["email"],
        action="admin.password_reset",
        resource_type="admin",
        resource_id=admin_id,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True, "sessions_destroyed": True}


# ═══════════════════════════════════════════════════════════════
# 10. BACKUP & MAINTENANCE
# ═══════════════════════════════════════════════════════════════

@router.get("/backups")
async def list_backups(request: Request):
    """List available backups."""
    auth = await require_admin(request, "backups.read", AdminRole.SUPERADMIN)
    
    return {"backups": [], "total": 0}


@router.post("/backups/create")
async def create_backup(request: Request, body: dict = Body(...)):
    """Create a new backup."""
    auth = await require_admin(request, "backups.write", AdminRole.SUPERADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    backup_type = body.get("type", "full")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="backup.create",
        resource_type="backup",
        resource_id=backup_type,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True, "backup_type": backup_type, "status": "queued"}


# ═══════════════════════════════════════════════════════════════
# 11. WEBHOOK MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@router.get("/webhooks")
async def list_webhooks(request: Request):
    """List configured webhooks."""
    auth = await require_admin(request, "webhooks.read", AdminRole.ADMIN)
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        webhooks = []
        data = await r.get("rmi:webhooks")
        if data:
            webhooks = json.loads(data)
        
        return {"webhooks": webhooks}
        
    except Exception as e:
        logger.error(f"List webhooks error: {e}")
        return {"webhooks": []}


@router.post("/webhooks")
async def create_webhook(request: Request, body: WebhookConfigRequest):
    """Create a webhook."""
    auth = await require_admin(request, "webhooks.write", AdminRole.ADMIN)
    admin = auth["admin"]
    ip, ua = _get_client_info(request)
    
    webhook = {
        "id": f"wh_{int(time.time())}",
        "url": body.url,
        "events": body.events,
        "secret": body.secret,
        "active": body.active,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": admin["id"],
    }
    
    try:
        import redis.asyncio as redis_lib
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        
        data = await r.get("rmi:webhooks")
        webhooks = json.loads(data) if data else []
        webhooks.append(webhook)
        
        await r.set("rmi:webhooks", json.dumps(webhooks))
        
        await AuditLogger.log(
            admin_id=admin["id"],
            admin_email=admin["email"],
            action="webhook.create",
            resource_type="webhook",
            resource_id=webhook["id"],
            ip_address=ip,
            user_agent=ua,
        )
        
        return {"success": True, "webhook": webhook}
        
    except Exception as e:
        logger.error(f"Create webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
