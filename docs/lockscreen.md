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
word in `~/.config/wheely/lock-design` (`wallpaper` when absent). The lock and its preview
build their view each time they show, reading that file then, so a switch needs no install or
restart.

A design that fails to load, from a syntax error or a missing folder, leaves the plain
background, and the field still unlocks. Designs are not Omarchy plugins: only this host loads them onto
the lock surface, so an installed plugin cannot draw where the password is typed.

Each design documents itself in its folder:

- [`rally`](../lock/rally/README.md): a line-art Group B rally car traced by comets, painted, then driven off on unlock.
- [`tunnel`](../lock/tunnel/README.md): the wheel's mark stacked into a corridor, flown through.
- [`mycelium`](../lock/mycelium/README.md): a colony of fine hyphae grows from the centre and draws back on unlock.
- [`shore`](../lock/shore/README.md): the wash meeting the sand from high above; unlocking brings the tide in.
- [`meadow`](../lock/meadow/README.md): wildflowers grow into “omarchy” under a starlit sunset sky.
- `wallpaper`: Omarchy's own blurred wallpaper (a video wallpaper's still poster), fading out on unlock.

## Wake and authentication

The service blanks the display after five seconds of inactivity, starting on lock and
restarting on input. After waking a blank display, a ten-second minimum allows the physical
monitor to recover: one 4K display measured about 4.2 seconds to show a picture after
DPMS returned. Input never shortens that allowance; afterward it gets the normal five seconds. A display lit by a
resume with no input is blanked again after five seconds.
These rules apply to every current and future design, regardless of animation progress.
One wake starts the animation automatically. The countdown pauses while the wake command runs,
so it cannot expire while that command is restoring the display. An in-flight blank command
finishes before a queued wake starts. Input after a quiet second runs the wake scripts;
steady typing or a moving mouse just restarts the timeout. The wake allowance is a margin,
not a signal that the physical monitor has finished waking.

## Remaining work

- Multi-monitor and fingerprint unlock still need device testing. Typing immediately
  after a wake command completes can precede the physical display becoming visible.

If the real lock gets stuck, switch to a TTY with Ctrl+Alt+F2 and log in. Run
`./revert.sh` from this checkout to restore the verified stock files, then restart
the session. Reverting from a working desktop also restarts the shell automatically.

Writing a design, the files involved, and how it is verified: [`dev/lockscreen.md`](dev/lockscreen.md).
