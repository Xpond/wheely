# Performance

Latest: [ambient dust renderer measurements](PERFORMANCE-DUST.md).

## 2026-10-20 follow-up: share decoded images

Before the dust renderer change linked above, ambient dust dominated active CPU
cost. Removing it in an isolated diagnostic reduced CPU from 39.4–39.8% at about
169 fps to 7.7% at 179 fps: approximately 2.35 versus 0.43 CPU milliseconds per
frame. The image-sharing changes measured below preserved particle density.

Four `cache: false` overrides prevented the cutout, wheel, shadow and storm images
from sharing decoded data between windows. Removing them uses Qt's normal image
cache, as the base and wheel covers already do. Identical image URLs and decode
sizes can share their decoded data. See [Qt's Image documentation](https://doc.qt.io/qt-6/qml-qtquick-image.html#performance).

First comparison, using one or two 1920×1080 offscreen windows in one process:

| Scene | Before RSS | After RSS | Before fps | After fps |
|---|---:|---:|---:|---:|
| One window | 335.5 MiB | 335.9 MiB | 168.8 | 169.0 |
| Two windows | 461.8 MiB | 411.3 MiB | 168.0 | 168.0 |

The two-window saving was 50.5 MiB, about 11%; peak RSS fell from 514.0 to
460.2 MiB. This is a memory improvement for matching displays, not an active CPU
or GPU-memory improvement. Different decode sizes still need separate images.
CPU for the two-window comparison was 111.4% before and 110.0% after, within
run-to-run variation. FPS is per window, not the sum of both windows.

Measurements used the same GTX 1080 Ti, Quickshell 0.3.2, Qt 6.12.0 and OpenGL
as the earlier review, with five seconds of warm-up and twelve seconds of sampling.
CPU percentages use one core. CPU time and RSS came from `/proc`, and frame counts
from `frameSwapped`.
The installed wallpaper and other desktop applications remained running.
The offscreen loop is uncapped; these are not native Wayland presentation rates.
Today's absolute CPU readings should not be treated as a regression against
earlier sessions: the before and after comparisons here used the same environment.

Pausing produced zero frames and no CPU ticks during each five-second sample.
The real controller still polls monitor state once per second. Unloading scenes
also stopped rendering. Qt's default unused decoded-image cache limit is 2 MiB; it
evicts excess data on release; OS/driver allocation retention can keep process
RSS or VRAM above their initial values. See the [Qt cache implementation](https://raw.githubusercontent.com/qt/qtdeclarative/6.12/src/quick/util/qquickpixmapcache.cpp).

Deterministic before/after renders were pixel-identical at 1920×1080, 1080×1920
and 3840×2160, at wheel angle 83°, storm phase 1.7, and storm approach 0 and 1.
Random particles were disabled; this comparison preceded the dust renderer change.
The initial 30-cycle scene reload experiment settled around 366–370 MiB after
warm-up, rather than growing with every reload.

Both versions passed 30 full controller unload/reload cycles, including lifecycle
assertions; after-change RSS stayed around 360–367 MiB. A second two-window run,
in reverse order, saved 47.5 MiB. Destroying both windows removed the process from
NVIDIA's graphics-process list and left RSS at 238.5 versus 243.8 MiB before.
Validation also passed `node tests/check.js`, shell syntax and `git diff --check`;
QML lint retained the same 49 warnings and zero errors.

This review preserves 2× decoding, particle density, animation timing and all
baked assets. The installed wallpaper was unchanged during this comparison.
Physical multiple displays, lock/unlock, DPMS cycling and suspend/resume remain
untested. The 4K checks cover still-image fidelity, not animation performance.

## 2026-10-20: images at screen size

Same machine, measured offscreen at 1920×1080 like the component experiments below
(uncapped, about 166 fps), two 16-second runs each:

| Scene process | RSS | VRAM | CPU, one core |
|---|---:|---:|---:|
| Before | 418–424 MiB | 273 MiB | 26.4–28.0% |
| After | 333–334 MiB | 191 MiB | 26.1–26.2% |

- Images decode at twice the pixels they cover on screen, never above native size.
  Before, 5504-pixel textures were sampled about 2.9 times minified without mipmaps.
  From 16:9 screens 1536 pixels tall upward, the decode is native and saves nothing.
- The scene is built once the screen's size and the layout are known, so each image
  decodes once. Starting it peaks at 445 instead of 624 MiB, but takes 1.5 instead of
  1.2 CPU seconds, for Qt's downscaling.
- Lighting is applied to a screen-sized layer, pixel for pixel. Before, the layer kept
  the scene's proportions and was stretched to the screen's: 0.8% at 16:9, 3.2 times on
  a portrait screen.
- Below the horizon the base takes the cutout's colors where the cutout is opaque.
  Decoded smaller, the stale sand hidden there showed as a light line at the cutout's edge.
- The idle controller held 167–171 MiB with a static background selected. It now exits
  when another theme is set. On a static Wheelie background it stays, because Omarchy
  has no background-change hook to start it again.
- Forest trail and hard enduro are quality-100 JPEG without chroma subsampling instead
  of PNG: 64.4 MB became 45.0 MB. No pixel moves more than 4 of 255 levels, natively or
  as the shell samples them at 1080p.

Fidelity was measured on deterministic 1080p stills (no particles; wheel angle 83°; storm
approach 0 and 1) against an exact box-filtered downsample of the native render, the
most detail a 1080p screen can show:

| Still | PSNR | SSIM, luma | Local error, 99th percentile | Gradient energy vs. ideal |
|---|---:|---:|---:|---:|
| Before | 40.0 dB | 0.991 | 4.9 | 1.32 |
| After | 45.3 dB | 0.997 | 2.6 | 1.11 |

The rider and bike rose from 39.5 to 43.0 dB, the wheels from 37.7 to 42.1 dB. No
neighborhood is worse by more than one level. Decoding at one times the screen size
blurred the bike (gradient energy 0.83), mipmaps were blurrier still, and three times
equals native at 1080p. Before, the extra gradient energy was aliasing on spokes, chain,
sand, and sky. Qt's image scaler truncates, so decoded images average 0.47 of 255 levels
darker than an exact mean, half the smallest 8-bit step. The native still is bit-identical.

## 2026-10-19 review

Wheelie sustains this machine's 144 Hz display, but is not fully optimized for
active rendering. Ambient dust dominates CPU cost. The changes in this review
remove unnecessary work while hidden and precompute static storm transparency;
they preserve particle density, native assets, and display-rate motion.

Measured on a GTX 1080 Ti, one 1920×1080 display at 143.981 Hz and scale 1,
Hyprland 0.56.2, Quickshell 0.3.2, Qt 6.12.0, OpenGL. Baseline source commit:
`24eb10b`. CPU percentages below are percentages of **one core**.

| Installed wallpaper, 15-second samples | CPU | Whole-GPU busy | Whole-GPU power |
|---|---:|---:|---:|
| Before, animating | 31.05% | 17.0% | 70.19 W |
| After, animating | 30.27% | 17.0% | 70.29 W |
| After, manually paused | 0.46% | 1.07% | 64.40 W |

These readings do **not** demonstrate a significant reduction in active cost.
GPU counters include the compositor and other applications, and power is total
board power, not wallpaper power. The pause sample retains monitor-state polling;
the regression test separately confirms that the scene stops submitting frames.

A native Wayland background-layer comparison, with the installed animation paused,
measured 143.88 fps before and 143.98 fps after. Both had 7 ms median and 95th-percentile
frame intervals. These are presentation intervals measured with `frameSwapped` and
millisecond timestamps, not GPU execution times. Vulkan also sustained 144 fps but
did not provide a useful CPU or power improvement, so the backend remains unchanged.

Component isolation used the same 1920×1080 scene offscreen. This render loop was
uncapped and ran at 171–182 fps, so compare the variants rather than treating these
numbers as desktop frame rates. Each run warmed for three seconds, sampled CPU/GPU
for eight seconds, and collected frame intervals for approximately ten seconds.

| Baseline component experiment | CPU | Observed fps | CPU ms per frame, approximate |
|---|---:|---:|---:|
| Whole scene | 29.30% | 171.07 | 1.71 |
| Without ambient dust | 4.31% | 182.24 | 0.24 |
| Without storm | 29.29% | 171.53 | 1.71 |
| Without final lighting layer | 27.86% | 171.87 | 1.62 |

The ambient emitters maintain roughly 13,000 live particles before accounting for
variation and particles outside the viewport. Qt 6.12's `QQuickImageParticle`
marks active geometry dirty on every frame, causing the renderer to upload it again.
This is a likely contributor to the measured dust cost despite GPU-evaluated motion.
See the [Qt implementation](https://code.qt.io/cgit/qt/qtdeclarative.git/tree/src/particles/qquickimageparticle.cpp?h=6.12)
and [particle performance guide](https://doc.qt.io/qt-6/qtquick-particles-performance.html).

The next candidate to profile is a particle renderer that retains its geometry on
the GPU. Its benefit needs measurement and visual/lifecycle validation. A frame-rate limit or reduced dust
density would also reduce work, but this review preserves the requested 144 Hz motion
and existing appearance.

Changes applied:

- Monitor state is refreshed once a second through Quickshell's native Hyprland IPC,
  only while the animated background is selected. Each display pauses for DPMS-off,
  session lock, or a compositor-reported solitary client. Hyprland draws only that
  client in this state; transparent/fullscreen windows are not guessed from geometry.
  See [Hyprland's rendering path](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/render/Renderer.cpp).
- Pausing retains the wheel angle instead of restarting its animation. Manual pause
  remains in force when a display wakes. Selecting a static background or another
  theme still unloads the scene.
- `sky.py` bakes a native 6336×2688 RGBA storm. The live shader uses one texture sample
  after distortion instead of sampling two images and solving coverage every frame.

Validation passed: fresh asset/shader build, Python compilation, `node tests/check.js`,
and QML lint (the same warning counts/categories as baseline). The new integration
test exercises actual scene/controller QML offscreen with simulated monitor snapshots:

```sh
python3 themes/wheelie/bake.py
python3 tests/wheelie-lifecycle.py
```

It checks frozen frames, wheel-phase continuity, lock/DPMS/fullscreen pausing,
manual-pause persistence, and repeated animated/static/theme transitions. The native
controller was also verified to receive live monitor snapshots without QML or shader
errors. Its log contains a Qt desktop-portal app-ID registration warning.

Before/after stills at 5504×3072, wheel angle 83°, storm phase 1.7 and approach 0/1
were compared with random particles disabled. Average RGB difference was 0.0196 and
0.0267 on a 0–255 scale; the 99th percentile was 1 in both cases. At most 17 pixels
in either 16.9-million-pixel frame differed by more than 3 in any channel. Visual
inspection found no visible change.

Limits: real lock/unlock, physical DPMS cycling, suspend/resume and multiple monitors
were not exercised. Ordinary window coverage is not inferred; animation remains active
where Hyprland does not confirm a solitary client. Native-size stills were checked,
but 4K animation and other GPUs were not benchmarked. This is not a long-duration
memory/leak soak test; native test-process RSS was approximately 465–530 MiB.

Temporary benchmark scene copies were removed after the review.
The installed animation was updated and left running. No source images were generated.
