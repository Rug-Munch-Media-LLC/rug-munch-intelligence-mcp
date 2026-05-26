#!/usr/bin/env python3
"""
Ingest extracted arxiv paper texts into RAG 'forensic_reports' collection.
Reads .txt files and metadata from /root/backend/data/papers/,
chunks each paper into ~2000 word sections, and ingests via the
RAG HTTP API at localhost:8000/api/v1/rag/ingest.

Usage:
    python3 ingest_papers.py [--api http://localhost:8000] [--chunk-words 2000] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
import time
import requests

PAPERS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "papers")
METADATA_FILE = os.path.join(PAPERS_DIR, "papers_metadata.json")
DEFAULT_API = "http://localhost:8000"
DEFAULT_CHUNK_WORDS = 2000


def load_metadata():
    with open(METADATA_FILE, "r") as f:
        return json.load(f)


def discover_txt_files():
    """Find all .txt files in papers_dir, map arxiv_id -> filepath."""
    txt_files = {}
    for fname in os.listdir(PAPERS_DIR):
        if fname.endswith(".txt"):
            arxiv_id = fname.replace(".txt", "")
            txt_files[arxiv_id] = os.path.join(PAPERS_DIR, fname)
    return txt_files


def chunk_text(text, chunk_words=DEFAULT_CHUNK_WORDS):
    """
    Split text into chunks of approximately chunk_words words.
    We try to split at paragraph/section boundaries when possible.
    Falls back to hard word-count splits if sections are too long.
    """
    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for para in paragraphs:
        para_words = len(para.split())
        
        # If single paragraph exceeds chunk size, split it further by sentences
        if para_words > chunk_words * 1.5:
            # Flush current chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_word_count = 0
            
            # Split long paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                sent_words = len(sent.split())
                if current_word_count + sent_words > chunk_words * 1.2 and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_word_count = 0
                current_chunk.append(sent)
                current_word_count += sent_words
        elif current_word_count + para_words > chunk_words * 1.2 and current_chunk:
            # Current chunk is full, start a new one
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_word_count = para_words
        else:
            current_chunk.append(para)
            current_word_count += para_words
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


def ingest_chunk(api_base, collection, content, metadata, doc_id=None):
    """Ingest a single chunk via the RAG HTTP API."""
    url = f"{api_base}/api/v1/rag/ingest"
    payload = {
        "collection": collection,
        "content": content,
        "metadata": metadata,
    }
    if doc_id:
        payload["doc_id"] = doc_id
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Ingest failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  [ERROR] Response: {e.response.text[:200]}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Ingest arxiv papers into RAG")
    parser.add_argument("--api", default=DEFAULT_API, help="API base URL")
    parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    parser.add_argument("--dry-run", action="store_true", help="Preview chunks without ingesting")
    parser.add_argument("--paper", type=str, help="Ingest only this specific arxiv ID")
    args = parser.parse_args()
    
    metadata = load_metadata()
    txt_files = discover_txt_files()
    
    total_chunks = 0
    total_ingested = 0
    total_failed = 0
    
    arxiv_ids = sorted(metadata.keys())
    if args.paper:
        arxiv_ids = [args.paper]
    
    for arxiv_id in arxiv_ids:
        meta = metadata.get(arxiv_id, {})
        txt_path = txt_files.get(arxiv_id)
        
        if not txt_path or not os.path.exists(txt_path):
            print(f"[SKIP] No .txt file for {arxiv_id}")
            continue
        
        title = meta.get("title", arxiv_id)
        print(f"\n{'='*60}")
        print(f"Processing: {title} ({arxiv_id})")
        print(f"{'='*60}")
        
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        word_count = len(text.split())
        print(f"  Total words: {word_count}")
        
        chunks = chunk_text(text, args.chunk_words)
        print(f"  Chunks created: {len(chunks)} (~{args.chunk_words} words each)")
        total_chunks += len(chunks)
        
        collection = meta.get("collection", "forensic_reports")
        
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                "source": "arxiv",
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": meta.get("authors", []),
                "year": meta.get("year"),
                "attack_types": meta.get("attack_types", []),
                "description": meta.get("description", ""),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_type": "academic_paper",
            }
            
            # Prepend header to content for better retrieval context
            header = f"[PAPER: {title} | {arxiv_id}.pdf | Part {i+1}/{len(chunks)}]\n\n"
            full_content = header + chunk
            
            # Generate stable doc_id
            doc_id = f"paper_{arxiv_id}_chunk{i:03d}"
            
            if args.dry_run:
                print(f"  [DRY-RUN] Chunk {i+1}/{len(chunks)}: {len(chunk.split())} words, doc_id={doc_id}")
                continue
            
            result = ingest_chunk(args.api, collection, full_content, chunk_meta, doc_id)
            if result:
                total_ingested += 1
                print(f"  [OK] Chunk {i+1}/{len(chunks)}: doc_id={result.get('id', doc_id)}")
            else:
                total_failed += 1
                print(f"  [FAIL] Chunk {i+1}/{len(chunks)}")
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.15)
    
    print(f"\n{'='*60}")
    print(f"INGESTION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Ingested: {total_ingested}")
    print(f"  Failed: {total_failed}")
    if args.dry_run:
        print(f"  Mode: DRY-RUN (no data sent)")
    

if __name__ == "__main__":
    main()
