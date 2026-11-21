# 0004. Retrain on evidence: decay, drift or age

- Status: Accepted
- Date: 2026-11-21

## Context

Retraining on a fixed schedule wastes compute when nothing changed and is too slow when the market
moves (a new tariff, a competitor offer). Retraining only on realised performance is late by design:
churn labels arrive a month after the scores.

## Options

| Option | For | Against |
|---|---|---|
| Fixed schedule only | Predictable | Blind between runs |
| Realised performance only | Directly measures harm | Lags by the label delay |
| **Any of: performance decay, input drift, maximum age** | Drift reacts before labels arrive; decay catches concept drift that PSI cannot see; age bounds staleness | Three thresholds to tune |

## Decision

`decide` (in `mlops/pipeline.py`) retrains when any of these holds:

- **no champion** yet and at least 4 labelled months exist (3 to train, 1 holdout);
- **performance decay**: last realised AUC < champion's holdout AUC − 0.03;
- **data drift**: maximum feature PSI > 0.25 against a 20k-row sample of the champion's training data
  (stored as `reference/churn/vN.parquet`);
- **scheduled**: champion trained 6 or more months ago.

The reasons are stored in `mlops.decisions` with their evidence (realised vs validation AUC, PSI feature).

## Consequences

Measured over the year: 2026-07 retrained on drift (`plan` PSI 0.3151, the new tariff) but the challenger
lost; 2026-08 retrained on decay **and** drift and won (0.819 vs 0.7796); 2026-09 retrained on drift
(`plan` 0.28 vs v3's data) and won (0.8249 vs 0.8188); 2026-10 and 2026-11 kept v4. The `scheduled`
trigger never fired in a 12-month window with this much change.
