#!/usr/bin/env python3
"""
TIER-1 SCAM INGESTION — Automated Knowledge Base Builder
=========================================================
Pulls scam/exploit data from public sources and indexes them.

Sources:
  - REKT News DB (rekt.news) — largest crypto exploit database
  - Chainabuse — community-reported scams
  - GoPlus Security API — real-time token risk assessment
  - QuickIntel API — honeypot/rug detection
  - TokenSniffer — scam detection scores
  - Web3IsGoingGreat — incident timeline
  - SlowMist Hacked — investigation reports
  - CertiK Alerts — audit findings

Architecture:
  1. Periodically poll sources (configurable intervals)
  2. Extract structured data (name, description, contract, txns, losses)
  3. Embed using CryptoEmbedder
  4. Store in pgvector + Redis (dual-write)
  5. Trigger re-scan of related tokens/wallets
"""

import os
import json
import hashlib
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# SOURCE CONNECTORS
# ══════════════════════════════════════════════════════════════════════

class RektNewsConnector:
    """REKT News — largest crypto exploit database. https://rekt.news"""

    BASE = "https://rekt.news"

    @staticmethod
    async def fetch_recent(limit: int = 50) -> List[dict]:
        """Fetch recent exploit reports. REKT doesn't have a public API,
        but we can scrape their leaderboard and article pages."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # REKT leaderboard JSON endpoint
                resp = await client.get(
                    f"{RektNewsConnector.BASE}/leaderboard.json",
                    headers={"User-Agent": "RMI-Scam-Indexer/1.0"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for entry in data[:limit]:
                        results.append({
                            "source": "rekt.news",
                            "type": "exploit",
                            "name": entry.get("name", ""),
                            "amount_lost_usd": entry.get("amount", 0),
                            "date": entry.get("date", ""),
                            "chain": entry.get("chain", "ethereum"),
                            "description": entry.get("description", ""),
                            "category": entry.get("category", "exploit"),
                            "url": f"{RektNewsConnector.BASE}{entry.get('slug', '')}",
                        })
        except Exception as e:
            logger.warning(f"REKT fetch failed: {e}")
        return results


class GoPlusConnector:
    """GoPlus Security API — real-time token risk detection.
    Free tier: rate limited but no API key needed for basic checks."""

    BASE = "https://api.gopluslabs.io/api/v1"

    @staticmethod
    async def check_token(chain_id: str, address: str) -> dict:
        """Check a single token for security risks."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{GoPlusConnector.BASE}/token_security/{chain_id}",
                    params={"contract_addresses": address}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("result", {})
                    token_data = result.get(address.lower(), {})
                    return {
                        "source": "goplus",
                        "type": "token_scan",
                        "address": address,
                        "chain": chain_id,
                        "is_honeypot": token_data.get("is_honeypot") == "1",
                        "is_open_source": token_data.get("is_open_source") == "1",
                        "buy_tax": token_data.get("buy_tax", "0"),
                        "sell_tax": token_data.get("sell_tax", "0"),
                        "can_take_back_ownership": token_data.get("can_take_back_ownership") == "1",
                        "hidden_owner": token_data.get("hidden_owner") == "1",
                        "is_blacklisted": token_data.get("is_blacklisted") == "1",
                        "is_whitelisted": token_data.get("is_whitelisted") == "1",
                        "is_proxy": token_data.get("is_proxy") == "1",
                        "owner_address": token_data.get("owner_address", ""),
                        "risk_score": token_data.get("risk_score", 0),
                    }
        except Exception as e:
            logger.warning(f"GoPlus check failed for {address}: {e}")
        return {}


class ChainabuseConnector:
    """Chainabuse — community scam reports. https://chainabuse.com"""

    BASE = "https://api.chainabuse.com/v1"

    @staticmethod
    async def fetch_reports(limit: int = 50) -> List[dict]:
        """Fetch recent scam reports."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{ChainabuseConnector.BASE}/reports",
                    params={"limit": limit, "sort": "recent"},
                    headers={"User-Agent": "RMI-Scam-Indexer/1.0"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for report in data.get("reports", data.get("data", []))[:limit]:
                        results.append({
                            "source": "chainabuse",
                            "type": "scam_report",
                            "name": report.get("title", ""),
                            "description": report.get("description", ""),
                            "addresses": report.get("addresses", []),
                            "category": report.get("category", "scam"),
                            "date": report.get("created_at", ""),
                            "chain": report.get("chain", ""),
                            "url": report.get("url", ""),
                        })
        except Exception as e:
            logger.warning(f"Chainabuse fetch failed: {e}")
        return results


class Web3IsGoingGreatConnector:
    """Web3IsGoingGreat — incident tracker by Molly White."""

    BASE = "https://www.web3isgoinggreat.com"

    @staticmethod
    async def fetch_recent(limit: int = 30) -> List[dict]:
        """Fetch recent incidents."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Try the API endpoint
                resp = await client.get(
                    f"{Web3IsGoingGreatConnector.BASE}/api/entries.json",
                    headers={"User-Agent": "RMI-Scam-Indexer/1.0"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    entries = data.get("entries", data if isinstance(data, list) else [])
                    for entry in entries[:limit]:
                        results.append({
                            "source": "web3isgoinggreat",
                            "type": "incident",
                            "name": entry.get("title", ""),
                            "description": entry.get("description", entry.get("body", "")),
                            "date": entry.get("date", ""),
                            "category": entry.get("category", "incident"),
                            "url": entry.get("url", ""),
                        })
        except Exception as e:
            logger.warning(f"W3IGG fetch failed: {e}")
        return results


class SlowMistConnector:
    """SlowMist Hacked — investigation reports."""

    BASE = "https://hacked.slowmist.io"

    @staticmethod
    async def fetch_recent(limit: int = 30) -> List[dict]:
        """Fetch recent SlowMist hack reports."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # SlowMist publishes via their API
                resp = await client.get(
                    f"{SlowMistConnector.BASE}/api/reports",
                    params={"limit": limit},
                    headers={"User-Agent": "RMI-Scam-Indexer/1.0"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for report in data.get("reports", data.get("data", []))[:limit]:
                        results.append({
                            "source": "slowmist",
                            "type": "hack_report",
                            "name": report.get("title", ""),
                            "description": report.get("summary", ""),
                            "amount_lost_usd": report.get("amount", 0),
                            "date": report.get("date", ""),
                            "chain": report.get("chain", ""),
                            "url": report.get("url", ""),
                        })
        except Exception as e:
            logger.warning(f"SlowMist fetch failed: {e}")
        return results


# ══════════════════════════════════════════════════════════════════════
# KNOWN SCAM DATABASE — Manual curated patterns (expanded)
# ══════════════════════════════════════════════════════════════════════

KNOWN_SCAMS_EXPANDED = [
    # From crypto_embeddings.py KNOWN_SCAM_PATTERNS
    {
        "name": "Honeypot — Sell Disabled",
        "description": "Token where only the creator can sell. maxSellAmount=0, tradingEnabled=false, blacklist of non-owner addresses.",
        "indicators": ["maxSellAmount=0", "tradingEnabled=false", "onlyOwner transfer", "blacklist all"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["maxSellAmount = 0", "tradingEnabled = false"],
    },
    {
        "name": "Unlimited Mint / Rug Pull",
        "description": "Owner can mint unlimited tokens, diluting holders to zero before draining liquidity.",
        "indicators": ["unrestricted mint", "onlyOwner mint", "no supply cap"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["function mint(address to, uint256 amount) external onlyOwner"],
    },
    {
        "name": "Hidden Fee Manipulation",
        "description": "Owner sets fees to 99% post-launch, making sells impossible or stealing all transfers.",
        "indicators": ["setTax(99)", "dynamic fee > 50%", "no max fee cap"],
        "severity": "high",
        "source": "rmi-curated",
        "code_snippets": ["function setFee(uint256 _fee) external onlyOwner", "taxFee = 99"],
    },
    {
        "name": "Liquidity Drain Backdoor",
        "description": "Hidden function allowing owner to remove all liquidity via manualSwap or rescueToken.",
        "indicators": ["manualSwap", "removeLiquidity all", "drain", "rescueToken onlyOwner"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["function manualSwap() external onlyOwner", "uniswapV2Router.removeLiquidity"],
    },
    {
        "name": "Proxy Upgrade Trap",
        "description": "Upgradeable proxy where admin can swap implementation to malicious contract post-launch.",
        "indicators": ["upgradeTo", "upgradeToAndCall", "UUPS", "changeAdmin"],
        "severity": "high",
        "source": "rmi-curated",
        "code_snippets": ["function upgradeTo(address newImplementation) external onlyOwner"],
    },
    {
        "name": "Wallet Drainer / Approval Scam",
        "description": "Contract tricks users into unlimited approval, then drains via transferFrom.",
        "indicators": ["unlimited approval", "transferFrom", "approveAndCall", "permit exploit"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["IERC20(token).transferFrom(victim, attacker, balance)"],
    },
    # Additional patterns from real-world incidents
    {
        "name": "Flash Loan Attack",
        "description": "Exploiter uses flash loan to manipulate price oracle or governance, then extracts value.",
        "indicators": ["flashLoan", "getFlashLoan", "onFlashLoan", "price oracle manipulation"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["function flashLoan(", "function onFlashLoan("],
    },
    {
        "name": "Reentrancy Attack",
        "description": "Contract calls external contract before updating state, allowing recursive withdrawal.",
        "indicators": ["reentrancy", "call before state update", "no reentrancy guard", "checks-effects-interactions violated"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["msg.sender.call{value:", "nonReentrant", "ReentrancyGuard"],
    },
    {
        "name": "Unchecked Return Value",
        "description": "Contract ignores return value of external call, assuming success. Classic King of the Ether pattern.",
        "indicators": ["unchecked send", "call without require", ".send( without check"],
        "severity": "high",
        "source": "rmi-curated",
        "code_snippets": ["address(msg.sender).send(", "address(this).balance"],
    },
    {
        "name": "Access Control Missing",
        "description": "Critical functions lack access control (no onlyOwner/modifier), allowing anyone to drain/modify.",
        "indicators": ["no onlyOwner", "public init function", "unprotected withdraw", "no modifier"],
        "severity": "critical",
        "source": "rmi-curated",
        "code_snippets": ["function withdraw() public {", "function init("],
    },
    {
        "name": "MEV Sandwich Vulnerability",
        "description": "High-slippage token that sandwich bots exploit repeatedly. Creator often runs the bots.",
        "indicators": ["slippage > 10%", "sandwich pattern", "same wallet MEV + deployer", "high tax token"],
        "severity": "medium",
        "source": "rmi-curated",
        "code_snippets": [],
    },
    {
        "name": "Fake Token — Name Squatting",
        "description": "Token with identical name/symbol to legitimate project. Trick users into buying the wrong token.",
        "indicators": ["identical name to top-100", "different contract from official", "recently created", "no liquidity"],
        "severity": "medium",
        "source": "rmi-curated",
        "code_snippets": [],
    },
    {
        "name": "Anti-Bot Launch Scam",
        "description": "Claims 'anti-bot' but actually blocks ALL buys except creator addresses. Classic honeypot variant.",
        "indicators": ["antiBot", "isBot", "botDetection", "onlyAllowed", "_isExcluded"],
        "severity": "high",
        "source": "rmi-curated",
        "code_snippets": ["modifier antiBot(", "require(!isBot(msg.sender)"],
    },
    {
        "name": "Cloned Contract with Modified Tax",
        "description": "Copy of popular token contract with tax parameters changed to steal from unaware investors.",
        "indicators": ["identical bytecode except tax", "same name as verified", "different deployer", "tax > 20%"],
        "severity": "high",
        "source": "rmi-curated",
        "code_snippets": [],
    },
    {
        "name": "Fake Liquidity Lock",
        "description": "Claims liquidity locked but LP tokens held by creator wallet with no time-lock or fake lock contract.",
        "indicators": ["fake lock", "LP in EOA", "no unicrypt/teamfinance", "liquidity lock claim unverified"],
        "severity": "high",
        "source": "rmi-curated",
        "code_snippets": [],
    },
]


# ══════════════════════════════════════════════════════════════════════
# INGESTION ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════

class ScamIngestionPipeline:
    """
    Automated pipeline for building the scam knowledge base.

    Usage:
        pipeline = ScamIngestionPipeline()
        stats = await pipeline.run_full_ingestion()
    """

    def __init__(self):
        self._last_run: Optional[datetime] = None
        self._total_ingested = 0
        self.connectors = [
            ("curated", self._ingest_curated),
            ("rekt", self._ingest_rekt),
            ("chainabuse", self._ingest_chainabuse),
            ("web3igg", self._ingest_w3igg),
            ("slowmist", self._ingest_slowmist),
        ]

    async def run_full_ingestion(self, force: bool = False) -> Dict[str, Any]:
        """Run all ingestion sources and return stats."""
        if not force and self._last_run and (datetime.now(timezone.utc) - self._last_run).seconds < 300:
            return {"status": "skipped", "reason": "rate limited", "last_run": self._last_run.isoformat()}

        from app.crypto_embeddings import get_embedder
        from app.supabase_vector import get_vector_store

        embedder = await get_embedder()
        vector_store = await get_vector_store()

        stats = {"sources": {}, "total": 0, "errors": 0}

        for source_name, ingest_fn in self.connectors:
            try:
                docs = await ingest_fn(embedder)
                if docs:
                    count = await vector_store.insert_batch(docs)
                    stats["sources"][source_name] = count
                    stats["total"] += count
                    logger.info(f"Ingested {count} docs from {source_name}")
            except Exception as e:
                logger.error(f"Ingestion failed for {source_name}: {e}")
                stats["errors"] += 1
                stats["sources"][source_name] = 0

        self._last_run = datetime.now(timezone.utc)
        self._total_ingested += stats["total"]

        # Build index after bulk ingestion
        if stats["total"] > 50:
            try:
                await vector_store.build_index()
            except Exception:
                pass

        return {
            "status": "completed",
            "total_ingested": stats["total"],
            "cumulative_total": self._total_ingested,
            "sources": stats["sources"],
            "errors": stats["errors"],
            "timestamp": self._last_run.isoformat(),
        }

    async def _ingest_curated(self, embedder) -> List[dict]:
        """Ingest manually curated scam patterns (always available)."""
        docs = []
        for pattern in KNOWN_SCAMS_EXPANDED:
            try:
                result = await embedder.embed_scam_pattern(
                    pattern_name=pattern["name"],
                    description=pattern["description"],
                    code_snippets=pattern.get("code_snippets", []),
                    indicators=pattern.get("indicators", []),
                    severity=pattern["severity"],
                )
                doc_id = hashlib.sha256(f"curated:{pattern['name']}".encode()).hexdigest()[:16]
                docs.append({
                    "id": doc_id,
                    "collection": "known_scams",
                    "embedding": result.vector,
                    "content": f"{pattern['name']}: {pattern['description']}",
                    "metadata": pattern,
                    "source": pattern["source"],
                    "severity": pattern["severity"],
                })
            except Exception as e:
                logger.warning(f"Failed to embed curated pattern {pattern['name']}: {e}")
        return docs

    async def _ingest_rekt(self, embedder) -> List[dict]:
        """Ingest REKT News exploit reports."""
        connector = RektNewsConnector()
        reports = await connector.fetch_recent(limit=50)
        docs = []
        for report in reports:
            try:
                content = f"EXPLOIT: {report['name']}. Lost: ${report.get('amount_lost_usd', 0):,.0f}. Chain: {report.get('chain', 'unknown')}. {report.get('description', '')}"
                result = await embedder.embed_scam_pattern(
                    pattern_name=report["name"],
                    description=content,
                    severity="critical",
                )
                doc_id = hashlib.sha256(f"rekt:{report['name']}".encode()).hexdigest()[:16]
                docs.append({
                    "id": doc_id,
                    "collection": "forensic_reports",
                    "embedding": result.vector,
                    "content": content,
                    "metadata": report,
                    "source": "rekt.news",
                    "severity": "critical",
                })
            except Exception as e:
                logger.warning(f"Failed to embed REKT report {report.get('name')}: {e}")
        return docs

    async def _ingest_chainabuse(self, embedder) -> List[dict]:
        """Ingest Chainabuse scam reports."""
        connector = ChainabuseConnector()
        reports = await connector.fetch_reports(limit=50)
        docs = []
        for report in reports:
            try:
                content = f"SCAM REPORT: {report['name']}. Category: {report.get('category', 'scam')}. Addresses: {', '.join(report.get('addresses', [])[:5])}. {report.get('description', '')}"
                result = await embedder.embed_scam_pattern(
                    pattern_name=report["name"],
                    description=content,
                    severity="high",
                )
                doc_id = hashlib.sha256(f"chainabuse:{report['name']}".encode()).hexdigest()[:16]
                docs.append({
                    "id": doc_id,
                    "collection": "scam_patterns",
                    "embedding": result.vector,
                    "content": content,
                    "metadata": report,
                    "source": "chainabuse",
                    "severity": "high",
                })
            except Exception as e:
                logger.warning(f"Failed to embed Chainabuse report: {e}")
        return docs

    async def _ingest_w3igg(self, embedder) -> List[dict]:
        """Ingest Web3IsGoingGreat incidents."""
        connector = Web3IsGoingGreatConnector()
        incidents = await connector.fetch_recent(limit=30)
        docs = []
        for incident in incidents:
            try:
                content = f"INCIDENT: {incident['name']}. {incident.get('description', '')}"
                result = await embedder.embed_scam_pattern(
                    pattern_name=incident["name"],
                    description=content,
                    severity="medium",
                )
                doc_id = hashlib.sha256(f"w3igg:{incident['name']}".encode()).hexdigest()[:16]
                docs.append({
                    "id": doc_id,
                    "collection": "market_intel",
                    "embedding": result.vector,
                    "content": content,
                    "metadata": incident,
                    "source": "web3isgoinggreat",
                    "severity": "medium",
                })
            except Exception as e:
                logger.warning(f"Failed to embed W3IGG incident: {e}")
        return docs

    async def _ingest_slowmist(self, embedder) -> List[dict]:
        """Ingest SlowMist hacked reports."""
        connector = SlowMistConnector()
        reports = await connector.fetch_recent(limit=30)
        docs = []
        for report in reports:
            try:
                content = f"HACK REPORT: {report['name']}. Lost: ${report.get('amount_lost_usd', 0):,.0f}. {report.get('description', '')}"
                result = await embedder.embed_scam_pattern(
                    pattern_name=report["name"],
                    description=content,
                    severity="critical",
                )
                doc_id = hashlib.sha256(f"slowmist:{report['name']}".encode()).hexdigest()[:16]
                docs.append({
                    "id": doc_id,
                    "collection": "forensic_reports",
                    "embedding": result.vector,
                    "content": content,
                    "metadata": report,
                    "source": "slowmist",
                    "severity": "critical",
                })
            except Exception as e:
                logger.warning(f"Failed to embed SlowMist report: {e}")
        return docs


# ══════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════

_pipeline: Optional[ScamIngestionPipeline] = None


async def get_ingestion_pipeline() -> ScamIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = ScamIngestionPipeline()
    return _pipeline
