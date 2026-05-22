"""
RAG Ingestion & Retrieval Service
==================================
Redis-backed vector store for crypto intelligence.
Collections: wallet_profiles, token_analysis, scam_patterns, forensic_reports, market_intel
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "ROTATED_REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

COLLECTIONS = [
    "wallet_profiles",
    "token_analysis", 
    "scam_patterns",
    "forensic_reports",
    "market_intel",
    "news_articles",
    "known_scams",
]


async def _get_redis():
    import redis.asyncio as redis
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
        db=REDIS_DB, decode_responses=True,
    )


async def ingest_document(collection: str, content: str, metadata: Dict = None) -> Dict:
    """Ingest a document into the RAG knowledge base."""
    r = await _get_redis()
    doc_id = hashlib.sha256(f"{collection}:{content[:100]}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]
    
    # Generate text chunks (simple sentence-based)
    sentences = [s.strip() for s in content.replace('\n', ' ').split('.') if len(s.strip()) > 10]
    chunks = []
    current_chunk = ""
    for s in sentences:
        if len(current_chunk) + len(s) < 500:
            current_chunk += s + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = s + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    if not chunks:
        chunks = [content[:500]]
    
    # Store document metadata
    doc = {
        "id": doc_id,
        "collection": collection,
        "content_preview": content[:200],
        "chunks": len(chunks),
        "metadata": metadata or {},
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await r.hset(f"rag:doc:{doc_id}", mapping={k: json.dumps(v) if isinstance(v, dict) else str(v) for k, v in doc.items()})
    await r.sadd(f"rag:collection:{collection}", doc_id)
    
    # Store chunks for retrieval
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}:{i}"
        await r.set(f"rag:chunk:{chunk_id}", json.dumps({
            "doc_id": doc_id, "collection": collection,
            "index": i, "text": chunk, "metadata": metadata or {},
        }))
        await r.sadd(f"rag:doc_chunks:{doc_id}", chunk_id)
        # Simple keyword index for retrieval
        words = set(chunk.lower().split())
        for word in words:
            if len(word) > 2:
                await r.sadd(f"rag:idx:{collection}:{word}", chunk_id)
    
    await r.close()
    logger.info(f"RAG ingest: {doc_id} → {collection} ({len(chunks)} chunks)")
    return {"id": doc_id, "collection": collection, "chunks": len(chunks), "status": "ingested"}


async def search_documents(collection: str, query: str, limit: int = 10) -> List[Dict]:
    """Search the RAG knowledge base by keyword matching."""
    r = await _get_redis()
    query_words = set(query.lower().split())
    
    # Find matching chunks
    chunk_scores = {}
    for word in query_words:
        if len(word) > 2:
            chunk_ids = await r.smembers(f"rag:idx:{collection}:{word}")
            for cid in chunk_ids:
                chunk_scores[cid] = chunk_scores.get(cid, 0) + 1
    
    # Sort by score, get top results
    sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    results = []
    seen_docs = set()
    for chunk_id, score in sorted_chunks:
        chunk_data = await r.get(f"rag:chunk:{chunk_id}")
        if chunk_data:
            chunk = json.loads(chunk_data)
            doc_id = chunk["doc_id"]
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                results.append({
                    "doc_id": doc_id,
                    "collection": chunk["collection"],
                    "relevance": score,
                    "content": chunk["text"][:300],
                    "metadata": chunk.get("metadata", {}),
                })
    
    await r.close()
    return results


async def get_collection_stats() -> Dict:
    """Get statistics for all RAG collections."""
    r = await _get_redis()
    stats = {}
    for collection in COLLECTIONS:
        doc_ids = await r.smembers(f"rag:collection:{collection}")
        total_chunks = 0
        for did in doc_ids:
            chunks = await r.smembers(f"rag:doc_chunks:{did}")
            total_chunks += len(chunks)
        stats[collection] = {"documents": len(doc_ids), "chunks": total_chunks}
    await r.close()
    return {"collections": stats, "total_documents": sum(s["documents"] for s in stats.values())}


async def ingest_known_scams():
    """Seed the RAG with known scam patterns from our database."""
    known = [
        {"pattern": "honeypot", "indicators": "sell restrictions, max transaction limits, whitelist-only transfers, 95-100% sell tax, tx.origin abuse in transfer/approve functions"},
        {"pattern": "rugpull", "indicators": "liquidity removal, deployer dumping, ownership not renounced, mint function active, large holder concentration >80%"},
        {"pattern": "bundled_supply", "indicators": "multiple wallets funded from same source within seconds, synchronized buys at launch, shared CEX withdrawal origin, identical gas parameters"},
        {"pattern": "fresh_wallet_farm", "indicators": "wallets with zero prior activity, batch-created from same funder, identical first-transaction timing, sub-threshold individual transactions"},
        {"pattern": "ponzi_structure", "indicators": "referral rewards from new deposits, guaranteed returns, withdrawal restrictions, multi-level commission structure, anonymous team"},
        {"pattern": "wash_trading", "indicators": "circular token flows, self-trading patterns, volume/liquidity ratio >50x, identical trade sizes, bot-like timing precision"},
        {"pattern": "cex_funding_sybil", "indicators": "funding from same CEX hot wallet, batch withdrawals within narrow time window, uniform funding amounts, peeling chain distribution"},
        {"pattern": "dust_attack", "indicators": "microscopic transfers to seed wallets, 1-lamport/satoshi amounts, batch processing scripts, reconnaissance pattern before large extraction"},
        {"pattern": "insider_trading", "indicators": "buys within seconds of announcement, predetermined contest winners, pre-positioned wallets, no on-chain voting mechanism at claimed time"},
        {"pattern": "phishing_token", "indicators": "copycat naming, similar contract bytecode to known scams, unverified contract, fake social links, no liquidity lock"},
    ]
    
    for item in known:
        await ingest_document("known_scams", json.dumps(item), {"source": "rmi_internal", "category": "scam_pattern"})
    
    logger.info(f"Seeded RAG with {len(known)} known scam patterns")


async def ingest_forensic_report(report_text: str, report_name: str = "forensic_report"):
    """Ingest a forensic investigation report."""
    return await ingest_document("forensic_reports", report_text, {
        "source": "investigation",
        "report_name": report_name,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    })
