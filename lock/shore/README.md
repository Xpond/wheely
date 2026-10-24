# Shore

Part of the lock screen; see [`docs/lockscreen.md`](../../docs/lockscreen.md) for the host, installation and wake handling.


Where the wash meets the sand, seen close from high above: shallow water fills the top of the
screen, damp sand the bottom, and the water's edge moves across the middle. Every six seconds or
so a foaming bore comes down through the water, runs up the sand under a rope of foam and slides
back. Unlocking brings the tide in as the beach fades.

`shore.frag` draws everything in one full-screen pass from the time alone; `Scene.qml` only runs
the clock. Surges differ in strength, rhythm and angle, and in how uneven their fronts are. Each
reaches each stretch of shore at its own time, a second or two apart, and runs its own distance, so
its edge keeps changing shape: stretches race ahead, lag, or drain back while others still advance.
Running up, its lip frays into small tongues that form and fade; draining back, the thinning film
tears into patches. Its reach is a parabola in time, warped so the backwash takes longer than the
run up, and the next surge catches the backwash near the centre, so the edge stays about the
middle.

Each surge arrives as a foaming bore that thins to a rope of foam along its edge, with lace
drifting in patches on the water behind. Foam, ripples and the light they focus ride on the
topmost water, stretching as it spreads and sliding back with the backwash; a new surge's water
runs over the old under its foam. The ripples bend the sand seen through the water, their light
draws a moving web on it, the surface mirrors the sky and glints, and the shallows turn green,
then turquoise, as reds are absorbed. The foam casts a soft shadow up the beach. Where the
backwash draws back, the sand shines with the sky in draining patches and dries within 16 seconds,
and a thin line of bubbles is stranded where each surge stopped. The dry sand is pale and warm,
golden brown where wet, with fine grains, some dark and some catching the sun, patches of wind
ripples and small bumps lit from up the beach, and faint lines of grit where earlier surges
stopped.

600 surges make an hour, then the surf repeats. The ripples and the light drift a whole number of
their repeats in that hour, so the scene wraps its clock to the hour seamlessly and the shader's
floats stay precise. Each lock opens at a random point in the hour, and the clock pauses while the
display is blank. `play()` fades the beach in over 1.2s; `leave()`
raises the tide 1.2 screen heights and fades it out within the 1.1s before the lock releases. A
surge whose water can't reach a point, however far its lip frays, skips its water there. At 1080p a
frame takes 1.3ms of GPU time on a GTX 1080 Ti at full clocks, the most of any design.

After GLSL changes, rebuild the shader:

```bash
scripts/build-shaders.sh lock/shore/shore.frag
```

## Files

| File | Responsibility |
|---|---|
| `lock/shore/Scene.qml` | Runs the surf's clock, fades the beach in and brings the tide in on unlock |
| `lock/shore/shore.frag` / `.qsb` | The wash: its edge, water, foam and light, and the sand it wets, source and compiled |
