"""Bring-your-own-key lookup: environment variable or macOS Keychain.

Keys are never accepted as command-line arguments and never printed.
"""

import os
import subprocess

from yap_kit.errors import Exit, YapError


def api_key(prefix: str, env=os.environ, run=subprocess.run) -> str:
    """Read <PREFIX>_API_KEY, else <PREFIX>_KEYCHAIN_SERVICE/_ACCOUNT."""
    key = env.get(f"{prefix}_API_KEY", "").strip()
    if key:
        return key
    service = env.get(f"{prefix}_KEYCHAIN_SERVICE", "").strip()
    account = env.get(f"{prefix}_KEYCHAIN_ACCOUNT", "").strip()
    if not (service and account):
        raise YapError(Exit.CREDENTIALS,
                       f"set {prefix}_API_KEY or {prefix}_KEYCHAIN_SERVICE "
                       f"and {prefix}_KEYCHAIN_ACCOUNT")
    try:
        result = run(["/usr/bin/security", "find-generic-password",
                      "-s", service, "-a", account, "-w"],
                     capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        raise YapError(Exit.CREDENTIALS, "Keychain lookup failed") from None
    key = result.stdout.strip() if result.returncode == 0 else ""
    if not key:
        raise YapError(Exit.CREDENTIALS, "Keychain lookup failed")
    return key
