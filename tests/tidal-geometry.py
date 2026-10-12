#!/usr/bin/env python3
"""Check cached coast geometry after resizing and at fractional display scale."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import qslog

repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tidal-geometry").resolve()
output.mkdir(parents=True, exist_ok=True)
shutil.copytree(repo / "themes/tidal/animated", output / "animated", dirs_exist_ok=True)
qml = '''import QtQuick
import Quickshell
import "animated"
Window {
  id: root
  width: 640; height: 360; visible: true
  title: "Tidal geometry resize check"
  property var sizes: [[960, 540], [960, 960], [1920, 540], [540, 960]]
  property int step: 0
  Surface { id: reused; width: 640; height: 360; running: false }
  Component { id: coast; Surface { running: false } }
  property var fresh
  Timer { interval: 20000; running: true; onTriggered: Qt.exit(1) }
  Timer {
    id: resize; interval: 100; running: true
    onTriggered: {
      reused.width = root.sizes[root.step][0]
      reused.height = root.sizes[root.step][1]
      root.fresh = coast.createObject(root.contentItem, {
        width: reused.width, height: reused.height
      })
      capture.start()
    }
  }
  Timer {
    id: capture; interval: 180
    onTriggered: reused.grabToImage(function(result) {
      if (!result.saveToFile(OUTPUT + "/reused-" + root.step + ".png")) Qt.exit(1)
      root.fresh.grabToImage(function(reference) {
        if (!reference.saveToFile(OUTPUT + "/fresh-" + root.step + ".png")) Qt.exit(1)
        root.fresh.destroy()
        root.step++
        if (root.step < root.sizes.length) resize.start()
        else { console.log("PASS geometry resize"); Qt.quit() }
      })
    })
  }
}
'''
for scale in ["1", "1.5"]:
    captures = output / scale
    captures.mkdir(exist_ok=True)
    (output / "shell.qml").write_text(qml.replace("OUTPUT", json.dumps(str(captures))))
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QT_SCALE_FACTOR=scale,
               XDG_CACHE_HOME=str(output / "cache"))
    run = subprocess.run(["quickshell", "--no-color", "-p", str(output / "shell.qml")],
                         env=env, capture_output=True, text=True, timeout=25)
    log = run.stdout + run.stderr
    (captures / "render.log").write_text(log)
    assert run.returncode == 0 and "PASS geometry resize" in log, log
    qslog.check(log)
    for step in range(4):
        comparison = subprocess.run(["magick", str(captures / f"fresh-{step}.png"),
            str(captures / f"reused-{step}.png"), "-metric", "PAE", "-compare",
            "-format", "%[distortion]", "info:"], capture_output=True, text=True, check=True)
        assert float(comparison.stdout) == 0, (scale, step, comparison.stdout)
    print(f"ok: resized coast matches a fresh render at {scale}x display scale", flush=True)
