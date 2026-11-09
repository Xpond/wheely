# Installing and reverting

What `install.sh` and `revert.sh` change, how updates are handled, and why `sudo` is needed.

## Tested setup

Only Omarchy 4.5.0rc3 with Quickshell 0.3.2.r7, on one NVIDIA GPU and one monitor, without
fingerprint unlock. The installer refuses an older Omarchy and does not check Quickshell.

It takes over `SUPER+A` and `SUPER+W`, and `Ctrl+Space` while one of its animated themes is
active.

## What install changes

Run from your Omarchy session, `install.sh`:

- links `plugins/` into `~/.config/omarchy/plugins/` and registers them in
  `~/.config/omarchy/shell.json`
- appends a marked block (keybinds, layer rules, blur) to `~/.config/hypr/hyprland.lua`
- links four helpers and a shell-launch wrapper directory into `~/.local/bin`
- links the lock-screen designs in `lock/` into `~/.local/share/wheely/`
- patches eight shell files
- installs a post-update hook, and restarts the shell

A file or folder of your own where a plugin's link goes stops it before anything changes.
Rerunning is safe, and `git pull && ./install.sh` updates it. Keep the checkout where it is:
the hook, plugins and helpers point to it. Run `./revert.sh` before moving or deleting it.
If it goes missing anyway, the lock screen still locks, without its design.

The shell-launch wrapper delegates to Omarchy's own launcher with jemalloc background
purging enabled and a one-second decay time. This returns freed search pages while
the shell is idle. Existing `MALLOC_CONF` options take precedence; the setting applies
to the shell's process environment, not the whole desktop. It also turns transparent huge pages
off except where a program asks for them (kernel 6.18+), about 100 MiB less resident memory;
apps the shell launches inherit this. Its dedicated directory
precedes Omarchy on the compositor's command path without reordering other commands. Revert removes the wrapper and managed path configuration.

Video previews need `qt6-multimedia` and `qt6-multimedia-ffmpeg`
(`sudo pacman -S --needed qt6-multimedia qt6-multimedia-ffmpeg`). The fullsize button opens
native mpv, which Omarchy includes.

## Why sudo

The eight patched files live in `/usr/share/omarchy/shell`, owned by the Omarchy package.
Copying them in (install) and restoring them (revert) are the only `sudo` calls, and each
runs only when a file actually needs changing. Everything else stays in your home directory.
The `shell.qml` patch sets two environment variables for the whole shell: a threaded render loop,
and software decoding for video previews.

## Omarchy updates

Because the package owns the patched files, `omarchy update` overwrites them. The hook then
reruns `install.sh`, which merges the patches onto the new version; a conflict leaves the
shipped file as it is and is reported, on the desktop too when `notify-send` is available.
The lock screen's two files are never merged: when an update changes either, both stay
Omarchy's own until wheely is updated for it (`git pull && ./install.sh`).

## Revert

`./revert.sh` removes the hook, plugins, Hyprland block and helper links, puts back Omarchy's
original shell files, and unlinks the lock-screen designs and forgets the chosen one after a
successful restore, then restarts the shell. It also works from a TTY or over SSH when the
desktop will not start.

Originals are checked against pacman's checksums before they are written, and a shell file
changed outside this project is left untouched and reported. If restoring fails, revert says
so and never restarts the shell into a lock screen whose two files do not match.

## What stays after revert

Your settings stay, so a reinstall starts where you left off:

- `wheel.json`, `wheel-blur`, `wheel-shortcut` and `wallpaper-pause-shortcut` in
  `~/.config/omarchy/`
- your picks in `~/.local/state/omarchy/wheel-uses.json`
- `[wheely] panels` and `[menu] scrim-alpha` in `~/.config/omarchy/shell.toml`. Omarchy's own
  menus keep using `scrim-alpha`, so delete that line to get the theme's back.
