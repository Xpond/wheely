"""Frame fd output in bounded, UTF-8-safe batches for Quickshell's SplitParser."""
import select
import signal
import subprocess
import sys
import time


try:
    child = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE)
except OSError as error:
    sys.exit(f"Wheel file scan: {error}")


def stop(signum, frame):
    raise SystemExit(128 + signum)


signal.signal(signal.SIGTERM, stop)
try:
    pending = b""
    flushed = 0  # Publish the first complete lines immediately.
    while True:
        ready = select.select([child.stdout], [], [], 0.016)[0]
        chunk = child.stdout.read1(65536) if ready else None
        if chunk:
            pending += chunk
        # A NUL cannot occur in a path. Decode only after a complete batch arrives.
        if len(pending) >= 65536 or not chunk or time.monotonic() - flushed >= 0.016:
            end = len(pending) if chunk == b"" else pending.rfind(b"\n") + 1
            if end:
                sys.stdout.buffer.write(pending[:end] + b"\0")
                sys.stdout.buffer.flush()
                pending = pending[end:]
                flushed = time.monotonic()
        if chunk == b"":
            break
    sys.exit(child.wait())
finally:
    if child.poll() is None:
        child.terminate()
    child.wait()
