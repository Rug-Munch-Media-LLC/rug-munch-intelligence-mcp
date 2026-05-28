"""
RAG Ingestion & Retrieval Service v2
====================================
Uses CryptoEmbedder for real semantic embeddings.
Redis-backed vector store with cosine similarity search.

Collections: wallet_profiles, token_analysis, scam_patterns,
             forensic_reports, market_intel, contract_audits, known_scams
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.crypto_embeddings import (
    CryptoEmbedder, get_embedder, COLLECTIONS, KNOWN_SCAM_PATTERNS,
    EmbeddingResult,
)

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Track seeding state
_seeded = False


async def _get_redis():
    import redis.asyncio as redis
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT,
        password=REDIS_PASSWORD or None, db=0,
        decode_responses=True,
    )


# ═══════════════════════════════════════════════════════════════════
# CORE INGEST
# ═══════════════════════════════════════════════════════════════════

async def ingest_document(
    collection: str,
    content: str,
    metadata: Dict = None,
    doc_id: str = None,
) -> Dict:
    """
    Ingest a document with real semantic embedding.
    """
    embedder = await get_embedder()
    metadata = metadata or {}

    if not doc_id:
        doc_id = hashlib.sha256(
            f"{collection}:{content[:100]}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

    # Choose embedding head based on collection
    result = await _embed_by_collection(embedder, collection, content, metadata)

    # Store
    r = await _get_redis()
    doc = {
        "id": doc_id,
        "collection": collection,
        "vector": result.vector,
        "dims": result.dims,
        "model": result.model,
        "metadata": {**metadata, "head": result.head},
        "content": content[:5000],
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    # TTL by collection type:
    #   Permanent (0 = no expiry): scam_patterns, contract_audits, transaction_patterns, forensic_reports
    #   Long-lived (365 days): wallet_profiles, known_scams, market_intel
    #   Short-lived (30 days): news_articles, general, token_analysis (volatile data)
    _TTL_MAP = {
        "scam_patterns": 0,
        "contract_audits": 0,
        "transaction_patterns": 0,
        "forensic_reports": 0,
        "wallet_profiles": 86400 * 365,
        "known_scams": 86400 * 365,
        "market_intel": 86400 * 365,
        "news_articles": 86400 * 30,
        "token_analysis": 86400 * 90,
        "general": 86400 * 30,
    }
    ttl = _TTL_MAP.get(collection, 86400 * 30)
    key = f"rag:{collection}:{doc_id}"
    if ttl == 0:
        await r.set(key, json.dumps(doc))  # permanent, no expiry
    else:
        await r.setex(key, ttl, json.dumps(doc))
    await r.sadd(f"rag:idx:{collection}", doc_id)

    logger.info(f"Ingested {collection}/{doc_id}: {content[:60]}...")
    return {"id": doc_id, "dims": result.dims, "collection": collection}


async def _embed_by_collection(
    embedder: CryptoEmbedder,
    collection: str,
    content: str,
    metadata: dict,
) -> EmbeddingResult:
    """Route to the right embedding head based on collection type."""
    if collection == "scam_patterns" or collection == "known_scams":
        return await embedder.embed_scam_pattern(
            pattern_name=metadata.get("name", content[:50]),
            description=content,
            severity=metadata.get("severity", "medium"),
        )
    elif collection == "token_analysis":
        code = metadata.get("contract_code", "")
        return await embedder.embed_token_scam(
            name=metadata.get("name", ""),
            symbol=metadata.get("symbol", ""),
            description=content,
            contract_code=code,
            chain=metadata.get("chain", "solana"),
            metadata=metadata,
        )
    elif collection == "wallet_profiles":
        return await embedder.embed_wallet(
            address=metadata.get("address", ""),
            labels=metadata.get("labels", []),
            transactions=metadata.get("transactions", []),
            chain=metadata.get("chain", "solana"),
            balance_usd=float(metadata.get("balance_usd", 0) or 0),
        )
    elif collection == "contract_audits":
        return EmbeddingResult(
            vector=await embedder._semantic_embed_one(content, "semantic"),
            dims=3072,
            model="openai/text-embedding-3-large",
            head="contract_audit",
        )
    else:
        # Generic semantic
        vec = await embedder._semantic_embed_one(content, "semantic")
        return EmbeddingResult(
            vector=vec,
            dims=len(vec),
            model="openai/text-embedding-3-large",
            head="semantic",
        )


# ═══════════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════════

async def search_similar(
    query: str,
    collection: str = "wallet_profiles",
    limit: int = 10,
    min_similarity: float = 0.6,
) -> List[Dict[str, Any]]:
    """
    Semantic search across any collection.
    """
    embedder = await get_embedder()
    return await embedder.search(
        query=query,
        collection=collection,
        limit=limit,
        min_similarity=min_similarity,
    )


async def search_multi_collection(
    query: str,
    collections: List[str] = None,
    limit: int = 10,
    min_similarity: float = 0.5,
) -> List[Dict[str, Any]]:
    """Search across multiple collections and merge results."""
    if collections is None:
        collections = COLLECTIONS

    embedder = await get_embedder()

    all_results = []
    for coll in collections:
        try:
            results = await embedder.search(query, coll, limit=limit, min_similarity=min_similarity)
            for r in results:
                r["collection"] = coll
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Search failed for {coll}: {e}")

    all_results.sort(key=lambda x: x["similarity"], reverse=True)
    return all_results[:limit]


# ═══════════════════════════════════════════════════════════════════
# SCAM PATTERN DETECTION
# ═══════════════════════════════════════════════════════════════════

async def detect_scam_patterns(
    token_data: dict,
    threshold: float = 0.65,
) -> Dict[str, Any]:
    """
    Compare a token against all known scam patterns.
    Returns matched patterns with similarity scores.
    """
    embedder = await get_embedder()

    # Build a token embedding
    code = token_data.get("contract_code", "")
    desc = token_data.get("description", "")
    name = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "???")

    # Quick pre-filter: check code for exact keyword matches (fast, no API)
    code_lower = code.lower() if code else ""
    quick_matches = []
    for pattern in KNOWN_SCAM_PATTERNS:
        if not pattern["code_snippets"]:
            continue
        hits = sum(1 for s in pattern["code_snippets"] if s.lower() in code_lower)
        if hits > 0:
            quick_matches.append({
                "pattern": pattern["name"],
                "severity": pattern["severity"],
                "quick_match_score": hits / len(pattern["code_snippets"]),
                "matched_snippets": hits,
            })

    # Deep semantic comparison
    token_result = await embedder.embed_token_scam(
        name=name, symbol=symbol,
        description=desc,
        contract_code=code,
        chain=token_data.get("chain", "solana"),
        metadata=token_data,
    )

    # Vector layout: token = [semantic(sem_dim) | code(128) | behavioral(64) | wallet(64)]
    # Pattern layout: [semantic(sem_dim) | code(128)]
    sem_dim = len(token_result.vector) - 128 - 64 - 64  # back out semantic dim
    if sem_dim <= 0:
        sem_dim = 1024  # fallback

    token_sem = token_result.vector[:sem_dim]
    token_code = token_result.vector[sem_dim:sem_dim + 128]

    deep_matches = []
    for pattern in KNOWN_SCAM_PATTERNS:
        pattern_text = f"SCAM: {pattern['name']}. {pattern['description']}"
        pattern_result = await embedder.embed_scam_pattern(
            pattern_name=pattern["name"],
            description=pattern["description"],
            code_snippets=pattern.get("code_snippets", []),
            indicators=pattern.get("indicators", []),
            severity=pattern.get("severity", "high"),
        )

        # Extract pattern semantic + code portions
        pat_sem_dim = len(pattern_result.vector) - 128
        pattern_sem = pattern_result.vector[:pat_sem_dim]
        pattern_code = pattern_result.vector[pat_sem_dim:pat_sem_dim + 128] if len(pattern_result.vector) > pat_sem_dim else [0.0] * 128

        # Compare same-length portions
        min_sem = min(len(token_sem), len(pattern_sem))
        sem_sim = embedder.cosine_similarity(token_sem[:min_sem], pattern_sem[:min_sem])

        # Code similarity
        from app.crypto_embeddings import extract_contract_features
        pat_code_features = (extract_contract_features(
            "\n".join(pattern.get("code_snippets", []))
        ).tolist() if pattern.get("code_snippets") else [0.0] * 128)
        code_sim = embedder.cosine_similarity(token_code, pat_code_features) if any(pat_code_features) else 0.0

        combined = 0.7 * sem_sim + 0.3 * code_sim

        if combined >= threshold:
            deep_matches.append({
                "pattern": pattern["name"],
                "severity": pattern["severity"],
                "description": pattern["description"],
                "similarity": round(combined, 4),
                "semantic_sim": round(sem_sim, 4),
                "code_sim": round(code_sim, 4),
            })

    deep_matches.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "quick_matches": quick_matches,
        "deep_matches": deep_matches,
        "highest_threat": deep_matches[0]["pattern"] if deep_matches else "none",
        "threat_severity": deep_matches[0]["severity"] if deep_matches else "low",
    }


# ═══════════════════════════════════════════════════════════════════
# SEEDING
# ═══════════════════════════════════════════════════════════════════

async def seed_known_scams() -> Dict[str, Any]:
    """Seed the RAG database with known scam patterns."""
    global _seeded

    r = await _get_redis()
    existing = await r.scard("rag:idx:known_scams")
    if existing > 0 and _seeded:
        return {"status": "already_seeded", "count": existing}

    embedder = await get_embedder()
    count = 0

    for pattern in KNOWN_SCAM_PATTERNS:
        try:
            pid = hashlib.sha256(f"scam:{pattern['name']}".encode()).hexdigest()[:16]
            result = await embedder.embed_scam_pattern(
                pattern_name=pattern["name"],
                description=pattern["description"],
                code_snippets=pattern.get("code_snippets", []),
                indicators=pattern.get("indicators", []),
                severity=pattern.get("severity", "high"),
            )

            doc = {
                "id": pid,
                "collection": "known_scams",
                "vector": result.vector,
                "dims": result.dims,
                "model": result.model,
                "metadata": pattern,
                "content": pattern["description"],
                "stored_at": datetime.now(timezone.utc).isoformat(),
            }
            key = f"rag:known_scams:{pid}"
            await r.set(key, json.dumps(doc))  # permanent — seed data should never expire
            await r.sadd("rag:idx:known_scams", pid)
            count += 1
            logger.info(f"Seeded scam pattern: {pattern['name']}")

        except Exception as e:
            logger.error(f"Failed to seed {pattern['name']}: {e}")

    _seeded = True
    return {"status": "seeded", "count": count, "patterns": [p["name"] for p in KNOWN_SCAM_PATTERNS]}


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════

async def ingest_forensic_report(
    report_text: str,
    report_name: str = "forensic_report",
    metadata: Dict = None,
) -> Dict:
    """
    Ingest a forensic report into the RAG knowledge base.
    Forensic reports are stored permanently (TTL=0) in the forensic_reports collection.
    """
    meta = {
        **(metadata or {}),
        "name": report_name,
        "type": "forensic_report",
    }
    return await ingest_document(
        collection="forensic_reports",
        content=report_text,
        metadata=meta,
    )


async def get_stats() -> Dict[str, Any]:
    embedder = await get_embedder()
    r = await _get_redis()

    collection_sizes = {}
    for coll in COLLECTIONS:
        try:
            size = await r.scard(f"rag:idx:{coll}")
            collection_sizes[coll] = size
        except Exception:
            collection_sizes[coll] = 0

    return {
        "embedder": embedder.stats,
        "collections": collection_sizes,
        "total_docs": sum(collection_sizes.values()),
        "seeded": _seeded,
    }
