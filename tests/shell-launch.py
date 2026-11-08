#!/usr/bin/env python3
"""The managed shell launcher delegates to upstream without losing arguments or user settings."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="wheely-launch-") as temporary:
    root = Path(temporary)
    upstream = root / "omarchy with spaces/bin"
    upstream.mkdir(parents=True)
    launcher = upstream / "omarchy-launch-shell"
    launcher.write_text('''#!/usr/bin/env python3
import ctypes, json, os, sys
thp = ctypes.CDLL(None).prctl(42, 0, 0, 0, 0)
print(json.dumps([os.getpid(), os.environ['MALLOC_CONF'], sys.argv[1:], thp]))
sys.exit(23)
''')
    launcher.chmod(0o755)
    bindir = root / "bin"
    bindir.mkdir()
    (bindir / launcher.name).symlink_to(repo / "bin/wheely-shell" / launcher.name)
    for inherited in (None, "", "dirty_decay_ms:8000,background_thread:false"):
        env = dict(os.environ, OMARCHY_PATH=str(upstream.parent), PATH=str(bindir) + ":" + os.environ["PATH"])
        env.pop("MALLOC_CONF", None)
        if inherited is not None:
            env["MALLOC_CONF"] = inherited
        args = ["space here", "$(literal)"]
        child = subprocess.Popen([launcher.name, *args], env=env, stdout=subprocess.PIPE, text=True)
        output, _ = child.communicate(timeout=5)
        pid, setting, received, thp = json.loads(output)
        assert pid == child.pid and child.returncode == 23 and received == args
        assert thp == 3, f"THP should be off except where advised, got {thp}"
        expected = "background_thread:true,dirty_decay_ms:1000"
        assert setting == expected + ("," + inherited if inherited else "")
print("ok: shell launcher preserves upstream supervision, arguments, exit status and allocator overrides,\n"
      "    and disables huge pages except where advised")
