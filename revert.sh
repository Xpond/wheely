#!/bin/bash
# Remove installed plugins and put back Omarchy's own shell files where ours are installed.
set -euo pipefail
(( EUID )) || { echo "Run as your own user, not root" >&2; exit 1; }

SHELL_DIR=/usr/share/omarchy/shell
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Resolved, so a write replaces a symlink's target rather than the link.
CONF=$(realpath -m ~/.config/omarchy/shell.json)
STATE=~/.local/state/wheely
source "$REPO/scripts/shell-files.sh"

# Remove first: even a later revert failure must not reinstall on the next update.
rm -f ~/.config/omarchy/hooks/post-update.d/wheely
echo "removed post-update hook"

# An edited block is reported, not fatal: the shell files below matter more.
config_failed=0
python3 "$REPO/scripts/user-config.py" revert ~/.config/hypr/hyprland.lua "$STATE" ~/.local/bin || config_failed=1

# Unregister every plugin before unlinking any: the shell rebuilds registered plugins when their
# files change, and would load one from files that are gone.
ids=()
for p in "$REPO"/plugins/*/; do ids+=("$(basename "$p")"); done
# A missing config must not prevent restoring package files.
if [[ -f $CONF ]] && ! { jq '.plugins = [.plugins[]? | select(.id | IN($ARGS.positional[]) | not)]' "$CONF" \
                           --args "${ids[@]}" > "$CONF.new" && mv "$CONF.new" "$CONF"; }; then
  rm -f "$CONF.new"
  echo "Could not unregister ${ids[*]} from $CONF; remove them from its plugins by hand" >&2
  config_failed=1
fi
# Only our links go; a file or folder in their place is the user's.
for id in "${ids[@]}"; do
  dest=~/.config/omarchy/plugins/$id
  if [[ -L $dest ]]; then
    rm -f "$dest"
    echo "removed $id"
  elif [[ -e $dest ]]; then
    echo "Left $dest: not wheely's link" >&2
    config_failed=1
  fi
done

# Only bytes matching pacman's checksum are written, and only over files that are ours.
failed=0
stock=$(mktemp)
backup=$(mktemp -d)  # the lock files this run replaces
trap 'rm -rf "$stock" "$backup"' EXIT
clear_copies
for f in "${FILES[@]}"; do
  installed="$SHELL_DIR/$f"
  written="$STATE/installed/$f"
  if [[ -z ${SUMS[$f]-} ]]; then
    echo "Not restored: $f — no package checksum to verify stock against; left untouched" >&2
    failed=1; continue
  fi
  if ! is_stock "$f" "$installed"; then
    if ! is_ours "$f" "$installed"; then
      echo "Not restored: $f — changed outside this project; left untouched" >&2
      failed=1; continue
    fi
    if ! stock_copy "$f" "$stock"; then
      echo "Not restored: $f — no verified stock copy in patches/orig or the package cache" >&2
      failed=1; continue
    fi
    mkdir -p "$(dirname "$written")" "$(dirname "$backup/$f")"
    if [[ $f == plugins/lock/* ]] && ! cp "$installed" "$backup/$f"; then
      echo "Not restored: $f — could not back it up first" >&2
      failed=1; continue
    fi
    if ! replace "$stock" "$installed" || ! is_stock "$f" "$installed"; then
      echo "Could not restore $f; rerun revert.sh" >&2
      failed=1; continue
    fi
    echo "restored $f"
  fi
  rm -f "$written" "$STATE/rebased/orig/$f" "$STATE/rebased/shell/$f"
done
find "$STATE" -depth -type d -empty -delete 2>/dev/null || true

# The lock's view and service only load as a pair: ours beside stock cannot lock.
lock=(plugins/lock/{LockView,Service}.qml)
mixed() { is_stock "$1" "$SHELL_DIR/$1" && ! is_stock "$2" "$SHELL_DIR/$2" && is_ours "$2" "$SHELL_DIR/$2"; }
mixed_lock() { mixed "${lock[0]}" "${lock[1]}" || mixed "${lock[1]}" "${lock[0]}"; }
# A lock file left unrestored strands its partner: put back what this run replaced, from its backup.
if mixed_lock; then
  for f in "${lock[@]}"; do
    [[ -f $backup/$f ]] && ! cmp -s "$backup/$f" "$SHELL_DIR/$f" || continue
    if ! { replace "$backup/$f" "$SHELL_DIR/$f" && cmp -s "$backup/$f" "$SHELL_DIR/$f"; }; then
      echo "Could not put back $f; shell not restarted. Backups: $backup" >&2
      echo "Rerun revert.sh, or reinstall the omarchy package." >&2
      trap 'rm -f "$stock"' EXIT
      exit 1
    fi
  done
fi
# A backup covers only this run: an earlier revert stopped between the two can still leave them mixed.
if mixed_lock; then
  echo "The lock screen's two files do not match; shell not restarted." >&2
  echo "Fix what is reported above, then rerun revert.sh." >&2
  exit 1
fi

# A failed restore may leave the custom lock screen in use; keep its designs then.
if (( failed == 0 )); then
  rm -f ~/.local/share/wheely/lock-session/{Bridge.qml,shell.qml,Commons,Lock}
  rmdir ~/.local/share/wheely/lock-session 2>/dev/null || true
  rm -f ~/.local/share/wheely/lock
  rmdir ~/.local/share/wheely 2>/dev/null || true
  rm -f ~/.config/wheely/lock-design
  rmdir ~/.config/wheely 2>/dev/null || true
fi

omarchy restart shell
(( failed == 0 && config_failed == 0 ))
