"""Local, offline synthesis with macOS `say`. No text leaves the machine."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from yap_permit.errors import Exit, YapError
from yap_permit.providers import Audio, Request


def synthesize(req: Request, run=subprocess.run,
               which=shutil.which) -> Audio:
    say = which("say")
    if not say:
        raise YapError(Exit.DEPENDENCY, "macOS `say` not found")
    with tempfile.TemporaryDirectory(prefix="yap-") as tmp:
        out = Path(tmp) / "speech.aiff"
        cmd = [say, "-o", str(out), "-f", "-"]
        if req.voice:
            cmd[1:1] = ["-v", req.voice]
        try:
            result = run(cmd, input=req.text.encode("utf-8"),
                         capture_output=True, timeout=req.timeout)
        except subprocess.TimeoutExpired:
            raise YapError(Exit.PROVIDER, "say timed out") from None
        if result.returncode != 0 or not out.exists():
            raise YapError(Exit.PROVIDER, "say failed")
        return Audio(out.read_bytes(), "aiff")
