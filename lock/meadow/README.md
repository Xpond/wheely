# Meadow

Part of the lock screen; see [`docs/lockscreen.md`](../../docs/lockscreen.md) for the host, installation and wake handling.

Multicolored wildflowers grow into lowercase “omarchy” above a flat meadow occupying the
bottom 20% of the screen, with a soft, irregular grassy edge. Behind it, a night sky deepens
overhead above a sunset glow that meets the meadow's horizon, warmest on the right. Twinkling
stars thin out towards the glow. Banks of cloud, their undersides lit by the sunset, drift
right with the breeze across the upper sky, with clear sky between them. A dim crescent moon
hangs top right behind a thin, drifting haze that shows only in its light, and passing clouds
veil it further. Fireflies, each a hot core in a warm glow, drift and pulse over the meadow.
Larger flowers, overlapping ground cover and low, rounded mossy stones frame a shallow clearing
around the password field. The closest corners soften out of focus to give the garden depth.
The exposed ground has patchy moss, soil grain, tiny pebbles and fallen stems, with finer
detail towards the far edge. Near-ground texture is painted once beneath the foliage.
Grass blades rise and bend over first. Shoots then climb out of the meadow, a green bud
nodding at each tip as it circles and leans; leaves unfold from beside the stem once the tip
has passed, and tendrils coil tighter as they lengthen. Each tip's small searching bend settles
as it climbs, independently of flowering. Buds begin opening during the climb at varied rates,
and gradually lift to face the viewer: sepals fold back and the
petals, each a blade tilted in 3D, spread from a cup to nearly flat, while lavender florets
open from the bottom of the spike. Individual petals loosen at slightly different rates;
the word emerges from the moving buds and finishes within four seconds after
preparation, before the normal five-second idle blank.

`garden.js` packs blossoms tightly along rounded, evenly spaced letter strokes, each on a
warm, lit, nearly upright stem that wavers slightly. Pointed leaves and curling tendrils
gather below the lettering, leaving the letters' insides open; flower heads are drawn after
all foliage, so no leaf hides part of a letter. Smaller flowers and grass clumps are scattered
near the ground. Daisies, cosmos, poppies, blue flowers and lavender spikes vary in petal
shape, size, tilt and foliage. Their layout uses a 900-unit-high frame, the word centred in it.
Plants grow as live geometry. A small canvas holds a table of every plant, one 24-bit
fixed-point field per texel, which `plants.vert` reads to shape each part of each plant at the
current moment: three grid meshes draw grass, then stems, leaves and tendrils, then flower
heads, each part a ribbon of quads whose end rows collapse so parts never join. `plants.frag`
antialiases ribbons and leaves across their width and ray-casts each flower head's sepals,
petals and centre as tilted blades and a disc, keeping the two nearest surfaces per pixel.
The meshes render the lettering and grass into a layer while growth runs; once it finishes
the layer stays still, and `meadow.frag` bends it with a quicker sway, traveling gusts and a
smaller rustle, continuing through the end of growth. Bending grows quadratically above the
meadow, keeping the roots still; explicit horizontal interpolation prevents pixel-sized jumps
in the texture. The lower flowers, the meadow's and the near bank's larger ones, sway from
their own roots in the same breeze, a few degrees at most: `plants.vert` bends their stems and
carries leaves and heads along, redrawing them every frame into two layers covering the
bottom 30%. A second canvas paints the near bank's ground, grass and stones once, back to
front so each stone hides what grows behind it, and returns its flowers for the plant shaders.
Below that, it holds each stone's outline and front edge, so `plants.frag` hides the flowers
rooted behind it. `meadow.frag` draws the sky and ground, the meadow's flowers behind the near
bank and its own in front, and softly reveals the bank and blurs its closest corners.
Blanking stops the clock; waking regrows the garden. Unlocking
fades it within the host's 1.1-second release delay. At 1080p `meadow.frag` takes about 0.28ms
on a GTX 1080 Ti at full clocks, skipping stars, ground noise, cloud rims and fireflies wherever
they cannot show; the swaying lower flowers add about 0.12ms a frame, and the plant layer about
0.2ms while it grows.

## Files

| File | Responsibility |
|---|---|
| `lock/meadow/Scene.qml` | Prepares the plant tables and near bank, and runs growth, wind and the unlock fade |
| `lock/meadow/garden.js` | Flower lettering and meadow flowers, and their plant table |
| `lock/meadow/foreground.js` | Near ground cover, grass and mossy stones, the stones' outlines, and the larger flowers framing the clearing |
| `lock/meadow/plants.vert` / `.frag` / `.qsb` | Grass, stems, leaves, tendrils and flowers as they grow, and the lower flowers' sway, source and compiled |
| `lock/meadow/meadow.frag` / `.qsb` | Night sky, moon, clouds, fireflies, ground and the swaying garden, source and compiled |
| `tests/meadow-render.py` | Wind keeps roots fixed, bends stems coherently and moves them smoothly, in the lettering and on the near bank, at 1080p and 4K |

Rebuild the shaders after GLSL changes:

```bash
scripts/build-shaders.sh lock/meadow/*.{frag,vert}
```
