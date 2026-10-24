"""Quickshell test helpers: a gate on unexpected warnings, checked source patches, and IPC polling."""
import json
import re
import subprocess
import time

LEVEL = re.compile(r"^(?:[\d-]+ [\d:.]+)?\s*(?:WARN|ERROR|FATAL)\b")
# An offscreen run inside a Wayland session gets a notice over three lines.
NOISE = ["QT_QPA_PLATFORM", "--- WARNING ---"]


def check(log, *expected):
    """Asserts the log has no line at warning level or above beyond that notice and the expected patterns."""
    lines = [line for line in log.splitlines()
             if LEVEL.match(line) and not any(re.search(p, line) for p in NOISE + list(expected))]
    assert not lines, "unexpected Quickshell warnings:\n" + "\n".join(lines)


def patch(text, old, new, count=-1):
    """Replace old, which must be present: a stale pattern would leave real code or state in use."""
    assert old in text, old
    return text.replace(old, new, count)


class Instance:
    """A running Quickshell config reached over IPC; a failure carries its log."""

    def __init__(self, process, shell, target, env, log_path):
        self.process, self.shell, self.target, self.env, self.log_path = process, shell, target, env, log_path

    def ipc(self, action, *args):
        result = subprocess.run(["quickshell", "ipc", "-p", str(self.shell), "call", self.target, action, *map(str, args)],
                                env=self.env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr + self.log_path.read_text()
        return json.loads(result.stdout) if action == "status" else None

    def wait_for(self, predicate):
        """Polls status until predicate holds, for up to 6 s, while the process lives."""
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            assert self.process.poll() is None, self.log_path.read_text()
            try:
                state = self.ipc("status")
                if predicate(state):
                    return state
            except AssertionError:
                if self.process.poll() is not None:
                    raise
            time.sleep(0.05)
        raise AssertionError(self.log_path.read_text())
