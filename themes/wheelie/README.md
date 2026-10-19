# Wheelie — work in progress

A light Omarchy theme built around a live desert scene. A rider holds a wheelie
while a sandstorm builds behind three framed sky prints. Native **5504×3072**.

![Current scene](preview.jpg)

## Theme

The palette in `colors.toml` comes from the scene. The base is `#FEE5D4`, the orange
at the center left of the amber print lifted to a light peach. Text is `#1C222B`, the
foreground sand's blue-grey darkened, at 13:1. The accent is the sand's own `#404651`.
The terminal colors take their hues from the sky prints and dunes, deepened to 6:1;
the bright ones read at 4.6:1. Omarchy generates the app configurations from
`colors.toml`; icons use Yaru's orange set.

```sh
./themes/wheelie/wheelie install
omarchy theme set wheelie
```

The installer rebakes the scene and copies the theme to `~/.config/omarchy/themes/wheelie`.
The baked scene goes in `animated/`. A native still, `00-wheelie-animated.png`, is
the theme's only background. Theme-change and post-boot hooks start the wallpaper
controller, `scene/wallpaper.qml`. While that still is selected, the controller runs
the live scene on every display. The scene is cropped to fill each screen and sits above
the shell's static background and below windows. It takes no input or focus. Choosing
another background or theme unloads it.

```sh
~/.config/omarchy/themes/wheelie/wheelie pause
~/.config/omarchy/themes/wheelie/wheelie resume
```

## Sky prints

The user approved the sky on 2026-10-18. Three sky photos, deep blue, rose-magenta,
and amber from top to bottom, replace the scene's sky as equal full-width strips,
bordered in white above and below like prints laid edge to edge, running off the
sides. Together they fill the sky down to the `horizon` row; the amber print's lower
edge lies behind the dunes. `sky.py`
cuts each strip from the middle of its photo, scaled to the scene width, and the
bake writes them into `base.png`. The storm draws over the prints, and
`scene/Surface.qml` redraws the borders over the storm from the `prints` rows and
`printBorder` width in `layout.json`, so thin dust never ghosts a border through it.
The rider, bike, and dunes stay in front of everything. The border width is set in
`bake.py`. The photos are native 8:1 and 4:1 panoramas, so every strip is
downscaled to the scene width rather than cut from a soft 21:9 frame.

An open preview reloads only when its QML changes, so restart it after a bake
that changes only the sky.

## Ambient dust

The first ambient pass adds fine airborne sand, softer nearby flecks, and faint
low wisps across the scene. Nearby sand moves faster than distant grains, with
varied sizes, lifetimes, and wind speeds. Emitters pre-roll so the air is already
populated when the preview opens. The existing rear-tire grains and puffs remain.

Tune density, tint, size, and motion in `scene/AmbientDust.qml`; all measurements
use the native scene coordinates and share its sunset lighting. This pass is
ready for visual review.
Verified with a native still, QML lint, and frame comparisons: dust moves while
running, holds identical frames while paused, and moves again after resuming.

Emitting, pre-roll included, waits for the window's first three drawn frames. Qt's
`ImageParticle` gives a particle its tint, rotation, and stretch only once its painter
has drawn, so a hot reload's pre-roll otherwise showed as bright white puffs for ~15 s.
Checked on hot reload, fresh launch, and offscreen stills.

The user liked how those white grains sparkled and approved untinted glints on
2026-10-18: they ride with the distant and near grains at half their rates, mirroring
their area and motion. The glint painter needs a rotation; without one Qt draws point
sprites, which ignore the scene's downscale and show as large soft blobs.

## Horizon sandstorm

The user judged the storm good on 2026-10-18. A blue-keyed plate always showed
its cut crest, so the storm plate is generated over a dusk sky like the scene's;
its crest fades into sky the way real dust does, and the shader removes that sky so
the sky prints show through. Keep the native 6336×2688 source and scene resolution.

A dense, textured sand bank grows behind the distant dunes over four
minutes, then continues billowing there. Its ten-minute texture-flow loop is seamless;
the approach does not reset or jump back. It pauses with the scene's particles.

`scene/HorizonStorm.qml` controls the timing; `scene/storm-wall.frag` scales and
gently distorts `sources/storm-wall-sky-4k.jpg`, keeping its original aspect ratio.
The 6336-pixel-wide source covers the native scene throughout the approach without
enlargement. The bake fits a smooth model of the plate's own sky (`storm-sky.png`);
the shader solves each pixel's dust coverage against it, using the dust hue measured
from the plate, and draws only the dust.

The storm replaces only the sky. `scene/rider-trace.svg` and `scene/dunes.svg` are
rough hand traces; near them `sky.py` separates the plate's sky from the rider,
bike, and dunes, and writes everything else to `cutout.png`, drawn over the storm
with decontaminated anti-aliased edges. The storm ends just inside the redrawn
dunes, at the `horizon` row in `layout.json`. The sky enclosed between the forearms is
seeded explicitly. The front wheel's plate holds borrowed sky, so the dunes'
skyline continues straight behind it. The wheel layers draw above the storm.
The bake gives changed storm shaders a new filename so Qt reloads their code
in the existing preview window. It writes the QML last and deletes superseded storm
shaders, so a reload during the bake cannot run stale shader code.

## Storm shade

The user approved the shade on 2026-10-19. `dunes.py` regrades the dunes in the bake to
the storm's dust hue, a little lighter and duller, with no lit crest. Near the rider,
color tells sand from the bike; along an edge, a pixel takes its share of the change to
the sand beside it, so no pale line remains. The far foreground takes on some of the
shade and cools toward the viewer over about 220 px, and the edge between them blends
over 7 rows. The photo's darker crest lip there is scaled by its own color, so it never
turns black. The shade is static. `scene/scene-light.frag`
darkens the foreground toward the bottom edge and its corners, in linear light; the
sand ripples and the wheel trail stay.
A vignette deepens the bottom edge behind the bar, keeping 25% of its light there,
less in the corners.

## Current checkpoint

- Separate front/rear wheels with concentric hubs, round traced rim edges, matte rim
  finishes, and shading evened from the rim's inner edge outward, so no rotating
  white patch looks like wobble.
- The front fork and brake cable are freed of the photo's sky where the larger tire
  passes behind them, so they show no white outline over it, and the fork's lower side
  is whole. The fork tube's underside darkens toward its edge; its warm reflection is the
  dust's own color, so against the storm the tube seemed to fade out.
- Animated drive chain, with links timed to the rear wheel and masked behind
  the boot and swingarm. The user marked this done.
- A stronger stationary contact shadow beneath the rear tire, accepted for now.
- Pronounced warm sunset lighting across the scene, with cooler foreground sand.
  Wheel lighting stays fixed to the upper-left light source while the tires turn.
- Dunes in the storm's shade, and a foreground that darkens into a vignette at the bottom.
- Existing rear-wheel sand grains and puffs remain a starting point for dust work.
- Ambient airborne sand, sparkling glints, and low drifting wisps fill the wider scene.
- A distant sandstorm slowly approaches, with moving billows behind the rider.
- Three white-framed sky prints, blue, magenta, and amber, replace the original sky.

Keep the native resolution. Use one ordinary preview window. **Never resize,
move, float, or rearrange it.** The scene letterboxes in the preview window.

## Build and preview

From the repository root:

```sh
python themes/wheelie/bake.py
/usr/lib/qt6/bin/qmllint themes/wheelie/build/*.qml
quickshell -n -p themes/wheelie/build
```

Dependencies: Python, NumPy, ImageMagick, Quickshell, and Qt's shader baker at
`/usr/lib/qt6/bin/qsb`. Tested with Quickshell 0.3.1 and Qt 6.11.2.
Edit `scene/`, then rebuild; `build/` is generated and Git-ignored.

For a matching native still (optional final argument is wheel angle in degrees):

```sh
python themes/wheelie/render.py themes/wheelie/build themes/wheelie/wallpaper-4k.png
```

The renderer uses the same QML and shaders offscreen with OpenGL. It needs access
to the graphics session but opens no desktop window. The still is Git-ignored.
Particles run during capture while the wheels hold the requested angle, so dust
positions vary between stills.
`preview.jpg` is a small documentation image and the theme picker's preview; the
scene does not use it.

## Files and checks

`scene/` owns the QML, lighting and storm shaders, dust textures, traces, and contact shadow.
`sources/` contains every rebuild input; no scratch-directory inputs are required.
`bake.py` builds wheel layers, stationary covers, the chain atlas, and compiled shaders.
`wheels.py` aligns and rounds sprites and evens their shading; `chain.py` places the links;
`sky.py` builds the sky-free cutout, the storm plate's sky model, and the sky prints;
`dunes.py` puts the dunes in the storm's shade.
`render.py` captures the assembled scene without duplicating its lighting code.

The sky prints checkpoint was checked by rebuilding from these inputs, confirming the
decoded bake outputs were identical before and after cleanup, linting QML, compiling
Python and shaders, rendering native stills at the start and end of the storm's
approach, and restarting the live preview. The live preview was verified earlier
with unchanged window geometry and consistent lighting at multiple wheel angles.

The old experiments and detailed review captures remain local under
`misc/bike/archive/v3-2026-10-17/`. Start previews from `themes/wheelie/build`;
the old scratch path, `misc/bike/v3/out`, is not a source directory.

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
- `sources/storm-wall-sky-4k.jpg`: original 6336×2688 dust-bank plate over a
  dusk sky from `google/gemini-3-pro-image` via `rb imagen`, 4K, 21:9, preserved
  unaltered. The shader removes its sky. Prompt: [sandstorm](prompts/storm-wall-sky-4k.txt).
- `sources/sky-blue.png`, `sources/sky-magenta.png`, `sources/sky-amber.png`:
  original sky panoramas from `google/gemini-3.1-flash-image` via `rb imagen`, 4K,
  preserved unaltered: blue at 8:1 (11712×1408), magenta and amber at 4:1
  (8256×2048). Prompts: [blue](prompts/sky-blue.txt), [magenta](prompts/sky-magenta.txt),
  [amber](prompts/sky-amber.txt).

Contact shadows and lighting are code-defined. Generated source assets are kept
unaltered; new bakes reproduce the compositing and motion layers from them.
