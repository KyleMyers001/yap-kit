"""POST JSON, get audio. Refuses redirects so keys are never forwarded."""

import json
import time
import urllib.error
import urllib.request

from yap_permit.errors import Exit, YapError

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # ~25 min of 128 kbps MP3
CHUNK = 64 * 1024


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused",
                                     headers, fp)


def post_for_audio(provider, url, headers, payload, timeout,
                   opener=None) -> bytes:
    """POST and return the audio body.

    `timeout` bounds each socket wait and the whole request in total, so a
    trickling server cannot hold the CLI open indefinitely.
    """
    deadline = time.monotonic() + timeout
    opener = opener or urllib.request.build_opener(_NoRedirects())
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **headers})
    try:
        with opener.open(request, timeout=timeout) as resp:
            mime = resp.headers.get("Content-Type", "")
            data = _read_capped(provider, resp, deadline)
    except urllib.error.HTTPError as exc:
        exc.close()
        # Never surface provider error bodies; they can echo request data.
        raise YapError(Exit.PROVIDER,
                       f"{provider} returned HTTP {exc.code}") from None
    except (urllib.error.URLError, OSError):
        raise YapError(Exit.PROVIDER, f"{provider} request failed") from None
    if not mime.lower().startswith("audio/") or not data:
        raise YapError(Exit.PROVIDER, f"{provider} returned no audio")
    return data


def _read_capped(provider, resp, deadline) -> bytes:
    data = bytearray()
    while True:
        if time.monotonic() > deadline:
            raise YapError(Exit.PROVIDER, f"{provider} request timed out")
        chunk = resp.read(CHUNK)
        if not chunk:
            return bytes(data)
        data += chunk
        if len(data) > MAX_AUDIO_BYTES:
            raise YapError(Exit.PROVIDER, f"{provider} response too large")
