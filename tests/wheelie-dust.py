#!/usr/bin/env python3
"""Check rendered dust: visible output, motion, pause and clock-wrap continuity.

Usage: python3 tests/wheelie-dust.py [bake-directory]
Requires the graphics session, Quickshell and ImageMagick.
QSG_RHI_BACKEND=vulkan uses a temporary Wayland background-layer window.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

repo = Path(__file__).resolve().parents[1]
build = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "themes/wheelie/build"
env = os.environ | {"QT_QPA_PLATFORM": "offscreen", "QT_QPA_PLATFORMTHEME": "generic",
                    "QT_QUICK_BACKEND": "rhi"}
env.setdefault("QSG_RHI_BACKEND", "opengl")

with tempfile.TemporaryDirectory(prefix="wheelie-dust-") as temp:
    output = Path(temp)
    config = output / "scene"
    shutil.copytree(build, config)
    shell = config / "dust-test.qml"
    qml = """import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
Window {
  id: window
  width: 640; height: 360; visible: true
  property string saved: ""
  Rectangle {
    id: canvas; anchors.fill: parent; color: "black"
    Item {
      anchors.centerIn: parent; width: 5504; height: 3072
      scale: Math.max(canvas.width / width, canvas.height / height)
      AmbientDust { id: dust; anchors.fill: parent; seed: 314159 }
    }
  }
  IpcHandler {
    target: "dust"
    function status(): string {
      return JSON.stringify({clock: dust.clock, epoch: dust.epoch, saved: window.saved})
    }
    function pause(): void { dust.running = false }
    function resume(): void { dust.running = true }
    function freeze(t: real, e: int): void {
      dust.running = false; dust.epoch = e; dust.clock = t
    }
    function capture(path: string): void {
      window.saved = ""
      canvas.grabToImage(r => { if (r.saveToFile(path)) window.saved = path })
    }
  }
}
"""
    if env["QSG_RHI_BACKEND"] == "vulkan":
        env["QT_QPA_PLATFORM"] = "wayland"
        qml = qml.replace("import Quickshell.Io", "import Quickshell.Io\nimport Quickshell.Wayland")
        qml = qml.replace("Window {", "PanelWindow {", 1).replace(
            "width: 640; height: 360; visible: true", """screen: Quickshell.screens[0]
  anchors { top: true; bottom: true; left: true; right: true }
  exclusionMode: ExclusionMode.Ignore
  mask: Region {}
  WlrLayershell.layer: WlrLayer.Bottom
  WlrLayershell.namespace: "wheelie-dust-test"
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.None""")
    shell.write_text(qml)
    log_path = output / "run.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(["quickshell", "--no-color", "-p", str(shell)],
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            def ipc(action, *args):
                result = subprocess.run(
                    ["quickshell", "ipc", "-p", str(shell), "call", "dust", action, *map(str, args)],
                    env=env, capture_output=True, text=True, timeout=5)
                assert result.returncode == 0, result.stderr + log_path.read_text()
                return json.loads(result.stdout) if action == "status" else None

            def wait_for(predicate):
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    assert process.poll() is None, log_path.read_text()
                    try:
                        state = ipc("status")
                        if predicate(state):
                            return state
                    except AssertionError:
                        if process.poll() is not None:
                            raise
                    time.sleep(0.05)
                raise AssertionError(log_path.read_text())

            def capture(name):
                path = output / f"{name}.png"
                ipc("capture", path)
                wait_for(lambda state: state["saved"] == str(path))
                return subprocess.check_output(["magick", str(path), "-depth", "8", "rgb:-"])

            wait_for(lambda state: state["clock"] > 0.2)
            ipc("pause")
            first = capture("paused")
            clock = ipc("status")["clock"]
            assert sum(first) > 10000, "Dust shader produced no visible particles"
            time.sleep(0.25)
            assert first == capture("paused-again"), "Paused dust still moves"
            assert ipc("status")["clock"] == clock
            ipc("resume")
            wait_for(lambda state: state["clock"] > clock + 0.2)
            ipc("pause")
            assert capture("resumed") != first, "Resumed dust did not move"
            assert clock + 0.2 < ipc("status")["clock"] < clock + 1

            # Two representations of the same instant must not jump at clock rollover.
            ipc("freeze", 2376, 0)
            last = capture("wrap-end")
            ipc("freeze", 0, 1)
            wrapped = capture("wrap-start")
            difference = [abs(a - b) for a, b in zip(last, wrapped)]
            assert max(difference) <= 4 and sum(difference) / len(difference) < 0.01, (
                max(difference), sum(difference) / len(difference))
            ipc("freeze", 0, 10000)
            assert capture("later-epoch") != wrapped, "Dust repeats on every clock rollover"
            errors = [line for line in log_path.read_text().splitlines()
                      if re.search(r"(TypeError|ReferenceError|Error:|Failed to)", line)
                      and "Failed to register with host portal" not in line]
            assert not errors, errors
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
print("ok: visible GPU dust, frozen pause, continuous resume, clock rollover, changing generations")
