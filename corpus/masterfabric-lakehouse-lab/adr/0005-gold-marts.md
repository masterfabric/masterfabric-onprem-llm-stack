# 0005. Gold marts: atomic overwrite, panel weight, baseline churn score

- Status: Accepted
- Date: 2026-11-21

## Marts and grain

| Table | Grain | Consumers |
|---|---|---|
| `gold.daily_subscriber_usage` | subscriber x day | billing checks, customer care, BI |
| `gold.cell_hourly_load` | cell x hour | radio planning, congestion alerting |
| `gold.churn_features` | subscriber (as of the last day) | churn model training and scoring |
| `gold.cell_congestion_ranking` (Scala) | cell | capacity upgrade backlog |

## Rebuild by atomic overwrite

Marts are derived, so they are recomputed with `INSERT OVERWRITE` and dynamic partition
overwrite. Iceberg commits the whole overwrite as one snapshot; readers see the old or the
new mart, never a mix. MERGE would add delete files and complexity for no benefit at this
volume. At larger volume, recompute only the partitions touched by the incremental silver
batch (the dates present in the batch), which the same statement already supports.

## Panel weight

The generator models a **probe panel**: each synthetic subscriber stands for
`--panel-weight` real subscribers (default 60). Concurrency per cell-hour uses Little's law
(busy seconds / 3600) and is multiplied by the weight before it is compared with the cell's
engineered capacity. Without the weight a 2,000-subscriber lab would never load a cell. The
weight is a single explicit parameter, recorded in `docs/results/gold_last_run.json`.

## Baseline churn score

`churn_risk_score` is a hand-weighted, explainable score:

| Signal | Weight |
|---|---|
| usage decline (last two days vs. first two days) | 0.35 |
| dropped call rate (saturates at 10 %) | 0.25 |
| prepaid segment | 0.15 |
| tenure under 180 days | 0.15 |
| fewer than 4 active days in the window | 0.10 |

It exists to give the mart a meaningful, testable column and a baseline to beat. The
follow-up repository *masterfabric-airflow-mlops* trains and registers a real model on these
features and compares it with this baseline using the generator's held-out labels.
