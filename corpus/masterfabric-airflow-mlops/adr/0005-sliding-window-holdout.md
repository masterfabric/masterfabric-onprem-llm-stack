# 0005. Sliding 3-month window, newest labelled month as holdout, minimum gain to promote

- Status: Accepted
- Date: 2026-11-21

## Context

Champion and challenger must be compared on data neither has seen, and on data that looks like the
next month, not like a random split of the past.

## Decision

- Train on the 3 most recent labelled months that passed the gate; hold out the newest labelled month.
- Score the current champion on the **same** holdout. Promote only if
  `challenger AUC ≥ champion AUC + 0.002`; otherwise register the challenger with `rejected_reason`.
- Model: scikit-learn `HistGradientBoostingClassifier` (lr 0.06, 300 iterations, 31 leaves, min 80 per
  leaf) behind a one-hot encoder for the categorical columns, logged with an MLflow signature.

## Options considered

| Option | Against |
|---|---|
| Random train/test split | Leaks future behaviour into training; overstates AUC under drift |
| Expanding window | Old regime dominates after a tariff change |
| Promote on any gain | Promotes noise; churns the registry |

## Consequences

- Measured: v2 (2026-07) lost by 0.0003 AUC and was rejected; v3 and v4 won by 0.039 and 0.006.
- Realised AUC is still the ground truth: it is computed next month on labels no model saw.
- An oracle AUC (the generator's own churn probabilities, 0.81–0.84 per month) bounds what any model
  could reach on this data; auto reached 0.830 in 2026-10 vs an oracle of 0.841.
