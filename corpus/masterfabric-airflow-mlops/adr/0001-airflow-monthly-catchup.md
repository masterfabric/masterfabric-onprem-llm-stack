# 0001. One Airflow run per month, backfilled in order with catchup

- Status: Accepted
- Date: 2026-11-21

## Context

A churn model at a telco is refreshed on the billing cycle: a subscriber snapshot lands every month and
the churn label for that snapshot is only known a month later. Each month's decision (keep, retrain,
promote) depends on the registry state that the previous month left behind. The lab has to replay a
year of that history reproducibly on a laptop.

## Options

| Option | For | Against |
|---|---|---|
| Cron + scripts | Minimal | No lineage, no retries, no per-task state or UI; backfills are manual |
| **Airflow 2.10, `@monthly`, `catchup=True`, `max_active_runs=1`** | Logical dates map 1:1 to months; backfill is just "unpause"; retries, branching and a UI out of the box; what CDE runs | Scheduler and metadata DB to operate |
| Kubeflow / Argo pipelines | Container-native, good for heavy training | Needs Kubernetes; the training here is seconds, not hours |
| Dagster / Prefect | Asset-oriented, nice local dev | Less common in Cloudera estates (CDE ships Airflow) |

## Decision

`dags/churn_monthly.py` runs `@monthly` from 2025-12-01 to 2026-11-01 with `catchup=True` and
`max_active_runs=1`, so the twelve months execute strictly in order. The month is passed to every task
as `{{ logical_date.strftime('%Y-%m') }}`; tasks are thin wrappers around `mlops/pipeline.py` so the
same logic is unit-testable without Airflow. `LocalExecutor` with PostgreSQL is enough for one DAG.

## Consequences

- The full year replays in about 10 minutes (task time per month 1.2–8.4 s; the rest is scheduling).
- Re-running a month is idempotent: every table write is an upsert keyed by month.
- The 2026-11 run is not due until December under `@monthly`; it was triggered manually with the same
  logical date (`airflow dags trigger -e 2026-11-01`). Documented in Limitations.
- Production: CDE's managed Airflow, with the CeleryExecutor or KubernetesExecutor and training jobs
  dispatched to CDE Spark or CML rather than run inside the worker.
