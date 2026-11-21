# MasterFabric On-Prem LLM Stack. Run `make help` for the list of targets.
SHELL   := /bin/bash
CLUSTER := mf-llm
RELEASE := llm
NS      := llm
CHART   := charts/onprem-llm
IMAGES  := ghcr.io/ggml-org/llama.cpp:server-b12464 pgvector/pgvector:pg16 curlimages/curl:8.11.1
API     := http://127.0.0.1:48080
PY      ?= .venv/bin/python

.PHONY: help cluster image deploy status ask test lint eval load down destroy

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

load: ## k6 load tests inside the cluster -> docs/results/load_*.json
	scripts/load.sh

down: ## Uninstall the release (keeps the cluster)
	helm uninstall $(RELEASE) -n $(NS) || true

destroy: ## Delete the k3d cluster
	k3d cluster delete $(CLUSTER)
