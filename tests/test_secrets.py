"""No API key may appear in any error text, whatever fails."""

import io
import urllib.error
import unittest
from unittest import mock

from yap_permit import cli
from yap_permit.devices import Output

KEY = "sk-test-SUPERSECRET-123"


class FailingOpener:
    def __init__(self, exc):
        self.exc = exc

    def open(self, request, timeout):
        raise self.exc


def run_cli(argv, exc):
    err = io.StringIO()
    env = {"OPENAI_API_KEY": KEY, "ELEVENLABS_API_KEY": KEY,
           "ELEVENLABS_VOICE_ID": "v1"}
    opener = FailingOpener(exc)
    with mock.patch.dict("os.environ", env, clear=True), \
            mock.patch("sys.stderr", err), \
            mock.patch("sys.stdout", io.StringIO()), \
            mock.patch("urllib.request.build_opener", return_value=opener), \
            mock.patch("yap_permit.devices.default_output",
                       return_value=Output("AirPods", "blue")):
        code = cli.main(argv)
    return code, err.getvalue()


class NoKeyInErrorsTest(unittest.TestCase):
    def test_provider_failures_never_echo_key(self):
        failures = [
            urllib.error.HTTPError("https://x", 401, f"bad key {KEY}", {},
                                   io.BytesIO(f"invalid {KEY}".encode())),
            urllib.error.URLError(f"refused {KEY}"),
            OSError(f"socket {KEY}"),
        ]
        for provider in ("openai", "elevenlabs"):
            for exc in failures:
                code, err = run_cli(["-p", provider, "-o", "-", "hi"], exc)
                self.assertEqual(code, 5, (provider, exc))
                self.assertNotIn(KEY, err)
                self.assertNotIn("SUPERSECRET", err)


if __name__ == "__main__":
    unittest.main()
