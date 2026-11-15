#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
role="$1"
shift
if [[ "${1:-}" == --help ]]; then
  echo 'Hospedar-Internet.sh [porta] [opções do jogo]'
  echo 'Entrar-Internet.sh IPv4-público-do-host [porta] [opções do jogo]'
  echo 'O anfitrião gera uma chave de partida. Encaminhe a porta TCP 27888 no roteador.'
  echo 'URBZ_NET_KEY permite fornecer a chave sem prompt; URBZ_NET_DELAY define o atraso (padrão: 6).'
  exit 0
fi
if [[ "$role" == join && ( $# -eq 0 || "$1" == --* ) ]]; then
  echo 'Uso: ./Entrar-Internet.sh IPv4-público-do-host [porta] [opções do jogo]' >&2
  exit 2
fi
if [[ -z "${URBZ_NET_KEY:-}" ]]; then
  if [[ "$role" == host ]]; then
    URBZ_NET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
  else
    read -r -s -p 'Chave da partida enviada pelo anfitrião: ' URBZ_NET_KEY
    echo
  fi
fi
if [[ ! "$URBZ_NET_KEY" =~ ^([[:xdigit:]]{32}|[[:xdigit:]]{64})$ ]]; then
  echo 'A chave precisa ter 32 ou 64 caracteres hexadecimais. Copie a chave inteira do anfitrião.' >&2
  exit 2
fi
export URBZ_NET_KEY
export URBZ_NET_DELAY="${URBZ_NET_DELAY:-6}"
export URBZ_NET_LABEL='Internet por IPv4'
if [[ "$role" == host ]]; then
  port=27888
  if [[ $# -gt 0 && "$1" != --* ]]; then port="$1"; shift; fi
  local_ip="$(ip -j -4 route get 1.1.1.1 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)[0].get("prefsrc",""))' 2>/dev/null || true)"
  public_ip="$(curl -4 -fsS --connect-timeout 2 --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  if [[ "$public_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "IPv4 público observado: $public_ip (a porta precisa estar encaminhada para receber conexões)."
  else
    echo 'Não foi possível consultar o IPv4 público; consulte-o no roteador ou em um serviço de consulta de IP.'
  fi
  printf 'Chave desta partida (envie ao amigo junto ao seu IPv4 público): %s\n' "$URBZ_NET_KEY"
  echo "Encaminhe TCP $port no roteador para ${local_ip:-este PC}, porta interna $port."
  exec scripts/urbz-lan.sh host "$port" --net-secure "$@"
else
  address="$1"
  shift
  port=27888
  if [[ $# -gt 0 && "$1" != --* ]]; then port="$1"; shift; fi
  exec scripts/urbz-lan.sh join "$address" "$port" --net-secure "$@"
fi
