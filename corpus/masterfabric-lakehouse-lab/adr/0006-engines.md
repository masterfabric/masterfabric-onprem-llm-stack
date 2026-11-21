# 0006. Spark for pipelines, Trino for interactive SQL

- Status: Accepted
- Date: 2026-11-21

## Context

A Cloudera estate typically runs Spark on YARN for pipelines, Hive (on Tez) for batch SQL,
and Impala for low-latency interactive SQL, all over the same tables. The lab needs the same
split at laptop scale.

## Decision

- **Spark 3.5.5** (PySpark plus one Scala job) for bronze, silver, gold, quality and table
  maintenance. Jobs run with `local[4]` inside the Spark container; on a cluster the only
  change is `--master yarn` (or Kubernetes) and executor sizing.
- **Trino 475** as the interactive MPP engine, the stand-in for **Impala**: long-running
  coordinator/worker daemons, in-memory pipelined execution, no per-query JVM start-up, ANSI
  SQL, Iceberg connector with time travel. It reads the same tables via the same REST catalog.

## Mapping to Cloudera CDP

| Lab | CDP equivalent |
|---|---|
| Spark local mode in a container | Spark on YARN (CDP Private Cloud Base) or CDE |
| Trino | Impala (CDW / Base), with Hive LLAP/Tez for heavy batch SQL |
| `spark-shell -I` Scala job | Scala Spark application submitted to YARN |
| Jupyter in the Spark image | Cloudera Machine Learning (CML) sessions / Hue notebooks |
| `make` targets | Oozie, Airflow (CDE) or Control-M |

## Consequences

- Spark jobs pay 2 to 3 seconds of JVM start-up each; this is visible in the per-layer
  timings and is the reason interactive questions go to Trino, not to spark-sql.
- Trino has no Kerberos/Ranger configured here. On CDP, Impala inherits Ranger policies and
  Kerberos from the cluster; see the security notes in the README.
