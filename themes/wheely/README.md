# Wheely desert scene — work in progress

Native **5504×3072** wallpaper scene checkpoint, 2026-10-17.
This is a preview and rebuildable scene, not an installable Omarchy theme yet.

![Current scene](preview.jpg)

## Next session: ambient dust

Add ambient airborne dust particles across the scene. The existing grains and
puffs are localized behind the rear tire; the wider scene still looks too clean.
This is the next task. Ambient dust has not been implemented in this checkpoint.
There is more scene refinement to do before theme packaging and installation.

## Current checkpoint

- Separate front/rear wheels with concentric hubs and rims, matte rim finishes,
  and even tire shading to avoid rotating white patches that look like wobble.
- Animated drive chain, with links timed to the rear wheel and masked behind
  the boot and swingarm. The user marked this done.
- A stronger stationary contact shadow beneath the rear tire, accepted for now.
- Pronounced warm sunset lighting across the scene, with cooler foreground sand.
  Wheel lighting stays fixed to the upper-left light source while the tires turn.
- Existing rear-wheel sand grains and puffs remain a starting point for dust work.

Keep the native resolution. Use one ordinary preview window. **Never resize,
move, float, or rearrange it.** The scene letterboxes in the preview window.

## Build and preview

From the repository root:

```sh
python themes/wheely/bake.py
qmllint themes/wheely/build/Surface.qml themes/wheely/build/Render.qml themes/wheely/build/shell.qml
quickshell -n -p themes/wheely/build
```

Dependencies: Python, NumPy, ImageMagick, Quickshell, and Qt's shader baker at
`/usr/lib/qt6/bin/qsb`. Tested with Quickshell 0.3.1 and Qt 6.11.2.
Edit `scene/`, then rebuild; `build/` is generated and Git-ignored.

For a matching native still (optional final argument is wheel angle in degrees):

```sh
python themes/wheely/render.py themes/wheely/build themes/wheely/wallpaper-4k.png
```

The renderer uses the same QML and shaders offscreen with OpenGL. It needs access
to the graphics session but opens no desktop window. The still is Git-ignored.
`preview.jpg` is a small documentation image; it is not used by the scene.

## Files and checks

`scene/` owns the QML, lighting shaders, dust texture, and contact shadow.
`sources/` contains every rebuild input; no scratch-directory inputs are required.
`bake.py` builds wheel layers, stationary covers, the chain atlas, and compiled shaders.
`wheels.py` aligns sprites and evens tire illumination; `chain.py` places the links.
`render.py` captures the assembled scene without duplicating its lighting code.

The cleanup was checked by rebuilding from these inputs, comparing the decoded
runtime assets with the accepted prototype, linting QML, compiling Python and
shaders, and rendering the native still. The live preview was verified earlier
with unchanged window geometry and consistent lighting at multiple wheel angles.

The old experiments and detailed review captures remain local under
`misc/bike/archive/v3-2026-10-17/`. The already-open legacy preview still reads
`misc/bike/v3/out`; leave it in place until that window is closed. Start subsequent
previews from `themes/wheely/build`. The old scratch path is not a source directory.

## Asset provenance

- `sources/scene.jpg`: original 5504×3072 output from
  `google/gemini-3-pro-image` via `rb imagen`, 4K, 16:9. Its decoded pixels exactly
  match the PNG used during development. Prompt: [scene](prompts/scene.txt).
- `sources/base.png` and `sources/layout.json`: preserved compositing plate and
  original wheel geometry derived from that scene. Required by the mask rebuild.
- `sources/wheels.png`: separate front/rear wheel sprites generated using the
  built-in imagegen tool. Prompt: [wheels](prompts/wheels.txt).
- `sources/matte-rims.png`: imagegen edit; only the rim finish is used by the bake.
  Prompt: [matte rims](prompts/matte-rims.txt).
- `sources/chain.png`: imagegen chain material. The bake extracts a single link
  and constructs the measured route. Prompt: [chain](prompts/chain.txt).

Contact shadows and lighting are code-defined. Generated source assets are kept
unaltered; new bakes reproduce the compositing and motion layers from them.
