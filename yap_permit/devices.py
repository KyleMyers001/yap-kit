"""Default-output detection and the output gate for --private / --device.

Yap Permit never switches outputs. It checks the current macOS default
output and refuses to play when that output is not allowed.
"""

import json
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

from yap_permit import coreaudio
from yap_permit.errors import Exit, YapError

SYSTEM_PROFILER = "/usr/sbin/system_profiler"
PRIVATE_KEYWORDS = ("airpods", "headphones", "beats", "earbuds", "buds")


def _name_from_system_profiler(run=subprocess.run) -> str:
    result = run([SYSTEM_PROFILER, "SPAudioDataType", "-json",
                  "-detailLevel", "mini"], capture_output=True, timeout=3)
    if result.returncode != 0:
        raise OSError("system_profiler failed")
    data = json.loads(result.stdout)
    for top in data.get("SPAudioDataType", []):
        for dev in top.get("_items", []):
            if (dev.get("coreaudio_default_audio_output_device")
                    == "spaudio_yes" and dev.get("_name")):
                return dev["_name"]
    raise OSError("no default output reported")


def default_output_name() -> str:
    """Fast system_profiler path, then CoreAudio. Raises OSError."""
    try:
        return _name_from_system_profiler()
    except (OSError, ValueError, AttributeError, TypeError,
            subprocess.TimeoutExpired):
        return coreaudio.default_output_name()


def is_private_output(name: str) -> bool:
    lowered = name.lower()
    return any(word in lowered for word in PRIVATE_KEYWORDS)


@dataclass(frozen=True)
class OutputGate:
    """What the current output must satisfy. Empty gate allows anything."""

    private: bool = False
    device: Optional[str] = None

    @property
    def active(self) -> bool:
        return self.private or bool(self.device)

    def allows(self, name: str) -> bool:
        if self.private and not is_private_output(name):
            return False
        if self.device and self.device.lower() not in name.lower():
            return False
        return True

    def check(self, lookup: Optional[Callable[[], str]] = None) -> str:
        """Return the allowed output name, or raise (fail closed)."""
        try:
            name = (lookup or default_output_name)()
        except Exception:
            raise YapError(Exit.OUTPUT_REFUSED,
                           "could not detect the audio output") from None
        if not self.allows(name):
            want = "private headphones" if self.private else self.device
            raise YapError(Exit.OUTPUT_REFUSED,
                           f"current output '{name}' is not {want}; "
                           "switch outputs and retry")
        return name
