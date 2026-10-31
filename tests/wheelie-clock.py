#!/usr/bin/env python3
"""Check animation cadence, storm timing and pause/resume on Wheelie's shared clock."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import qslog

repo = Path(__file__).resolve().parents[1]
qml = '''import QtQuick
import Quickshell
Window {
  id: window
  width: 640; height: 360; visible: true
  property int updates: 0
  property int frames: 0
  property var storms: []
  property double started: 0
  property real stopped: 0
  property real stoppedStorm: 0
  property int stoppedFrames: 0
  property bool resumed: false
  onFrameSwapped: frames++
  Surface { id: scene; anchors.fill: parent; running: false }
  Connections {
    target: scene
    function onSecondsChanged() { window.updates++ }
    function onStormSecondsChanged() {
      if (!scene.running || scene.stormSeconds !== scene.seconds) {
        console.error("FAIL storm does not share the animation tick"); Qt.exit(1)
      }
      window.storms.push(Date.now() - window.started)
    }
  }
  function start() {
    updates = 0; storms = []; started = Date.now()
    scene.running = true; measure.start()
  }
  Timer { interval: 500; running: true; onTriggered: window.start() }
  Timer {
    id: measure; interval: 2200
    onTriggered: {
      const count = window.storms.length
      if (window.updates < 130 || window.updates > 145 || count !== 4) {
        console.error("FAIL cadence", window.updates, JSON.stringify(window.storms)); Qt.exit(1); return
      }
      for (let i = 0; i < count; i++) {
        const gap = window.storms[i] - (i ? window.storms[i - 1] : 0)
        if (gap < 500 || gap > 600) { console.error("FAIL storm interval", gap); Qt.exit(1); return }
      }
      console.log("CADENCE", window.updates, JSON.stringify(window.storms))
      scene.running = false
      if (window.resumed) { console.log("PASS shared clock"); Qt.quit(); return }
      window.stopped = scene.seconds; window.stoppedStorm = scene.stormSeconds
      settle.start()
    }
  }
  Timer { id: settle; interval: 200; onTriggered: { window.stoppedFrames = window.frames; pause.start() } }
  Timer {
    id: pause; interval: 700
    onTriggered: {
      if (scene.seconds !== window.stopped || scene.stormSeconds !== window.stoppedStorm
          || window.frames !== window.stoppedFrames) {
        console.error("FAIL paused scene advanced or presented"); Qt.exit(1); return
      }
      window.resumed = true; window.start()
    }
  }
  Timer { interval: 15000; running: true; onTriggered: { console.error("FAIL timeout"); Qt.exit(1) } }
}
'''
with tempfile.TemporaryDirectory(prefix="wheelie-clock-") as temp:
    scene = Path(temp) / "scene"
    shutil.copytree(repo / "themes/wheelie/scene", scene)
    shell = scene / "clock-test.qml"
    shell.write_text(qml)
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "QT_QPA_PLATFORMTHEME": "generic",
                        "QT_QUICK_BACKEND": "rhi", "QSG_RHI_BACKEND": "opengl"}
    run = subprocess.run(["quickshell", "--no-color", "-p", str(shell)],
                         env=env, capture_output=True, text=True, timeout=20)
    log = run.stdout + run.stderr
    assert run.returncode == 0 and "PASS shared clock" in log, log
    qslog.check(log)
    print("\n".join(line for line in log.splitlines() if "CADENCE" in line))
print("ok: full-rate animation, synchronized storm updates, frozen pause and fresh resume deadline")
