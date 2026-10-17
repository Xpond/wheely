"""Separate sky from everything else, in the scene plate and in the storm plate."""
import subprocess

import numpy as np


def blur(a, r):
    """Approximate a Gaussian with three box passes along each axis."""
    for _ in range(6):
        c = np.cumsum(np.pad(a, [(r + 1, r)] + [(0, 0)] * (a.ndim - 1), mode="edge"), 0,
                      dtype=np.float64)
        a = ((c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)).swapaxes(0, 1)
    return a


def grow(m):
    g = m.copy()
    g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
    return g


def flood(seed, allowed):
    while (grown := seed | (grow(seed) & allowed)).sum() > seed.sum():
        seed = grown
    return seed


def cutout(scene, base, layout):
    """Everything but the sky as an RGBA crop, its origin, and the row where the storm ends.

    Rough hand traces of the rider and the dunes' skyline mark where the plate needs a
    closer look; there the sky is separated at half resolution.
    """
    h, w = base.shape[0] // 2, base.shape[1] // 2

    def trace(name):
        svg = subprocess.check_output(["magick", "-background", "none", "-density", "192",
                                       str(scene / name), "-depth", "8", "rgba:-"])
        return np.frombuffer(svg, np.uint8).reshape(h, w, 4)[..., 3] / 255

    skyline = np.argmax(trace("dunes.svg") > 0.5, 0)
    low = int(skyline.max()) + 4  # Below the traced skyline's lowest point, all is dune.

    # Everything 28 px beyond the rider trace and 40 px above the traced skyline is sky.
    # Nearer, estimate the smooth sky from bright, neutral pixels already freed and free
    # matching pixels connected to them; a second, closer estimate reaches the narrow
    # gaps. A seed frees the sky enclosed between the forearms. The front wheel's plate
    # holds sky copied from farther left, so the skyline continues straight across it.
    inside = trace("rider-trace.svg")[:low] > 0.5
    plate = base[:2 * low, :, :3].reshape(low, 2, w, 2, 3).mean((1, 3))
    near = inside
    for _ in range(28):
        near = grow(near)
    y, x = np.mgrid[0:low, 0:w]
    wheel = layout["wheels"]["front"]
    disc = np.hypot(2 * x - wheel["center"][0], 2 * y - wheel["center"][1]) < wheel["radius"] + 18
    zone = (near | (y >= skyline - 40)) & ~disc
    skyish = (plate.min(-1) > 0.7) & (plate.max(-1) - plate.min(-1) < 0.2)
    freed = ~zone
    freed[1285 // 2, 3960 // 2] = True
    for r in (30, 10):
        anchor = freed & skyish
        sky = blur(plate * anchor[..., None], r) / np.maximum(blur(anchor, r), 1e-9)[..., None]
        match = (np.abs(plate - sky).max(-1) < 0.06) & zone
        freed = flood(freed | (~inside & match), match)
    cols = np.nonzero(disc.any(0))[0]  # Continue the skyline found beside the front wheel.
    found = np.argmax(~freed & (y >= skyline - 40), 0)
    line = np.interp(np.arange(w), cols[[0, -1]], found[[cols[0] - 2, cols[-1] + 2]])
    freed = np.where(disc, y < line, freed)
    freed = ~flood(~freed & (y == low - 1), ~freed)  # Stray specks unjoined to the dunes are sky.

    # Full resolution. The anti-aliased outlines still hold the plate's pale sky, which
    # would outline them against the storm. Within two pixels either side of an outline,
    # recover each pixel's coverage against the sky estimate and use the nearest solid color.
    kept = ~np.repeat(np.repeat(freed, 2, 0), 2, 1)
    back = np.repeat(np.repeat(sky, 2, 0), 2, 1)
    pixels = base[:2 * low, :, :3]
    solid = ~grow(grow(~kept))
    color, known = pixels * solid[..., None], solid.copy()
    for _ in range(5):
        total, count = np.zeros_like(color), np.zeros(known.shape)
        for axis, step in ((0, 1), (0, -1), (1, 1), (1, -1)):
            total += np.roll(color, step, axis)
            count += np.roll(known, step, axis)
        new = ~known & (count > 0)
        color[new] = total[new] / count[new, None]
        known |= new
    color = np.where(known[..., None], color, pixels)  # Too thin to have a solid core.
    gap = ((color - back) ** 2).sum(-1)
    coverage = np.clip(((pixels - back) * (color - back)).sum(-1) / np.maximum(gap, 1e-3), 0, 1)
    # Where a color is too close to the sky's, soften the outline instead.
    edge = known & ~solid & grow(grow(kept))
    alpha = np.where(edge, np.where(gap < 0.01, blur(kept.astype(np.float32), 1), coverage), kept)
    ys, xs = np.nonzero(alpha)
    rgba = np.dstack([color, alpha])[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # The storm ends a few rows inside the redrawn dunes, so none shows under their edge.
    return rgba, [int(xs.min()), int(ys.min())], 2 * (low - 3)


def storm_sky(storm):
    """The smooth dusk sky the storm plate was generated over, at an eighth of its size.

    Fit a smooth surface to the open sky well above the first warm dust, then hold it
    constant down into the dust body. storm-wall.frag removes it from the plate.
    """
    h, w = storm.shape[0] // 8, storm.shape[1] // 8
    storm = storm[:h * 8, :w * 8, :3].reshape(h, 8, w, 8, 3).mean((1, 3))
    crest = np.argmax(storm[..., 0] - storm[..., 2] > 0.15, 0)
    y, x = np.mgrid[-1:1:h * 1j, -1:1:w * 1j]
    terms = np.stack([x ** i * y ** j for i in range(5) for j in range(5 - i)], -1)
    open_sky = np.arange(h)[:, None] < crest - 19
    sky = terms @ np.linalg.lstsq(terms[open_sky], storm[open_sky], rcond=None)[0]
    for col, row in enumerate(np.minimum(crest + 12, h - 1)):
        sky[row:, col] = sky[row, col]
    return np.dstack([np.clip(blur(sky, 2), 0, 1), np.ones((h, w))])
