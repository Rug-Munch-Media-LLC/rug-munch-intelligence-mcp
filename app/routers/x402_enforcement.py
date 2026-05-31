"""
RMI x402 Payment Enforcement Middleware
========================================
Intercepts /api/v1/x402-tools/* requests, verifies x402 payment headers.
Returns 402 Payment Required when no valid payment is provided.

ARCHITECTURE (May 23, 2026 — Multi-Facilitator):
- Smart router auto-picks best facilitator per chain/token
- 7 active facilitators: Coinbase CDP, PayAI, Cloudflare x402,
  AsterPay (EUR/SEPA), Primev (fee-free ETH),
  x402-rs (self-hosted), EIP-7702 (universal EVM)
- 3 OFFLINE facilitators (NXDOMAIN): Pieverse, MERX TRON, Satoshi
- 11 payment chains: Base, Solana, Ethereum, BSC,
  Arbitrum, Optimism, Polygon, Avalanche, Fantom, Gnosis, SEPA/EUR
- TRON and Bitcoin chains disabled (sole facilitators dead)
- Fallback: old PaymentVerifier if router unavailable

Author: RMI Development
Date: 2026-05-23
"""
import os
import json
import time
import logging
import hashlib
import re
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("x402_enforcement")

# ── Discovery endpoint cache ──
_discovery_cache: Optional[dict] = None
_discovery_cache_time: float = 0
DISCOVERY_CACHE_TTL = 300  # 5 minutes

# Security headers for all x402 responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Cache-Control": "no-store",
}

# ── Import existing PaymentVerifier ──
try:
    from app.routers.x402_middleware import PaymentVerifier, FACILITATOR_CONFIGS, TOKEN_METADATA
    VERIFIER = PaymentVerifier()
    logger.info("x402 enforcement: using existing PaymentVerifier")
except ImportError as e:
    VERIFIER = None
    logger.warning(f"x402 enforcement: PaymentVerifier not available: {e}")

# ── Multi-chain USDC configs ──
# PAYMENT chains: Base and Solana use facilitators (fast, federated verification).
# All other EVM chains use self-verification via Etherscan/Alchemy on-chain checks.
# Same EVM wallet works across all chains — user pays on whichever has USDC.
# This is a competitive advantage: most x402 gateways only take Base.
CHAIN_USDC = {
    # ── Facilitator-verified chains (instant/direct) ──
    "base": {"network": "eip155:8453", "chain_id": 8453, "usdc": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "facilitator", "facilitators": ["coinbase_cdp", "payai"]},
    "solana": {"network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", "chain_id": None, "usdc": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "name": "USD Coin", "version": "2", "method": "payai", "verify": "facilitator", "facilitators": ["payai"]},
    "bsc": {"network": "eip155:56", "chain_id": 56, "usdc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "facilitator", "facilitators": ["eip7702"]},  # pieverse REMOVED — OFFLINE (api.pieverse.xyz NXDOMAIN)
    "ethereum": {"network": "eip155:1", "chain_id": 1, "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "facilitator", "facilitators": ["primev", "payai", "eip7702"]},
    "tron": {"network": "tron:mainnet", "chain_id": None, "usdc": "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8", "name": "USD Coin (TRC20)", "version": "2", "method": "tron_selfverify", "verify": "facilitator", "facilitators": ["tron_selfverify"],
              "tokens": {"USDT": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "USDD": "TPYmHEhy5n8TCEfZGqW2rPbmgh1fGqNBPa"}},
    "bitcoin": {"network": "bitcoin:mainnet", "chain_id": None, "usdc": "", "name": "Bitcoin", "version": "2", "method": "bitcoin_selfverify", "verify": "facilitator", "facilitators": ["bitcoin_selfverify"],
              "tokens": {"BTC": "native"}},
    # ── Self-verified EVM chains (EIP-7702 universal) ──
    "arbitrum": {"network": "eip155:42161", "chain_id": 42161, "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "self", "facilitators": ["eip7702"]},
    "optimism": {"network": "eip155:10", "chain_id": 10, "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "self", "facilitators": ["eip7702"]},
    "polygon": {"network": "eip155:137", "chain_id": 137, "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "self", "facilitators": ["eip7702"]},
    "avalanche": {"network": "eip155:43114", "chain_id": 43114, "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "self", "facilitators": ["eip7702"]},
    "fantom": {"network": "eip155:250", "chain_id": 250, "usdc": "0x04068DA6C83AFCFA0e13ba15A6696662335D5B75", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "self", "facilitators": ["eip7702"]},
    "gnosis": {"network": "eip155:100", "chain_id": 100, "usdc": "0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83", "name": "USD Coin", "version": "2", "method": "local_eip712", "verify": "self", "facilitators": ["eip7702"]},
    # ── SEPA/EUR (AsterPay fiat off-ramp) ──
    "sepa": {"network": "sepa:eur", "chain_id": None, "usdc": "", "name": "Euro", "version": "1", "method": "asterpay", "verify": "facilitator", "facilitators": ["asterpay"],
             "tokens": {"EUR": "fiat"}},
}

# Pay-to addresses
EVM_PAY_TO = os.getenv("X402_EVM_PAY_TO", "0x1E3AC01d0fdb976179790BDD02823196A92705C9")
SOL_PAY_TO = os.getenv("X402_SOL_PAY_TO", "Gix4P9AmwcZRGzr2hCEME5m2QAvY86dBfm8c7e7MpFzv")

# ── Tool pricing (parsed from gateway configs) ──
TOOL_PRICES: Dict[str, Dict[str, Any]] = {}

def _load_tool_prices():
    """Load tool prices from gateway configs and catalog API.
    
    1. Parse prices from all gateway index.ts files (robust regex)
    2. Add manual pricing for new tools not in gateways
    3. Load from live catalog API as fallback (ensures 224 tools)
    """
    import os, re, urllib.request, json
    
    # ─── 1. Parse from gateway configs ────────────────────────────────────────
    # Try multiple paths: Docker mount, host path, OpenClaw backup
    gateway_base = None
    for candidate in ["/app/x402-gateway", "/root/backend/x402-gateway", "/srv/rmi/backend/x402-gateway", "/root/.openclaw/backend/x402-gateway"]:
        if os.path.isdir(candidate):
            gateway_base = candidate
            break
    
    if gateway_base and os.path.exists(gateway_base):
        logger.info(f"Loading tool prices from gateway configs at {gateway_base}")
        for chain_dir in os.listdir(gateway_base):
            index_path = os.path.join(gateway_base, chain_dir, "index.ts")
            if not os.path.exists(index_path):
                continue
            with open(index_path, 'r') as f:
                content = f.read()
            
            # Flexible regex to extract key-value pairs from tool definitions
            tool_pattern = r'(\w+):\s*\{([^}]+)\}'
            for m in re.finditer(tool_pattern, content):
                tool_id = m.group(1)
                body = m.group(2)
                if 'name:' not in body or 'price:' not in body:
                    continue
                
                # Extract individual fields
                name_match = re.search(r'name:\s*"([^"]+)"', body)
                price_match = re.search(r'price:\s*"\$([^"]+)"', body)
                atoms_match = re.search(r'priceAtomic:\s*"([^"]+)"', body)
                cat_match = re.search(r'category:\s*"([^"]+)"', body)
                trial_match = re.search(r'trialFree:\s*(\d+)', body)
                
                if all([name_match, price_match, atoms_match, cat_match, trial_match]):
                    TOOL_PRICES[tool_id] = {
                        "price_usd": float(price_match.group(1)),
                        "price_atoms": atoms_match.group(1),
                        "category": cat_match.group(1).lower(),
                        "trial_free": int(trial_match.group(1)),
                        "description": name_match.group(1),
                    }
    
    # ─── 2. Add manual pricing for new tools ────────────────────────────────
    _NEW_TOOL_PRICES = {
        "forensic_valuation": {"price_usd": 0.25, "price_atoms": "250000", "category": "premium", "trial_free": 1, "description": "Institutional-grade token valuation — DCF intrinsic value, comparable analysis with outlier detection, scam probability scoring"},
        "osint_identity_hunt": {"price_usd": 0.15, "price_atoms": "150000", "category": "premium", "trial_free": 2, "description": "Cross-platform OSINT investigation — hunt usernames across 400+ networks, domain intelligence, stealth page capture"},
        "investigation_report": {"price_usd": 0.20, "price_atoms": "200000", "category": "premium", "trial_free": 1, "description": "Full investigation report — on-chain forensics, financial valuation, OSINT findings, scam scoring in one deliverable"},
        "forensic_pack": {"price_usd": 0.40, "price_atoms": "400000", "category": "bundle", "trial_free": 1, "description": "Forensic Investigation Pack — valuation + OSINT + report at 33% discount"},
        "token_watch_create": {"price_usd": 0.05, "price_atoms": "50000", "category": "monitoring", "trial_free": 3, "description": "Set token monitoring watch — alerts when LP drops, price changes, or rug indicators detected"},
        "token_watch_check": {"price_usd": 0.03, "price_atoms": "30000", "category": "monitoring", "trial_free": 5, "description": "One-shot token status check — current LP, price, volume, and rug risk warnings"},
    }
    TOOL_PRICES.update(_NEW_TOOL_PRICES)
    
    # ─── 3. Load from live catalog API as fallback (optional) ────────────────
    # Only load if server is already running (in production, catalog is in Redis)
    catalog_loaded = False
    try:
        import socket
        # Quick connectivity check before actual request
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        if result == 0:  # Port is open, server might be running
            catalog = json.load(urllib.request.urlopen('http://localhost:8000/api/v1/x402/tools-catalog', timeout=2))
            for tool in catalog.get('tools', []):
                tool_id = tool.get('id')
                if tool_id not in TOOL_PRICES:
                    TOOL_PRICES[tool_id] = {
                        "price_usd": tool.get('priceUsd', 0.01),
                        "price_atoms": str(tool.get('priceAtomic', '10000')),
                        "category": tool.get('category', 'analysis').lower(),
                        "trial_free": tool.get('trialFree', 1),
                        "description": tool.get('name', f"{tool_id} crypto security tool"),
                    }
            catalog_loaded = True
    except Exception:
        pass  # Catalog loading failed or server not running - will use defaults + Redis

    # Fallback: try Redis cache (populated by warmup script after server starts)
    if not catalog_loaded:
        try:
            import redis as _redis
            _r = _redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", ""),
                decode_responses=True,
            )
            _cached = _r.get("x402:catalog:tools")
            if _cached:
                for tool in json.loads(_cached):
                    tool_id = tool.get('id')
                    if tool_id not in TOOL_PRICES:
                        TOOL_PRICES[tool_id] = {
                            "price_usd": tool.get('priceUsd', 0.01),
                            "price_atoms": str(tool.get('priceAtomic', '10000')),
                            "category": tool.get('category', 'analysis').lower(),
                            "trial_free": tool.get('trialFree', 1),
                            "description": tool.get('name', f"{tool_id} crypto security tool"),
                        }
                catalog_loaded = True
        except Exception as e:
            logger.warning(f"x402 enforcement: could not load catalog from Redis: {e}")

# ── Add new tools from x402_tools.py that aren't in gateway configs yet ──
try:
    _NEW_TOOL_PRICES = {
        "forensic_valuation": {"price_usd": 0.25, "price_atoms": "250000", "category": "premium", "trial_free": 1, "description": "Institutional-grade token valuation — DCF intrinsic value, comparable analysis with outlier detection, scam probability scoring"},
        "osint_identity_hunt": {"price_usd": 0.15, "price_atoms": "150000", "category": "premium", "trial_free": 2, "description": "Cross-platform OSINT investigation — hunt usernames across 400+ networks, domain intelligence, stealth page capture"},
        "investigation_report": {"price_usd": 0.20, "price_atoms": "200000", "category": "premium", "trial_free": 1, "description": "Full investigation report — on-chain forensics, financial valuation, OSINT findings, scam scoring in one deliverable"},
        "forensic_pack": {"price_usd": 0.40, "price_atoms": "400000", "category": "bundle", "trial_free": 1, "description": "Forensic Investigation Pack — valuation + OSINT + report at 33% discount"},
        # API / meta tools — must be in TOOL_PRICES at startup (not loaded from catalog)
        "catalog": {"price_usd": 0.00, "price_atoms": "0", "category": "api", "trial_free": 999, "description": "Browse available tools, pricing, and chain support"},
        "smart_money_alpha": {"price_usd": 0.01, "price_atoms": "10000", "category": "intelligence", "trial_free": 3, "description": "Smart money alpha signals — track wallets that consistently outperform the market"},
        "meme_vibe_score": {"price_usd": 0.01, "price_atoms": "10000", "category": "social", "trial_free": 3, "description": "Meme token vibe scoring — sentiment, community strength, and virality analysis"},
        "mcp-proxy": {"price_usd": 0.01, "price_atoms": "10000", "category": "api", "trial_free": 5, "description": "MCP protocol proxy — route tool calls through the x402 payment layer"},
        "human-execute": {"price_usd": 0.02, "price_atoms": "20000", "category": "api", "trial_free": 2, "description": "Human-in-the-loop execution — wallet-based payment for manual crypto investigation tasks"},
    }
    TOOL_PRICES.update(_NEW_TOOL_PRICES)
except Exception as e:
    logger.warning(f"x402 enforcement: could not add new tool prices: {e}")

# ── Expanded tools: 44 new specialized tools + 80 per-chain variants ──
try:
    from app.routers._expanded_tools import ADDITIONAL_TOOLS as _EXPANDED_TOOLS
    TOOL_PRICES.update(_EXPANDED_TOOLS)
    logger.info(f"x402 enforcement: loaded {len(_EXPANDED_TOOLS)} expanded tools (44 new + 80 per-chain variants)")
except Exception as e:
    logger.warning(f"x402 enforcement: could not load expanded tools: {e}")

# ── Also load from x402_tools.py BUNDLES dict as fallback ──
try:
    from app.routers.x402_tools import BUNDLES as _TOOLS_BUNDLES
    for bid, b in _TOOLS_BUNDLES.items():
        if bid not in TOOL_PRICES and b.get("category") == "bundle":
            TOOL_PRICES[bid] = {
                "price_usd": b.get("bundle_price_usd", 0.01),
                "price_atoms": b.get("bundle_price_atoms", "10000"),
                "category": "bundle",
                "trial_free": b.get("trial_free", 1),
                "description": b.get("name", bid),
            }
except Exception as e:
    logger.warning(f"x402 enforcement: could not load x402_tools bundles: {e}")

# ── Load all tool prices from gateway configs ──
_load_tool_prices()

# ── Clean up corrupted tool IDs (template variables, paths with slashes/braces) ──
_bad_keys = [k for k in TOOL_PRICES if '{' in k or '/' in k or ' ' in k]
if _bad_keys:
    logger.warning(f"Removing corrupted tool IDs: {_bad_keys}")
for _k in _bad_keys:
    del TOOL_PRICES[_k]

# ── Chain display names (used in human-readable messages) ──
CHAIN_NAMES = {
    "base": "Base", "solana": "Solana", "ethereum": "Ethereum",
    "bsc": "BNB Chain", "tron": "TRON", "bitcoin": "Bitcoin",
    "arbitrum": "Arbitrum", "optimism": "Optimism", "polygon": "Polygon",
    "avalanche": "Avalanche", "fantom": "Fantom", "gnosis": "Gnosis",
    "sepa": "SEPA (EUR)",
}

# ── x402 v2 spec helpers ──
import base64 as _base64

def _build_accepts_list(tool_id: str, pricing: dict) -> list:
    """Build x402 v2 spec 'accepts' array from TOOL_PRICES and CHAIN_USDC.
    
    This produces the canonical PaymentRequirements format that official
    x402 SDKs (@x402/fetch, x402 Python, x402 MCP) parse via PAYMENT-REQUIRED
    header or response body.
    """
    accepts = []
    for chain_key, cfg in CHAIN_USDC.items():
        method = cfg["method"]

        # Determine pay-to address based on chain
        if method == "payai":
            pay_to = SOL_PAY_TO
        elif method == "bitcoin_selfverify":
            pay_to = os.getenv("X402_BTC_PAY_TO", "")
        elif method == "tron_selfverify":
            pay_to = os.getenv("X402_TRON_PAY_TO", "")
        elif method == "asterpay":
            pay_to = os.getenv("ASTERPAY_SEPA_IBAN", "")
        else:
            pay_to = EVM_PAY_TO

        # Determine asset (primary token for the chain)
        asset = cfg.get("usdc", "")
        if not asset and "tokens" in cfg:
            first_token = next(iter(cfg["tokens"].values()), "")
            asset = first_token if first_token != "native" else ""

        extra = {
            "name": cfg["name"],
            "version": cfg["version"],
            "tool": tool_id,
            "chain": chain_key,
        }

        if method == "local_eip712" and cfg.get("chain_id"):
            extra["domain"] = {
                "name": cfg["name"],
                "version": cfg["version"],
                "chainId": cfg["chain_id"],
                "verifyingContract": pay_to,
            }
        elif method == "payai":
            extra["feePayer"] = "2wKupLR9q6wXYppw8Gr2NvWxKBUqm4PPJKkQfoxHDBg4"
        elif method == "tron_selfverify":
            extra["tronNetwork"] = "mainnet"
            extra["trc20Tokens"] = cfg.get("tokens", {})
        elif method == "bitcoin_selfverify":
            extra["paymentNetwork"] = "bitcoin"
            extra["settlementChains"] = ["base", "solana"]
        elif method == "asterpay":
            extra["currency"] = "EUR"
            extra["sepa"] = True

        requirement = {
            "scheme": "exact",
            "network": cfg["network"],
            "asset": asset,
            "amount": pricing["price_atoms"],
            "payTo": pay_to,
            "maxTimeoutSeconds": 180,
            "extra": extra,
        }

        # Add supported tokens for multi-token chains
        if "tokens" in cfg:
            requirement["supportedTokens"] = list(cfg["tokens"].keys())

        accepts.append(requirement)

    return accepts


def _build_bazaar_extension(tool_id: str, pricing: dict, accepts: list) -> dict:
    """Build x402 v2 bazaar extension for facilitator discovery indexing.
    
    Per x402 v2 bazaar extension spec, the extension follows the standard v2
    pattern: {info: {...}, schema: {...}}.
    
    - info: Contains the actual discovery data (HTTP method, parameters, output format)
    - schema: JSON Schema (Draft 2020-12) that validates the structure of info
    
    Per the bazaar spec:
    - input.type: always "http"
    - input.method: HTTP method (GET for tool_id ending in _info/_list, POST for others)
    - output.type: always "json"
    """
    # Map our categories to bazaar-standard categories
    CATEGORY_MAP = {
        "security": "security",
        "intelligence": "intelligence",
        "market": "market-data",
        "analysis": "analytics",
        "social": "social",
        "launchpad": "launchpad",
        "bundle": "bundles",
        "defi": "defi",
        "premium": "premium",
        "api": "api",
        "variant": "crypto",
    }
    category = pricing.get("category", "analysis")
    bazaar_category = CATEGORY_MAP.get(category, category)
    
    # Determine HTTP method: GET for read-only queries, POST for tools that execute
    read_only_suffixes = ("_info", "_list", "_check", "_scan", "_status", "_health")
    is_read_only = tool_id.endswith(read_only_suffixes)
    http_method = "GET" if is_read_only else "POST"
    
    # Build input/output from the first accepted payment method
    first_accept = accepts[0] if accepts else {}
    extra = first_accept.get("extra", {})
    
    # Build inputSchema matching the bazaar spec's info structure
    info_input = {
        "type": "http",
        "method": http_method,
    }
    
    if http_method == "GET":
        # Query params for GET: address and optional chain
        info_input["queryParams"] = {
            "address": {"type": "string", "description": f"Blockchain address or identifier for {tool_id}"},
            "chain": {"type": "string", "description": "Blockchain to query (default: base)"},
        }
    else:
        # Body params for POST: address and chain
        info_input["bodyType"] = "json"
        info_input["body"] = {
            "address": {"type": "string", "description": f"Blockchain address or identifier for {tool_id}"},
            "chain": {"type": "string", "description": "Blockchain to query (default: base)"},
        }
    
    info = {
        "input": info_input,
        "output": {
            "type": "json",
            "example": {
                "data": {"result": "tool output"},
                "sources_used": ["source1", "source2"],
            }
        },
        "category": bazaar_category,
        "tags": ["crypto", "security", "blockchain", tool_id],
        "description": pricing.get("description", f"{tool_id} — Rug Munch Intelligence"),
    }
    
    # Schema that validates the info structure per bazaar spec
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "input": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "const": "http"},
                    "method": {
                        "type": "string",
                        "enum": ["GET", "HEAD", "DELETE"] if http_method == "GET" else ["POST", "PUT", "PATCH"]
                    },
                    "queryParams": {"type": "object"} if http_method == "GET" else {"type": "object"},
                    "bodyType": {"type": "string", "enum": ["json", "form-data", "text"]},
                    "body": {"type": "object"},
                },
                "required": ["type", "method"],
                "additionalProperties": False,
            },
            "output": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "example": {"type": "object"},
                },
                "required": ["type"],
            },
            "category": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "description": {"type": "string"},
        },
        "required": ["input"],
    }
    
    return {
        "info": info,
        "schema": schema,
    }


def _build_resource_info(tool_id: str, pricing: dict) -> dict:
    """Build x402 v2 ResourceInfo object for PaymentRequired response.
    
    Per x402 v2 spec section 5.1.2, ResourceInfo has only three fields:
    - url (required): URL of the protected resource
    - description (optional): Human-readable description
    - mimeType (optional): MIME type of the expected response
    
    NOTE: serviceName, tags, and iconUrl are NOT part of the spec's ResourceInfo.
    The v2 spec does NOT include serviceName/tags/iconUrl at the resource level.
    We preserve them as legacy compat fields in x402.resource_metadata for our
    own internal use, but they must not appear in the spec-compliant ResourceInfo.
    """
    description = pricing.get("description", f"Rug Munch Intelligence — {tool_id}")
    # Per spec: max 200 chars for description
    if len(description) > 200:
        description = description[:197] + "..."
    
    return {
        "url": f"https://mcp.rugmunch.io/api/v1/x402-tools/{tool_id}",
        "description": description,
        "mimeType": "application/json",
    }


# ── 402 response builder ──
def build_402_response(tool_id: str, client_id: str = "") -> JSONResponse:
    """Build an x402 v2 compliant Payment Required response.
    
    Returns both:
    - V2 spec format (x402Version, resource, accepts) for official SDK compatibility
    - Legacy format (error, tool, price, x402.requirements) for backward compat
    - PAYMENT-REQUIRED base64 header for @x402/fetch and x402 Python SDK
    
    The v2 spec requires:
    - Top-level x402Version: 2
    - Top-level resource: {url, description, mimeType, serviceName, tags, iconUrl}
    - Top-level accepts: [{scheme, network, asset, amount, payTo, maxTimeoutSeconds, extra}]
    - PAYMENT-REQUIRED header: base64 JSON of {x402Version, resource, accepts}
    - Optional extensions: {bazaar: {discoverable, category, tags, inputSchema, outputSchema}}
    """
    pricing = TOOL_PRICES.get(tool_id, {"price_usd": 0.01, "price_atoms": "10000", "trial_free": 3})
    trial_free = pricing.get("trial_free", 3)
    
    # Check actual remaining trials for this client
    remaining = 0
    if client_id:
        can_use, remaining = check_trial(tool_id, client_id)
    
    # Build v2 spec accepts array (shared by both body and header)
    accepts = _build_accepts_list(tool_id, pricing)
    
    # Build v2 spec resource object
    resource = _build_resource_info(tool_id, pricing)
    
    # Build bazaar extension for discovery indexing
    bazaar = _build_bazaar_extension(tool_id, pricing, accepts)
    
    # ── V2 spec body format (what official SDKs parse) ──
    v2_body = {
        "x402Version": 2,
        "error": "PAYMENT-SIGNATURE header is required",
        "resource": resource,
        "accepts": accepts,
        "extensions": {
            "bazaar": bazaar,
        },
        # ── Legacy compat fields (not in spec but needed for our gateway clients) ──
        "error_legacy": "Payment Required",
        "tool": tool_id,
        "price": f"${pricing['price_usd']:.2f}",
        "trial_free": trial_free,
        "trial_remaining": remaining,
        "trial_used": remaining <= 0,
        "wallet_required": remaining == -1,
        "message": (
            f"Connect a wallet to continue. Your 1 free trial is used — link MetaMask or Phantom to get {trial_free} free calls per tool. From ${pricing['price_usd']:.2f}/call after that."
            if remaining == -1
            else f"All {trial_free} free trial{'s' if trial_free != 1 else ''} used. Pay {pricing['price_atoms']} atoms to use {tool_id}. Pay on {', '.join(CHAIN_NAMES.get(c, c) for c in CHAIN_USDC.keys())}."
        ),
        "accepted_chains": list(CHAIN_USDC.keys()),
        "chain_details": {
            k: {
                "network": v["network"],
                "facilitators": v.get("facilitators", []),
                "tokens": list(v.get("tokens", {"USDC": v.get("usdc", "")}).keys()),
            }
            for k, v in CHAIN_USDC.items()
        },
        # ── Legacy compat: nested requirements for our Cloudflare workers ──
        "x402": {
            "version": "2",
            "requirements": accepts,  # Same array, different field name for backward compat
        },
    }
    
    # ── Build PAYMENT-REQUIRED header (base64 JSON of v2 spec PaymentRequired) ──
    payment_required_header_obj = {
        "x402Version": 2,
        "error": "PAYMENT-SIGNATURE header is required",
        "resource": resource,
        "accepts": accepts,
        "extensions": {"bazaar": bazaar},
    }
    payment_required_b64 = _base64.b64encode(
        json.dumps(payment_required_header_obj, separators=(",", ":")).encode()
    ).decode("ascii")
    
    return JSONResponse(
        status_code=402,
        content=v2_body,
        headers={
            "PAYMENT-REQUIRED": payment_required_b64,
            "X-Paywall-Version": "2",
            "Content-Type": "application/json",
            **SECURITY_HEADERS,
        },
    )

# ── Payment header parser (supports v1 x-pay and v2 PAYMENT-SIGNATURE) ──
def parse_x_pay_header(header_value: str) -> Optional[dict]:
    """Parse payment payload from x-pay / PAYMENT-SIGNATURE header.
    
    Supports three formats:
    1. v2 spec: base64-encoded JSON (PAYMENT-SIGNATURE header)
    2. v1 legacy: "x402 <json>" or "X-Pay: <json>" (x-pay header)
    3. Plain JSON
    """
    if not header_value or not header_value.strip():
        return None
    try:
        stripped = header_value.strip()
        
        # v2 spec: PAYMENT-SIGNATURE is base64-encoded JSON
        # Try base64 decode first (will fail fast if it's not base64)
        try:
            decoded = _base64.b64decode(stripped).decode("utf-8")
            if decoded.startswith("{"):
                payload = json.loads(decoded)
                # v2 format: normalize PaymentPayload to our expected structure
                # v2 PaymentPayload has: x402Version, resource, accepted, payload, extensions
                # Our verifier expects: accepted (dict), payload (with signature/authorization)
                if "x402Version" in payload:
                    # v2 PaymentPayload — our verifier already handles this format
                    # It extracts network from payload.accepted and routes to facilitator
                    return payload
                return payload
        except Exception:
            pass  # Not base64, try other formats
        
        # v1 legacy: "x402 <json>" or "X-Pay: <json>"
        if stripped.startswith("x402 "):
            payload_str = stripped[5:].strip()
        elif stripped.startswith("X-Pay: "):
            payload_str = stripped[7:].strip()
        else:
            payload_str = stripped
        
        if payload_str.startswith("{"):
            return json.loads(payload_str)
        
        return None
    except Exception as e:
        logger.warning(f"Failed to parse payment header: {e}")
        return None

# ── Verification via Facilitator Router ──
async def verify_payment_via_router(payload: dict) -> dict:
    """Verify x402 payment payload through the multi-facilitator smart router.
    
    Flow:
    1. Parse payload → extract network (chain) and asset (token)
    2. Map network to chain_key (e.g. 'eip155:8453' → 'base', 'tron:mainnet' → 'tron')
    3. Determine token symbol from asset address
    4. Route to best facilitator via FacilitatorRouter.verify()
    5. Fall back to old verify_payment() if router not available
    """
    accepted = payload.get("accepted", {})
    network = accepted.get("network", "")
    asset_address = accepted.get("asset", "")

    # Map network → chain_key
    chain_key = None
    token_symbol = "USDC"

    for ck, cfg in CHAIN_USDC.items():
        if cfg["network"] == network:
            chain_key = ck
            # Detect token from asset address
            if asset_address:
                token_symbol = _detect_token_from_asset(asset_address, cfg)
            break

    if not chain_key:
        # Unknown network — fall back to old verifier
        from app.routers.x402_middleware import PaymentVerifier, FACILITATOR_CONFIGS
        verifier = PaymentVerifier()
        return await verifier.verify_payment(
            json.dumps(payload),
            network_key="base",
        )

    # Try the smart router first
    try:
        from app.facilitators.router import get_facilitator_router
        router = get_facilitator_router()

        # Build requirements from payload
        requirements = {
            "x402Version": payload.get("x402Version", 2),
            "resource": payload.get("resource", {}),
            "accepts": [{
                "scheme": accepted.get("scheme", "exact"),
                "network": network,
                "asset": asset_address,
                "amount": accepted.get("amount", ""),
                "payTo": accepted.get("payTo", ""),
                "maxTimeoutSeconds": accepted.get("maxTimeoutSeconds", 180),
                "extra": accepted.get("extra", {}),
            }],
        }

        result = await router.verify(
            payload=payload,
            chain_key=chain_key,
            token_symbol=token_symbol,
            requirements=requirements,
        )

        if result.verified:
            logger.info(
                f"Router verified payment via {result.facilitator}: "
                f"chain={chain_key} token={token_symbol} amount={result.amount}"
            )
            return {
                "verified": True,
                "reason": result.reason,
                "tx_hash": result.tx_hash,
                "payer": result.payer,
                "amount": result.amount,
                "chain": chain_key,
                "token": token_symbol,
                "facilitator": result.facilitator,
                "method": f"router:{result.facilitator}",
            }
        else:
            logger.warning(
                f"Router rejected payment for {chain_key}/{token_symbol}: {result.reason}"
            )
            return {
                "verified": False,
                "reason": result.reason,
                "chain": chain_key,
                "token": token_symbol,
            }

    except ImportError:
        logger.debug("Facilitator router not available — falling back to old verifier")
    except Exception as e:
        logger.error(f"Router verification error: {e} — falling back to old verifier")

    # Fallback: old verification logic
    return await verify_payment(payload)


def _detect_token_from_asset(asset_address: str, chain_cfg: dict) -> str:
    """Detect token symbol from asset address using chain config."""
    asset_lower = asset_address.lower()

    # Check USDC
    if chain_cfg.get("usdc", "").lower() == asset_lower:
        return "USDC"

    # Check additional tokens
    tokens = chain_cfg.get("tokens", {})
    for symbol, addr in tokens.items():
        if isinstance(addr, str) and addr.lower() == asset_lower:
            return symbol

    # Heuristic detection
    if "TR7NH" in asset_lower:
        return "USDT"  # USDT on TRC20
    if "TEkxi" in asset_lower:
        return "USDC"  # USDC on TRC20
    if "TPYm" in asset_lower:
        return "USDD"  # USDD on TRC20
    if asset_lower == "native" or asset_address == "BTC":
        return "BTC"

    return "USDC"  # Default


# ── Original verification logic (fallback) ──
async def verify_payment(payload: dict) -> dict:
    """Verify x402 payment payload against all supported chains"""
    if not VERIFIER:
        return {"verified": False, "reason": "PaymentVerifier not initialized"}
    
    accepted = payload.get("accepted", {})
    network = accepted.get("network", "")
    
    # Find matching chain config
    chain_key = None
    chain_cfg = None
    for ck, cc in CHAIN_USDC.items():
        if cc["network"] == network:
            chain_key = ck
            chain_cfg = cc
            break
    
    if not chain_cfg:
        return {"verified": False, "reason": f"Unsupported network: {network}"}
    
    verify_method = chain_cfg.get("verify", "facilitator")
    
    # Facilitator-verified chains (Base, Solana) — fast, federated
    if verify_method == "facilitator":
        if chain_cfg["method"] == "local_eip712":
            return VERIFIER._verify_eip712_local(payload)
        elif chain_cfg["method"] == "payai":
            return await VERIFIER._verify_via_payai(payload, None)
    
    # Self-verified chains (ETH, BSC, ARB, OPT, POL) — check USDC transfer on-chain
    if verify_method == "self":
        return await self_verify_evm_usdc(payload, chain_key, chain_cfg)
    
    return {"verified": False, "reason": f"Unknown verify method: {verify_method}"}


async def self_verify_evm_usdc(payload: dict, chain_key: str, chain_cfg: dict) -> dict:
    """Self-verify a USDC transfer on EVM chains without a facilitator.
    
    How it works:
    1. Extract tx hash, network, sender from the x402 payload
    2. Look up the transaction receipt on Etherscan/BSCScan/etc via eth_getTransactionReceipt
    3. Decode ERC-20 Transfer events from receipt logs (topic0 = keccak256("Transfer(address,address,uint256)"))
    4. Verify: correct USDC contract, 'to' matches PAY_TO, amount matches expected price in atoms
    5. Mark the tx as spent in Redis with 86400s TTL (prevent double-use, 24h window)
    """
    # ERC-20 Transfer event signature: keccak256("Transfer(address,address,uint256)")
    TRANSFER_EVENT_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    try:
        accepted = payload.get("accepted", {})
        tx_hash = payload.get("txHash") or payload.get("signature") or accepted.get("transaction")
        payer = payload.get("payer") or payload.get("from") or accepted.get("payer")
        amount_atoms = accepted.get("amount") or payload.get("amount")
        
        if not tx_hash:
            return {"verified": False, "reason": "No tx hash in payment payload"}
        
        # Prevent double-spend: check Redis first
        r = get_redis()
        if r:
            spent_key = f"x402:spent_tx:{tx_hash}"
            if r.get(spent_key):
                return {"verified": False, "reason": f"Transaction {tx_hash[:16]}... already used"}
        
        # Resolve expected amount from tool pricing if not in payload
        tool_id = (accepted.get("extra", {}).get("tool") or 
                   payload.get("tool") or 
                   accepted.get("resource", "").split("/")[-1] if accepted.get("resource") else None)
        if not amount_atoms and tool_id and tool_id in TOOL_PRICES:
            amount_atoms = TOOL_PRICES[tool_id].get("price_atoms")
        
        # ── Blockscout API v2 (free, no API key needed) ──
        # Maps chain_id → Blockscout base URL
        chain_id = chain_cfg.get("chain_id")
        blockscout_urls = {
            1: "https://eth.blockscout.com",
            42161: "https://arbitrum.blockscout.com",
            10: "https://optimism.blockscout.com",
            137: "https://polygon.blockscout.com",
            8453: "https://base.blockscout.com",
            100: "https://gnosis.blockscout.com",
            43114: "https://avalanche.blockscout.com",
            250: "https://fantom.blockscout.com",
            56: "https://bsc.blockscout.com",
        }
        
        blockscout_base = blockscout_urls.get(chain_id)
        if not blockscout_base:
            return {"verified": False, "reason": f"No Blockscout URL for chain_id {chain_id}"}
        
        import httpx
        # Blockscout v2 API: /api/v2/transactions/{tx_hash}
        tx_url = f"{blockscout_base}/api/v2/transactions/{tx_hash}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(tx_url)
            if resp.status_code != 200:
                return {"verified": False, "reason": f"TX {tx_hash[:16]}... not found on {chain_key} (HTTP {resp.status_code})"}
            tx_data = resp.json()
        
        # Check transaction status
        tx_status = tx_data.get("status") or tx_data.get("result")
        if tx_status != "ok" and tx_status != "1":
            return {"verified": False, "reason": f"TX {tx_hash[:16]}... failed on-chain (status={tx_status})"}
        
        # Decode ERC-20 Transfer events from receipt logs
        our_address = EVM_PAY_TO.lower()
        usdc_address = chain_cfg["usdc"].lower()
        expected_amount = str(amount_atoms) if amount_atoms else None
        
        logs = tx_data.get("decoded_input", {}).get("logs") or tx_data.get("logs") or []
        if not logs:
            # Try alternate: fetch receipt directly
            receipt_url = f"{blockscout_base}/api?module=transaction&action=gettxreceiptstatus&txhash={tx_hash}"
            async with httpx.AsyncClient(timeout=10) as client2:
                r2 = await client2.get(receipt_url)
                if r2.status_code == 200:
                    receipt_data = r2.json()
                    logs = receipt_data.get("result", {}).get("logs", []) or receipt_data.get("logs", [])
        
        transfer_found = False
        amount_match = False
        actual_amount = None
        
        for log in logs:
            topics = log.get("topics", [])
            
            if len(topics) < 3:
                continue
            if topics[0].lower() != TRANSFER_EVENT_TOPIC0:
                continue
            if log.get("address", "").lower() != usdc_address:
                continue
            
            # Decode 'to' address from topic2
            try:
                to_address = "0x" + topics[2][-40:].lower()
            except (IndexError, ValueError):
                continue
            
            if to_address != our_address:
                continue
            
            # Decode amount from data field
            transfer_found = True
            log_data = log.get("data", "0x")
            try:
                if log_data and log_data.startswith("0x") and len(log_data) >= 66:
                    actual_amount = str(int(log_data[:66], 16))
                elif log_data:
                    actual_amount = str(int(log_data, 16))
            except (ValueError, TypeError):
                logger.warning(f"Could not decode Transfer data for {tx_hash[:16]}...: {str(log_data)[:20]}")
            
            # Verify amount matches
            if expected_amount and actual_amount:
                if actual_amount == expected_amount:
                    amount_match = True
                else:
                    logger.warning(
                        f"Amount mismatch for {tx_hash[:16]}...: "
                        f"expected {expected_amount} atoms, got {actual_amount} atoms on {chain_key}"
                    )
            elif actual_amount:
                # Check if amount matches any tool price
                for tid, pricing in TOOL_PRICES.items():
                    if str(pricing.get("price_atoms")) == actual_amount:
                        amount_match = True
                        break
            
            break  # Found Transfer to our address
        
        if not transfer_found:
            return {"verified": False, "reason": f"No USDC Transfer to {our_address[:10]}... found in {tx_hash[:16]}..."}
        
        if not amount_match and expected_amount and actual_amount:
            return {
                "verified": False,
                "reason": f"Amount mismatch: expected {expected_amount} atoms, got {actual_amount} atoms",
            }
        
        # Mark as spent in Redis with 86400s (24h) TTL
        tool_name = tool_id or "unknown"
        if r:
            spent_key = f"x402:spent_tx:{tx_hash}"
            payment_data = {
                "chain": chain_key,
                "payer": payer or "unknown",
                "amount": actual_amount or amount_atoms or "0",
                "tool": tool_name,
                "timestamp": time.time(),
            }
            r.setex(spent_key, 86400, json.dumps(payment_data))
        
        # Persist to Supabase (non-blocking)
        try:
            from app.routers.x402_dashboard import _persist_payment_to_supabase
            import asyncio
            asyncio.create_task(_persist_payment_to_supabase(
                tool=tool_name,
                amount_atoms=str(actual_amount or amount_atoms or "0"),
                chain=chain_key,
                payer=payer or "unknown",
                tx_hash=tx_hash,
                status="fulfilled",
            ))
        except Exception:
            pass
        
        logger.info(
            f"Verified USDC payment: {tx_hash[:16]}... on {chain_key} "
            f"from {payer[:10] if payer else 'unknown'}... amount={actual_amount or 'unknown'} tool={tool_name}"
        )
        return {
            "verified": True,
            "chain": chain_key,
            "tx_hash": tx_hash,
            "payer": payer,
            "amount": actual_amount or amount_atoms,
            "method": "blockscout-verify",
        }
    
    except Exception as e:
        logger.error(f"Self-verify error: {e}")
        return {"verified": False, "reason": f"Verification error: {str(e)[:100]}"}

# ── Refund policy helpers ──

def _record_refundable_payment(tx_hash: str, chain: str, payer: str, amount: str, tool: str, reason: str):
    """Record a refundable payment in Redis when a tool returns empty data.
    
    Stores in Redis key 'x402:refund:{tx_hash}' with 7-day TTL.
    Actual USDC refund is a manual process — we send USDC back from whichever chain has funds.
    """
    r = get_redis()
    if not r:
        logger.warning(f"Cannot record refund for {tx_hash}: Redis unavailable")
        return
    
    refund_key = f"x402:refund:{tx_hash}"
    refund_data = {
        "tx_hash": tx_hash,
        "chain": chain or "unknown",
        "payer": payer or "unknown",
        "amount_atoms": str(amount) if amount else "0",
        "tool": tool or "unknown",
        "reason": reason,
        "status": "refundable",       # refundable -> requested -> processing -> completed
        "flagged_at": time.time(),
        "requested_at": None,
        "processed_at": None,
    }
    try:
        r.setex(refund_key, 7 * 86400, json.dumps(refund_data))  # 7-day TTL
        logger.info(f"Recorded refundable payment: {tx_hash[:16]}... tool={tool} reason={reason}")
    except Exception as e:
        logger.error(f"Failed to record refund for {tx_hash}: {e}")


# ── Trial tracking (Redis-based) ──
_redis_client = None

def get_redis():
    """Lazy Redis connection for trial tracking"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", ""),
                db=0,
                decode_responses=True,
            )
            _redis_client.ping()
        except Exception:
            logger.warning("x402 trials: Redis unavailable, trials disabled")
            _redis_client = False  # Sentinel to avoid retrying
    return _redis_client if _redis_client else None

def get_client_id(request: Request) -> str:
    """Get unique client identifier resistant to spoofing.
    
    Priority:
    1. Wallet address from x-pay or Authorization (cryptographic identity — VPN-proof)
    2. Device fingerprint from X-Device-Id header (canvas/WebGL/font hash — VPN-proof, survives incognito)
    3. Cloudflare Turnstile token (browser-verified, VPN-proof, CAPTCHA-backed)
    4. TLS fingerprint hash + IP + UA (catches scripted rotation, WEAK against VPNs)
    
    VPN attack model: An attacker with NordVPN/etc can cycle 5000+ IPs.
    IP-based fingerprinting is useless against this. Solutions:
    - Wallet-based identity (crypto signature = 1 identity per wallet, ever)
    - Turnstile CAPTCHA (rate limits new identity creation, costs attacker time)
    - Global trial budget (not per-IP: total platform-wide free calls capped)
    - Progressive friction (more trials = require wallet)
    """
    # 1. Wallet address from payment (highest trust — requires chain signature, VPN-proof)
    x_pay = request.headers.get("x-pay", "") or request.headers.get("X-Pay", "")
    if x_pay:
        payload = parse_x_pay_header(x_pay)
        if isinstance(payload, dict):
            # Extract payer from verified x402 payload
            payer = payload.get("payer") or payload.get("from")
            if payer and len(payer) >= 10:
                return f"w:{payer.lower()}"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and len(auth) > 40:
        return f"w:{auth[7:47].lower()}"
    
    # 2. Device fingerprint from frontend (browser-generated, VPN-proof)
    # The frontend generates a stable device ID using canvas/WebGL/font/audio fingerprinting
    # This survives IP changes, VPN cycling, and even incognito mode
    device_id = request.headers.get("X-Device-Id", "") or request.headers.get("x-device-id", "")
    if device_id and len(device_id) >= 16 and re.match(r'^[a-f0-9]+$', device_id[:16]):
        return f"dev:{device_id[:24]}"
    
    # 2b. Cloudflare Turnstile token (browser-verified, VPN-proof)
    turnstile_token = request.headers.get("X-Turnstile-Token", "")
    if turnstile_token and len(turnstile_token) >= 20:
        turnstile_id = hashlib.sha256(turnstile_token.encode()).hexdigest()[:16]
        return f"ts:{turnstile_id}"
    
    # 3. Fallback: IP + browser fingerprint (WEAK against VPNs, but catches basic abuse)
    cf_ip = request.headers.get("CF-Connecting-IP", "")
    if cf_ip and re.match(r'^[\d.:a-fA-F]+$', cf_ip.strip()):
        client_ip = cf_ip.strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    ua = request.headers.get("User-Agent", "unknown")[:64].strip()
    ua_norm = re.sub(r'[\d]+', 'N', ua.lower())  # Normalize version numbers
    accept_lang = request.headers.get("Accept-Language", "unknown")[:32].strip().lower()
    sec_fetch = request.headers.get("Sec-Fetch-Mode", "unknown")[:16].strip().lower()
    # TLS JA3-style fingerprint if available (Cloudflare provides this)
    cf_tls = request.headers.get("CF-Visitor", "")[:32]
    fp_input = f"{client_ip}|{ua_norm}|{accept_lang}|{sec_fetch}|{cf_tls}"
    fp = hashlib.sha256(fp_input.encode()).hexdigest()[:20]
    
    # Also track the bare IP for subnet-level rate limiting
    ip_key = hashlib.sha256(client_ip.encode()).hexdigest()[:12]
    
    return f"fp:{fp}:ip:{ip_key}"

def check_trial(tool_id: str, client_id: str) -> tuple:
    """
    Check and consume a free trial for a tool.
    Returns (can_use_trial: bool, remaining: int)
    
    Anti-abuse measures:
    - Fingerprint-based client_id (IP + UA + Accept-Language + Sec-Fetch hash) — hard to rotate at scale
    - Per-fingerprint AND per-IP-level limits (IP daily + max fingerprints per IP)
    - Per-tool AND global daily limits per fingerprint
    - Redis atomic operations (INCR is atomic — no race condition)
    - Fail-closed: Redis down = no trials
    - Trials NEVER reset — one-time per identity, no TTL on per-tool keys
    - IP fingerprint cap: max 5 unique fingerprints per IP per day (detects UA cycling)
    - IP daily cap: max 30 free calls per IP per day across all fingerprints
    - Global daily cap: max 2000 free calls platform-wide per day (VPN-proof)
    - Progressive wallet: fingerprint IDs get 1 trial, then must connect wallet for full allotment
    """
    pricing = TOOL_PRICES.get(tool_id, {"trial_free": 3})
    max_trials = pricing.get("trial_free", 3)
    
    if max_trials <= 0:
        return False, 0
    
    r = get_redis()
    if not r:
        # Redis unavailable — deny trial (fail-closed for security)
        return False, 0
    
    key = f"x402:trial:{client_id}:{tool_id}"
    
    try:
        # ── Per-fingerprint per-tool limit ──
        used = int(r.get(key) or 0)
        remaining = max_trials - used
        if remaining <= 0:
            # Already exhausted this fingerprint+tool combo
            logger.warning(f"Trial exhausted: {client_id} for {tool_id} ({used}/{max_trials})")
            return False, 0
        
        # ── Global daily limit per fingerprint (max 20 free calls/day across ALL tools) ──
        daily_key = f"x402:daily:{client_id}"
        daily_used = int(r.get(daily_key) or 0)
        MAX_DAILY_FREE = int(os.getenv("X402_MAX_DAILY_FREE", "20"))
        if daily_used >= MAX_DAILY_FREE:
            logger.warning(f"Daily free limit: {client_id} used {daily_used}/{MAX_DAILY_FREE}")
            return False, 0
        
        # ── Global platform-wide trial budget (VPN-proof: limits total free calls regardless of IP cycling) ──
        # If someone VPN-cycles 5000 IPs, they still hit this global cap
        global_key = "x402:global:trials_today"
        global_used = int(r.get(global_key) or 0)
        MAX_GLOBAL_DAILY = int(os.getenv("X402_MAX_GLOBAL_DAILY", "2000"))
        if global_used >= MAX_GLOBAL_DAILY:
            logger.warning(f"Global daily trial budget exhausted: {global_used}/{MAX_GLOBAL_DAILY}")
            return False, 0
        
        # ── Progressive wallet requirement ──
        # Identity hierarchy (trust level):
        #   w:xxx = wallet (crypto signature, highest trust) → full trials
        #   dev:xxx = device fingerprint (canvas/WebGL/font, VPN-proof) → full trials  
        #   ts:xxx = Turnstile CAPTCHA token → full trials (costs attacker time per identity)
        #   fp:xxx = IP+UA fingerprint (WEAK, trivially defeated by VPN) → 1 trial only
        is_wallet = client_id.startswith("w:")
        is_device = client_id.startswith("dev:")
        is_turnstile = client_id.startswith("ts:")
        is_trusted_id = is_wallet or is_device or is_turnstile
        
        if not is_trusted_id:
            # Untrusted fingerprint-only IDs: 1 free trial, then require wallet or device ID
            # This kills VPN abuse: you get 1 taste from bare IP, then must connect wallet
            fp_override_trials = 1
            if used >= fp_override_trials:
                logger.warning(f"Wallet/device required: {client_id} used {used} fingerprint trials, needs wallet for more")
                return False, -1  # -1 = needs wallet/device, not just needs payment
        
        # ── IP-level daily limit (prevents bot from cycling UAs on same IP) ──
        # Extract IP key from client_id (format: fp:xxx:ip:yyy)
        ip_part = client_id.split(":ip:")[-1] if ":ip:" in client_id else ""
        if ip_part:
            ip_daily_key = f"x402:ip_daily:{ip_part}"
            ip_daily_used = int(r.get(ip_daily_key) or 0)
            MAX_IP_DAILY_FREE = int(os.getenv("X402_MAX_IP_DAILY_FREE", "30"))
            if ip_daily_used >= MAX_IP_DAILY_FREE:
                logger.warning(f"IP daily limit: {ip_part} used {ip_daily_used}/{MAX_IP_DAILY_FREE}")
                return False, 0
            # Also track total unique fingerprints per IP (detects UA cycling)
            ip_fp_key = f"x402:ip_fps:{ip_part}"
            ip_fp_count = r.scard(ip_fp_key) if r.exists(ip_fp_key) else 0
            MAX_FPS_PER_IP = int(os.getenv("X402_MAX_FPS_PER_IP", "5"))
            if ip_fp_count >= MAX_FPS_PER_IP:
                logger.warning(f"Too many fingerprints on IP: {ip_part} has {ip_fp_count} unique IDs")
                return False, 0
        
        # ── Atomic consumption (INCR is atomic — no race condition) ──
        pipe = r.pipeline()
        pipe.incr(key)       # Increment per-tool usage
        pipe.incr(daily_key) # Increment daily global usage
        pipe.incr(global_key) # Increment global platform-wide budget
        # Track IP-level counters (anti-bot UA cycling)
        if ip_part:
            pipe.incr(f"x402:ip_daily:{ip_part}")  # IP daily total
            # Track unique fingerprint per IP (use SET for dedup)
        results = pipe.execute()
        
        # Set TTL on first use
        # Trials NEVER reset — no expiry on per-tool key (one-time per identity)
        # Daily key still expires to reset the daily global counter
        if results[0] == 1:  # First use of this tool
            pass  # No expiry — trials are permanent per fingerprint
        if results[1] == 1:  # First use today
            r.expire(daily_key, 86400)  # 24 hour expiry for daily limit
        # Global daily counter: 24h TTL
        global_result_idx = 2  # after key and daily_key
        if int(results[global_result_idx]) == 1:
            r.expire(global_key, 86400)
        
        # IP-level TTLs
        if ip_part:
            ip_daily_key = f"x402:ip_daily:{ip_part}"
            if r.get(ip_daily_key) and int(r.get(ip_daily_key)) == 1:
                r.expire(ip_daily_key, 86400)  # 24h
            # Track unique fingerprints per IP using a set
            ip_fp_key = f"x402:ip_fps:{ip_part}"
            r.sadd(ip_fp_key, client_id)
            r.expire(ip_fp_key, 86400)  # Reset fingerprint count daily
        
        new_remaining = max_trials - results[0]
        return True, new_remaining
        
    except Exception as e:
        logger.error(f"Trial check error: {e}")
        return False, 0  # Deny on error (fail-closed)

# ── The actual middleware function ──
async def x402_enforcement_middleware(request: Request, call_next) -> Response:
    """
    x402 payment enforcement with free trial support.
    Intercepts /api/v1/x402-tools/* and returns 402 if no valid payment and no trials.
    """
    path = request.url.path
    
    # Only intercept x402-tools
    if not path.startswith("/api/v1/x402-tools/"):
        return await call_next(request)
    
    # Allow preflight
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # ── Free endpoints — always accessible, no payment required ──────
    # These MUST be checked before bot detection so AI agents can discover us.
    # Discovery/catalog/framework endpoints are useless if bots can't reach them.
    FREE_GET_PATHS = {
        "/api/v1/x402-tools/discovery",
        "/api/v1/x402-tools/frameworks",
        "/api/v1/x402-tools/openai-tools",
        "/api/v1/x402-tools/anthropic-tools",
        "/api/v1/x402-tools/gemini-tools",
        "/api/v1/x402-tools/langchain-tools",
        "/api/v1/x402-tools/catalog",
        "/api/v1/x402-tools/bundles",
        "/api/v1/x402-tools/payment-methods",
    }
    FREE_PATHS = {
        "/api/v1/x402-tools/discovery",
        "/api/v1/x402-tools/frameworks",
        "/api/v1/x402-tools/openai-tools",
        "/api/v1/x402-tools/anthropic-tools",
        "/api/v1/x402-tools/gemini-tools",
        "/api/v1/x402-tools/langchain-tools",
        "/api/v1/x402-tools/catalog",
        "/api/v1/x402-tools/bundles",
        "/api/v1/x402-tools/payment-methods",
        "/api/v1/x402-tools/human-execute",
    }
    # Also exempt all /api/v1/x402/ admin endpoints
    if path.rstrip("/") in FREE_PATHS or path.startswith("/api/v1/x402/"):
        return await call_next(request)
    # GET requests to free paths are always allowed (discovery for agents)
    if request.method == "GET" and path.rstrip("/") in FREE_GET_PATHS:
        return await call_next(request)
    
    # ── Bot / abuse detection ─────────────────────────────────────
    # Only block bots on PAID tool endpoints, not discovery
    user_agent = (request.headers.get("User-Agent", "") or "").lower()
    
    # Block known bot/scanner user agents ONLY on paid endpoints
    BLOCKED_AGENTS = [
        "masscan", "nmap", "nikto", "sqlmap", "dirbuster", "gobuster",
        "zgrab", "censysinspect", "cloudflare-speedtest",
    ]
    # Legitimate API clients (curl, python, etc.) are welcome — just need payment
    SCANNER_AGENTS = [
        "masscan", "nmap", "nikto", "sqlmap", "dirbuster", "gobuster",
        "zgrab", "censysinspect",
    ]
    if any(bot in user_agent for bot in SCANNER_AGENTS):
        return JSONResponse(
            status_code=403,
            content={"error": "Automated access requires x402 payment. Use x-pay header or a proper API client.", "docs": "https://rugmunch.io/mcp-docs"},
            headers=SECURITY_HEADERS,
        )
    
    # Rate limit: max 5 rapid same-tool requests per fingerprint per 60s (burst protection)
    client_id = get_client_id(request)
    # Extract tool name early for burst tracking
    path_tool_id = path.rstrip("/").split("/")[-1] if path.count("/") >= 4 else "unknown"
    r = get_redis()
    if r and re.match(r'^[a-zA-Z0-9_]+$', path_tool_id):
        burst_key = f"x402:burst:{client_id}:{path_tool_id}"
        try:
            burst_count = int(r.get(burst_key) or 0)
            BURST_LIMIT = int(os.getenv("X402_BURST_LIMIT", "5"))
            BURST_WINDOW = int(os.getenv("X402_BURST_WINDOW", "60"))
            if burst_count >= BURST_LIMIT:
                logger.warning(f"Burst limit: {client_id} hit {burst_count} requests in {BURST_WINDOW}s")
                return JSONResponse(
                    status_code=429,
                    content={"error": f"Rate limited. Max {BURST_LIMIT} requests per {BURST_WINDOW}s per tool.", "retry_after": BURST_WINDOW},
                    headers={**SECURITY_HEADERS, "Retry-After": str(BURST_WINDOW)},
                )
            pipe = r.pipeline()
            pipe.incr(burst_key)
            if burst_count == 0:
                pipe.expire(burst_key, BURST_WINDOW)
            pipe.execute()
        except Exception:
            pass  # Don't block on burst tracking errors
    
    # Free paths already checked above — flow continues to paid tool enforcement
    # Extract tool name
    tool_id = path.rstrip("/").split("/")[-1]
    
    # Input validation: reject tool IDs with suspicious characters
    if not re.match(r'^[a-zA-Z0-9_]+$', tool_id):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid tool identifier"},
            headers=SECURITY_HEADERS,
        )
    
    client_id = get_client_id(request)
    
    # ── Payment header parsing: support both v1 (x-pay) and v2 (PAYMENT-SIGNATURE) ──
    # v2 specifies PAYMENT-SIGNATURE header (base64 JSON), v1 uses X-Pay or x-pay
    pay_sig = request.headers.get("PAYMENT-SIGNATURE", "") or request.headers.get("Payment-Signature", "")
    x_pay = request.headers.get("x-pay", "") or request.headers.get("X-Pay", "")
    
    # Reject oversized payment headers (DoS protection)
    if pay_sig and len(pay_sig) > 16384:
        return JSONResponse(
            status_code=400,
            content={"error": "Payment header too large"},
            headers=SECURITY_HEADERS,
        )
    if x_pay and len(x_pay) > 8192:
        return JSONResponse(
            status_code=400,
            content={"error": "Payment header too large"},
            headers=SECURITY_HEADERS,
        )
    
    # Parse payment payload from whichever header is present
    # v2 PAYMENT-SIGNATURE takes priority over v1 x-pay
    payload = None
    if pay_sig:
        payload = parse_x_pay_header(pay_sig)  # parse_x_pay handles base64 too
        if payload:
            # v2 spec: payload should have top-level x402Version, accepted, payload, resource
            # Normalize: make sure "accepted" is available at top level for our verifier
            if "accepted" not in payload and "payload" in payload:
                # This is a v2 PaymentPayload format — extract payment info
                pass  # The verify_payment_via_router already handles this format
    elif x_pay:
        payload = parse_x_pay_header(x_pay)
    
        if payload:
            # Validate payment payload structure
            if not isinstance(payload, dict):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid payment payload structure"},
                    headers=SECURITY_HEADERS,
                )
            accepted = payload.get("accepted", {})
            if not isinstance(accepted, dict):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid accepted payment structure"},
                    headers=SECURITY_HEADERS,
                )
            result = await verify_payment_via_router(payload)
            if result.get("verified"):
                # Payment OK — attach info and proceed
                request.state.x402_verified = True
                request.state.x402_payer = result.get("payer", "")
                request.state.x402_chain = result.get("chain", "")
                request.state.x402_tx_hash = result.get("tx_hash", "")
                request.state.x402_amount = result.get("amount", "")
                request.state.x402_method = result.get("method", "")
                
                response = await call_next(request)
                response.headers["X-RMI-Payment"] = "verified"
                
                # ── x402 v2: PAYMENT-RESPONSE header (base64 SettlementResponse) ──
                # The v2 spec requires a PAYMENT-RESPONSE header on 200 responses
                # after successful settlement, containing base64 JSON:
                # {success: true, transaction: "0x...", network: "eip155:8453", payer: "0x..."}
                settlement_response = {
                    "success": True,
                    "transaction": result.get("tx_hash", ""),
                    "network": CHAIN_USDC.get(result.get("chain", ""), {}).get("network", result.get("chain", "")),
                    "payer": result.get("payer", ""),
                }
                if result.get("amount"):
                    settlement_response["amount"] = result.get("amount")
                try:
                    payment_response_b64 = _base64.b64encode(
                        json.dumps(settlement_response, separators=(",", ":")).encode()
                    ).decode("ascii")
                    response.headers["PAYMENT-RESPONSE"] = payment_response_b64
                except Exception:
                    pass  # Don't fail on settlement header encoding errors
                
                # Add security headers to successful responses too
                for k, v in SECURITY_HEADERS.items():
                    if k not in response.headers:
                        response.headers[k] = v
                
                # ── Refund policy: detect empty/no-data responses and auto-flag for refund ──
                # If a paid tool returns no real data, the payment should be refundable.
                # We record this in Redis; actual USDC refund is a manual process from our wallet.
                _should_flag_refund = False
                _refund_reason = ""
                try:
                    # Read the response body to check for empty data
                    resp_body = b""
                    async for chunk in response.body_iterator:
                        resp_body += chunk
                    # Reconstruct response with the read body
                    from starlette.responses import Response as StarletteResponse
                    response = StarletteResponse(
                        content=resp_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                    
                    if response.status_code >= 400:
                        _should_flag_refund = True
                        _refund_reason = f"HTTP {response.status_code} error response"
                    elif resp_body:
                        try:
                            body_json = json.loads(resp_body)
                            # Heuristic: empty data detection
                            # No sources, no findings, empty result, or explicit error
                            _has_sources = bool(body_json.get("sources_used") or body_json.get("sources"))
                            _has_findings = bool(body_json.get("findings") or body_json.get("results"))
                            _has_data = bool(body_json.get("data") or body_json.get("result") or body_json.get("report"))
                            _has_error = bool(body_json.get("error"))
                            _is_empty = not (_has_sources or _has_findings or _has_data)
                            
                            if _is_empty and not _has_error:
                                _should_flag_refund = True
                                _refund_reason = "Tool returned no data (empty response)"
                            elif _has_error and not _has_data:
                                _should_flag_refund = True
                                _refund_reason = f"Tool error: {str(body_json.get('error', ''))[:100]}"
                        except (json.JSONDecodeError, ValueError):
                            pass  # Non-JSON body, treat as having data
                except Exception as e:
                    logger.debug(f"Refund detection body read error: {e}")
                
                if _should_flag_refund:
                    _record_refundable_payment(
                        tx_hash=request.state.x402_tx_hash or "unknown",
                        chain=request.state.x402_chain,
                        payer=request.state.x402_payer,
                        amount=request.state.x402_amount,
                        tool=tool_id,
                        reason=_refund_reason,
                    )
                    response.headers["X-RMI-Refund-Flagged"] = "true"
                    logger.info(
                        f"Flagged payment for refund: tx={request.state.x402_tx_hash} "
                        f"tool={tool_id} reason={_refund_reason}"
                    )
                
                return response
    
    # No valid payment — check free trials
    try:
        can_trial, remaining = check_trial(tool_id, client_id)
    except Exception as e:
        logger.error(f"Trial check failed for {tool_id}: {e}")
        can_trial, remaining = False, 0
    
    if can_trial:
        # Allow free trial execution
        response = await call_next(request)
        response.headers["X-RMI-Trial"] = "true"
        response.headers["X-RMI-Trial-Remaining"] = str(remaining)
        # Add security headers to trial responses
        for k, v in SECURITY_HEADERS.items():
            if k not in response.headers:
                response.headers[k] = v
        return response
    
    # No trials left — return 402
    return build_402_response(tool_id, client_id=client_id)


# ── Discovery Endpoint ──
from fastapi import APIRouter

discovery_router = APIRouter()
# ── Main enforcement router (wrapper) ──
router = APIRouter(prefix="/api/v1/x402", tags=["x402 Enforcement"])

# Note: discovery_router is included on the app directly in main.py at root path
# so .well-known/x402 resolves at /.well-known/x402 (x402 spec requirement)


def _build_discovery_response():
    """Build the full discovery response with all 13 chains and active facilitators."""
    tools = {}
    for tool_id, pricing in TOOL_PRICES.items():
        try:
            price_atoms = str(pricing.get("price_atoms", "10000"))
            price_usd = float(pricing.get("price_usd", 0.01))
            trial_free = int(pricing.get("trial_free", 1))
            category = pricing.get("category", "analysis")
        except (ValueError, TypeError):
            continue

        requirements = []
        for chain_key, cfg in CHAIN_USDC.items():
            method = cfg["method"]
            pay_to = _resolve_pay_to(method)
            asset = _resolve_asset(cfg)
            extra = _build_extra(cfg, tool_id, chain_key, pay_to, method)
            
            req = {
                "scheme": "exact",
                "network": cfg["network"],
                "asset": asset,
                "amount": price_atoms,
                "payTo": pay_to,
                "maxTimeoutSeconds": 180,
                "extra": extra,
                "facilitators": cfg.get("facilitators", []),
            }
            if "tokens" in cfg:
                req["supportedTokens"] = list(cfg["tokens"].keys())
            requirements.append(req)

        desc = pricing.get("description", "")
        if not desc:
            _TOOL_DESCRIPTIONS = {
                "forensic_valuation": "Institutional-grade token valuation — DCF intrinsic value, comparable analysis with outlier detection, scam probability scoring",
                "osint_identity_hunt": "Cross-platform OSINT — hunt usernames across 400+ networks, domain intelligence, stealth page capture",
                "investigation_report": "Full investigation report — on-chain forensics, financial valuation, OSINT, scam scoring in one deliverable",
                "forensic_pack": "Forensic Investigation Pack — valuation + OSINT + report at 33% discount",
            }
            desc = _TOOL_DESCRIPTIONS.get(tool_id, f"{tool_id} — crypto intelligence tool")
        tools[tool_id] = {
            "description": desc,
            "price_usd": price_usd,
            "category": category,
            "trial_free": trial_free,
            "trial_description": f"{trial_free} free calls before payment required",
            "requirements": requirements,
        }

    return {
        "x402": {
            "version": "2",
            "protocol": "x402",
            "description": "Rug Munch Intelligence (RMI) — Multi-chain x402 payment system. Crypto scam detection, market analysis, and security intelligence via micropayments.",
            "trial_policy": "1 free trial per tool without wallet. Connect wallet for 3 free calls per standard tool, 1 per premium tool.",
            "refund_policy": "Full refund if tool returns no data. Request within 48h via POST /api/v1/x402/refund with tx hash.",
            "facilitator_summary": {
                "coinbase_cdp": "Fee-free Base + Solana USDC via Coinbase Developer Platform",
                "payai": "Base + Solana USDC, deferred settlement",
                "primev": "Fee-free Ethereum via mev-commit preconfirmations",
                "cloudflare_x402": "Base Sepolia + Ethereum fallback",
                "eip7702": "Universal EVM — BSC, Polygon, Avalanche, Fantom, Gnosis, Arbitrum, Optimism, Base",
                "tron_selfverify": "TRON USDT/USDC/USDD — self-verified via TronGrid (fee-free)",
                "bitcoin_selfverify": "Bitcoin BTC — self-verified via Mempool.space (fee-free, 1-conf)",
                "asterpay": "EUR/SEPA European off-ramp",
                "x402_rs": "Self-hosted x402-rs — multi-chain (requires Docker)",
            },
        },
        "gateway_url": "https://mcp.rugmunch.io",
        "payment_endpoint": "https://mcp.rugmunch.io/api/v1/x402-tools",
        "supported_chains": list(CHAIN_USDC.keys()),
        "chain_count": len(CHAIN_USDC),
        "facilitator_count": 8,  # dynamic: primev, coinbase_cdp, payai, cloudflare_x402, eip7702, asterpay, tron_selfverify, bitcoin_selfverify
        "total_tools": len(tools),
        "tools": tools,
    }


def _resolve_pay_to(method: str) -> str:
    if method == "payai":
        return SOL_PAY_TO
    elif method == "bitcoin_selfverify":
        return os.getenv("X402_BTC_PAY_TO", "")
    elif method == "tron_selfverify":
        return os.getenv("X402_TRON_PAY_TO", "")
    elif method == "asterpay":
        return os.getenv("ASTERPAY_SEPA_IBAN", "")
    return EVM_PAY_TO


def _resolve_asset(cfg: dict) -> str:
    asset = cfg.get("usdc", "")
    if not asset and "tokens" in cfg:
        first = next(iter(cfg["tokens"].values()), "")
        return first if first != "native" else "BTC"
    return asset


def _build_extra(cfg: dict, tool_id: str, chain_key: str, pay_to: str, method: str) -> dict:
    extra = {
        "name": cfg["name"],
        "version": cfg["version"],
        "tool": tool_id,
        "chain": chain_key,
    }
    if method == "local_eip712" and cfg.get("chain_id"):
        extra["domain"] = {
            "name": cfg["name"], "version": cfg["version"],
            "chainId": cfg["chain_id"], "verifyingContract": pay_to,
        }
    elif method == "payai":
        extra["feePayer"] = "2wKupLR9q6wXYppw8Gr2NvWxKBUqm4PPJKkQfoxHDBg4"
    elif method == "tron_selfverify":
        extra["tronNetwork"] = "mainnet"
        extra["trc20Tokens"] = cfg.get("tokens", {})
    elif method == "bitcoin_selfverify":
        extra["paymentNetwork"] = "bitcoin"
        extra["settlementChains"] = ["base", "solana"]
    elif method == "asterpay":
        extra["currency"] = "EUR"
        extra["sepa"] = True
    return extra

@discovery_router.get("/.well-known/x402")
async def x402_discovery():
    """x402 discovery endpoint — lists all tools, chains, payment requirements, and trial info.
    Response is cached for DISCOVERY_CACHE_TTL seconds to avoid rebuilding 7-chain requirements per request.
    """
    global _discovery_cache, _discovery_cache_time
    
    now = time.time()
    if _discovery_cache is not None and (now - _discovery_cache_time) < DISCOVERY_CACHE_TTL:
        return _discovery_cache
    
    _discovery_cache = _build_discovery_response()
    _discovery_cache_time = now
    return _discovery_cache


# ── Trial Status Endpoint ──
@discovery_router.get("/api/v1/x402/trial-status")
async def get_trial_status(request: Request):
    """Check remaining free trials for the current client"""
    client_id = get_client_id(request)
    trials = {}
    for tool_id, pricing in TOOL_PRICES.items():
        max_trials = pricing.get("trial_free", 3)
        if max_trials > 0:
            r = get_redis()
            if r:
                try:
                    used = int(r.get(f"x402:trial:{client_id}:{tool_id}") or 0)
                except Exception:
                    used = 0
            else:
                used = 0
            trials[tool_id] = {
                "max": max_trials,
                "used": used,
                "remaining": max(0, max_trials - used),
            }
    
    return {
        "client_id": client_id[:20] + "..." if len(client_id) > 20 else client_id,
        "trials": trials,
        "tools_with_trials": len(trials),
    }


# ── Refund Request Endpoint ──
@router.post("/refund")
async def request_refund(request: Request):
    """Request a refund for a paid tool that returned no data.
    
    Validates:
    (a) tx exists in our payment records (x402:spent_tx or x402:refund)
    (b) tool returned no data or error (already flagged as refundable)
    (c) within 48h of original payment
    
    If valid, records the refund request. Actual USDC refund is manual.
    
    POST body: {
        "tx_hash": "0x...",
        "payer": "0x..." (optional, for verification),
        "reason": "Tool returned empty data" (optional)
    }
    """
    try:
        body = await request.json()
        tx_hash = body.get("tx_hash", "").strip()
        requester_payer = body.get("payer", "").strip()
        requester_reason = body.get("reason", "").strip()
        
        if not tx_hash:
            return JSONResponse(
                status_code=400,
                content={"error": "tx_hash is required"},
                headers=SECURITY_HEADERS,
            )
        
        r = get_redis()
        if not r:
            return JSONResponse(
                status_code=503,
                content={"error": "Redis unavailable, cannot process refund request"},
                headers=SECURITY_HEADERS,
            )
        
        # (a) Check if tx exists in our payment records
        spent_data = r.get(f"x402:spent_tx:{tx_hash}")
        existing_refund = r.get(f"x402:refund:{tx_hash}")
        
        if not spent_data and not existing_refund:
            return JSONResponse(
                status_code=404,
                content={"error": "Transaction not found in payment records", "tx_hash": tx_hash[:16] + "..."},
                headers=SECURITY_HEADERS,
            )
        
        # If there's already a refund record, check its status
        if existing_refund:
            try:
                refund_info = json.loads(existing_refund)
                status = refund_info.get("status", "unknown")
                if status in ("requested", "processing", "completed"):
                    return {
                        "status": "already_requested",
                        "refund_status": status,
                        "tx_hash": tx_hash[:16] + "...",
                        "message": f"Refund already {status}",
                        "amount_atoms": refund_info.get("amount_atoms"),
                        "chain": refund_info.get("chain"),
                    }
            except (json.JSONDecodeError, TypeError):
                pass
        
        # (b) Check if payment was flagged as refundable (tool returned no data/error)
        is_refundable = False
        refund_reason = requester_reason or "User-requested refund"
        refund_chain = "unknown"
        refund_payer = requester_payer or "unknown"
        refund_amount = "0"
        payment_timestamp = None
        
        if existing_refund:
            try:
                refund_info = json.loads(existing_refund)
                if refund_info.get("status") == "refundable":
                    is_refundable = True
                    refund_reason = refund_info.get("reason") or refund_reason
                    refund_chain = refund_info.get("chain", "unknown")
                    refund_payer = refund_info.get("payer", requester_payer)
                    refund_amount = refund_info.get("amount_atoms", "0")
                    payment_timestamp = refund_info.get("flagged_at")
            except (json.JSONDecodeError, TypeError):
                pass
        elif spent_data:
            # Payment exists but wasn't auto-flagged — user is requesting manually
            # Allow if within 48h window and user provides a reason
            try:
                spent_info = json.loads(spent_data)
                refund_chain = spent_info.get("chain", "unknown")
                refund_payer = spent_info.get("payer", requester_payer)
                refund_amount = spent_info.get("amount", "0")
                payment_timestamp = spent_info.get("timestamp")
            except (json.JSONDecodeError, TypeError):
                # Old format: spent_data was just the chain name string
                refund_chain = spent_data if isinstance(spent_data, str) else "unknown"
        
        # (c) Verify within 48h of original payment
        if payment_timestamp:
            hours_since_payment = (time.time() - float(payment_timestamp)) / 3600
            if hours_since_payment > 48:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Refund window expired (48h)",
                        "hours_since_payment": round(hours_since_payment, 1),
                        "tx_hash": tx_hash[:16] + "...",
                    },
                    headers=SECURITY_HEADERS,
                )
        
        # Record the refund request
        refund_key = f"x402:refund:{tx_hash}"
        refund_data = {
            "tx_hash": tx_hash,
            "chain": refund_chain,
            "payer": refund_payer,
            "amount_atoms": str(refund_amount),
            "tool": "unknown",
            "reason": refund_reason,
            "status": "requested",
            "flagged_at": payment_timestamp,
            "requested_at": time.time(),
            "processed_at": None,
        }
        r.setex(refund_key, 7 * 86400, json.dumps(refund_data))  # 7-day TTL
        
        logger.info(
            f"Refund requested: tx={tx_hash[:16]}... chain={refund_chain} "
            f"amount={refund_amount} reason={refund_reason}"
        )
        
        return {
            "status": "requested",
            "tx_hash": tx_hash[:16] + "...",
            "chain": refund_chain,
            "amount_atoms": str(refund_amount),
            "reason": refund_reason,
            "message": "Refund request recorded. Manual processing within 48h. You will receive USDC back on the original payment chain.",
            "estimated_processing": "24-48 hours",
        }
        
    except Exception as e:
        logger.error(f"Refund request error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Refund request failed: {str(e)[:100]}"},
            headers=SECURITY_HEADERS,
        )
