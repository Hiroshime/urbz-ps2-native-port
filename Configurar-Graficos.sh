#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
source scripts/urbz-env.sh
exec python urbz-project/graphics.py select "$@"
