# Ambient dust performance — 2026-10-20

The ambient dust now uses fixed meshes with shader-evaluated motion. In two
comparisons on this desktop, the full scene used about **72% less CPU** while
maintaining **144 Hz**. Particle rates, size ranges, lifetimes, wind, tints, textures
and white glints retain their original settings. Rear-tire dust is unchanged.

## Native Wayland measurements

GTX 1080 Ti, one 1920×1080 display at 143.981 Hz, Quickshell 0.3.2, Qt 6.12.0,
OpenGL. Each temporary background-layer scene warmed for four seconds, then ran
twelve one-second samples. Order: old, new, new, old. CPU is a percentage of
**one core**, measured from `/proc`; frame intervals come from `frameSwapped`
with millisecond timestamps.

| Full scene | CPU | Presentation rate | Median / p95 interval |
|---|---:|---:|---:|
| Original particles, first run | 47.43% | ~144 fps | 7 / 7 ms |
| Fixed meshes, first run | 13.21% | ~144 fps | 7 / 7 ms |
| Fixed meshes, repeat | 13.44% | ~144 fps | 7 / 7 ms |
| Original particles, repeat | 47.85% | ~144 fps | 7 / 7 ms |

The installed wallpaper, compositor and other applications remained running.
These are matched scene-process measurements, not total desktop CPU usage.
Pausing each scene produced no frames and no CPU ticks in four-second samples.
The production controller's separate once-per-second monitor polling is unchanged.

Whole-GPU busy fell from about 30% to 21–23%, including all other applications.
Board power varied from 69–73 W, so these short runs establish no reliable energy
saving. RSS was 427–429 MiB before, 457 MiB on the first new-shader run and 394 MiB
on the repeat. That variation does not establish a guaranteed memory saving.

An uncapped 1080p offscreen check also reduced CPU from 37.6–39.0% at about
170 fps to 7.3–7.8% at about 179 fps. Offscreen rates are not desktop presentation
rates, and absolute CPU readings from different review sessions are not comparable.

## Implementation

Qt's existing particle renderer already calculates movement in its vertex shader,
but marks active particle geometry dirty every frame. The replacement keeps
geometry fixed and updates time uniforms. The original implementation is documented
in [Qt's particle renderer](https://raw.githubusercontent.com/qt/qtdeclarative/v6.12.0/src/particles/qquickimageparticle.cpp)
and [vertex shader](https://raw.githubusercontent.com/qt/qtdeclarative/v6.12.0/src/particles/shaders_ng/imageparticle.vert).

Five `ShaderEffect` layers cover distant grains, nearby flecks, low wisps and the
two glint populations. A regular `GridMesh` supplies quads; collapsed connecting
rows prevent triangles between particles. Slots cover each layer's maximum
lifetime, with births staggered at its original rate. Expected live population
remains about 12,970 particles before viewport clipping.

The shader preserves Qt's fade curve, quadratic size interpolation, minimum size,
premultiplied tint and random parameter ranges. Positions use a new random sequence,
so stochastic frames are not pixel-identical to the old renderer. The clock wraps
every 2376 seconds with a continuing generation offset, preserving floating-point
precision during long sessions. Pausing freezes that clock.

The bake compiles both shader stages with `qsb --qt6` and includes source hashes
in their URLs so live reload cannot reuse stale shaders. The random generator uses
float arithmetic compatible with Qt's desktop GLSL 120 path; no native plugin or
new runtime dependency is needed. See [Qt's ShaderEffect documentation](https://doc.qt.io/qt-6/qml-qtquick-shadereffect.html).

## Validation and limits

Passed:

- Fresh asset/shader bake and native-resolution poster render.
- Dust rendering, identical paused pixels, resume movement, clock rollover and
  different later generations on OpenGL and Vulkan.
- Controller lifecycle regression tests, including simulated lock, DPMS,
  fullscreen and static/theme transitions. Dust and lifecycle checks also pass
  on a copy containing only the installer's runtime files.
- `node tests/check.js`, Python syntax, `git diff --check`, and QML lint:
  47 warnings, zero errors; the dust component itself has no warnings.
- All eight runtime PNG assets match the installed copies pixel for pixel.
  Rebuilding changes PNG metadata, so compressed-file hashes differ.

Commands after baking:

```sh
python3 tests/wheelie-dust.py
QSG_RHI_BACKEND=vulkan python3 tests/wheelie-dust.py
python3 tests/wheelie-lifecycle.py
```

OpenGL uses an offscreen window. Vulkan uses a temporary, non-interactive Wayland
background window: Qt's offscreen platform cannot create a Vulkan instance.
An initial offscreen Vulkan attempt crashed during graphics initialization;
the corrected native test passed.

Full-scene stills were visually inspected. Across eight isolated dust snapshots
per version, bright-pixel coverage differed by about 2%; overall brightness and
coverage differed by 6–7%. Sparse large wisps vary substantially between snapshots;
this sample does not prove perceptual equivalence. Settings were preserved instead
of adjusting density to fit a small sample.

At 1080p, the two representations of the clock-wrap boundary differed by at most
3 of 255 channel levels, averaging 0.00114. These checks simulate large elapsed
times; they are not a long-duration runtime or leak test.

Performance results cover this GPU and 1080p display. Vulkan was checked for
correctness, not benchmarked here. Other GPUs, 4K animation, physical multiple
monitors, lock/DPMS cycling and suspend/resume remain untested.

The installed wallpaper was left running unchanged during validation.
