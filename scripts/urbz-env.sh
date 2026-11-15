#!/usr/bin/env bash
# Local toolchain used by this prototype; source this file from any directory.
URBZ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URBZ_CLANG="$URBZ_ROOT/tools/hookshot-toolchain/usr/lib/hookshot/emsdk/upstream/bin"
if [[ -d "$URBZ_ROOT/tools/python/bin" ]]; then export PATH="$URBZ_ROOT/tools/python/bin:$PATH"; fi
if [[ -x "$URBZ_CLANG/clang++" ]]; then
  export PATH="$URBZ_CLANG:$PATH"
  export CXX="${CXX:-$URBZ_CLANG/clang++}"
fi
if [[ -f "$URBZ_ROOT/tools/sdl2/SDL2Config.cmake" ]]; then
  export CMAKE_PREFIX_PATH="$URBZ_ROOT/tools/sdl2${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
fi
export PS2_JOBS="${PS2_JOBS:-8}"
export CXXFLAGS="${CXXFLAGS:--ffp-contract=off}"
