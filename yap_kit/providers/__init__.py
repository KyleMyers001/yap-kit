"""Provider registry. Each provider turns text into audio bytes."""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from yap_kit.errors import Exit, YapError


@dataclass(frozen=True)
class Audio:
    data: bytes
    extension: str  # "mp3", "aiff", ...


@dataclass(frozen=True)
class Request:
    text: str
    voice: Optional[str] = None
    model: Optional[str] = None
    timeout: float = 60


Synthesize = Callable[[Request], Audio]


def registry() -> Dict[str, Synthesize]:
    # Imported lazily so one provider's imports never break another.
    from yap_kit.providers import elevenlabs, macos_say, openai
    return {
        "say": macos_say.synthesize,
        "elevenlabs": elevenlabs.synthesize,
        "openai": openai.synthesize,
    }


def get(name: str) -> Synthesize:
    providers = registry()
    if name not in providers:
        raise YapError(Exit.USAGE, f"unknown provider '{name}'; choose "
                       f"from {', '.join(sorted(providers))}")
    return providers[name]
