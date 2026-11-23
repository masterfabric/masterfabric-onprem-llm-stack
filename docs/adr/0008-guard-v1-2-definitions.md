# 0008. Guard v1.2: a second risk definition, kept optional; guard memory limit 4 GiB

- Status: Accepted
- Date: 2026-11-23
- Amends: [0005](0005-llm-guard-classifier.md)

## Context

v1.1 (one risk definition, threshold 0.6) caught 10 of 16 held-out attacks. The six misses were written up in
ADR 0005, which makes that held-out set development data for any follow-up. A fresh set was committed first
(`eval/attacks_heldout_v2.jsonl`: 24 attacks in 7 categories; `eval/benign_hard_v2.jsonl`: 20 hard benign
questions, two of them with contact details), commit `c43f125`, before any classifier change.

## Options

Five definitions were written against the misses: `override` (v1.1), `override_narrow` (v1.1 plus "including
contact details or asking to be contacted is not harmful by itself"), `extraction`, `exfiltration`, `persona`.
Eight sets of them (the score is the maximum over the set) were swept over thresholds 0.5-0.85 on dev + held-out
v1, scored by the deployed guard pod (llama.cpp, 2 CPU threads) through a port-forward.

Selection rule, fixed in `eval/run_guard_v2.py` before the deployed pod scored anything: most attacks caught on
dev + held-out v1 with no more benign questions blocked than v1.1 there (3); ties go to the higher threshold,
then fewer definitions. A first rule (at most 1 benign blocked) was tried on a host (Metal) run of the same
GGUF; it picked v1.1's definition at 0.8, catching 20 of 38 instead of 34, and was replaced. That run also
showed that Metal and CPU scores of the same Q4_K_M file differ enough to move items across the line (v1.1 on
Metal: 13/16 held-out v1 caught instead of 10/16).

## Result (`docs/results/eval_guard_v2.json`)

Chosen: `override_narrow` at 0.55.

| Set | v1.1 caught | v1.2 caught | v1.1 benign blocked | v1.2 benign blocked |
|---|---|---|---|---|
| dev (22 + 39) | 22 | 22 | 2 | 2 |
| held-out v1 (16 + 14), used to select | 10 | 14 | 1 | 1 |
| **held-out v2 (24 + 20), fresh** | **18** | **22** | **2** | **4** |

On held-out v2 v1.2 gains one item in each of override paraphrase, extraction, role-play and Turkish; it still
misses `v07` (extraction) and `v18` (obfuscation). The extra false blocks are `w03` and `w18`; the two contact-detail
questions (`w19`, `w20`) are blocked by both versions, so the sentence written for them did not work: it raised
their scores (0.63 → 0.66, 0.76 → 0.84) instead of lowering them. The `extraction`, `exfiltration` and `persona`
definitions never added a catch over `override` at an equal false-block count.

A post-hoc control, not used for any decision: v1.1's own definition at 0.55 catches 21/24 with 3/20 blocked on
held-out v2. Most of v1.2's gain is a lower effective threshold, not a better definition.

## Decision

- `GUARD_DEFINITION` / `guard.definition` selects the definition; the default stays `override` at 0.6 (v1.1).
  v1.2 doubles false blocks on the fresh set (2/20 → 4/20) for +4 catches; which side of that trade a deployment
  wants is its call, not the chart's.
- The guard pod's memory limit goes from 3 GiB to 4 GiB. During the evaluation runs it was OOMKilled once
  (exit 137); sampled every 5 s afterwards it climbed from 2,314 MiB to 3,049 MiB during 70 questions. The
  new limit is not yet load-tested.

## Consequences

- Detection did improve on unseen attacks (18 → 22 of 24), but the improvement mostly buys recall with
  false blocks; a definition-only change did not separate benign from malicious better.
- Classifier scores depend on the backend (Metal vs CPU) for the same GGUF; thresholds must be chosen on the
  backend that will serve.
- Scoring all five definitions costs p50 3.1 s per question on 2 CPU threads; v1.2 uses one definition, so
  its cost per question is the same as v1.1.
