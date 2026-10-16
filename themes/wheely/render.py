"""Render the live QML scene offscreen: render.py <bake directory> <output.png> [angle]."""
import json
import os
from pathlib import Path
import subprocess
import sys

directory, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
size = json.loads((directory / "layout.json").read_text())["size"]
env = os.environ | {
    "QT_QPA_PLATFORM": "offscreen",
    "QT_QUICK_BACKEND": "rhi",  # The default offscreen software backend cannot draw shaders.
    "QSG_RHI_BACKEND": "opengl",
    "WHEELY_WIDTH": str(size[0]), "WHEELY_HEIGHT": str(size[1]),
    "WHEELY_ANGLE": sys.argv[3] if len(sys.argv) > 3 else "0",
    "WHEELY_OUTPUT": str(output),
}
subprocess.run(["quickshell", "-p", str(directory / "Render.qml")],
               env=env, check=True, timeout=60)
