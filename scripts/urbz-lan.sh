#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
source scripts/urbz-env.sh
role="$1"
shift
source scripts/urbz-graphics.sh
urbz_graphics_args "$@"
set -- "${URBZ_GAME_ARGS[@]}"
if [[ "${1:-}" == --help ]]; then
  echo 'Hospedar-LAN.sh [porta] [opções do jogo]'
  echo 'Entrar-LAN.sh IPv4-do-host [porta] [opções do jogo]'
  echo 'Porta TCP padrão: 27888. URBZ_NET_DELAY define o atraso (padrão: 3 frames).'
  exit 0
fi
if [[ "$role" == host ]]; then
  port=27888
  if [[ $# -gt 0 && "$1" != --* ]]; then port="$1"; shift; fi
  peer=(--net-host "$port")
else
  if [[ $# -eq 0 || "$1" == --* ]]; then
    echo 'Uso: ./Entrar-LAN.sh IPv4-do-host [porta] [opções do jogo]' >&2
    exit 2
  fi
  address="$1"
  shift
  port=27888
  if [[ $# -gt 0 && "$1" != --* ]]; then port="$1"; shift; fi
  peer=(--net-join "$address:$port")
fi
mkdir -p "games/urbz-pal/user/lan-$role"
card="games/urbz-pal/user/lan-$role/card.ps2"
if [[ ! -e "$card" ]]; then
  python scripts/mcformat.py "$card" --date '2026-01-01 00:00:00'
fi
echo "${URBZ_NET_LABEL:-LAN}: $role, TCP $port, atraso ${URBZ_NET_DELAY:-3} frames. Use seu primeiro controle ou teclado."
echo 'O save compartilhado é o do anfitrião. Salve pelo menu do próprio jogo.'
exec build/native-urbz-pal/ps2run --disc games/urbz-pal/disc.iso --game-dir games/urbz-pal \
  --pal --language en --window --quick-dir "games/urbz-pal/user/lan-$role" \
  --net-sync-card --memcard "$card" \
  "${peer[@]}" --net-delay "${URBZ_NET_DELAY:-3}" --net-timeout-ms 300000 "$@"
