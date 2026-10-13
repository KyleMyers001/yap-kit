"""Play an audio file with macOS `afplay`, watching the output if gated.

When a gate is active, the output is polled during playback and the
player is stopped as soon as the output stops satisfying the gate. This
is polling, not device-bound routing: a fraction of a second can still
play on the new output.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from yap_permit.devices import Output, OutputGate, default_output
from yap_permit.errors import Exit, YapError

POLL_SECONDS = 0.25


def _stop(proc) -> None:
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def play(path: Path, gate: OutputGate, expected_output: Output,
         lookup: Optional[Callable[[], Output]] = None,
         popen=subprocess.Popen, which=shutil.which) -> None:
    """Block until playback finishes. Raises YapError on any failure."""
    lookup = lookup or default_output
    afplay = which("afplay")
    if not afplay:
        raise YapError(Exit.DEPENDENCY, "macOS `afplay` not found")
    proc = popen([afplay, str(path)], stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL)
    try:
        while proc.poll() is None:
            if gate.active and not _still_allowed(gate, expected_output,
                                                  lookup):
                _stop(proc)
                raise YapError(Exit.OUTPUT_CHANGED,
                               "output changed during playback; stopped")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        _stop(proc)
        raise YapError(Exit.CANCELLED, "cancelled") from None
    if proc.returncode != 0:
        raise YapError(Exit.PLAYBACK, "afplay failed")


def _still_allowed(gate: OutputGate, expected: Output, lookup) -> bool:
    try:
        current = lookup()
    except Exception:
        return False  # detection failure is fail-closed
    return current == expected and gate.allows(current)
