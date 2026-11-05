#!/usr/bin/env python3
"""Size wallpaper textures from the window's ratio, which a fractional output reports truly."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import qslog

repo = Path(__file__).resolve().parents[1]
# The hosts hand each Surface their window's ratio; Screen's is rounded up, 1.5 to 2.
for host in ["themes/wheelie/scene/wallpaper.qml", "themes/tidal/animated/shell.qml"]:
    assert re.search(r"Surface \{[^}]*dpr: wallpaper\.devicePixelRatio", (repo / host).read_text()), host

qml = '''import QtQuick
import Quickshell
import Quickshell.Wayland
import "scene" as Wheelie
import "animated" as Tidal
Scope {
  // The hosts' own binding, on the installed Quickshell's PanelWindow.
  PanelWindow {
    id: panel
    implicitWidth: 64; implicitHeight: 64
    exclusionMode: ExclusionMode.Ignore
    mask: Region {}
    WlrLayershell.layer: WlrLayer.Background
    Wheelie.Surface { id: hosted; anchors.fill: parent; running: false; dpr: panel.devicePixelRatio }
  }
  Window {
    width: 640; height: 360; visible: true
    Wheelie.Surface { id: scene; anchors.fill: parent; running: false; dpr: 1.5 }
    Tidal.Surface { id: sea; anchors.fill: parent; running: false; dpr: 1.5 }
    Timer { interval: 1500; running: true; onTriggered: {
      var loader = scene.children.find(c => c.item)
      var size = loader.item.children[0].layer.textureSize
      var surge = sea.surgeData.textureSize
      console.log("SIZES", JSON.stringify([size.width, size.height, surge.width, scene.Screen.devicePixelRatio,
                                           Math.ceil(scene.width * 1.5), Math.ceil(scene.height * 1.5)]))
      console.log("PANEL", JSON.stringify([typeof panel.devicePixelRatio, hosted.dpr === panel.devicePixelRatio && hosted.dpr > 0]))
      Qt.quit()
    } }
  }
}
'''
with tempfile.TemporaryDirectory(prefix="theme-dpr-") as temporary:
    base = Path(temporary)
    shutil.copytree(repo / "themes/wheelie/scene", base / "scene")
    shutil.copytree(repo / "themes/tidal/animated", base / "animated")
    (base / "shell.qml").write_text(qml)
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic", QT_SCALE_FACTOR="2",
               QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", XDG_CACHE_HOME=str(base / "cache"))
    run = subprocess.run(["quickshell", "--no-color", "-p", str(base / "shell.qml")],
                         env=env, capture_output=True, text=True, timeout=20)
    log = run.stdout + run.stderr
    assert run.returncode == 0, log
    qslog.check(log)
    sizes = json.loads(re.search(r"SIZES (\[.*\])", log)[1])
    width, height = sizes[4:]
    assert sizes[:4] == [width, height, width, 2], sizes
    assert re.search(r"PANEL (\[.*\])", log)[1] == '["number",true]', log
print("ok: Wheelie's layer and Tidal's geometry follow the window's 1.5x, not Screen's rounded 2x; PanelWindow supplies it")
