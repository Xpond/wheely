Performance review — 2026-10-19

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

Raw samples, logs and visual comparisons are retained locally under
`/tmp/wheelie-perf/`; installed-file backups are in its `installed-backup/` directory.
Temporary benchmark scene copies were removed after the review.
The installed animation was updated and left running. No source images were generated.
