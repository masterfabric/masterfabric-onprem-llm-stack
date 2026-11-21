# 0003. Iceberg REST catalog instead of a Hive Metastore

- Status: Accepted
- Date: 2026-11-21

## Context

An Iceberg table needs a catalog that atomically swaps the pointer to its current metadata
file. Cloudera CDP uses the Hive Metastore (HMS) for this, and HMS is also what Impala and
Hive use for everything else. In the open ecosystem the Iceberg **REST catalog** protocol
has become the engine-neutral contract (Apache Polaris, Apache Gravitino, Nessie, Unity,
AWS Glue and Snowflake Open Catalog all implement it).

## Options

| Option | For | Against |
|---|---|---|
| Hive Metastore + its RDBMS | Matches CDP exactly | Two more containers (HMS + Postgres), Thrift, Hadoop config |
| **Iceberg REST catalog** | One small container; same HTTP contract as Polaris/Gravitino/Glue; Spark and Trino both speak it natively | The fixture server used here is a reference implementation, not hardened |
| JDBC catalog directly from engines | Simple | Every engine needs DB credentials and drivers |

## Decision

Use `apache/iceberg-rest-fixture:1.8.1` with SQLite on a volume
(`jdbc:sqlite:file:/var/lib/iceberg/catalog.db`), so tables survive restarts.

## Consequences

- Spark and Trino resolve `lake.<namespace>.<table>` through the same catalog, which is how
  Trino can query the marts Spark builds, time travel included.
- Moving to HMS on CDP means changing `spark.sql.catalog.lake.type` to `hive` and the URI; the
  pipeline code does not change.
- For production, replace the fixture with a governed catalog (Polaris, Gravitino, or HMS
  with Ranger) that adds authentication, authorisation and credential vending.
