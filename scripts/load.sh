#!/usr/bin/env bash
# Run the k6 load test as a pod inside the cluster and store the summary in docs/results/load_k6.json.
# The pod carries the model-client label, so the NetworkPolicies let it reach the LLM server directly.
set -euo pipefail
NS=${NS:-llm}; STAGE_S=${STAGE_S:-30}; LEVELS=${LEVELS:-1,2,4,8}
cd "$(dirname "$0")/.."
kubectl -n "$NS" create configmap k6-script --from-file=load/k6-stack.js --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl -n "$NS" delete pod k6 --ignore-not-found >/dev/null
kubectl -n "$NS" run k6 --restart=Never --image=grafana/k6:latest --labels=onprem-llm/model-client=true \
  --overrides='{"spec":{"volumes":[{"name":"s","configMap":{"name":"k6-script"}}],"containers":[{"name":"k6","image":"grafana/k6:latest","args":["run","--quiet","/s/k6-stack.js"],"env":[{"name":"STAGE_S","value":"'"$STAGE_S"'"},{"name":"LEVELS","value":"'"$LEVELS"'"}],"volumeMounts":[{"name":"s","mountPath":"/s"}]}]}}' >/dev/null
kubectl -n "$NS" wait --for=jsonpath='{.status.phase}'=Succeeded pod/k6 --timeout=30m >/dev/null
mkdir -p docs/results
kubectl -n "$NS" logs k6 | sed -n '/=====K6-JSON=====/,/=====END=====/p' | sed '1d;$d' | python3 -m json.tool > docs/results/load_k6.json
kubectl -n "$NS" delete pod k6 >/dev/null
echo "wrote docs/results/load_k6.json"
