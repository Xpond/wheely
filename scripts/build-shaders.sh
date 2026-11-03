#!/usr/bin/env bash
# Rebuild compiled shaders after GLSL changes: scripts/build-shaders.sh [shader...], or all of them.
# Each shader's .qsb lands beside it, or under $QSB_OUT at the same relative path when that is set.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

QSB=${QSB:-/usr/lib/qt6/bin/qsb}
(( $# )) || set -- $(git ls-files '*.frag' '*.vert')
for shader; do
  flags=(--qt6)
  # The tunnel's mark vertex shader is also built for scene-graph batching.
  [[ $shader == lock/tunnel/mark.vert ]] && flags+=(-b)
  out=${QSB_OUT:+$QSB_OUT/}$shader.qsb
  [[ -z ${QSB_OUT:-} ]] || mkdir -p "$(dirname "$out")"
  "$QSB" "${flags[@]}" -o "$out" "$shader"
done
