#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
source scripts/urbz-env.sh
export PS2_BENCH_PREFIX="$PWD/tools/wine-prefix"
if [ ! -x tools/wine-bench/linux-llvm-mingw/bin/x86_64-w64-mingw32-clang++ ]; then
  bash scripts/wine-bench.sh setup
fi
bash scripts/fetch_urbz_tls.sh
exec bash scripts/wine-bench.sh build urbz-pal
