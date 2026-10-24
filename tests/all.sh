#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

output=$(mktemp -d "${TMPDIR:-/tmp}/wheely-checks-XXXXXX")
trap 'rm -rf "$output"' EXIT

node tests/check.js
for test in install desktop open-path wheelie-install wallpaper-toggle runtime files-preview \
            lock-process wheelie-lifecycle wheelie-dust; do
  printf '\nRunning %s\n' "$test"
  python3 "tests/$test.py"
done

for test in mycelium-render meadow-render lock-render tidal tidal-geometry; do
  printf '\nRunning %s\n' "$test"
  python3 "tests/$test.py" "$output/$test"
done

node tests/wheel-live.js
