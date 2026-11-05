# wheely

A radial launcher for [Omarchy](https://omarchy.org). `SUPER+A` puts your bar's panels on a
ring; start typing to search for anything: apps, open windows, keybindings, the Omarchy menu,
themes, fonts and files. It works alongside Omarchy's own menu and Walker.

<!-- screenshot: the wheel -->

> **Early release.** Tested on Omarchy 4.5 with Quickshell 0.3.2, one NVIDIA GPU and one
> monitor. It patches Omarchy's shell files with `sudo`, so `omarchy plugin add` cannot
> install it. It takes over `SUPER+A` and `SUPER+W`. The lock screen is a work in progress.

## Features

- **Wheel**: your panels on a ring, and one search for anything. Start with `/` for files,
  `=` to calculate; type `help` for every keybind. [Guide](docs/wheel.md)
- **Files**: a keyboard-driven file browser with previews and a right-click menu.
  [Guide](docs/files.md)
- **Centered panels**: bar panels open centered over a blurred desktop.
  [Guide](docs/centered-panels.md)
- **Lock screen**: six designs, picked in the wheel under Style › Lockscreen Designs.
  [Guide](docs/lockscreen.md)

## Install

Needs `jq`, `python3`, `git`, `hyprctl`, `sudo`, `fd`, `wl-copy`, `gio`, `xdg-open`,
`xdg-mime` and `setsid`. Optional: Pygments (code colours), ImageMagick (image sizes),
`qt6-multimedia` and `qt6-multimedia-ffmpeg` (video previews).

```bash
git clone https://github.com/Xpond/wheely
cd wheely
./install.sh
```

Update with `git pull && ./install.sh`. Keep the checkout where it is, as the install points
to it; run `./revert.sh` before moving or deleting it.

`omarchy update` overwrites the patched files; a hook reapplies the patches automatically and
reports any conflict. What the install changes, and why it needs `sudo`:
[docs/install.md](docs/install.md).

## Uninstall

```bash
./revert.sh
```

Puts back Omarchy's original files and removes everything else. Your settings are kept for a
reinstall. It also works from a TTY or over SSH.

## Also in this repo

Two light Omarchy themes with animated wallpapers, installed separately:
[Tidal](themes/tidal/README.md), an animated coast, and [Wheelie](themes/wheelie/README.md),
a desert rider in a building sandstorm.

## Bugs and contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for what to include in a bug report, and how to work
on wheely.

## License

MIT, see [LICENSE](LICENSE). Files derived from Omarchy are under
[LICENSE.omarchy](LICENSE.omarchy). The fluid animation in the wheel's easter egg is adapted
from hyprglaze's `fluid.frag` shader, under [LICENSE.hyprglaze](plugins/xpo.wheel/LICENSE.hyprglaze).
The wallpapers and lock-screen art are AI-generated; their READMEs name the model.
