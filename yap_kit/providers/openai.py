"""OpenAI cloud synthesis (bring your own key)."""

import os

from yap_kit import credentials
from yap_kit.providers import Audio, Request
from yap_kit.providers.http import post_for_audio

URL = "https://api.openai.com/v1/audio/speech"
DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "alloy"


def synthesize(req: Request, post=post_for_audio,
               env=os.environ) -> Audio:
    key = credentials.api_key("OPENAI", env=env)
    payload = {
        "model": req.model or DEFAULT_MODEL,
        "voice": req.voice or env.get("OPENAI_VOICE") or DEFAULT_VOICE,
        "input": req.text,
        "response_format": "mp3",
    }
    data = post("OpenAI", URL, {"Authorization": f"Bearer {key}"},
                payload, req.timeout)
    return Audio(data, "mp3")
