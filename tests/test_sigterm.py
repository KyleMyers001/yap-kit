"""End to end: SIGTERM stops the player and exits 130.

Uses fake `say` and `afplay` scripts on PATH so it runs on any POSIX host.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAKE_SAY = """#!/bin/sh
while [ $# -gt 0 ]; do
  if [ "$1" = "-o" ]; then shift; printf FORM > "$1"; fi
  shift
done
cat > /dev/null
"""
FAKE_AFPLAY = """#!/bin/sh
echo $$ > "$YAP_TEST_PIDFILE"
exec sleep 30
"""


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A zombie still answers kill(0); check its state where possible.
    stat = Path(f"/proc/{pid}/stat")
    return not (stat.exists() and stat.read_text().split()[2] == "Z")


@unittest.skipIf(os.name != "posix", "POSIX only")
class SigtermTest(unittest.TestCase):
    def test_sigterm_exits_130_and_stops_player(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp)
            for name, body in (("say", FAKE_SAY), ("afplay", FAKE_AFPLAY)):
                path = bin_dir / name
                path.write_text(body)
                path.chmod(0o755)
            pidfile = bin_dir / "afplay.pid"
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                   "YAP_TEST_PIDFILE": str(pidfile),
                   "PYTHONPATH": str(ROOT)}
            env.pop("YAP_PROVIDER", None)
            proc = subprocess.Popen(
                [sys.executable, "-m", "yap_kit", "hello"], env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            deadline = time.monotonic() + 10
            while not (pidfile.exists() and pidfile.read_text().strip()):
                self.assertLess(time.monotonic(), deadline, "player never ran")
                time.sleep(0.05)
            player_pid = int(pidfile.read_text())
            proc.send_signal(signal.SIGTERM)
            _, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 130, err)
            time.sleep(0.2)
            self.assertFalse(alive(player_pid), "player still running")


if __name__ == "__main__":
    unittest.main()
