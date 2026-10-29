#!/usr/bin/env bash
# Restore the corpus at the pinned commits listed in manifest.txt (≈1.8 GB).
set -euo pipefail
cd "$(dirname "$0")"
while read -r name url sha; do
  [ -z "$name" ] && continue
  if [ ! -d "$name/.git" ]; then
    git clone --filter=blob:none "$url" "$name"
  fi
  git -C "$name" fetch --depth 1 origin "$sha" 2>/dev/null || git -C "$name" fetch origin
  git -C "$name" checkout -q "$sha"
  echo "$name @ ${sha:0:7}"
done < manifest.txt
