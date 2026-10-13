import unittest
from unittest import mock

from yap_permit import devices
from yap_permit.devices import Output, OutputGate, is_private_output
from yap_permit.errors import Exit, YapError

BT = "blue"
BUILTIN = "bltn"


class PrivateOutputTest(unittest.TestCase):
    def test_bluetooth_airpods_allowed(self):
        self.assertTrue(is_private_output(Output("Kyle's AirPods Pro", BT)))
        self.assertTrue(is_private_output(Output("WH-1000 Headphones",
                                                 "blea")))

    def test_wired_headphone_jack_allowed(self):
        self.assertTrue(is_private_output(
            Output("External Headphones", BUILTIN, "hdpn")))

    def test_beats_pill_refused(self):
        self.assertFalse(is_private_output(Output("Beats Pill", BT)))

    def test_beats_brand_alone_refused(self):
        self.assertFalse(is_private_output(Output("Beats Studio", BT)))

    def test_speaker_word_refused_even_with_headphone_word(self):
        self.assertFalse(is_private_output(
            Output("Headphones Speaker", BT)))

    def test_headphone_name_on_non_bluetooth_refused(self):
        # A renamed AirPlay/USB/built-in speaker must not pass on name.
        for transport in ("airp", "usb ", BUILTIN, ""):
            self.assertFalse(is_private_output(
                Output("AirPods", transport)), transport)

    def test_builtin_speakers_refused(self):
        self.assertFalse(is_private_output(
            Output("MacBook Pro Speakers", BUILTIN, "ispk")))


class DefaultOutputTest(unittest.TestCase):
    def test_wraps_coreaudio(self):
        with mock.patch.object(devices.coreaudio, "default_output",
                               return_value=("AirPods", BT, None)):
            self.assertEqual(devices.default_output(), Output("AirPods", BT))


class GateTest(unittest.TestCase):
    def test_device_substring_case_insensitive(self):
        gate = OutputGate(device="studio")
        self.assertTrue(gate.allows(Output("Studio Display Speakers")))
        self.assertFalse(gate.allows(Output("AirPods", BT)))

    def test_private_and_device_both_required(self):
        gate = OutputGate(private=True, device="max")
        self.assertTrue(gate.allows(Output("AirPods Max", BT)))
        self.assertFalse(gate.allows(Output("AirPods Pro", BT)))

    def test_check_refuses_beats_pill(self):
        with self.assertRaises(YapError) as ctx:
            OutputGate(private=True).check(lambda: Output("Beats Pill", BT))
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_REFUSED)

    def test_check_fails_closed_when_detection_fails(self):
        def broken():
            raise OSError("no CoreAudio")
        with self.assertRaises(YapError) as ctx:
            OutputGate(private=True).check(broken)
        self.assertEqual(ctx.exception.code, Exit.OUTPUT_REFUSED)

    def test_inactive_gate(self):
        self.assertFalse(OutputGate().active)
        self.assertTrue(OutputGate().allows(Output("anything")))


if __name__ == "__main__":
    unittest.main()
