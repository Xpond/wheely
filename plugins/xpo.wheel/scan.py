"""Frame fd output in bounded, UTF-8-safe batches for Quickshell's SplitParser."""
import os
import select
import signal
import sys
import time


read_fd, write_fd = os.pipe()
try:
    child = os.posix_spawnp(sys.argv[1], sys.argv[1:], os.environ,
                           file_actions=[(os.POSIX_SPAWN_DUP2, write_fd, 1)],
                           setsigdef=(signal.SIGPIPE, signal.SIGXFSZ))
except OSError as error:
    sys.exit(f"Wheel file scan: {error}")
finally:
    os.close(write_fd)


def stop(signum, frame):
    raise SystemExit(128 + signum)


signal.signal(signal.SIGTERM, stop)
try:
    pending = b""
    flushed = 0  # Publish the first complete lines immediately.
    while True:
        ready = select.select([read_fd], [], [], 0.016)[0]
        chunk = os.read(read_fd, 65536) if ready else None
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
    _, status = os.waitpid(child, 0)
    child = None
    sys.exit(os.waitstatus_to_exitcode(status))
finally:
    os.close(read_fd)
    if child is not None:
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass
        os.waitpid(child, 0)
