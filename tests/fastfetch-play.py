#!/usr/bin/env python3
"""Play a tiny two-frame scene through wheely-fetch on a pseudo-terminal, with fastfetch stubbed."""
import os
from pathlib import Path
import pty
import subprocess
import tempfile
import tty

player = Path(__file__).resolve().parents[1] / "themes/fastfetch-play"

with tempfile.TemporaryDirectory(prefix="fastfetch-play-") as temp:
    home, commands = Path(temp) / "home", Path(temp) / "bin"
    scene = home / ".local/state/omarchy/current/theme/fastfetch"
    scene.mkdir(parents=True)
    commands.mkdir()
    # fastfetch draws a 2-row logo padded down one line beside 3 info lines, then its blank line.
    stub = commands / "fastfetch"
    stub.write_text('#!/bin/sh\necho "$*" >> "$HOME/calls"\nprintf "info\\nLOGO1 info\\nLOGO2 info\\n  \\n\\033[m"\n')
    stub.chmod(0o755)
    env = os.environ | {"HOME": str(home), "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}"}

    def run(*args):
        """The player's output on a terminal."""
        leader, follower = pty.openpty()
        tty.setraw(follower)  # bytes as written, without newline translation
        subprocess.run([str(player), *args], env=env, stdout=follower, check=True, timeout=10)
        os.close(follower)
        out = b""
        try:
            while chunk := os.read(leader, 65536): out += chunk
        except OSError:
            pass
        return out.decode()

    # Without a scene, plain fastfetch.
    run()
    assert (home / "calls").read_text() == "\n", "a theme without a scene was not plain fastfetch"

    (scene / "scene.txt").write_text("4 2 2 60\nAAAA\nBBBB\n\x1b[2CX\n\n")
    out = run()
    assert (home / "calls").read_text().splitlines()[-1] == f"-c {scene}/config.jsonc --pipe false"
    # fastfetch printed 4 lines: each frame climbs 3 to the logo, draws its 2 rows, steps back down 1.
    assert out.count("\x1b[3A") == 2 and out.count("\x1b[1B") == 2, out
    assert "\x1b[2CAAAA\r\n\x1b[2CBBBB\r\n" in out and "\x1b[2C\x1b[2CX\r\n\x1b[2C\r\n" in out, out
    # The cursor shows again, and fastfetch's blank last line is taken back for the prompt.
    assert out.endswith("\x1b[?25h") and "\x1b[1A" in out.rsplit("\x1b[2C", 1)[1], out
    print("ok: wheely-fetch plays the scene over fastfetch's logo")

    # Arguments, or a pipe, get plain fastfetch.
    run("--logo", "none")
    assert (home / "calls").read_text().splitlines()[-1] == "--logo none"
    piped = subprocess.run([str(player)], env=env, capture_output=True, text=True, check=True)
    assert (home / "calls").read_text().splitlines()[-1] == "" and "\x1b[" not in piped.stdout.replace("\x1b[m", "")
    print("ok: wheely-fetch is plain fastfetch for arguments and pipes")
