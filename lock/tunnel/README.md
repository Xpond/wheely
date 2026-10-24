# Tunnel

Part of the lock screen; see [`docs/lockscreen.md`](../../docs/lockscreen.md) for the host, installation and wake handling.

Forty copies of the wheel's mark, stacked in perspective, form a corridor flown through
first person. The mark is the centrelines of Omarchy's icon on its 30-unit grid: drawn 0.1
wide they cover every stroke pixel of the wheel's `mark.png`; the tunnel draws them 0.07
wide. Marks stand every 4 units, each 0.7–1.3× in size and turned at random; the
choice is fixed by its place along the corridor, so a mark keeps it as it nears, and one flown
past returns to the far end as another. It fades in there, and fades out from 3 units ahead to
1.5, where even the smallest is already past the edges of a 16:9 screen.
The corridor's centreline wanders on a few sine waves; the camera looks down its tangent, so
the far end swings, and it banks into the turns. The view is 90° high: a mark 14 units
ahead fills the screen's height.

Each mark is a `ShaderEffect`: `mark.vert` places it from the distance flown, and `mark.frag`
draws the maze's 17 stretches and a comet through them as the wheel's runs: out from where the
bottom bar meets the inner square, splitting at every junction. Each stretch carries its ends'
distances along the maze, which match `mark.png`'s at every junction. A mark's place picks its
hue, from cyan to magenta, and its comet's start, pace (0.3–0.8 laps a second at cruise), tail
(12–35% of the run) and way round: three in ten run back in from the ends. The comets keep time
with the flight, so they race on unlock. Behind the marks, `space.frag` lights the far end,
where the tunnel's tangent meets the screen, and dust drifts past as small dots, each its own
size. Before evaluating a dust mote's heading and coverage, the shader rejects pixels farther
from its radial distance than the largest mote can reach. This leaves identical pixels while
roughly halving the dust pass's GPU cost.

QML works out each mark's depth every frame, and the random picks for its place only when it
comes round again; its position, size, turn, fade and comet head come from the vertex shader, so
a frame moves 40 marks without moving 40 items. A mark faded below a thousandth isn't drawn, and
`mark.frag` returns early for points farther than any glow from the grid lines every stretch
lies on. At 1080p on a GTX 1080 Ti the tunnel holds 144fps using about a tenth of a CPU core and
0.76ms of GPU time a frame at full clocks.

`play()` fades the tunnel in over 1.2s while it accelerates to 8 units a second.
`leave()` accelerates tenfold and fades out within the 1.1s before the lock releases.
The flight pauses while the display is blank. After GLSL changes, rebuild the shaders:

```bash
scripts/build-shaders.sh lock/tunnel/*.{frag,vert}
```

## Files

| File | Responsibility |
|---|---|
| `lock/tunnel/Scene.qml` | The wheel's mark stacked into a corridor, flown through |
| `lock/tunnel/mark.vert` / `.qsb` | Places and fades one mark as the flight goes on, source and compiled |
| `lock/tunnel/mark.frag` / `.qsb` | One mark: its maze and a comet running through it, source and compiled |
| `lock/tunnel/space.frag` / `.qsb` | The glow at the tunnel's far end and the dust, source and compiled |
