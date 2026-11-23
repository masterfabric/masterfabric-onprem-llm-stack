# MasterFabric On-Prem LLM Stack. Run `make help` for the list of targets.
SHELL   := /bin/bash
CLUSTER := mf-llm
RELEASE := llm
NS      := llm
CHART   := charts/onprem-llm
IMAGES  := ghcr.io/ggml-org/llama.cpp:server-b12464 pgvector/pgvector:pg16 curlimages/curl:8.11.1 prom/prometheus:v3.16.0 grafana/grafana:13.2.6
API     := http://127.0.0.1:48080
PY      ?= .venv/bin/python

.PHONY: help cluster image deploy status ask test lint eval eval-guard eval-rerank eval-guard-v2 eval-rag-judge dashboards load down destroy

help: ## Show targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

cluster: ## Create the k3d cluster (single node, ingress on 127.0.0.1:48080)
	k3d cluster list $(CLUSTER) >/dev/null 2>&1 || k3d cluster create --config k3d/cluster.yaml
	kubectl config use-context k3d-$(CLUSTER)

image: ## Build the RAG API image and import it (and the pinned server images) into the cluster
	docker build -t mf-rag-api:dev -f rag/Dockerfile .
	for i in $(IMAGES); do docker image inspect $$i >/dev/null 2>&1 || docker pull -q $$i; done
	CLUSTER=$(CLUSTER) scripts/import_images.sh mf-rag-api:dev $(IMAGES)

deploy: ## helm upgrade --install; waits for the models to download and load
	helm upgrade --install $(RELEASE) $(CHART) -n $(NS) --create-namespace --wait --timeout 20m

status: ## Pods, services, PVCs and the ingest job
	kubectl -n $(NS) get pods,svc,pvc,ingress,networkpolicy,jobs

ask: ## Ask one question: make ask Q="Which object store do the labs use?"
	@curl -s $(API)/v1/ask -H 'content-type: application/json' -d "$$(jq -nc --arg q "$(Q)" '{question:$$q}')" | jq .

test: ## Guardrail and chunking unit tests (in the API image)
	docker run --rm -e PYTHONPATH=/app -w /app mf-rag-api:dev python -m pytest -q -p no:cacheprovider tests

lint: ## helm lint + render both value sets
	helm lint $(CHART) && helm lint $(CHART) -f $(CHART)/values-vllm-gpu.yaml
	helm template t $(CHART) >/dev/null && helm template t $(CHART) -f $(CHART)/values-vllm-gpu.yaml >/dev/null

eval: ## Answer-quality and guardrail evaluation through the ingress -> docs/results/
	$(PY) eval/run_eval.py --api $(API)

eval-guard: ## Rules + LLM classifier on dev and held-out sets -> docs/results/eval_classifier.json
	$(PY) eval/run_guard_eval.py --api $(API)

eval-rerank: ## Same questions with and without the reranker -> docs/results/eval_rerank.json
	$(PY) eval/run_rerank_eval.py --api $(API)

eval-guard-v2: ## Guard v1.2 candidates scored by the deployed guard pod; select on dev+heldout1, then held-out v2
	kubectl -n llm port-forward svc/llm-guard 58092:8080 >/dev/null 2>&1 & PF=$$!; sleep 3; \
	$(PY) eval/run_guard_v2.py score --url http://127.0.0.1:58092 --sets dev,heldout1 && \
	$(PY) eval/run_guard_v2.py select && \
	$(PY) eval/run_guard_v2.py score --url http://127.0.0.1:58092 --sets heldout2 && \
	$(PY) eval/run_guard_v2.py final; kill $$PF

JUDGE_MODEL ?= $(HOME)/.cache/mf-models/qwen2.5-7b-instruct-q4_k_m.gguf
eval-rag-judge: ## RAGAS-style metrics: collect in the API pod, judge with Qwen2.5-7B on the host (llama.cpp)
	kubectl -n llm exec -i deploy/llm-rag -- env QUESTIONS="$$(python3 -c 'import json;print(json.dumps([json.loads(l) for l in open("eval/questions.jsonl")]))')" python - < eval/collect_rag.py > docs/results/rag_collect.jsonl
	llama-server -m $(JUDGE_MODEL) --host 127.0.0.1 --port 58090 -c 8192 -ngl 99 >/dev/null 2>&1 & J=$$!; \
	kubectl -n llm port-forward svc/llm-embed 58093:8080 >/dev/null 2>&1 & PF=$$!; \
	for i in $$(seq 120); do curl -sf 127.0.0.1:58090/health >/dev/null && break; sleep 1; done; \
	$(PY) eval/rag_judge.py; kill $$J $$PF

dashboards: ## Port-forward Grafana to 127.0.0.1:43000 and Prometheus to 127.0.0.1:49090 (Ctrl-C to stop)
	kubectl -n $(NS) port-forward svc/$(RELEASE)-prometheus 49090:9090 & \
	kubectl -n $(NS) port-forward svc/$(RELEASE)-grafana 43000:3000

load: ## k6 load tests inside the cluster -> docs/results/load_*.json
	scripts/load.sh

down: ## Uninstall the release (keeps the cluster)
	helm uninstall $(RELEASE) -n $(NS) || true

destroy: ## Delete the k3d cluster
	k3d cluster delete $(CLUSTER)
