"""Render the live QML scene offscreen: render.py <bake directory> <output.png> [angle]."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

directory, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
size = json.loads((directory / "layout.json").read_text())["size"]
env = os.environ | {
    "QT_QPA_PLATFORM": "offscreen",
    "QT_QUICK_BACKEND": "rhi",  # The default offscreen software backend cannot draw shaders.
    "QSG_RHI_BACKEND": "opengl",
    "WHEELIE_WIDTH": str(size[0]), "WHEELIE_HEIGHT": str(size[1]),
    "WHEELIE_ANGLE": sys.argv[3] if len(sys.argv) > 3 else "0",
}
with tempfile.TemporaryDirectory(prefix=".wheelie-render-", dir=output.parent) as temp:
    poster = Path(temp) / "poster.png"
    env["WHEELIE_OUTPUT"] = str(poster)
    subprocess.run(["quickshell", "-p", str(directory / "Render.qml")],
                   env=env, check=True, timeout=60)
    # A complete scene fills the frame; a saved transparent image is not a successful render.
    opaque = subprocess.check_output(["magick", str(poster), "-format", "%[opaque]", "info:"], text=True)
    if opaque.strip().lower() != "true":
        sys.exit("Wheelie scene did not render completely; previous poster preserved.")
    poster.replace(output)
