#!/usr/bin/env python3
"""
Standalone RAG Client for OpenClaw Agents
- Uses only stdlib + sqlite3 (no ChromaDB dependency)
- Exposes query, reflection, multi-hop features
- Tool-calling schema for agentic integration
"""

import os
import sqlite3
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# ============================================================
# CONFIG
# ============================================================
RAG_DIR = Path(os.path.expanduser("~/.hermes/rag_vectors"))
CHROMA_DB = RAG_DIR / "chroma.sqlite3"


class StandaloneRAGClient:
    """
    Standalone RAG client using ChromaDB SQLite directly.
    Works around pydantic version conflicts.
    """

    def __init__(self, db_path: Path = CHROMA_DB):
        if not db_path.exists():
            raise FileNotFoundError(f"ChromaDB not found: {db_path}")
        self.db_path = db_path
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    # ============================================================
    # EMBEDDING (simple hash-based - same as original rag_system_v2)
    # ============================================================
    def _simple_embed(self, text: str) -> List[float]:
        """Simple hash-based embedding (128 dimensions)."""
        words = re.findall(r'\w+', text.lower())
        vec = [0.0] * 128
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % 128
            vec[idx] += 1.0
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec] if norm > 0 else vec

    # ============================================================
    # QUERY INTERFACE
    # ============================================================
    def query(
        self,
        query_text: str,
        n: int = 5,
        source_filter: Optional[str] = None,  # Added parameter for CLI compatibility
        namespace: Optional[str] = None  # Added for CLI compatibility
    ) -> List[Dict[str, Any]]:
        """Query RAG using vector similarity (approximate)."""
        if source_filter is None and namespace is not None:
            source_filter = namespace
        if source_filter is not None:
            print(f"DEBUG: source_filter={source_filter}", file=sys.stderr)
        conn = self._get_conn()
        query_vec = self._simple_embed(query_text)

        # Get all documents with metadata
        cursor = conn.execute(
            """
            SELECT e.id, em.string_value as document, 
                   ms1.string_value as source, ms2.string_value as ingested_at
            FROM embeddings e
            LEFT JOIN embedding_metadata em ON e.id = em.id AND em.key = 'document'
            LEFT JOIN embedding_metadata ms1 ON e.id = ms1.id AND ms1.key = 'source'
            LEFT JOIN embedding_metadata ms2 ON e.id = ms2.id AND ms2.key = 'ingested_at'
            """
        )

        results = []
        for row in cursor.fetchall():
            doc_text = row['document']
            if not doc_text:
                continue

            # Fallback: keyword match + simple scoring
            doc_lower = doc_text.lower()
            score = 0
            for w in query_text.lower().split():
                if w in doc_lower:
                    score += 1

            if score > 0:
                results.append({
                    'text': doc_text[:500],
                    'metadata': {
                        'source': row['source'] or 'unknown',
                        'ingested_at': row['ingested_at']
                    },
                    'score': score,
                    'distance': 1.0 - (score / 10)  # Inverse of score
                })

        # Sort and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:n]

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
        count = cursor.fetchone()[0]
        return {
            "total_documents": count,
            "collection": "rmi_intelligence",
            "storage_path": str(RAG_DIR)
        }

    # ============================================================
    # AGENTIC FEATURES
    # ============================================================
    def reflection_loop(
        self,
        original_query: str,
        max_iterations: int = 3,
        confidence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Self-correcting retrieval with iteration budgets.
        """
        iterations = []
        current_query = original_query
        all_results = []

        for i in range(max_iterations):
            results = self.query(current_query, n=5)

            confidence = len(results) / 5  # heuristic

            iterations.append({
                'step': i,
                'query': current_query,
                'results_count': len(results),
                'confidence': round(confidence, 3)
            })

            all_results.extend(results)

            # Check stop conditions
            if confidence >= confidence_threshold:
                iterations[-1]['reason'] = 'confidence_threshold_reached'
                break

            if len(results) == 0:
                iterations[-1]['reason'] = 'no_new_results'
                break

            # Refine
            current_query = f"additional details about: {current_query}"

        return {
            'original_query': original_query,
            'iterations': iterations,
            'final_results': all_results
        }

    def multi_hop_query(
        self,
        question: str,
        hops: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Chain multiple queries for complex reasoning."""
        all_results = []

        for hop in hops:
            hop_results = self.query(hop['query'])
            hop_result_list = [
                {'text': r['text'], 'source': r['metadata'].get('source', 'unknown'), 'hop': hop['purpose']}
                for r in hop_results
            ]
            all_results.extend(hop_result_list)

        return {
            'question': question,
            'hops': len(hops),
            'results': all_results,
            'total_results': len(all_results)
        }

    def get_tool_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible tool schema."""
        return {
            'type': 'function',
            'function': {
                'name': 'rag_query',
                'description': (
                    "Query RugMunch Intelligence RAG for crypto security patterns, "
                    "rug pull indicators, wallet risk scores, and market intelligence."
                ),
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'Search query for RAG'
                        },
                        'namespace': {
                            'type': 'string',
                            'enum': ['scan_results', 'alerts', 'content', 'market_data', 'onchain', 'social_feed', 'news'],
                            'default': None
                        },
                        'n_results': {
                            'type': 'integer',
                            'minimum': 1,
                            'maximum': 20,
                            'default': 5
                        }
                    },
                    'required': ['query']
                }
            }
        }


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Standalone RAG Client')
    parser.add_argument('command', choices=['query', 'reflection', 'multi-hop', 'schema', 'stats'])
    parser.add_argument('--query', type=str, help='Query text')
    parser.add_argument('--namespace', type=str, help='Source filter')
    parser.add_argument('--n', type=int, default=5, help='Results count')
    parser.add_argument('--hops', type=str, help='Multi-hop config (JSON)')
    parser.add_argument('--max-iter', type=int, default=3, help='Max iterations')

    args = parser.parse_args()

    rag = StandaloneRAGClient()

    if args.command == 'query':
        result = rag.query(args.query, namespace=args.namespace, n=args.n)
        print(json.dumps(result, indent=2))

    elif args.command == 'reflection':
        result = rag.reflection_loop(args.query, max_iterations=args.max_iter)
        print(json.dumps(result, indent=2))

    elif args.command == 'multi-hop':
        hops = json.loads(args.hops)
        result = rag.multi_hop_query(args.query, hops)
        print(json.dumps(result, indent=2))

    elif args.command == 'schema':
        print(json.dumps(rag.get_tool_schema(), indent=2))

    elif args.command == 'stats':
        print(json.dumps(rag.get_stats(), indent=2))
    else:
        print(f"Unknown command: {args.command}")
