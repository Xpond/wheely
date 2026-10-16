"""Place photographic chain links on a measured path behind the bike's fixed parts."""
import base64
import subprocess

import numpy as np

from wheels import load, sample, save


def build_chain(root, out, scene):
    source = load(root / "sources/chain.png")
    # A straight link from the generated material; its two rivets define the pitch.
    pin = np.array([619.0, 335.0])
    direction = np.array([58.0, -14.0])
    span = np.linalg.norm(direction)
    u = direction / span
    v = np.array([-u[1], u[0]])
    ty, tx = np.mgrid[-28:28, -14:int(np.ceil(span)) + 14].astype(float) + 0.5
    link = sample(source, pin[0] + tx * u[0] + ty * v[0], pin[1] + tx * u[1] + ty * v[1])
    save(out / "chain-link.png", link)

    front, rear = np.array([3860.0, 1995.0]), np.array([4338.0, 2314.0])
    small, large = 29.0, 103.0
    axis = rear - front
    length = np.linalg.norm(axis)
    u = axis / length
    v = np.array([-u[1], u[0]])
    q = (large - small) / length
    upper, lower = -q * u - np.sqrt(1 - q * q) * v, -q * u + np.sqrt(1 - q * q) * v
    a, b = front + small * upper, rear + large * upper
    c, d = rear + large * lower, front + small * lower
    t = np.linspace(0, 1, 600, endpoint=False)[:, None]
    angle = np.arctan2(upper[1], upper[0])
    sweep = (np.arctan2(lower[1], lower[0]) - angle) % (2 * np.pi)
    rear_angles = angle + np.linspace(0, sweep, 400, endpoint=False)
    front_angles = angle + np.linspace(sweep, 2 * np.pi, 160, endpoint=False)
    bottom = c * (1 - t) + d * t + np.array([0, 5]) * 4 * t * (1 - t)
    route = np.concatenate([a * (1 - t) + b * t,
                            rear + large * np.stack([np.cos(rear_angles), np.sin(rear_angles)], 1),
                            bottom,
                            front + small * np.stack([np.cos(front_angles), np.sin(front_angles)], 1), [a]])
    distance = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(route, axis=0), axis=1))])
    teeth = 43  # The rear sprite's measured tooth repetition.
    pitch = 2 * np.pi * large / teeth
    count = round(distance[-1] / pitch)
    left, top = np.floor(route.min(0) - 12).astype(int)
    width, height = np.ceil(route.max(0) + 12 - [left, top]).astype(int)
    encoded = base64.b64encode((out / "chain-link.png").read_bytes()).decode()
    # In front of the wheel, behind the boot/engine; rear-cover.png masks the swingarm.
    patch = scene[top:top + height, left:left + width]
    neutral = np.clip((patch[..., 2] - patch[..., 0] + 0.16) / 0.04, 0, 1)
    dark = np.clip((0.48 - patch[..., 1]) / 0.05, 0, 1)
    y, x = np.mgrid[top:top + height, left:left + width]
    hide = np.maximum(neutral, dark) * (x < 4050) * (y < 2220)
    frames, columns = 12, 4
    atlas = np.zeros((height * (frames // columns), width * columns, 4), dtype=np.float32)
    for frame in range(frames):
        # Route is clockwise; subtract travel for the counterclockwise rear wheel.
        steps = ((np.arange(count + 1) - frame / frames) * distance[-1] / count) % distance[-1]
        points = np.stack([np.interp(steps, distance, route[:, i]) for i in (0, 1)], 1)
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}">',
               f'<defs><image id="link" width="{link.shape[1]}" height="{link.shape[0]}" xlink:href="data:image/png;base64,{encoded}"/></defs>']
        for start, stop in zip(points[:-1], points[1:]):
            delta = stop - start
            rotation = np.degrees(np.arctan2(delta[1], delta[0]))
            scale = np.linalg.norm(delta) / span
            x, y = start - [left, top]
            svg.append(f'<use xlink:href="#link" x="-14" y="-28" transform="translate({x} {y}) rotate({rotation}) scale({scale})"/>')
        svg.append('</svg>')
        document = "\n".join(svg) + "\n"
        raster = subprocess.run(["magick", "-background", "none", "-density", "192", "svg:-",
                                 "-resize", f"{width}x{height}!", "-depth", "8", "rgba:-"],
                                input=document.encode(), stdout=subprocess.PIPE, check=True).stdout
        chain = np.frombuffer(raster, np.uint8).reshape(height, width, 4).astype(np.float32) / 255
        chain[..., 3] *= 1 - hide
        row, col = divmod(frame, columns)
        atlas[row * height:(row + 1) * height, col * width:(col + 1) * width] = chain
        if frame == 0:
            (out / "chain.svg").write_text(document)
            save(out / "chain.png", chain)
    save(out / "chain-motion.png", atlas)
    print(f"chain: {count} links, {distance[-1] / count:.2f}px pitch; box {left},{top},{width},{height}")
    return {"box": [int(left), int(top), int(width), int(height)],
            "frames": frames, "columns": columns, "teeth": teeth}
