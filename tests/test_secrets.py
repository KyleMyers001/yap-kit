"""No API key may appear in any error text, whatever fails."""

import io
import unittest
from unittest import mock

from yap_kit import cli
from yap_kit.devices import Output

KEY = "sk-test-SUPERSECRET-123"


class FailingConn:
    def __init__(self, result):
        self.result = result

    def request(self, *a, **k):
        pass

    def getresponse(self):
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result

    def close(self):
        pass


class ErrorResponse(io.BytesIO):
    status = 401

    def getheader(self, name, default=None):
        return "application/json"


def run_cli(argv, exc):
    err = io.StringIO()
    env = {"OPENAI_API_KEY": KEY, "ELEVENLABS_API_KEY": KEY,
           "ELEVENLABS_VOICE_ID": "v1"}
    conn = FailingConn(exc)
    with mock.patch.dict("os.environ", env, clear=True), \
            mock.patch("sys.stderr", err), \
            mock.patch("sys.stdout", io.StringIO()), \
            mock.patch("yap_kit.providers.http._connection",
                       return_value=(conn, "/")), \
            mock.patch("yap_kit.devices.default_output",
                       return_value=Output("AirPods", "blue")):
        code = cli.main(argv)
    return code, err.getvalue()


class NoKeyInErrorsTest(unittest.TestCase):
    def test_provider_failures_never_echo_key(self):
        failures = [
            ErrorResponse(f"invalid {KEY}".encode()),
            ConnectionRefusedError(f"refused {KEY}"),
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
