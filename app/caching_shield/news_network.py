"""
RMI News Network - World's Best Crypto News Aggregator

Architecture:
  RSS/API Sources → MCP News Pipeline → Sentiment Analysis → Categorization → Feed

Sources: 25+ trusted crypto news outlets, newsletters, blogs, and mirrors.
"""

import os, re, time, hashlib, json, asyncio, logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import feedparser
import httpx

logger = logging.getLogger("news_network")

# ═══════════════════════════════════════════════════════════════════════════
# 25+ NEWS SOURCES - Mainstream, independent, newsletters, blogs
# ═══════════════════════════════════════════════════════════════════════════

NEWS_SOURCES = [
    # Tier 1 - Major Crypto News
    {"name": "CoinDesk", "url": "https:#www.coindesk.com/arc/outboundfeeds/v2/all/", "tier": 1},
    {"name": "CoinTelegraph", "url": "https:#cointelegraph.com/rss", "tier": 1},
    {"name": "The Block", "url": "https:#www.theblock.co/rss/", "tier": 1},
    {"name": "Decrypt", "url": "https:#decrypt.co/feed", "tier": 1},
    {"name": "Blockworks", "url": "https:#blockworks.co/feed", "tier": 1},
    {"name": "DL News", "url": "https:#www.dlnews.com/feed", "tier": 1},
    
    # Tier 2 - Quality Independent
    {"name": "Bankless", "url": "https:#www.bankless.com/feed", "tier": 2},
    {"name": "The Defiant", "url": "https:#thedefiant.io/feed", "tier": 2},
    {"name": "CryptoSlate", "url": "https:#cryptoslate.com/feed/", "tier": 2},
    {"name": "BeInCrypto", "url": "https:#beincrypto.com/feed/", "tier": 2},
    {"name": "Crypto Briefing", "url": "https:#cryptobriefing.com/feed/", "tier": 2},
    {"name": "AMB Crypto", "url": "https:#ambcrypto.com/feed/", "tier": 2},
    {"name": "Bitcoin Magazine", "url": "https:#bitcoinmagazine.com/feed", "tier": 2},
    {"name": "NewsBTC", "url": "https:#www.newsbtc.com/feed/", "tier": 2},
    
    # Tier 3 - Niche & Technical
    {"name": "TrustNodes", "url": "https:#www.trustnodes.com/feed", "tier": 3},
    {"name": "CoinSpeaker", "url": "https:#www.coinspeaker.com/feed/", "tier": 3},
    {"name": "Altcoin Buzz", "url": "https:#www.altcoinbuzz.io/feed/", "tier": 3},
    {"name": "ZyCrypto", "url": "https:#zycrypto.com/feed/", "tier": 3},
    {"name": "CoinGape", "url": "https:#coingape.com/feed/", "tier": 3},
    {"name": "Watcher Guru", "url": "https:#watcher.guru/news/feed", "tier": 3},
    {"name": "Bitcoinist", "url": "https:#bitcoinist.com/feed/", "tier": 3},
    
    # Tier 4 - Security & DeFi Focused
    {"name": "Rekt News", "url": "https:#rekt.news/rss/", "tier": 4},
    {"name": "SlowMist", "url": "https:#slowmist.medium.com/feed", "tier": 4},
    {"name": "PeckShield", "url": "https:#peckshield.medium.com/feed", "tier": 4},
    {"name": "Chainalysis", "url": "https:#blog.chainalysis.com/feed/", "tier": 4},
    
    # Newsletters & Blogs
    {"name": "Milk Road", "url": "https:#www.milkroad.com/feed", "tier": 5},
    {"name": "CoinBureau", "url": "https:#www.coinbureau.com/feed/", "tier": 5},
    {"name": "Messari", "url": "https:#messari.io/feed", "tier": 5},
    {"name": "Electric Capital", "url": "https:#www.electriccapital.com/rss.xml", "tier": 5},
    {"name": "Dragonfly", "url": "https:#www.dragonfly.xyz/feed", "tier": 5},
]

# Extended category detection with 12 categories
CATEGORY_KEYWORDS = {
    "Bitcoin": ["bitcoin", "btc", "satoshi", "halving", "ordinals", "lightning network", "taproot"],
    "Ethereum": ["ethereum", "eth", "vitalik", "layer 2", "l2", "staking", "merge", "eip", "erc"],
    "Solana": ["solana", "sol", "phantom", "jupiter", "raydium", "pump.fun", "bonk"],
    "DeFi": ["defi", "yield", "liquidity pool", "amm", "swap", "lending", "borrowing", "tvl"],
    "Regulation": ["sec", "regulation", "lawsuit", "compliance", "cftc", "doj", "legal", "court", "ban"],
    "Security": ["hack", "exploit", "rug pull", "scam", "phishing", "vulnerability", "audit", "stolen"],
    "Markets": ["price", "market", "bull", "bear", "rally", "crash", "dump", "pump", "trading"],
    "NFTs": ["nft", "collectible", "mint", "opensea", "blur", "magic eden", "pudgy"],
    "AI": ["ai", "artificial intelligence", "machine learning", "agent", "llm", "gpt", "copilot"],
    "Memecoins": ["meme", "dogecoin", "shiba", "pepe", "bonk", "wojak", "cum"],
    "Adoption": ["adoption", "partnership", "enterprise", "institutional", "bank", "etf"],
    "Privacy": ["privacy", "zk", "zero knowledge", "mixer", "tornado", "monero", "zec"],
}


SENTIMENT_DICT = {
    "surge": 0.8, "soar": 0.9, "rally": 0.7, "breakout": 0.8, "pump": 0.6,
    "bullish": 0.9, "gain": 0.5, "profit": 0.6, "growth": 0.6, "adoption": 0.7,
    "partnership": 0.6, "launch": 0.5, "mainnet": 0.6, "upgrade": 0.5, "record": 0.7,
    "crash": -0.9, "dump": -0.7, "hack": -0.95, "exploit": -0.95, "scam": -0.9,
    "rug pull": -0.95, "bearish": -0.9, "loss": -0.6, "decline": -0.5,
    "lawsuit": -0.7, "ban": -0.8, "crackdown": -0.7, "liquidation": -0.8,
}


@dataclass
class Article:
    id: str
    title: str
    source: str
    source_tier: int
    url: str
    summary: str = ""
    image: str = ""
    published: str = ""
    categories: List[str] = field(default_factory=list)
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    impact_level: str = "low"
    reading_time: int = 1
    votes_up: int = 0
    votes_down: int = 0
    comments: List[dict] = field(default_factory=list)
    bookmarks: int = 0


_db: Dict[str, Article] = {}


async def fetch_all(max_per_source: int = 8) -> List[Article]:
    """Fetch from all 30 sources in parallel."""
    new_articles = []
    
    async def fetch_source(source):
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(source["url"], follow_redirects=True)
                if r.status_code == 200:
                    feed = feedparser.parse(r.text)
                    for entry in feed.entries[:max_per_source]:
                        aid = hashlib.md5((entry.link or entry.title).encode()).hexdigest()[:12]
                        if aid in _db:
                            continue
                        
                        summary = entry.get("summary", entry.get("description", ""))
                        summary = re.sub(r'<[^>]+>', '', summary)[:400]
                        title = entry.title or "Untitled"
                        
                        article = Article(
                            id=aid, title=title, source=source["name"],
                            source_tier=source["tier"], url=entry.link,
                            summary=summary,
                            image=entry.get("media_content", [{}])[0].get("url", ""),
                            published=entry.get("published", ""),
                        )
                        
                        # Classify
                        text = (title + " " + summary).lower()
                        for cat, keywords in CATEGORY_KEYWORDS.items():
                            if any(kw in text for kw in keywords):
                                article.categories.append(cat)
                        if not article.categories:
                            article.categories = ["General"]
                        
                        # Sentiment
                        score = 0.0
                        for word, weight in SENTIMENT_DICT.items():
                            if word in text:
                                score += weight
                        article.sentiment_score = round(score / max(abs(score), 1), 2) if score != 0 else 0
                        article.sentiment_label = "bullish" if article.sentiment_score > 0.15 else "bearish" if article.sentiment_score < -0.15 else "neutral"
                        
                        # Reading time
                        words = len(text.split())
                        article.reading_time = max(1, round(words / 200))
                        
                        # Impact level
                        article.impact_level = "high" if abs(article.sentiment_score) > 0.5 or any(kw in text for kw in ["hack", "exploit", "crash", "surge", "breakout"]) else "medium" if abs(article.sentiment_score) > 0.2 else "low"
                        
                        _db[aid] = article
                        new_articles.append(article)
        except Exception:
            pass

    await asyncio.gather(*[fetch_source(s) for s in NEWS_SOURCES])
    return new_articles


def get_feed(category: str = None, sentiment: str = None, tier: int = None,
             sort: str = "latest", limit: int = 50, offset: int = 0,
             impact: str = None, source: str = None) -> dict:
    """Get the news feed with all filters."""
    articles = list(_db.values())
    
    if category and category != "All":
        articles = [a for a in articles if category in a.categories]
    if sentiment:
        articles = [a for a in articles if a.sentiment_label == sentiment]
    if tier:
        articles = [a for a in articles if a.source_tier <= tier]
    if impact:
        articles = [a for a in articles if a.impact_level == impact]
    if source:
        articles = [a for a in articles if a.source == source]
    
    if sort == "popular":
        articles.sort(key=lambda a: a.votes_up - a.votes_down, reverse=True)
    elif sort == "bullish":
        articles.sort(key=lambda a: a.sentiment_score, reverse=True)
    elif sort == "bearish":
        articles.sort(key=lambda a: a.sentiment_score)
    elif sort == "impact":
        impact_order = {"high": 3, "medium": 2, "low": 1}
        articles.sort(key=lambda a: impact_order.get(a.impact_level, 0), reverse=True)
    else:
        articles.sort(key=lambda a: a.published, reverse=True)
    
    total = len(articles)
    page = articles[offset:offset + limit]
    
    return {
        "articles": [{
            "id": a.id, "title": a.title, "source": a.source, "source_tier": a.source_tier,
            "url": a.url, "summary": a.summary, "image": a.image, "published": a.published,
            "categories": a.categories, "sentiment_score": a.sentiment_score,
            "sentiment_label": a.sentiment_label, "impact_level": a.impact_level,
            "reading_time": a.reading_time, "votes_up": a.votes_up,
            "votes_down": a.votes_down, "comment_count": len(a.comments),
            "bookmarks": a.bookmarks,
        } for a in page],
        "total": total,
        "all_categories": sorted(set(c for a in articles for c in a.categories)),
        "all_sources": sorted(set(a.source for a in articles)),
        "stats": {
            "total_articles": len(_db),
            "sources_indexed": len(set(a.source for a in _db.values())),
            "sentiment": {
                "bullish": sum(1 for a in _db.values() if a.sentiment_label == "bullish"),
                "bearish": sum(1 for a in _db.values() if a.sentiment_label == "bearish"),
                "neutral": sum(1 for a in _db.values() if a.sentiment_label == "neutral"),
            },
            "high_impact": sum(1 for a in _db.values() if a.impact_level == "high"),
            "latest_update": datetime.now(timezone.utc).isoformat(),
        },
    }


def vote_article(article_id: str, direction: str) -> dict:
    a = _db.get(article_id)
    if not a:
        return {"error": "Not found"}
    if direction == "up": a.votes_up += 1
    elif direction == "down": a.votes_down += 1
    return {"id": article_id, "votes_up": a.votes_up, "votes_down": a.votes_down}


def add_comment(article_id: str, user: str, text: str) -> dict:
    a = _db.get(article_id)
    if not a:
        return {"error": "Not found"}
    comment = {
        "id": hashlib.md5(f"{article_id}{time.time()}".encode()).hexdigest()[:8],
        "user": user[:50], "text": text[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "votes": 0,
    }
    a.comments.append(comment)
    return comment


def get_comments(article_id: str) -> List[dict]:
    a = _db.get(article_id)
    return sorted(a.comments, key=lambda c: c.get("votes", 0), reverse=True) if a else []


def bookmark(article_id: str) -> dict:
    a = _db.get(article_id)
    if a:
        a.bookmarks += 1
        return {"id": article_id, "bookmarks": a.bookmarks}
    return {"error": "Not found"}


def get_categories() -> list:
    cats = set()
    for a in _db.values():
        for c in a.categories:
            cats.add(c)
    icons = {"Bitcoin": "₿", "Ethereum": "Ξ", "Solana": "◎", "DeFi": "🏦", "Regulation": "⚖️",
             "Security": "🛡️", "Markets": "📊", "NFTs": "🎨", "AI": "🤖",
             "Memecoins": "🐸", "Adoption": "🚀", "Privacy": "🔐", "General": "📰"}
    return [{"name": c, "icon": icons.get(c, "📌")} for c in sorted(cats)]


def search_articles(query: str, limit: int = 20) -> list:
    q = query.lower()
    results = []
    for a in _db.values():
        if q in a.title.lower() or q in a.summary.lower() or q in a.source.lower():
            results.append({"id": a.id, "title": a.title, "source": a.source, "url": a.url, "summary": a.summary[:200]})
    return results[:limit]
