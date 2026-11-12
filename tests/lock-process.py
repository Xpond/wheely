#!/usr/bin/env python3
"""Offscreen lifecycle test: simulated compositor, stubbed display commands, no PAM authentication."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
import qslog


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


signal.signal(signal.SIGTERM, interrupted)
repo = Path(__file__).resolve().parents[1]
omarchy = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"))
# install.sh keeps Omarchy's own lock once upstream changes it, so a stale patches/orig means no designs.
for name in ["LockView.qml", "Service.qml"]:
    installed = (omarchy / "shell/plugins/lock" / name).read_bytes()
    if installed not in [(repo / part / "plugins/lock" / name).read_bytes() for part in ["patches/orig", "patches/shell"]]:
        raise SystemExit(f"Omarchy changed plugins/lock/{name}: install.sh will keep its stock lock. "
                         "Rebase patches/shell onto it and copy it to patches/orig.")
with tempfile.TemporaryDirectory(prefix="lock-process-") as directory:
    out = Path(directory)
    home, runtime, stubs = out / "home", out / "runtime", out / "bin"
    data = home / ".local/share/wheely"
    worker = data / "lock-session"
    sources = out / "sources"
    shutil.copytree(repo / "lock-session", sources)
    worker.mkdir(parents=True)
    for name in ["Bridge.qml", "shell.qml"]:
        (worker / name).symlink_to(sources / name)
    shutil.copytree(repo / "lock", data / "lock")
    # The wallpaper design names each URL it requests, and logs once its wallpaper is ready.
    scene = data / "lock/wallpaper/Scene.qml"
    scene.write_text(qslog.patch(scene.read_text(), "    cache: true\n", "    cache: true\n"
        '    onSourceChanged: if (String(source)) console.log("WALLPAPER_REQUEST", source)\n'
        '    onStatusChanged: if (status === Image.Ready) console.log("WALLPAPER_READY")\n', exactly=True))
    lock = out / "installed"
    # As installed: Omarchy's lock plugin (FingerprintModel.js, poster.sh) with our two files over it.
    shutil.copytree(omarchy / "shell/plugins/lock", lock)
    shutil.copytree(repo / "patches/shell/plugins/lock", lock, dirs_exist_ok=True)
    (worker / "Lock").symlink_to(lock)
    (out / "Lock").symlink_to(lock)
    shutil.copytree(omarchy / "shell/Commons", out / "installed-commons")
    (worker / "Commons").symlink_to(out / "installed-commons")
    (out / "Commons").symlink_to(worker / "Commons")
    runtime.mkdir(mode=0o700)
    stubs.mkdir()
    config = home / ".config/wheely"
    config.mkdir(parents=True)
    (config / "lock-design").write_text("mycelium\n")
    for name in ["omarchy-hyprland-session-locked", "fprintd-list", "omarchy-system-wake",
                 "omarchy-brightness-display", "omarchy-brightness-keyboard"]:
        # A wake leaves its file until it finishes, so one killed with its worker stays behind.
        command = 'touch "$HOME/wake.$$"; sleep 2; rm "$HOME/wake.$$"' if name == "omarchy-system-wake" else 'exit 1'
        if name == "omarchy-hyprland-session-locked":
            command = "exit 2" # The compositor cannot report its lock state during startup.
        path = stubs / name
        path.write_text("#!/bin/sh\n" + command + "\n")
        path.chmod(0o755)
    source = (lock / "Service.qml").read_text()
    source = source.replace("import QtQuick\n", "import QtQuick\nimport QtQuick.Window as QW\n")
    source = re.sub(r"  function realScreenCount\(\) \{.*?\n  }", "  function realScreenCount() { return 1 }", source, flags=re.S)
    source = source.replace("WlSessionLock {", "TestSessionLock {")
    source = source.replace("WlSessionLockSurface {", "Loader { active: sessionLock.locked; sourceComponent: QW.Window {\ntransientParent: null\nwidth: 1920; height: 1080; visible: true\nproperty bool firstFrame: true\nonFrameSwapped: if (firstFrame) { firstFrame = false; console.log('LOCK_FRAME', Date.now()) }")
    source = source.replace("  PanelWindow {", "  }\n  PanelWindow {")
    source = source.replace("PanelWindow {", "QW.Window {\ntransientParent: null\nwidth: 1920; height: 1080\nproperty int frames: 0\nonFrameSwapped: if (++frames === 30) console.log(\"RENDERED\")")
    source = re.sub(r"^    (anchors \{ top:.*|WlrLayershell\..*|exclusionMode:.*)\n", "", source, flags=re.M)
    # Only the offscreen test contains this synthetic authentication entry point.
    source = source.replace('target: "lock"', 'target: "lock"\nfunction authenticated(): string { root.driveOffThenUnlock(); return "ok" }')
    # The unlock names the delay it waited, which the design sets.
    source = qslog.patch(source, "    onTriggered: root.finishUnlock()",
                         '    onTriggered: { console.log("RELEASE_DELAY", interval); root.finishUnlock() }', exactly=True)
    (lock / "Service.qml").write_text(source)
    (lock / "TestSessionLock.qml").write_text('''import QtQuick
Item {
 property bool locked: false
 property bool secure: locked
 signal lockStateChanged()
 signal secureStateChanged()
 onLockedChanged: lockStateChanged()
 onSecureChanged: secureStateChanged()
}''')
    (out / "shell.qml").write_text('''import QtQuick
import Quickshell
import "Lock" as Lock
ShellRoot { Lock.Service {} }
''')
    env = dict(os.environ, HOME=str(home), PATH=str(stubs) + ":/usr/bin",
               QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic", QT_QUICK_BACKEND="rhi",
               QSG_RHI_BACKEND="opengl", QSG_RENDER_LOOP="threaded", XDG_RUNTIME_DIR=str(runtime),
               XDG_CACHE_HOME=str(out / "cache"), QS_DISABLE_FILE_WATCHER="1")
    env.pop("OMARCHY_LOCK_SESSION", None)

    def ipc(action, child=False):
        result = subprocess.run(["quickshell", "ipc", "-p", str(worker if child else out),
                                 "call", "lock", action], env=env, capture_output=True, text=True, timeout=3)
        return result.stdout.strip() if result.returncode == 0 else ""

    def status():
        return json.loads(ipc("status") or "{}")

    def logs():
        return "\n".join(p.read_text() for p in runtime.glob("quickshell/by-id/*/log.log"))

    def until(check, message, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = check()
            if value:
                return value
            time.sleep(0.05)
        raise AssertionError(message + "\n" + logs())

    def child_pid():
        result = subprocess.run(["quickshell", "list", "-p", str(worker), "-j"],
                                env=env, capture_output=True, text=True, timeout=3)
        instances = json.loads(result.stdout) if result.stdout.lstrip().startswith("[") else []
        return instances[0]["pid"] if instances else None

    def rss(pid):
        return int(re.search(r"VmRSS:\s+(\d+)", Path(f"/proc/{pid}/status").read_text())[1]) / 1024

    def start():
        return subprocess.Popen(["quickshell", "--no-color", "-p", str(out)], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    parent = None
    try:
        parent = start()
        until(lambda: status().get("passwordPam"), "bridge did not start")
        time.sleep(1)
        until(lambda: not child_pid(), "undetermined recovery retained its worker after the retry budget", timeout=12)
        (stubs / "omarchy-hyprland-session-locked").write_text("#!/bin/sh\nexit 1\n")
        baseline = rss(parent.pid)
        for cycle, design in enumerate(["mycelium", "rally", "mycelium"]):
            (config / "lock-design").write_text(design + "\n")
            assert ipc("preview") == "ok"
            pid = until(child_pid, "preview worker did not start")
            until(lambda: logs().count("RENDERED") > cycle, f"{design} never rendered")
            print(f"loaded {design}: worker RSS {rss(pid):.1f} MiB", flush=True)
            assert ipc("hidePreview") == "ok"
            until(lambda: not child_pid(), "closed preview retained its worker")
            retained = rss(parent.pid) - baseline
            assert retained < 12, f"parent retained {retained:.1f} MiB after {design}"
            print(f"ok: {design} worker {pid} exits; parent RSS change {retained:.1f} MiB", flush=True)

        # Every worker so far retired cleanly, which logs nothing.
        qslog.check(logs())

        # Each lock reads the background in a fresh worker. Its URL must change once, to the
        # versioned file: an unversioned URL on the way costs a second decode before the wallpaper shows.
        state = home / ".local/state/omarchy/current"
        state.mkdir(parents=True)
        (state / "background").symlink_to(repo / "themes/wheelie/backgrounds/02-night-track.jpg")
        (config / "lock-design").write_text("wallpaper\n")
        assert ipc("preview") == "ok"
        until(lambda: "WALLPAPER_READY" in logs(), "wallpaper design never drew its wallpaper")
        assert ipc("hidePreview") == "ok"
        until(lambda: not child_pid(), "closed preview retained its worker")
        requests = re.findall(r"WALLPAPER_REQUEST (\S+)", logs())
        assert len(requests) == 1 and requests[0].endswith("?v=1"), requests
        (state / "background").unlink()
        (config / "lock-design").write_text("mycelium\n")
        print("ok: a fresh worker requests its wallpaper once", flush=True)

        requested_at = time.time() * 1000
        assert ipc("lock") == "ok"
        until(lambda: status().get("sessionLocked"), "lock never took hold")
        frame = until(lambda: re.search(r"LOCK_FRAME (\d+)", logs()), "lock surface never rendered")
        print(f"lock request to first frame: {int(frame[1]) - requested_at:.0f} ms", flush=True)
        pid = child_pid()
        # A suspend waits on secure, which the lock withholds until it has blanked: the design's
        # five seconds are seen before the machine sleeps, and the first key after wakes a blank.
        assert not status().get("secure"), "a suspend would cut the design's entrance short"
        until(lambda: status().get("secure"), "a blanked lock still held a suspend back")
        assert status()["lastEvent"] == "display: blank" and time.time() * 1000 - requested_at > 4500
        # Stopped past the watch's tick, the worker sees the wall clock jump as a suspend does it.
        # It lights the display and leaves the design hidden for the first input.
        os.kill(pid, signal.SIGSTOP)
        time.sleep(4)
        os.kill(pid, signal.SIGCONT)
        until(lambda: status()["lastEvent"] == "display: lit by resume", "a resume left a blanked lock dark")
        until(lambda: list(home.glob("wake.*")), "a resume ran no wake command", timeout=3)
        print("ok: a suspend waits for the lock's blank, and a resume lights it without playing the design", flush=True)
        parent.terminate()
        parent.wait(timeout=3)
        time.sleep(1)
        assert Path(f"/proc/{pid}").exists(), "shell exit killed the active lock"
        parent = start()
        until(lambda: status().get("sessionLocked"), "shell restart did not reconnect")
        assert child_pid() == pid, "shell restart replaced the active lock"
        parent.kill()
        parent.wait(timeout=3)
        time.sleep(1)
        parent = start()
        until(lambda: status().get("sessionLocked"), "shell crash did not reconnect")
        assert child_pid() == pid, "shell crash replaced the active lock"
        os.kill(pid, signal.SIGKILL)
        until(lambda: child_pid() and child_pid() != pid and status().get("sessionLocked"), "crashed lock did not recover")
        # A suspend asks for the lock before it sleeps. Landing in the design's exit, that request
        # keeps the lock: taken as already done, the machine would wake unlocked.
        assert ipc("authenticated", child=True) == "ok" and ipc("lock") == "ok"
        time.sleep(1.5)
        assert status().get("locked") and status()["lastEvent"] == "unlock: cancelled", status()
        assert ipc("authenticated", child=True) == "ok"
        until(lambda: not status().get("locked"), "authenticated unlock did not release")
        assert "RELEASE_DELAY 550" in logs(), "mycelium's unlock did not wait its own releaseDelay"
        until(lambda: not child_pid(), "unlock retained its worker")
        until(lambda: not list(home.glob("wake.*")), "worker exited before its wake command finished", timeout=3)
        print("ok: shell restart/crash reconnects, worker crash recovers, unlock/wake retires", flush=True)

        # A worker that cannot start, then a missing bridge: the shell locks in-process instead.
        entry = worker / "shell.qml"
        entry.write_text("invalid qml\n")
        assert ipc("lock") == "ok"
        until(lambda: status().get("sessionLocked"), "failed worker did not fall back to an in-process lock")
        assert not child_pid(), "fallback lock started a worker"
        parent.terminate()
        parent.wait(timeout=3)
        (worker / "Bridge.qml").unlink()
        parent = start()
        until(lambda: status().get("passwordPam"), "missing bridge left no lock service")
        assert ipc("lock") == "ok"
        until(lambda: status().get("sessionLocked"), "missing bridge did not lock in-process")
        assert not child_pid(), "missing bridge started a worker"
        print("ok: a failed worker or missing bridge locks in-process", flush=True)
    finally:
        # Stop the bridge first so killing an active test worker cannot respawn it.
        if parent is not None:
            parent.terminate()
            try:
                parent.wait(timeout=3)
            except subprocess.TimeoutExpired:
                parent.kill()
                parent.wait(timeout=3)
        subprocess.run(["quickshell", "kill", "-p", str(worker)], env=env,
                       capture_output=True, timeout=3)
        until(lambda: not child_pid(), "cleanup retained its worker")
