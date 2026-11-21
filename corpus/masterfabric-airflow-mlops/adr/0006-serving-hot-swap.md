# 0006. Online API resolves @champion and hot-swaps without a restart

- Status: Accepted
- Date: 2026-11-21

## Context

Monthly batch scores feed the CRM retention list, but online channels (call centre, app) need a score
for one subscriber now, from the same model the batch used.

## Options

| Option | For | Against |
|---|---|---|
| Bake the model into the image | Immutable | A redeploy per promotion; rollback is a redeploy |
| Registry webhook → reload | Instant | Needs the webhook plumbing (not in OSS MLflow 2.22) |
| **Poll the alias every 15 s, swap atomically** | Simple, works with OSS MLflow; rollback is an alias move | Up to one poll interval of lag |
| MLflow `models serve` per version | Zero code | One process per version; no alias following |

## Decision

`serving/app.py` (FastAPI) resolves `models:/churn@champion` at start-up and re-checks the alias every
15 s; when the version changes it loads the new pyfunc model and swaps a reference under a lock. MLflow's
signature enforcement is kept on, so a wrongly typed request fails loudly instead of being cast silently.

## Consequences

- Measured: 200 single-subscriber requests p50 2.67 ms, p95 2.93 ms; a 1000-row batch in 11.4 ms; max
  absolute difference to the offline batch scores 5.0e-6.
- Measured rollback: moving `@champion` v4 → v3 was served after 3.41 s and v3 → v4 after 15.27 s,
  bounded by the poll interval; no restart.
- Signature enforcement caught a real bug during the build: the request model declared `discount_pct`
  as float while the trained signature says integer.
- Production: CML Model Endpoints or KServe behind the API gateway, with the same alias contract.
