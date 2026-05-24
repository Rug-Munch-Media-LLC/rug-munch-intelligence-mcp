-- ═══════════════════════════════════════════════════════════════════
-- RMI pgvector Setup — Run ONCE in Supabase SQL Editor
-- https://ufblzfxqwgaekrewncbi.supabase.co → SQL Editor
-- ═══════════════════════════════════════════════════════════════════

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the vector table
CREATE TABLE IF NOT EXISTS rag_vectors (
    id TEXT PRIMARY KEY,
    collection TEXT NOT NULL,
    content TEXT,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    source TEXT,
    severity TEXT DEFAULT 'medium',
    chain TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create indexes
CREATE INDEX IF NOT EXISTS idx_rag_collection ON rag_vectors (collection);
CREATE INDEX IF NOT EXISTS idx_rag_severity ON rag_vectors (severity);
CREATE INDEX IF NOT EXISTS idx_rag_source ON rag_vectors (source);
CREATE INDEX IF NOT EXISTS idx_rag_chain ON rag_vectors (chain);
CREATE INDEX IF NOT EXISTS idx_rag_content_fts ON rag_vectors
    USING GIN (to_tsvector('english', COALESCE(content, '')));

-- 4. Create the store_embedding function (missing from Supabase)
CREATE OR REPLACE FUNCTION store_embedding(
    document_id TEXT,
    embedding vector(1024),
    namespace TEXT DEFAULT 'default',
    content_hash TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    model_name TEXT DEFAULT ''
) RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    result JSONB;
BEGIN
    INSERT INTO rag_vectors (id, collection, embedding, metadata, source, updated_at)
    VALUES (document_id, namespace, embedding, metadata, model_name, NOW())
    ON CONFLICT (id) DO UPDATE SET
        embedding = EXCLUDED.embedding,
        metadata = EXCLUDED.metadata,
        updated_at = NOW();
    
    result = jsonb_build_object('status', 'stored', 'document_id', document_id);
    RETURN result;
END;
$$;

-- 5. Update search_embeddings to point at rag_vectors (if needed)
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1024),
    namespace TEXT DEFAULT 'default',
    match_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7
) RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    source TEXT,
    severity TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rv.id,
        rv.content,
        rv.metadata,
        rv.source,
        rv.severity,
        (1 - (rv.embedding <=> query_embedding))::FLOAT AS similarity
    FROM rag_vectors rv
    WHERE (namespace = 'default' OR rv.collection = namespace)
      AND 1 - (rv.embedding <=> query_embedding) > similarity_threshold
    ORDER BY rv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 6. Update search_embeddings to handle 128-dim vectors too (for hash fallback)
CREATE OR REPLACE FUNCTION search_embeddings_128(
    query_embedding vector(128),
    namespace TEXT DEFAULT 'default',
    match_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7
) RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    source TEXT,
    severity TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rv.id,
        rv.content,
        rv.metadata,
        rv.source,
        rv.severity,
        (1 - (rv.embedding::vector(128) <=> query_embedding))::FLOAT AS similarity
    FROM rag_vectors rv
    WHERE (namespace = 'default' OR rv.collection = namespace)
      AND 1 - (rv.embedding::vector(128) <=> query_embedding) > similarity_threshold
    ORDER BY rv.embedding::vector(128) <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 7. After data is loaded, build the ANN index
-- Run this separately after you've loaded a few hundred documents:
-- CREATE INDEX IF NOT EXISTS idx_rag_embedding_ivfflat ON rag_vectors
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Verify
SELECT 'pgvector setup complete' AS status;
SELECT count(*) AS vector_count FROM rag_vectors;
