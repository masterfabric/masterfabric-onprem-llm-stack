#!/usr/bin/env bash
# Import local images into the k3d node's containerd.
# `k3d image import` fails on multi-platform images from Docker's containerd image store
# ("content digest ... not found"); saving a single platform and importing with ctr works.
set -euo pipefail
NODE="k3d-${CLUSTER:-mf-llm}-server-0"
PLATFORM="linux/$(docker version -f '{{.Server.Arch}}')"
for img in "$@"; do
  docker save --platform "$PLATFORM" "$img" | docker exec -i "$NODE" ctr -n k8s.io images import --platform "$PLATFORM" - >/dev/null
  echo "imported $img ($PLATFORM)"
done
