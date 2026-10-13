"""POST JSON, get audio. Refuses redirects so keys are never forwarded."""

import json
import urllib.error
import urllib.request

from yap_permit.errors import Exit, YapError


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused",
                                     headers, fp)


def post_for_audio(provider, url, headers, payload, timeout,
                   opener=None) -> bytes:
    opener = opener or urllib.request.build_opener(_NoRedirects())
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **headers})
    try:
        with opener.open(request, timeout=timeout) as resp:
            mime = resp.headers.get("Content-Type", "")
            data = resp.read()
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
