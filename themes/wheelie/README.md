# Wheelie

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

The installer prepares the complete theme before stopping the running one, so a failed
copy leaves it untouched; the scene stops only for the directory swap. Rerun the
installer if a later step fails. The baked scene in `scene/` goes in `animated/`.
A native still, `00-wheelie-animated.png`, is the theme's first background; four static
scenes follow it. Theme-change and post-boot hooks start the wallpaper controller,
`scene/wallpaper.qml`. While that still is selected, the controller runs
the live scene on every display. The scene is cropped to fill each screen and sits above
the shell's static background and below windows. It takes no input or focus. Choosing
another background unloads it; choosing another theme also ends the controller, until
the theme-set hook starts it again. Re-applying Wheelie moves Omarchy on to the next
background, as for any theme; select the poster again to resume the scene.
Display-off, session-lock, and compositor-confirmed fullscreen coverage pause that
display's scene within one second. Waking it preserves the wheel angle and any manual
pause. The controller checks monitor state in-process only while animation is selected.

```sh
~/.config/omarchy/themes/wheelie/wheelie pause
~/.config/omarchy/themes/wheelie/wheelie resume
~/.config/omarchy/themes/wheelie/wheelie toggle
```

Wheely binds Ctrl+Space to `toggle` while Wheelie is installed. For an app that
needs Ctrl+Space, change the key with Wheely's Wallpaper pause setting
(`wheely settings`). It is separate from Omarchy's Super+Ctrl+Space background
switcher.

## Static backgrounds

The static scenes include forest riding, hard enduro, and two night settings.
Forest trail and hard enduro have a baked black bottom vignette for the bar.
The smooth fade runs from 72% to 98% of the image height, starting up to 6% earlier
at the corners. Both are 5456×3072 quality-100 JPEGs.

| Background | Scene |
|---|---|
| [Forest trail](backgrounds/01-forest-trail.jpg) | A rider on a mossy forest singletrack |
| [Night track](backgrounds/02-night-track.jpg) | A rider airborne over a floodlit motocross jump |
| [Hard enduro](backgrounds/03-hard-enduro.jpg) | A rider climbing an exposed rocky mountain slope |
| [Desert camp](backgrounds/04-desert-camp.jpg) | The bike parked by a campfire under the Milky Way |

## Bike

Separate front and rear wheels turn over the plate under stationary covers. Their
lighting stays fixed to the upper-left light source while the tires turn. An animated
drive chain, timed to the rear wheel, runs behind the boot and swingarm, and a
stationary contact shadow sits beneath the rear tire.

## Sky prints

Three sky photos, deep blue, rose-magenta,
and amber from top to bottom, replace the scene's sky as equal full-width strips,
bordered in white above and below like prints laid edge to edge, running off the
sides. Together they fill the sky down to the `horizon` row; the amber print's lower
edge lies behind the dunes. The strips are baked into `base.png`. The storm draws
over the prints, and `scene/Surface.qml` redraws the borders over the storm from the
`prints` rows and `printBorder` width in `layout.json`, so thin dust never ghosts a
border through it. The rider, bike, and dunes stay in front of everything.

## Ambient dust

Fine airborne sand, softer nearby flecks, and faint low wisps fill the scene.
Nearby sand moves faster than distant grains, with varied sizes, lifetimes, and
wind speeds. Rear-tire grains and puffs lift beside the wheel's trail.

`scene/AmbientDust.qml` sets each layer's emission rate, tint, sizes, lifetimes, and
velocities. `ambient-dust.vert` moves fixed meshes on the GPU, so thousands of particles
need no geometry uploads each frame; `ambient-dust.frag` samples the grain and wisp SVG
textures. Slots stagger new randomized lives at each layer's emission rate, and the air
starts populated.

The clock wraps every 2376 seconds, a common multiple of the particle-slot periods;
the generation counter continues the random sequence across that boundary.
Pausing holds the clock and every particle in place.

Untinted glints ride with the distant and near grains at half their rates, sharing
their area and motion.

## Horizon sandstorm

A dense, textured sand bank grows behind the distant dunes over four
minutes, then continues billowing there. Its ten-minute texture-flow loop is seamless;
the approach does not reset or jump back. It pauses with the scene's particles.

`scene/HorizonStorm.qml` controls the timing; `scene/storm-wall.frag` scales and
gently distorts the baked `storm.png`, keeping the plate's original aspect ratio.
The 6336-pixel-wide plate covers the native scene throughout the approach without
enlargement. Its own sky is baked out, so `storm.png` holds only the dust.

The storm replaces only the sky. `cutout.png` holds everything else, with
anti-aliased edges, and is drawn over the storm, which ends just inside the redrawn
dunes at the `horizon` row in `layout.json`. The wheel layers draw above the storm.

## Storm shade

The dunes lie in the storm's shade, regraded to its dust hue, a little lighter and
duller, with no lit crest. The far foreground takes on some of the shade and cools
toward the viewer. This shade is baked. `scene/scene-light.frag`
darkens the foreground toward the bottom edge and its corners, in linear light; the
sand ripples and the wheel trail stay.
A vignette deepens the bottom edge behind the bar, keeping 25% of its light there,
less in the corners.

## Editing

The scene's images and `layout.json` in `scene/` are baked outside this repository.
After editing a shader in `scene/`, recompile it:

```sh
for f in themes/wheelie/scene/*.{frag,vert}; do /usr/lib/qt6/bin/qsb --qt6 -o "$f.qsb" "$f"; done
```

## Asset provenance

- Scene, storm plate, and the night track and desert camp backgrounds:
  `google/gemini-3-pro-image` via `rb imagen`, 4K.
- Sky prints: `google/gemini-3.1-flash-image` via `rb imagen`, 4K.
- Wheel sprites, rim finish, and chain material: the built-in imagegen tool.
- `backgrounds/01-forest-trail.jpg` and `03-hard-enduro.jpg`: 5456×3072 outputs
  from `black-forest-labs/flux-3-image` via `rb imagen`, 4K, 16:9, with the bottom
  vignette added.

Contact shadows and lighting are code-defined.
