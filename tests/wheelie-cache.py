#!/usr/bin/env python3
"""Compare the finished-background cache with the uncached grade on native Wayland."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import qslog

repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/wheelie-cache").resolve()
scene = output / "scene"
shutil.copytree(repo / "themes/wheelie/scene", scene, dirs_exist_ok=True)
source = (scene / "Surface.qml").read_text()
marker = "id: background\n      anchors.fill: parent\n      layer.enabled: true"
(scene / "Reference.qml").write_text(qslog.patch(source, marker, marker.replace("true", "false")))
dust = scene / "AmbientDust.qml"
dust.write_text(qslog.patch(dust.read_text(), "Math.floor(Math.random() * 8388591) + 1", "314159"))

# Reuse the same instances through size and storm changes to catch stale cache contents.
cases = [[1920, 1080, 0], [1920, 1080, 70], [1920, 1080, 300],
         [3840, 2160, 300], [1080, 1920, 70], [2560, 1080, 300],
         [1920, 1080, 2375.999], [1920, 1080, 2376.001], [1920, 1080, 300]]
qml = '''import QtQuick
import Quickshell
import "scene"
Window {
  id: root
  width: 640; height: 360; visible: true
  title: "Wheelie cache comparison"
  property var cases: CASES
  property int step: 0
  readonly property var sample: cases[step]
  Surface {
    id: cached
    width: root.sample[0]; height: root.sample[1]
    seconds: root.sample[2]; stormSeconds: seconds; running: false
  }
  Reference {
    id: reference
    width: cached.width; height: cached.height
    seconds: cached.seconds; stormSeconds: seconds; running: false
  }
  Timer { interval: 120000; running: true; onTriggered: { console.error("FAIL capture timeout"); Qt.exit(1) } }
  Timer {
    id: capture; interval: 300; running: true
    onTriggered: cached.grabToImage(result => {
      if (!result.saveToFile(OUTPUT + "/cached-" + root.step + ".png")) { Qt.exit(1); return }
      reference.grabToImage(original => {
        if (!original.saveToFile(OUTPUT + "/reference-" + root.step + ".png")) { Qt.exit(1); return }
        if (root.step + 1 === root.cases.length) { console.log("PASS cache comparison"); Qt.quit(); return }
        root.step++
        capture.start()
      })
    })
  }
}
'''
for scale in ["1", "1.5", "2"]:
    captures = output / scale
    captures.mkdir(exist_ok=True)
    selected = cases if scale == "1" else [case for case in cases if case[0] < 3840]
    shell = output / "shell.qml"
    shell.write_text(qml.replace("CASES", json.dumps(selected)).replace("OUTPUT", json.dumps(str(captures))))
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QT_SCALE_FACTOR=scale,
               XDG_CACHE_HOME=str(output / "cache"))
    run = subprocess.run(["quickshell", "--no-color", "-p", str(shell)],
                         env=env, capture_output=True, text=True, timeout=125)
    log = run.stdout + run.stderr
    (captures / "render.log").write_text(log)
    assert run.returncode == 0 and "PASS cache comparison" in log, log
    qslog.check(log)
    for step, case in enumerate(selected):
        paths = [captures / f"{kind}-{step}.png" for kind in ["cached", "reference"]]
        sizes = [struct.unpack(">II", path.read_bytes()[16:24]) for path in paths]
        assert sizes[0] == sizes[1] == tuple(round(n * float(scale)) for n in case[:2]), sizes
        pixels = [subprocess.check_output(["magick", str(path), "-depth", "8", "RGBA:-"]) for path in paths]
        assert len(set(pixels[0])) > 100, "scene did not render"
        differences = [abs(a - b) for a, b in zip(*pixels) if a != b]
        maximum = max(differences, default=0)
        print(f"{scale}x {case}: max={maximum}/255, changed={len(differences)} channels", flush=True)
        assert maximum <= 1 and len(differences) / len(pixels[0]) < 0.001, (scale, case, maximum, len(differences))
    # Returning to the original settled scene must restore the same cached pixels.
    assert (captures / "cached-2.png").read_bytes() == (captures / f"cached-{len(selected) - 1}.png").read_bytes()
    print(f"ok: {scale}x finished cache preserves scene detail through storm, resize and clock wrap", flush=True)
