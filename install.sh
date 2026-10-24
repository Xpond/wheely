#!/bin/bash
# Install plugins and rebase the shell patches onto upstream changes.
set -uo pipefail

SHELL_DIR=/usr/share/omarchy/shell
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Resolved, so a write replaces a symlink's target rather than the link.
CONF=$(realpath -m ~/.config/omarchy/shell.json)
STATE=~/.local/state/wheely
source "$REPO/scripts/shell-files.sh"

# Hook failures can scroll away, so report them on the desktop too.
alert() {
  printf '\n\e[31m%s\e[0m\n' "$1" >&2
  printf '%s\n' "${@:2}" >&2
  command -v notify-send >/dev/null && notify-send -u critical "wheely" "$1"
}

# Link the lock-screen designs before any QML can load them.
data=~/.local/share/wheely
mkdir -p "$data" && ln -sfn "$REPO/lock" "$data/lock" || { alert "Could not link the lock-screen designs"; exit 1; }
mkdir -p "$data/lock-session" &&
  ln -sfn "$REPO/lock-session/Bridge.qml" "$data/lock-session/Bridge.qml" &&
  ln -sfn "$REPO/lock-session/shell.qml" "$data/lock-session/shell.qml" &&
  ln -sfn "$SHELL_DIR/plugins/lock" "$data/lock-session/Lock" &&
  ln -sfn "$SHELL_DIR/Commons" "$data/lock-session/Commons" || { alert "Could not link the lockscreen worker"; exit 1; }

# ------------------------------------------------------------------ plugins
# Link plugins for live editing and register them idempotently via a temp file.
command -v jq >/dev/null || { alert "jq is required to register plugins"; exit 1; }
command -v python3 >/dev/null || { alert "python3 is required to manage user configuration"; exit 1; }
command -v hyprctl >/dev/null || { alert "hyprctl is required to validate user configuration"; exit 1; }
python3 "$REPO/scripts/user-config.py" install ~/.config/hypr/hyprland.lua "$STATE" ~/.local/bin ||
  { alert "Could not update the Hyprland configuration"; exit 1; }
mkdir -p ~/.config/omarchy/plugins ~/.local/bin || exit 1
if [[ ! -e $CONF ]]; then
  cp "${OMARCHY_PATH:-/usr/share/omarchy}/config/omarchy/shell.json" "$CONF" || exit 1
fi
plugins_ok=1
ids=()
for p in "$REPO"/plugins/*/; do
  id=$(basename "$p")
  if ln -sfn "${p%/}" ~/.config/omarchy/plugins/"$id" &&
     jq --arg id "$id" 'if any(.plugins[]?; .id == $id) then .
                        else .plugins = (.plugins // []) + [{id: $id}] end' \
        "$CONF" > "$CONF.new" && mv "$CONF.new" "$CONF"; then
    ids+=("$id")
  else
    plugins_ok=0
    rm -f "$CONF.new"
    alert "Could not register $id in shell.json"
  fi
done

(( ${#ids[@]} )) && echo "plugins: ${ids[*]}"

# The copied hook is a shell-quoted trampoline back to this checkout.
hook_dir=$(mktemp -d) || exit 1
printf '#!/bin/bash\nexec %q\n' "$REPO/install.sh" > "$hook_dir/wheely" &&
  omarchy hook install post-update "$hook_dir/wheely" || {
    plugins_ok=0
    alert "Could not install the post-update hook"
  }
rm -rf "$hook_dir"

# ------------------------------------------------------------------- patches
applied=()   # patch copied in
rebased=()   # patch re-based onto a new upstream version first
conflicts=() # merge failed; installed file left untouched
foreign=()   # neither stock nor ours; installed file left untouched
held=()      # lock file whose partner was left untouched; left untouched too
failed=()    # recording or installation failed
ready=()     # patch due to be copied in
declare -A from=()  # the patch each ready file gets

for f in "${FILES[@]}"; do
  installed="$SHELL_DIR/$f"
  ours="$REPO/patches/shell/$f"
  base="$REPO/patches/orig/$f"
  stock="$STATE/rebased/orig/$f"
  merged="$STATE/rebased/shell/$f"

  # A patch made for another Omarchy version is rebased onto the installed one in the state, never in
  # the checkout, so git pull keeps working. Stock is kept there for reruns once the patch covers it.
  if is_stock "$f" "$base"; then
    rm -f "$stock" "$merged"
  elif ! cmp -s "$installed" "$ours"; then
    mkdir -p "$(dirname "$stock")" "$(dirname "$merged")"
    is_stock "$f" "$installed" && cp "$installed" "$stock"
    is_stock "$f" "$stock" || stock_copy "$f" "$stock" || { rm -f "$stock"; failed+=("$f"); continue; }
    cp "$ours" "$merged" && git merge-file -q "$merged" "$base" "$stock" ||
      { rm -f "$merged"; conflicts+=("$f"); continue; }
    ours=$merged
  fi
  cmp -s "$installed" "$ours" && continue
  [[ $ours == "$merged" ]] && rebased+=("$f")

  # Stock and any version of our patch are replaced; anything else is not ours to touch.
  is_stock "$f" "$installed" || is_ours "$f" "$installed" || { foreign+=("$f"); continue; }
  from[$f]=$ours
  ready+=("$f")
done

lock_backup=
lock_written=()
if [[ " ${ready[*]}" == *" plugins/lock/"* ]]; then
  lock_backup=$(mktemp -d "$STATE/lock-backup.XXXXXX") &&
    cp "$SHELL_DIR/plugins/lock/"{LockView,Service}.qml "$lock_backup/" ||
    { rm -rf "$lock_backup"; alert "Could not back up the lock screen's files"; exit 1; }
fi

for f in "${ready[@]}"; do
  # The lock's view and service only load as a pair, so one left untouched holds back the other.
  if [[ $f == plugins/lock/* && " ${conflicts[*]} ${foreign[*]} ${failed[*]}" == *" plugins/lock/"* ]]; then
    held+=("$f"); continue
  fi
  installed="$SHELL_DIR/$f"
  ours=${from[$f]}
  written="$STATE/installed/$f"

  # Record the bytes, then mark the copy pending, so an interrupted copy is still ours.
  if ! { mkdir -p "$(dirname "$written")" && cp "$ours" "$written.new" &&
         mv "$written.new" "$written" && touch "$written.pending"; }; then
    rm -f "$written.new"
    failed+=("$f"); continue
  fi
  [[ $f == plugins/lock/* ]] && lock_written+=("$f")
  if sudo cp "$ours" "$installed" && cmp -s "$ours" "$installed" && rm -f "$written.pending"; then
    applied+=("$f")
  else
    failed+=("$f")
  fi
done

# A failed copy may have truncated its target after its partner was already installed.
if [[ " ${failed[*]}" == *" plugins/lock/"* ]]; then
  for f in "${lock_written[@]}"; do
    saved="$lock_backup/${f##*/}"
    installed="$SHELL_DIR/$f"
    written="$STATE/installed/$f"
    if ! { { cmp -s "$saved" "$installed" || sudo cp "$saved" "$installed"; } &&
           cmp -s "$saved" "$installed" && cp "$saved" "$written" && rm -f "$written.pending"; }; then
      alert "Could not restore the lock screen; shell not restarted. Backups: $lock_backup"
      exit 1
    fi
  done
  for i in "${!applied[@]}"; do
    if [[ ${applied[i]} == plugins/lock/* ]]; then
      held+=("${applied[i]}"); unset 'applied[i]'
    fi
  done
fi
[[ -z $lock_backup ]] || rm -rf "$lock_backup"

(( ${#rebased[@]} )) && printf 'rebased onto new upstream: %s\n' "${rebased[*]}"
(( ${#applied[@]} )) && printf 'installed: %s\n' "${applied[*]}"
(( ${#applied[@]} + ${#conflicts[@]} + ${#foreign[@]} + ${#failed[@]} )) || echo "already up to date"

broken=("${conflicts[@]}" "${foreign[@]}" "${held[@]}" "${failed[@]}")
if (( ${#broken[@]} )); then
  msg=("Not patched: ${broken[*]}")
  (( ${#conflicts[@]} )) && msg+=("Merge conflicted; installed files left untouched." \
                                  "Rebase by hand: diff orig/ against shell/ for: ${conflicts[*]}")
  (( ${#foreign[@]} )) && msg+=("Files changed outside this project, left untouched: ${foreign[*]}" \
                                "Reinstall the omarchy package to restore them, then rerun install.sh.")
  (( ${#held[@]} )) && msg+=("Held back so the lock screen's files stay a matching pair: ${held[*]}")
  alert "${msg[@]}"
else
  # Critical toasts outlive restarts, so archive a failed run's one as if dismissed; the restart drops it.
  notes=~/.local/state/omarchy/notifications
  for n in "$notes"/*.json; do
    jq -e '.summary == "wheely" and (.body | startswith("Not patched:"))' "$n" &>/dev/null &&
      mkdir -p "$notes/history" && mv "$n" "$notes/history/"
  done
fi

omarchy restart shell || { alert "Could not restart Omarchy shell"; exit 1; }

# Verify this shell's render thread; other Quickshell configs may have no windows.
render_ok=0
for _ in $(seq 20); do
  pid=$(quickshell list -j -p "$SHELL_DIR" | jq -r '.[0].pid // empty')
  if [[ -n $pid ]] && grep -qs QSGRenderThread /proc/"$pid"/task/*/comm; then
    render_ok=1; break
  fi
  sleep 0.5
done

(( render_ok )) || alert "Could not verify Omarchy shell's threaded render loop" \
  'Check the managed block at the end of ~/.config/hypr/hyprland.lua;' \
  'Then: hyprctl reload && omarchy restart shell'

# Fail the hook when installation or rendering failed.
(( plugins_ok == 1 && ${#broken[@]} == 0 && render_ok == 1 ))
