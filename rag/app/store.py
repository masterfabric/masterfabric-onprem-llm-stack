"""pgvector storage: one row per chunk with a 384-d embedding and an HNSW cosine index."""
from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector

from .config import settings

SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS chunks (
    id          bigserial PRIMARY KEY,
    source      text NOT NULL,          -- repo/path of the document
    section     text NOT NULL,          -- heading path inside the document
    content     text NOT NULL,
    trust       text NOT NULL DEFAULT 'internal',
    embedding   vector({settings.embed_dim}) NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
"""


def connect() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def init(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA)


def search(conn: psycopg.Connection, vec, k: int) -> list[dict]:
    rows = conn.execute(
        "SELECT source, section, content, trust, 1 - (embedding <=> %s) AS score "
        "FROM chunks ORDER BY embedding <=> %s LIMIT %s", (vec, vec, k)).fetchall()
    return [dict(source=r[0], section=r[1], content=r[2], trust=r[3], score=float(r[4])) for r in rows]
