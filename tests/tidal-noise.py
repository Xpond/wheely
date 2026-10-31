#!/usr/bin/env python3
"""Compare the cached noise with the original procedural shader at native pixel sizes."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import qslog

repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tidal-noise").resolve()
animated = output / "animated"
shutil.copytree(repo / "themes/tidal/animated", animated, dirs_exist_ok=True)

# Keep the pre-cache arithmetic as an independent reference, including negative-cell wrapping.
original = '''vec3 sloped(vec2 p) {
    vec2 i = floor(p), f = fract(p), s = f * f * (3.0 - 2.0 * f), ds = 6.0 * f * (1.0 - f);
    float a = hash(mod(i, 64.0)), b = hash(mod(i + vec2(1, 0), 64.0));
    float c = hash(mod(i + vec2(0, 1), 64.0)), d = hash(mod(i + vec2(1, 1), 64.0));
    return vec3(a + (b - a) * s.x + (c - a) * s.y + (a - b - c + d) * s.x * s.y,
                ds * (vec2(b - a, c - a) + (a - b - c + d) * s.yx));
}'''
source = (animated / "tidal.frag").read_text()
start = source.index("vec3 sloped(")
end = source.index("\n}", start) + 2
reference = animated / "reference.frag"
reference.write_text(source[:start] + original + source[end:])
subprocess.run(["/usr/lib/qt6/bin/qsb", "--qt6", "-o", str(reference) + ".qsb",
                str(reference)], check=True)

cases = [[1920, 1080, 148, 0], [1920, 1080, 149.5, 1], [3840, 2160, 152, 0],
         [1080, 1920, 159, 1], [2560, 1080, 180, 0],
         [1920, 1080, 3599.999, 1], [1920, 1080, 3600.001, 0]]
qml = '''import QtQuick
import Quickshell
import "animated"
Window {
  id: root
  width: 640; height: 360; visible: true
  title: "Tidal noise comparison"
  property var cases: CASES
  property int step: 0
  readonly property var sample: cases[step]
  Surface {
    id: sea
    width: root.sample[0]; height: root.sample[1]
    seconds: root.sample[2]; muted: root.sample[3]; running: false
  }
  Surface {
    id: reference
    width: sea.width; height: sea.height
    seconds: sea.seconds; muted: sea.muted; running: false
    fragmentShader: Qt.resolvedUrl("animated/reference.frag.qsb")
  }
  Timer { interval: 60000; running: true; onTriggered: Qt.exit(1) }
  Timer {
    id: capture; interval: 180; running: true
    onTriggered: sea.grabToImage(function(result) {
      if (!result.saveToFile(OUTPUT + "/cached-" + root.step + ".png")) { Qt.exit(1); return }
      reference.grabToImage(function(original) {
        if (!original.saveToFile(OUTPUT + "/reference-" + root.step + ".png")) { Qt.exit(1); return }
        if (root.step + 1 === root.cases.length) { console.log("PASS noise comparison"); Qt.quit(); return }
        root.step++
        capture.start()
      })
    })
  }
}
'''
for scale in ["1", "1.5"]:
    captures = output / scale
    captures.mkdir(exist_ok=True)
    selected = cases if scale == "1" else [case for case in cases if case[0] < 3840]
    shell = output / "shell.qml"
    shell.write_text(qml.replace("CASES", json.dumps(selected)).replace("OUTPUT", json.dumps(str(captures))))
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QT_SCALE_FACTOR=scale,
               XDG_CACHE_HOME=str(output / "cache"))
    run = subprocess.run(["quickshell", "--no-color", "-p", str(shell)],
                         env=env, capture_output=True, text=True, timeout=65)
    log = run.stdout + run.stderr
    (captures / "render.log").write_text(log)
    assert run.returncode == 0 and "PASS noise comparison" in log, log
    qslog.check(log)
    for step in range(len(selected)):
        size = struct.unpack(">II", (captures / f"cached-{step}.png").read_bytes()[16:24])
        assert size == tuple(round(n * float(scale)) for n in selected[step][:2]), size
        pixels = [subprocess.check_output(["magick", str(captures / f"{kind}-{step}.png"),
                                          "-depth", "8", "RGBA:-"])
                  for kind in ["cached", "reference"]]
        assert pixels[0] == pixels[1], (scale, selected[step], "cached noise changed pixels")
    print(f"ok: cached noise matches procedural coast in {len(selected)} frames at {scale}x", flush=True)
