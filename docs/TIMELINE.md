# Build timeline

How this repo was built: cluster definition, corpus, guardrails and the RAG service, the Helm chart, deployment fixes found on the running cluster (image import, readiness deadlock, chunk size), evaluation, load tests, images, ADRs and documentation.

Every step below is one commit, in order. Times are Europe/Istanbul (UTC+3).

| # | Commit | Time | Change |
|---|---|---|---|
| 1 | `1e1eb06` | 2026-11-21 03:44 | chore: scaffold repository with AGPL-3.0 license and community files |
| 2 | `f651042` | 2026-11-21 03:47 | feat(infra): add k3d cluster definition |
| 3 | `75a2b60` | 2026-11-21 03:48 | feat(corpus): add MasterFabric lab documentation as the RAG corpus |
| 4 | `c2a3e49` | 2026-11-21 03:50 | feat(guardrails): add input, context and output guardrails |
| 5 | `a420baf` | 2026-11-21 03:50 | feat(rag): add pgvector store, model clients and corpus ingestion |
| 6 | `2c4e7d5` | 2026-11-21 03:50 | feat(rag): add guarded question-answering API |
| 7 | `1580aeb` | 2026-11-21 03:50 | test(guardrails): unit tests for PII, injection, filtering and chunking |
| 8 | `567e12b` | 2026-11-21 03:52 | feat(helm): add onprem-llm chart for models, pgvector and the RAG API |
| 9 | `58932a0` | 2026-11-21 03:53 | build(make): add cluster, image, deploy, test, lint, eval and load targets |
| 10 | `25a059d` | 2026-11-21 03:54 | fix(build): import images into k3d with ctr for a single platform |
| 11 | `e3ab212` | 2026-11-21 04:01 | fix(rag): report ready before the first ingest |
| 12 | `9e9564c` | 2026-11-21 04:01 | fix(ingest): cap chunks at 800 characters for bge's 512-token window |
| 13 | `6fc39db` | 2026-11-21 04:01 | test(eval): add question set, attack set and a poisoned page |
| 14 | `5e2f555` | 2026-11-21 04:01 | feat(eval): add evaluation runner for quality and guardrails |
| 15 | `6606b7a` | 2026-11-21 04:09 | feat(rag): ask for one citation per sentence in the system prompt |
| 16 | `f22fcd5` | 2026-11-21 04:09 | fix(eval): compare the first PII value of each attack row |
| 17 | `8d22112` | 2026-11-21 04:09 | docs(results): add answer-quality evaluation, prompt v1 and v2 |
| 18 | `57522e3` | 2026-11-21 04:14 | docs(results): add guardrail evaluation |
| 19 | `79e9654` | 2026-11-21 04:14 | feat(load): add in-cluster k6 load test |
| 20 | `1db6afc` | 2026-11-21 04:15 | docs(adr): 0001 llamacpp-in-lab-vllm-in-chart |
| 21 | `664b460` | 2026-11-21 04:15 | docs(adr): 0002 pgvector |
| 22 | `7485e4b` | 2026-11-21 04:15 | docs(adr): 0003 deterministic-guardrails |
| 23 | `4d99ed5` | 2026-11-21 04:15 | docs(adr): 0004 one-chart-networkpolicies |
| 24 | `610c544` | 2026-11-21 04:15 | docs(adr): add ADR index |
| 25 | `deaa43d` | 2026-11-21 04:16 | docs(images): add architecture diagram |
| 26 | `4418e79` | 2026-11-21 04:16 | docs(contributing): add contribution guide |
| 27 | `5be6b2c` | 2026-11-21 04:21 | docs(results): add measured in-cluster k6 load test |
| 28 | `16d117c` | 2026-11-21 04:21 | docs(images): add evaluation and load-test charts |
| 29 | `3b731fb` | 2026-11-21 04:22 | docs(screenshots): add Swagger capture of a live RAG answer |
| 30 | `69605ae` | 2026-11-21 04:22 | docs(hero): add 1600x900 hero from real results |
| 31 | `4220121` | 2026-11-21 04:23 | docs(readme): full README with results, figures, chart reference and limitations |

The final commit adds this file; see `git log` for the full messages, which explain
the why of each step (including the fixes found by running the system).


## Addition: LLM guardrail classifier, reranker, Prometheus and Grafana (v1.1)

Goal: catch the paraphrase attacks the rules miss with a model-based classifier, add a reranker, and
add monitoring to the chart. Times are Europe/Istanbul (UTC+3).

| # | Commit | Time | Change |
|---|---|---|---|
| 1 | `03928ea` | 2026-11-21 11:29 | eval: held-out paraphrased attacks (16) and hard benign questions (14), fixed before the classifier is built |
| 2 | `f247198` | 2026-11-21 11:47 | feat(guard): Granite Guardian classifier client with a frozen risk definition and threshold 0.6 |
| 3 | `977148e` | 2026-11-21 11:47 | feat(rag): settings for the classifier and the reranker; /v1/rerank client |
| 4 | `bbf0f58` | 2026-11-21 11:47 | feat(rag): classifier after the rules (fail-closed), optional cross-encoder rerank of 12 candidates, /v1/guard for evaluation |
| 5 | `8df069f` | 2026-11-21 11:49 | feat(chart): guard and rerank llama.cpp servers, Prometheus and Grafana with a provisioned dashboard, scrape-only NetworkPolicy rule |
| 6 | `8544d53` | 2026-11-21 12:02 | eval: classifier scored in-cluster on dev and held-out sets (frozen definition, threshold 0.6) with threshold sweep |
| 7 | `288b16d` | 2026-11-21 12:02 | eval: reranker A/B script (same questions, rerank off vs on) |
| 8 | `c055288` | 2026-11-21 12:04 | docs(adr): 0005 LLM risk classifier, pre-declared threshold, measured results |
| 9 | `9b022b1` | 2026-11-21 12:04 | docs(adr): 0007 Prometheus and Grafana in the chart |
| 10 | `09f0445` | 2026-11-21 12:04 | eval: --tag keeps the v1.0 result files as a baseline |
| 11 | `5a2e101` | 2026-11-21 12:12 | results: reranker A/B (hit@1 0.833 -> 0.933, answer accuracy unchanged at 0.80, +3.8 s p50) |
| 12 | `e531834` | 2026-11-21 12:12 | feat: rerank only on request by default (rerank.default=false) after the A/B |
| 13 | `181742d` | 2026-11-21 12:14 | docs(adr): 0006 reranker A/B and decision, ADR index |
| 14 | `7989287` | 2026-11-21 12:14 | NOTICE: Granite Guardian, bge-reranker-v2-m3, Prometheus, Grafana licenses |
| 15 | `36cadf8` | 2026-11-21 12:15 | docs: architecture diagram with guard, rerank and monitoring |
| 16 | `ada13da` | 2026-11-21 12:15 | docs: classifier score/sweep and reranker A/B charts |
| 17 | `f73facd` | 2026-11-21 12:19 | results: v1.1 end-to-end eval with the classifier (guardrails 24/26, evasions 4/4, PII 2/4) |
| 18 | `7b090eb` | 2026-11-21 12:21 | chart: dashboard stat colours and score panel note |
| 19 | `f3687fb` | 2026-11-21 12:21 | docs: Grafana dashboard and Prometheus targets screenshots from the running cluster |
| 20 | `a2f9c27` | 2026-11-21 12:22 | make: eval-guard, eval-rerank and dashboards targets |
| 21 | `3c4bcf5` | 2026-11-21 12:23 | README: classifier, reranker and monitoring results with figures, updated limitations and quickstart |
| 22 | (this commit) | | docs(timeline): this section |

### Verification (measured on the running k3d cluster)

| Check | Result |
|---|---|
| `make test` / `make lint` (both value sets) | 13 passed / 0 charts failed |
| Pods after `helm upgrade` | llm, embed, guard, rerank, pgvector, rag, prometheus, grafana Running; ingest Job Complete (207 chunks) |
| Prometheus targets | 5/5 up (rag, llm, embed, guard, rerank) |
| Classifier, dev set (threshold 0.6 chosen here) | rules 18/22 → rules + classifier 22/22; benign blocked 0/39 → 2/39 |
| Classifier, held-out set (committed before the classifier) | rules 0/16 → 10/16; hard benign blocked 1/14 |
| Classifier latency | p50 1.17 s, p95 1.24 s (2 CPU threads) |
| `/v1/ask` guardrail suite | 22/26 → 24/26 (evasions 4/4; PII 2/4, two false positives) |
| `/v1/ask` quality with the classifier | accuracy 0.800, refusals 5/5, benign blocked 0, p50 4.92 s |
| Reranker A/B (35 questions) | hit@1 0.833 → 0.933, hit@4 0.933 → 1.000, MRR 0.875 → 0.961, answer accuracy 0.800 → 0.800, p50 4.77 → 8.11 s |

### Found while running it

- The first classifier prototype returned inverted scores: the top-logprob list has several spellings
  of each label (`Yes`, ` Yes`, `YES`) and a dict kept only the last one. Spellings are summed now and a
  unit test covers it.
- The built-in Granite Guardian `jailbreak` risk caught only 2 of the 4 dev evasions; a custom
  definition for "ignore, override or reveal your instructions" caught all 4. The definition and
  threshold were frozen before the held-out set was scored.
- The classifier blocks two PII questions ("email me at …", "call … and tell me …") as out-of-role
  requests. Reported as a regression rather than tuned away on the evaluation set.
- The reranker improved ranking but not answers, at +3.8 s on CPU; the chart now deploys it with
  `rerank.default: false` and clients opt in per request.
- Every `helm upgrade` re-runs the post-upgrade ingest hook (about 59 s of embedding); visible as embed
  spikes in Grafana.
- Grafana's default stat thresholds coloured the request counter red above 80; the dashboard now uses
  fixed colours.


## Addition: guard v1.2 on a fresh held-out set, RAG quality with a local judge (2026-11-23)

Started from `80b2a9c`. The fresh held-out sets were committed first, before any classifier change. Times are
Europe/Istanbul.

| # | Commit | Time | Change |
|---|---|---|---|
| 1 | `c43f125` | 2026-11-23 12:04 | eval: fresh held-out sets v2 (24 attacks, 20 hard benign incl. 2 with contact details), committed before any guard change |
| 2 | `c711e8b` | 2026-11-23 12:06 | guard v1.2 candidates: five risk definitions, max score; selection script with a non-regression rule |
| 3 | `5f108d1` | 2026-11-23 12:11 | guard v1.2 selection frozen on dev + heldout1 (deployed backend): override_narrow at 0.55 |
| 4 | `b7ad973` | 2026-11-23 12:14 | guard v1.2 on fresh held-out v2: 22/24 caught (v1.1 18/24), 4/20 benign blocked (v1.1 2/20) |
| 5 | `6823df9` | 2026-11-23 12:14 | api: GUARD_DEFINITION setting; default stays v1.1 'override' |
| 6 | `1608106` | 2026-11-23 12:28 | chart: guard.definition value; guard memory limit 3Gi -> 4Gi after an OOMKill at 3049Mi peak |
| 7 | `95d472d` | 2026-11-23 12:28 | rag eval: collect question, contexts and answer from inside the API pod (vector and rerank) |
| 8 | `c92b5de` | 2026-11-23 12:40 | rag eval: RAGAS-style faithfulness, relevancy, context precision/recall with a local Qwen2.5-7B judge, plus judge sanity checks |
| 9 | `2e352d9` | 2026-11-23 12:40 | rag eval: manual read of the 8 negative judge verdicts (3 wrong, all false 'unsupported') |
| 10 | `984ca6e` | 2026-11-23 12:40 | charts: guard v1.1 vs v1.2 on three sets; RAG judge metrics and sanity |
| 11 | `e691547` | 2026-11-23 12:41 | docs: ADRs 0008 (guard v1.2) and 0009 (local-judge RAG eval); Makefile eval-guard-v2, eval-rag-judge |
| 12 | `327fd92` | 2026-11-23 12:41 | Makefile: name the guard v1.2 target so make help lists it |
| 13 | `7f8f94b` | 2026-11-23 12:42 | README: guard v1.2 and RAG judge sections (figures 5-6, later figures +2), key results, ADRs 0008-0009, limitations |
| 14 | (this commit) | | docs(timeline): this section |

### Verification (measured on the M4 Pro, k3d cluster `mf-llm`)

| Check | Result |
|---|---|
| v1.1 re-scored by the deployed guard pod | held-out v1 10/16 caught, 1/14 blocked: same as the published v1.1 numbers |
| Selection (dev + held-out v1, rule fixed in code) | `override_narrow` at 0.55: 36/38 caught, 3/53 blocked (v1.1: 32/38, 3/53) |
| Fresh held-out v2 | v1.1 18/24 caught, 2/20 blocked; v1.2 22/24, 4/20 |
| Post-hoc control (not used to choose) | v1.1 definition at 0.55: 21/24, 3/20 |
| Guard pod memory | OOMKilled once (exit 137, 3 GiB limit); 2,314 → 3,049 MiB over 70 questions, sampled every 5 s |
| RAG collection | 70 runs (35 questions × vector/rerank) inside the API pod, 0 blocked in the kept run |
| RAG judge | faithfulness 0.967 / 0.817 (0.917 after a manual read), relevancy 0.810 / 0.844, context precision 0.650 / 0.878, recall 0.967 / 1.000 |
| Judge sanity | swapped contexts: faithfulness 0.178 / 0.278; swapped question: relevancy 0.604 / 0.599; recall agrees with string match on 97% / 100% |
| Judge cost | 360 calls, 610 s (Qwen2.5-7B Q4_K_M, Metal) |
| API unit tests | 13 passed (in the `mf-rag-api:dev` image); `helm lint` clean |
| Machine state | judge llama-server and port-forwards stopped; k3d `mf-llm` stopped again as found; ports 3000, 8081, 11234 not touched |

### Found while running it

- The first selection rule (at most 1 benign blocked), tried on a host Metal run of the same GGUF, chose v1.1's
  definition at 0.8 and caught 20 of 38 attacks instead of 34. It was replaced by a non-regression rule before
  the deployed pod scored anything; both are described in ADR 0008.
- Metal and CPU scores of the same Q4_K_M model differ: v1.1 catches 13/16 held-out v1 attacks on Metal and
  10/16 on the CPU pod.
- The sentence added for contact-detail questions raised their scores; `w19` and `w20` stay blocked.
- The first RAG collection was blocked from question 14 onwards: the guard pod had been OOMKilled and the API
  fails closed. The collection was repeated with memory sampling and the limit raised in the chart.
- The judge marked 3 verbatim-supported claims as unsupported, all in the reranked run.
- The repository's `.venv` was deleted by a disk clean-up outside this work while it ran (all `.venv` folders
  under `~/Documents/GitHub` at 12:21); the scripts ran from a fresh virtual environment under `/tmp`.
