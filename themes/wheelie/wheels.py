"""Prepare concentric rotating sprites from the generated RGBA wheel sheet."""
import subprocess

import numpy as np


def load(path):
    w, h = map(int, subprocess.check_output(
        ["magick", "identify", "-format", "%w %h", str(path)]).split())
    raw = subprocess.check_output(["magick", str(path), "-depth", "8", "rgba:-"])
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4).astype(np.float32) / 255


def save(path, pixels):
    h, w = pixels.shape[:2]
    subprocess.run(["magick", "-size", f"{w}x{h}", "-depth", "8", "rgba:-", str(path)],
                   input=(np.clip(pixels, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)


def sample(pixels, x, y):
    x = np.clip(x - 0.5, 0, pixels.shape[1] - 1.001)
    y = np.clip(y - 0.5, 0, pixels.shape[0] - 1.001)
    ix, iy = x.astype(int), y.astype(int)
    fx, fy = (x - ix)[..., None], (y - iy)[..., None]
    return (pixels[iy, ix] * (1 - fx) * (1 - fy) + pixels[iy, ix + 1] * fx * (1 - fy)
            + pixels[iy + 1, ix] * (1 - fx) * fy + pixels[iy + 1, ix + 1] * fx * fy)


def circle(x, y):
    d, e, f = np.linalg.lstsq(np.stack([x, y, np.ones_like(x)], 1),
                             -(x * x + y * y), rcond=None)[0]
    return -d / 2, -e / 2, np.sqrt((d * d + e * e) / 4 - f)


def waves(angle):
    """Cosine and sine of the first six angular harmonics, on a new last axis."""
    return np.stack([f(k * angle) for k in range(1, 7) for f in (np.cos, np.sin)], -1)


def contour(theta, radius, keep):
    """A traced edge's mean radius and first six harmonics, refit without stray angles."""
    basis = np.c_[np.ones_like(theta), waves(theta)]
    for _ in range(3):
        fit = np.linalg.lstsq(basis[keep], radius[keep], rcond=None)[0]
        keep = keep & (np.abs(radius - basis @ fit) < 1.5)
    return fit


def even_tire_light(sprite, inner):
    # Broad light/contrast patches rotating around a centered tire look like wobble.
    # Remove slow angular variation only; tread blocks and fine texture stay sharp.
    center = len(sprite) / 2
    theta = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    radii = np.arange(int(inner), int(center))
    polar = sample(sprite, center + radii[:, None] * np.cos(theta),
                   center + radii[:, None] * np.sin(theta))
    light, weight = polar[..., :3].mean(-1), polar[..., 3]
    basis = np.c_[np.ones_like(theta), waves(theta)]
    level, spread, mean = light.copy(), np.ones_like(light), light.mean(1)
    for i, w in enumerate(weight):
        if w.sum() < 40:
            continue
        level[i] = basis @ np.linalg.lstsq(basis * w[:, None], light[i] * w, rcond=None)[0]
        mean[i] = np.average(level[i], weights=w)
        contrast = np.abs(light[i] - level[i])
        slow = basis @ np.linalg.lstsq(basis * w[:, None], contrast * w, rcond=None)[0]
        spread[i] = np.clip(np.average(contrast, weights=w) / np.maximum(slow, 0.01), 0.5, 1.5)
    y, x = np.mgrid[:len(sprite), :len(sprite)] + 0.5 - center
    radius, angle = np.hypot(x, y), np.arctan2(y, x)
    ri = np.clip(np.rint(radius).astype(int) - radii[0], 0, len(radii) - 1)
    ai = np.rint(angle * 720 / (2 * np.pi)).astype(int) % 720
    original = sprite[..., :3].mean(-1)
    corrected = mean[ri] + (original - level[ri, ai]) * spread[ri, ai]
    fade = np.clip((radius - inner) / 4, 0, 1)
    # The rim-side sidewall is lit about 3.5x brighter on one side; allow enough gain to even it.
    gain = np.clip(corrected / np.maximum(original, 0.01), 0.25, 4)
    sprite[..., :3] *= (1 + (gain - 1) * fade)[..., None]


def prepare(sheet, matte_sheet, name, radius, destination):
    side = sheet.shape[0]
    source = sheet[:, :side] if name == "front" else sheet[:, side:]
    alpha = source[..., 3]
    yy, xx = np.mgrid[:side, :side] + 0.5
    # The bearing opening is transparent; center it independently from the tire.
    hole = (np.hypot(xx - side / 2, yy - side / 2) < 22) & (alpha < 0.25)
    hx, hy = xx[hole].mean(), yy[hole].mean()
    theta = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
    radii = np.arange(side * 0.30, side * 0.50, 0.25)
    polar = sample(source, hx + radii[:, None] * np.cos(theta),
                   hy + radii[:, None] * np.sin(theta))[..., 3]
    outer = radii[len(radii) - 1 - np.argmax((polar > 0.5)[::-1], axis=0)]
    _, _, tr = circle(hx + outer * np.cos(theta), hy + outer * np.sin(theta))
    # Locate the rim's inner edge at the last transparent gap between spokes.
    gaps = (polar < 0.5) & (radii[:, None] < tr * 0.80)
    inner = radii[len(radii) - 1 - np.argmax(gaps[::-1], axis=0)]
    valid = gaps.any(0) & (inner > np.median(inner) - 15)
    for _ in range(3):
        rx, ry, rr = circle(hx + inner[valid] * np.cos(theta[valid]),
                             hy + inner[valid] * np.sin(theta[valid]))
        residual = np.hypot(hx + inner * np.cos(theta) - rx, hy + inner * np.sin(theta) - ry) - rr
        valid = gaps.any(0) & (np.abs(residual) < 3)
    # Correct only broad tire-outline deviations; retain the individual tread blocks.
    harmonics = np.linalg.lstsq(waves(theta), outer - outer.mean(), rcond=None)[0]
    # Take only the new rim finish; keep the accepted tire, spokes, hub, and alpha.
    matte = matte_sheet[:, :side] if name == "front" else matte_sheet[:, side:]
    rim_distance = np.hypot(xx - rx, yy - ry)
    finish = (np.clip((rim_distance - rr - 2) / 3, 0, 1)
              * np.clip((rr + 54 - rim_distance) / 5, 0, 1))[..., None]
    source = source.copy()
    source[..., :3] = source[..., :3] * (1 - finish) + matte[..., :3] * finish
    # Trace both rim edges from the rim center: where the spoke gaps end, and the dark seam
    # where the tire begins. Elliptical edges would visibly pulse as the wheel turns.
    band = np.arange(rr - 10, rr + 50, 0.25)
    ring = sample(source, rx + band[:, None] * np.cos(theta), ry + band[:, None] * np.sin(theta))
    edge = band[len(band) - 1 - np.argmax((ring[..., 3] < 0.5)[::-1], axis=0)]
    seam = band[np.argmin(np.where(band[:, None] > rr + 30, ring[..., :3].mean(-1), 1), axis=0)]
    rim = contour(theta, edge, (ring[band < rr - 4, :, 3] < 0.25).all(0))
    seam = contour(theta, seam, np.ones_like(theta, bool))
    size = 2 * (radius + 18)
    y, x = (np.mgrid[:size, :size].astype(np.float32) + 0.5 - size / 2) * tr / radius
    dist, angle = np.hypot(x, y), np.arctan2(y, x)
    # Map the bearing, both rim edges, and the tread outline onto concentric circles.
    knots = [0, 0.25 * tr, rim[0], seam[0], tr]
    centers = [np.interp(dist, knots, [h, h, r, r, h]) for h, r in ((hx, rx), (hy, ry))]
    wave = waves(angle)
    shift = sum(np.interp(dist, knots, hat) * (wave @ fit)
                for hat, fit in zip(np.eye(5)[2:], (rim[1:], seam[1:], harmonics)))
    factor = 1 + shift / dist
    premultiplied = source.copy()
    premultiplied[..., :3] *= source[..., 3:]
    sprite = sample(premultiplied, centers[0] + x * factor, centers[1] + y * factor)
    sprite[..., :3] /= np.maximum(sprite[..., 3:], 1e-6)
    sprite[sprite[..., 3] < 0.01] = 0
    # Start at the rim: uneven light on it or the sidewall beside it rotates as a bright arc.
    even_tire_light(sprite, rim[0] * radius / tr + 1)
    save(destination, sprite)
    print(f"{name}: source hub {hx:.2f},{hy:.2f}; rim {rx:.2f},{ry:.2f}; "
          f"tread r={tr:.2f}; output {size}px, radius {radius}px")
    return size
