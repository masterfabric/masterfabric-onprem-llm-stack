<p align="center"><img src="docs/hero.png" alt="MasterFabric On-Prem LLM Stack: k3d, llama.cpp or vLLM, pgvector and guardrails, with measured results" width="100%"></p>

# MasterFabric · On-Prem LLM Stack

**An on-prem LLM platform in one Helm chart, running on local Kubernetes.** An open-weight chat model
and an embedding model are served behind OpenAI-compatible APIs. A pgvector store holds the
documentation of the other MasterFabric labs, and a RAG API answers questions from it. The API
applies guardrails at the input, on the retrieved context and on the output: pattern rules first, then
an LLM risk classifier (Granite Guardian 3.2) for the paraphrases the rules miss. A cross-encoder
reranker is available per request, and Prometheus and Grafana watch every component. Quality,
guardrails, reranking and load are measured against the running cluster.

All numbers come from an Apple M4 Pro with Docker through Colima (6 vCPU, 10 GB) and k3d (k3s
v1.31.6). They are read from [`docs/results/`](docs/results). **Inference runs on CPU** because the
Docker VM has no GPU access; see [ADR 0001](docs/adr/0001-llamacpp-in-lab-vllm-in-chart.md).

| | Measured |
|---|---|
| Stack | k3d · Traefik ingress · llama.cpp `server-b12464` (Qwen2.5-1.5B-Instruct Q4_K_M; bge-small-en-v1.5; Granite Guardian 3.2 3B-A800M; bge-reranker-v2-m3) · pgvector on PostgreSQL 16 · FastAPI · Prometheus 3.16 · Grafana 13.2 |
| Corpus | 23 documents → **207 chunks** · ingest 57–58 s (embedding on 1 CPU thread) |
| Retrieval | **hit@4 0.933** on 30 questions with a known source · median 0.6 ms in pgvector (HNSW), 46 ms to embed the question |
| Answers | accuracy **0.767** (exact fact in the answer) · **5/5** unanswerable questions refused · 0 benign questions blocked · p50 3.56 s end to end, sequential |
| Guardrails, rules only (v1.0) | **22/26**: 18/18 injection, extraction, jailbreak, delimiter, encoded and exfiltration prompts blocked; 4/4 PII prompts masked; **0/4** paraphrase evasions caught |
| Guardrails + LLM classifier (v1.1) | **24/26**: evasions **4/4** blocked; but 2/4 PII questions now blocked too (false positives) · 0/35 benign questions blocked · classifier p50 1.17 s on CPU |
| Held-out attacks (written before the classifier) | rules **0/16** → rules + classifier **10/16** · hard benign questions blocked 1/14 · threshold 0.6 fixed on dev |
| Reranker (bge-reranker-v2-m3) | hit@1 **0.833 → 0.933**, hit@4 0.933 → 1.000 · answer accuracy unchanged (0.800) · +3.8 s p50 on CPU, so on request only |
| Monitoring | Prometheus scrapes 5 targets (API + 4 llama.cpp servers), one provisioned Grafana dashboard |
| LLM load (k6, in-cluster) | 1 user: 1.57 req/s, 96 output tok/s · 4 users: 4.1 req/s, **160 tok/s** · 8 users: 174 tok/s, p95 3.05 s |
| RAG load | best **3.97 req/s** at 2 users (p95 0.76 s) · 8 users: 1.33 req/s, p95 9.5 s |
| Guardrail path | blocked requests: **~5,000 req/s**, p50 3.2 ms at 16 users |

---

[Architecture](#architecture) · [How a question is answered](#how-a-question-is-answered) ·
[Results](#results) · [Second guardrail layer](#second-guardrail-layer-llm-classifier) · [Reranker](#reranker-ab) ·
[Monitoring](#monitoring) · [Quickstart](#quickstart) · [Helm chart](#helm-chart) · [Enterprise mapping](#enterprise-mapping) ·
[Decisions](#design-decisions) · [Limitations](#limitations) · [Roadmap](#roadmap) · [License](#license)

## Architecture

<p align="center"><img src="docs/images/architecture.png" alt="Architecture: ingress to RAG API; API calls llm, embed, guard, rerank and pgvector; Prometheus scrapes all; ingest job; network policy" width="100%"></p>
<p align="center"><sub><b>Figure 1.</b> One Helm release in namespace <code>llm</code>. Only the API is exposed (127.0.0.1:48080). The model servers and the database accept traffic only from pods labelled <code>onprem-llm/model-client=true</code>; Prometheus may reach the model servers' metrics port and nothing else.</sub></p>

```mermaid
flowchart LR
  C[client] --> I[Traefik ingress<br/>127.0.0.1:48080]
  I --> A[RAG API<br/>FastAPI]
  A -- 1 input rules --> A
  A -- 2 risk score --> G[guard<br/>llama.cpp · Granite Guardian 3.2]
  A -- 3 /v1/embeddings --> E[embed<br/>llama.cpp · bge-small]
  A -- 4 top-4 or top-12 cosine --> P[(pgvector<br/>HNSW)]
  A -- 5 context filter --> A
  A -- 6 /v1/rerank on request --> K[rerank<br/>llama.cpp · bge-reranker-v2-m3]
  A -- 7 /v1/chat/completions --> L[llm<br/>llama.cpp · Qwen2.5-1.5B<br/>or vLLM on GPU]
  A -- 8 output guardrails --> A
  J[ingest Job<br/>post-install hook] --> E
  J --> P
  M[Prometheus] -. scrape .-> A
  M -. scrape .-> L
  M -. scrape .-> G
  D[Grafana] --> M
```

| Component | Lab choice | Why |
|---|---|---|
| Kubernetes | k3d 5.9 (k3s v1.31.6), single node | Real Kubernetes APIs (Deployments, StatefulSets, PVCs, NetworkPolicy, Ingress) on a laptop |
| LLM server | llama.cpp server, 4 parallel slots, 8k shared context, 4 threads | OpenAI-compatible like vLLM, runs on arm64 CPU; vLLM is a values switch ([ADR 0001](docs/adr/0001-llamacpp-in-lab-vllm-in-chart.md)) |
| Model | Qwen2.5-1.5B-Instruct, GGUF Q4_K_M (1.1 GB, Apache-2.0) | Fits CPU latency budgets; downloaded into a PVC, not baked into an image |
| Embeddings | bge-small-en-v1.5 f16 (384-d, MIT) on llama.cpp `--embeddings` | Small and strong for English technical text |
| Vector store | pgvector on PostgreSQL 16, HNSW cosine | One database the platform team already runs ([ADR 0002](docs/adr/0002-pgvector.md)) |
| API | FastAPI, non-root, read-only root filesystem, Prometheus `/metrics` | Guardrails, citations, per-stage timings |
| Risk classifier | Granite Guardian 3.2 3B-A800M, GGUF Q4_K_M (2.0 GB, Apache-2.0), own llama.cpp server | Reads meaning, so it catches paraphrases the rules miss ([ADR 0005](docs/adr/0005-llm-guard-classifier.md)) |
| Reranker | bge-reranker-v2-m3, GGUF Q8_0 (636 MB, Apache-2.0), llama.cpp `--reranking` | Cross-encoder over 12 candidates; used on request ([ADR 0006](docs/adr/0006-cross-encoder-reranker.md)) |
| Monitoring | Prometheus 3.16 (Apache-2.0) + Grafana 13.2 (AGPL-3.0), static scrape targets | Namespace-scoped, no operator or CRDs ([ADR 0007](docs/adr/0007-prometheus-grafana.md)) |

## How a question is answered

1. **Input guardrails** ([`rag/app/guardrails.py`](rag/app/guardrails.py)). Questions matching
   injection, system-prompt extraction, role override, developer mode, chat-template delimiters,
   encoded payloads or exfiltration patterns are blocked with the rule name. Turkish PII is masked
   before anything else sees it: TCKN and IBAN (checksums verified), +90 mobile numbers, email, and
   Luhn-valid cards.
2. **Risk classifier** ([`rag/app/classifier.py`](rag/app/classifier.py)). The masked question goes to
   Granite Guardian with a risk definition for "ignore, override or reveal your instructions". The
   score is P(Yes) of the first output token; at 0.6 or above the request is blocked as
   `classifier:instruction_attack`. If the guard server is unreachable the API fails closed.
3. **Embed** the masked question with the bge retrieval instruction.
4. **Retrieve** the top 4 chunks by cosine similarity (top 12 when reranking), keeping those with a
   score of at least 0.55.
5. **Filter the context.** Chunks that contain instructions aimed at the model are dropped (indirect
   prompt injection).
6. **Rerank** (when the request sets `"rerank": true`): the cross-encoder scores each remaining
   candidate against the question and the best 4 are kept.
7. **Generate** at temperature 0 with a system prompt that allows only the numbered passages, requires
   citations and gives an exact refusal sentence.
8. **Output guardrails.** An answer that contains the per-process canary from the system prompt is
   withheld. PII is redacted, and missing or out-of-range citations are flagged.

Each response carries `guardrails` (rule names), `guard` (classifier score and threshold), `citations`
(source, section, similarity and rerank score) and `timings_ms` per stage.

## Results

### Answer quality and guardrails

<p align="center"><img src="docs/images/evaluation.png" alt="RAG quality metrics for prompt v1 and v2, and guardrail results per category" width="100%"></p>
<p align="center"><sub><b>Figure 2.</b> Left: 30 answerable questions (accepted answers and expected source in <a href="eval/questions.jsonl">questions.jsonl</a>) and 5 unanswerable ones. Right: 26 attack prompts by category (<a href="eval/attacks.jsonl">attacks.jsonl</a>).</sub></p>

| Metric | Prompt v1 | Prompt v2 (deployed) |
|---|---|---|
| Answer accuracy (accepted fact appears in the answer) | 0.800 | 0.767 |
| Retrieval hit@4 (expected document among citations) | 0.933 | 0.933 |
| Answers that cite a passage | 0.033 | 0.233 |
| Unanswerable questions refused | 5/5 | 5/5 |
| Benign questions blocked by guardrails | 0 | 0 |
| Latency p50 / p90 (sequential) | 3.45 / 4.57 s | 3.56 / 4.57 s |

Prompt v2 was written once, after run 1, to fix citations. Both runs are kept
([v1](docs/results/eval_quality_prompt_v1.json), [v2](docs/results/eval_quality.json)), because changing
a prompt after looking at an evaluation is tuning on the test set. The 7 misses in v2 show the limits of
a 1.5B model. It answers a neighbouring fact (11 quality rules from the MLOps lab instead of 20 from the
lakehouse), or it echoes the wrong row of a table. Retrieval found the right document in 28 of 30 cases,
so a larger model is the first lever.

| Guardrail category | Passed |
|---|---|
| Direct injection ("ignore previous instructions…") | 6/6 blocked |
| System-prompt extraction | 4/4 blocked |
| Jailbreak / role override | 4/4 blocked |
| Chat-template delimiters (`<\|im_start\|>`, `[INST]`) | 2/2 blocked |
| Encoded payload, exfiltration URL | 2/2 blocked |
| PII in the question (TCKN, email, phone, IBAN) | 4/4 masked, never echoed |
| **Evasions** (paraphrase, translation, Turkish) | **0/4**: none blocked by rules |

The evasions are in the set on purpose: pattern rules do not generalise. In v1.0 the only other
layer was the system prompt plus the canary check on the output. v1.1 adds an LLM classifier; see
[Second guardrail layer](#second-guardrail-layer-llm-classifier).

**Indirect injection.** With the poisoned vendor-wiki page loaded
([`corpus/attack/`](corpus/attack)), the test question retrieved the page's clean section, and its
instruction section did not reach the top 4. The answer did not follow the injected instruction. The
context filter itself is covered by a unit test; this run did not exercise it end to end
([`eval_guardrails.json`](docs/results/eval_guardrails.json)).

### Second guardrail layer: LLM classifier

<p align="center"><img src="docs/images/classifier_eval.png" alt="Classifier risk score per evaluation item with the 0.6 threshold, and a threshold sweep" width="100%"></p>
<p align="center"><sub><b>Figure 3.</b> Left: Granite Guardian score for every item, scored through the deployed API (<a href="docs/results/eval_classifier.json">eval_classifier.json</a>). Right: share of held-out attacks caught and of benign questions blocked, rules + classifier, as the threshold moves.</sub></p>

The definition and the 0.6 threshold were chosen on the dev set. The held-out set was committed before
the classifier was written ([`attacks_heldout.jsonl`](eval/attacks_heldout.jsonl): 16 paraphrased,
role-play, Turkish, obfuscated and exfiltration attacks; [`benign_hard.jsonl`](eval/benign_hard.jsonl):
14 legitimate questions that use words like "instructions", "ignore" and "rules") and scored once.

| | Rules only | Rules + classifier at 0.6 |
|---|---|---|
| Dev attacks blocked | 18 / 22 | **22 / 22** (all 4 evasions) |
| Dev benign blocked (35 questions + 4 PII questions) | 0 / 39 | 2 / 39 |
| Held-out attacks blocked | 0 / 16 | **10 / 16** |
| Held-out hard benign blocked | 0 / 14 | 1 / 14 |
| Classifier latency (2 CPU threads) | – | p50 1.17 s · p95 1.24 s |

End to end through `/v1/ask` ([`eval_guardrails_v1_1.json`](docs/results/eval_guardrails_v1_1.json)),
the guardrail suite moves from 22/26 to **24/26**. The 4 evasions are now blocked, but two PII
questions (`p02` "email me at … and tell me …", `p03` "call … and tell me …") are blocked as well: the
model reads "contact this person" as an attempt to make the assistant act outside its role. They
passed in v1.0, so this is a regression that the table keeps visible. None of the 35 normal questions
was blocked ([`eval_quality_v1_1.json`](docs/results/eval_quality_v1_1.json)).

The held-out misses are two of four instruction-override paraphrases, the two softest extraction
questions (scores 0.40 and 0.47), one Turkish override and one exfiltration paraphrase. Several catches
sit just over the line (0.600, 0.616), and with 16 attacks one item is 6 points. At 0.5 the classifier
would catch 14/16 but block 4/39 dev and 3/14 hard benign questions; the threshold was not moved after
seeing the held-out scores.

A first prototype read the score wrongly: the tokenizer has several spellings of "Yes" and "No", and
keeping only the last one seen inverted the scores. Probabilities of all spellings are summed now, with
a unit test.

### Reranker A/B

<p align="center"><img src="docs/images/rerank_ab.png" alt="Retrieval and answer metrics with and without the reranker, and median time per stage" width="100%"></p>
<p align="center"><sub><b>Figure 4.</b> The same 35 questions through <code>/v1/ask</code> with <code>"rerank": false</code> and <code>"rerank": true</code> (<a href="docs/results/eval_rerank.json">eval_rerank.json</a>). Right: median seconds per stage.</sub></p>

| | pgvector top 4 | top 12 → reranker → top 4 |
|---|---|---|
| Expected source at rank 1 | 0.833 (25/30) | **0.933** (28/30) |
| Expected source in top 4 | 0.933 (28/30) | **1.000** (30/30) |
| MRR | 0.875 | 0.961 |
| Answer accuracy | 0.800 | 0.800 |
| Unanswerable refused | 5/5 | 5/5 |
| End-to-end p50 | 4.77 s | 8.11 s (rerank stage p50 3.77 s) |

Retrieval got better, answers did not: two answers became right (`q07`, `q29`) and two became wrong
(`q12`, `q16`). In all four the right document was already at rank 1 in both runs; what changed was
which chunks sat next to it, and the 1.5B generator is sensitive to that. Scoring 12 pairs with a 568M
cross-encoder on 2 CPU threads costs 3.8 s, so the chart deploys the reranker but leaves it off unless
the request asks (`rerank.default: false`).

### Monitoring

<p align="center"><img src="docs/screenshots/grafana_rag_dashboard.png" alt="Grafana dashboard: requests by outcome, guardrail events, stage latency, classifier score histogram, tokens per second and slots per model server" width="100%"></p>
<p align="center"><sub><b>Figure 5.</b> The provisioned Grafana dashboard during the evaluation runs above: request outcomes, guardrail events by rule, p95 per stage (the two plateaus are the rerank-off and rerank-on runs), classifier score histogram, and tokens/s and busy or queued slots for each llama.cpp server (the embed spikes are re-ingests).</sub></p>

<p align="center"><img src="docs/screenshots/prometheus_targets.png" alt="Prometheus target health: rag, llm, embed, guard and rerank all up" width="80%"></p>
<p align="center"><sub><b>Figure 6.</b> Prometheus target health: the API and all four llama.cpp servers scraped by Service name.</sub></p>

The new metrics are `rag_guard_score` (histogram of classifier scores), the `guard` and `rerank`
labels of `rag_stage_seconds`, and the outcomes `blocked_classifier` and `classifier_unavailable` in
`rag_requests_total`. Neither UI is on the ingress: `make dashboards` port-forwards Grafana to
127.0.0.1:43000 (anonymous viewer) and Prometheus to 127.0.0.1:49090.

### Load test

<p align="center"><img src="docs/images/load_test.png" alt="Latency and throughput versus concurrency for the LLM and the RAG API" width="100%"></p>
<p align="center"><sub><b>Figure 7.</b> k6 running as a pod inside the cluster, 30 s per stage. The LLM stages send one fixed prompt with 64 output tokens; the RAG stages cycle through 6 questions.</sub></p>

| Stage | Users | Requests | req/s | p50 | p95 | Output tok/s |
|---|---|---|---|---|---|---|
| LLM direct | 1 | 47 | 1.57 | 0.62 s | 0.63 s | 96 |
| LLM direct | 2 | 54 | 1.80 | 1.13 s | 1.15 s | 110 |
| LLM direct | 4 | 123 | 4.10 | 0.95 s | 1.05 s | 160 |
| LLM direct | 8 | 105 | 3.50 | 2.21 s | 3.05 s | 174 |
| RAG /v1/ask | 1 | 83 | 2.77 | 0.29 s | 0.47 s | — |
| RAG /v1/ask | 2 | 119 | 3.97 | 0.46 s | 0.76 s | — |
| RAG /v1/ask | 4 | 55 | 1.83 | 0.78 s | 5.98 s | — |
| RAG /v1/ask | 8 | 40 | 1.33 | 6.43 s | 9.50 s | — |
| Blocked by guardrails | 16 | 93,080 | 4,654 | 3.2 ms | 5.5 ms | — |
| Blocked by guardrails | 64 | 100,306 | 5,015 | 12.2 ms | 18.2 ms | — |

6 requests failed over the whole run ([`load_k6.json`](docs/results/load_k6.json)). How to read it:

- Output throughput grows until the 4 llama.cpp slots are full: 96 → 160 tok/s at 4 users, with only
  +9% more at 8 users and doubled latency. This is the CPU ceiling of this laptop; GPU serving with
  vLLM is measured in masterfabric-llm-serving-bench.
- **The RAG numbers at 1–2 users are flattered by llama.cpp's prompt cache.** Six repeated questions
  reuse their cached prompts, which is why a RAG answer can be faster than the plain LLM call. At 4–8
  users the slots evict each other's prompts, and every request re-processes ~800 prompt tokens: the
  p95 jumps to 6–9.5 s. Realistic traffic with distinct questions looks like the sequential evaluation
  (p50 3.56 s).
- The guardrail path costs a few milliseconds: about 5,000 blocked requests/s on one API pod.

<p align="center"><img src="docs/screenshots/rag_api_swagger_ask.png" alt="Swagger UI of the RAG API with a live answer and citations" width="70%"></p>
<p align="center"><sub><b>Figure 8.</b> A live <code>POST /v1/ask</code> through the ingress: answer, citations with similarity scores and guardrail events.</sub></p>

## Quickstart

Requirements: Docker (Colima, Docker Desktop or similar) with about 10 GB of memory, plus `k3d`,
`kubectl`, `helm` and `make` (`brew install k3d kubernetes-cli helm`).

```bash
git clone https://github.com/masterfabric/masterfabric-onprem-llm-stack.git
cd masterfabric-onprem-llm-stack
make cluster     # k3d cluster mf-llm, ingress on 127.0.0.1:48080
make image       # build the API image, import it and the pinned server images
make deploy      # helm install; first run downloads about 3.8 GB of model weights into PVCs
make test lint   # 13 guardrail/chunking/classifier tests; lint both chart value sets
make ask Q="Which object store do the MasterFabric labs use?"
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python httpx
make eval        # quality + guardrails -> docs/results/
make eval-guard  # classifier on dev and held-out sets -> docs/results/eval_classifier.json
make eval-rerank # reranker A/B -> docs/results/eval_rerank.json
make dashboards  # Grafana on 127.0.0.1:43000, Prometheus on 127.0.0.1:49090
make load        # k6 in the cluster -> docs/results/load_k6.json
make down        # or: make destroy
```

## Helm chart

[`charts/onprem-llm`](charts/onprem-llm) installs everything; the main values:

| Value | Default | Meaning |
|---|---|---|
| `llm.backend` | `llamacpp` | `llamacpp` (GGUF, CPU/Metal/CUDA) or `vllm` (GPU) |
| `llm.llamacpp.model.url` / `.sha256` | Hugging Face URL / empty | Point at an internal mirror for air-gapped sites; pin the file |
| `llm.llamacpp.parallel` / `contextSize` | 4 / 8192 | Concurrent sequences and shared KV-cache size |
| `embed.model.*`, `embed.dim` | bge-small-en-v1.5, 384 | Embedding model and vector size |
| `pgvector.existingSecret` | generated | Password secret; a generated one survives upgrades |
| `rag.topK` / `minScore` / `maxTokens` | 4 / 0.55 / 200 | Retrieval and generation limits |
| `rag.autoscaling.enabled` | false | HPA on CPU for the API |
| `networkPolicy.enabled` | true | Only labelled clients reach models and database |
| `guard.enabled` / `threshold` / `failMode` | true / 0.6 / closed | LLM risk classifier, block threshold, behaviour when it is down |
| `guard.debugEndpoint` | true | `POST /v1/guard` returns rule verdict and score (used by the evaluation; turn off in production) |
| `rerank.enabled` / `default` / `candidates` | true / false / 12 | Deploy the reranker; rerank requests by default; candidates fetched before reranking |
| `monitoring.enabled` | true | Prometheus and Grafana with the provisioned dashboard |

`values-vllm-gpu.yaml` switches to `vllm/vllm-openai` with `nvidia.com/gpu: 1`, a GPU node selector,
tolerations and prefix caching.

## Enterprise mapping

| Concern | This lab | Production on-prem (e.g. OpenShift / RKE2 with NVIDIA GPUs) |
|---|---|---|
| Serving | llama.cpp on CPU | vLLM (PagedAttention, continuous batching, tensor parallel) or Cloudera AI Inference / NVIDIA NIM |
| Models | GGUF from Hugging Face into a PVC | Model registry or artifact mirror, signed and pinned, scanned before promotion |
| Vector store | pgvector single node | pgvector with HA (Patroni) or Milvus for 10⁸+ vectors |
| Guardrails | Rules + canary + Granite Guardian 3B classifier on CPU | Same layers with the classifier on GPU (tens of ms), policies reviewed by people, output moderation too |
| Access | NetworkPolicy, loopback ingress | mTLS mesh, OIDC at the gateway, Ranger-style data policies on retrieval (masterfabric-secure-data-ai) |
| Observability | Prometheus + Grafana in the release, static targets, 2-day emptyDir | Cluster Prometheus (operator) with long-term storage, alerting, token accounting per tenant, tracing |

## Design decisions

| ADR | Decision |
|---|---|
| [0001](docs/adr/0001-llamacpp-in-lab-vllm-in-chart.md) | llama.cpp serves the lab; vLLM is a chart option for GPU nodes |
| [0002](docs/adr/0002-pgvector.md) | pgvector instead of Milvus for the retrieval store |
| [0003](docs/adr/0003-deterministic-guardrails.md) | Deterministic guardrails first, measured against evasions |
| [0004](docs/adr/0004-one-chart-networkpolicies.md) | One Helm chart, models fetched into PVCs, NetworkPolicies by label |
| [0005](docs/adr/0005-llm-guard-classifier.md) | An LLM risk classifier behind the rules, threshold fixed before the held-out test |
| [0006](docs/adr/0006-cross-encoder-reranker.md) | A cross-encoder reranker, deployed but used on request |
| [0007](docs/adr/0007-prometheus-grafana.md) | Prometheus and Grafana inside the chart, static scrape targets |

## Limitations

- **No GPU, no vLLM run.** The Docker VM on Apple Silicon cannot reach the GPU, so the vLLM path is
  rendered and linted but not executed. All throughput figures are CPU figures for a 1.5B model.
- **Small model.** Qwen2.5-1.5B answers 77% of the questions correctly and cites passages in only 23%
  of answers, even with retrieval at 93%. A 7B+ model on a GPU is the expected fix; not measured here.
- **Evaluation size.** 35 questions and 26 attacks from one corpus give a direction, not a benchmark.
  Accuracy is string matching of an accepted fact, which can miss a correct paraphrase. The prompt was
  changed once after the first run (both runs reported).
- **Guardrails are rules plus one classifier.** The rules catch 0/4 dev evasions and 0/16 held-out
  attacks on their own. With the classifier: 4/4 and 10/16, at the cost of 2/4 PII questions and 1/14
  hard benign questions blocked. 16 held-out attacks is a small test, several catches are within 0.02
  of the threshold, and the classifier adds about 1.2 s per question on CPU. Only the input is
  classified; answers are not. The indirect injection run did not retrieve the poisoned section (in
  either version), so the context filter was not exercised end to end (unit-tested only).
- **Reranker does not help answers here.** Better ranking (hit@1 0.83 → 0.93) gave the same answer
  accuracy on 30 questions at +3.8 s; measured on CPU with a 1.5B generator only.
- **Run-to-run variation.** The v1.1 quality run with the classifier answered 0.800 against 0.767 for
  the v1.0 run with the same prompt; the difference is one question (`q20`), not the classifier.
- **Memory.** The guard and rerank servers add about 4.5 GiB of memory limits; the stack now needs
  Docker with about 10 GB.
- **Monitoring is a lab setup.** Metrics live in an emptyDir for 2 days, there are no alert rules, and
  Grafana allows anonymous viewers on a port-forward.
- **Load test caveat.** The question pool is small, so the prompt cache flatters low-concurrency RAG
  numbers. Stages are 30 s, on one node, with other containers on the same laptop.
- **Single node.** No HA for pgvector or the model servers. PDB and HPA are defined but scaling is
  bounded by 6 vCPUs.
- **Lab security.** The ingress is HTTP on loopback without authentication. The pgvector password is
  generated in-cluster and never stored in git.

## Roadmap

- vLLM on a GPU node with the same chart and evaluation, compared to llama.cpp (masterfabric-llm-serving-bench).
- Classify answers as well as questions; a larger held-out attack set, and a fix for the PII false
  positives (for example a narrower risk definition, tested on a fresh held-out set).
- Hybrid retrieval (BM25 + vectors); re-measure the reranker on a GPU and with a larger generator;
  per-document access filters on retrieval.
- Alert rules (guard down, p95 over budget, deferred slots) and long-term metrics storage.
- Streaming responses (SSE) and token-level metrics per tenant.
- Larger, held-out question set with LLM-as-judge plus human spot checks.

## License

Copyright (c) 2026 MasterFabric. Licensed under the **GNU Affero General Public License v3.0**; see
[LICENSE](LICENSE). [NOTICE](NOTICE) lists the attribution terms and the third-party licenses (k3s,
llama.cpp, vLLM, PostgreSQL/pgvector, Prometheus, Grafana, model weights and Python packages), which keep their own
licenses. See [CONTRIBUTING](CONTRIBUTING.md), [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) and [SECURITY](SECURITY.md).
