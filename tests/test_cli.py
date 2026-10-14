import io
import os
import tempfile
import unittest
from unittest import mock

from yap_permit import cli
from yap_permit.errors import Exit
from yap_permit.devices import Output
from yap_permit.providers import Audio

AIRPODS = Output("AirPods Pro", "blue")
SPEAKERS = Output("MacBook Pro Speakers", "bltn", "ispk")


def main_with(argv, stdin="", output=AIRPODS, synth=None):
    synth = synth or mock.Mock(return_value=Audio(b"ID3", "mp3"))
    err = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), \
            mock.patch("sys.stderr", err), \
            mock.patch("yap_permit.devices.default_output",
                       **_lookup(output)), \
            mock.patch("yap_permit.providers.get", return_value=synth), \
            mock.patch.object(cli, "play") as play:
        code = cli.main(argv)
    return code, synth, play, err.getvalue()


def _lookup(output):
    if isinstance(output, list):
        return {"side_effect": output}
    return {"return_value": output}


class CliTest(unittest.TestCase):
    def test_reads_stdin_and_plays(self):
        code, synth, play, _ = main_with([], stdin="hello\n")
        self.assertEqual(code, Exit.OK)
        self.assertEqual(synth.call_args[0][0].text, "hello")
        play.assert_called_once()

    def test_private_refuses_speakers_before_synthesis(self):
        code, synth, play, err = main_with(
            ["--private", "hi"], output=SPEAKERS)
        self.assertEqual(code, Exit.OUTPUT_REFUSED)
        synth.assert_not_called()
        play.assert_not_called()
        self.assertIn("not private headphones", err)

    def test_private_plays_on_airpods(self):
        code, _, play, _ = main_with(["--private", "hi"])
        self.assertEqual(code, Exit.OK)
        self.assertEqual(play.call_args[0][2], AIRPODS)

    def test_prepay_recheck_refuses_after_synthesis(self):
        # AirPods at the first gate, speakers by the time audio is ready.
        code, synth, play, err = main_with(["--private", "hi"],
                                           output=[AIRPODS, SPEAKERS])
        self.assertEqual(code, Exit.OUTPUT_REFUSED)
        synth.assert_called_once()
        play.assert_not_called()

    def test_out_writes_file_without_playing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.mp3")
            code, _, play, _ = main_with(["-o", path, "hi"])
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"ID3")
        self.assertEqual(code, Exit.OK)
        play.assert_not_called()

    def test_out_with_private_is_usage_error(self):
        code, *_ = main_with(["-o", "x.mp3", "--private", "hi"])
        self.assertEqual(code, Exit.USAGE)

    def test_out_missing_dir_refused_before_synthesis(self):
        code, synth, _, err = main_with(["-o", "/nonexistent/dir/x.mp3",
                                         "hi"])
        self.assertEqual(code, Exit.OUTPUT_FILE)
        synth.assert_not_called()
        self.assertNotIn("Traceback", err)

    def test_out_directory_refused_before_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, synth, _, _ = main_with(["-o", tmp, "hi"])
        self.assertEqual(code, Exit.OUTPUT_FILE)
        synth.assert_not_called()

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0,
                     "needs POSIX permissions as non-root")
    def test_existing_writable_file_in_readonly_dir_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.mp3")
            open(path, "wb").close()
            os.chmod(tmp, 0o555)
            try:
                code, _, _, err = main_with(["-o", path, "hi"])
                with open(path, "rb") as f:
                    self.assertEqual(f.read(), b"ID3")
            finally:
                os.chmod(tmp, 0o755)
        self.assertEqual(code, Exit.OK, err)

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0,
                     "needs POSIX permissions as non-root")
    def test_readonly_file_in_writable_dir_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.mp3")
            with open(path, "wb") as f:
                f.write(b"OLD")
            os.chmod(path, 0o444)
            code, synth, _, _ = main_with(["-o", path, "hi"])
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"OLD")
        self.assertEqual(code, Exit.OUTPUT_FILE)
        synth.assert_not_called()

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0,
                     "needs POSIX permissions as non-root")
    def test_new_file_in_readonly_dir_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o555)
            try:
                code, synth, _, _ = main_with(
                    ["-o", os.path.join(tmp, "new.mp3"), "hi"])
            finally:
                os.chmod(tmp, 0o755)
        self.assertEqual(code, Exit.OUTPUT_FILE)
        synth.assert_not_called()

    @unittest.skipUnless(os.path.exists("/dev/stdout")
                         and os.access("/dev/stdout", os.W_OK),
                         "/dev/stdout not available")
    def test_dev_stdout_passes_precheck(self):
        # Pre-check only: the real write would hit the test runner's stdout.
        cli._check_writable("/dev/stdout")

    def test_write_error_is_clean_exit(self):
        with mock.patch.object(cli.Path, "write_bytes",
                               side_effect=PermissionError(13, "denied")):
            code, _, _, err = main_with(["-o", "x.mp3", "hi"])
        self.assertEqual(code, Exit.OUTPUT_FILE)
        self.assertIn("could not write", err)

    def test_broken_pipe_on_stdout_is_quiet(self):
        stdout = mock.Mock()
        stdout.buffer.write.side_effect = BrokenPipeError
        stdout.fileno.return_value = 999  # dup2 is mocked below
        with mock.patch("sys.stdout", stdout), \
                mock.patch.object(cli.os, "dup2"):
            code, _, _, err = main_with(["-o", "-", "hi"])
        self.assertEqual(code, Exit.OK)
        self.assertEqual(err, "")

    def test_invalid_utf8_stdin_rejected(self):
        stdin = mock.Mock()
        stdin.buffer.read.return_value = b"\xff\xfe hi"
        err = io.StringIO()
        with mock.patch("sys.stdin", stdin), mock.patch("sys.stderr", err):
            code = cli.main(["--dry-run"])
        self.assertEqual(code, Exit.USAGE)
        self.assertIn("UTF-8", err.getvalue())

    def test_empty_text(self):
        code, *_ = main_with([], stdin="  \n")
        self.assertEqual(code, Exit.USAGE)

    def test_too_long(self):
        code, *_ = main_with(["x" * 5001])
        self.assertEqual(code, Exit.USAGE)

    def test_bad_flag_is_usage_not_refused(self):
        with mock.patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["--nope"])
        self.assertEqual(ctx.exception.code, Exit.USAGE)

    def test_dry_run_skips_synthesis(self):
        code, synth, play, err = main_with(["--dry-run", "--private", "x"])
        self.assertEqual(code, Exit.OK)
        synth.assert_not_called()
        self.assertIn("AirPods Pro", err)


if __name__ == "__main__":
    unittest.main()
