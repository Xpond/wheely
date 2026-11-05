#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

output=$(mktemp -d "${TMPDIR:-/tmp}/wheely-checks-XXXXXX")
trap 'rm -rf "$output"' EXIT

# Compiled shaders must match their sources; built aside, so a differing qsb cannot dirty the checkout.
QSB_OUT="$output/qsb" scripts/build-shaders.sh
for shader in $(git ls-files '*.frag' '*.vert'); do
  cmp -s "$shader.qsb" "$output/qsb/$shader.qsb" ||
    { echo "$shader.qsb is stale or built by another qsb: run scripts/build-shaders.sh $shader" >&2; exit 1; }
done

node tests/check.js
for test in install desktop open-path wheelie-install wallpaper-toggle runtime files-preview files-markdown \
            lock-process wheelie-lifecycle wheelie-dust wheelie-clock theme-dpr; do
  printf '\nRunning %s\n' "$test"
  python3 "tests/$test.py"
done

for test in mycelium-render meadow-render lock-render tidal tidal-geometry; do
  printf '\nRunning %s\n' "$test"
  python3 "tests/$test.py" "$output/$test"
done

node tests/wheel-live.js
