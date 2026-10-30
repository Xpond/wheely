# Centered shell panels

Makes Omarchy's bar panels (Display, Audio, Network, Power…) open centered on
screen over a blurred desktop, instead of tucked against the bar edge beside
their widget. The wheel's **Centered panels** setting turns this off.

**Working:** centering, blur, Ctrl+Left/Right panel switching, the
panel-to-panel handoff, and the open/close animation.

---

## 1. How to work on this

```
orig/     upstream merge bases
shell/    patched copies, mirroring /usr/share/omarchy/shell/
```

### The constraint that shapes everything

The files being changed are **shared shell chrome**, not plugins.
`omarchy plugin clone` cannot reach them, and `/usr/share/omarchy/` is
package-owned, so **`omarchy update` overwrites them** and the shell
silently reverts to stock.

**This is self-repairing.** `omarchy update` runs `omarchy-hook
post-update` right after migrations, and `install.sh` installs a hook there
with this checkout's path baked in. Rerun `install.sh` after moving the
checkout. `revert.sh` removes the hook, so a later update cannot reinstall
the patch behind you.

The hook is a one-line trampoline into `install.sh` on purpose — `omarchy hook
install` *copies* the file, so any logic living in the hook would drift from
the repo.

**Re-applying is not just copying.** An update may ship a new version of a
patched file (4.0.2 changed `Bar.qml`: added an `omarchy.bar` IpcHandler and
`textFormat: Text.PlainText` on the tooltip). Blindly restoring our copy would
have discarded both without a word. So `install.sh` checks each installed
file against pacman's checksum for the installed package and against this
checkout's patch history:

| Installed file is | Action |
|---|---|
| `shell/` | already patched — skip |
| any recorded or committed version of our patch | our previous version — replace it |
| stock, same as `orig/` | upstream unchanged — copy the patch in |
| stock, different from `orig/` | new upstream version — **three-way merge** into `~/.local/state/wheely/rebased/`, never this checkout |
| anything else | changed outside this project — left untouched and reported |

A merge that conflicts leaves the installed file untouched, reports
it on stderr *and* via `notify-send`, and exits non-zero so the hook logs
`Hook failed`. It never writes conflict markers into a QML file — that would
break the entire shell, which is far worse than losing the patch.

Until `orig/` matches the installed package again, every run redoes the merge
from this checkout's patch, so pulled fixes still apply, and keeps the stock
file beside it for revert. To publish a clean rebase, copy its `orig/` and
`shell/` files from there into `patches/`.

The lock screen's `LockView.qml` and `Service.qml` only load as a pair (our
`Service.qml` sets properties only our `LockView.qml` has), so when either is
left untouched, the other is held back too. They are never merged: a clean merge
can still leave the lock unable to lock (our 4.0.6 `Service.qml` merges onto 4.0.5
without conflict, calling a function 4.0.5 lacks). When upstream changes either,
both stay stock, with a note, until `orig/` catches up. An Omarchy older than
`BASE` in `install.sh` is refused before anything changes.

`revert.sh` writes stock back only over files that are ours, and only bytes
matching pacman's checksum: `orig/` or a rebase's kept stock when one matches,
otherwise the file from the cached package. Anything else stays in place and
produces an error. See the [install and revert summary](../README.md#revert).

---

## 2. What changed

Eight package-owned QML files plus Hyprland config.

| File | Change |
|---|---|
| `Ui/KeyboardPanel.qml` | centred placement in `cardOrigin`, unless `[wheely] panels` is `native`; `slideX`/`originScale` transform; entry/exit animations; reports surface visibility to the bar |
| `Ui/PanelKeyCatcher.qml` | Ctrl+Left/Right → `tabRequested`; Backspace asks `xpo.wheel back` |
| `plugins/bar/Bar.qml` | `PanelScrim` — the shared blurred backdrop; `lastSwitchDirection`; `visiblePanelSurfaces` counter; carries Wheely's return across panel switches |
| `plugins/clipboard/Clipboard.qml` | Backspace past an empty filter asks `xpo.wheel back` — it rolls its own key handler instead of using `PanelKeyCatcher`; drops its own scrim for the shared one; bare Backspace cancels the clear-history confirmation |
| `plugins/lock/LockView.qml` | hosts the chosen lock-screen design from `lock/` behind a frosted password field; not panel-related, but patched through the same machinery. See [`lockscreen.md`](lockscreen.md) |
| `plugins/lock/Service.qml` | runs in its own worker process, started by `lock-session/Bridge.qml`; on successful authentication the design plays its exit before a timer releases the lock; tracks `blanked` for the wake flow |
| `services/PluginShellApi.qml` | narrow peer-panel, popout, and shared-scrim callbacks without exposing host objects |
| `shell.qml` | grants menu plugins control of enabled non-authentication UI plugins and implements the callbacks above |

`config/hyprland.lua` is the installed source of truth. It explicitly disables
blur on the wheel/files overlays, then installation reloads Hyprland and rolls
back if the block adds configuration errors. Revert removes only the managed block.

### Why the scrim lives in the bar

Panels are separate layer surfaces that unmap and remap as you tab between
them — and so are the wheel, the browser and the clipboard, which unmap and
remap as the wheel hands over to whatever you picked. A scrim inside any of
them blinks out mid-handoff and takes Hyprland's blur with it. One bar-owned
surface stays mapped across the whole interaction, and every one of those
surfaces holds a count on it (`panelSurfaceVisible`) rather than drawing its
own.

Ordering is by **Wayland layer**, not by `layer_rule`'s `order` field:

```
Overlay   omarchy-keyboard-panel   the card — opaque, stays sharp
Overlay   omarchy-wheel            the ring
Overlay   omarchy-files            the browser card
Overlay   omarchy-clipboard        the clipboard card
Top       omarchy-panel-scrim      the blurred wash, held by all of the above
Top       omarchy-bar
```

`order` was tried first and did not hold — the scrim came out above the panel
and blurred the card along with the desktop. Layer separation is a protocol
guarantee; `order` is a hint.

### Why `shell.qml` is patched: plugin capabilities

4.0.3 stopped handing plugins the host `ShellRoot`. A plugin now gets a
`services/PluginShellApi.qml` facade, closed over its own id.

Trust is decided by **which directory the plugin was scanned from**, nothing
else — `PluginRegistry.parseScanOutput` sets `__isFirstParty` from the scan
kind, and only `/usr/share/omarchy/shell/plugins` scans first-party. Our
plugins are symlinked into `~/.config/omarchy/plugins`, so they scan third
party. Symlinking them into the packaged directory instead does not work:
that scan is `find … -type f` with no `-L`, so it neither descends a
symlinked directory nor matches a symlinked file.

The wheel exists to launch *other* plugins, so the stock facade denies several
things it needs — silently, because a denied call just returns `false`:

| Call | Sandboxed result |
|---|---|
| `shell.toggle("omarchy.menu", …)` | `false` — no panel ever opens |
| `shell.summon("xpo.files", …)` | `false` — browser never opens |
| `shell.isPluginOpen(other)` / `hide(other)` | `false` — close-others and Backspace-to-wheel dead |
| shared surface reporting | absent — shared scrim never maps |
| peer-panel coordination | absent — surfaces can stack and fight for focus |

`PluginShellApi` now exposes only the missing operations as callbacks closed
over the caller's id. A plugin with kind `menu` may summon, hide, toggle, and
inspect enabled non-authentication UI plugins. Visual plugins may report one
mapped surface and claim their own popout object; the bar validates ownership.
The host closes peer panels internally, so neither its panel maps nor the live
Bar object cross the facade. Files uses the public shell IPC for its one call
back to the wheel.

`pluginShellFor` now returns the scoped facade for every third-party plugin.
No namespace or plugin id is a trust grant: an unrelated `xpo.*` manifest,
including a replacement using one of these ids, still receives only the narrow
capabilities declared by its kinds.

This is a QML capability boundary, not an OS sandbox. Plugin code still has
the Quickshell APIs available to its process.

**Keep capability checks on the original registry manifest.** Passing a
manifest through an Instantiator model role converts its arrays to QML
sequences. `Array.isArray(manifest.kinds)` then returns false, silently denying
the wheel's menu and visual capabilities. The panel loader passes the host
registry's original manifest to `pluginShellFor()` to preserve those arrays.
This fixes the missing shared blur without granting the plugin ShellRoot.

`tests/plugin_shell.py`, included in the runtime suite, exercises the actual
loader and API factory together. It checks restricted host access, menu
capabilities, backdrop counting, duplicate reports, and panel handoffs.

---

## 3. Findings worth not rediscovering

### The render loop (read this first)

**Qt renders this shell at 62Hz on a 144Hz display unless told otherwise.** On
NVIDIA + Wayland Qt falls back to the `basic` scene-graph render loop, which
advances animations from a fixed 16ms timer instead of vsync. Every animation
step is then held for 2 or 3 refreshes in an uneven 2,2,3 pattern — textbook
judder, on every panel, in both directions. Measured with a bare `qml6` app:

| `QSG_RENDER_LOOP` | median frame | implied |
|---|---|---|
| *(default)* | 15.9ms | 63Hz |
| `threaded` | **6.9ms** | **145Hz** |
| `basic` | 16.0ms | 62Hz |

The installer includes this line in its managed Hyprland block:

```lua
hl.env("QSG_RENDER_LOOP", "threaded")
```

**It must be `hl.env()` in Lua.** Writing `env = QSG_RENDER_LOOP,threaded` in
`hyprland.conf` is silently ignored — the same legacy-syntax trap as
`layerrule` below. `hyprctl configerrors` stays clean, the line looks right,
and the var is simply never exported.
(`hyprland.conf` *is* loaded — its binds work — so this is specifically the
`env` keyword, not the file.) Omarchy launches the shell from a `hyprland.start`
callback, after configuration is parsed. Installation also reloads configuration
before restarting the shell.

In-shell, that took the entry animation from ~12 rendered frames to ~44.

One side effect worth knowing: `threaded` exposes a latent binding loop in
stock `plugins/panels/power/Panel.qml` (`opened`) that `basic` never
surfaced — it appears in the journal the moment the render loop changes. It
is stock, package-owned, and not worth another patched file.

The `height` loops in `network/Panel.qml` are unrelated, intermittent, and
predate all of this work — they appear on shell starts going back well before
the prototype.

`hl.env` takes effect on `hyprctl reload` — no logout needed. Apply it with
`hyprctl reload && omarchy restart shell`.

### Verify it, don't assume it

The render thread exists only under `threaded`, so this checks the running shell rather
than its configuration; `install.sh` runs the same check after restarting the shell:

```bash
P=$(quickshell list -j -p /usr/share/omarchy/shell | jq -r '.[0].pid // empty')
grep QSGRenderThread /proc/"$P"/task/*/comm
```

### Everything else

**Omarchy 4 uses Hyprland's Lua parser.** Legacy `layerrule = blur on, …`
lines in a `.conf` file are **silently ignored** — no error, no warning,
`hyprctl configerrors` stays clean. Layer rules must go through
`hl.layer_rule({...})`.

**`hyprctl keyword` cannot set layerrules** on this parser: *"keyword can't
work with non-legacy parsers."* Edit the Lua and `hyprctl reload`.

**The scrim's rule has no `ignore_alpha`.** With one, Hyprland blurs only where
the surface is more opaque than the threshold, so a lighter scrim loses its blur
while the dim still renders — which looks exactly like a broken scrim. Without
one, the blur covers the whole surface at any alpha.

**Only the scrim surface is blurred.** Every other shell surface — the panels,
`omarchy-wheel`, `omarchy-files`, `omarchy-clipboard` — draws a card over it
and nothing behind. Blurring one of them *as well as*
the scrim is not free — it blurs an already blurred desktop a second
time inside the card, and recomputes a fullscreen blur on every frame the
wheel's ring spins.

**Every Omarchy shell layer surface sets `no_anim = true, animation = "none"`**
(see `default/hypr/apps/omarchy-shell.lua`). Without it Hyprland runs its own
fade on map/unmap, and on a *blurred* surface that means recomputing a
fullscreen blur every frame of the fade. Adding this cut the post-close churn
from 278ms to 132ms.

**Never animate the scrim's alpha,** for the same reason — one QML fade cost a
fullscreen blur recompute per frame. It snaps on, and is *held* through the
close by a timer instead.

**Qt Quick already applies transforms on the GPU.** `layer.enabled` to "avoid
re-rasterization" was based on a false premise and made things measurably
worse — it only added an FBO allocation and an extra render-to-texture pass.

**`In*` easing is wrong for a dismissal.** `InQuint` covers `0.5⁵ = 3%` of the
distance by the halfway point, so the card hangs still while the fade runs,
then jumps. Both directions want fast-start (`Out*`) curves.

---

## 4. Measuring, instead of guessing

`FrameAnimation` fires once per *rendered* frame, so buffering its `frameTime` while a
panel opens, and printing it when the animation stops, shows what the compositor actually
displayed. Drive the panel over IPC (`omarchy-shell -q omarchy.monitor open`) so runs repeat.
A healthy trace on a 144Hz display is a wall of ~6.9ms; a wall of ~16ms means the render
loop is wrong (§3), not the animation. A single large value is real latency.

---

## 5. Known limits

**Latency before the first frame**, which is sluggishness rather than judder:
monitor 152ms, bluetooth 74ms, clock 44ms, network 37ms. Only `monitor` is bad
enough to notice, and it is the 4 processes `refresh()` spawns on open. Fixing it means
deferring that work until after the entry animation, in another package-owned file.

---

## 6. Tunables

`patches/shell/Ui/KeyboardPanel.qml`:

| Knob | Value | Effect |
|---|---|---|
| `openMotionDuration` | `260` | entry length |
| `closeMotionDuration` | `150` | exit length |
| `fadeDuration` | `180` | open fade |
| `closeFadeDuration` | `130` | close fade |
| `emergeScale` | `0.96` | start scale — below ~0.9 glyph stretching becomes visible |
| `maxTravel` | `Style.space(56)` | the handoff slide distance |

`patches/shell/plugins/bar/Bar.qml`:

| Knob | Value | Effect |
|---|---|---|
| `panelScrimColor` | `Commons.Color.menu.scrim` | the one backdrop, behind panels, wheel, browser and clipboard alike |
| `panelScrimHoldMs` | `150` | **must stay >= `closeFadeDuration`** or the backdrop drops out early |

Installed blur strength comes from `config/hyprland.lua` (`size 4, passes 2`);
the wheel's **Backdrop** setting turns it off at 0% (`docs/wheel.md`, Settings).
Put personal overrides after the managed block in your main Hyprland config.
`passes` has the most effect; `passes 1` for a lighter frost.

> Two cross-file couplings, both easy to break: `panelScrimHoldMs` >=
> `closeFadeDuration`, and `bar.lastSwitchDirection` / `bar.panelSurfaceVisible()`
> are a contract `KeyboardPanel` depends on.
