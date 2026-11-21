# 0007. Merge-on-read writes with scheduled compaction and snapshot expiry

- Status: Accepted
- Date: 2026-11-21

## Context

`silver.cdr` receives small, frequent correction batches (re-rated and late CDRs). With
copy-on-write, every MERGE rewrites each data file that contains a matched row: cheap reads,
expensive writes. With merge-on-read, a MERGE writes small data files plus position-delete
files: cheap writes, reads that must apply deletes until compaction.

## Decision

- `silver.cdr` uses **merge-on-read** for MERGE, UPDATE and DELETE.
- Maintenance is a scheduled job, in this order:
  1. `rewrite_data_files` (binpack; `rewrite-all` after a partition-spec change so old files
     move to the new spec; `remove-dangling-deletes`)
  2. `rewrite_position_delete_files`
  3. `expire_snapshots` (keep the last N, here 3; in production keep 5 to 7 days so time
     travel covers a full weekly reconciliation)
  4. orphan file scan, with a minimum age of 24 h
- Orphan scan through **Iceberg FileIO** (`listPrefix` vs. every file referenced by any
  snapshot, manifest or metadata version), because Iceberg's built-in action lists storage
  through a Hadoop `FileSystem` and the Spark image has no `s3://` Hadoop connector.

## Evidence

The demo applies 10 correction micro-batches and then compacts. The measured file counts,
delete files, snapshot counts and query times before and after are in
`docs/results/iceberg_demos.json` and in the README.

## Consequences

- Readers between compactions pay for delete files; the compaction cadence (hourly for hot
  partitions, daily for the rest) is the knob.
- Snapshot expiry ends time travel beyond the retained window. That is a governance decision
  (how far back must an auditor be able to look?) and must be agreed with the data owner.
- The Iceberg guard that refuses an orphan scan younger than 24 h is kept on purpose: a file
  being written by a concurrent job looks exactly like an orphan.
