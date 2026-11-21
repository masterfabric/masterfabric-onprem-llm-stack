#!/usr/bin/env bash
# Copy the RAG corpus (READMEs and ADRs of the other MasterFabric labs) into corpus/.
# Usage: scripts/sync_corpus.sh [path containing the sibling repositories]
set -euo pipefail
SRC="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
DST="$(cd "$(dirname "$0")/.." && pwd)/corpus"
for repo in masterfabric-lakehouse-lab masterfabric-realtime-telco masterfabric-airflow-mlops; do
  mkdir -p "$DST/$repo/adr"
  cp "$SRC/$repo/README.md" "$DST/$repo/README.md"
  find "$SRC/$repo/docs/adr" -name '0*.md' -exec cp {} "$DST/$repo/adr/" \;
  ( cd "$SRC/$repo" && printf '%s %s\n' "$repo" "$(git rev-parse --short HEAD)" ) >> "$DST/.sources.tmp"
done
sort -u "$DST/.sources.tmp" > "$DST/SOURCES.txt" && rm "$DST/.sources.tmp"
echo "corpus: $(find "$DST" -name '*.md' | wc -l | tr -d ' ') markdown files"
