"""
Auth Router — Complete authentication system (email, wallet, OAuth, Telegram)
"""
import json
import logging
import os
import secrets
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from passlib.context import CryptContext
from jose import jwt, JWTError

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# ── Config ──
JWT_SECRET = os.getenv("JWT_SECRET", "rmi-jwt-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7

# Password hashing context (bcrypt via passlib)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password using bcrypt via Passlib."""
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(password, hashed)

# ── Helpers ──
def _is_valid_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def _create_jwt(user_id: str, email: str, tier: str = "FREE", role: str = "USER", wallet: Optional[str] = None) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    if wallet:
        payload["wallet"] = wallet
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "id": payload["sub"],
            "email": payload["email"],
            "tier": payload.get("tier", "FREE"),
            "role": payload.get("role", "USER"),
            "wallet": payload.get("wallet"),
        }
    except JWTError:
        return None

def _derive_user_id(email: str) -> str:
    import hashlib
    return hashlib.sha256(email.lower().encode()).hexdigest()[:32]

def generate_nonce() -> str:
    return secrets.token_urlsafe(16)

# ── Storage (Redis-backed user store) ──
def get_redis():
    import redis
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD", ""),
        decode_responses=True
    )

def _get_user(user_id: str) -> Optional[Dict]:
    r = get_redis()
    data = r.hget("rmi:users", user_id)
    return json.loads(data) if data else None

def _save_user(user: Dict):
    r = get_redis()
    r.hset("rmi:users", user["id"], json.dumps(user))

def _get_user_by_email(email: str) -> Optional[Dict]:
    r = get_redis()
    user_id = r.hget("rmi:users:email", email.lower())
    if user_id:
        return _get_user(user_id)
    return None

# ── Models ──
class EmailLoginRequest(BaseModel):
    email: str
    password: str

class EmailRegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    wallet_address: Optional[str] = None
    wallet_chain: Optional[str] = None

class WalletNonceRequest(BaseModel):
    address: str
    chain: str

class WalletVerifyRequest(BaseModel):
    address: str
    chain: str
    nonce: str
    signature: str
    message: str

class NonceResponse(BaseModel):
    nonce: str
    timestamp: str
    message: Optional[str] = None

class WalletAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    wallet_address: Optional[str]
    wallet_chain: Optional[str]
    tier: str
    role: str
    created_at: str
    xp: int = 0
    level: int = 1
    badges: list = []

class GoogleAuthResponse(BaseModel):
    url: str

class TelegramAuthRequest(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


# ── Email Auth ──
@router.post("/register", response_model=WalletAuthResponse)
def register_email(req: EmailRegisterRequest):
    """Register a new user with email/password."""
    if not _is_valid_email(req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Check if user exists
    existing = _get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = _derive_user_id(req.email)
    hashed = hash_password(req.password)
    
    user = {
        "id": user_id,
        "email": req.email,
        "display_name": req.display_name,
        "password_hash": hashed,
        "wallet_address": req.wallet_address,
        "wallet_chain": req.wallet_chain,
        "tier": "FREE",
        "role": "USER",
        "created_at": datetime.utcnow().isoformat(),
        "xp": 0,
        "level": 1,
        "badges": [],
        "scans_remaining": 5,
        "scans_used": 0,
    }
    
    # Save user + email index
    r = get_redis()
    r.hset("rmi:users", user_id, json.dumps(user))
    r.hset("rmi:users:email", req.email.lower(), user_id)
    
    token = _create_jwt(user_id, req.email, "FREE", "USER", req.wallet_address)
    
    return {
        "access_token": token,
        "refresh_token": token,
        "user": {
            "id": user_id,
            "email": req.email,
            "display_name": req.display_name,
            "wallet_address": req.wallet_address,
            "wallet_chain": req.wallet_chain,
            "tier": "FREE",
            "role": "USER",
            "created_at": user["created_at"],
        },
    }


@router.post("/login", response_model=WalletAuthResponse)
def login_email(req: EmailLoginRequest):
    """Login with email/password."""
    user = _get_user_by_email(req.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = _create_jwt(user["id"], user["email"], user.get("tier", "FREE"), user.get("role", "USER"), user.get("wallet_address"))
    
    return {
        "access_token": token,
        "refresh_token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user.get("display_name", user["email"]),
            "wallet_address": user.get("wallet_address"),
            "wallet_chain": user.get("wallet_chain"),
            "tier": user.get("tier", "FREE"),
            "role": user.get("role", "USER"),
            "created_at": user.get("created_at"),
        },
    }


# ── Wallet Auth ──
@router.post("/wallet/nonce", response_model=NonceResponse)
async def wallet_nonce(req: WalletNonceRequest):
    """Get a nonce for wallet signature."""
    nonce = generate_nonce()
    timestamp = datetime.utcnow().isoformat()
    message = f"RugMunch Intelligence wants you to sign in with your {req.chain.title()} account.\n\nWallet: {req.address}\nNonce: {nonce}\nTimestamp: {timestamp}"
    return {
        "nonce": nonce,
        "timestamp": timestamp,
        "message": message,
    }


@router.post("/wallet/verify", response_model=WalletAuthResponse)
async def wallet_verify(req: WalletVerifyRequest):
    """Verify wallet signature and create session."""
    from app.auth_wallet import verify_wallet_signature, get_or_create_wallet_user
    
    if not verify_wallet_signature(req.message, req.signature, req.address):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    user_data = await get_or_create_wallet_user(req.address)
    
    return {
        "access_token": user_data["access_token"],
        "refresh_token": user_data["refresh_token"],
        "user": {
            "id": user_data["id"],
            "email": user_data["email"],
            "display_name": user_data.get("display_name", f"Agent {req.address[2:8].upper()}"),
            "wallet_address": req.address,
            "wallet_chain": req.chain,
            "tier": user_data["tier"],
            "role": user_data["role"],
            "created_at": user_data["created_at"],
        },
    }


# ── User Profile ──
@router.get("/user/me", response_model=UserResponse)
async def get_current_user(request: Request):
    """Get current authenticated user profile."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    
    token = auth_header[7:]
    payload = _verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = _get_user(payload["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user.get("display_name", user["email"]),
        "wallet_address": user.get("wallet_address"),
        "wallet_chain": user.get("wallet_chain"),
        "tier": user.get("tier", "FREE"),
        "role": user.get("role", "USER"),
        "created_at": user.get("created_at"),
        "xp": user.get("xp", 0),
        "level": user.get("level", 1),
        "badges": user.get("badges", []),
    }


# ── Google OAuth ──
@router.get("/google/url", response_model=GoogleAuthResponse)
async def google_auth_url():
    """Get Google OAuth URL."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "https://rugmunch.io/auth/google/callback")
    
    if not client_id:
        return {"url": "/auth/google/callback?error=not_configured"}
    
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"url": url}


@router.post("/google/callback", response_model=WalletAuthResponse)
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    body = await request.json()
    code = body.get("code")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    import httpx
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "https://rugmunch.io/auth/google/callback")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")
        
        tokens = resp.json()
        access_token = tokens.get("access_token")
        
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        google_user = resp.json()
        email = google_user.get("email")
        
        user = _get_user_by_email(email)
        if not user:
            user_id = _derive_user_id(email)
            user = {
                "id": user_id,
                "email": email,
                "display_name": google_user.get("name", email),
                "tier": "FREE",
                "role": "USER",
                "created_at": datetime.utcnow().isoformat(),
                "xp": 0,
                "level": 1,
                "badges": [],
                "scans_remaining": 5,
                "scans_used": 0,
            }
            r = get_redis()
            r.hset("rmi:users", user_id, json.dumps(user))
            r.hset("rmi:users:email", email.lower(), user_id)
        
        jwt_token = _create_jwt(user["id"], user["email"], user.get("tier", "FREE"), user.get("role", "USER"))
        
        return {
            "access_token": jwt_token,
            "refresh_token": jwt_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "display_name": user.get("display_name", email),
                "wallet_address": None,
                "wallet_chain": None,
                "tier": user.get("tier", "FREE"),
                "role": user.get("role", "USER"),
                "created_at": user.get("created_at"),
            },
        }


# ── Telegram Auth ──
@router.post("/telegram", response_model=WalletAuthResponse)
async def telegram_auth(req: TelegramAuthRequest):
    """Authenticate via Telegram Web App data."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="Telegram auth not configured")
    
    data_check = {
        "id": str(req.id),
        "auth_date": str(req.auth_date),
    }
    if req.first_name:
        data_check["first_name"] = req.first_name
    if req.last_name:
        data_check["last_name"] = req.last_name
    if req.username:
        data_check["username"] = req.username
    if req.photo_url:
        data_check["photo_url"] = req.photo_url
    
    import hashlib
    import hmac
    sorted_data = "\n".join(f"{k}={v}" for k, v in sorted(data_check.items()))
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(secret, sorted_data.encode(), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(req.hash, expected_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
    
    telegram_user_id = f"tg:{req.id}"
    user = _get_user(telegram_user_id)
    
    if not user:
        display_name = f"{req.first_name or ''} {req.last_name or ''}".strip() or req.username or f"User{req.id}"
        email = f"{req.id}@telegram.rmi"
        
        user = {
            "id": telegram_user_id,
            "email": email,
            "display_name": display_name,
            "telegram_id": req.id,
            "telegram_username": req.username,
            "tier": "FREE",
            "role": "USER",
            "created_at": datetime.utcnow().isoformat(),
            "xp": 0,
            "level": 1,
            "badges": [],
            "scans_remaining": 5,
            "scans_used": 0,
        }
        r = get_redis()
        r.hset("rmi:users", telegram_user_id, json.dumps(user))
        r.hset("rmi:users:telegram", str(req.id), telegram_user_id)
    
    jwt_token = _create_jwt(user["id"], user["email"], user.get("tier", "FREE"), user.get("role", "USER"))
    
    return {
        "access_token": jwt_token,
        "refresh_token": jwt_token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user.get("display_name"),
            "wallet_address": None,
            "wallet_chain": None,
            "tier": user.get("tier", "FREE"),
            "role": user.get("role", "USER"),
            "created_at": user.get("created_at"),
        },
    }


# ── GitHub OAuth ──
@router.get("/github/url", response_model=GoogleAuthResponse)
async def github_auth_url():
    """Get GitHub OAuth URL."""
    client_id = os.getenv("GITHUB_CLIENT_ID")
    redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "https://rugmunch.io/auth/github/callback")
    
    if not client_id:
        return {"url": "/auth/github/callback?error=not_configured"}
    
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email",
    }
    url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return {"url": url}


# ── FastAPI Dependency Functions (for @router/@app endpoints) ──
async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Verify JWT from Authorization header (wallet or email)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    payload = _verify_jwt(token)
    if not payload:
        return None
    user = _get_user(payload["id"])
    if not user:
        return None
    return user


async def require_auth(request: Request) -> Dict[str, Any]:
    """Require valid JWT. Raises 401 if missing/invalid."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
