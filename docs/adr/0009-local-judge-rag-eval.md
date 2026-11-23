# 0009. RAG quality with a local judge (RAGAS-style), checked against string matching and by hand

- Status: Accepted
- Date: 2026-11-23

## Context

Answer quality was measured by string matching an accepted fact (`eval/run_eval.py`). That says nothing about
whether an answer is grounded in what was retrieved, or whether the retrieved passages were the useful ones.
Data must stay on the machine, so a hosted judge is out.

## Decision

`eval/collect_rag.py` runs inside the API pod and records, for the 30 answerable questions, the exact contexts
the generator saw and its answer, with and without the reranker. `eval/rag_judge.py` scores them with
Qwen2.5-7B-Instruct Q4_K_M under llama.cpp on the host (temperature 0, JSON-schema output), using the RAGAS
metric definitions re-implemented with our own prompts (the `ragas` package is not a dependency): faithfulness,
answer relevancy (bge-small embeddings of judge-written questions), context precision, context recall.
The judge is checked three ways: answers paired with another question's contexts or question, agreement with
string matching, and a manual read of every negative verdict (`docs/results/rag_judge_audit.json`).

## Result (`docs/results/eval_rag_judge.json`)

| | pgvector top 4 | top 12 → reranker → top 4 |
|---|---|---|
| Faithfulness (judge) | 0.967 | 0.817 |
| Faithfulness after the manual read | 0.967 | 0.917 |
| Answer relevancy | 0.810 | 0.844 |
| Context precision | 0.650 | **0.878** |
| Context recall (judge / string match) | 0.967 / 0.933 | 1.000 / 1.000 |
| Answers correct by string match | 23/30 | 25/30 |

Judge sanity: faithfulness drops to 0.18 / 0.28 when answers are checked against another question's contexts,
and answer relevancy to 0.60 against another question. Context recall agrees with string matching on 97% and
100% of questions. Of 8 negative verdicts, 3 were wrong (claims stated verbatim in the context judged
unsupported), all on the reranked run. 360 judge calls took 610 s on the M4 Pro (Metal).

## Consequences

- The reranker's gain shows up where it should, in context precision (0.65 → 0.88), not in answers.
- The judge is useful for ranking and for finding bad answers (the circular `q05`, the wrong-question `q04`),
  but its "unsupported" verdicts need a human look: 3 of 8 were false. Relevancy separates real from swapped
  questions only modestly (0.81-0.84 vs 0.60) because all questions share one domain.
- 30 questions, one generator, one judge of the same model family as the generator (Qwen): self-preference
  bias is possible and not measured.
