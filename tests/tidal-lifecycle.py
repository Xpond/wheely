#!/usr/bin/env python3
"""Check animated/static round trips and pausing against temporary Omarchy and monitor state."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import qslog


def patch(text, old, new, count=-1):
    """Replace old, which must be present: a stale pattern would leave real desktop state in use."""
    assert old in text, old
    return text.replace(old, new, count)


repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tidal-lifecycle").resolve()
config = output / "controller"
shutil.copytree(repo / "themes/tidal/animated", config, dirs_exist_ok=True)
# Keep state outside the config so Quickshell hot reload cannot mask watcher bugs.
state = output / "state"
state.mkdir(exist_ok=True)
for name in ["one.jpg", "two.jpg", "00-living-coast-animated.png", "00-muted-coast-animated.png"]:
    (state / name).write_bytes(b"unused: this fixture creates no wallpaper surfaces")
background = state / "background"
background.unlink(missing_ok=True)
background.symlink_to(state / "one.jpg")
theme = state / "theme.name"
theme.write_text("tidal\n")
activity = state / "activity.json"
activity.write_text('{"dpmsStatus": true}')
shell = config / "shell.qml"
source = patch(shell.read_text(), 'Quickshell.env("HOME") + "/.local/state/omarchy/current"', json.dumps(str(state)))
# One windowless surface stands for the displays, and the compositor's monitor state comes from a file.
source = patch(source, "model: root.animated ? Quickshell.screens : []", "model: root.animated ? [0] : []")
source = patch(source, "PanelWindow {", "Item {")
source, removed = re.subn(r"^      (screen:|anchors \{|color:|exclusionMode:|mask:|WlrLayershell\.).*\n", "", source, flags=re.M)
assert removed == 8, removed
source = patch(source, "monitor: Hyprland.monitorFor(screen)", "monitor: null")
source = patch(source, "monitorState: monitor ? monitor.lastIpcObject : ({})", "monitorState: root.activity")
source = patch(source, "onTriggered: Hyprland.refreshMonitors()", "onTriggered: {}")
source = patch(source, "Surface {", '''Surface {
        Component.onCompleted: console.log("SURFACE")
        onRunningChanged: console.log("RUNNING", running)''')
source = patch(source, "id: root", '''id: root
  property var activity: ({})
  FileView {
    path: %s; watchChanges: true
    onFileChanged: reload()
    onLoaded: root.activity = JSON.parse(text())
  }
  onAnimatedChanged: console.log("STATE", root.animated)
  Component.onCompleted: console.log("STATE", root.animated)''' % json.dumps(str(activity)), 1)
source = patch(source, "root.background = path", '''root.background = path
        console.log("SELECTION", path, root.animated, root.muted)
        if (root.tidalTheme) console.log("READY watching")''')
shell.write_text(source)
log_path = output / "run.log"
with log_path.open("w") as log:
    process = subprocess.Popen(["quickshell", "--no-color", "-p", str(config)],
        stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, QT_QPA_PLATFORMTHEME="generic"))
    try:
        def wait_for(expected, after=0):
            deadline = time.monotonic() + 4
            while True:
                content = log_path.read_text()
                assert process.poll() is None, content
                marker = expected.split(" ", 1)[0] + " "
                messages = [line.split(marker, 1)[1] for line in content[after:].splitlines() if marker in line]
                if messages and messages[-1] == expected[len(marker):]:
                    return
                assert time.monotonic() < deadline, content
                time.sleep(0.02)

        def select(name, animated, muted=False):
            after = len(log_path.read_text())
            replacement = state / "replacement"
            replacement.symlink_to(state / name)
            replacement.replace(background)
            wait_for(f"SELECTION {state / name} {str(animated).lower()} {str(muted).lower()}", after)

        wait_for("READY watching")
        wait_for("STATE false")
        for _ in range(2):
            select("00-living-coast-animated.png", True)
            select("00-muted-coast-animated.png", True, True)
            select("00-living-coast-animated.png", True)
            select("two.jpg", False)
        select("two.jpg", False)
        select("00-muted-coast-animated.png", True, True)
        theme.write_text("another-theme\n")
        wait_for("STATE false")
        theme.write_text("tidal\n")
        wait_for("STATE true")
        for name, animated in [("another-theme", False), ("tidal", True)]:
            replacement = state / "replacement"
            replacement.write_text(name + "\n")
            replacement.replace(theme)
            wait_for("STATE true" if animated else "STATE false")
        (state / "unrelated").unlink(missing_ok=True)
        after = len(log_path.read_text())
        (state / "unrelated").write_text("changed")
        wait_for(f"SELECTION {background.resolve()} true true", after)

        # Display-off, the session lock and a fullscreen client pause the surface until they clear.
        for value, running in [({"solitaryBlockedBy": ["LOCK"]}, False), ({}, True), ({"dpmsStatus": False}, False),
                               ({}, True), ({"solitary": "abcdef"}, False), ({"solitary": "0"}, True)]:
            after = len(log_path.read_text())
            activity.write_text(json.dumps({"dpmsStatus": True, **value}))
            wait_for(f"RUNNING {str(running).lower()}", after)

        # Waking the display keeps a manual pause, and re-applying the theme, which empties theme.name
        # and replaces the folder the link points into, neither recreates the surface nor lifts it.
        (state / "theme").mkdir(exist_ok=True)
        (state / "theme/00-living-coast-animated.png").touch()
        select("theme/00-living-coast-animated.png", True)
        after = len(log_path.read_text())
        subprocess.run(["quickshell", "ipc", "-p", str(config), "call", "tidal", "pause"], check=True, timeout=5)
        wait_for("RUNNING false", after)
        activity.write_text('{"dpmsStatus": false}')
        time.sleep(0.2)
        activity.write_text('{"dpmsStatus": true}')
        shutil.rmtree(state / "theme")
        theme.write_text("")
        time.sleep(0.3)
        (state / "theme").mkdir()
        (state / "theme/00-living-coast-animated.png").touch()
        theme.write_text("tidal\n")
        time.sleep(0.3)
        assert not re.search(r"SURFACE|RUNNING true|STATE false", log_path.read_text()[after:]), log_path.read_text()
        subprocess.run(["quickshell", "ipc", "-p", str(config), "call", "tidal", "resume"], check=True, timeout=5)
        wait_for("RUNNING true", after)
        qslog.check(log_path.read_text())
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)
print("ok: colorful/muted/static selections and theme changes resume the same controller; lock/DPMS/fullscreen "
      "pause it, and waking or re-applying the theme keeps a manual pause", flush=True)

# Check the CLI's wallpaper paths without changing the desktop selection.
installed = output / "config/omarchy/themes/tidal"
installed.mkdir(parents=True, exist_ok=True)
shutil.copy2(repo / "themes/tidal/tidal", installed / "tidal")
bin_dir = output / "bin"
bin_dir.mkdir(exist_ok=True)
for name, script in {"quickshell": "exit 0", "omarchy": 'printf "%s\\n" "$@" > "$TIDAL_CLI_LOG"'}.items():
    command = bin_dir / name
    command.write_text("#!/bin/sh\n" + script + "\n")
    command.chmod(0o755)
cli_log = output / "cli.log"
cli_env = dict(os.environ, XDG_CONFIG_HOME=str(output / "config"),
               PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], TIDAL_CLI_LOG=str(cli_log))
help_text = subprocess.check_output([str(installed / "tidal"), "help"], env=cli_env, text=True)
assert "animate [colorful|muted]" in help_text
for args, wallpaper in [([], "living"), (["colorful"], "living"), (["muted"], "muted")]:
    subprocess.run([str(installed / "tidal"), "animate", *args], env=cli_env, check=True)
    expected = Path.home() / f".local/state/omarchy/current/theme/backgrounds/00-{wallpaper}-coast-animated.png"
    assert cli_log.read_text().splitlines() == ["theme", "bg", "set", str(expected)]
invalid = subprocess.run([str(installed / "tidal"), "animate", "unknown"], env=cli_env, capture_output=True, text=True)
assert invalid.returncode == 1 and "Usage:" in invalid.stderr
print("ok: animate defaults to colorful, accepts muted, and rejects unknown palettes", flush=True)
