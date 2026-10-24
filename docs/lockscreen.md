# Lock screen

The lock screen has swappable designs. The patched `LockView.qml` is their host: it keeps
the password field, the connection to `Service.qml` and the wake handling, and loads a
design's `Scene.qml` from this checkout's `lock/`. That is outside the shell directory the
patches replace, so a design can span any number of files. Six ship: `rally`, `tunnel`,
`mycelium`, `shore` and `meadow`, listed below, and `wallpaper`, Omarchy's own blurred wallpaper.

## Designs

In the wheel, Style › Lockscreen Designs lists the designs (search "lockscreen"); picking
one only switches to it, and the next lock shows it. From a terminal,
`omarchy-lock-design list`, `current` and `set <name>` do the same. The choice is one
word in `~/.config/wheely/lock-design` (`rally` when absent). The lock and its preview
build their view each time they show, reading that file then, so a switch needs no install or
restart.

A design is a folder in `lock/` holding a `Scene.qml`, plus whatever QML, JavaScript,
shaders and images it loads relative to itself. The scene fills the screen behind the field,
which is frosted glass: the scene blurred under a dark tint, edged in the design's accent with a
faint glow.
Every design declares `property var host`: the host sets it before the scene's bindings
run, and the log warns if it's missing. The rest is optional:

| Member | Use |
|---|---|
| `host` | The `LockView`, for state such as `backgroundPath`, `failureMessage`, `authenticatingPassword` or `passwordText.length` |
| `play()` | Called when the lock shows and automatically when wake completes |
| `hide()` | Called when the display blanks, resetting the design for its next `play()` |
| `leave()` | Called when the password is accepted; the lock releases after 550ms for mycelium or 1.1s for the other designs, whatever the animation does |
| `accent` | The field's edge colour, in the design's own light; white when absent |

A design that fails to load, from a syntax error or a missing folder, leaves the plain
background, and the field still unlocks. Each lock or preview runs in a fresh worker, so edits
appear on its next opening. Restart the shell after adding a design to refresh the wheel's
list; neither needs `install.sh` or sudo. Designs are not Omarchy plugins: only this host loads them onto
the lock surface, so an installed plugin cannot draw where the password is typed.

Each design documents itself in its folder:

- [`rally`](../lock/rally/README.md): a line-art Sport quattro S1 E2 traced by comets, painted, then driven off on unlock.
- [`tunnel`](../lock/tunnel/README.md): the wheel's mark stacked into a corridor, flown through.
- [`mycelium`](../lock/mycelium/README.md): a colony of fine hyphae grows from the centre and draws back on unlock.
- [`shore`](../lock/shore/README.md): the wash meeting the sand from high above; unlocking brings the tide in.
- [`meadow`](../lock/meadow/README.md): wildflowers grow into “omarchy” under a starlit sunset sky.
- `wallpaper`: Omarchy's own blurred wallpaper, fading out on unlock.

## Files and installation

| File | Responsibility |
|---|---|
| `patches/shell/plugins/lock/LockView.qml` | Host: password field, wake handling, loads the chosen design |
| `patches/shell/plugins/lock/Service.qml` | PAM flow, unlock delay, display blanking, wake state and the preview |
| `lock-session/Bridge.qml` | Keeps the shell's lock IPC available and starts/reconnects the worker |
| `lock-session/shell.qml` | Runs the installed authentication service and exits after unlock/wake or preview closure |
| `patches/orig/plugins/lock/` | Stock copies used by the verified install/revert workflow |
| `bin/omarchy-lock-design` | Lists the designs, names the chosen one, or sets the one the next lock shows |
| `lock/wallpaper/Scene.qml` | The wallpaper, blurred, fading out on unlock |
| `tests/lock-idle.js` | The shared five-second idle blank, the monitor wake allowance and one replay per wake |
| `tests/lock-render.py` | GPU captures, drive-off exit and design switching checks |
| `tests/lock-process.py` | Offscreen memory, process exit, shell reconnection and crash recovery; simulated compositor and authentication |

Run `./install.sh` to apply the patches. It links `lock/` to `~/.local/share/wheely/lock`
and links the worker plus the installed lock service and Commons under `lock-session/`
before updating the QML and restarting the shell, and needs no shader compiler. `./revert.sh`
restores stock files, then removes the link and the design choice only after a successful
restore, so a retained custom lock screen can still render. Installer tests cover both paths,
including failures.

The desktop shell retains only the bridge. A separate Quickshell process owns PAM and the
lock surfaces, using the same patched service, then exits after unlock and the final wake
command. This releases the renderer's native and graphics caches. The worker stays alive
while locked, including while blanked, and survives a desktop-shell restart. Only lock,
preview and hide-preview commands cross the private runtime socket; passwords stay in the worker.
Its normal startup also runs the existing stranded-lock recovery check before retiring.

## Wake and authentication

The service blanks the display after five seconds of inactivity, starting on lock and
restarting on input. After waking a blank display, a ten-second minimum allows the physical
monitor to recover: this display was measured taking about 4.2 seconds to show a picture after
DPMS returned. Input never shortens that allowance; afterward it gets the normal five seconds.
These rules apply to every current and future design, regardless of animation progress.
One wake starts the animation automatically. The countdown pauses while the wake command runs,
so it cannot expire while that command is restoring the display. An in-flight blank command
finishes before a queued wake starts. Input after a quiet second runs the wake scripts;
steady typing or a moving mouse just restarts the timeout. The wake allowance is a margin,
not a signal that the physical monitor has finished waking.

Authentication stays in the stock trusted lock plugin. On success, `driveOffThenUnlock()`
sets `unlocking`, which disables input; its independent timer calls `finishUnlock()`
after 550ms for mycelium or 1100ms for the other designs. Each lock view sets the interval from
its selected design; 1100ms remains the fallback if no view loads. The field fades out within
300ms, still reading "Checking…", so it is gone before any design finishes its exit.

## Verification

```bash
node tests/lock.js
node tests/mycelium.js
node tests/check.js
node tests/lock-idle.js
python3 tests/mycelium-render.py
python3 tests/meadow-render.py
python3 tests/lock-render.py
python3 tests/lock-process.py
python3 tests/install.py
```

Every test that starts Quickshell also fails on a warning it doesn't expect: `tests/qslog.py`
ignores only an offscreen run's notice, and a test names any it expects.

The GPU test opens a temporary preview, never a session lock. It needs a working
Wayland/OpenGL session, Quickshell and ImageMagick. Captures go to `/tmp/lock-render/`
or a directory supplied as its argument. The car is captured parked, then departed, when it
must have cleared the frame. Then the host switches to `tunnel`,
which must draw its lines; `mycelium`, whose colony 1.5s after its textures are ready must have grown about the centre with
no line beyond it, where only the dark ground shows; `shore`, whose water must fill the top edge and
sand the bottom corner wherever in the surf it opens; `meadow`, which must have grown flowers;
then `wallpaper` and a missing design. The field's top edge shows each design's accent, white
for `shore`, `wallpaper` and the missing design, which leaves the plain background. Half a second
after the password is accepted, sooner than the shortest release, only that background remains
where the field was.

`omarchy-shell lock preview` and `omarchy-shell lock hidePreview` show/hide the real
view without locking. That preview plays the entrance but does not exercise PAM,
drive-off or wake flow. For lock events, inspect the user journal for `omarchy lock`:
`display: blank`, `display: wake`, `unlock: driving off`, `unlocked`.

Use GPU captures for visual checks; SVGs miss Qt fill defects and the software
renderer has crashed on this scene. Use a timeout and file-backed Quickshell logs
so crash-handler pipes cannot hold the test open.

## Remaining work

- Multi-monitor and fingerprint unlock still need device testing. Typing immediately
  after a wake command completes can precede the physical display becoming visible.

If the real lock gets stuck, switch to a TTY with Ctrl+Alt+F2 and log in. Run
`./revert.sh` from this checkout to restore the verified stock files, then restart
the session. Reverting from a working desktop also restarts the shell automatically.
