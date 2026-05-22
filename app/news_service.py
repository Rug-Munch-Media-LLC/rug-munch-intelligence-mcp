"""
RMI News Aggregation Service — Multi-Source Crypto Intelligence
=================================================================
Aggregates crypto news from 15+ sources for the website news page.

Sources:
  RSS — CoinTelegraph, CoinDesk, Decrypt, The Block, The Defiant, Bankless, DL News
  API  — CoinGecko, CryptoPanic, CoinMarketCal
  Social — Reddit (r/CryptoCurrency, r/CryptoMarkets, r/ethdev)
  Internal — Ghost blog, RMI Intel
  X/Twitter — Via n8n pipeline (ingests to RAG)

Environment:
  COINGECKO_API_KEY — For CoinGecko news API
  CRYPTOPANIC_API_KEY — For CryptoPanic API
  GHOST_CONTENT_API_KEY — For Ghost CMS
"""

import os
import asyncio
import hashlib
import logging
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "").strip()
GHOST_URL = os.getenv("GHOST_URL", "http://172.19.0.3:2368")
GHOST_CONTENT_KEY = os.getenv("GHOST_CONTENT_API_KEY", "")

# ─── RSS FEED CONFIG ──────────────────────────────────────────────

RSS_FEEDS = [
    ("https://cointelegraph.com/rss", "CoinTelegraph"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://decrypt.co/feed", "Decrypt"),
    ("https://blockworks.co/feed", "Blockworks"),
    ("https://thedefiant.io/feed", "The Defiant"),
    ("https://bitcoinmagazine.com/feed", "Bitcoin Magazine"),
    ("https://coingeek.com/feed/", "CoinGeek"),
    ("https://blog.chainalysis.com/feed/", "Chainalysis"),
    ("https://blog.bitmex.com/feed/", "BitMEX Research"),
]

# ─── REDDIT CONFIG ────────────────────────────────────────────────

REDDIT_SUBREDDITS = [
    "CryptoCurrency",
    "CryptoMarkets",
    "ethdev",
    "CryptoTechnology",
    "defi",
]

REDDIT_USER_AGENT = "RMI-News-Aggregator/2.0"


class NewsService:
    """Multi-source crypto news aggregator for the RMI website."""

    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_fetch: Optional[datetime] = None
        self.seen_hashes: set = set()

    # ─── RSS FETCHERS ─────────────────────────────────────────────

    async def _fetch_rss(self, url: str, source_name: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Fetch and parse an RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers={"User-Agent": REDDIT_USER_AGENT})
                if resp.status_code != 200:
                    return []

            feed = feedparser.parse(resp.text)
            articles = []

            for entry in feed.entries[:limit]:
                try:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    desc = entry.get("summary", "") or entry.get("description", "") or title

                    # Parse date
                    pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub_parsed:
                        published = datetime(*pub_parsed[:6]).isoformat()
                    else:
                        published = datetime.utcnow().isoformat()

                    # Skip old articles (>48h)
                    if pub_parsed:
                        pub_dt = datetime(*pub_parsed[:6])
                        if datetime.utcnow() - pub_dt > timedelta(hours=48):
                            continue

                    content_hash = hashlib.md5(f"rss:{title}:{link}".encode()).hexdigest()
                    if content_hash in self.seen_hashes:
                        continue
                    self.seen_hashes.add(content_hash)

                    articles.append({
                        "id": f"rss-{content_hash[:12]}",
                        "title": title,
                        "url": link,
                        "description": desc[:300],
                        "source": source_name,
                        "published_at": published,
                        "category": self._categorize(title + " " + desc),
                        "sentiment": self._analyze_sentiment(title + " " + desc),
                        "kind": "external",
                    })

                except Exception:
                    continue

            logger.info(f"RSS {source_name}: {len(articles)} articles")
            return articles

        except Exception as e:
            logger.warning(f"RSS {source_name} failed: {e}")
            return []

    async def _fetch_all_rss(self, limit_per_source: int = 8) -> List[Dict[str, Any]]:
        """Fetch from all RSS feeds in parallel."""
        tasks = [self._fetch_rss(url, name, limit_per_source) for url, name in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
        return all_articles

    # ─── REDDIT FETCHER ───────────────────────────────────────────

    async def _fetch_reddit_hot(self, subreddit: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch hot posts from a Reddit subreddit (no auth needed for .json)."""
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    params={"limit": limit, "raw_json": "1"},
                    headers={"User-Agent": REDDIT_USER_AGENT},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()

            posts = data.get("data", {}).get("children", [])
            articles = []

            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                permalink = post_data.get("permalink", "")
                url = f"https://reddit.com{permalink}" if permalink else post_data.get("url", "")
                text = post_data.get("selftext", "")[:300]
                created = datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat()
                score = post_data.get("score", 0)
                num_comments = post_data.get("num_comments", 0)

                content_hash = hashlib.md5(f"reddit:{title}:{permalink}".encode()).hexdigest()
                if content_hash in self.seen_hashes:
                    continue
                self.seen_hashes.add(content_hash)

                # Only include posts with decent engagement
                if score < 10:
                    continue

                articles.append({
                    "id": f"reddit-{content_hash[:12]}",
                    "title": f"r/{subreddit}: {title}",
                    "url": url,
                    "description": text[:250],
                    "source": f"Reddit r/{subreddit}",
                    "published_at": created,
                    "category": self._categorize_reddit(subreddit, title + " " + text),
                    "sentiment": self._analyze_sentiment(title + " " + text),
                    "kind": "external",
                    "reddit_score": score,
                    "reddit_comments": num_comments,
                })

            logger.info(f"Reddit r/{subreddit}: {len(articles)} posts")
            return articles

        except Exception as e:
            logger.warning(f"Reddit r/{subreddit} failed: {e}")
            return []

    async def _fetch_all_reddit(self) -> List[Dict[str, Any]]:
        """Fetch from all Reddit subreddits in parallel."""
        tasks = [self._fetch_reddit_hot(sub, 10) for sub in REDDIT_SUBREDDITS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_posts = []
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)
        return all_posts

    # ─── API FETCHERS ─────────────────────────────────────────────

    async def _fetch_coingecko(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch from CoinGecko news API."""
        if not COINGECKO_API_KEY:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/news",
                    headers={"x-cg-demo-api-key": COINGECKO_API_KEY},
                    params={"per_page": limit},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()

            articles = []
            for item in data.get("data", []):
                title = item.get("title", "")
                url = item.get("url", "")
                desc = item.get("description", "") or title
                pub_str = item.get("updated_at", item.get("created_at", ""))

                content_hash = hashlib.md5(f"cg:{title}:{url}".encode()).hexdigest()
                if content_hash in self.seen_hashes:
                    continue
                self.seen_hashes.add(content_hash)

                try:
                    published = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).isoformat()
                except:
                    published = datetime.utcnow().isoformat()

                articles.append({
                    "id": f"cg-{content_hash[:12]}",
                    "title": title,
                    "url": url,
                    "description": desc[:300],
                    "source": "CoinGecko",
                    "published_at": published,
                    "category": self._categorize(title + " " + desc),
                    "sentiment": self._analyze_sentiment(title + " " + desc),
                    "kind": "external",
                })

            logger.info(f"CoinGecko: {len(articles)} articles")
            return articles

        except Exception as e:
            logger.warning(f"CoinGecko fetch failed: {e}")
            return []

    async def _fetch_cryptopanic(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch from CryptoPanic API."""
        try:
            params = {"public": "true", "kind": "news", "limit": min(limit, 20)}
            if CRYPTOPANIC_API_KEY:
                params["auth_token"] = CRYPTOPANIC_API_KEY
                url = "https://cryptopanic.com/api/v1/posts/"
            else:
                url = "https://cryptopanic.com/api/free/v1/posts/"

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return []
                data = resp.json()

            articles = []
            for item in data.get("results", []):
                title = item.get("title", "")
                url = item.get("url", "")
                source_title = item.get("source", {}).get("title", "CryptoPanic") if isinstance(item.get("source"), dict) else "CryptoPanic"
                pub_str = item.get("published_at", item.get("created_at", ""))

                content_hash = hashlib.md5(f"cp:{title}:{url}".encode()).hexdigest()
                if content_hash in self.seen_hashes:
                    continue
                self.seen_hashes.add(content_hash)

                try:
                    published = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).isoformat()
                except:
                    published = datetime.utcnow().isoformat()

                # Use votes for sentiment
                votes = item.get("votes", {})
                bull = votes.get("positive", 0) if isinstance(votes, dict) else 0
                bear = votes.get("negative", 0) if isinstance(votes, dict) else 0
                sentiment = "bullish" if bull > bear else "bearish" if bear > bull else "neutral"

                articles.append({
                    "id": f"cp-{content_hash[:12]}",
                    "title": title,
                    "url": url,
                    "source": source_title,
                    "published_at": published,
                    "category": self._categorize(title),
                    "sentiment": sentiment,
                    "kind": "external",
                })

            logger.info(f"CryptoPanic: {len(articles)} articles")
            return articles

        except Exception as e:
            logger.warning(f"CryptoPanic failed: {e}")
            return []

    # ─── GHOST BLOG ────────────────────────────────────────────────

    async def _fetch_ghost(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch from our Ghost blog."""
        if not GHOST_CONTENT_KEY:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{GHOST_URL}/ghost/api/content/posts/",
                    params={
                        "key": GHOST_CONTENT_KEY,
                        "limit": limit,
                        "fields": "title,url,published_at,excerpt,slug",
                        "order": "published_at DESC",
                    },
                )
                data = resp.json()
                posts = data.get("posts", [])
                return [
                    {
                        "id": f"ghost-{p.get('id', '')}",
                        "title": p.get("title"),
                        "url": f"/ghost/{p.get('slug', '')}/",
                        "source": "RMI Blog",
                        "published_at": p.get("published_at"),
                        "excerpt": (p.get("excerpt", "") or "")[:200],
                        "category": "analysis",
                        "kind": "internal",
                    }
                    for p in posts
                ]
        except Exception as e:
            logger.warning(f"Ghost fetch failed: {e}")
            return []

    # ─── INTELLIGENCE LAYER ────────────────────────────────────────

    def _categorize(self, text: str) -> str:
        """Categorize content based on keyword matching."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["hack", "exploit", "rug", "scam", "phish", "drain", "stolen", "vulnerability", "breach"]):
            return "security"
        if any(w in text_lower for w in ["sec", "regulation", "etf", "lawsuit", "court", "compliance", "sanction"]):
            return "regulation"
        if any(w in text_lower for w in ["defi", "yield", "staking", "lending", "protocol", "amm", "dex"]):
            return "defi"
        if any(w in text_lower for w in ["nft", "collection", "mint", "opensea", "blur"]):
            return "nft"
        if any(w in text_lower for w in ["meme", "doge", "shib", "pepe", "bonk", "wif"]):
            return "memes"
        if any(w in text_lower for w in ["whale", "accumulat", "dump", "sell", "buy", "inflow"]):
            return "whales"
        if any(w in text_lower for w in ["fed", "inflation", "interest rate", "cpi", "recession", "gdp", "economy"]):
            return "macro"
        return "market"

    def _categorize_reddit(self, subreddit: str, text: str) -> str:
        """Reddit-specific categorization."""
        if subreddit == "ethdev":
            return "technology"
        if subreddit == "CryptoTechnology":
            return "technology"
        return self._categorize(text)

    def _analyze_sentiment(self, text: str) -> str:
        """Simple keyword-based sentiment analysis."""
        bullish_words = ["surge", "rally", "pump", "bull", "ath", "breakout", "gain", "rise", "soar",
                         "moon", "growth", "adopt", "partnership", "launch", "green", "up"]
        bearish_words = ["crash", "dump", "bear", "plunge", "drop", "fall", "decline", "hack",
                         "exploit", "scam", "rug", "ban", "lawsuit", "red", "down", "sell", "fear"]

        text_lower = text.lower()
        bull_count = sum(1 for w in bullish_words if w in text_lower)
        bear_count = sum(1 for w in bearish_words if w in text_lower)

        if bull_count > bear_count:
            return "slightly_bullish" if bull_count < 3 else "bullish"
        elif bear_count > bull_count:
            return "slightly_bearish" if bear_count < 3 else "bearish"
        return "neutral"

    # ─── MAIN AGGREGATION ──────────────────────────────────────────

    async def get_all_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Aggregate all news sources. Called by API endpoint."""
        # Check cache
        if self.last_fetch and (datetime.utcnow() - self.last_fetch).seconds < self.cache_ttl:
            if "all" in self.cache:
                return self.cache["all"][:limit]

        logger.info("Starting full news aggregation cycle...")

        # Clear seen hashes periodically to allow re-fetch
        if len(self.seen_hashes) > 10000:
            self.seen_hashes.clear()

        # Fetch all sources in parallel
        rss, reddit, coingecko, cryptopanic, ghost = await asyncio.gather(
            self._fetch_all_rss(limit_per_source=6),
            self._fetch_all_reddit(),
            self._fetch_coingecko(limit=20),
            self._fetch_cryptopanic(limit=20),
            self._fetch_ghost(limit=10),
        )

        # RMI Intel items (manual/hardcoded for now)
        rmi_intel = [
            {
                "id": "rmi-1",
                "title": "SOSANA V2.0 Token Migration: Active Threat Detected",
                "url": "/autopsy",
                "source": "RMI Intel",
                "published_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "category": "security",
                "kind": "internal",
                "highlight": True,
            },
            {
                "id": "rmi-2",
                "title": "BONK Whale Accumulation Signals on Solana",
                "url": "/whale-watch",
                "source": "RMI Intel",
                "published_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                "category": "whales",
                "kind": "internal",
            },
        ]

        all_news = rss + reddit + coingecko + cryptopanic + ghost + rmi_intel

        # Sort by date (newest first)
        def sort_key(item):
            try:
                return datetime.fromisoformat(item.get("published_at", "").replace("Z", "+00:00"))
            except:
                return datetime(2000, 1, 1)

        all_news.sort(key=sort_key, reverse=True)

        # Cache
        self.cache["all"] = all_news
        self.last_fetch = datetime.utcnow()

        logger.info(f"Aggregated {len(all_news)} total articles from all sources")
        return all_news[:limit]

    async def get_top_headlines(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get top N headlines for front page."""
        news = await self.get_all_news(limit=50)
        # Prioritize security and internal intel
        security = [n for n in news if n.get("category") == "security" or n.get("highlight")]
        others = [n for n in news if n not in security]
        return (security + others)[:count]


# Singleton
news_service = NewsService()
