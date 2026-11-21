# 0006. A cross-encoder reranker, deployed but used on request

- Status: Accepted
- Date: 2026-11-21

## Decision

Add **bge-reranker-v2-m3** (Apache-2.0, 568M parameters, GGUF Q8_0) on a llama.cpp server started
with `--reranking` (`rerank` in the chart). With reranking, the API fetches 12 candidates from
pgvector (`rerank.candidates`), drops those under `min_score`, removes chunks that carry
instructions (ADR 0003), asks the reranker for a relevance score per candidate and keeps the top 4.
If the reranker fails, the vector order is used and the response records `rerank_skipped`.

It is **off by default per request** (`rerank.default: false`); a client turns it on with
`{"rerank": true}`.

## Measurement (`docs/results/eval_rerank.json`)

The same 35 questions were asked twice through the deployed API, without and with reranking
(30 answerable, 5 unanswerable). Retrieval is scored by the rank of the first citation from the
expected document.

| | pgvector top 4 | top 12 → reranker → top 4 |
|---|---|---|
| Expected source at rank 1 (hit@1) | 0.833 (25/30) | **0.933** (28/30) |
| Expected source in top 4 (hit@4) | 0.933 (28/30) | **1.000** (30/30) |
| MRR | 0.875 | 0.961 |
| Answer accuracy | 0.800 (24/30) | 0.800 (24/30) |
| Refusal accuracy (unanswerable) | 5/5 | 5/5 |
| Rerank stage p50 / p95 | – | 3.77 s / 4.45 s |
| End-to-end p50 | 4.77 s | 8.11 s |

## Why on request and not always

Retrieval got clearly better, but the answers did not: two answers became correct (`q07`, `q29`) and
two became wrong (`q12`, `q16`), all four with the right document already at rank 1 in both runs.
The difference is which other chunks sit next to it, and the 1.5B generator is sensitive to that.
Paying 3.8 s per question (12 query–passage pairs through a 568M cross-encoder on 2 CPU threads)
for no gain in answer accuracy is not a good default on CPU. On a GPU node, or with a larger
generator that uses better context, the trade-off should be measured again.

## Consequences

- The reranker pod costs about 0.8–1.5 GiB of memory even when idle; `rerank.enabled: false`
  removes it.
- The test is small (30 answerable questions, one item = 3.3 points).
