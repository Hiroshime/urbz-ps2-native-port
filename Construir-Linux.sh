#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
source scripts/urbz-env.sh
iso="${1:-../Urbz, The - Sims in the City (Europe) (En,Fr,De,Es,It,Nl,Sv,No,Da,Fi,Pl).iso}"
if [ $# -gt 0 ]; then shift; fi
python - "$iso" <<'PY'
import hashlib, json, sys
from pathlib import Path
config = json.loads(Path('urbz-project/game.json').read_text())
image = Path(sys.argv[1])
if not image.is_file() or image.stat().st_size != config['iso_bytes']:
    sys.exit('A ISO PAL esperada não foi encontrada ou tem outro tamanho.')
with image.open('rb') as stream:
    if hashlib.file_digest(stream, 'sha256').hexdigest() != config['iso_sha256']:
        sys.exit('O hash da ISO difere da revisão usada neste projeto.')
PY
mkdir -p games/urbz-pal
if [ ! -f games/urbz-pal/entries.txt ]; then
  cp urbz-project/entries.txt games/urbz-pal/entries.txt
fi
bash scripts/port.sh urbz-pal "$iso" --native-only --no-explore "$@"
python urbz-project/apply_game_features.py
ninja -C build/native-urbz-pal -j"$PS2_JOBS" ps2run ps2padtest ps2savetest
