#!/usr/bin/env python3
"""
Supabase vector search helper (RAG integration).
Uses the existing search_embeddings RPC already installed on the project.
No pinecone/weaviate needed — SQL + pgvector.
"""
import os
import json
import httpx
from typing import Optional, List, Dict, Any

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

async def search_similar(
    query_embedding: List[float],
    namespace: str = "default",
    match_count: int = 10,
    similarity_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Search for semantically similar documents using pgvector.
    Returns matching document IDs with similarity scores.
    
    Args:
        query_embedding: The embedding vector from your model (e.g., OpenAI Ada-002, 1536 dims)
        namespace: Search namespace to restrict results
        match_count: Number of results to return
        similarity_threshold: Minimum cosine similarity (0-1)
    """
    url = f"{SUPABASE_URL}/rest/v1/rpc/search_embeddings"
    payload = {
        "query_embedding": query_embedding,
        "match_count": match_count,
        "namespace": namespace,
        "similarity_threshold": similarity_threshold,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        return []


async def store_embedding(
    document_id: str,
    embedding: List[float],
    namespace: str = "default",
    content_hash: str = "",
    metadata: dict = None,
    model_name: str = "",
) -> Optional[Dict]:
    """
    Store an embedding for later retrieval.
    Idempotent — uses ON CONFLICT (document_id) for upsert via REST.
    """
    url = f"{SUPABASE_URL}/rest/v1/embeddings"
    payload = {
        "document_id": document_id,
        "embedding": embedding,
        "namespace": namespace,
        "content_hash": content_hash,
        "metadata": metadata or {},
        "model_name": model_name,
    }
    headers = dict(HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload, headers=headers)
        return r.json() if r.status_code in (200, 201) else None


async def get_namespace_stats(namespace: str = "default") -> dict:
    """Get document count and stats for a namespace."""
    url = f"{SUPABASE_URL}/rest/v1/embeddings?namespace=eq.{namespace}&select=id"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers={**HEADERS, "Prefer": "count=exact"})
        return {
            "namespace": namespace,
            "count": int(r.headers.get("content-range", "0").split("/")[-1] or 0),
            "status": r.status_code,
        }
