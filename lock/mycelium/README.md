# Mycelium

Part of the lock screen; see [`docs/lockscreen.md`](../../docs/lockscreen.md) for the host, installation and wake handling.

Fine hyphae grow from the centre, with white tips cooling through cyan to teal. They light a
mottled ground, with a softer colony beneath them for depth. The camera drifts and the strands
sway slowly. Unlocking draws the colony back into the centre while it fades.

`grow.js` builds a new colony each lock in a coordinate space 1080 units high. Twelve strands
step outward, wander, branch into open space and fuse when they meet another strand. Each tapers
according to the length it feeds, including its branches. The result contains paths grouped by
width, segments grouped by arrival step, and a coarse map of density and average arrival time.
The scene calls `begin()` and resumes its builder with a 3ms budget on each timer tick, so colony
creation leaves time for input and the first frame. It pauses while blanked and releases the
builder when complete.

`Scene.qml` draws four canvases once, each on the canvas thread rather than holding up the lock:
the arrival map takes a quarter of a second. Growth starts once all four have drawn.

- `web`: antialiased surface lines.
- `times`: arrival steps packed into red and green, drawn without antialiasing. Wider strokes
  cover the line edges; earlier steps win at intersections.
- `shine`: the coarse light map.
- `deeper`: the colony at half resolution, with arrival time in its colour.

`ground.frag` draws the background once. `mycelium.frag` combines it with the canvases in one
full-screen pass. Cubic B-spline sampling smooths the surface lines during camera motion and
magnifies the light and deep layers. This removes the triangular edges left by bilinear line
sampling. The arrival map is sampled linearly and decoded without rounding its channels,
dividing out alpha at its edges; interpolation also works across the packed 255-to-256 boundary.

Growth advances at 45 steps a second on the frame clock, starting once the colony is drawn.
Both growth and camera motion pause when the display is blank. `hide()` resets growth and
freezes the ground while blanked; `play()` resumes both automatically after wake. `leave()`
keeps the camera moving while it retracts and fades over the host's 550ms unlock delay; then the
clock stops.

After GLSL changes, rebuild the shaders:

```bash
scripts/build-shaders.sh lock/mycelium/*.frag
```

## Files

| File | Responsibility |
|---|---|
| `lock/mycelium/Scene.qml` | Grows and draws back the colony, drifts the camera, and draws the canvases its shader reads |
| `lock/mycelium/grow.js` | Grows a colony: its lines, the step that reaches each, and the light it casts |
| `lock/mycelium/mycelium.frag` / `.qsb` | The colony as grown so far on the ground it lights, and its deep hyphae, source and compiled |
| `lock/mycelium/ground.frag` / `.qsb` | The ground's clouds and grain, drawn once, source and compiled |
| `tests/mycelium.js` | Colony coverage, arrival steps and light distribution |
| `tests/mycelium-render.py` | Strand smoothness at 1080p and 4K, and growth across the packed step boundary |

## Verification

`tests/mycelium.js` grows colonies from fixed seeds at four
screen shapes: each must cross over 95% of the screen's 60-unit squares, every line drawn must have
its step, and its light must cover the screen, reaching the corners after the centre.

`tests/mycelium-render.py` renders three isolated, shallow-angle strands through the scene and
shader at 1080p and 4K. It checks brightness variation along their edges and growth across the
packed step's 255-to-256 boundary. Captures go to `/tmp/mycelium-render/` or the directory supplied
as its argument.
