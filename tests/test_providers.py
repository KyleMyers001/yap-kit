import io
import subprocess
import unittest
import unittest.mock
import urllib.error
from pathlib import Path

from yap_permit import providers
from yap_permit.errors import Exit, YapError
from yap_permit.providers import Request, elevenlabs, macos_say, openai
from yap_permit.providers.http import post_for_audio


class FakePost:
    def __init__(self):
        self.calls = []

    def __call__(self, name, url, headers, payload, timeout):
        self.calls.append((name, url, headers, payload, timeout))
        return b"ID3audio"


class RegistryTest(unittest.TestCase):
    def test_unknown_provider(self):
        with self.assertRaises(YapError) as ctx:
            providers.get("nope")
        self.assertEqual(ctx.exception.code, Exit.USAGE)

    def test_known_providers(self):
        self.assertEqual(set(providers.registry()),
                         {"say", "elevenlabs", "openai"})


class ElevenLabsTest(unittest.TestCase):
    def test_request_shape(self):
        post = FakePost()
        env = {"ELEVENLABS_API_KEY": "k", "ELEVENLABS_VOICE_ID": "v1"}
        audio = elevenlabs.synthesize(Request("hi"), post=post, env=env)
        self.assertEqual((audio.data, audio.extension), (b"ID3audio", "mp3"))
        _, url, headers, payload, _ = post.calls[0]
        self.assertIn("/text-to-speech/v1?", url)
        self.assertEqual(headers["xi-api-key"], "k")
        self.assertEqual(payload, {"text": "hi", "model_id": "eleven_v4"})

    def test_voice_required_before_credentials(self):
        with self.assertRaises(YapError) as ctx:
            elevenlabs.synthesize(Request("hi"), post=FakePost(), env={})
        self.assertEqual(ctx.exception.code, Exit.USAGE)

    def test_rejects_path_like_voice(self):
        env = {"ELEVENLABS_API_KEY": "k"}
        with self.assertRaises(YapError):
            elevenlabs.synthesize(Request("hi", voice="../x"),
                                  post=FakePost(), env=env)


class OpenAITest(unittest.TestCase):
    def test_request_shape(self):
        post = FakePost()
        openai.synthesize(Request("hi", voice="nova"), post=post,
                          env={"OPENAI_API_KEY": "k"})
        _, url, headers, payload, _ = post.calls[0]
        self.assertEqual(headers["Authorization"], "Bearer k")
        self.assertEqual(payload["voice"], "nova")
        self.assertEqual(payload["input"], "hi")


class MacSayTest(unittest.TestCase):
    def test_writes_aiff_via_say(self):
        def run(cmd, input, **kwargs):
            Path(cmd[cmd.index("-o") + 1]).write_bytes(b"FORM")
            self.assertEqual(input, b"hello")
            self.assertEqual(cmd[1:3], ["-v", "Samantha"])
            return subprocess.CompletedProcess(cmd, 0)
        audio = macos_say.synthesize(Request("hello", voice="Samantha"),
                                     run=run, which=lambda _: "/usr/bin/say")
        self.assertEqual((audio.data, audio.extension), (b"FORM", "aiff"))

    def test_missing_say(self):
        with self.assertRaises(YapError) as ctx:
            macos_say.synthesize(Request("x"), which=lambda _: None)
        self.assertEqual(ctx.exception.code, Exit.DEPENDENCY)


class FakeResponse(io.BytesIO):
    def __init__(self, data, mime, status=200):
        super().__init__(data)
        self.status = status
        self.mime = mime

    def getheader(self, name, default=None):
        return self.mime

    def read1(self, size=-1):
        return self.read(min(size, 4))


class FakeConn:
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


class HttpTest(unittest.TestCase):
    def call(self, result, timeout=5):
        return post_for_audio("P", "https://x", {}, {}, timeout,
                              connect=lambda u, t: (FakeConn(result), "/"))

    def test_returns_audio(self):
        self.assertEqual(self.call(FakeResponse(b"abcdefg", "audio/mpeg")),
                         b"abcdefg")

    def test_rejects_non_audio(self):
        with self.assertRaises(YapError) as ctx:
            self.call(FakeResponse(b"{}", "application/json"))
        self.assertEqual(ctx.exception.code, Exit.PROVIDER)

    def test_response_size_cap(self):
        from yap_permit.providers import http
        with unittest.mock.patch.object(http, "MAX_AUDIO_BYTES", 10):
            with self.assertRaises(YapError) as ctx:
                self.call(FakeResponse(b"x" * 11, "audio/mpeg"))
        self.assertIn("too large", str(ctx.exception))

    def test_http_error_hides_body(self):
        with self.assertRaises(YapError) as ctx:
            self.call(FakeResponse(b"secret detail", "text/plain", 401))
        self.assertEqual(str(ctx.exception), "P returned HTTP 401")

    def test_socket_timeout_says_timed_out(self):
        import socket
        with self.assertRaises(YapError) as ctx:
            self.call(socket.timeout())
        self.assertEqual(str(ctx.exception), "P request timed out")

    def test_connection_error_says_failed(self):
        with self.assertRaises(YapError) as ctx:
            self.call(ConnectionRefusedError())
        self.assertEqual(str(ctx.exception), "P request failed")


if __name__ == "__main__":
    unittest.main()
