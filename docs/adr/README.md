# Architecture decision records

| # | Decision |
|---|---|
| [0001](0001-llamacpp-in-lab-vllm-in-chart.md) | llama.cpp serves the lab; vLLM is a chart option for GPU nodes |
| [0002](0002-pgvector.md) | pgvector instead of Milvus for the retrieval store |
| [0003](0003-deterministic-guardrails.md) | Deterministic guardrails first, measured against evasions |
| [0004](0004-one-chart-networkpolicies.md) | One Helm chart, models fetched into PVCs, NetworkPolicies by label |
| [0005](0005-llm-guard-classifier.md) | An LLM risk classifier (Granite Guardian 3.2) behind the rules, threshold fixed before the held-out test |
| [0006](0006-cross-encoder-reranker.md) | A cross-encoder reranker, deployed but used on request |
| [0007](0007-prometheus-grafana.md) | Prometheus and Grafana inside the chart, static scrape targets |
| [0008](0008-guard-v1-2-definitions.md) | Guard v1.2 definition kept optional (more catches, more false blocks); guard memory 4 GiB |
| [0009](0009-local-judge-rag-eval.md) | RAG quality with a local Qwen2.5-7B judge, checked against string matching and by hand |
