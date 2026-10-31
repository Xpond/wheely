#!/usr/bin/env python3
"""Compare the compact dust mesh with the original grid using identical particles."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import qslog

repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/wheelie-mesh").resolve()
scene = output / "scene"
shutil.copytree(repo / "themes/wheelie/scene", scene, dirs_exist_ok=True)
surface = qslog.patch((scene / "Surface.qml").read_text(), "  id: root", "  id: root\n  property int dustSeed: 314159", 1)
surface = qslog.patch(surface, "AmbientDust {", "AmbientDust {\n          seed: root.dustSeed", 1)
(scene / "Surface.qml").write_text(surface)
(scene / "Reference.qml").write_text(qslog.patch(surface, "AmbientDust {", "ReferenceDust {", 1))
dust = qslog.patch((scene / "AmbientDust.qml").read_text(), "Qt.size(3 * count - 2, 1)", "Qt.size(1, 4 * count - 3)")
dust = qslog.patch(dust, '"ambient-dust.vert.qsb"', '"reference-dust.vert.qsb"')
(scene / "ReferenceDust.qml").write_text(dust)

# Keep the old topology and slot/corner decoding independent of the compact mesh.
original = '''    float row = floor(qt_MultiTexCoord0.y * float(4 * count - 3) + 0.5);
    float slot = floor((row + 1.0) / 4.0);
    float edge = mod(row, 4.0);
    uv = edge == 0.0 ? vec2(qt_MultiTexCoord0.x, 0.0)
       : edge == 1.0 ? vec2(qt_MultiTexCoord0.x, 1.0)
       : edge == 2.0 ? vec2(1.0) : vec2(0.0);'''
vertex = (scene / "ambient-dust.vert").read_text()
start, end = vertex.index("    float column ="), vertex.index("\n\n    // Stagger births")
reference = scene / "reference-dust.vert"
reference.write_text(vertex[:start] + original + vertex[end:])
subprocess.run(["/usr/lib/qt6/bin/qsb", "--qt6", "-o", str(reference) + ".qsb", str(reference)], check=True)

cases = [[1920, 1080, 0, 1], [1920, 1080, 0.016, 314159], [1920, 1080, 300, 8388591],
         [3840, 2160, 300, 314159], [1080, 1920, 70, 314159], [2560, 1080, 180, 314159],
         [1920, 1080, 2375.999, 314159], [1920, 1080, 2376.001, 314159],
         [1920, 1080, 23760000.5, 8388591]]
qml = '''import QtQuick
import Quickshell
import "scene"
Window {
  id: root
  width: 640; height: 360; visible: true
  title: "Wheelie mesh comparison"
  property var cases: CASES
  property int step: 0
  readonly property var sample: cases[step]
  Surface {
    id: compact
    width: root.sample[0]; height: root.sample[1]
    seconds: root.sample[2]; stormSeconds: Math.min(seconds, 300); dustSeed: root.sample[3]; running: false
  }
  Reference {
    id: reference
    width: compact.width; height: compact.height
    seconds: compact.seconds; stormSeconds: compact.stormSeconds; dustSeed: compact.dustSeed; running: false
  }
  Timer { interval: 120000; running: true; onTriggered: { console.error("FAIL capture timeout"); Qt.exit(1) } }
  Timer {
    id: capture; interval: 300; running: true
    onTriggered: compact.grabToImage(result => {
      if (!result.saveToFile(OUTPUT + "/compact-" + root.step + ".png")) { Qt.exit(1); return }
      reference.grabToImage(original => {
        if (!original.saveToFile(OUTPUT + "/reference-" + root.step + ".png")) { Qt.exit(1); return }
        if (root.step + 1 === root.cases.length) { console.log("PASS mesh comparison"); Qt.quit(); return }
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
    selected = cases if scale == "1" else [cases[i] for i in [0, 2, 4, 5, 7]]
    shell = output / "shell.qml"
    shell.write_text(qml.replace("CASES", json.dumps(selected)).replace("OUTPUT", json.dumps(str(captures))))
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QT_SCALE_FACTOR=scale,
               XDG_CACHE_HOME=str(output / "cache"))
    run = subprocess.run(["quickshell", "--no-color", "-p", str(shell)],
                         env=env, capture_output=True, text=True, timeout=125)
    log = run.stdout + run.stderr
    (captures / "render.log").write_text(log)
    assert run.returncode == 0 and "PASS mesh comparison" in log, log
    qslog.check(log)
    for step, case in enumerate(selected):
        paths = [captures / f"{kind}-{step}.png" for kind in ["compact", "reference"]]
        sizes = [struct.unpack(">II", path.read_bytes()[16:24]) for path in paths]
        assert sizes[0] == sizes[1] == tuple(round(n * float(scale)) for n in case[:2]), sizes
        assert paths[1].stat().st_size > 100000, "scene did not render"
        pixels = [subprocess.check_output(["magick", str(path), "-depth", "8", "RGBA:-"]) for path in paths]
        assert pixels[0] == pixels[1], (scale, case, "compact mesh changed pixels")
    print(f"ok: {len(selected)} pixel-identical dust mesh comparisons at {scale}x", flush=True)
