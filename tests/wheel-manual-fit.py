#!/usr/bin/env python3
"""The production manual sheet fits common screens whole, never scrolled, and stays readable."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import qslog

repo = Path(__file__).resolve().parents[1]
plugin = repo / "plugins/xpo.wheel"
shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
# Screens as [width, height, windowed, least scale]: the overlay on 1080p and 1440p, and a pinned window.
SCREENS = "[[1920, 1080, false, 0.8], [2560, 1440, false, 0.8], [1280, 800, true, 0.5]]"
# Pass a directory to keep a capture of each screen for a look.
shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None

with tempfile.TemporaryDirectory(prefix="wheely-manual-") as temporary:
    base = Path(temporary)
    for name in ("Commons", "Ui"):
        (base / name).symlink_to(shell / name)
    for name in ("WheelManual.qml", "ClickShield.qml", "MenuIndex.js"):
        shutil.copyfile(plugin / name, base / name)
    out = shots or base / "out"
    out.mkdir(parents=True, exist_ok=True)
    (base / "shell.qml").write_text('''import QtQuick
import Quickshell
import "MenuIndex.js" as MenuIndex
Scope {
  id: root
  property var screens: ''' + SCREENS + '''
  property int at: 0
  function check(ok, message) { if (!ok) throw new Error("FAIL " + message) }
  QtObject {
    id: wheel
    property var manualRows: MenuIndex.manualRows(''' + repr((plugin / "manual.md").read_text()) + ''')
    property string query: ""
    property bool manualRead: true
    property bool reading: true
    property bool windowed: root.screens[root.at][2]
    property int fadeDuration: 0
    property color surfaceFill: "#f2dccb"
    property color surfaceEdge: "#33000000"
    property int searchWidth: 280
    property int searchHeight: 40
  }
  Window {
    id: window
    width: root.screens[root.at][0]; height: root.screens[root.at][1]; visible: true; color: "#806050"
    WheelManual { id: sheet; wheel: wheel }
  }
  Timer {
    interval: 200; running: true; repeat: true
    onTriggered: {
      try {
        var s = root.screens[root.at], panel = sheet.children[0].item
        var shown = panel.mapToItem(window.contentItem, 0, 0, panel.width, panel.height)
        var name = "''' + str(out) + '''/" + s[0] + "x" + s[1] + ".png", last = root.at === root.screens.length - 1
        console.log("SCREEN", s[0] + "x" + s[1], "columns", sheet.count, "scale", sheet.fit.toFixed(3))
        stop()
        // Captured before the checks, so a failure leaves its picture behind.
        window.contentItem.grabToImage(function (image) {
          try {
            root.check(image.saveToFile(name), "capture failed")
            root.check(shown.y >= 0 && shown.y + shown.height <= s[1] + 0.5, "panel runs off the bottom")
            root.check(shown.x >= 0 && shown.x + shown.width <= s[0] + 0.5, "panel runs off the side")
            root.check(sheet.fit >= s[3], "shrunk past readable at " + s[0] + "x" + s[1])
            if (last) { console.log("PASS"); Qt.quit() } else { root.at++; start() }
          } catch (error) { console.error(String(error)); Qt.exit(1) }
        })
      } catch (error) { console.error(String(error)); Qt.exit(1) }
    }
  }
}
''')
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic", QT_FORCE_STDERR_LOGGING="1",
               QT_SCALE_FACTOR="1", XDG_RUNTIME_DIR=str(base / "runtime"), XDG_CACHE_HOME=str(base / "cache"))
    result = subprocess.run(["quickshell", "--no-color", "-p", str(base / "shell.qml")], cwd=base,
                            env=env, capture_output=True, text=True, timeout=60)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and "PASS" in log, log
    qslog.check(log)
    print("ok: " + "; ".join(l.split("SCREEN ", 1)[1] for l in log.splitlines() if "SCREEN " in l))
