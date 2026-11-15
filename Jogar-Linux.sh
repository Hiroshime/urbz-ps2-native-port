#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
source scripts/urbz-env.sh
export PS2_NO_VU_THREAD=1 PS2_GS_SYNC_READBACK=1
source scripts/urbz-graphics.sh
urbz_graphics_args "$@"
set -- "${URBZ_GAME_ARGS[@]}"
mkdir -p games/urbz-pal/user
exec build/native-urbz-pal/ps2run --disc games/urbz-pal/disc.iso --game-dir games/urbz-pal \
  --pal --language en --window --memcard games/urbz-pal/user/card.ps2 --quick-dir games/urbz-pal/user "$@"
