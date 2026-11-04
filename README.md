# wheely

A radial launcher for [Omarchy](https://omarchy.org): your bar's panels on a ring, and
one search for apps, open windows, the Omarchy menu, every keybinding, themes, fonts and
files. It also brings a keyboard-driven file browser, centered shell panels, and swappable
lock-screen designs. It sits alongside Omarchy's own menu and Walker rather than replacing them.

> **Before you install.** Tested only on Omarchy 4.5.0rc3 with Quickshell 0.3.2.r7, on one
> NVIDIA GPU and one monitor, without fingerprint unlock; the installer refuses an older
> Omarchy and does not check Quickshell. It patches eight package-owned shell files with
> `sudo` (see [Why sudo](#why-sudo)), so it is not a plugin `omarchy plugin add` can install.
> It takes over `SUPER+A` and `SUPER+W`, and `Ctrl+Space` while one of its animated themes
> is active. The lock screen is a work in progress.

## What you get

- **Wheel** (`SUPER+A`): your bar's panels on a ring. Start typing to search
  every panel, the Omarchy menu, every keybinding, apps, open windows
  (`workspace` lists them all), themes and fonts. Begin with `/` to search files and
  folders under your home and any folders you add (`Ctrl+Enter` opens a terminal in one),
  or with `=` to calculate (`Enter` copies the answer). `SUPER+W` closes the wheel and any
  open shell panel, otherwise the active window. Its settings are search rows too:
  `wheely shortcut` changes the key that opens it. Type `help` to search the manual, every
  key and setting in one place. See [`docs/wheel.md`](docs/wheel.md).
- **Files**: a keyboard-driven directory browser with previews and a right-click
  menu that changes with the file type, opened from the wheel. See [`docs/files.md`](docs/files.md).
- **Centered panels**: bar panels open centered over a blurred desktop, unless
  the wheel's Centered panels setting is off. See
  [`docs/centered-panels.md`](docs/centered-panels.md).
- **Lock screen**: six swappable designs (`rally`, `tunnel`, `mycelium`, `shore`, `meadow`
  and the default `wallpaper`), picked in the wheel under Style › Lockscreen Designs and
  previewed without locking with `omarchy-shell lock preview`. See
  [`docs/lockscreen.md`](docs/lockscreen.md).

## Install

Needs `jq`, `python3`, `git`, `hyprctl`, `sudo`, `fd`, `wl-copy`, `gio`,
`xdg-open`, `xdg-mime` and `setsid`. Optional: Pygments for code colours and
ImageMagick's `identify` for image sizes. Run from your Omarchy session:

```bash
git clone https://github.com/Xpond/wheely
cd wheely
./install.sh
```

It links `plugins/` into `~/.config/omarchy/plugins/` and registers them in
`~/.config/omarchy/shell.json`, appends a marked block (keybinds, layer rules,
blur) to `~/.config/hypr/hyprland.lua`, links four helpers into
`~/.local/bin`, links the lock-screen designs in `lock/` into
`~/.local/share/wheely/`, patches eight shell files, installs a post-update
hook, and restarts the shell. Rerunning is safe, and `git pull && ./install.sh`
updates it. Keep the checkout where it is: the hook, plugins and helpers point to it.
Run `./revert.sh` before moving or deleting it. If it goes missing anyway, the lock screen
still locks, without its design.

Video previews also need `qt6-multimedia` and `qt6-multimedia-ffmpeg`
(`sudo pacman -S --needed qt6-multimedia qt6-multimedia-ffmpeg`). The fullsize
button opens native mpv, which Omarchy includes.

## Revert

```bash
./revert.sh
```

Removes the hook, plugins, Hyprland block and helper links, puts back Omarchy's
original shell files, and unlinks the lock-screen designs and forgets the chosen one
after a successful restore, then restarts the shell. It also works from a TTY or over
SSH when the desktop will not start. Originals are checked against
pacman's checksums before they are written, and a shell file changed outside
this project is left untouched and reported.
Your settings stay: `wheel.json`, `wheel-blur`, `wheel-shortcut` and
`wallpaper-pause-shortcut` in `~/.config/omarchy/`, and your picks in
`~/.local/state/omarchy/wheel-uses.json`, so a reinstall starts where you left off.
So do `[wheely] panels` and `[menu] scrim-alpha` in `~/.config/omarchy/shell.toml`;
Omarchy's own menus keep using `scrim-alpha`, so delete that line to get the theme's back.

## Why sudo

The eight patched files live in `/usr/share/omarchy/shell`, owned by the Omarchy
package. Copying them in (install) and restoring them (revert) are the only
`sudo` calls, and each runs only when a file actually needs changing.
Everything else stays in your home directory. Two of the patches set environment
variables for the whole shell: a threaded render loop, and software decoding for video
previews.

Because the package owns them, `omarchy update` overwrites them. The hook then
reruns `install.sh`, which merges the patches onto the new version; a conflict
leaves the shipped file as it is and is reported, on the desktop too when
`notify-send` is available. The lock screen's two files are never merged: when an
update changes either, both stay Omarchy's own until wheely is updated for it
(`git pull && ./install.sh`).

## Also in this repo

Two light Omarchy themes with animated wallpapers, each installed separately:

- [Tidal](themes/tidal/README.md): an animated coast in colorful and muted palettes, plus
  three static wallpapers. Preview it with `./themes/tidal/tidal preview`.
- [Wheelie](themes/wheelie/README.md): a live desert scene where a rider holds a wheelie
  while a sandstorm builds, plus four static wallpapers. Install it with
  `./themes/wheelie/wheelie install`.

## Reporting a bug

Open an [issue](https://github.com/Xpond/wheely/issues) with what you did, what
happened, your GPU, and the output of:

```bash
omarchy-version
quickshell log -p "$OMARCHY_PATH/shell" -t 50
# The lock screen runs in its own process:
quickshell log -p ~/.local/share/wheely/lock-session -t 50
```

Working on it: see [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`tests/README.md`](tests/README.md).

## License

MIT, see [`LICENSE`](LICENSE). `patches/` holds original and modified Omarchy
shell files and `plugins/xpo.wheel/mark.png` is derived from Omarchy's icon,
both under [`LICENSE.omarchy`](LICENSE.omarchy). The fluid shader is adapted
from hyprglaze: [`LICENSE.hyprglaze`](plugins/xpo.wheel/LICENSE.hyprglaze). The
wallpapers, scene layers and the rally lock screen's backdrop are AI-generated; each
theme's README and `lock/rally/README.md` name the model.
