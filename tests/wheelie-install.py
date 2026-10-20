#!/usr/bin/env python3
"""Exercise Wheelie's installer with isolated paths, tiny assets and command failures."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1] / "themes/wheelie"


def snapshot(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file()}


with tempfile.TemporaryDirectory(prefix="wheelie-install-") as temp:
    root = Path(temp)
    source, commands = root / "source", root / "bin"
    source.mkdir()
    commands.mkdir()
    shutil.copy2(repo / "wheelie", source / "wheelie")
    for folder in ("hooks", "backgrounds"):
        (source / folder).mkdir()
    shutil.copy2(repo / "hooks/wheelie-wallpaper", source / "hooks/wheelie-wallpaper")
    for name in ("colors.toml", "icons.theme", "preview.jpg", "backgrounds/static.jpg"):
        (source / name).write_text("new " + name)
    (source / "bake.py").write_text("""import os, sys
from pathlib import Path
if os.environ["WHEELIE_FAIL"] == "bake": sys.exit(41)
build = Path(__file__).parent / "build"
build.mkdir(exist_ok=True)
for name in ("wallpaper.qml", "ambient-dust.vert.qsb", "ambient-dust.frag.qsb",
             "chain.png", "chain-link.png", "chain.svg", "shell.qml", "Render.qml"):
    (build / name).write_text("new " + name)
""")
    (source / "render.py").write_text("""import os, sys
from pathlib import Path
if os.environ["WHEELIE_FAIL"] == "render": sys.exit(42)
Path(sys.argv[2]).write_text("new poster")
""")
    stub = """#!/usr/bin/env python3
import os, signal, subprocess, sys
from pathlib import Path
name, args = Path(sys.argv[0]).name, sys.argv[1:]
failure = os.environ["WHEELIE_FAIL"]
with open(os.environ["WHEELIE_LOG"], "a") as log:
    log.write(name + " " + " ".join(args) + "\\n")
if name == "cp" and args[0] == "-a" and args[-2].endswith("/build"):
    if failure in ("copy", "interrupt"):
        Path(args[-1]).mkdir(exist_ok=True)
        (Path(args[-1]) / "partial").touch()
        if failure == "interrupt": os.kill(os.getppid(), signal.SIGTERM)
        sys.exit(43)
if name == "mv" and Path(args[-2]).name == "new" and failure == "swap":
    sys.exit(44)
if name == "mv" and failure == "restore" and Path(args[-2]).name != "wheelie":
    sys.exit(44)
if name == "omarchy" and failure == "hook": sys.exit(45)
if name == "quickshell" and "--daemonize" in args:
    if failure == "start": sys.exit(46)
    assert Path(args[-1]).is_file()
if name in ("cp", "mv"):
    sys.exit(subprocess.call(["/usr/bin/" + name, *args]))
"""
    for name in ("cp", "mv", "omarchy", "quickshell"):
        command = commands / name
        command.write_text(stub)
        command.chmod(0o755)

    for failure in ("bake", "render", "copy", "interrupt", "swap", "hook", "start", "restore", "none"):
        config = root / failure
        destination = config / "omarchy/themes/wheelie"
        (destination / "animated").mkdir(parents=True)
        (destination / "backgrounds").mkdir()
        for name in ("animated/wallpaper.qml", "animated/obsolete", "backgrounds/old.jpg", "personal.txt"):
            (destination / name).write_text("old " + name)
        launcher = destination / "wheelie"
        launcher.write_text('#!/bin/sh\nprintf "restored watch\\n" >> "$WHEELIE_LOG"\n')
        launcher.chmod(0o755)
        original = snapshot(destination)
        log = root / f"{failure}.log"
        env = os.environ | {
            "XDG_CONFIG_HOME": str(config), "WHEELIE_FAIL": failure, "WHEELIE_LOG": str(log),
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        }
        result = subprocess.run([str(source / "wheelie"), "install"], env=env,
                                capture_output=True, text=True, timeout=20)
        calls = log.read_text() if log.exists() else ""
        if failure == "none":
            assert result.returncode == 0, result.stderr
            assert (destination / "animated/wallpaper.qml").read_text() == "new wallpaper.qml"
            assert (destination / "personal.txt").read_text() == "old personal.txt"
            assert (destination / "backgrounds/00-wheelie-animated.png").read_text() == "new poster"
            for name in ("ambient-dust.vert.qsb", "ambient-dust.frag.qsb"):
                assert (destination / "animated" / name).is_file()
            for name in ("obsolete", "chain.png", "chain-link.png", "chain.svg", "shell.qml", "Render.qml"):
                assert not (destination / "animated" / name).exists(), name
            assert "--daemonize" in calls and "post-boot" in calls and "theme-set" in calls
        elif failure == "restore":
            backups = list(destination.parent.glob(".wheelie-install-*/previous"))
            assert result.returncode != 0 and len(backups) == 1, result.stderr
            assert snapshot(backups[0]) == original
            assert str(backups[0]) in result.stderr, result.stderr
            print("ok: failed restore retains the previous theme and reports its location")
            continue
        else:
            assert result.returncode != 0, failure
            assert snapshot(destination) == original, (failure, result.stderr, calls)
            if failure in ("bake", "render", "copy", "interrupt"):
                assert "quickshell kill" not in calls, (failure, calls)
            else:
                assert "restored watch" in calls, (failure, calls)
        assert not list(destination.parent.glob(".wheelie-install-*")), failure
        print(f"ok: Wheelie install {failure}")

    for failure in ("copy", "start", "none"):
        config = root / f"fresh-{failure}"
        destination = config / "omarchy/themes/wheelie"
        env.update(XDG_CONFIG_HOME=str(config), WHEELIE_FAIL=failure)
        result = subprocess.run([str(source / "wheelie"), "install"], env=env,
                                capture_output=True, text=True, timeout=20)
        assert (result.returncode == 0) == (failure == "none"), result.stderr
        assert destination.exists() == (failure == "none")
        assert not list(destination.parent.glob(".wheelie-install-*"))
        print(f"ok: first Wheelie install {failure}")
