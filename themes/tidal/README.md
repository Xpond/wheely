# Tidal

A light Omarchy theme: chalk, sea glass, warm sand, and marine ink.
One animated coast and three original static wallpapers. Independent of Wheely.

![Tidal's animated coast and three static wallpapers](preview.png)

## Preview

From the Wheely checkout:

```bash
./themes/tidal/tidal preview
```

The gallery shows the living coast, the palette, and the three static images.
Space pauses the tide; Escape closes the gallery. Previewing changes no desktop settings.

## Install

```bash
./themes/tidal/tidal install
omarchy theme set tidal
```

The installer copies this directory into `~/.config/omarchy/themes/tidal`.
It also installs Omarchy theme-change and post-boot hooks for background selection.
Omarchy generates matching app configurations from `colors.toml`; `shell.toml`
supplies the ivory surfaces and sea-glass selections.
Wheely's installer does not install or select Tidal.

## The living coast

Open Omarchy's **Background** picker, including through Wheely, and choose the
first thumbnail: **Living Coast — Animated** (`00-living-coast-animated.png`).
Choose any static image to switch back. You can also select the animation with:

```bash
~/.config/omarchy/themes/tidal/tidal animate
```

The camera stays still while irregular surges roll along a horizontal shoreline.
Caustics drift through shallow turquoise water, foam thins along the edge, and wet
sand dries behind the backwash. Adapted from Wheely's original Shore shader, with
a lighter palette and a tide running at 30% of Shore's speed.

Quickshell renders one input-transparent surface per display, above the shell's
static background and below application windows. It takes no keyboard focus or
screen space. A 32 ms timer targets about 30 animation updates per second.
The detailed foam, caustics, and ripples render directly at the display's resolution,
including 4K, with no low-resolution texture cap or upscaling. No video player
is needed.

```bash
~/.config/omarchy/themes/tidal/tidal pause
~/.config/omarchy/themes/tidal/tidal resume
~/.config/omarchy/themes/tidal/tidal stop
```

Selecting a static wallpaper or changing theme unloads the animated surfaces.
The small controller stays idle, watching Omarchy's selection, so choosing Living
Coast starts it again. The hooks restore this behavior after login and theme changes.
The `stop` command selects the last static wallpaper; pause freezes the animation.

## Static collection

| Wallpaper | Composition |
|---|---|
| [Shoreline](backgrounds/01-shoreline.jpg) | A sweeping boundary between turquoise water and ivory sand |
| [Shallows](backgrounds/02-shallows.jpg) | Sunlit caustics over a quiet central sand bank |
| [Ebb](backgrounds/03-ebb.jpg) | Sculpted sand flats and branching tidal channels |

The JPEGs are unmodified `rb imagen` outputs: 5504 × 3072 pixels, generated at
Google Gemini 3 Pro Image's native 4K tier. The living coast renders at screen
resolution; its picker thumbnail is a lossless 3840 × 2160 shader capture.
Prompts, model, and generation provenance are in [PROMPTS.md](PROMPTS.md).
Code and assets are distributed under the repository's [MIT license](../../LICENSE).

## Development

Rebuild the shader after editing `animated/tidal.frag`:

```bash
/usr/lib/qt6/bin/qsb --glsl '100 es,120,150' --hlsl 50 --msl 12 \
  -o themes/tidal/animated/tidal.frag.qsb themes/tidal/animated/tidal.frag
python3 tests/tidal.py
```

The check validates text contrast, the three wallpapers, Omarchy's generated app
configs, GPU captures of motion, pause, horizontal surf, native 4K rendering,
continuous wave edges and the hourly clock wrap, and repeated animated/static
wallpaper selections and theme changes using the same controller.
Tested on Omarchy 4.0.4 and Quickshell 0.3.1.
