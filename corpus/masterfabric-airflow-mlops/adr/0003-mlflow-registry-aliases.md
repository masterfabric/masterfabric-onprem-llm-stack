# 0003. MLflow registry aliases as the deployment contract

- Status: Accepted
- Date: 2026-11-21

## Context

Training and serving must agree on which model is live without a redeploy, and rollback must be a
metadata change. MLflow 2.9+ deprecates stages (Staging/Production) in favour of aliases.

## Options

| Option | For | Against |
|---|---|---|
| Stages (`Production`) | Familiar | Deprecated; one model per stage |
| **Aliases `@champion` and `@static_baseline`** | Any number of named pointers; atomic move; consumers resolve `models:/churn@champion` | Consumers must re-resolve (poll or webhook) |
| Copy the artefact to a fixed path | No registry needed | No lineage, no audit, race conditions |

## Decision

Every challenger is registered as a new version of `churn` with tags `holdout_auc`, `holdout_month`,
`train_months` and `trained_in_month` (and `rejected_reason` if it lost). Promotion is
`set_registered_model_alias("churn", "champion", v)`. The first champion also gets `@static_baseline`
and keeps it forever: it is the "never retrain" policy that the realised-AUC comparison is run against.
Batch scoring writes both policies' scores every month.

## Consequences

- Rejected challengers stay in the registry with the reason (v2: `auc 0.7816 < champion 0.7819 + 0.002`).
- Rollback is one call; measured end to end in [0006](0006-serving-hot-swap.md).
- Production: CML Model Registry (MLflow-compatible), with alias changes gated by an approval step.
