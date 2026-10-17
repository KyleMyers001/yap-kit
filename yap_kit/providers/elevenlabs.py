"""ElevenLabs cloud synthesis (bring your own key)."""

import os
import re
import urllib.parse

from yap_kit import credentials
from yap_kit.errors import Exit, YapError
from yap_kit.providers import Audio, Request
from yap_kit.providers.http import post_for_audio

URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
DEFAULT_MODEL = "eleven_v4"
_ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def synthesize(req: Request, post=post_for_audio,
               env=os.environ) -> Audio:
    voice = req.voice or env.get("ELEVENLABS_VOICE_ID", "")
    model = req.model or DEFAULT_MODEL
    if not _ID.fullmatch(voice):
        raise YapError(Exit.USAGE,
                       "set a valid --voice or ELEVENLABS_VOICE_ID")
    if not _ID.fullmatch(model):
        raise YapError(Exit.USAGE, "invalid --model")
    key = credentials.api_key("ELEVENLABS", env=env)
    url = URL.format(voice=urllib.parse.quote(voice, safe=""))
    url += "?output_format=mp3_44100_128"
    data = post("ElevenLabs", url,
                {"xi-api-key": key, "Accept": "audio/mpeg"},
                {"text": req.text, "model_id": model}, req.timeout)
    return Audio(data, "mp3")
