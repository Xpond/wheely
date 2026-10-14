"""The scan framer preserves bytes, bounds batches, and reaps its fd child."""
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def check(repo):
    reader = [sys.executable, str(repo / "plugins/xpo.wheel/scan.py")]
    raw = ("/home/test/café-数据.txt\n" * 10000).encode() + b"/final"
    with tempfile.TemporaryDirectory(prefix="wheel-reader-") as tmp:
        snapshot = Path(tmp) / "paths"
        snapshot.write_bytes(raw)
        chunks = subprocess.check_output(reader + ["cat", str(snapshot)]).split(b"\0")
        assert b"".join(chunks) == raw, "framing changed path bytes"
        assert max(map(len, chunks)) < 131072, "a batch retained the whole scan"
        for chunk in chunks:
            chunk.decode("utf-8")

        pidfile = Path(tmp) / "pid"
        command = [sys.executable, "-c",
                   "import os,time; from pathlib import Path; "
                   f"Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)"]
        child = subprocess.Popen(reader + command, stdout=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            assert pidfile.exists(), "scan child never started"
            pid = int(pidfile.read_text())
            child.terminate()
            child.wait(timeout=3)
            assert not Path(f"/proc/{pid}").exists(), "cancelling left the fd child alive"
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=3)
    print("ok: bounded scan frames, Unicode and child cancellation")
