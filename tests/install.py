#!/usr/bin/env python3
"""Exercise install/revert with temporary system paths and no desktop changes."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from desktop import verify
from install_fixture import Installer

source = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="omarchy-install-") as temporary:
    base = Path(temporary)
    fixture = Installer(source, base)
    conf = fixture.user / ".config/omarchy/shell.json"
    hook = fixture.user / ".config/omarchy/hooks/post-update.d/wheely"
    asset_dir = fixture.user / ".local/share/wheely"
    result = fixture.run()
    assert result.returncode == 0, result.stderr
    designs = asset_dir / "lock"
    assert designs.resolve() == fixture.repo / "lock"
    assert (asset_dir / "lock-session/shell.qml").resolve() == fixture.repo / "lock-session/shell.qml"
    assert (asset_dir / "lock-session/Bridge.qml").resolve() == fixture.repo / "lock-session/Bridge.qml"
    assert (asset_dir / "lock-session/Commons").readlink() == fixture.shell / "Commons"
    assert (asset_dir / "lock-session/Lock").readlink() == fixture.shell / "plugins/lock"
    verify(fixture.user, fixture.repo)
    expected = [{"id": "xpo.files"}, {"id": "xpo.wheel"}]
    assert json.loads(conf.read_text())["plugins"] == expected
    assert "plugins: xpo.files xpo.wheel" in result.stdout
    assert hook.exists()
    assert (fixture.user / ".config/omarchy/plugins/xpo.files").resolve() == fixture.repo / "plugins/xpo.files"
    print("ok: fresh install from a path containing spaces, quotes, and shell syntax")

    config = {"plugins": expected + [{"id": "other", "enabled": False}], "idle": {"lock": 30}}
    conf.write_text(json.dumps(config))
    fixture.env["HYPR_BINDS"] = json.dumps([{"modmask": 64, "key": "S", "description": "Other", "arg": "o"},
                                            {"modmask": 64, "key": "A", "description": "", "arg": "chat"}])
    result = fixture.run()
    assert result.returncode == 0 and 'SUPER + A was "chat"' in result.stdout, result.stdout
    fixture.env["HYPR_BINDS"] = json.dumps([{"modmask": 64, "key": "A", "description": "Wheel", "arg": "257"}])
    result = fixture.run()
    assert result.returncode == 0 and "SUPER + A was" not in result.stdout and "type help" in result.stdout, result.stdout
    print("ok: a key the wheel takes over is named, and a rerun names nothing")
    assert json.loads(conf.read_text()) == config
    assert [p.name for p in hook.parent.iterdir()] == ["wheely"]
    # Execute the generated trampoline too, so quoting is checked by bash itself.
    result = subprocess.run([str(hook)], cwd=fixture.base, env=fixture.env, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert not (fixture.base / "injected").exists()
    print("ok: idempotent registration and generated hook execution")

    # A shell.json kept in dotfiles stays a link; install and revert write its target.
    dotfile = fixture.user / "dotfiles/shell.json"
    dotfile.parent.mkdir()
    dotfile.write_text(conf.read_text())
    conf.unlink()
    conf.symlink_to(dotfile)
    assert fixture.run("revert.sh").returncode == 0 and conf.is_symlink()
    assert json.loads(dotfile.read_text())["plugins"] == [{"id": "other", "enabled": False}]
    assert fixture.run().returncode == 0 and conf.is_symlink()
    assert json.loads(dotfile.read_text())["plugins"] == [{"id": "other", "enabled": False}] + expected
    conf.unlink()
    conf.write_text(dotfile.read_text())
    print("ok: a symlinked shell.json stays a link through revert and install")

    # An unrelated Quickshell instance must neither hide nor cause a render failure.
    for failure in ["render", "no-shell"]:
        result = fixture.run(failure=failure)
        assert result.returncode != 0, failure
        assert "threaded render loop" in result.stderr, result.stderr
    print("ok: render checks select the desktop shell and reject a missing render thread or shell")

    for failure in ["malformed", "mv", "hook"]:
        original = "{bad" if failure == "malformed" else json.dumps(config)
        conf.write_text(original)
        result = fixture.run(failure=failure)
        assert result.returncode != 0, failure
        assert conf.read_text() == original or failure == "hook", failure
        if failure != "hook":
            assert "plugins: xpo.files" not in result.stdout, failure
        assert not Path(str(conf) + ".new").exists(), failure
    print("ok: malformed JSON, failed mv, and hook failures return failure")

    conf.write_text(json.dumps(config))
    result = fixture.run("revert.sh")
    assert result.returncode == 0, result.stderr
    verify(fixture.user, fixture.repo, installed=False)
    assert not hook.exists()
    assert not (fixture.user / ".config/omarchy/plugins/xpo.files").is_symlink()
    assert json.loads(conf.read_text()) == {"plugins": [{"id": "other", "enabled": False}],
                                          "idle": {"lock": 30}}
    assert fixture.all_stock()
    # Restored from a private temporary copy, a shell file is still readable by everyone.
    assert all((fixture.shell / f).stat().st_mode & 0o777 == 0o644 for f in fixture.files)
    assert not asset_dir.exists()
    assert fixture.run("revert.sh").returncode == 0
    print("ok: revert removes the hook and plugins, restores QML, and preserves other settings")

    # The state revert broke on: patches an older installer left without records, two of
    # them an older committed version of the patch.
    assert fixture.run().returncode == 0
    shutil.rmtree(fixture.user / ".local/state/wheely/installed")
    older = {}
    for relative in ["shell.qml", "services/PluginShellApi.qml"]:
        current = fixture.patched(relative)
        older[relative] = current + b"// older patch\n"
        (fixture.repo / "patches/shell" / relative).write_bytes(older[relative])
        fixture.git("commit", "-qam", "older patch")
        (fixture.repo / "patches/shell" / relative).write_bytes(current)
        fixture.git("commit", "-qam", "current patch")
        (fixture.shell / relative).write_bytes(older[relative])
    result = fixture.run("revert.sh")
    assert result.returncode == 0 and fixture.all_stock(), result.stdout + result.stderr
    print("ok: revert restores Omarchy's files from unrecorded and older versions of the patch")

    for relative, content in older.items():
        (fixture.shell / relative).write_bytes(content)
    result = fixture.run()
    assert result.returncode == 0 and "rebased" not in result.stdout, result.stdout + result.stderr
    assert all(fixture.installed(relative) == fixture.patched(relative) for relative in fixture.files)
    assert all((fixture.repo / "patches/orig" / relative).read_bytes() == fixture.stock[relative] for relative in fixture.files)
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: an older committed patch is replaced on install and restored to stock on revert")

    relative = "shell.qml"
    update = fixture.stock[relative] + b"// upstream addition\n"
    assert fixture.run().returncode == 0
    fixture.publish({**fixture.stock, relative: update})
    (fixture.shell / relative).write_bytes(update)  # the package update replaced our patch
    result = fixture.run()
    assert result.returncode == 0 and "rebased onto new upstream: shell.qml" in result.stdout, result.stderr
    assert fixture.installed(relative) != update and fixture.installed(relative).endswith(b"// upstream addition\n")
    # The rebase is kept in the state, never in the checkout, so git pull keeps working.
    assert not fixture.git("status", "--porcelain", "patches").stdout
    rebased = fixture.user / ".local/state/wheely/rebased"
    assert (rebased / "orig" / relative).read_bytes() == update
    assert (rebased / "shell" / relative).read_bytes() == fixture.installed(relative)
    assert "already up to date" in fixture.run().stdout
    shutil.rmtree(fixture.package / "cache")
    assert fixture.run("revert.sh").returncode == 0 and fixture.installed(relative) == update
    assert not rebased.exists()
    fixture.publish(fixture.stock)
    (fixture.shell / relative).write_bytes(fixture.stock[relative])
    print("ok: a package update is rebased onto outside the checkout, and revert restores the updated stock file")

    # An upstream change to either lock file keeps Omarchy's own lock: never merged, both stay stock.
    lock = ["plugins/lock/LockView.qml", "plugins/lock/Service.qml"]
    for changed in lock:
        update = {**fixture.stock, changed: b"// upstream addition\n" + fixture.stock[changed]}
        fixture.publish(update)
        (fixture.shell / changed).write_bytes(update[changed])
        result = fixture.run()
        assert result.returncode == 0 and "Lock screen left as Omarchy's" in result.stdout \
            and "already up to date" not in result.stdout, result.stdout + result.stderr
        assert all(fixture.installed(relative) == update[relative] for relative in lock), changed
        assert fixture.installed("shell.qml") == fixture.patched("shell.qml")
        assert fixture.run("revert.sh").returncode == 0
        fixture.publish(fixture.stock)
        (fixture.shell / changed).write_bytes(fixture.stock[changed])
    print("ok: an upstream change to either lock file keeps Omarchy's own lock pair")

    # A lock file left stock holds back its partner.
    notes = fixture.user / ".local/state/omarchy/notifications"
    notes.mkdir(parents=True)
    live = notes / "live.json"
    toast = {"key": "a", "app": "notify-send", "summary": "wheely", "body": "Not patched: plugins/lock/Service.qml"}
    other = {"key": "b", "app": "kitty", "summary": "Claude Code", "body": "waiting"}
    live.write_text(json.dumps([toast, other]))
    edited = fixture.stock[lock[0]] + b"// personal edit\n"
    (fixture.shell / lock[0]).write_bytes(edited)
    result = fixture.run()
    assert result.returncode == 1 and "Held back" in result.stderr and lock[1] in result.stderr, result.stderr
    assert fixture.installed(lock[0]) == edited and fixture.installed(lock[1]) == fixture.stock[lock[1]]
    assert json.loads(live.read_text()) == [toast, other]
    (fixture.shell / lock[0]).write_bytes(fixture.stock[lock[0]])
    (fixture.user / "restarts").unlink(missing_ok=True)
    assert fixture.run().returncode == 0
    assert json.loads(live.read_text()) == [other]
    assert (fixture.user / "restarts").read_text().split() == ["dismiss", "restart"], "dismissed after the restart"
    assert fixture.run("revert.sh").returncode == 0
    print("ok: a lock file that cannot be patched holds back its partner, keeping the stock lock")
    print("ok: the next clean install dismisses the failed run's toast before restarting the shell")

    relative = "plugins/bar/Bar.qml"
    edited = fixture.stock[relative] + b"// personal edit\n"
    (fixture.shell / relative).write_bytes(edited)
    result = fixture.run()
    assert result.returncode == 1 and fixture.installed(relative) == edited, result.stderr
    assert "changed outside" in result.stderr
    result = fixture.run("revert.sh")
    assert result.returncode == 1 and fixture.installed(relative) == edited and "changed outside" in result.stderr
    (fixture.shell / relative).write_bytes(fixture.stock[relative])
    assert fixture.all_stock()
    print("ok: files edited outside this project are neither patched over nor restored over")

    # A copy stopped partway leaves the file it was replacing whole, and nothing beside it.
    relative = "shell.qml"
    leftovers = lambda: list(fixture.shell.rglob("*.wheely-new"))
    assert fixture.run(failure="partial").returncode == 1 and fixture.installed(relative) == fixture.stock[relative]
    assert not leftovers()
    # The failed copy claims nothing: an edit made since is still someone else's.
    (fixture.shell / relative).write_bytes(edited)
    assert fixture.run().returncode == 1 and fixture.installed(relative) == edited
    (fixture.shell / relative).write_bytes(fixture.stock[relative])
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    assert fixture.run().returncode == 0 and fixture.installed(relative) == fixture.patched(relative)
    assert fixture.run("revert.sh", "partial").returncode == 1 and fixture.installed(relative) == fixture.patched(relative)
    assert not leftovers()
    # A run stopped between copy and rename leaves its copy; the next run clears it, even with nothing to write.
    for script in ["install.sh", "revert.sh"]:
        (fixture.shell / "shell.qml.wheely-new").write_bytes(b"stranded copy\n")
        fixture.run(script)
        assert not leftovers(), script
    assert fixture.run().returncode == 0
    assert fixture.run("revert.sh", "partial").returncode == 1
    assert designs.is_symlink(), "a failed revert must keep the lock screen's designs"
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: interrupted installs and restores are recognised as ours and recover on retry")

    # A copy failing partway through either lock file leaves the patched pair, never half a pair.
    restarts = fixture.user / "restarts"
    for failing in lock:
        assert fixture.run().returncode == 0
        restarts.unlink(missing_ok=True)
        result = fixture.run("revert.sh", "once:" + Path(failing).name)
        assert result.returncode == 1 and restarts.exists(), result.stderr
        assert all(fixture.installed(f) == fixture.patched(f) for f in lock), failing
        assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: a failed lock-file restore puts the patched pair back before the shell restarts")

    assert fixture.run().returncode == 0
    restarts.unlink(missing_ok=True)
    result = fixture.run("revert.sh", f"always:{Path(lock[1]).name} again:{Path(lock[0]).name}")
    assert result.returncode == 1 and "shell not restarted" in result.stderr and not restarts.exists(), result.stderr
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: a lock pair that cannot be put back is never restarted into, and a retry recovers")

    # An earlier revert, stopped between the two lock files, left a mixed pair this run cannot finish.
    assert fixture.run().returncode == 0
    (fixture.shell / lock[0]).write_bytes(fixture.stock[lock[0]])
    restarts.unlink(missing_ok=True)
    result = fixture.run("revert.sh", "once:" + Path(lock[1]).name)
    assert result.returncode == 1 and "shell not restarted" in result.stderr and not restarts.exists(), result.stderr
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: a mixed lock pair left by an earlier revert is never restarted into")

    # A lock file with no verified stock copy keeps its partner patched too, so the pair still matches.
    assert fixture.run().returncode == 0
    orig = fixture.repo / "patches/orig" / lock[1]
    orig.write_bytes(b"not stock\n")
    (fixture.package / "cache").rename(fixture.package / "away")
    result = fixture.run("revert.sh")
    assert result.returncode == 1 and "no verified stock copy" in result.stderr, result.stderr
    assert all(fixture.installed(f) == fixture.patched(f) for f in lock), result.stderr
    orig.write_bytes(fixture.stock[lock[1]])
    (fixture.package / "away").rename(fixture.package / "cache")
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: a lock file that cannot be restored keeps its partner patched")

    # A file or folder in a plugin's place is the user's: install refuses it, revert keeps it and still recovers.
    plugin = fixture.user / ".config/omarchy/plugins/xpo.files"
    for make in [lambda: (plugin.mkdir(), (plugin / "mine").write_text("keep")), lambda: plugin.write_text("keep")]:
        conf.write_text(json.dumps(config))
        make()
        result = fixture.run()
        assert result.returncode == 1 and "not wheely's link" in result.stderr, result.stderr
        assert fixture.all_stock() and not hook.exists() and json.loads(conf.read_text()) == config
        shutil.rmtree(plugin) if plugin.is_dir() else plugin.unlink()
    assert fixture.run().returncode == 0
    plugin.unlink(); plugin.mkdir(); (plugin / "mine").write_text("keep")
    result = fixture.run("revert.sh")
    assert result.returncode == 1 and "not wheely's link" in result.stderr, result.stderr
    assert (plugin / "mine").read_text() == "keep" and fixture.all_stock()
    assert not (fixture.user / ".config/omarchy/plugins/xpo.wheel").exists()
    shutil.rmtree(plugin)
    print("ok: a plugin path the user owns is refused by install, kept by revert, and recovery continues")

    # A shell.json revert cannot rewrite is reported, after the shell's files are restored.
    for failure, original in [("", "{bad"), ("mv", json.dumps(config))]:
        conf.write_text(json.dumps(config))
        assert fixture.run().returncode == 0
        conf.write_text(original)
        result = fixture.run("revert.sh", failure)
        assert result.returncode == 1 and "Could not unregister" in result.stderr, result.stderr
        assert conf.read_text() == original and not Path(str(conf) + ".new").exists() and fixture.all_stock()
    conf.write_text(json.dumps(config))
    assert fixture.run("revert.sh").returncode == 0
    print("ok: malformed or unwritable shell.json fails revert without stopping recovery")

    assert fixture.run().returncode == 0
    (fixture.repo / "patches/orig" / relative).write_bytes(b"a different repository baseline\n")
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    (fixture.repo / "patches/orig" / relative).write_bytes(fixture.stock[relative])
    assert fixture.run().returncode == 0
    (fixture.package / "local").rename(fixture.package / "hidden")
    result = fixture.run("revert.sh")
    assert result.returncode == 1 and "no package checksum" in result.stderr
    assert fixture.installed(relative) == fixture.patched(relative)
    (fixture.package / "hidden").rename(fixture.package / "local")
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: stock comes from the cached package when needed, and is never guessed")

    # An edited block is reported, but revert still restores Omarchy's files.
    assert fixture.run().returncode == 0
    lua = fixture.user / ".config/hypr/hyprland.lua"
    lua.write_text(lua.read_text().replace("-- END wheely\n", "-- my edit\n-- END wheely\n"))
    result = fixture.run("revert.sh")
    assert result.returncode == 1 and "was edited" in result.stderr, result.stderr
    assert fixture.all_stock() and not hook.exists() and not asset_dir.exists()
    lua.write_text(lua.read_text().replace("-- my edit\n", ""))
    assert fixture.run("revert.sh").returncode == 0 and "BEGIN wheely" not in lua.read_text()
    print("ok: an edited Hyprland block does not stop revert restoring the shell")

    fixture.publish(fixture.stock, "4.0.6-1")
    result = fixture.run()
    assert result.returncode == 1 and "needs Omarchy 4.5.0rc3 or newer" in result.stderr, result.stderr
    assert fixture.all_stock() and not asset_dir.exists() and not hook.exists()
    print("ok: an older Omarchy is refused before anything changes")

    # Edge's omarchy-dev is versioned from the 4.0.0 tag, yet ahead of every release.
    fixture.publish(fixture.stock, "4.0.0.r7561.ga69b19f-1", "omarchy-dev")
    result = fixture.run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert all(fixture.installed(relative) == fixture.patched(relative) for relative in fixture.files)
    assert fixture.run("revert.sh").returncode == 0 and fixture.all_stock()
    print("ok: edge's omarchy-dev is patched and reverted like a release")

    # A missing command is named before anything changes.
    fixture.publish(fixture.stock)
    bare = fixture.base / "bin-without-fd"
    bare.mkdir()
    for tool in Path("/usr/bin").iterdir():
        if tool.name != "fd": (bare / tool.name).symlink_to(tool)
    fixture.env["PATH"] = str(fixture.stubs) + ":" + str(bare)
    result = fixture.run()
    assert result.returncode == 1 and "wheely needs fd" in result.stderr, result.stderr
    assert fixture.all_stock() and not asset_dir.exists() and not hook.exists()
    print("ok: a missing command is named before anything changes")
