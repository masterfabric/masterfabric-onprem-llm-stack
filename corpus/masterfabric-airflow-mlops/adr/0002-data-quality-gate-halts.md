# 0002. A blocking data-quality gate that halts the month

- Status: Accepted
- Date: 2026-11-21

## Context

A broken upstream feed (nulls, negative fees after a billing migration, a missing column) silently
poisons three things at once: drift statistics, the next training set and the scores sent to CRM.

## Options

| Option | For | Against |
|---|---|---|
| Warn and continue | Never blocks the business | Bad data reaches training and the retention list |
| **Critical rules block; warnings are recorded** | Bad months never reach models or customers; warnings keep noise low | A false positive blocks a month (needs an override path) |
| Impute and continue | Keeps the cadence | Hides the incident; imputed training data |

## Decision

`mlops/quality.py` runs 11 rules on every snapshot: 9 critical (schema complete, minimum rows, unique
`subscriber_id`, null rate ≤ 1% per column, non-negative fee, ranges for dropped-call rate, NPS and
tenure, binary 5G flag) and 2 warnings (row-count change ≤ 20%, only catalogued tariffs). `dq_gate` is a
`BranchPythonOperator`: any critical failure routes to `halt_month`, which skips drift, training and
scoring for that month. Results land in `mlops.dq_results`.

A month that fails the gate is also excluded from future training windows (`labelled_months`).

## Consequences

- Measured: the injected 2026-03 failure was caught (`null_rate_max`, `monthly_fee_non_negative`), the
  month was halted, and March never entered a training or holdout set: v1 was held out on 2026-04
  and v2 trained on 2026-02, 2026-04 and 2026-05.
- The new `postpaid_5g` tariff (2026-07) is catalogued, so it does not trip `plan_known`; it shows up
  as drift instead, which is the intended signal.
- Production: the same rules as Great Expectations or Deequ suites, with an explicit "release month"
  override recorded in the audit log.
