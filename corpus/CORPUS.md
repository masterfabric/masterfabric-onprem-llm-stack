# RAG corpus

The knowledge base the RAG API answers from: the README and the architecture decision records of three
other MasterFabric labs (lakehouse, realtime streaming, MLOps), copied by `scripts/sync_corpus.sh`.
`SOURCES.txt` records the commit of each source repository. All files are AGPL-3.0, like this repo.

Why this corpus: it is real technical documentation with exact, checkable facts (versions, thresholds,
measured numbers), so retrieval and answers can be scored automatically against known answers in
`eval/questions.jsonl`. It is not part of the eval if a fact is not in here.

`attack/` is **not** part of the corpus. It holds one deliberately poisoned page used by the guardrail
tests to show that retrieved text with injected instructions is filtered before it reaches the model.
