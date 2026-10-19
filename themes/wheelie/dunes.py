"""Put the dunes in the storm's shade."""
import numpy as np

from sky import blur, trace

# Sand in the storm's shade: its dust hue (storm-wall.frag), a little lighter and duller.
SHADE = np.array([0.498, 0.366, 0.289])


def linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def encode(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def smooth(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def shade(scene, base, rgba, top):
    """Darken the dunes and blend the foreground's far edge into them, in place, in the plate
    and in the cutout whose first row is `top`."""
    first, last = 1850, 2700  # The rows holding the dunes, with margin.
    split = top + len(rgba)  # Above this row the cutout shows; below it, the plate.
    solid = base[first:last, :, :3].copy()
    solid[:split - first] = rgba[first - top:, :, :3]
    h, w = base.shape[0] // 2, base.shape[1] // 2
    rider = trace(scene / "rider-trace.svg", h, w).repeat(2, 0).repeat(2, 1)[first:last] > 0.5
    traced = 2 * np.argmax(trace(scene / "dunes.svg", h, w) > 0.5, 0).repeat(2)
    y, x = np.arange(first, last)[:, None], np.arange(2 * w)

    # Near the rider, color tells pale warm sand from paint, plastic, metal, and rubber.
    warmth = solid[..., 0] - solid[..., 2]
    peak = solid.max(-1)
    key = (smooth(0.10, 0.18, warmth) * (1 - smooth(0.42, 0.50, warmth))
           * smooth(0.55, 0.68, solid @ [0.2126, 0.7152, 0.0722])
           * (1 - smooth(0.45, 0.55, (peak - solid.min(-1)) / np.maximum(peak, 1e-4))))
    cols = np.nonzero(rider.any(0))[0]
    near = (x >= cols[0] - 40) & (x <= cols[-1] + 40)
    # The skyline is the cutout's edge; behind the rider it follows the traced skyline.
    sky = np.argmax(rgba[first - top:, :, 3] >= 0.5, 0) + first
    sky = np.interp(x, x[~near], (sky - traced)[~near]) + traced
    # The foreground's far edge is the last warm row; the rider sits above it.
    edge = last - 1 - np.argmax(warmth[::-1] > 0.08, 0)
    # The pale crest is sand wherever the rider trace does not reach it.
    rows = (sky - first + np.arange(-5, 26)[:, None]).astype(int)
    crest = (y < sky + 25) & ~(np.convolve(rider[rows, x].any(0), np.ones(41), "same") > 0)
    # Along the edge, a pixel's share of sand lies between the warmth of the sand above and below.
    above, below = warmth[edge - first - 4, x], warmth[edge - first + 5, x]
    share = np.clip((warmth - below) / np.maximum(above - below, 0.05), 0, 1)
    mask = np.where(y < edge, np.where(near & ~crest, key, 1), np.where(y <= edge + 3, share, 0))

    # One gain takes the sand, crest aside, to the shade. A partly covered pixel takes its share
    # of the change to the sand beside it, so no pale sand lingers along an edge.
    c = linear(solid)
    pure = mask >= 0.99
    gain = linear(SHADE) / c[pure & ~near & (y >= sky + 25)].mean(0)
    weight = blur(pure.astype(np.float32), 6)
    sand = blur(c * pure[..., None], 6) / np.maximum(weight, 1e-6)[..., None]
    # At the foreground edge, scale each pixel itself: the photo's crest lip is darker than
    # either side, and taking the bright sand's change would crush it to black.
    sand = np.where(((weight > 0.05) & (y < edge))[..., None], sand, c)
    c = c + (gain - 1) * np.where(pure[..., None], c, mask[..., None] * sand)
    # The far foreground takes on some of the shade and cools toward the viewer, so the
    # dunes do not meet it in a hard color change.
    tint = linear(SHADE) / c[(y > edge + 5) & (y < edge + 60) & ~near].mean(0)
    fade = 0.75 * (1 - smooth(0, 220, y - edge)) * (y > edge) * (1 - mask)
    c = c * (1 + (tint - 1) * fade[..., None])
    # Soften the edge itself: each column blends over the 7 rows around it.
    s = np.cumsum(np.pad(c, [(4, 3), (0, 0), (0, 0)], mode="edge"), 0)
    new = encode(c + ((s[7:] - s[:-7]) / 7 - c) * (1 - smooth(3, 6, np.abs(y - edge)))[..., None])
    rgba[first - top:, :, :3] = new[:split - first]
    base[split:last, :, :3] = new[split - first:]
