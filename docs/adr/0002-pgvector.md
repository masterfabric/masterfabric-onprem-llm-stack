# 0002. pgvector instead of Milvus for the retrieval store

- Status: Accepted
- Date: 2026-11-21

## Context

The corpus is small (207 chunks), and the platform team already runs PostgreSQL.

## Options

| Option | For | Against |
|---|---|---|
| **PostgreSQL 16 + pgvector (HNSW, cosine)** | One familiar database, SQL filters next to vectors, backups and RBAC already solved | Single node; not built for billions of vectors |
| Milvus | Scales out, GPU indexes | Etcd, MinIO/S3, Pulsar or Kafka, several services: heavy for a laptop and for this corpus size |
| In-process FAISS | Fastest to start | No persistence, no concurrent writers, no access control |

## Decision

pgvector runs as a StatefulSet with a PVC and a generated password that is kept across upgrades. One
`chunks` table stores source, section, content, a `trust` label and a `vector(384)` with an HNSW index.

## Consequences

- Measured retrieval takes milliseconds per question (see `timings_ms.retrieve` in the evaluation output).
- The `trust` column is what a row-level filter needs (for example, excluding `untrusted` sources for
  some users). Fine-grained access is the topic of masterfabric-secure-data-ai.
