#!/usr/bin/env bash
# Sync partials, build the sections and validate the theme.
# Usage: scripts/check.sh [sealed|development]   (default: sealed, the upload rules)
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/sync_partials.py
tringify theme build .
tringify theme check . --mode "${1:-sealed}"
