#!/usr/bin/env python3
"""Check special-character paths and rejection of an incomplete poster."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
build = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else repo / "themes/wheelie/build"
with tempfile.TemporaryDirectory(prefix="wheelie-render-") as temp:
    config = Path(temp) / "scene #100%"
    config.mkdir()
    for file in build.iterdir():
        if file.suffix in (".qml", ".json"):
            shutil.copy2(file, config / file.name)
        elif file.is_file():
            (config / file.name).symlink_to(file)
    output = config / "poster #100%.png"
    command = [sys.executable, str(repo / "themes/wheelie/render.py"), str(config), str(output)]
    env = os.environ | {"QT_QPA_PLATFORMTHEME": "generic"}
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=65)
    assert result.returncode == 0, result.stdout + result.stderr
    opaque = subprocess.check_output(["magick", str(output), "-format", "%[opaque]", "info:"], text=True)
    assert opaque.strip().lower() == "true", result.stdout + result.stderr
    previous = output.read_bytes()
    surface = config / "Surface.qml"
    surface.write_text(surface.read_text().replace('"layout.json"', '"missing-layout.json"'))
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=65)
    assert result.returncode != 0, "A blank scene was accepted as a successful poster"
    assert output.read_bytes() == previous, "Failed rendering replaced the previous poster"
    assert not list(config.glob(".wheelie-render-*"))
print("ok: special-character paths render; incomplete posters fail without replacing the previous output")
