import json
import subprocess
import unittest

from yap_permit import devices
from yap_permit.devices import OutputGate
from yap_permit.errors import Exit, YapError


def profiler_result(items, code=0):
    out = json.dumps({"SPAudioDataType": [{"_items": items}]}).encode()
    return subprocess.CompletedProcess([], code, out, b"")


class SystemProfilerTest(unittest.TestCase):
    def test_returns_default_output(self):
        items = [{"_name": "Speakers"},
                 {"_name": "Kyle's AirPods Pro",
                  "coreaudio_default_audio_output_device": "spaudio_yes"}]
        name = devices._name_from_system_profiler(
            run=lambda *a, **k: profiler_result(items))
        self.assertEqual(name, "Kyle's AirPods Pro")

    def test_no_default_raises(self):
        with self.assertRaises(OSError):
            devices._name_from_system_profiler(
                run=lambda *a, **k: profiler_result([{"_name": "X"}]))

    def test_nonzero_exit_raises(self):
        with self.assertRaises(OSError):
            devices._name_from_system_profiler(
                run=lambda *a, **k: profiler_result([], code=1))


class GateTest(unittest.TestCase):
    def test_private_allows_headphones_only(self):
        gate = OutputGate(private=True)
        self.assertTrue(gate.allows("AirPods Max"))
        self.assertTrue(gate.allows("External Headphones"))
        self.assertFalse(gate.allows("MacBook Pro Speakers"))
        self.assertFalse(gate.allows("Living Room"))

    def test_device_substring_case_insensitive(self):
        gate = OutputGate(device="studio")
        self.assertTrue(gate.allows("Studio Display Speakers"))
        self.assertFalse(gate.allows("AirPods"))

    def test_private_and_device_both_required(self):
        gate = OutputGate(private=True, device="max")
        self.assertTrue(gate.allows("AirPods Max"))
        self.assertFalse(gate.allows("AirPods Pro"))

    def test_check_refuses_speakers(self):
        with self.assertRaises(YapError) as ctx:
            OutputGate(private=True).check(lambda: "MacBook Speakers")
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_REFUSED)

    def test_check_fails_closed_when_detection_fails(self):
        def broken():
            raise OSError("no CoreAudio")
        with self.assertRaises(YapError) as ctx:
            OutputGate(private=True).check(broken)
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_REFUSED)

    def test_inactive_gate(self):
        self.assertFalse(OutputGate().active)
        self.assertTrue(OutputGate().allows("anything"))


if __name__ == "__main__":
    unittest.main()
