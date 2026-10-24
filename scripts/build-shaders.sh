#!/usr/bin/env bash
# Rebuild compiled shaders after GLSL changes: scripts/build-shaders.sh [shader...], or all of them.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

(( $# )) || set -- $(git ls-files '*.frag' '*.vert')
for shader; do
  flags=(--qt6)
  # The tunnel's mark vertex shader is also built for scene-graph batching.
  [[ $shader == lock/tunnel/mark.vert ]] && flags+=(-b)
  /usr/lib/qt6/bin/qsb "${flags[@]}" -o "$shader.qsb" "$shader"
done
