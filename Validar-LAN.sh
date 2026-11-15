#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
source scripts/urbz-env.sh
ninja -C build/native-urbz-pal -j "${PS2_JOBS}" ps2nettest
python urbz-project/test_lan_protocol.py
exec python urbz-project/test_lan_game.py "$@"
