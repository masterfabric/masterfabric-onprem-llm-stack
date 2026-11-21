# 0001. llama.cpp serves the lab; vLLM is a chart option for GPU nodes

- Status: Accepted
- Date: 2026-11-21

## Context

The target platform serves open-weight models on-prem with vLLM on NVIDIA GPUs. The lab runs on an
Apple M4 Pro, where Docker runs in a Linux VM with **no GPU access**. Metal cannot be passed into the
VM, and vLLM's supported accelerators are CUDA, ROCm, TPU and others, with a CPU backend that targets
x86 and is not meant for production.

## Options

| Option | For | Against |
|---|---|---|
| vLLM CPU build in the cluster | Same server as production | Slow, heavy image, not representative of GPU behaviour |
| Ollama on the host (Metal) | Fast on Apple Silicon | Runs outside Kubernetes; breaks the "everything from one chart" story |
| **llama.cpp server in the cluster** | OpenAI-compatible API like vLLM (`/v1/chat/completions`, `/v1/embeddings`), continuous batching over parallel slots, GGUF quantisation, small arm64 image, Prometheus `/metrics` | CPU-only in the VM; not PagedAttention |

## Decision

The chart has `llm.backend: llamacpp | vllm`. The lab uses llama.cpp (`server-b12464`) with
Qwen2.5-1.5B-Instruct Q4_K_M, 4 parallel slots and an 8192-token shared context. The same image serves
bge-small-en-v1.5 embeddings. `values-vllm-gpu.yaml` switches to `vllm/vllm-openai` with a GPU
request, node selector and tolerations. The RAG API only talks to the OpenAI API, so it needs no change.

## Consequences

- The vLLM path is rendered and linted (`make lint`) but **not run** here. Throughput numbers in this
  repo are CPU numbers and say nothing about GPU serving. masterfabric-llm-serving-bench measures that
  separately.
