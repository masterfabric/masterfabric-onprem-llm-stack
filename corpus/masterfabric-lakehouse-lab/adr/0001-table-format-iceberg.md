# 0001. Apache Iceberg as the table format

- Status: Accepted
- Date: 2026-11-21

## Context

The lab has to behave like an enterprise lakehouse: several engines (Spark for pipelines, an
MPP SQL engine for analysts) read and write the same tables, records arrive late and get
corrected, schemas change while the tables are in use, and the storage layer is object
storage, where renames are not atomic and listing is slow.

Plain Hive tables (directories of files plus a metastore partition list) do not give atomic
multi-file commits, rely on directory listing for planning, and make schema and partition
changes either impossible or a full rewrite.

## Options

| Option | For | Against |
|---|---|---|
| **Apache Iceberg** | Engine-neutral spec; hidden partitioning and partition evolution; snapshot isolation; row-level deletes (v2); REST catalog standard; first-class in Cloudera CDP (Spark, Hive, Impala), Trino, Flink, Snowflake, BigQuery | More metadata objects to maintain (manifests, snapshots) |
| Delta Lake | Mature, very good Spark integration | Strongest in the Databricks ecosystem; Impala on CDP does not read it |
| Apache Hudi | Strong record-level upserts and incremental pulls | Heavier write path, smaller engine ecosystem |
| Hive ACID (ORC) | Native on older CDH/HDP | Tied to Hive; compaction pain; no clean multi-engine story |

## Decision

Use **Apache Iceberg (format v2)** for every table in every layer.

## Consequences

- Partition columns are derived by transforms (`months(event_time)`, `days(event_time)`), so
  queries filter on `event_time` and still prune. When volume grew, `silver.cdr` moved from
  monthly to daily partitions with one metadata commit and zero rewritten files
  (see the README, partition evolution).
- Every write is an atomic snapshot; the pipeline can read "exactly what was appended since
  the last run" with incremental scans, which is how silver stays incremental.
- Snapshots, manifests and delete files accumulate and must be maintained: see ADR 0007.
- On Cloudera CDP the same tables are readable by Impala and Hive (Iceberg is GA in CDP
  Public and Private Cloud), so the design carries over without a format migration.
