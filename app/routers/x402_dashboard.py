"""
RMI x402 Analytics Dashboard Endpoint
=======================================
GET /api/v1/x402/dashboard — Public analytics endpoint returning:
  - Total earnings, earnings by chain, earnings by tool, earnings by day
  - Trial usage counts (today, all-time, unique fingerprints, unique wallets)
  - Top tools by revenue, top tools by usage
  - Paid from Redis x402:spent_tx:*, x402:trial:*, x402:global:trials_today, etc.
  - Persisted via Supabase x402_payments table

Author: RMI Development
Date: 2026-05-20
"""
import os
import json
import time
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("x402_dashboard")

router = APIRouter(prefix="/api/v1/x402", tags=["x402 Analytics Dashboard"])

# ── Redis helper (reuse existing pattern from enforcement) ─────────────

def _get_redis():
    """Synchronous Redis client for dashboard queries."""
    try:
        import redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            db=0,
            decode_responses=True,
        )
        r.ping()
        return r
    except Exception as e:
        logger.warning(f"Dashboard: Redis unavailable: {e}")
        return None


async def _get_redis_async():
    """Async Redis client for dashboard queries."""
    try:
        from app.auth import get_redis
        r = await get_redis()
        return r
    except Exception:
        return _get_redis()


# ── Supabase payment persistence ────────────────────────────────────

async def _persist_payment_to_supabase(tool: str, amount_atoms: str, chain: str,
                                         payer: str, tx_hash: str, status: str = "fulfilled"):
    """Insert a payment record into Supabase x402_payments table."""
    try:
        from app.services.supabase_service import _post
        await _post("x402_payments", {
            "tool": tool,
            "amount_atoms": str(amount_atoms),
            "chain": chain,
            "payer": payer or "unknown",
            "tx_hash": tx_hash or "",
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Persisted x402 payment to Supabase: tool={tool} chain={chain} tx={tx_hash[:16] if tx_hash else 'N/A'}")
    except Exception as e:
        logger.warning(f"Supabase payment persist failed: {e}")


async def _sync_spent_tx_to_supabase():
    """Sync Redis x402:spent_tx:* entries to Supabase (run periodically).
    
    Reads all x402:spent_tx:* keys from Redis and upserts them into x402_payments.
    Uses tx_hash as dedup key to avoid duplicates.
    """
    r = _get_redis()
    if not r:
        return 0
    
    synced = 0
    try:
        from app.services.supabase_service import _get, _post
        # Get existing tx_hashes from Supabase to avoid duplicates
        existing = await _get("x402_payments", select="tx_hash", limit=10000)
        existing_txs = {row["tx_hash"] for row in existing if row.get("tx_hash")}
        
        # Scan Redis for spent_tx entries
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match="x402:spent_tx:*", count=200)
            for key in keys:
                tx_hash = key.replace("x402:spent_tx:", "")
                if tx_hash in existing_txs:
                    continue
                try:
                    data = json.loads(r.get(key))
                    tool = "unknown"  # Not stored in spent_tx, derive later
                    amount_atoms = data.get("amount", "0")
                    chain = data.get("chain", "unknown")
                    payer = data.get("payer", "unknown")
                    await _post("x402_payments", {
                        "tool": tool,
                        "amount_atoms": str(amount_atoms),
                        "chain": chain,
                        "payer": payer,
                        "tx_hash": tx_hash,
                        "status": "fulfilled",
                        "created_at": datetime.fromtimestamp(
                            data.get("timestamp", time.time()), tz=timezone.utc
                        ).isoformat() if data.get("timestamp") else datetime.now(timezone.utc).isoformat(),
                    })
                    existing_txs.add(tx_hash)
                    synced += 1
                except Exception as e:
                    logger.debug(f"Sync failed for {key}: {e}")
            if cursor == 0:
                break
        if synced:
            logger.info(f"Synced {synced} x402 payments from Redis to Supabase")
    except Exception as e:
        logger.warning(f"Redis->Supabase sync error: {e}")
    return synced


# ── Dashboard data aggregation from Redis ────────────────────────────

def _aggregate_payment_stats(r) -> Dict[str, Any]:
    """Aggregate payment/earnings data from Redis x402:spent_tx:* keys."""
    total_earnings_atoms = 0
    earnings_by_chain: Dict[str, int] = defaultdict(int)
    earnings_by_tool: Dict[str, int] = defaultdict(int)
    unique_payers = set()
    all_payments = []  # For daily breakdown
    
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor, match="x402:spent_tx:*", count=500)
        for key in keys:
            try:
                data = json.loads(r.get(key))
                amount = int(data.get("amount", "0") or "0")
                chain = data.get("chain", "unknown")
                payer = data.get("payer", "unknown")
                timestamp = data.get("timestamp", 0)
                
                total_earnings_atoms += amount
                earnings_by_chain[chain] += amount
                # Tool info not in spent_tx; we track usage separately
                if payer and payer != "unknown":
                    unique_payers.add(payer)
                
                all_payments.append({
                    "amount": amount,
                    "chain": chain,
                    "payer": payer,
                    "timestamp": timestamp,
                })
            except Exception:
                continue
        if cursor == 0:
            break
    
    # Also check x402-tool:* keys (from record_x402_payment in x402_tools.py)
    cursor = 0
    tool_usage: Dict[str, int] = defaultdict(int)
    tool_revenue: Dict[str, int] = defaultdict(int)
    while True:
        cursor, keys = r.scan(cursor, match="x402-tool:*", count=500)
        for key in keys:
            try:
                data = json.loads(r.get(key))
                tool = data.get("tool", "unknown")
                amount_str = data.get("amount", "0")
                # Amount might be in USD format (e.g., "0.05") or atoms
                try:
                    amt = float(amount_str)
                    # Convert USD to atoms if < 1 (heuristic: USD prices are < 1)
                    if amt < 1:
                        amt_atoms = int(amt * 1e6)
                    else:
                        amt_atoms = int(amt)
                except (ValueError, TypeError):
                    amt_atoms = 0
                
                tool_usage[tool] += 1
                tool_revenue[tool] += amt_atoms
                total_earnings_atoms += amt_atoms
                
                customer = data.get("customer", "")
                if customer:
                    unique_payers.add(customer)
                chain = data.get("chain", "unknown")
                # x402-tool entries may not have chain info
                if chain != "unknown":
                    earnings_by_chain[chain] += amt_atoms
            except Exception:
                continue
        if cursor == 0:
            break
    
    # Also check x402:receipt:* keys (from x402_middleware.py)
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor, match="x402:receipt:*", count=500)
        for key in keys:
            try:
                data = json.loads(r.get(key))
                tool = data.get("tool", "unknown")
                amount_str = str(data.get("amount", "0"))
                chain = data.get("network", data.get("chain", "unknown"))
                customer = data.get("customer_address", data.get("customer", ""))
                
                try:
                    amt = float(amount_str)
                    if amt < 1:
                        amt_atoms = int(amt * 1e6)
                    else:
                        amt_atoms = int(amt)
                except (ValueError, TypeError):
                    amt_atoms = 0
                
                tool_usage[tool] += 1
                total_earnings_atoms += amt_atoms
                tool_revenue[tool] += amt_atoms
                if chain:
                    earnings_by_chain[chain] += amt_atoms
                if customer:
                    unique_payers.add(customer)
            except Exception:
                continue
        if cursor == 0:
            break
    
    # Earnings by day (from all_payments timestamps)
    now = time.time()
    earnings_by_day: Dict[str, int] = defaultdict(int)
    for p in all_payments:
        if p.get("timestamp"):
            try:
                day = datetime.fromtimestamp(p["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")
                earnings_by_day[day] += p.get("amount", 0)
            except Exception:
                pass
    
    # Today's earnings
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_earnings = earnings_by_day.get(today_str, 0)
    
    # Convert atoms to USDC (6 decimals)
    total_earnings_usdc = total_earnings_atoms / 1e6
    today_earnings_usdc = today_earnings / 1e6
    
    earnings_by_chain_usdc = {k: v / 1e6 for k, v in earnings_by_chain.items()}
    earnings_by_day_usdc = {k: v / 1e6 for k, v in sorted(earnings_by_day.items())[-30:]}  # Last 30 days
    tool_revenue_usdc = {k: v / 1e6 for k, v in tool_revenue.items()}
    
    # Top tools by revenue
    top_tools_revenue = sorted(tool_revenue_usdc.items(), key=lambda x: -x[1])[:10]
    # Top tools by usage count
    top_tools_usage = sorted(tool_usage.items(), key=lambda x: -x[1])[:10]
    
    return {
        "total_earnings_usdc": round(total_earnings_usdc, 6),
        "today_earnings_usdc": round(today_earnings_usdc, 6),
        "earnings_by_chain": earnings_by_chain_usdc,
        "earnings_by_day": earnings_by_day_usdc,
        "unique_payers": len(unique_payers),
        "top_tools_by_revenue": [{"tool": t, "revenue_usdc": round(r, 6)} for t, r in top_tools_revenue],
        "top_tools_by_usage": [{"tool": t, "calls": c} for t, c in top_tools_usage],
    }


def _aggregate_trial_stats(r) -> Dict[str, Any]:
    """Aggregate trial usage stats from Redis x402:trial:* keys."""
    total_trials_all_time = 0
    unique_fingerprints = set()
    unique_wallets = set()
    trials_by_tool: Dict[str, int] = defaultdict(int)
    
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor, match="x402:trial:*", count=500)
        for key in keys:
            # Key format: x402:trial:{client_id}:{tool_id}
            try:
                parts = key.replace("x402:trial:", "").split(":", 1)
                client_id = parts[0] if parts else "unknown"
                tool_id = parts[1] if len(parts) > 1 else "unknown"
                
                val = int(r.get(key) or 0)
                total_trials_all_time += val
                trials_by_tool[tool_id] += val
                
                # Categorize identity
                if client_id.startswith("w:"):
                    unique_wallets.add(client_id)
                elif client_id.startswith("dev:") or client_id.startswith("ts:"):
                    unique_fingerprints.add(client_id)
                else:
                    unique_fingerprints.add(client_id)
            except Exception:
                continue
        if cursor == 0:
            break
    
    # Today's trials
    trials_today = 0
    try:
        trials_today = int(r.get("x402:global:trials_today") or 0)
    except Exception:
        pass
    
    # IP daily stats
    cursor = 0
    ip_daily_total = 0
    while True:
        cursor, keys = r.scan(cursor, match="x402:ip_daily:*", count=500)
        for key in keys:
            try:
                ip_daily_total += int(r.get(key) or 0)
            except Exception:
                pass
        if cursor == 0:
            break
    
    return {
        "trials_today": trials_today,
        "trials_all_time": total_trials_all_time,
        "unique_fingerprint_ids": len(unique_fingerprints),
        "unique_wallet_ids": len(unique_wallets),
        "trials_by_tool": dict(sorted(trials_by_tool.items(), key=lambda x: -x[1])[:20]),
        "ip_daily_free_calls": ip_daily_total,
    }


# ── Dashboard endpoint ──────────────────────────────────────────────

@router.get("/dashboard")
async def x402_dashboard():
    """
    Public analytics dashboard for x402 payment and trial stats.
    
    Returns:
    - Total earnings (USDC), today's earnings
    - Earnings breakdown by chain, tool, day
    - Trial stats: today, all-time, unique fingerprints/wallets
    - Top tools by revenue and usage count
    - System health metadata
    """
    try:
        r = _get_redis()
        
        if r:
            payment_stats = _aggregate_payment_stats(r)
            trial_stats = _aggregate_trial_stats(r)
        else:
            payment_stats = {
                "total_earnings_usdc": 0,
                "today_earnings_usdc": 0,
                "earnings_by_chain": {},
                "earnings_by_day": {},
                "unique_payers": 0,
                "top_tools_by_revenue": [],
                "top_tools_by_usage": [],
            }
            trial_stats = {
                "trials_today": 0,
                "trials_all_time": 0,
                "unique_fingerprint_ids": 0,
                "unique_wallet_ids": 0,
                "trials_by_tool": {},
                "ip_daily_free_calls": 0,
            }
        
        # Try to get Supabase data for enrichment
        supabase_count = 0
        supabase_total = 0.0
        supabase_summary = {}
        try:
            from app.services.supabase_service import get_x402_earnings_summary, _get
            rows = await _get("x402_payments", select="id,amount_atoms,chain,tool,status", limit=5000)
            supabase_count = len(rows)
            for row in rows:
                try:
                    supabase_total += int(row.get("amount_atoms", "0") or "0") / 1e6
                except (ValueError, TypeError):
                    pass
            # Get full Supabase earnings summary
            supabase_summary = await get_x402_earnings_summary()
        except Exception as e:
            logger.debug(f"Supabase dashboard enrichment failed: {e}")
        
        # Trigger background sync (non-blocking)
        try:
            asyncio.create_task(_sync_spent_tx_to_supabase())
        except Exception:
            pass
        
        return {
            "earnings": payment_stats,
            "trials": trial_stats,
            "supabase": {
                "persisted_count": supabase_count,
                "total_usdc": round(supabase_total, 6),
                "earnings_summary": supabase_summary,
            },
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "redis_available": r is not None,
                "chains_supported": ["base", "solana", "ethereum", "bsc", "arbitrum", "optimism", "polygon"],
            },
        }
    
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)[:200]}")


# ── Supabase table creation helper ──────────────────────────────────

async def ensure_x402_payments_table():
    """Ensure x402_payments table exists in Supabase.
    
    Delegates to supabase_service.ensure_x402_payments_table()
    which uses the working exec_sql RPC function.
    """
    try:
        from app.services.supabase_service import ensure_x402_payments_table as _ensure
        result = await _ensure()
        if result:
            logger.info("x402_payments table ensured in Supabase")
        else:
            logger.warning("x402_payments table creation may have failed")
        return result
    except ImportError:
        # Fallback: direct call via REST
        try:
            from app.services.supabase_service import SUPABASE_URL, SUPABASE_SERVICE_KEY
            sql = """
            DO $$ BEGIN
                CREATE TABLE IF NOT EXISTS x402_payments (
                    id BIGSERIAL PRIMARY KEY,
                    tool TEXT NOT NULL DEFAULT 'unknown',
                    amount_atoms TEXT NOT NULL DEFAULT '0',
                    chain TEXT NOT NULL DEFAULT 'unknown',
                    payer TEXT NOT NULL DEFAULT 'unknown',
                    tx_hash TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status TEXT NOT NULL DEFAULT 'fulfilled'
                );
            END $$;
            CREATE INDEX IF NOT EXISTS idx_x402_payments_tool ON x402_payments(tool);
            CREATE INDEX IF NOT EXISTS idx_x402_payments_chain ON x402_payments(chain);
            CREATE INDEX IF NOT EXISTS idx_x402_payments_tx_hash ON x402_payments(tx_hash);
            CREATE INDEX IF NOT EXISTS idx_x402_payments_created_at ON x402_payments(created_at);
            CREATE INDEX IF NOT EXISTS idx_x402_payments_payer ON x402_payments(payer);
            """
            import httpx
            headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                    json={"query": sql},
                    headers=headers,
                )
                logger.info(f"x402_payments table creation via exec_sql: {r.status_code}")
                return r.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Could not ensure x402_payments table (fallback): {e}")
            return False
    except Exception as e:
        logger.warning(f"Could not ensure x402_payments table: {e}")
        return False


# ── Register on app startup ─────────────────────────────────────────

async def on_startup():
    """Call this on app startup to ensure the table exists."""
    await ensure_x402_payments_table()