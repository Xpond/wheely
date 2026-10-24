# Rally

Part of the lock screen; see [`docs/lockscreen.md`](../../docs/lockscreen.md) for the host, installation and wake handling.

A fixed front-left view of a Sport quattro S1 E2 assembles as blue comets trace its outlines.
The wireframe builds over 2940ms, followed by a 600ms paint sweep from nose to tail.
Successful authentication starts the car, spins the wheels and launches it left;
the session unlocks after the 1.1-second drive-off.

The scene uses a painted neon-city plate behind the live car, a contact shadow,
and a subdued wet-floor reflection. The grille
and wheel wells have solid dark backing so the bright pavement cannot show through.
The accepted artwork is **1672×941**, generated with the built-in imagegen tool.

The car is framed at 89% scale about screen centre, then lowered by 4% of screen
height. The shadow and floor reflection share these transforms through the drive-off.
The paint layer uses smooth filtering so the smaller car keeps clean edges.

## Model and animation

`carModel()` in `model.js` returns `{ parts, surfaces, panes, dash }`. Parts are 3D polylines with
cumulative distances and trace timings; surfaces carry a paint tone and optional
wheel axle. Design units are approximately centimetres: x along the car, y upward,
z across it, with the near side at negative z.

- `warp()` shortens the nose; `shape()` leans and rounds the bumper. Every outline,
  surface and decal uses the same transform.
- `zAt()` defines the body width and box flares. `along()` samples flank lines so
  they follow those flares; `across()` and `smooth()` form crowned tops and soft edges.
- The body has black window frames, a painted windscreen surround, six spotlights,
  solid navy mirrors, a charcoal roll cage and two bucket seats with red harnesses.
  Interior outlines are clipped to glass and occluded by the seats and dashboard.
- Wheels have a tyre radius of 32, dished gold mesh rims and recessed hubs. Wheel
  parts rotate around their axle; visible tread edges marked `still` follow the wheel
  without rotating. Tyres are black rubber with a shine along the shoulder.
  Each tyre has a complete 20-unit-deep cylinder, projected as one convex silhouette
  behind the bodywork. The wheel-well backing reaches the bottom of each opening,
  keeping the tread and recess solid when the body pitches during launch.
- Decals are geometry on the body: Martini bands wrap continuously around the
  bumper and sweep over the rear quarter. Lettering follows the same surfaces.

`project()` uses yaw 30°, downward pitch 0.2 radians and perspective distance 1400.
The scale fits 88% of the width or 80% of the height; the camera centre is four design
units above screen centre. The shader reconstructs rays from these same values. Its
nose constants are post-warp positions (front-face anchor x 7, bumper corner base 18,
spotlight planes 7 and 5.7, headlamps 14); pre-warp values silently miss the lamps.

Each outline takes `max(300, length / 0.9)` milliseconds. `add()` starts one every
22ms across all groups: sills, wheels, body, glass, then cabin. This keeps 13–15
outlines in flight without pauses between groups. `car.traced` ends the tracing;
`car.paintTime` is the paint sweep; `car.duration` is their sum. Each comet has three
heat bands and a glow, with its flight offset easing to zero as tracing completes.
`frame()` rebuilds finished outlines only when another part completes. Line groups
0–3 cover interior, detail, panels and silhouette; group 4 renders construction edges
beneath paint. `underPaint` marks edges the paint covers (the rear opening, rounded
bumper join, wing and intake mouth), preserving the tracing without drawing a seam
over a continuous painted surface.

| Drive-off time | Behaviour |
|---|---|
| 0–300ms | Lamps flicker on; the body idles with a small shake |
| 300–500ms | Wheels spin; the body pitches nose-up around the rear axle |
| 500–1100ms | The car scales and slides left with trailing speed streaks |

Wheel rotation advances by up to 0.14 radians per frame to avoid apparent reverse
rotation. Body surfaces pitch and shake; wheel surfaces do not. The shader undoes
the body pose before shading so the environment stays fixed. The floor reflection mirrors
the car about its tyre-contact line, blurs and fades it, and follows the animations.

The body keeps its parked shapes through the drive-off and takes its pose as one flat transform,
`car.bodyPose`: the affine least-squares fit, over every eighth body outline point, from where they
park to where the pose takes them. Paintwork's body shapes (`BodyCoat`, `BodyInk`, `BodyMask`)
carry it; the wheels' shapes sit between them in the same drawing order and are projected again only
as they turn. Streaks trail on screen from the posed body. The fit matches the shake within 0.5px,
but a flat transform can't show the squat's parallax: at full pitch it strays 4.7px on average and up
to 20px at 1080p (twice that at 4K). Re-posing the body exactly cost about 40ms of projection and
tessellation a frame and held the first 500ms near 25fps; the whole drive now keeps the display's 144fps.
`project()` runs once per size: width and height each report a resize, and the car completes at its size.

## Paint and shader

Visible geometry uses `Shape.CurveRenderer`. A separate offscreen material mask uses
`GeometryRenderer`: interpolating discrete material IDs at its edges would select
unrelated materials. Mask red stores `panel / 16`; green stores top-plane height / 160,
or on black plastic whether it is a spotlight can. Cabin tones get one mask fill each:
overlapping tones merged into one path cancel under either fill rule.
The solid far cabin panels use winding fill: odd-even curve tessellation dropped
triangles through the windscreen and beside the seat as the body pitched during drive-off.

| Mask ID | Surface |
|---|---|
| 0 | Excluded: glass, centre caps, glints and background |
| 1 | Flank, wheel skirts and wing fins (green encodes their Z plane) |
| 2 | Front faces |
| 3 | Hood, roof, deck, bumper ledge; wing (green 1) |
| 4 | Upper flank |
| 5 | Inner arch walls and recessed sill return |
| 6 | Windscreen surround |
| 7 | Rounded bumper |
| 8–10 | Gold rim lip, spokes and hub |
| 11 | Tyre sidewalls, treads and volume |
| 12 | Gloss black lamp panel, spotlight cans, intake and wing carbon tips |
| 13 | Lamp and indicator glass |
| 14 | Chrome bezels and spotlight rims |
| 15 | Cabin shell, seats, dash and roll cage |
| 16 | Rounded mirror housings (green 0 near / 1 far) and rubber flaps (green 0.5) |

The S1 wing is kept compact: a 24-unit chord and a 2-unit airfoil section from x 384
to 408, rising from 120 to 121.5. It stands on white fins flush with the deck's edges
(z ±76), no deeper than the plane: from a short foot (x 393–403) their front edges
sweep forward to its nose, like the S1's, with carbon tips curving up over the
trailing edge. The deck runs flat to the tail (the Quattro's lip is gone), and each
fin's rear edge rises from the tail's top corner, so nothing pokes out beside it.
The fins share the flank's curved clear-coat normal, so the body's reflections carry
across them; the far fin's inner face darkens toward the plane's shade. The carbon
tips use the mirror housings' glossy material, their normals curling up and forward
toward the top edge into a sky highlight; mask blue marks the far tip's plane. The
plane, far fin and far tip render before the cabin/body in both paint and mask; only
the near fin and tip render afterward. Wing tracing sits under the paint, so the roof
and C-pillar hide the far fin.
The mirrors are flattened rounded housings, with an explicit rear rim and short
mount. Their shader intersects the same rounded-box surface used by the geometry.
The intake mouth lies on the flare's front face at x=270, spanning its width in z.
Its mesh sits behind that plane along the car's length. A painted outer cheek blends
back into the arch at x=286 and into the shoulder/sill above and below. The body and
livery share this surface; the shader intersects the same shape. Intake mask green
0.4 uses blue 1 for mesh, 0.5 for the return, 0.25 for the front lip, and 0 for the cheek.
The ochre rubber flaps shade continuously into the arch.

These mask IDs are separate from the QML paint-tone indices into `car.paint`:
`Paint { tone: N }` fills tone N's body surfaces in its pigment (`Wheel` its wheel
surfaces), and `Inked` strokes a tone at its `car.ink` width. Bumper tone 28 has its own
surface group and the same pigment as flank tone 0. It must not inherit the upper-flank pigment: even a small difference
leaves a visible seam below the stripes.

The fragment shader reconstructs each surface position, adds analytical curvature to
its normal, and samples the city artwork in the reflected direction. This treats the
2D plate as an approximate environment, not a calibrated panorama. A fixed mip level
keeps the clear-coat reflections soft at both 1080p and 4K. Cooler, dimmer diffuse light
and pink spill from the signs replace the white studio lighting.
It shades in linear colour and converts back for display. Reflections cover the
livery; gold retains its satin response. Shading covers whatever the mask holds,
so unpainted tracing is unchanged and the metal arrives with the paint.
Gold uses one broad reflection lobe for a continuous satin highlight on the hubs and
rims. Its lighting branch skips the body clear coat's detailed city reflections.
Tyre sidewalls are flat, rolling over at the shoulder, where they shine with analytic
lights only: a sky highlight and a soft pink glow. Mirroring the city there washed them
grey, and even its bright lights alone smeared into streaks across the turning shoulder.
Spotlight cans sample the city at a high mip level, only as a faint glow. The rim barrel
has no outline: seen through the mesh, it read as the tyre's far side. Lamps are domed
round the known spotlight centres (headlamps curve across their height): glass shows a
bright reflector ring round a dark bulb and chrome mirrors a softened city. The cabin
sits in shadow with a pool of light mid-cabin, blue at the front and pink at the rear.
The nose's fine lines and spotlights draw inside the shaded layer so the spotlights can
be lit; their draw order is unchanged.

Every painted group is a `Coat`, clipped at `car.front` until `painted == 1`.
Sliding the clip avoids reshaping surfaces each frame. The material mask uses the
same clip on a wrapping `Item`, since a layered shape cannot clip its own paths.
Before the paint starts both are transparent, so the layers redrawn for every tracing frame skip
them; transparent rather than invisible, since a hidden shape misses updates to its paths.
`car.wavefront` follows the surface crossings, stroked in the comets' blue.

This approximates curved panels on projected polygons. It is not a full 3D mesh or
PBR renderer; glass and outlines retain their existing rendering.

### Joins that must stay continuous

- **Bumper:** `faceAt()`/`shape()` and the shader agree on the corner and lower foot;
  the tangent matches the flank's full normal and lighting position.
- **Wheel skirts:** share the flank's normal field, without a separate radial highlight.
- **Inner returns:** a radius-36 cylinder blends from the lip at z=-88 to shadow at
  z=-80; coverage outside the opening preserves body lighting. Shadow fades below
  1.5 pixels of projected width. The sill return shares this recessed material.
- **Arch geometry:** `wallAngles()` solves the projected edge meeting; `arch()` uses
  one two-degree grid for the opening and returns, without an extra return stroke.
- **Draw order:** construction lines stay beneath paint, including the rear opening
  and bumper joins.

The final focus pass covers the complete car, including its outlines. A height
ramp between the projected tops of the near wheels and the far roof approximates
depth: wheels and lower body stay sharp, while upper edges soften with a nine-tap
Gaussian kernel reaching 1.35 pixels at 1080p (scaled for 4K). Premultiplied color
and alpha blur together to blend into the scenery without dark fringes. The ramp
follows body pitch, lives inside the departure transforms, and fades in with paint.

After GLSL changes, rebuild the bundled shaders:

```bash
scripts/build-shaders.sh lock/rally/*.frag
```

## Files

| File | Responsibility |
|---|---|
| `lock/rally/Scene.qml` | Scenery, contact shadow, floor reflection and the car's framing |
| `lock/rally/Car.qml` | Projection, tracing, paint sweep and drive-off |
| `lock/rally/Paintwork.qml` | Material mask, shaded paint, outlines and comets, in draw order |
| `lock/rally/model.js` | Assembles the car from its parts |
| `lock/rally/shape.js` | Body width, nose warp and the curves every part is drawn with |
| `lock/rally/outlines.js` | Traced outlines: sills, wheels, shell, flank, front, details and wing |
| `lock/rally/cabin.js` | Dash, steering wheel, roll cage, harness and seats |
| `lock/rally/body.js` | Painted panels: bodywork, glass, wheels, mirrors, lamps and wing |
| `lock/rally/livery.js` | Stripes, decals, lettering and the side intake |
| `lock/rally/car-paint.frag` / `.qsb` | Analytical surface normals and city reflections, source and compiled |
| `lock/rally/car-focus.frag` / `.qsb` | Final camera focus pass, source and compiled |
| `lock/rally/neon-city.png` | Illustrated background and paint reflection source |
| `tests/lock.js` | Finite tracing and drive-off frames, paint sweep, glass clipping and flat-pose bounds |

## Verification

`lock.js` checks that every tracing and drive-off frame is finite, the paint sweeps the whole
car behind a lit edge, inside outlines are clipped to the glass, and the body's flat drive-off
pose keeps within half a pixel of the exact shake and 5px on average of the squat.
The tests check behaviour, not looks: inspect whole captures for visual changes.

## S1 E2 history

Rejected along the way; don't retry these without a new direction from the user:

- **Bonnet vents:** triangular S1 openings, aligned louvres, black-backed pockets with
  woven floors and tapered outboard cutouts all read as grilles laid on the hood, with
  pixelated edges and stripes cut between slots. The bonnet is continuous; a new attempt
  must solve the flatness, the edges and the stripe clash.
- **Side intake:** side-facing recesses read as pasted on and flat, even with deeper
  shading. The mouth now faces forward on the flare's front face.
- **Mirrors:** pointed cones; now rounded, flattened housings.
- **Wing:** a 46–60 unit chord on grey block supports with end plates read as bigger than
  the car, and its far side drew over the roof. The Quattro's deck lip poked out beside
  it; the deck now runs flat to the tail, without the lip or its black rubber strip.
- **Mud flaps:** flat colour bands; now continuously shaded rubber.

## Remaining work

- The S1 E2's aero parts remain subject to visual review.
- Thin gaps along the roof and belt show during pitch.
- Native 4K artwork is deferred.
