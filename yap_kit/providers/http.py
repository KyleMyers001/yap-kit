"""POST JSON, get audio, within one total deadline.

Uses http.client directly: redirects are never followed (so keys are
never forwarded), and a watchdog closes the socket at the deadline, so
slow connects, dripping headers, and trickling bodies are all bounded.
"""

import http.client
import json
import socket
import threading
import time
import urllib.parse

from yap_kit.errors import Exit, YapError

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # ~25 min of 128 kbps MP3
CHUNK = 64 * 1024


class _Deadline:
    def __init__(self, seconds: float) -> None:
        self.end = time.monotonic() + seconds

    def remaining(self) -> float:
        left = self.end - time.monotonic()
        if left <= 0:
            raise socket.timeout()
        return left


def _connection(url: str, timeout: float):
    parts = urllib.parse.urlsplit(url)
    cls = {"https": http.client.HTTPSConnection,
           "http": http.client.HTTPConnection}.get(parts.scheme)
    if cls is None or not parts.hostname:
        raise ValueError("unsupported URL")
    path = parts.path + (f"?{parts.query}" if parts.query else "")
    return cls(parts.hostname, parts.port, timeout=timeout), path


def post_for_audio(provider, url, headers, payload, timeout,
                   connect=None) -> bytes:
    """POST and return the audio body; `timeout` bounds the whole call."""
    deadline = _Deadline(timeout)
    conn, path = (connect or _connection)(url, timeout)
    # Closing the socket from another thread unblocks any pending read.
    aborted = threading.Event()
    watchdog = threading.Timer(timeout, _abort, (conn, aborted))
    watchdog.daemon = True
    watchdog.start()
    try:
        body = json.dumps(payload).encode("utf-8")
        conn.request("POST", path, body=body, headers={
            "Content-Type": "application/json", **headers})
        resp = conn.getresponse()
        if resp.status != 200:
            # Never surface provider error bodies; they can echo the key.
            raise YapError(Exit.PROVIDER,
                           f"{provider} returned HTTP {resp.status}")
        mime = resp.getheader("Content-Type", "")
        data = _read_capped(provider, resp, deadline, aborted)
    except (socket.timeout, TimeoutError):
        raise YapError(Exit.PROVIDER, f"{provider} request timed out") \
            from None
    except (OSError, http.client.HTTPException, ValueError):
        if time.monotonic() >= deadline.end:
            raise YapError(Exit.PROVIDER, f"{provider} request timed out") \
                from None
        raise YapError(Exit.PROVIDER, f"{provider} request failed") from None
    finally:
        watchdog.cancel()
        conn.close()
    if not mime.lower().startswith("audio/") or not data:
        raise YapError(Exit.PROVIDER, f"{provider} returned no audio")
    return data


def _abort(conn, aborted: threading.Event) -> None:
    aborted.set()  # set first: a reader woken by shutdown must see it
    sock = getattr(conn, "sock", None)
    if sock is not None:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def _read_capped(provider, resp, deadline, aborted) -> bytes:
    """Read the whole body; a cut-off or short body is never success."""
    data = bytearray()
    while True:
        deadline.remaining()  # raises once time is up
        chunk = resp.read1(CHUNK)
        if not chunk:
            # The watchdog's shutdown looks like EOF to the reader.
            if aborted.is_set() or time.monotonic() >= deadline.end:
                raise socket.timeout()
            remaining = getattr(resp, "length", None)
            if isinstance(remaining, int) and remaining > 0:
                raise http.client.IncompleteRead(bytes(data), remaining)
            return bytes(data)
        data += chunk
        if len(data) > MAX_AUDIO_BYTES:
            raise YapError(Exit.PROVIDER, f"{provider} response too large")
