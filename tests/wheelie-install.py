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
    for name in ("colors.toml", "icons.theme", "preview.jpg", "backgrounds/00-wheelie-animated.jpg",
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
        code = root / (failure + "-data") / "wheely/themes/wheelie"
        (code / "animated").mkdir(parents=True)
        (destination / "backgrounds").mkdir(parents=True)
        for name in ("animated/wallpaper.qml", "animated/obsolete"):
            (code / name).write_text("old " + name)
        (destination / "backgrounds/old.jpg").write_text("old backgrounds/old.jpg")
        os.utime(destination, (0, 0))
        original = snapshot(destination), snapshot(code)
        log = root / f"{failure}.log"
        env = os.environ | {
            "XDG_CONFIG_HOME": str(config), "XDG_DATA_HOME": str(root / (failure + "-data")), "WHEELIE_FAIL": failure, "WHEELIE_LOG": str(log),
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        }
        result = subprocess.run([str(source / "wheelie"), "install"], env=env,
                                capture_output=True, text=True, timeout=20)
        calls = log.read_text()
        if failure == "none":
            assert result.returncode == 0, result.stderr
            assert (code / "animated/wallpaper.qml").read_text() == "new scene/wallpaper.qml"
            # Nothing that runs is in the theme's folder, which another theme may replace.
            assert sorted(p.name for p in destination.iterdir()) == ["backgrounds", "colors.toml", "icons.theme", "preview.jpg"]
            poster = "backgrounds/00-wheelie-animated.jpg"
            assert (destination / poster).read_text() == "new " + poster
            for name in ("ambient-dust.vert.qsb", "ambient-dust.frag.qsb"):
                assert (code / "animated" / name).is_file()
            for stale in (code / "animated/obsolete", code / "animated/ambient-dust.vert",
                          code / "animated/ambient-dust.frag", destination / "backgrounds/old.jpg"):
                assert not stale.exists(), stale
            # Omarchy's theme picker rebuilds a theme's preview only when its folder's time changes.
            assert destination.stat().st_mtime > 0
            assert "--daemonize" in calls and "post-boot" in calls and "theme-set" in calls
        else:
            # A failed copy leaves the installed theme and its running scene untouched; a failed swap
            # puts the theme back.
            assert result.returncode != 0, failure
            assert (snapshot(destination), snapshot(code)) == original, (failure, result.stderr, calls)
            assert ("quickshell kill" in calls) == (failure == "swap"), (failure, calls)
        assert not list(destination.parent.parent.glob(".wheelie-install-*")), failure
        print(f"ok: Wheelie install {failure}")

    for failure in ("copy", "none"):
        config = root / f"fresh-{failure}"
        destination = config / "omarchy/themes/wheelie"
        env.update(XDG_CONFIG_HOME=str(config), XDG_DATA_HOME=str(config / "data"), WHEELIE_FAIL=failure)
        result = subprocess.run([str(source / "wheelie"), "install"], env=env,
                                capture_output=True, text=True, timeout=20)
        assert (result.returncode == 0) == (failure == "none"), result.stderr
        assert destination.exists() == (config / "data/wheely/themes/wheelie").exists() == (failure == "none")
        assert not list(destination.parent.parent.glob(".wheelie-install-*"))
        print(f"ok: first Wheelie install {failure}")

    # Omarchy's theme removal deletes only the folder; each animated theme's hook then removes itself
    # and what it runs. Until then it runs that, never the folder's own file of the same name.
    for theme in ("wheelie", "tidal"):
        home = root / ("home-" + theme)
        hook = home / ".config/omarchy/hooks/theme-set.d" / (theme + "-wallpaper")
        hook.parent.mkdir(parents=True)
        shutil.copy2(repo.parent / theme / "hooks" / hook.name, hook)
        (home / ".local/state/omarchy/current").mkdir(parents=True)
        (home / ".local/state/omarchy/current/theme.name").write_text("other\n")
        folder, code = home / ".config/omarchy/themes" / theme, home / "data/wheely/themes" / theme
        for where, who in ((folder, "theirs"), (code, "ours")):
            where.mkdir(parents=True)
            (where / theme).write_text(f'#!/bin/sh\necho {who} >> "$HOME/ran"\n')
            (where / theme).chmod(0o755)
        hooked = os.environ | {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
                               "XDG_DATA_HOME": str(home / "data")}
        subprocess.run(["bash", str(hook)], env=hooked, check=True)
        assert hook.exists() and not (home / "ran").exists(), theme + "'s hook ran or left under another theme"
        (home / ".local/state/omarchy/current/theme.name").write_text(theme + "\n")
        subprocess.run(["bash", str(hook)], env=hooked, check=True)
        assert (home / "ran").read_text() == "ours\n", theme + "'s hook ran a file from the theme's folder"
        shutil.rmtree(folder)
        subprocess.run(["bash", str(hook)], env=hooked, check=True)
        assert not hook.exists() and not code.exists(), theme + "'s hook or scene outlived its theme"
        print(f"ok: {theme}'s hook leaves with its theme")
