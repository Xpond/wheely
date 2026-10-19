#!/usr/bin/env python3
"""Exercise Wheelie's controller and pause/resume offscreen with isolated desktop state.

Usage: python3 tests/wheelie-lifecycle.py [bake-directory]
Requires the graphics session, but creates no desktop windows or real locks.
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
                    "QT_QUICK_BACKEND": "rhi", "QSG_RHI_BACKEND": "opengl"}

with tempfile.TemporaryDirectory(prefix="wheelie-lifecycle-") as temp:
    output = Path(temp)
    config, state = output / "controller", output / "state"
    shutil.copytree(build, config)
    state.mkdir()
    (state / "theme.name").write_text("wheelie\n")
    for name in ("00-wheelie-animated.png", "static.png"):
        (state / name).touch()
    (state / "background").symlink_to(state / "00-wheelie-animated.png")
    activity = output / "activity.json"
    activity.write_text('{"dpmsStatus": true}')
    shell = config / "wallpaper.qml"
    qml = shell.read_text().replace('import QtQuick\n', 'import QtQuick\nimport QtQuick.Window\n', 1)
    qml = qml.replace('Quickshell.env("HOME") + "/.local/state/omarchy/current"', json.dumps(str(state)))
    # Supply compositor snapshots without changing the user's display or lock state.
    qml = qml.replace('id: root', '''id: root
  property var activity: ({})
  property var testScene: null
  property int frames: 0
  FileView {
    path: %s; watchChanges: true
    onFileChanged: reload()
    onLoaded: root.activity = JSON.parse(text())
  }''' % json.dumps(str(activity)), 1)
    qml = qml.replace('function pause(): void', '''function status(): string {
      return JSON.stringify({animated: root.animated, loaded: !!root.testScene,
        running: root.testScene ? root.testScene.running : false,
        turn: root.testScene ? root.testScene.wheelTurn : 0, frames: root.frames})
    }
    function pause(): void''')
    qml = qml.replace('onTriggered: Hyprland.refreshMonitors()', 'onTriggered: {}')
    qml = qml.replace('PanelWindow {', 'Window {\n      width: 640; height: 360; visible: true')
    qml = qml.replace('screen: modelData', '')
    qml = qml.replace('monitor: Hyprland.monitorFor(screen)', 'monitor: null')
    qml = qml.replace('monitorState: monitor ? monitor.lastIpcObject : ({})', 'monitorState: root.activity')
    qml = re.sub(r'^      (anchors \{|exclusionMode:|mask:|WlrLayershell\.).*\n', '', qml, flags=re.M)
    qml = qml.replace('Surface { anchors.fill:', '''Connections {
        target: wallpaper
        function onFrameSwapped() { root.frames++ }
      }
      Surface {
        id: scene
        Component.onCompleted: root.testScene = scene
        Component.onDestruction: root.testScene = null
        anchors.fill:''')
    shell.write_text(qml)
    log_path = output / "run.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(["quickshell", "--no-color", "-p", str(shell)],
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            def ipc(action):
                result = subprocess.run(["quickshell", "ipc", "-p", str(shell), "call", "wheelie", action],
                                        env=env, capture_output=True, text=True, timeout=5)
                assert result.returncode == 0, result.stderr + log_path.read_text()
                return json.loads(result.stdout) if action == "status" else None

            def wait_for(predicate):
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    assert process.poll() is None, log_path.read_text()
                    try:
                        current = ipc("status")
                        if predicate(current):
                            return current
                    except AssertionError:
                        if process.poll() is not None:
                            raise
                    time.sleep(0.05)
                raise AssertionError(log_path.read_text())

            def frozen():
                time.sleep(0.15)  # Drain the last submitted frame.
                first = ipc("status")
                time.sleep(0.35)
                second = ipc("status")
                assert not second["running"] and first == second, (first, second)
                return second["turn"]

            def set_activity(value):
                activity.write_text(json.dumps(value))

            def select(name):
                replacement = state / "replacement"
                replacement.symlink_to(state / name)
                replacement.replace(state / "background")

            wait_for(lambda s: s["running"] and s["frames"] > 10)
            time.sleep(0.2)
            ipc("pause")
            turn = frozen()
            ipc("resume")
            resumed = wait_for(lambda s: s["running"] and s["turn"] != turn)
            assert (resumed["turn"] - turn) % 1 < 0.25, (turn, resumed)
            set_activity({"dpmsStatus": True, "solitaryBlockedBy": ["LOCK"]})
            wait_for(lambda s: not s["running"])
            frozen()
            set_activity({"dpmsStatus": False, "solitaryBlockedBy": []})
            frozen()
            set_activity({"dpmsStatus": True, "solitary": "abcdef"})
            frozen()  # Compositor-confirmed coverage by a fullscreen client.
            set_activity({"dpmsStatus": True, "solitary": "0"})
            wait_for(lambda s: s["running"])
            ipc("pause")
            set_activity({"dpmsStatus": True})
            frozen()  # Waking a display must preserve the user's manual pause.
            ipc("resume")
            wait_for(lambda s: s["running"])
            for _ in range(2):
                select("static.png")
                wait_for(lambda s: not s["animated"] and not s["loaded"])
                select("00-wheelie-animated.png")
                wait_for(lambda s: s["running"])
            (state / "theme.name").write_text("other\n")
            wait_for(lambda s: not s["loaded"])
            (state / "theme.name").write_text("wheelie\n")
            wait_for(lambda s: s["running"])
            assert not re.search(r'(TypeError|ReferenceError|Error:|Failed to)', log_path.read_text()), log_path.read_text()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
print("ok: frozen frames, continuous resume, lock/DPMS/fullscreen gating, manual pause, static/theme round trips")
