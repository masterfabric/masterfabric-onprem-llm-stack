# 0004. Medallion layers with explicit contracts and quarantine

- Status: Accepted
- Date: 2026-11-21

## Context

Telecom feeds are messy: switches retransmit, mediation systems deliver late, vendor exports
mix timestamp formats, and a bad deploy upstream can change a field overnight. The platform
must never lose a record silently, must not double count, and must be able to prove both.

## Decision

| Layer | Contract | Write pattern |
|---|---|---|
| **bronze** | Raw values as STRING, plus `_source_file`, `_source_date`, `_batch_id`, `_ingested_at`. Nothing is rejected. | Append; each source file exactly once (`ops.ingest_log`) |
| **silver** | Typed, validated, deduplicated on the business key, conformed to subscribers and cells. Failed rows go to `silver.quarantine` with the first failed rule and the raw payload. | Incremental scan of new bronze snapshots, then `MERGE INTO` (newer `_ingested_at` wins) |
| **gold** | Business-ready marts with documented grain. | `INSERT OVERWRITE` (dynamic partitions), atomic |
| **ops** | Ingest log, silver checkpoints, data quality history. | Append |

Quality is a gate, not a report: `lakehouse/quality.py` exits non-zero on any error-level
rule so the orchestrator does not publish gold.

## Why these choices

- **Strings in bronze**: parsing at ingest is the most common way records disappear. A raw
  layer that cannot fail keeps a replayable copy of exactly what arrived.
- **Incremental by snapshot, not by timestamp column**: Iceberg snapshots are exact. A
  watermark on `_ingested_at` breaks with clock skew and with backfills.
- **MERGE with newer-wins**: a re-sent identical record is a no-op, a correction updates, a
  stale re-send cannot overwrite a newer value. Covered by `tests/spark/test_iceberg_merge.py`.
- **Quarantine with reasons**: operations can count defects per producer and per rule and
  replay them after a fix.
- **Reconciliation against the producer's manifest**: the generator states how many
  duplicates and malformed rows it produced; the gate checks the pipeline removed exactly
  that many. In production the same idea uses control totals from mediation.

## Consequences

- Bronze roughly doubles storage for event data. Retention on bronze (e.g. 30 to 90 days)
  bounds that cost.
- The first-failure rule list reports one reason per row; multi-reason reporting would need
  an array column and is deliberately left out to keep the quarantine queryable.
