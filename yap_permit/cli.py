"""Command-line entry point: parse, gate, synthesize, then play or write."""

import argparse
import os
import signal
import sys
import tempfile
from pathlib import Path
from typing import Optional

from yap_permit import __version__, providers
from yap_permit.devices import OutputGate
from yap_permit.errors import Exit, YapError
from yap_permit.player import play

MAX_CHARS = 5000


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse exits 2 by default, which is our "output refused" code.
        self.print_usage(sys.stderr)
        self.exit(Exit.USAGE, f"yap: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(
        prog="yap", description="Speak text through a chosen audio output.")
    p.add_argument("text", nargs="?", default="-",
                   help='text to speak, or "-" (default) to read stdin')
    p.add_argument("-p", "--provider", default=os.environ.get(
        "YAP_PROVIDER", "say"), help="say (default), elevenlabs, openai")
    p.add_argument("-v", "--voice", help="provider voice name or ID")
    p.add_argument("-m", "--model", help="provider model ID")
    p.add_argument("--private", action="store_true",
                   help="play only through AirPods/headphones; else refuse")
    p.add_argument("-d", "--device",
                   help="require the current output name to contain this")
    p.add_argument("-o", "--out", help='write audio to a file ("-" = stdout)'
                   " instead of playing")
    p.add_argument("--timeout", type=float, default=60,
                   help="provider timeout in seconds (default 60)")
    p.add_argument("--dry-run", action="store_true",
                   help="validate input and output gate only")
    p.add_argument("--version", action="version", version=__version__)
    return p


def read_text(arg: str) -> str:
    text = (sys.stdin.read() if arg == "-" else arg).strip()
    if not text:
        raise YapError(Exit.USAGE, "no text to speak")
    if len(text) > MAX_CHARS:
        raise YapError(Exit.USAGE, f"text exceeds {MAX_CHARS} characters")
    return text


def run(args) -> None:
    if args.timeout <= 0:
        raise YapError(Exit.USAGE, "--timeout must be positive")
    if args.out and (args.private or args.device):
        raise YapError(Exit.USAGE, "--out cannot be combined with "
                       "--private or --device")
    synthesize = providers.get(args.provider)
    text = read_text(args.text)
    gate = OutputGate(private=args.private, device=args.device)
    # Gate before credentials or network so a refused output costs nothing.
    output = gate.check() if gate.active else ""
    if args.dry_run:
        print(f"ok: provider={args.provider} chars={len(text)}"
              + (f" output={output!r}" if output else ""), file=sys.stderr)
        return
    audio = synthesize(providers.Request(text, args.voice, args.model,
                                         args.timeout))
    if args.out:
        _write(audio.data, args.out)
        return
    with tempfile.TemporaryDirectory(prefix="yap-") as tmp:
        path = Path(tmp) / f"speech.{audio.extension}"
        path.write_bytes(audio.data)
        if gate.active:
            output = gate.check()  # synthesis can be slow; recheck
        play(path, gate, output)


def _write(data: bytes, out: str) -> None:
    if out == "-":
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    else:
        Path(out).write_bytes(data)


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        run(args)
    except YapError as exc:
        print(f"yap: {exc}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("yap: cancelled", file=sys.stderr)
        return Exit.CANCELLED
    return Exit.OK
