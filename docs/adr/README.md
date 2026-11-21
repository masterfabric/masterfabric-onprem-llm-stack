# Architecture decision records

| # | Decision |
|---|---|
| [0001](0001-llamacpp-in-lab-vllm-in-chart.md) | llama.cpp serves the lab; vLLM is a chart option for GPU nodes |
| [0002](0002-pgvector.md) | pgvector instead of Milvus for the retrieval store |
| [0003](0003-deterministic-guardrails.md) | Deterministic guardrails first, measured against evasions |
| [0004](0004-one-chart-networkpolicies.md) | One Helm chart, models fetched into PVCs, NetworkPolicies by label |
