# Package-owned shell files, sourced by install.sh and revert.sh (which set REPO and STATE).
# Pacman's checksums say what stock is; this checkout's patch history says what is ours.
PACKAGE_LOCAL=/var/lib/pacman/local
PACKAGE_CACHE=/var/cache/pacman/pkg
# Edge installs omarchy-dev in omarchy's place; the two conflict, so one is present.
PACKAGE_DB=$(ls -d "$PACKAGE_LOCAL"/omarchy{,-dev}-[0-9]* 2>/dev/null | tail -n 1) || true
FILES=(Ui/KeyboardPanel.qml Ui/PanelKeyCatcher.qml plugins/bar/Bar.qml
       plugins/clipboard/Clipboard.qml plugins/lock/LockView.qml plugins/lock/Service.qml
       services/PluginShellApi.qml shell.qml)

# Each shell file's checksum, read once: the checks below ask about the same few files again and again.
declare -A SUMS=()
[[ -z $PACKAGE_DB ]] || while read -r path sum; do SUMS[$path]=$sum; done < <(zcat "$PACKAGE_DB/mtree" |
  awk 'sub(/^\.\/usr\/share\/omarchy\/shell\//, "", $1) { for (i = 2; i <= NF; i++) if ($i ~ /^sha256digest=/) print $1, substr($i, 14) }')

is_stock() {
  local want=${SUMS[$1]-}
  [[ -n $want && -f $2 && $(sha256sum < "$2") == "$want  -" ]]
}

# A recorded install, the current patch, or any committed version of it. A run stopped partway
# needs no mark: replace() leaves the file it was replacing, or the one recorded before it ran.
is_ours() {
  cmp -s "$2" "$STATE/installed/$1" ||
    cmp -s "$2" "$REPO/patches/shell/$1" ||
    [[ -n $(git -C "$REPO" log --all -1 --format=%h --find-object="$(git hash-object "$2" 2>/dev/null)" \
            -- "patches/shell/$1" 2>/dev/null) ]]
}

# Write $1 over the shell file $2 whole: copied beside it, then renamed in, so a copy stopped partway
# never leaves a truncated file. The copy is not *.qml, so the shell never loads one left behind.
replace() {
  sudo install -m 644 "$1" "$2.wheely-new" && sudo mv -f "$2.wheely-new" "$2" ||
    { sudo rm -f "$2.wheely-new"; return 1; }
}

# A run stopped between that copy and its rename leaves the copy; clear any before writing.
clear_copies() {
  local f
  for f in "${FILES[@]}"; do
    if [[ -e $SHELL_DIR/$f.wheely-new ]]; then sudo rm -f "$SHELL_DIR/$f.wheely-new"; fi
  done
}

# Write verified stock bytes to $2: the checkout's merge base, the copy a rebase kept, else the cached package.
stock_copy() {
  local archive copy
  for copy in "$REPO/patches/orig/$1" "$STATE/rebased/orig/$1"; do
    if is_stock "$1" "$copy"; then cp "$copy" "$2"; return; fi
  done
  archive=$(ls "$PACKAGE_CACHE/${PACKAGE_DB##*/}"-*.pkg.tar.zst 2>/dev/null | head -n 1)
  [[ -n $archive ]] && bsdtar -xOf "$archive" "usr/share/omarchy/shell/$1" > "$2" 2>/dev/null &&
    is_stock "$1" "$2"
}
