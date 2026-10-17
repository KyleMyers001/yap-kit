import subprocess
import unittest

from yap_kit.credentials import api_key
from yap_kit.errors import Exit, YapError


def never_run(*a, **k):
    raise AssertionError("Keychain should not be used")


class ApiKeyTest(unittest.TestCase):
    def test_env_key_wins(self):
        self.assertEqual(api_key("X", env={"X_API_KEY": " k "},
                                 run=never_run), "k")

    def test_keychain_lookup(self):
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "secret\n", "")
        env = {"X_KEYCHAIN_SERVICE": "svc", "X_KEYCHAIN_ACCOUNT": "acct"}
        self.assertEqual(api_key("X", env=env, run=run), "secret")
        self.assertIn("svc", calls[0])
        self.assertIn("acct", calls[0])

    def test_missing_config(self):
        with self.assertRaises(YapError) as ctx:
            api_key("X", env={}, run=never_run)
        self.assertEqual(ctx.exception.code, Exit.CREDENTIALS)

    def test_keychain_failure_hides_details(self):
        def run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 44, "", "item svc gone")
        env = {"X_KEYCHAIN_SERVICE": "svc", "X_KEYCHAIN_ACCOUNT": "acct"}
        with self.assertRaises(YapError) as ctx:
            api_key("X", env=env, run=run)
        self.assertEqual(ctx.exception.code, Exit.CREDENTIALS)
        self.assertNotIn("svc", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
