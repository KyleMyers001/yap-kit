"""Real sockets: --timeout bounds hung and slow-drip servers in total."""

import http.server
import threading
import time
import unittest

from yap_permit.errors import Exit, YapError
from yap_permit.providers.http import post_for_audio


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        mode = self.path.strip("/")
        try:
            if mode == "hang":
                time.sleep(5)
                return
            if mode == "drip-headers":
                self.wfile.write(b"HTTP/1.1 200 OK\r\n")
                for _ in range(20):
                    self.wfile.write(b"X-Slow: 1\r\n")
                    self.wfile.flush()
                    time.sleep(0.2)
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            for _ in range(20):  # 1 byte every 0.2 s for ~4 s
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(0.2)
        except OSError:
            pass


class SlowServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                                     Handler)
        cls.server.daemon_threads = True
        threading.Thread(target=cls.server.serve_forever,
                         daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def assert_times_out(self, mode):
        start = time.monotonic()
        with self.assertRaises(YapError) as ctx:
            post_for_audio("P", f"{self.base}/{mode}", {}, {}, 1)
        elapsed = time.monotonic() - start
        self.assertEqual(ctx.exception.code, Exit.PROVIDER)
        self.assertEqual(str(ctx.exception), "P request timed out")
        self.assertLess(elapsed, 2.0)

    def test_body_drip_bounded(self):
        self.assert_times_out("drip")

    def test_header_drip_bounded(self):
        self.assert_times_out("drip-headers")

    def test_hung_server_bounded(self):
        self.assert_times_out("hang")


if __name__ == "__main__":
    unittest.main()
