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
    for folder in ("hooks", "backgrounds", "scene"):
        (source / folder).mkdir()
    shutil.copy2(repo / "hooks/wheelie-wallpaper", source / "hooks/wheelie-wallpaper")
    for name in ("colors.toml", "icons.theme", "preview.jpg", "backgrounds/00-wheelie-animated.png",
                 "backgrounds/static.jpg", "scene/wallpaper.qml", "scene/ambient-dust.vert.qsb",
                 "scene/ambient-dust.frag.qsb", "scene/ambient-dust.vert", "scene/ambient-dust.frag"):
        (source / name).write_text("new " + name)
    os.utime(source, (0, 0))
    stub = """#!/usr/bin/env python3
import os, signal, subprocess, sys
from pathlib import Path
name, args = Path(sys.argv[0]).name, sys.argv[1:]
failure = os.environ["WHEELIE_FAIL"]
with open(os.environ["WHEELIE_LOG"], "a") as log:
    log.write(name + " " + " ".join(args) + "\\n")
if name == "cp" and args[0] == "-a" and args[-2].endswith("/scene") and failure in ("copy", "interrupt"):
    Path(args[-1]).mkdir(exist_ok=True)
    (Path(args[-1]) / "partial").touch()
    if failure == "interrupt": os.kill(os.getppid(), signal.SIGTERM)
    sys.exit(43)
if name == "quickshell" and "--daemonize" in args:
    assert Path(args[-1]).is_file()
if name == "cp":
    sys.exit(subprocess.call(["/usr/bin/cp", *args]))
if name == "mv" and failure == "swap" and ".wheelie-install-" in args[-2] and args[-2].endswith("/wheelie"):
    sys.exit(1)
if name == "mv":
    sys.exit(subprocess.call(["/usr/bin/mv", *args]))
"""
    for name in ("cp", "mv", "omarchy", "quickshell"):
        command = commands / name
        command.write_text(stub)
        command.chmod(0o755)

    for failure in ("copy", "interrupt", "swap", "none"):
        config = root / failure
        destination = config / "omarchy/themes/wheelie"
        (destination / "animated").mkdir(parents=True)
        (destination / "backgrounds").mkdir()
        for name in ("animated/wallpaper.qml", "animated/obsolete", "backgrounds/old.jpg"):
            (destination / name).write_text("old " + name)
        os.utime(destination, (0, 0))
        original = snapshot(destination)
        log = root / f"{failure}.log"
        env = os.environ | {
            "XDG_CONFIG_HOME": str(config), "WHEELIE_FAIL": failure, "WHEELIE_LOG": str(log),
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        }
        result = subprocess.run([str(source / "wheelie"), "install"], env=env,
                                capture_output=True, text=True, timeout=20)
        calls = log.read_text()
        if failure == "none":
            assert result.returncode == 0, result.stderr
            assert (destination / "animated/wallpaper.qml").read_text() == "new scene/wallpaper.qml"
            poster = "backgrounds/00-wheelie-animated.png"
            assert (destination / poster).read_text() == "new " + poster
            for name in ("ambient-dust.vert.qsb", "ambient-dust.frag.qsb"):
                assert (destination / "animated" / name).is_file()
            for name in ("animated/obsolete", "animated/ambient-dust.vert", "animated/ambient-dust.frag",
                         "backgrounds/old.jpg"):
                assert not (destination / name).exists(), name
            # Omarchy's theme picker rebuilds a theme's preview only when its folder's time changes.
            assert destination.stat().st_mtime > 0
            assert "--daemonize" in calls and "post-boot" in calls and "theme-set" in calls
        else:
            # A failed copy leaves the installed theme and its running scene untouched; a failed swap
            # puts the theme back.
            assert result.returncode != 0, failure
            assert snapshot(destination) == original, (failure, result.stderr, calls)
            assert ("quickshell kill" in calls) == (failure == "swap"), (failure, calls)
        assert not list(destination.parent.parent.glob(".wheelie-install-*")), failure
        print(f"ok: Wheelie install {failure}")

    for failure in ("copy", "none"):
        config = root / f"fresh-{failure}"
        destination = config / "omarchy/themes/wheelie"
        env.update(XDG_CONFIG_HOME=str(config), WHEELIE_FAIL=failure)
        result = subprocess.run([str(source / "wheelie"), "install"], env=env,
                                capture_output=True, text=True, timeout=20)
        assert (result.returncode == 0) == (failure == "none"), result.stderr
        assert destination.exists() == (failure == "none")
        assert not list(destination.parent.parent.glob(".wheelie-install-*"))
        print(f"ok: first Wheelie install {failure}")
