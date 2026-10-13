import io
import unittest
from unittest import mock

from yap_permit import cli
from yap_permit.errors import Exit
from yap_permit.providers import Audio


def main_with(argv, stdin="", output="AirPods Pro", synth=None):
    synth = synth or mock.Mock(return_value=Audio(b"ID3", "mp3"))
    err = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), \
            mock.patch("sys.stderr", err), \
            mock.patch("yap_permit.devices.default_output_name",
                       return_value=output), \
            mock.patch("yap_permit.providers.get", return_value=synth), \
            mock.patch.object(cli, "play") as play:
        code = cli.main(argv)
    return code, synth, play, err.getvalue()


class CliTest(unittest.TestCase):
    def test_reads_stdin_and_plays(self):
        code, synth, play, _ = main_with([], stdin="hello\n")
        self.assertEqual(code, Exit.OK)
        self.assertEqual(synth.call_args[0][0].text, "hello")
        play.assert_called_once()

    def test_private_refuses_speakers_before_synthesis(self):
        code, synth, play, err = main_with(
            ["--private", "hi"], output="MacBook Pro Speakers")
        self.assertEqual(code, Exit.OUTPUT_REFUSED)
        synth.assert_not_called()
        play.assert_not_called()
        self.assertIn("not private headphones", err)

    def test_private_plays_on_airpods(self):
        code, _, play, _ = main_with(["--private", "hi"])
        self.assertEqual(code, Exit.OK)
        self.assertEqual(play.call_args[0][2], "AirPods Pro")

    def test_out_writes_file_without_playing(self):
        import tempfile, os
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
