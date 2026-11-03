# Lock screen: internals

Maintainer notes for [the lock screen](../lockscreen.md): writing a design, the files and
processes involved, the unlock timing, and verification.

## Writing a design

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
| `leave()` | Called when the password is accepted; the lock releases `releaseDelay` later, whatever the animation does |
| `releaseDelay` | Milliseconds from the password being accepted to the lock releasing; 1100 when absent, 550 for mycelium |
| `accent` | The field's edge colour, in the design's own light; white when absent |

Each lock or preview runs in a fresh worker, so edits
appear on its next opening. Restart the shell after adding a design to refresh the wheel's
list; neither needs `install.sh` or sudo.

## Files and installation

| File | Responsibility |
|---|---|
| `patches/shell/plugins/lock/LockView.qml` | Host: password field, wake handling, loads the chosen design |
| `patches/shell/plugins/lock/Service.qml` | PAM flow, unlock delay, display blanking, wake state and the preview |
| `lock-session/Bridge.qml` | Keeps the shell's lock IPC available and starts/reconnects the worker; if it is missing or its worker cannot start, Service.qml locks in-process |
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

## Unlock timing

Authentication stays in the stock trusted lock plugin. On success, `driveOffThenUnlock()`
sets `unlocking`, which disables input; its independent timer calls `finishUnlock()`
after the design's `releaseDelay`: 550ms for mycelium, 1100ms for the others. Each lock view binds
the interval to its design's; 1100ms remains the fallback if no view loads. The field fades out within
300ms, still reading "Checking…", so it is gone before any design finishes its exit.

## Verification

```bash
node tests/check.js
python3 tests/mycelium-render.py
python3 tests/meadow-render.py
python3 tests/lock-render.py
python3 tests/lock-process.py
python3 tests/install.py
```

`tests/check.js` runs `lock.js`, `lock-idle.js` and `mycelium.js` among its suites.

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
