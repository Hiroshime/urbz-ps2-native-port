#!/usr/bin/env bash
# Sourced after urbz-env.sh. Selected profiles affect rendering only.
urbz_graphics_args() {
  local requested="${URBZ_GRAFICOS:-${URBZ_GRAPHICS_PROFILE:-}}" resolved upscaler=""
  URBZ_GAME_ARGS=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --fsr|--fsr1) upscaler=fsr1; shift ;;
      --no-fsr|--sem-fsr) upscaler=off; shift ;;
      --qhd) URBZ_GAME_ARGS+=(--window-size 2560x1440); shift ;;
      --wide) URBZ_GAME_ARGS+=(--widescreen); shift ;;
      --graficos|--graphics)
        if [[ $# -lt 2 ]]; then echo 'Informe um perfil após --graficos.' >&2; return 2; fi
        requested="$2"; shift 2 ;;
      --graficos=*|--graphics=*) requested="${1#*=}"; shift ;;
      *) URBZ_GAME_ARGS+=("$1"); shift ;;
    esac
  done
  local -a command=(python "$URBZ_ROOT/urbz-project/graphics.py" resolve)
  if [[ -n "$requested" ]]; then command+=("$requested"); fi
  resolved="$("${command[@]}")" || return 2
  local -a values
  mapfile -t values <<< "$resolved"
  if [[ "${values[1]}" != 0 ]]; then
    export PS2_SCALE="${values[1]}" PS2_LOOK="${values[2]}" PS2_SHARP_2D="${values[3]}"
    if [[ "${values[5]:--}" != - ]]; then export PS2_UPSCALER="${values[5]}"; fi
    if [[ "${values[6]:--}" != - ]]; then export PS2_WINDOW_SIZE="${values[6]}"; fi
    echo "Gráficos: ${values[4]}."
  fi
  if [[ -n "$upscaler" ]]; then export PS2_UPSCALER="$upscaler"; fi
}
