"""
News Router — THE Crypto News Aggregator Feed
=============================================
200+ sources. Real data only. No fake articles.

Endpoints:
  GET /api/v1/news/feed       — Full aggregated feed with filters
  GET /api/v1/news/sources    — Active sources list with counts
  GET /api/v1/news/sentiment  — Real-time sentiment overview
  GET /api/v1/news/headlines  — Top headlines only
  GET /api/v1/news/stats      — Source/category statistics
  POST /api/v1/news/comment   — Comment on article (social)
  GET /api/v1/news/comments/:article_id — Get comments for article
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx
import hashlib
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/news", tags=["news"])

# ─── Models ───────────────────────────────────────────────────────
class NewsArticle(BaseModel):
    id: Optional[str] = None
    title: str = ""
    url: str = ""
    description: Optional[str] = None
    source: str = ""
    published_at: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    kind: Optional[str] = None
    tier: Optional[str] = None
    reddit_score: Optional[int] = None
    reddit_comments: Optional[int] = None
    risk_score: Optional[float] = None
    token_address: Optional[str] = None
    chain: Optional[str] = None
    comment_count: Optional[int] = 0

class NewsFeedResponse(BaseModel):
    status: str = "success"
    articles: List[NewsArticle] = []
    total: int = 0
    sources: List[str] = []
    source_count: int = 0
    sentiment_summary: Dict[str, int] = {}
    tiers: List[str] = []
    cached: bool = False
    fetched_at: str = ""

class CommentRequest(BaseModel):
    article_id: str
    author: str = "anon"
    content: str
    parent_id: Optional[str] = None

class CommentResponse(BaseModel):
    id: str
    article_id: str
    author: str
    content: str
    created_at: str
    parent_id: Optional[str] = None
    likes: int = 0

# ─── In-memory cache ──────────────────────────────────────────────
_NEWS_CACHE = []
_CACHE_TS: Optional[datetime] = None
_CACHE_TTL = timedelta(minutes=3)

# In-memory comments store (ephemeral — persists via Redis later)
_COMMENTS: Dict[str, List[Dict]] = {}

# ─── Helpers ──────────────────────────────────────────────────────

def _make_comment_id(article_id: str, content: str) -> str:
    h = hashlib.md5(f"{article_id}:{content}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()
    return f"comment-{h[:12]}"

async def _refresh_cache(include_rss: bool, include_reddit: bool, include_internal: bool):
    """Background cache refresh task."""
    global _NEWS_CACHE, _CACHE_TS
    try:
        from app.news_service import get_news_service
        svc = get_news_service()
        result = await svc.fetch_all(
            limit=200,
            include_rss=include_rss,
            include_reddit=include_reddit,
            include_internal=include_internal,
        )
        _NEWS_CACHE = result
        _CACHE_TS = datetime.now(timezone.utc)
        logger.info(f"News cache refreshed: {result.get('total', 0)} articles from {result.get('source_count', 0)} sources")
    except Exception as e:
        logger.warning(f"Background news refresh failed: {e}")


# ─── Main Feed ────────────────────────────────────────────────────

@router.get("/feed", response_model=NewsFeedResponse)
async def get_news_feed(
    limit: int = Query(50, ge=1, le=200),
    sentiment: Optional[str] = Query(None, description="bullish, bearish, neutral, slightly_bullish, slightly_bearish"),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tier: Optional[str] = Query(None, description="news, social, market, rmi, api"),
    kind: Optional[str] = Query(None, description="external, internal, social, api"),
    include_rss: bool = Query(True),
    include_reddit: bool = Query(True),
    include_internal: bool = Query(True),
    refresh: bool = Query(False, description="Force refresh, bypass cache"),
):
    """Full aggregated news feed from all sources."""
    global _NEWS_CACHE, _CACHE_TS

    # Return cache if fresh
    if not refresh and _NEWS_CACHE and _CACHE_TS and (datetime.now(timezone.utc) - _CACHE_TS) < _CACHE_TTL:
        result = _NEWS_CACHE
    else:
        # Serve stale cache immediately while refreshing in background
        if _NEWS_CACHE and not refresh:
            result = _NEWS_CACHE
            # Background refresh
            asyncio.create_task(_refresh_cache(include_rss, include_reddit, include_internal))
        else:
            # First load or forced refresh — fetch inline but with limits
            try:
                from app.news_service import get_news_service
                svc = get_news_service()
                result = await svc.fetch_all(
                    limit=200,
                    include_rss=include_rss,
                    include_reddit=include_reddit,
                    include_internal=include_internal,
                )
                _NEWS_CACHE = result
                _CACHE_TS = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"News fetch failed: {e}")
                if _NEWS_CACHE:
                    result = _NEWS_CACHE
                else:
                    raise HTTPException(status_code=500, detail=f"News aggregation failed: {str(e)}")

    articles = result.get("articles", [])

    # Apply filters
    if sentiment:
        articles = [a for a in articles if a.get("sentiment", "").lower() == sentiment.lower()]
    if source:
        articles = [a for a in articles if source.lower() in a.get("source", "").lower()]
    if category:
        articles = [a for a in articles if a.get("category", "").lower() == category.lower()]
    if tier:
        articles = [a for a in articles if a.get("tier", "").lower() == tier.lower()]
    if kind:
        articles = [a for a in articles if a.get("kind", "").lower() == kind.lower()]

    articles = articles[:limit]

    # Enrich with comment counts
    for a in articles:
        aid = a.get("id", "")
        a["comment_count"] = len(_COMMENTS.get(aid, []))

    return NewsFeedResponse(
        status="success",
        articles=[NewsArticle(**a) for a in articles],
        total=len(articles),
        sources=result.get("sources", []),
        source_count=result.get("source_count", 0),
        sentiment_summary=result.get("sentiment_summary", {}),
        tiers=result.get("tiers", []),
        cached=bool(_NEWS_CACHE),
        fetched_at=(_CACHE_TS or datetime.now(timezone.utc)).isoformat(),
    )


# ─── Headlines ────────────────────────────────────────────────────

@router.get("/headlines")
async def get_headlines(
    count: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None),
):
    """Top headlines only — fast, lightweight."""
    feed = await get_news_feed(limit=count, category=category, include_reddit=False)
    return {
        "headlines": [
            {
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "published_at": a.published_at,
                "category": a.category,
                "sentiment": a.sentiment,
                "kind": a.kind,
            }
            for a in feed.articles[:count]
        ],
        "count": len(feed.articles[:count]),
    }


# ─── Sources ──────────────────────────────────────────────────────

@router.get("/sources")
async def get_news_sources():
    """Get all active news sources."""
    feed = await get_news_feed(limit=200, refresh=False)
    sources = {}
    for a in feed.articles:
        src = a.source
        sources[src] = sources.get(src, 0) + 1

    return {
        "sources": [
            {"name": name, "article_count": count, "tier": a.tier if hasattr(a, 'tier') else "unknown"}
            for name, count in sorted(sources.items(), key=lambda x: -x[1])
            for a in [next((art for art in feed.articles if art.source == name), None)]
        ],
        "total_sources": len(sources),
    }


# ─── Sentiment ────────────────────────────────────────────────────

@router.get("/sentiment")
async def get_sentiment():
    """Real-time sentiment overview from current news feed."""
    feed = await get_news_feed(limit=200, refresh=False)
    return {
        "sentiment": feed.sentiment_summary,
        "sample_size": feed.total,
        "fetched_at": feed.fetched_at,
        "trending": [
            a.title for a in feed.articles[:5]
            if a.sentiment in ("bullish", "bearish")
        ],
    }


# ─── Categories ───────────────────────────────────────────────────

@router.get("/categories")
async def get_categories():
    """Get all news categories with counts."""
    feed = await get_news_feed(limit=200, refresh=False)
    cats = {}
    for a in feed.articles:
        cat = a.category or "general"
        cats[cat] = cats.get(cat, 0) + 1
    return {
        "categories": [{"name": n, "count": c} for n, c in sorted(cats.items(), key=lambda x: -x[1])],
    }


# ─── Stats ────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Aggregate statistics about the news pipeline."""
    feed = await get_news_feed(limit=200, refresh=False)
    source_counts = {}
    tier_counts = {}
    for a in feed.articles:
        src = a.source or "unknown"
        source_counts[src] = source_counts.get(src, 0) + 1
        t = a.tier or "unknown"
        tier_counts[t] = tier_counts.get(t, 0) + 1

    return {
        "total_articles": feed.total,
        "total_sources": feed.source_count,
        "sentiment": feed.sentiment_summary,
        "source_breakdown": dict(sorted(source_counts.items(), key=lambda x: -x[1])[:20]),
        "tier_breakdown": tier_counts,
        "fetched_at": feed.fetched_at,
    }


# ─── Comments / Social ────────────────────────────────────────────

@router.post("/comment", response_model=CommentResponse)
async def post_comment(req: CommentRequest):
    """Post a comment on any news article."""
    if not req.article_id or not req.content.strip():
        raise HTTPException(status_code=400, detail="article_id and content required")

    comment = {
        "id": _make_comment_id(req.article_id, req.content),
        "article_id": req.article_id,
        "author": req.author[:50] or "anon",
        "content": req.content[:2000],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parent_id": req.parent_id,
        "likes": 0,
    }

    if req.article_id not in _COMMENTS:
        _COMMENTS[req.article_id] = []
    _COMMENTS[req.article_id].append(comment)

    return CommentResponse(**comment)


@router.get("/comments/{article_id}", response_model=List[CommentResponse])
async def get_comments(article_id: str):
    """Get comments for a specific article."""
    comments = _COMMENTS.get(article_id, [])
    return [CommentResponse(**c) for c in sorted(comments, key=lambda x: x["created_at"])]


# ─── Internal: for cron jobs to post scanner findings as news ─────

@router.post("/internal/scanner-alert")
async def post_scanner_alert(token_name: str, chain: str, risk_score: float,
                              address: str, flags: str = ""):
    """Internal endpoint for cron jobs to inject scanner findings into news feed."""
    global _NEWS_CACHE
    content_hash = hashlib.md5(f"internal:{address}:{chain}".encode()).hexdigest()
    article = {
        "id": f"rmi-{content_hash[:12]}",
        "title": f"RMI Scanner: {token_name} ({chain.upper()}) — Risk {risk_score}/100",
        "url": f"https://rugmunch.io/scanner?address={address}&chain={chain}",
        "description": f"Scanner detected {token_name} on {chain}. Risk: {risk_score}/100. Flags: {flags}. Address: {address}",
        "source": "RMI Scanner",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "category": "security",
        "sentiment": "bearish" if risk_score > 50 else "neutral",
        "kind": "internal",
        "tier": "rmi",
        "risk_score": risk_score,
        "token_address": address,
        "chain": chain,
    }
    # Prepend to cache
    if _NEWS_CACHE:
        _NEWS_CACHE["articles"] = [article] + _NEWS_CACHE.get("articles", [])
        _NEWS_CACHE["total"] = len(_NEWS_CACHE["articles"])
    return {"status": "injected", "id": article["id"]}
