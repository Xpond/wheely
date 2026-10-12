#!/usr/bin/env python3
"""Tidal palette, Omarchy templates, and GPU renders. Opens a temporary preview window.

Run from a Wayland desktop: python3 tests/tidal.py [/tmp/tidal-preview]
Requires Omarchy, Quickshell, ImageMagick, and a working OpenGL session.
"""
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tomllib
import qslog

repo = Path(__file__).resolve().parents[1]
theme = repo / "themes/tidal"
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tidal-preview").resolve()
output.mkdir(parents=True, exist_ok=True)
palette = tomllib.loads((theme / "colors.toml").read_text())
tomllib.loads((theme / "shell.toml").read_text())
assert palette["mode"] == "light"


def luminance(hex_color):
    rgb = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


for key in ["foreground", "dark_foreground", "light_foreground", "bright_foreground", "accent", "muted",
            "red", "yellow", "orange", "green", "cyan", "blue", "magenta", "brown",
            "bright_red", "bright_yellow", "bright_green", "bright_cyan", "bright_blue", "bright_magenta"]:
    contrast = (luminance(palette["background"]) + 0.05) / (luminance(palette[key]) + 0.05)
    assert contrast >= 4.5, (key, contrast)
for background in ["dark_background", "darker_background", "lighter_background"]:
    for key in ["foreground", "dark_foreground", "light_foreground", "bright_foreground", "muted"]:
        contrast = (luminance(palette[background]) + 0.05) / (luminance(palette[key]) + 0.05)
        assert contrast >= 4.5, (background, key, contrast)
contrast = (luminance(palette["selection_background"]) + 0.05) / (luminance(palette["selection_foreground"]) + 0.05)
assert contrast >= 4.5, ("selection", contrast)
print("ok: text, accent, terminal colors, secondary text, and selections contrast at least 4.5:1", flush=True)

wallpapers = sorted((theme / "backgrounds").glob("*.jpg"))
assert len(wallpapers) == 3
for wallpaper in wallpapers:
    width, height = map(int, subprocess.check_output(
        ["magick", "identify", "-format", "%w %h", str(wallpaper)], text=True).split())
    assert width >= 3840 and height >= 2160 and 1.7 < width / height < 1.85
posters = sorted((theme / "backgrounds").glob("*.png"))
assert [p.name for p in posters] == ["00-living-coast-animated.png", "00-muted-coast-animated.png"]
assert all(struct.unpack(">II", p.read_bytes()[16:24]) == (3840, 2160) for p in posters)
print("ok: three native 4K-or-larger wallpapers and two animated coast posters", flush=True)

# Run Omarchy's real generator against a scratch staging directory, never the user's next theme.
omarchy = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"))
staged = output / "staged"
staged.mkdir(exist_ok=True)
for name in ["colors.toml", "shell.toml"]:
    shutil.copyfile(theme / name, staged / name)
source = (omarchy / "bin/omarchy-theme-set-templates").read_text()
old = 'NEXT_THEME_DIR="$HOME/.local/state/omarchy/current/next-theme"'
assert source.count(old) == 1
generator = output / "templates.sh"
generator.write_text(source.replace(old, "NEXT_THEME_DIR=" + "'" + str(staged).replace("'", "'\\''") + "'"))
subprocess.run(["bash", str(generator)], check=True, env=dict(os.environ, OMARCHY_PATH=str(omarchy)))
for name in ["alacritty.toml", "foot.ini", "ghostty.conf", "kitty.conf", "hyprland.lua", "neovim.lua", "btop.theme"]:
    text = (staged / name).read_text()
    assert not re.search(r"\{\{.*?\}\}", text), name
assert tomllib.loads((staged / "alacritty.toml").read_text())["colors"]["primary"]["background"] == palette["background"]
print("ok: Omarchy generates the terminal, editor, monitor, and border configurations", flush=True)

shutil.copytree(theme / "animated", output / "animated", dirs_exist_ok=True)
qml = '''import QtQuick
import Quickshell
import "animated"
Window {
  id: root
  width: 960; height: 540; visible: true
  title: "Tidal render check"
  property var frames: [148, 148.0001, 152, 152.0001, 160, 160.0001, 170, 170.0001, 180, 180.0001, 0, 3600]
  property int frame: 0
  property real stopped: 0
  property int updates: 0
  Surface { id: sea; width: 1920; height: 1080; running: false; seconds: 148; muted: MUTED }
  Connections { target: sea; function onSecondsChanged() { if (sea.running) root.updates++ } }
  Timer { interval: 20000; running: true; onTriggered: { console.error("FAIL timeout"); Qt.exit(1) } }
  Timer {
    id: capture; interval: 180; running: true
    onTriggered: sea.grabToImage(function(result) {
      if (!result.saveToFile(OUTPUT + "/animated-" + root.frames[root.frame] + ".png")) {
        console.error("FAIL capture"); Qt.exit(1); return
      }
      root.frame++
      if (root.frame < root.frames.length) {
        sea.seconds = root.frames[root.frame]; capture.restart()
      } else { sea.width = 3840; sea.height = 2160; ultra.start() }
    })
  }
  Timer { id: ultra; interval: 180; onTriggered: {
    if (sea.resolution.x !== 3840 || sea.resolution.y !== 2160 || sea.layer.enabled) {
      console.error("FAIL downscaled 4K render"); Qt.exit(1); return
    }
    sea.grabToImage(function(result) {
      result.saveToFile(OUTPUT + "/animated-4k.png")
      sea.width = 1920; sea.height = 1080
      sea.seconds = 148; sea.running = true; advancing.start()
    })
  } }
  Timer { id: advancing; interval: 1000; onTriggered: {
    if (sea.seconds <= 148) { console.error("FAIL no motion"); Qt.exit(1); return }
    console.log("Animation updates in one second:", root.updates)
    if (root.updates < 24) { console.error("FAIL choppy motion"); Qt.exit(1); return }
    sea.running = false; root.stopped = sea.seconds; paused.start()
  } }
  Timer { id: paused; interval: 180; onTriggered: {
    if (sea.seconds !== root.stopped) { console.error("FAIL pause"); Qt.exit(1); return }
    console.log("PASS motion and pause"); Qt.quit()
  } }
}
'''
env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
           QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", XDG_CACHE_HOME=str(output / "cache"))
for variant in ["colorful", "muted"]:
    capture = output / variant
    capture.mkdir(exist_ok=True)
    render = qml.replace("OUTPUT", json.dumps(str(capture))).replace("MUTED", str(int(variant == "muted")))
    (output / "render.qml").write_text(render)
    run = subprocess.run(["quickshell", "--no-color", "-p", str(output / "render.qml")],
                         env=env, capture_output=True, text=True, timeout=25)
    log = run.stdout + run.stderr
    (capture / "render.log").write_text(log)
    assert run.returncode == 0 and "PASS" in log, log
    qslog.check(log)
    frames = {n: subprocess.check_output(["magick", str(capture / f"animated-{n}.png"), "-depth", "8", "RGB:-"])
              for n in [148, 152, 0, 3600]}
    assert frames[0] == frames[3600], "hourly wrap jumps"
    assert struct.unpack(">II", (capture / "animated-4k.png").read_bytes()[16:24]) == (3840, 2160)
    change = sum(abs(a - b) for a, b in zip(frames[148], frames[152])) / len(frames[148])
    assert change > 0.67, "the water does not move"
    pixel = lambda x, y: frames[148][(y * 1920 + x) * 3:(y * 1920 + x) * 3 + 3]
    sea, sand = pixel(150, 100), pixel(1750, 950)
    if variant == "muted":
        assert max(sea) - min(sea) <= 1 and 50 < min(sea) <= max(sea) < 100 and sand[0] >= sand[1] > sand[2], (sea, sand)
        assert sum(sand) - sum(sea) > 240, "the charcoal water and warm grey shore blend together"
        assert 180 < sum(sand) / len(sand) < 215, "the shore should stay a muted warm grey"
    else:
        assert sea[2] - sea[0] > 30 and sand[0] > sand[2], (sea, sand)
        assert sum(frames[148]) / len(frames[148]) > 170, "the coast is too dark for Tidal"
    waterlines = []
    for x in [150, 944, 1738]:
        column = subprocess.check_output(["magick", str(capture / "animated-148.png"),
            "-crop", f"32x1080+{x}+0", "+repage", "-scale", "1x1080!", "-depth", "8", "RGB:-"])
        waterlines.append(max(y for y in range(1080)
            if sum((column[3*y+i] - sea[i]) ** 2 for i in range(3))
             < sum((column[3*y+i] - sand[i]) ** 2 for i in range(3))))
    assert max(waterlines) - min(waterlines) < 216, "the shoreline tilts across the display"
    for moment in [148, 152, 160, 170, 180]:
        # Average individual sand grains; a wave seam changes whole neighboring regions.
        difference = subprocess.run(["magick",
            str(capture / f"animated-{moment}.png"), str(capture / f"animated-{moment}.0001.png"),
            "-blur", "0x1", "-metric", "PAE", "-compare", "-format", "%[distortion]", "info:"],
            capture_output=True, text=True, check=True)
        maximum = float(difference.stdout)
        print(f"{variant}: nearby frames at {moment}s: maximum pixel change {maximum:.4f}", flush=True)
        assert maximum < 0.04, "the wave edge jumps between nearby instants"
    print(f"ok: {variant} native 4K coast draws, moves smoothly, pauses, wraps, and stays continuous", flush=True)

# Render the collection gallery that `tidal preview` opens.
shutil.copytree(theme / "backgrounds", output / "backgrounds", dirs_exist_ok=True)
gallery = (theme / "preview.qml").read_text()
gallery = gallery.replace("  id: gallery", '''  id: gallery
  property int loadedImages: 0
  Timer { interval: 100; repeat: true; running: true; onTriggered: {
    if (gallery.loadedImages !== 3) return
    stop()
    page.grabToImage(function(result) {
      result.saveToFile(OUTPUT + "/gallery.png"); console.log("PASS gallery"); Qt.quit()
    })
  } }
  Timer { interval: 20000; running: true; onTriggered: Qt.exit(1) }
'''.replace("OUTPUT", json.dumps(str(output))))
gallery = gallery.replace("asynchronous: true", "asynchronous: true\n          onStatusChanged: if (status === Image.Ready) gallery.loadedImages++")
(output / "gallery.qml").write_text(gallery)
run = subprocess.run(["quickshell", "--no-color", "-p", str(output / "gallery.qml")],
                     env=env, capture_output=True, text=True, timeout=25)
log = run.stdout + run.stderr
assert run.returncode == 0 and "PASS gallery" in log, log
qslog.check(log)
assert struct.unpack(">II", (output / "gallery.png").read_bytes()[16:24]) == (1440, 1000)
gallery_background = subprocess.check_output(["magick", str(output / "gallery.png"),
    "-crop", "1x1+0+0", "+repage", "-depth", "8", "RGB:-"])
assert gallery_background == bytes.fromhex(palette["background"][1:]), "gallery background differs from the palette"
print("ok: gallery loads every wallpaper and renders without warnings", flush=True)
subprocess.run([sys.executable, str(repo / "tests/tidal-lifecycle.py"), str(output / "lifecycle")],
               check=True, env=env)
print("Captures:", output, flush=True)
