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
