"""
Aggressive Caching Shield — Multi-Layer API Protection for Free RPC Tiers

Protects free tier RPC API keys (Helius, QuickNode, Alchemy) from
exhaustion by frontend traffic. Enforces cache-first architecture:

  1. RpcCacheClient — Redis L2 + in-memory L1 cache with TTL tiers
  2. RpcRateLimiter — Token bucket rate limiting per provider
  3. RpcBatcher — JSON-RPC batch request grouper (reduces call count)
  4. HistoryDepthController — Caps default query depth, gates deep scans
  5. WsClientManager — Connection-pooled Redis pub/sub for live streams

All modules fall back gracefully if Redis is unavailable.

Usage:
    from app.caching_shield import (
        get_rpc_cache,
        get_rate_limiter,
        get_ws_manager,
        get_history_controller,
    )

    # Cache-first RPC query
    cache = get_rpc_cache()
    result = await cache.get_balance("SoL...")

    # Rate-limited via token bucket
    limiter = get_rate_limiter()
    allowed, wait = await limiter.acquire("helius", "getBalance")
    if not allowed:
        raise HTTPException(429, f"Rate limited, retry in {wait:.1f}s")

    # Broadcast to WebSocket stream
    ws = get_ws_manager()
    await ws.broadcast_scan({"token": "SoL...", "safety_score": 85})

    # Clamp query depth
    hdc = get_history_controller()
    limit = hdc.clamp_limit(100, is_deep_scan=True)
"""

from app.caching_shield.rpc_cache import (
    RpcCacheClient,
    CacheStats,
    get_rpc_cache,
    TTL_TABLE,
)

from app.caching_shield.rate_limiter import (
    RpcRateLimiter,
    ProviderLimit,
    PROVIDER_LIMITS,
    get_rate_limiter,
)

from app.caching_shield.batcher import (
    RpcBatcher,
    BatchRequest,
    BatchResult,
    MAX_BATCH_SIZE,
    BATCH_WINDOW_MS,
)

from app.caching_shield.history_depth import (
    HistoryDepthController,
    get_history_controller,
    DEFAULT_DEPTH,
    MAX_DEPTH,
    MAX_PAGINATED,
)

from app.caching_shield.ws_broadcaster import (
    WsClientManager,
    get_ws_manager,
    CHANNEL_SCANS,
    CHANNEL_ALERTS,
    CHANNEL_PRICES,
    CHANNEL_TOKENS,
)

from app.caching_shield.solana_tracker import (
    SolanaTrackerClient,
    get_solana_tracker,
)

from app.caching_shield.api_registry import (
    UnifiedApiManager,
    KeyPool,
    ApiKey,
    ProviderConfig,
    PROVIDER_REGISTRY,
    get_api_manager,
)

from app.caching_shield.funding_tracer import (
    FundingTrace,
    trace_funding_source,
)

from app.caching_shield.unified_layer import (
    UnifiedDataLayer,
    ToolResult,
    get_data_layer,
)

from app.caching_shield.tool_data import (
    ToolData,
    td,
)

__all__ = [
    "RpcCacheClient", "CacheStats", "get_rpc_cache", "TTL_TABLE",
    "RpcRateLimiter", "ProviderLimit", "PROVIDER_LIMITS", "get_rate_limiter",
    "RpcBatcher", "BatchRequest", "BatchResult", "MAX_BATCH_SIZE", "BATCH_WINDOW_MS",
    "HistoryDepthController", "get_history_controller", "DEFAULT_DEPTH", "MAX_DEPTH", "MAX_PAGINATED",
    "WsClientManager", "get_ws_manager", "CHANNEL_SCANS", "CHANNEL_ALERTS", "CHANNEL_PRICES", "CHANNEL_TOKENS",
    "SolanaTrackerClient", "get_solana_tracker",
]
