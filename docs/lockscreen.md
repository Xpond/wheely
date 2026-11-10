# Lock screen

The lock screen has swappable designs. Pick one in the wheel under Style › Lockscreen
Designs (search `lockscreen`), or from a terminal with `omarchy-lock-design list`,
`current` and `set <name>`. `omarchy-shell lock preview` shows the chosen design without
locking. The next lock uses it; nothing needs reinstalling.

![The six lock designs](images/tidal/08-lock-grid.webp)

| design | |
|---|---|
| [`rally`](../lock/rally/README.md) | a line-art rally car traced by comets, painted, then driven off on unlock |
| [`tunnel`](../lock/tunnel/README.md) | the wheel's mark stacked into a corridor, flown through |
| [`mycelium`](../lock/mycelium/README.md) | fine hyphae grow from the centre and draw back on unlock |
| [`shore`](../lock/shore/README.md) | the wash meeting the sand from above; unlocking brings the tide in |
| [`meadow`](../lock/meadow/README.md) | wildflowers grow into “omarchy” under a starlit sunset |
| `wallpaper` | your blurred wallpaper (the default) |

A design that fails to load leaves a plain background, and the password field still
unlocks. The display blanks after five seconds without input, and after waking stays on
at least ten seconds so the monitor can recover.

## Known limits

- Multi-monitor and fingerprint unlock are untested.
- Typing right after a wake can start before the monitor shows a picture again.

If the real lock gets stuck, switch to a TTY with `Ctrl+Alt+F2`, log in, and run
`./revert.sh` from this checkout to restore Omarchy's own lock, then restart the session.
Lock events (locking, blanking, waking, unlocking) also go to the journal, so they survive a reboot:
`journalctl -t wheely-lock -t systemd-sleep --since yesterday`.

Writing a design, the files involved, and how it is verified:
[`dev/lockscreen.md`](dev/lockscreen.md).
