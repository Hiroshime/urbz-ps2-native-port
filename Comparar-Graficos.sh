#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
source scripts/urbz-env.sh
python urbz-project/benchmark_graphics.py "$@"
exec "${URBZ_REPORT_PYTHON:-/usr/bin/python3}" urbz-project/graphics_report.py
