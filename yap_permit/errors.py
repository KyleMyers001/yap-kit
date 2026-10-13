"""Exit codes and the single error type the CLI turns into them."""

from enum import IntEnum


class Exit(IntEnum):
    OK = 0
    USAGE = 1             # bad arguments or input
    OUTPUT_REFUSED = 2    # current output fails --private / --device
    OUTPUT_CHANGED = 3    # output changed or vanished during playback
    CREDENTIALS = 4       # API key missing or unreadable
    PROVIDER = 5          # synthesis failed
    DEPENDENCY = 6        # required binary or platform missing
    PLAYBACK = 7          # player failed
    CANCELLED = 130       # SIGINT / SIGTERM


class YapError(Exception):
    """An expected failure with a fixed exit code and a safe message."""

    def __init__(self, code: Exit, message: str) -> None:
        super().__init__(message)
        self.code = code
