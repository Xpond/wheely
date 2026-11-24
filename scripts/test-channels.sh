#!/usr/bin/env bash
# Test wheely against each Omarchy channel's packages without switching to it: the shell patches must
# apply, and every test that reads OMARCHY_PATH must pass on that channel's files.
# Usage: scripts/test-channels.sh [stable] [rc] [edge]   (all three by default)
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/shell-files.sh
cache=${XDG_CACHE_HOME:-$HOME/.cache}/wheely/channels
tests=$(grep -l OMARCHY_PATH tests/*.py tests/*.js)
failed=0

# The channel's Omarchy, its files and its menu, unpacked once per version.
fetch() {
  local channel=$1 suffix="" db pkg name files=()
  [[ $channel == edge ]] && suffix=-dev
  db=$(mktemp) || return 1
  curl -fsSL "https://pkgs.omarchy.org/$channel/x86_64/omarchy.db" -o "$db" || { rm -f "$db"; return 1; }
  for pkg in omarchy omarchy-settings; do
    files+=("$(tar -xOf "$db" --wildcards "$pkg$suffix-[0-9]*/desc" | awk '/%FILENAME%/ { getline; print }')")
  done
  rm -f "$db"
  name=${files[0]%-*.pkg.tar.zst}
  if [[ ! -d $cache/$channel/$name ]]; then
    rm -rf "${cache:?}/$channel" && mkdir -p "$cache/$channel/$name.part" || return 1
    for pkg in "${files[@]}"; do
      curl -fsSL "https://pkgs.omarchy.org/$channel/x86_64/$pkg" | tar --zstd -x -C "$cache/$channel/$name.part" usr/share/omarchy ||
        return 1
    done
    mv "$cache/$channel/$name.part" "$cache/$channel/$name"
  fi
  echo "$cache/$channel/$name"
}

channels=("$@")
(( $# )) || channels=(stable rc edge)
for channel in "${channels[@]}"; do
  tree=$(fetch "$channel") || { echo "$channel: could not fetch its packages"; failed=1; continue; }
  printf '\n%s: %s\n' "$channel" "${tree##*/}"
  omarchy=$tree/usr/share/omarchy
  for f in "${FILES[@]}"; do
    git merge-file -p "patches/shell/$f" "patches/orig/$f" "$omarchy/shell/$f" >/dev/null 2>&1 ||
      { echo "  FAIL patch does not apply: $f"; failed=1; }
  done
  out=$(mktemp -d)
  for t in $tests; do
    case $t in *.py) run=(python3 "$t" "$out/$(basename "$t" .py)") ;; *) run=(node "$t") ;; esac
    if OMARCHY_PATH=$omarchy "${run[@]}" >"$out/log" 2>&1; then echo "  ok   $t"
    else echo "  FAIL $t"; tail -n 3 "$out/log" | sed 's/^/       /'; failed=1; fi
  done
  rm -rf "$out"
done
exit $failed
