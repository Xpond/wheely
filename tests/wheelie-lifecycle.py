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


def patch(text, old, new, count=-1):
    """Replace old, which must be present: a stale pattern would leave real Hyprland code running."""
    assert old in text, old
    return text.replace(old, new, count)


def stage(theme):
    """Omarchy's copy of the current theme, which the background link points into."""
    (theme / "backgrounds").mkdir(parents=True)
    for name in ("00-wheelie-animated.png", "static.png"):
        (theme / "backgrounds" / name).touch()


with tempfile.TemporaryDirectory(prefix="wheelie-lifecycle-") as temp:
    output = Path(temp)
    config, state = output / "controller #100%", output / "state"
    shutil.copytree(build, config)
    state.mkdir()
    (state / "theme.name").write_text("wheelie\n")
    stage(state / "theme")
    (state / "background").symlink_to(state / "theme/backgrounds/00-wheelie-animated.png")
    activity = output / "activity.json"
    activity.write_text('{"dpmsStatus": true}')
    shell = config / "wallpaper.qml"
    qml = patch(shell.read_text(), 'import QtQuick\n', 'import QtQuick\nimport QtQuick.Window\n', 1)
    qml = patch(qml, 'Quickshell.env("HOME") + "/.local/state/omarchy/current"', json.dumps(str(state)))
    # Supply compositor snapshots without changing the user's display or lock state.
    qml = patch(qml, 'id: root', '''id: root
  property var activity: ({})
  property var testScene: null
  property int scenes: 0
  property int frames: 0
  FileView {
    path: %s; watchChanges: true
    onFileChanged: reload()
    onLoaded: root.activity = JSON.parse(text())
  }''' % json.dumps(str(activity)), 1)
    qml = patch(qml, 'function pause(): void', '''function status(): string {
      return JSON.stringify({animated: root.animated, loaded: !!root.testScene, scenes: root.scenes,
        running: root.testScene ? root.testScene.running : false,
        ready: root.testScene ? !!root.testScene.layout.cutout : false,
        turn: root.testScene ? root.testScene.wheelTurn : 0, frames: root.frames})
    }
    function pause(): void''')
    qml = patch(qml, 'onTriggered: Hyprland.refreshMonitors()', 'onTriggered: {}')
    qml = patch(qml, 'PanelWindow {', 'Window {\n      width: 640; height: 360; visible: true')
    qml = patch(qml, 'screen: modelData', '')
    qml = patch(qml, 'monitor: Hyprland.monitorFor(screen)', 'monitor: null')
    qml = patch(qml, 'monitorState: monitor ? monitor.lastIpcObject : ({})', 'monitorState: root.activity')
    qml, removed = re.subn(r'^      (anchors \{|exclusionMode:|mask:|WlrLayershell\.).*\n', '', qml, flags=re.M)
    assert removed == 6, removed
    qml = patch(qml, 'Surface { anchors.fill:', '''Connections {
        target: wallpaper
        function onFrameSwapped() { root.frames++ }
      }
      Surface {
        id: scene
        Component.onCompleted: { root.testScene = scene; root.scenes++ }
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
                replacement.symlink_to(state / "theme/backgrounds" / name)
                replacement.replace(state / "background")

            wait_for(lambda s: s["ready"] and s["running"] and s["frames"] > 10)
            time.sleep(0.2)
            ipc("pause")
            turn = frozen()
            ipc("resume")
            resumed = wait_for(lambda s: s["running"] and s["turn"] != turn)
            assert (resumed["turn"] - turn) % 1 < 0.25, (turn, resumed)
            ipc("toggle")
            frozen()
            ipc("toggle")
            wait_for(lambda s: s["running"])
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
            # Setting the theme again replaces the folder the link points into, and empties
            # theme.name before writing it. Neither may restart the scene or lift a pause.
            ipc("pause")
            turn, scenes = frozen(), ipc("status")["scenes"]
            shutil.rmtree(state / "theme")
            (state / "theme.name").write_text("")
            time.sleep(0.3)
            stage(state / "next")
            (state / "next").rename(state / "theme")
            (state / "theme.name").write_text("wheelie\n")
            time.sleep(0.3)
            assert frozen() == turn and ipc("status")["scenes"] == scenes, ipc("status")
            ipc("resume")
            wait_for(lambda s: s["running"])
            # Another theme ends the process; the theme-set hook starts it when Wheelie returns.
            (state / "theme.name").write_text("other\n")
            assert process.wait(timeout=6) == 0, log_path.read_text()
            assert not re.search(r'(TypeError|ReferenceError|Error:|Failed to)', log_path.read_text()), log_path.read_text()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
print("ok: frozen frames, continuous resume, lock/DPMS/fullscreen gating, manual pause, static round trips, "
      "theme re-apply, exit on another theme")
