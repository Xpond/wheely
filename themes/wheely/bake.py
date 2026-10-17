"""Build the native scene from source assets: python bake.py [output directory]."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

from wheels import load, prepare, save
from chain import build_chain
from sky import cutout, storm_sky

root = Path(__file__).resolve().parent
out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "build"
out.mkdir(parents=True, exist_ok=True)
sources = root / "sources"
scene = load(sources / "scene.jpg")
base = load(sources / "base.png")
sheet = load(sources / "wheels.png")
matte_sheet = load(sources / "matte-rims.png")
layout = json.loads((sources / "layout.json").read_text())

for name, center, radius in (("front", (3146.5, 1763.5), 322), ("rear", (4338, 2314), 296)):
    size = prepare(sheet, matte_sheet, name, radius, out / f"{name}.png")
    cx, cy = center
    half = radius + 18
    left, top = int(cx) - half, int(cy) - half
    region = (slice(top, top + half * 2), slice(left, left + half * 2))
    patch = scene[region].copy()
    y, x = np.mgrid[region].astype(np.float32) + 0.5
    dx, dy = x - cx, y - cy
    old = layout["wheels"][name]
    old_dist = np.hypot(x - old["center"][0], y - old["center"][1])
    old_radius = old["size"] / 2 / 1.02
    rgb = patch[..., :3]
    spill = np.minimum(rgb[..., 0], rgb[..., 2]) - rgb[..., 1]
    key_alpha = np.clip(1 - np.maximum(spill, 0) / 0.94, 0, 1)
    # Only the connected fork/swingarm belongs in front of the rotating wheel.
    if name == "front":
        arm = (dx > -45) & (np.abs(dy + 0.88 * dx - 12) < 54)
        outside = np.clip((0.85 - rgb.mean(-1)) / 0.08, 0, 1)
    else:
        arm = (dx < 42) & (np.abs(dy - 0.68 * dx + 5) < 57)
        outside = np.clip((0.77 - rgb.mean(-1)) / 0.10, 0, 1)
    inside = old_dist < old_radius - 5
    alpha = np.where(inside | (spill > 0.08), key_alpha, outside) * arm
    # Remove magenta from partially covered edge pixels, preserving their soft alpha.
    unkeyed = (rgb - (1 - key_alpha[..., None]) * np.array([1, 0, 1])) / np.maximum(key_alpha[..., None], 0.01)
    unkeyed[..., 1] = np.minimum(unkeyed[..., 1], unkeyed[..., [0, 2]].mean(-1) + 0.025)
    patch[..., :3] = np.where(((spill > 0.025) & arm)[..., None], np.clip(unkeyed, 0, 1), rgb)
    patch[..., 3] = alpha
    if name == "front":
        # The old row interpolation sampled the fork, leaving a grey stripe in the sky.
        # Use nearby clean sky texture above the dune, feathering into the existing plate.
        plate = base[region].copy()
        sky = scene[top:top + 2 * half, left - 650:left + 2 * half - 650]
        mix = np.clip((1880 - y) / 24, 0, 1) * np.clip((old_radius - old_dist - 6) / 16, 0, 1)
        plate[..., :3] = plate[..., :3] * (1 - mix[..., None]) + sky[..., :3] * mix[..., None]
        base[region] = plate
    else:
        # Restore sand texture through the lower spokes from clean ground at the same height.
        plate = base[region].copy()
        clean = scene[top:top + 2 * half, left - 650:left + 2 * half - 650]
        mix = (np.clip((y - 2370) / 32, 0, 1)
               * np.clip((old_radius - old_dist - 10) / 18, 0, 1))
        plate[..., :3] = plate[..., :3] * (1 - mix[..., None]) + clean[..., :3] * mix[..., None]
        base[region] = plate
        # The ground stays stationary while tread passes behind the contact patch.
        ground_y = 2588 + 0.014 * (x - cx) + 1.5 * np.sin((x - cx) / 13)
        ground = np.clip((y - ground_y) / 3, 0, 1)
        sand = scene[region].copy()
        keyed = spill > 0.025
        sand[..., :3] = np.where(keyed[..., None], clean[..., :3], sand[..., :3])
        patch[..., :3] = np.where((ground > 0)[..., None], sand[..., :3], patch[..., :3])
        patch[..., 3] = np.maximum(patch[..., 3], ground)
    save(out / f"{name}-cover.png", patch)
    layout["wheels"][name] = {"center": list(center), "size": size, "radius": radius,
                             "box": [left, top, half * 2]}
    if name == "rear":
        layout["wheels"][name]["contactY"] = 2588

save(out / "base.png", base)

# The storm replaces only the sky; everything else is redrawn over it.
rgba, layout["cutout"], layout["horizon"] = cutout(root / "scene", base, layout)
save(out / "cutout.png", rgba)
layout["chain"] = build_chain(root, out, scene)
(out / "layout.json").write_text(json.dumps(layout, indent=1) + "\n")
shutil.copy2(sources / "storm-wall-sky-4k.jpg", out / "storm-wall-sky-4k.jpg")
save(out / "storm-sky.png", storm_sky(load(sources / "storm-wall-sky-4k.jpg")))
for name in ("dust.svg", "sand-grain.svg", "contact-shadow.svg",
             "storm-wall.frag", "wheel-light.frag", "scene-light.frag"):
    shutil.copy2(root / "scene" / name, out / name)
for name in ("wheel-light", "scene-light", "storm-wall"):
    shader = out / f"{name}.frag"
    filename = f"{name}.frag.qsb"
    if name == "storm-wall":
        # Qt retains shaders by URL across reloads; changed code needs a fresh URL.
        digest = hashlib.sha256(shader.read_bytes()).hexdigest()[:12]
        filename = storm_shader = f"{name}-{digest}.frag.qsb"
    subprocess.run(["/usr/lib/qt6/bin/qsb", "--qt6", "-o", str(out / filename),
                    str(shader)], check=True)
# An open preview reloads whenever its QML changes, even mid-bake. Write the QML last,
# complete, and remove superseded storm shaders, so a reload never runs stale code.
for name in ("Surface.qml", "AmbientDust.qml", "HorizonStorm.qml", "shell.qml", "Render.qml"):
    qml = (root / "scene" / name).read_text()
    (out / name).write_text(qml.replace("storm-wall.frag.qsb", storm_shader))
for old in out.glob("storm-wall*.frag.qsb"):
    if old.name != storm_shader:
        old.unlink()
