# AGENTS.md

Guidance for anyone (human or AI) changing this repository.

## Project

`yap` is a text-to-speech CLI. It reads text, synthesizes it with a
provider, and plays it on the current macOS output or writes it to a file.
Python 3.9+, standard library only.

```
yap_permit/
  cli.py          argument parsing and the run pipeline
  errors.py       exit codes (public contract) and YapError
  devices.py      default-output detection and the output gate
  coreaudio.py    ctypes fallback for output detection
  player.py       afplay playback with output monitoring and cancellation
  credentials.py  API keys from env or macOS Keychain
  providers/      one module per TTS provider, plus a shared HTTP helper
tests/            unittest, no network, no audio hardware
```

## Commands

```sh
python3 -m unittest discover -s tests -t .   # run tests
python3 -m yap_permit --dry-run "hello"       # run without installing
```

## Rules

- No third-party runtime dependencies without a strong reason.
- Exit codes in `errors.py` are a public contract; document any change in
  the README.
- Private mode must fail closed. Any failure to confirm the output is
  allowed means refusing or stopping playback, never falling back to
  speakers. Gate before reading credentials or calling a provider.
- Never accept API keys as arguments. Never print keys, Keychain
  selectors in errors, or provider error bodies.
- Never switch the user's audio output automatically.
- Inject subprocess/HTTP/device dependencies so tests run without macOS,
  network, or audio hardware. Add a test with every behavior change.
- Keep modules small (aim for under ~200 lines) and focused.
- Changes that affect real audio routing need a manual check on a Mac with
  the relevant device; say so in the pull request.
