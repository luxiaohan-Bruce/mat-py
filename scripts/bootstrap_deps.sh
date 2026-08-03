#!/usr/bin/env bash
# Clone third-party Matlab baselines into matlab/ (ignored by git).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/matlab"
cd "$ROOT/matlab"

clone_if_missing() {
  local dir="$1" url="$2"
  if [[ -d "$dir/.git" ]]; then
    echo "[skip] $dir already present"
  else
    echo "[clone] $url -> $dir"
    git clone --depth 1 "$url" "$dir"
  fi
}

clone_if_missing matpower  https://github.com/MATPOWER/matpower.git
clone_if_missing most      https://github.com/MATPOWER/most.git
clone_if_missing pglib-opf https://github.com/power-grid-lib/pglib-opf.git

echo "Done. Third-party trees under: $ROOT/matlab"
