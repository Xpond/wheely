#!/usr/bin/env python3
"""Check animated/static round trips against temporary Omarchy state."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import qslog

repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tidal-lifecycle").resolve()
config = output / "controller"
shutil.copytree(repo / "themes/tidal/animated", config, dirs_exist_ok=True)
# Keep state outside the config so Quickshell hot reload cannot mask watcher bugs.
state = output / "state"
state.mkdir(exist_ok=True)
for name in ["one.jpg", "two.jpg", "00-living-coast-animated.png"]:
    (state / name).write_bytes(b"unused: this fixture creates no wallpaper surfaces")
background = state / "background"
background.unlink(missing_ok=True)
background.symlink_to(state / "one.jpg")
theme = state / "theme.name"
theme.write_text("tidal\n")
shell = config / "shell.qml"
source = shell.read_text().replace(
    'Quickshell.env("HOME") + "/.local/state/omarchy/current"', json.dumps(str(state)))
source = source.replace("model: root.animated ? Quickshell.screens : []", "model: []")
source = source.replace("id: root", '''id: root
  onAnimatedChanged: console.log("STATE", root.animated)
  Component.onCompleted: console.log("STATE", root.animated)''', 1)
source = source.replace("root.background = path", '''root.background = path
        if (root.tidalTheme) console.log("READY watching")''')
shell.write_text(source)
log_path = output / "run.log"
with log_path.open("w") as log:
    process = subprocess.Popen(["quickshell", "--no-color", "-p", str(config)],
        stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, QT_QPA_PLATFORMTHEME="generic"))
    try:
        def wait_for(expected):
            deadline = time.monotonic() + 4
            while True:
                content = log_path.read_text()
                assert process.poll() is None, content
                states = [line.rsplit("STATE ", 1)[1] for line in content.splitlines() if "STATE " in line]
                if expected in content and (expected == "READY watching" or states[-1] == expected):
                    return
                assert time.monotonic() < deadline, content
                time.sleep(0.02)

        def select(name, animated):
            replacement = state / "replacement"
            replacement.symlink_to(state / name)
            replacement.replace(background)
            wait_for("true" if animated else "false")

        wait_for("READY watching")
        wait_for("false")
        for _ in range(2):
            select("00-living-coast-animated.png", True)
            select("two.jpg", False)
        select("two.jpg", False)
        select("00-living-coast-animated.png", True)
        theme.write_text("another-theme\n")
        wait_for("false")
        theme.write_text("tidal\n")
        wait_for("true")
        for name, animated in [("another-theme", False), ("tidal", True)]:
            replacement = state / "replacement"
            replacement.write_text(name + "\n")
            replacement.replace(theme)
            wait_for("true" if animated else "false")
        (state / "unrelated").write_text("changed")
        time.sleep(0.15)
        wait_for("true")
        qslog.check(log_path.read_text())
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)
print("ok: repeated animated/static selections and theme changes resume the same controller", flush=True)
