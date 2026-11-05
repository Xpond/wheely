# The wheel: internals

Maintainer notes for [the wheel](../wheel.md): the files, the comet and its scene, transitions,
traps, how search is built, and what the tests check.

## Files

    plugins/xpo.wheel/
      manifest.json    kinds: "overlay", "menu"; keepLoaded
      Wheel.qml        surface, geometry, state, and the comet
      WheelRing.qml    discs, labels, illumination and the disc mask
      RingTrack.qml    ring shader bindings
      ring.frag       antialiased circle, fading trail and disc cutouts
      WheelResults.qml the ring unrolled: the ranked list and its rail
      WheelManual.qml  the manual sheet, filtered as you type
      manual.md        the manual itself, also searched as rows
      Sky.qml          day/night palette, sun/moon positions and logo lighting
      Fluid.qml        transparent fluid ShaderEffect and its uniform interface
      fluid.frag       merging contours bent by the sun and moon (compiled to .qsb)
      QuietPoints.qml  stationary background points with three depth levels
      logo.frag        path reveal, runner light, and bevel (compiled to .qsb)
      mark.png         stroke mask, path distance, and bevel normals
      LICENSE.hyprglaze MIT notice for the adapted fluid shader
      PanelIcon.qml    a first-party panel's own mark, loaded from it
      ClickShield.qml  a surface that stops a click reaching the scrim
      MenuIndex.js     JSONC parsing, flattening, search
      MenuKeys.js      the key map: which verb a key means
      Calc.js          the calculator behind a leading `=`
      Pinned.js        the pinned search's window and focus helpers, shared with Files
      scan.py          fd's NUL-ended paths as JSON-list batches: names keep their newlines and spaces

The ring and the results take the dial as `wheel`, the way the browser's own
components take their panel, so each one's single dependency is visible at the
call site. The key maps are libraries rather than QML: they decide which verb a
key means and the dial performs it, which is what lets a test press a key.

## The comet

`ring.frag` draws the resting circle and colored trail in one antialiased
2px stroke. A live alpha mask cuts out each disc at its animated size, keeping
the track hidden beneath translucent fills. The trail has softly fading ends
and no exterior glow.

`arcHead` and `arcTail` follow the selection at different speeds. Once the effects
start, their separation sets the trail's length and lights the discs it passes.
`select()` accumulates the shortest angular delta, so crossing north
continues forward. At rest, the arc brackets the selected disc.

After four seconds of sustained spin, the trail widens to at most two thirds
of the ring and the resting circle fades out. The trail follows the same selection
head throughout; starting or ending the effects eases its length over 240ms
without moving its tip. The comet keeps the theme's accent color throughout.
Selection's emphasis fades while spinning fast, so the comet carries the motion
without the discs flashing on every key repeat.
`tests/trails.js` checks the handoff and trail length.

The dial's stroke runs through every disc's **center**, so slice labels sit
outside the ring on their own spokes rather than hung under their discs -- a
label below the east or west disc lands exactly on the arc's path. The reach
is measured to the label box's nearest edge (`|cos|·width + |sin|·height`) so
every label clears its disc by `labelGap` whatever its width and angle, and it
is measured from the disc's *grown* radius so selecting a slice does not close
the gap as the disc scales up.

## Logo and background points

After the same four-second hold, the Omarchy mark draws along its strokes over
about 2.2s, then a soft runner circles every 3s over a faint outline. Brief spins
stay quiet; release quickly fades the whole scene, even mid-draw. Closing the wheel
clears it immediately. The thin strokes have a satin finish without an offset edge
or drop shadow, lit by a grazing key light that is the `key`
uniform: it points at whichever of the sun or the moon is up (The day), so the
mark is lit from the left at dawn, overhead at noon and from the right at dusk.
The bevel normals are baked into `mark.png`'s GB channels.

`QuietPoints.qml` fills cells of roughly 100×90px with stationary, jittered points
in three sizes and brightnesses for depth, dimmer around the controls. Their soft
white stays fixed under the accent-colored comet.

## The day

The scene sits above the shared blurred-desktop scrim: `Sky.qml` draws a
translucent sky, `Fluid.qml` adds transparent contours, and `QuietPoints.qml`
draws stars above them, all fading around the controls and following
`markReveal`. `daylight` counts one day per unit, faster with charge (about 7s a
day at full spin), and never wraps, so its interpolated motion keeps moving
forward across midnight.

The sun follows an ellipse, rising on the left, overhead at noon, setting on
the right; the moon follows the same arc half a day later. `bodyPosition(side)`
places both for the radial glows and the fluid's deformation. Twilight spans
both sides of the horizon; the sky stays translucent, with noon held down for
legibility. `keyFacing` hands the logo's light from sun to moon, through frontal
light at the horizon; moonlight is blue and dimmer.

The fluid shader sums six slowly moving fields into merging contour lines, bent
around each sky light, and adds at most a faint tint between lines so the sky and
desktop blur stay visible. Stars dim in daylight and blur at twilight; their
blur layer stays allocated through the reveal so its framebuffer and shader are
not recreated twice per cycle.

The fluid shader is adapted from [slastra/hyprglaze](https://github.com/slastra/hyprglaze/blob/120c5082aba3ee2d675ed9be8f705d9239d1755c/shaders/fluid.frag).
Its MIT notice is in `plugins/xpo.wheel/LICENSE.hyprglaze`. Only the shader
math is used; the scene needs no daemon, audio capture, or window watcher.

Assets are shipped ready to load. To rebuild the shaders from the repo root
using Qt Shader Tools:

```bash
scripts/build-shaders.sh plugins/xpo.wheel/*.frag
node tests/check.js
omarchy restart shell
```

`tests/scene.js`, included by `tests/check.js`, checks the shaders' QML
uniform interfaces and the sky's arc, day/night, haze and light directions.
`tests/trails.js` checks disc-light continuity, trail length, and the eased
handoff between spinning and selection.
Render visual checks on a graphics backend: Qt's offscreen software renderer
does not reproduce the shaders and star blur.

To rebuild `mark.png`, run `python3 scripts/generate-mark.py` with NumPy and
ImageMagick available. The generator writes coverage to alpha, path distance
to R, and bevel normal XY to GB. Optional arguments, a stroke width and then
an output path, allow comparison before replacing the shipped asset.

## Transitions

One tempo, `fadeDuration`, drives the whole wheel: the open, the close, and
the ring-to-results swap.

`visible` follows `opened`. Cancellation drops `shown` and unmaps after the
130 ms fade. Executing a pick uses `close(true)` to unmap immediately, then
runs `queued` on the next tick: Hyprland must receive the unmap before the
target requests keyboard focus. This applies to apps, commands, settings
commands, window switching, file opens, copying answers, and opening a terminal
in a folder. Pinned search runs picks directly because it has no overlay to
unmap. Late input after closing, or during a cancellation fade, runs nothing.
Reopening mid-fade cancels the pending unmap and counts as a fresh open.

The saved wheel shortcut uses Hyprland's global-shortcut protocol. Its press
toggles the wheel and its release commits a flick, without spawning an IPC
client for either event. The existing shell IPC commands still work.

Typing swaps the ring for the results by fading rather than switching
`visible`: the ring draws back to 0.94 while the stack grows from
`transformOrigin: Item.Top`, pinned under the pill. Both still drop out of
`visible` once faded -- the result rows carry `MouseArea`s, so a transparent
stack would keep catching clicks meant for the ring behind it.

The results are not a card. Each row is a capsule wearing the disc's own fill
and hairline, standing on the scrim the way a disc does, one size down from the
field so the field stays the largest thing in the hole. A box holding rows is a
second surface language, and the jump from a dial of discs into one is the
thing the wheel's geometry exists to avoid. Selection is the same signature
everywhere -- accent fill, accent hairline, accent label -- on a disc, on a
bead, and on a row of the file browser.

Opening sends the selection bracket once around the ring. `spin` is a `Timer`
that steps `arcTarget` by a whole slice every 25ms for one lap. The lap draws no
streak: the trail and disc light wait for four seconds of sustained spin.
Selecting during the lap stops the timer.

The bracket shows while anything is selected or while `arcDrag` is non-zero, so
it stays up past the end of the lap for as long as the tail needs to catch up,
then fades on its own.

## Why a plugin and not a patch

Third-party plugins live in `~/.config/omarchy/plugins/<id>/` and are
discovered from a `manifest.json`. The shell injects a capability-scoped
facade into the loaded item. The wheel's `menu` kind may control enabled UI
plugins and use a detached application-library API, but it never receives the
host ShellRoot, Bar, or plugin-loader maps. Small versioned shell patches add
that facade support; the installer rebases them when Omarchy updates.

`import qs.Commons` and `import qs.Ui` resolve from a third-party plugin, so
the theme singletons (`Color`, `Style`, `Border`) and shared widgets
(`CursorSurface`, `BorderSurface`) are all available. The ring and results have
no colours of their own — they read the `[menu]` theme tokens, so they follow
theme switches for free.

## Traps

**`SUPER`+arrows never reach the client.** Hyprland binds `SUPER+↑/↓/←/→` to
"Focus on <dir> window" and consumes them before any surface sees them. The
hold-a-modifier-and-flick-with-arrows gesture is therefore impossible on a
stock Omarchy keymap; the wheel is tap-then-arrow instead. Bare arrows reach
it fine.

**The pointer-enter is a synthetic move.** When the layer surface maps, Wayland
delivers a pointer enter carrying the cursor's current position, and Qt raises
it as `onPositionChanged`. Arming selection on that means a bare tap fires
whichever slice the cursor happened to point at. The first sample is kept as an
origin and selection only arms once the pointer has travelled past a threshold.

**`omarchyPath` is injected after the component loads.** The host sets it in
the Loader's `onLoaded`, which is *after* first binding evaluation — a
`FileView` bound to it reads an empty path and fails. Default it from
`Quickshell.env("OMARCHY_PATH")` and let the injection override.

**Editing a plugin needs a shell restart.** `rescanPlugins` re-walks manifests
but QML components are cached, so changed code keeps running the old version.
Use `omarchy restart shell`.

**The wheel does not own its backdrop.** The wash and the blur behind the ring
are one scrim surface owned by the bar, which the centered panels, the browser
and the clipboard hold a count on too. The wheel takes that count when it opens
and drops it as its fade starts (`panelSurfaceVisible`), so the bar's 150 ms
hold outlasts the 130 ms fade by 20 ms. Drawing a scrim on the
wheel instead unmaps the blur along with the wheel, and the desktop snaps sharp
for the frames in between. See [`centered-panels.md`](centered-panels.md) for the scrim itself.

**`SUPER+W` must be conditional.** The wheel is a layer surface, not a window,
so a plain `killactive` with the wheel up closes whatever window sits behind
the scrim. `bin/omarchy-wheel-close` asks the wheel to close first and falls
through to close-window only when nothing of ours was on screen. It fails
*open* for a shell that is not running, which still closes the window, because
this runs on every window close. A shell that took the request but did not
answer within 0.5s is left alone: the wheel may be closing itself, and closing
the window too would take one the user never meant. A hung shell therefore
costs `SUPER+W` until it recovers.

Two things about that script are load-bearing:

**Legacy Hyprland dispatchers do nothing.** Omarchy 4's Hyprland takes Lua
dispatchers — `hyprctl` wraps the argument as `hl.dispatch(<arg>)`, so the
legacy string form is rejected at runtime and the action never happens. Same
trap as `env =` in `hyprland.conf` and `layerrule`: accepted by the tooling,
inert in practice.

`killactive` fails loudly, with a nonzero exit; use `hl.dsp.window.close()`.
Focusing a window fails *silently*: Quickshell's `HyprlandToplevel.activate()`
returns without error and focus simply does not move, because it sends
`focuswindow` under the hood. Use `hl.dsp.focus({ window = "address:0x..." })`.
Note the `0x` — Quickshell reports the address without it, and Hyprland only
matches it with one.

**A `var` reassigned an equal value still notifies.** QML compares a `string`
before notifying, but not a `var`: assigning an array or an object, even the
very same object, re-runs every binding on it. So whatever the wheel re-reads on
open is kept as raw text in a `string` (`conditionText`, `themeText`,
`lockText`…) and parsed by bindings on that, and an open whose answers have not
changed rebuilds nothing.

**Inside a `MouseArea`, `wheel` is the `MouseArea`'s.** A handler looks up a bare
name on its own object first, and every `MouseArea` has a `wheel` signal, so the
results' `wheel` property is out of reach there: `wheel.run` throws, so hovering
a row selects nothing and a click runs nothing. Those handlers say `stack.wheel`;
`python3 tests/runtime.py` hovers and clicks the real rows.

**Do not use `omarchy-shell -q` when you need the answer.** Quiet mode
suppresses stdout (`if (( !QUIET )) && [[ -n $output ]]`), so the result never
comes back and every press takes the fallback. Plain `omarchy-shell` still
writes failures to stderr, so redirecting stderr keeps the fail-open
behaviour.

## Search internals

`MenuIndex.js` reads both menu definitions —
`$OMARCHY_PATH/default/omarchy/omarchy-menu.jsonc` and
`~/.config/omarchy/extensions/omarchy-menu.jsonc` — strips JSONC comments and
trailing commas, and merges the user's over the defaults by id, as Omarchy does:
anything not an object is skipped, and an entry with a `target` opens that
menu's ring. Ids are dotted (`trigger.capture.qr`), so an entry's breadcrumb is just its ancestors' labels.
Both files are watched, as Omarchy's own menu watches them: an edit shows when
it is saved, and an entry taken out of the user's file is gone rather than
merged over.

An entry's `iconFont` is honoured. Omarchy draws its own marks — the Omarchy
logo, Codex, Cursor, Grok — from a font of its own, at codepoints a Nerd Font
fills with other glyphs, so drawn in the menu font they come out as a COBOL
logo and the like.

That invariant is checked rather than asserted. `tests/wheel-live.js` runs the real index
against this machine's real menu files:

    node tests/wheel-live.js

- every entry whose `when` passes, and that is not a submenu emptied by its
  children's, appears in `menuRows()`
- every row has an action or a node
- no node opens onto an empty ring
- every call site in the plugin names something `MenuIndex.js` defines
- the one batched script answers every `when` and `checked` the way each
  answers when asked alone
- every keybinding, read with the wheel's own command, is found by its
  description on a row that runs it

It also notes, without failing, a bar whose slices are not even on the wheel:
an odd ring has no slice at 3 or 9 o'clock.

Run it after touching `MenuIndex.js`, and against a new Omarchy release — the
menu file is upstream's, and a new entry shape is exactly what would slip
through.

Every check goes out as **one**
bash script, each line echoing `<id>:w` or `<id>:c` when its check holds.
Asked one at a time the package checks alone took over a second, so the script
asks `pacman -T` once for every package they name and answers
`omarchy-pkg-present` from that. Known readers in simple comparisons — such as
`[[ $(omarchy-default-browser) == brave ]]` — share one read. Other Bash expressions
run unchanged, preserving exit status, quoting and short-circuit guards. The script
runs in the background: the wheel opens on the last answers and the new ones
land a moment later, rebuilding only if they changed (see the trap above).

Applications come from `shell.appLibrary` (`services/AppLibrary.qml`), which
wraps Quickshell's `DesktopEntries`: it sorts, drops entries marked hidden,
resolves an icon name to a file, and launches through `uwsm-app -- gtk-launch`
so an app does not inherit the compositor's service scope.

A window row carries its address rather than its toplevel
object, so it can never go stale on a window that has
since closed, and focusing one is a `Hyprland.dispatch` — see the trap above.

Keybindings come from Omarchy's own keybindings menu (`SUPER+K`). Hyprland
reports every Lua bind as dispatcher `__lua` with an index, so `hyprctl binds`
cannot say what one does; `omarchy-menu-keybindings` recovers each command by
re-running `hyprland.lua` against a stub `hl`, and caches the result in
`~/.cache/omarchy/keybindings-<sha>.records`, keyed on `hyprctl binds`. The
wheel asks it to print, which refreshes that cache whenever the binds changed,
and reads the records on every open. A record is
`KEYS → Description<TAB>kind<TAB>arg`. An `exec` bind runs its command as a
menu row does, and a `lua` bind goes to `Hyprland.dispatch`, as window focus
does. The rest cannot run from a row: a `sendshortcut` needs its web app
focused, and a mouse bind needs the mouse.

The live half of the index — apps, windows and live panels — is rebuilt when
the wheel opens. That is the only moment any of it has to be correct, and it means
they are all as fresh as the keystroke that asked for them. The menu half is a
binding rather than a per-open rebuild: flattening the menu costs several times
what everything else costs together, and it only changes when the menu files
load or when the conditions come back. When they do come back — after the wheel
is already on screen — the ring re-reads them on its own, and `onStaticRowsChanged`
tells the index to rebuild, since that half is built by hand. The theme and font
rows are a binding of their own, `styleRows`, rebuilt the same way when a
re-read changes them.

`node tests/wheel-search.js` covers matching and ranking, including issue #1's
calculator results. `node tests/wheel-binds.js` covers reading the records and
which bindings join which rows. `node tests/wheel-conditions.js` checks the
batched script, custom Bash included; `python3 tests/runtime.py` checks live
refresh, selection and menu-file changes, and like every test that starts
Quickshell, fails on a warning it doesn't expect (`tests/qslog.py`).

Both are asked for 40, and the stack shows 8: `resultTop` is the first
row on screen and `showResult()` walks it by one whenever the selection steps
past an edge, jumping outright when the selection wraps around an end. The
`Repeater` is fed that window, so eight delegates exist however deep the list
runs. A rail beside the stack -- the same one the file browser runs beside its
list -- is what says the ninth row is there at all, and `Ctrl+Home` and
`Ctrl+End` are what reach the two ends of it without walking.

Windows' recency: Hyprland publishes a `focusHistoryID`, but only
inside each toplevel's cached IPC object, which is **not** re-fetched when
focus moves — it keeps reporting the order from whenever the list was last
pulled. `Hyprland.activeToplevel` does track focus, so the wheel accumulates
the order from that instead, and falls back to the cached history for windows
it has not yet seen focused (everything, for a moment after a shell restart).

`node tests/wheel-calc.js` pins issue #8's sums and
checks 2000 random ones against JavaScript's own arithmetic.

`tests/check.js` fails when a sigil joins `MODES` without a word in the field's
placeholder (`Search · / files · = calc`).

## Pinning, manual, memory and ring internals

`Pinned.js` hands the window to Files. Both plugins import it, and a plugin
reload reloads both, so they always share one copy; Files therefore needs the
wheel installed.

`tests/wheel-manual.js` fails when a key in this file's or Files' key tables is
missing from the manual, other than the few its two rules cover.

`tests/wheel-live.js` holds both invariants of the use counts: every counted row has a key,
and no two share one.

Every icon in `PANELS` is one the widget itself already draws. Tailscale
and Dropbox have no Nerd Font glyph — Omarchy renders each as a QML shape of
its own — so those two carry an `iconFile` and the wheel loads that component
off `omarchyPath`. There is no codepoint that stands in for a product's mark,
and picking one that looks close is how you ship a logo the product doesn't
have.

**Keep the count even.** East and west are half a turn apart, so half a turn
has to be a whole number of steps, which only happens when the count is even.
An even ring is rotated so two slices land at 3 and 9 o'clock, flanking the
field; an odd one is still evenly spaced but anchors north instead, and nothing
sits beside the field.

The catalogue is sized so the default lands even on a stock machine: the bar
Omarchy ships carries seven of these plus the clipboard overlay. Changing
`PANELS` means re-checking that.
