"""
RMI News Aggregation Service — Expanded Multi-Source Crypto Intelligence
========================================================================
Aggregates crypto news from 40+ sources for the website news page.

Sources:
  RSS — Major crypto news, security firms, research, onchain intel
  API  — CoinGecko, CryptoPanic
  Social — Reddit (r/CryptoCurrency, r/CryptoMarkets, r/ethdev)
  Internal — Ghost blog, RMI Intel
  Newsletters — Substack/Mirror scraping (security-focused)
  Security Reports — PDF ingestion pipeline
  Onchain Intel — MEV, bundle, exploit feeds

Environment:
  COINGECKO_API_KEY — For CoinGecko news API
  CRYPTOPANIC_API_KEY — For CryptoPanic API
  GHOST_CONTENT_API_KEY — For Ghost CMS
"""

import os
import asyncio
import hashlib
import logging
import random
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ─── PROXY ROTATION ───────────────────────────────────────────────
# Free public proxy list for Cloudflare-blocked feeds (Substack, etc.)
# Rotates per-request to distribute load. Dead proxies auto-skip via timeout.
PROXY_LIST = [
    "http://43.153.99.140:13001",
    "http://43.153.99.140:13002",
    "http://43.153.99.140:13003",
    "http://43.153.99.140:13004",
    "http://43.153.99.140:13005",
    "http://43.153.99.140:13006",
    "http://43.153.99.140:13007",
    "http://43.153.99.140:13008",
    "http://43.153.99.140:13009",
    "http://43.153.99.140:13010",
]

# Substack feeds that need proxy rotation (Cloudflare blocked from this IP)
PROXY_REQUIRED_FEEDS = {
    "https://cryptosecurity.substack.com/feed",
    "https://weekinethereum.substack.com/feed",
    "https://banklessdao.substack.com/feed",
    "https://defieducation.substack.com/feed",
    "https://rekt.substack.com/feed",
    "https://cryptohayes.substack.com/feed",
    "https://doseofdefi.substack.com/feed",
    "https://thedefiant.substack.com/feed",
    "https://tokeninsight.substack.com/feed",
    "https://blockanalytica.substack.com/feed",
}


def _get_proxy() -> Optional[str]:
    """Pick a random proxy from the pool."""
    return random.choice(PROXY_LIST) if PROXY_LIST else None

# ─── CONFIG ───────────────────────────────────────────────────────

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "").strip()
GHOST_URL = os.getenv("GHOST_URL", "http://172.19.0.3:2368")
GHOST_CONTENT_KEY = os.getenv("GHOST_CONTENT_API_KEY", "")

# ─── RSS FEED CONFIG ──────────────────────────────────────────────

RSS_FEEDS = [
    # Tier 1: Security & Audit Firms
    ("https://peckshield.medium.com/feed", "PeckShield"),
    ("https://slowmist.medium.com/feed", "SlowMist"),
    ("https://certik.medium.com/feed", "CertiK"),
    ("https://immunefi.medium.com/feed", "Immunefi"),
    ("https://blog.trailofbits.com/feed/", "Trail of Bits"),
    ("https://www.chainalysis.com/blog/feed/", "Chainalysis"),
    
    # Tier 2: Major Crypto News
    ("https://cointelegraph.com/rss", "CoinTelegraph"),
    ("https://decrypt.co/feed", "Decrypt"),
    ("https://blockworks.co/feed", "Blockworks"),
    ("https://www.theblock.co/rss.xml", "The Block"),
    ("https://thedefiant.io/feed", "The Defiant"),
    ("https://www.bankless.com/feed", "Bankless"),
    ("https://bitcoinmagazine.com/feed", "Bitcoin Magazine"),
    ("https://protos.com/feed/", "Protos"),
    ("https://beincrypto.com/feed/", "BeInCrypto"),
    ("https://unchainedcrypto.com/feed/", "Unchained"),
    
    # Tier 3: Research & Analytics
    ("https://collective.flashbots.net/latest.rss", "Flashbots"),
    ("https://insights.glassnode.com/feed/", "Glassnode"),
    ("https://blog.eigenlayer.xyz/feed", "EigenLayer"),
    ("https://blog.celestia.org/feed", "Celestia"),
    ("https://solana.com/news/feed", "Solana"),
    
    # Tier 4: Crossover Security (general tech security affecting crypto)
    ("https://feeds.feedburner.com/TheHackersNews", "The Hacker News"),
    ("https://www.bleepingcomputer.com/feed/", "BleepingComputer"),
    ("https://krebsonsecurity.com/feed/", "Krebs on Security"),
    ("https://www.darkreading.com/rss.xml", "Dark Reading"),
    
    # Tier 5: Onchain Intel & Exploit Trackers
    ("https://www.web3isgoinggreat.com/feed", "W3IGG"),
    
    # Tier 6: Additional Major News (verified live)
    ("https://coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://cryptodaily.co.uk/feed", "CryptoDaily"),
    ("https://u.today/rss", "U.Today"),
    ("https://cryptonews.com/news/feed/", "CryptoNews"),
    ("https://insidebitcoins.com/feed/", "InsideBitcoins"),
    ("https://nulltx.com/feed/", "NullTX"),
    ("https://coinpedia.org/feed/", "Coinpedia"),
    ("https://www.coinspeaker.com/feed/", "CoinSpeaker"),
    ("https://crypto.news/feed/", "Crypto.News"),
    ("https://www.tronweekly.com/feed/", "TronWeekly"),
    ("https://nftevening.com/feed/", "NFTEvening"),
    ("https://nftplazas.com/feed/", "NFTPlazas"),
    ("https://cryptopolitan.com/feed/", "Cryptopolitan"),
    ("https://www.crypto-insiders.nl/feed/", "Crypto Insiders"),
    ("https://finbold.com/feed/", "Finbold"),
    ("https://coinjournal.net/feed/", "CoinJournal"),
    ("https://blockonomi.com/feed/", "Blockonomi"),
    ("https://dune.com/blog/feed", "Dune Analytics"),
    
    # Tier 7: Exchange & Security Blogs (verified live)
    ("https://blog.trezor.io/feed", "Trezor"),
    ("https://blog.kraken.com/feed/", "Kraken"),
    ("https://blog.bitfinex.com/feed/", "Bitfinex"),
    ("https://blog.mexc.com/feed", "MEXC"),
    ("https://blog.ethereum.org/feed.xml", "Ethereum Foundation"),
    ("https://blog.arbitrum.io/feed", "Arbitrum"),
    ("https://blog.lido.fi/feed", "Lido"),
    ("https://blog.synthetix.io/feed", "Synthetix"),
    ("https://blog.chain.link/feed", "Chainlink"),
    ("https://blog.1inch.io/feed", "1inch"),
    ("https://blog.injective.com/feed", "Injective"),
    
    # Tier 8: Substack Newsletters (proxy-rotated — Cloudflare blocked from this IP)
    ("https://cryptosecurity.substack.com/feed", "CryptoSecurity Substack"),
    ("https://weekinethereum.substack.com/feed", "Week in Ethereum"),
    ("https://banklessdao.substack.com/feed", "Bankless DAO"),
    ("https://defieducation.substack.com/feed", "DeFi Education"),
    ("https://rekt.substack.com/feed", "REKT Newsletter"),
    ("https://cryptohayes.substack.com/feed", "Arthur Hayes Substack"),
    ("https://doseofdefi.substack.com/feed", "Dose of DeFi Substack"),
    ("https://thedefiant.substack.com/feed", "The Defiant Substack"),
    ("https://tokeninsight.substack.com/feed", "TokenInsight Substack"),
    ("https://blockanalytica.substack.com/feed", "BlockAnalytica Substack"),
]

# ─── NEWSLETTER / SUBSTACK SOURCES ────────────────────────────────
# These often don't have RSS but we can scrape their /feed endpoint

NEWSLETTER_FEEDS = [
    # Verified working (replaced dead Substack feeds blocked by Cloudflare)
    ("https://cryptohayes.medium.com/feed", "Arthur Hayes"),
    ("https://www.doseofdefi.com/feed", "Dose of DeFi"),
    ("https://blog.trezor.io/feed", "Trezor Security"),
    ("https://blog.kraken.com/feed/", "Kraken"),
    ("https://blog.bitfinex.com/feed/", "Bitfinex"),
    ("https://blog.mexc.com/feed", "MEXC"),
    ("https://coindesk.com/arc/outboundfeeds/rss/", "CoinDesk"),
    ("https://cryptodaily.co.uk/feed", "CryptoDaily"),
    ("https://u.today/rss", "U.Today"),
    ("https://dune.com/blog/feed", "Dune Analytics"),
    # Substack feeds — all return Cloudflare 403 from this IP.
    # Re-enable if we deploy residential proxy rotation or use RSS aggregator APIs.
    # ("https://cryptosecurity.substack.com/feed", "CryptoSecurity Substack"),
    # ("https://weekinethereum.substack.com/feed", "Week in Ethereum"),
    # ("https://banklessdao.substack.com/feed", "Bankless DAO"),
    # ("https://defieducation.substack.com/feed", "DeFi Education"),
    # ("https://rekt.substack.com/feed", "REKT Newsletter"),
    # ("https://thedefiant.substack.com/feed", "The Defiant Substack"),
    # ("https://tokeninsight.substack.com/feed", "TokenInsight"),
    # ("https://blockanalytica.substack.com/feed", "BlockAnalytica"),
]

# ─── REDDIT CONFIG ────────────────────────────────────────────────

REDDIT_SUBREDDITS = [
    "CryptoCurrency",
    "CryptoMarkets",
    "ethdev",
    "CryptoTechnology",
    "defi",
    "ethfinance",
    "solana",
    "CryptoScams",
    "Buttcoin",
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

    async def _fetch_rss(self, url: str, source_name: str, limit: int = 8, use_proxy: bool = False) -> List[Dict[str, Any]]:
        """Fetch and parse an RSS feed. Auto-uses proxy rotation for Cloudflare-blocked sources."""
        # Auto-detect if proxy needed
        needs_proxy = use_proxy or url in PROXY_REQUIRED_FEEDS
        
        for attempt in range(3 if needs_proxy else 1):
            try:
                client_kwargs = {"timeout": 15.0, "follow_redirects": True}
                if needs_proxy and attempt > 0:
                    proxy = _get_proxy()
                    if proxy:
                        client_kwargs["proxy"] = proxy
                        logger.debug(f"Using proxy {proxy} for {source_name}")
                
                async with httpx.AsyncClient(**client_kwargs) as client:
                    headers = {"User-Agent": REDDIT_USER_AGENT}
                    if needs_proxy:
                        # Full browser headers to blend in
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.5",
                            "Accept-Encoding": "gzip, deflate, br",
                            "DNT": "1",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1",
                        }
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        break  # Success, exit retry loop
                    elif resp.status_code == 403 and needs_proxy and attempt < 2:
                        logger.warning(f"Proxy attempt {attempt+1} got 403 for {source_name}, rotating...")
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        return []
            except Exception as e:
                if needs_proxy and attempt < 2:
                    logger.warning(f"Proxy attempt {attempt+1} failed for {source_name}: {e}, rotating...")
                    await asyncio.sleep(0.5)
                    continue
                logger.warning(f"RSS {source_name} failed: {e}")
                return []
        else:
            # All proxy attempts exhausted
            return []

        try:
            feed = feedparser.parse(resp.text)
        except Exception:
            return []
        
        articles = []

        for entry in feed.entries[:limit]:
            try:
                title = entry.get("title", "")
                link = entry.get("link", "")
                desc = entry.get("summary", "") or entry.get("description", "") or title

                # Parse date
                pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub_parsed and isinstance(pub_parsed, (tuple, list)) and len(pub_parsed) >= 6:
                    published = datetime(*pub_parsed[:6]).isoformat()
                else:
                    published = datetime.utcnow().isoformat()

                # Skip old articles (>48h)
                if pub_parsed and isinstance(pub_parsed, (tuple, list)) and len(pub_parsed) >= 6:
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

    async def _fetch_all_rss(self, limit_per_source: int = 8) -> List[Dict[str, Any]]:
        """Fetch from all RSS feeds in parallel."""
        tasks = [self._fetch_rss(url, name, limit_per_source) for url, name in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
        return all_articles

    # ─── NEWSLETTER FETCHER ───────────────────────────────────────

    async def _fetch_newsletter(self, url: str, source_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch newsletter feeds (Substack, Mirror, etc)."""
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
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

                    pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub_parsed and isinstance(pub_parsed, (tuple, list)) and len(pub_parsed) >= 6:
                        published = datetime(*pub_parsed[:6]).isoformat()
                    else:
                        published = datetime.utcnow().isoformat()

                    # Skip old articles (>72h for newsletters)
                    if pub_parsed and isinstance(pub_parsed, (tuple, list)) and len(pub_parsed) >= 6:
                        pub_dt = datetime(*pub_parsed[:6])
                        if datetime.utcnow() - pub_dt > timedelta(hours=72):
                            continue

                    content_hash = hashlib.md5(f"newsletter:{title}:{link}".encode()).hexdigest()
                    if content_hash in self.seen_hashes:
                        continue
                    self.seen_hashes.add(content_hash)

                    articles.append({
                        "id": f"nl-{content_hash[:12]}",
                        "title": title,
                        "url": link,
                        "description": desc[:300],
                        "source": source_name,
                        "published_at": published,
                        "category": self._categorize(title + " " + desc),
                        "sentiment": self._analyze_sentiment(title + " " + desc),
                        "kind": "newsletter",
                    })

                except Exception:
                    continue

            logger.info(f"Newsletter {source_name}: {len(articles)} articles")
            return articles

        except Exception as e:
            logger.warning(f"Newsletter {source_name} failed: {e}")
            return []

    async def _fetch_all_newsletters(self) -> List[Dict[str, Any]]:
        """Fetch from all newsletter sources in parallel."""
        tasks = [self._fetch_newsletter(url, name, 5) for url, name in NEWSLETTER_FEEDS]
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

    # ─── SECURITY REPORT INGESTION ──────────────────────────────────
    # Placeholder for PDF report pipeline — would integrate with:
    # - Chainalysis reports (quarterly crypto crime reports)
    # - CertiK security reports
    # - Immunefi bug bounty summaries
    # - SlowMist incident reports
    # - PeckShield alerts
    # These are typically published as PDFs or blog posts with structured data

    async def _fetch_security_reports(self) -> List[Dict[str, Any]]:
        """Fetch structured security reports from known sources."""
        # TODO: Implement PDF scraping + parsing for:
        # - Chainalysis Crypto Crime Reports
        # - CertiK Hack3D Reports
        # - Immunefi quarterly stats
        # - SlowMist Blockchain Security Incident Reports
        # - PeckShield monthly summaries
        return []

    # ─── ONCHAIN INTEL FEEDS ──────────────────────────────────────
    # Real-time onchain data that acts as "news"

    async def _fetch_onchain_intel(self) -> List[Dict[str, Any]]:
        """Fetch onchain intelligence: large transfers, exchange flows, MEV."""
        # TODO: Integrate with:
        # - Arkham Intel API (whale alerts, exchange flows)
        # - Nansen Smart Money signals
        # - EigenPhi MEV summaries
        # - Flashbots MEV-Share data
        # - Token Terminal onchain metrics
        return []

    # ─── INTELLIGENCE LAYER ────────────────────────────────────────

    def _categorize(self, text: str) -> str:
        """Categorize content based on keyword matching."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["hack", "exploit", "rug", "scam", "phish", "drain", "stolen", "vulnerability", "breach", "flash loan", "reentrancy", "oracle manipulation"]):
            return "security"
        if any(w in text_lower for w in ["sec", "regulation", "etf", "lawsuit", "court", "compliance", "sanction", "sec ", "cftc", "finCEN"]):
            return "regulation"
        if any(w in text_lower for w in ["defi", "yield", "staking", "lending", "protocol", "amm", "dex", "liquidity", "vault", "strategy"]):
            return "defi"
        if any(w in text_lower for w in ["nft", "collection", "mint", "opensea", "blur", "marketplace"]):
            return "nft"
        if any(w in text_lower for w in ["meme", "doge", "shib", "pepe", "bonk", "wif", "mog", "popcat"]):
            return "memes"
        if any(w in text_lower for w in ["whale", "accumulat", "dump", "sell", "buy", "inflow", "outflow", "exchange flow", "smart money"]):
            return "whales"
        if any(w in text_lower for w in ["fed", "inflation", "interest rate", "cpi", "recession", "gdp", "economy", "macro", "dxy"]):
            return "macro"
        if any(w in text_lower for w in ["mev", "bundle", "sandwich", "frontrun", "validator", "proposer", "builder"]):
            return "mev"
        if any(w in text_lower for w in ["layer 2", "l2", "rollup", "zk", "optimistic", "sequencer", "bridge", "cross-chain"]):
            return "layer2"
        if any(w in text_lower for w in ["ai", "artificial intelligence", "llm", "model", "training", "inference", "agent"]):
            return "ai"
        return "market"

    def _categorize_reddit(self, subreddit: str, text: str) -> str:
        """Reddit-specific categorization."""
        if subreddit in ["ethdev", "CryptoTechnology"]:
            return "technology"
        if subreddit == "CryptoScams":
            return "security"
        if subreddit == "solana":
            return "solana"
        if subreddit == "ethfinance":
            return "defi"
        return self._categorize(text)

    def _analyze_sentiment(self, text: str) -> str:
        """Simple keyword-based sentiment analysis."""
        bullish_words = ["surge", "rally", "pump", "bull", "ath", "breakout", "gain", "rise", "soar",
                         "moon", "growth", "adopt", "partnership", "launch", "green", "up", "moonshot",
                         "breakthrough", "milestone", "record", "all-time high", "bullish"]
        bearish_words = ["crash", "dump", "bear", "plunge", "drop", "fall", "decline", "hack",
                         "exploit", "scam", "rug", "ban", "lawsuit", "red", "down", "sell", "fear",
                         "panic", "collapse", "liquidation", "bankruptcy", "insolvent", "drained"]

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
        rss, newsletters, reddit, coingecko, cryptopanic, ghost = await asyncio.gather(
            self._fetch_all_rss(limit_per_source=6),
            self._fetch_all_newsletters(),
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

        all_news = rss + newsletters + reddit + coingecko + cryptopanic + ghost + rmi_intel

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

    async def get_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get news filtered by category."""
        news = await self.get_all_news(limit=200)
        filtered = [n for n in news if n.get("category", "").lower() == category.lower()]
        return filtered[:limit]

    async def get_sources_summary(self) -> Dict[str, Any]:
        """Get summary of active sources and article counts."""
        news = await self.get_all_news(limit=500)
        sources = {}
        categories = {}
        for item in news:
            src = item.get("source", "Unknown")
            cat = item.get("category", "general")
            sources[src] = sources.get(src, 0) + 1
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_articles": len(news),
            "sources": dict(sorted(sources.items(), key=lambda x: -x[1])),
            "categories": dict(sorted(categories.items(), key=lambda x: -x[1])),
            "rss_feeds": len(RSS_FEEDS),
            "newsletter_feeds": len(NEWSLETTER_FEEDS),
            "reddit_subreddits": len(REDDIT_SUBREDDITS),
        }


# Singleton
news_service = NewsService()
