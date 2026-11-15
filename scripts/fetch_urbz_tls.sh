#!/usr/bin/env bash
# Pinned OpenSSL LTS, statically cross-compiled for the Windows prototype.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
root="$PWD"
version=3.5.9
digest=603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a
prefix="$root/tools/openssl-win"
if [[ -f "$prefix/.urbz-openssl-$version" ]]; then exit 0; fi
archive="$root/tools/openssl-$version.tar.gz"
mkdir -p tools build/openssl-win
if [[ ! -f "$archive" ]]; then
  curl -fL --retry 3 -o "$archive.tmp" "https://github.com/openssl/openssl/releases/download/openssl-$version/openssl-$version.tar.gz"
  mv "$archive.tmp" "$archive"
fi
printf '%s  %s\n' "$digest" "$archive" | sha256sum -c -
if [[ ! -d "$root/tools/openssl-$version" ]]; then tar -xzf "$archive" -C tools; fi
toolchain="$root/tools/wine-bench/linux-llvm-mingw/bin"
cd build/openssl-win
CC="$toolchain/x86_64-w64-mingw32-clang" AR="$toolchain/llvm-ar" RANLIB="$toolchain/llvm-ranlib" \
  RC="$toolchain/x86_64-w64-mingw32-windres" \
  perl "$root/tools/openssl-$version/Configure" mingw64 no-shared no-tests no-asm no-module no-legacy \
    --prefix="$prefix" --openssldir="$prefix/ssl" --libdir=lib
make -j"${PS2_JOBS:-8}" build_sw
make install_sw
touch "$prefix/.urbz-openssl-$version"
