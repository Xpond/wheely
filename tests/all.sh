#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

output=$(mktemp -d "${TMPDIR:-/tmp}/wheely-checks-XXXXXX")
trap 'rm -rf "$output"' EXIT

# Compiled shaders must match their sources.
compiled=$(git ls-files '*.qsb' | xargs sha256sum)
scripts/build-shaders.sh
git ls-files '*.qsb' | xargs sha256sum | diff - <(echo "$compiled")

node tests/check.js
for test in install desktop open-path wheelie-install wallpaper-toggle runtime files-preview \
            lock-process wheelie-lifecycle wheelie-dust wheelie-clock; do
  printf '\nRunning %s\n' "$test"
  python3 "tests/$test.py"
done

for test in mycelium-render meadow-render lock-render tidal tidal-geometry; do
  printf '\nRunning %s\n' "$test"
  python3 "tests/$test.py" "$output/$test"
done

node tests/wheel-live.js
