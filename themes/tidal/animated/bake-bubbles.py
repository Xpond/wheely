from pathlib import Path
import numpy as np
import subprocess

# Seamless bubble distances (R) and surface slopes (GB).
size, cells = 1024, 64
rng = np.random.default_rng(812)
points = rng.random((cells, cells, 2)).astype(np.float32)
y, x = np.mgrid[:size, :size].astype(np.float32) * cells / size
ix, iy = x.astype(int), y.astype(int)
fx, fy = x - ix, y - iy
distance = np.full((size, size), 9, dtype=np.float32)
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        p = points[(iy + dy) % cells, (ix + dx) % cells]
        d = (dx + p[..., 0] - fx)**2 + (dy + p[..., 1] - fy)**2
        distance = np.minimum(distance, d)
distance = np.sqrt(distance)
gx = (np.roll(distance, -1, 1) - np.roll(distance, 1, 1)) * size / cells / 2
gy = (np.roll(distance, -1, 0) - np.roll(distance, 1, 0)) * size / cells / 2
rgb = np.stack((distance, gx * .5 + .5, gy * .5 + .5), axis=-1)
rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
out = Path(__file__).parent
subprocess.run(['magick', 'ppm:-', '-strip', str(out / 'bubbles.png')],
               input=f'P6\n{size} {size}\n255\n'.encode() + rgb.tobytes(), check=True)
