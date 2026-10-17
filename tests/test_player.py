import unittest
from pathlib import Path
from unittest import mock

from yap_kit import player
from yap_kit.devices import Output, OutputGate
from yap_kit.errors import Exit, YapError


class FakeProc:
    def __init__(self, polls_until_done=3, returncode=0):
        self.remaining = polls_until_done
        self.returncode = None
        self.final = returncode
        self.terminated = False

    def poll(self):
        if self.terminated:
            self.returncode = -15
        elif self.remaining <= 0:
            self.returncode = self.final
        else:
            self.remaining -= 1
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.poll()


AIRPODS = Output("AirPods", "blue")


def run_play(proc, gate, lookup=lambda: AIRPODS):
    with mock.patch.object(player, "POLL_SECONDS", 0):
        player.play(Path("a.mp3"), gate, AIRPODS, lookup=lookup,
                    popen=lambda *a, **k: proc,
                    which=lambda _: "/usr/bin/afplay")


class PlayTest(unittest.TestCase):
    def test_completes(self):
        run_play(FakeProc(), OutputGate(private=True))

    def test_stops_when_output_changes(self):
        proc = FakeProc(polls_until_done=100)
        with self.assertRaises(YapError) as ctx:
            run_play(proc, OutputGate(private=True),
                     lookup=lambda: Output("MacBook Speakers", "bltn"))
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_CHANGED)
        self.assertTrue(proc.terminated)

    def test_stops_when_switched_to_other_headphones(self):
        proc = FakeProc(polls_until_done=100)
        with self.assertRaises(YapError) as ctx:
            run_play(proc, OutputGate(private=True),
                     lookup=lambda: Output("Other AirPods", "blue"))
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_CHANGED)

    def test_stops_when_detection_fails(self):
        def broken():
            raise OSError
        proc = FakeProc(polls_until_done=100)
        with self.assertRaises(YapError) as ctx:
            run_play(proc, OutputGate(private=True), lookup=broken)
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_CHANGED)

    def test_ungated_never_checks_output(self):
        def boom():
            raise AssertionError("should not poll")
        run_play(FakeProc(), OutputGate(), lookup=boom)

    def test_player_failure(self):
        with self.assertRaises(YapError) as ctx:
            run_play(FakeProc(returncode=1), OutputGate())
        self.assertEqual(ctx.exception.code, Exit.PLAYBACK)

    def test_cancel_stops_player(self):
        proc = FakeProc(polls_until_done=100)

        def interrupt(_seconds):
            raise KeyboardInterrupt
        with mock.patch.object(player.time, "sleep", side_effect=interrupt):
            with self.assertRaises(YapError) as ctx:
                player.play(Path("a"), OutputGate(), None, popen=lambda *a, **k:
                            proc, which=lambda _: "afplay")
        self.assertEqual(ctx.exception.code, Exit.CANCELLED)
        self.assertTrue(proc.terminated)


if __name__ == "__main__":
    unittest.main()
