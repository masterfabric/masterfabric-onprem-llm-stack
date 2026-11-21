# 0004. One Helm chart, models fetched into PVCs, NetworkPolicies by label

- Status: Accepted
- Date: 2026-11-21

## Decision

- One chart (`charts/onprem-llm`) installs both model servers, pgvector, the API, the ingest Job and
  the ingress, so an environment is one `helm upgrade --install` with a values file.
- Model weights are not baked into images. An initContainer downloads each GGUF once into a PVC; the
  URL can point at an internal mirror (Artifactory or Nexus) for air-gapped sites, and an optional
  `sha256` pins the file.
- Only pods labelled `onprem-llm/model-client=true` (the API, the ingest Job and the load-test pod) can
  reach the model servers and the database. The ingress exposes only the API.
- The ingest Job is a post-install/upgrade hook. Readiness does not depend on it, which avoids a
  deadlock with `helm --wait` that the build actually hit.
