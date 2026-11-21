# 0007. Prometheus and Grafana inside the chart, scraping by static targets

- Status: Accepted
- Date: 2026-11-21

## Decision

`monitoring.enabled` adds one Prometheus (v3.16, 2-day retention, emptyDir) and one Grafana (13.2)
to the release. Prometheus scrapes the RAG API `/metrics` and the `--metrics` endpoint of every
llama.cpp server (`llm`, `embed`, `guard`, `rerank`) by Service name. Grafana is provisioned with a
datasource and one dashboard (`charts/onprem-llm/dashboards/rag-stack.json`): request outcomes,
guardrail events by rule, latency per stage (including `guard` and `rerank`), the classifier score
histogram, and tokens/s plus busy/queued slots per model server.

## Why not the Prometheus Operator / kube-prometheus-stack

The operator brings CRDs, cluster-wide RBAC and a dozen components. This chart is meant to install
into one namespace with namespace rights only. Static targets are enough because every scrape
target is a Service the chart creates itself. A cluster that already runs the operator can turn
`monitoring.enabled` off and point its own Prometheus at the same endpoints.

## Security

- The model-server NetworkPolicies gain one extra ingress rule: pods labelled
  `onprem-llm/metrics-scraper: "true"` may reach port 8080. Only the Prometheus pod has that label.
  It does not get the `model-client` label, so it cannot reach pgvector.
- Grafana allows anonymous **Viewer** access (lab convenience). The admin password is a random
  Secret generated on first install and kept across upgrades. Neither Service is exposed on the
  ingress; use `kubectl port-forward`.
- Grafana is AGPL-3.0, the same license as this repository; it runs unmodified from the upstream
  image.

## Consequences

- Metrics are lost when the Prometheus pod restarts (emptyDir). Fine for a lab, not for production.
- llama.cpp metric names (`llamacpp:*`) are not a stable API; the dashboard may need edits after a
  llama.cpp upgrade.
