#!/usr/bin/env python3
"""The shared shortcut routes to the active theme's actual CLI, never the other controller."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="wallpaper-toggle-") as temporary:
    home = Path(temporary)
    config = home / ".config"
    themes = config / "omarchy/themes"
    for name in ("tidal", "wheelie"):
        (themes / name).mkdir(parents=True)
        shutil.copy2(repo / "themes" / name / name, themes / name / name)
    state = home / ".local/state/omarchy/current"
    state.mkdir(parents=True)
    commands = home / "bin"
    commands.mkdir()
    log = home / "calls"
    stub = commands / "quickshell"
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$CALL_LOG"\n')
    stub.chmod(0o755)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(config), CALL_LOG=str(log),
               PATH=str(commands) + os.pathsep + os.environ["PATH"])
    for name in (None, "tidal", "wheelie", "another-theme", "../../bin/unwanted"):
        if name is not None:
            (state / "theme.name").write_text(name + "\n")
        log.write_text("")
        subprocess.run([str(repo / "bin/omarchy-wallpaper-toggle")], env=env, check=True)
        expected = []
        if name in ("tidal", "wheelie"):
            path = themes / name / "animated"
            if name == "wheelie":
                path /= "wallpaper.qml"
            expected = ["ipc", "-p", str(path), "call", name, "toggle"]
        assert log.read_text().splitlines() == expected, (name, log.read_text())
    (state / "theme.name").write_text("tidal\n")
    (themes / "tidal/tidal").unlink()
    log.write_text("")
    subprocess.run([str(repo / "bin/omarchy-wallpaper-toggle")], env=env, check=True)
    assert not log.read_text(), "a missing active theme must not toggle another theme"
print("ok: shortcut routes Tidal and Wheelie to their own toggle IPC; other/missing themes do nothing")
