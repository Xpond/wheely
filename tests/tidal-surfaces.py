#!/usr/bin/env python3
"""Check native wallpaper pieces, fractional-scale fallback, frames, and output recreation."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import qslog

repo = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tidal-surfaces").resolve()
config = output / "controller"
shutil.copytree(repo / "themes/tidal/animated", config, dirs_exist_ok=True)
state = output / "state"
state.mkdir(exist_ok=True)
(state / "theme.name").write_text("tidal\n")
(state / "00-living-coast-animated.png").touch()
(state / "background").unlink(missing_ok=True)
(state / "background").symlink_to(state / "00-living-coast-animated.png")
source = (config / "shell.qml").read_text()
source = qslog.patch(source, 'Quickshell.env("HOME") + "/.local/state/omarchy/current"', json.dumps(str(state)))
source = qslog.patch(source, "property bool paused: false", "property bool paused: true")
source = qslog.patch(source, "root.animated ? Quickshell.screens : []", "root.animated && root.outputs ? Quickshell.screens.slice(0, 1) : []")
source = qslog.patch(source, "id: root", "id: root\n  property var panels: []\n  property bool outputs: true\n  property bool saved: false", 1)
source = qslog.patch(source, 'WlrLayershell.namespace: "tidal-wallpaper"', 'WlrLayershell.namespace: "tidal-surfaces-test"')
source = qslog.patch(source, "PanelWindow {\n          required", "PanelWindow {\n          id: sandWindow\n          required", 1)
for window in ["wallpaper", "sandWindow"]:
    source = qslog.patch(source, "id: " + window, "id: " + window + f'''
      property int frames: 0
      Connections {{ target: {window}.contentItem.Window.window
        function onFrameSwapped() {{ {window}.frames++ }} }}''', 1)

# Capturable QML items around the real window contents preserve the actual clipped viewport.
for role, window, indent in [("moving", "wallpaper", "      "), ("sand", "sandWindow", "          ")]:
    start = source.index(indent + "Surface {")
    end = source.index("\n" + indent + "}", start) + len(indent) + 2
    block = source[start:end]
    block = block.replace("Surface {", f'''Surface {{
          id: {role}Scene
          Component.onCompleted: root.panels.push({{role: "{role}", window: {window}, view: {role}View, scene: {role}Scene}})''', 1)
    source = source[:start] + indent + f"Item {{ id: {role}View; anchors.fill: parent; clip: true\n" + block + "\n" + indent + "}" + source[end:]

source = qslog.patch(source, 'target: "tidal"', '''target: "tidal"
    function status(): string {
      return JSON.stringify({saved: root.saved, panels: root.panels.map(p => ({role: p.role,
        dpr: p.view.Screen.devicePixelRatio, frames: p.window.frames}))})
    }
    function sample(t: real, muted: bool): void {
      root.paused = true
      root.panels.find(p => p.role === "moving").scene.seconds = t
      root.background = root.stateDir + (muted ? "/00-muted-coast-animated.png" : "/00-living-coast-animated.png")
    }
    function outputs(enabled: bool): void { root.panels = []; root.outputs = enabled }
    function capture(dir: string): void {
      root.saved = false
      const pieces = root.panels, moving = pieces.find(p => p.role === "moving")
      function piece(i) {
        if (i === pieces.length) { root.saved = true; return }
        pieces[i].view.grabToImage(r => {
          if (!r.saveToFile(dir + "/" + pieces[i].role + ".png")) { Qt.exit(1); return }
          piece(i + 1)
        })
      }
      moving.scene.grabToImage(r => {
        if (!r.saveToFile(dir + "/reference.png")) { Qt.exit(1); return }
        piece(0)
      })
    }''')
shell = config / "shell.qml"
shell.write_text(source)

def layers():
    monitors = json.loads(subprocess.check_output(["hyprctl", "layers", "-j"], text=True))
    return [layer for monitor in monitors.values() for group in monitor["levels"].values()
            for layer in group if layer.get("namespace") == "tidal-surfaces-test"]

for scale in ["1", "1.5", "2"]:
    captures = output / scale
    captures.mkdir(exist_ok=True)
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QT_SCALE_FACTOR=scale)
    log_path = captures / "run.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(["quickshell", "--no-color", "-p", str(config)], env=env, stdout=log, stderr=log)
        try:
            instance = qslog.Instance(process, config, "tidal", env, log_path)
            ipc, wait = instance.ipc, instance.wait_for
            wait(lambda s: bool(s["panels"]))
            dpr = ipc("status")["panels"][0]["dpr"]
            split = dpr == round(dpr)
            count = 2 if split else 1
            wait(lambda s: len(s["panels"]) == count and len(layers()) == count)
            for t, muted in [(148, False), (152, True), (3599.999, False)]:
                folder = captures / str(t)
                folder.mkdir(exist_ok=True)
                ipc("sample", t, str(muted).lower())
                time.sleep(0.3)
                ipc("capture", folder)
                wait(lambda s: s["saved"])
                names = ["moving", "sand"] if split else ["moving"]
                paths = [folder / f"{name}.png" for name in ["reference", *names]]
                sizes = [struct.unpack(">II", path.read_bytes()[16:24]) for path in paths]
                assert all(size[0] == sizes[0][0] for size in sizes) and sum(s[1] for s in sizes[1:]) == sizes[0][1], sizes
                pixels = [subprocess.check_output(["magick", str(path), "-depth", "8", "RGBA:-"]) for path in paths]
                original, joined = pixels[0], b"".join(pixels[1:])
                differences = [abs(a - b) for a, b in zip(original, joined) if a != b]
                maximum = max(differences, default=0)
                # Viewport interpolation can move isolated grain samples across a cell boundary.
                large = sum(delta > 3 for delta in differences)
                print(f"{scale}x t={t}: max={maximum}/255, changed={len(differences)} channels, >3={large}", flush=True)
                assert maximum <= 32 and large <= 30 and len(differences) / len(original) < 0.001, (scale, t, maximum, len(differences), large)
                if split:
                    assert pixels[-1] == original[-len(pixels[-1]):], "stationary sand changed"
                    boxes = sorted(layers(), key=lambda layer: layer["y"])
                    assert (boxes[0]["x"], boxes[0]["w"]) == (boxes[1]["x"], boxes[1]["w"]), boxes
                    assert boxes[0]["y"] + boxes[0]["h"] == boxes[1]["y"], boxes
                else:
                    assert original == joined, "fractional-scale fallback changed pixels"
            time.sleep(0.3)
            before = {p["role"]: p["frames"] for p in ipc("status")["panels"]}
            ipc("resume")
            time.sleep(1.1)
            after = {p["role"]: p["frames"] for p in ipc("status")["panels"]}
            assert 25 <= after["moving"] - before["moving"] <= 40, (before, after)
            if split:
                assert after["sand"] == before["sand"], "stationary surface keeps presenting"
            ipc("pause")
            time.sleep(0.3)
            before = [p["frames"] for p in ipc("status")["panels"]]
            time.sleep(0.3)
            assert before == [p["frames"] for p in ipc("status")["panels"]], "paused scene presents"
            ipc("outputs", "false")
            wait(lambda s: not s["panels"] and not layers())
            ipc("outputs", "true")
            wait(lambda s: len(s["panels"]) == count and len(layers()) == count)
            qslog.check(log_path.read_text())
        finally:
            process.terminate()
            process.wait(timeout=5)
    print(f"ok: {scale}x surfaces align, meet image tolerances, pause, resume, and recreate; sand stays still", flush=True)
