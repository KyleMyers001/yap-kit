"""Default-output detection and the output gate for --private / --device.

Yap Permit never switches outputs. It checks the current macOS default
output and refuses to play when that output is not allowed.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from yap_permit import coreaudio
from yap_permit.errors import Exit, YapError

BLUETOOTH_TRANSPORTS = ("blue", "blea")   # Classic and LE
BUILTIN_TRANSPORT = "bltn"
HEADPHONE_DATA_SOURCE = "hdpn"            # wired headphones on the jack
PRIVATE_NAME_WORDS = ("airpods", "headphones", "earbuds", "buds")
SPEAKER_NAME_WORDS = ("speaker", "pill")


@dataclass(frozen=True)
class Output:
    name: str
    transport: str = ""             # CoreAudio FourCC, e.g. "blue"
    data_source: Optional[str] = None


def default_output() -> Output:
    """Read the default output from CoreAudio. Raises OSError."""
    return Output(*coreaudio.default_output())


def is_private_output(output: Output) -> bool:
    """True only when the device type is verified as personal listening.

    Wired: the built-in jack reports the headphone data source.
    Bluetooth: transport is Bluetooth AND the name is on a strict allowlist
    with no speaker words (Bluetooth speakers share the transport).
    Anything unverified is refused.
    """
    if (output.transport == BUILTIN_TRANSPORT
            and output.data_source == HEADPHONE_DATA_SOURCE):
        return True
    if output.transport not in BLUETOOTH_TRANSPORTS:
        return False
    name = output.name.lower()
    if any(word in name for word in SPEAKER_NAME_WORDS):
        return False
    return any(word in name for word in PRIVATE_NAME_WORDS)


@dataclass(frozen=True)
class OutputGate:
    """What the current output must satisfy. Empty gate allows anything."""

    private: bool = False
    device: Optional[str] = None

    @property
    def active(self) -> bool:
        return self.private or bool(self.device)

    def allows(self, output: Output) -> bool:
        if self.private and not is_private_output(output):
            return False
        if self.device and self.device.lower() not in output.name.lower():
            return False
        return True

    def check(self, lookup: Optional[Callable[[], Output]] = None) -> Output:
        """Return the allowed output, or raise (fail closed)."""
        try:
            output = (lookup or default_output)()
        except Exception:
            raise YapError(Exit.OUTPUT_REFUSED,
                           "could not detect the audio output") from None
        if not self.allows(output):
            want = "private headphones" if self.private else self.device
            raise YapError(Exit.OUTPUT_REFUSED,
                           f"current output '{output.name}' is not {want}; "
                           "switch outputs and retry")
        return output
