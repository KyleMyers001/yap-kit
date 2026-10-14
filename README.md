# Yap Permit

An open-source, agent-friendly text-to-speech CLI. `yap` speaks text through
your current audio output, can write audio to a file or stdout, and has a
**private mode** that only plays through AirPods or headphones and refuses
otherwise.

> Status: early MVP. Playback is macOS-only (`afplay`); `--out` works
> anywhere the provider works.

## Install (macOS)

From a clone (editable, good for development):

```sh
git clone https://github.com/KyleMyers001/yap-permit.git
cd yap-permit
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip   # macOS ships pip 21, which can't do editable installs from pyproject.toml
pip install -e .
yap --dry-run "hello"
```

Or install without cloning:

```sh
python3 -m venv ~/.yap-venv && source ~/.yap-venv/bin/activate
pip install --upgrade pip
pip install "git+https://github.com/KyleMyers001/yap-permit"
```

Requires Python 3.9+. No third-party Python packages. Run
`source .venv/bin/activate` in each new terminal, or call
`/path/to/yap-permit/.venv/bin/yap` directly.

## Usage

```sh
yap "Build finished."                       # macOS say, current output
echo "Tests passed" | yap                   # stdin (default when no text)
yap --private "Your 3pm moved to 4."        # headphones only, or exit 2
yap --device "Studio Display" "hello"       # require a named output
yap -p elevenlabs -v VOICE_ID "hello"       # cloud provider
yap -p openai -o hello.mp3 "hello"          # write a file (overwrites), don't play
yap -p openai -o - "hello" | ffplay -i -    # write audio to stdout
yap --dry-run --private "check"             # validate without speaking
```

For multiline text from scripts, use a quoted heredoc so the shell does
not interpolate it:

```sh
yap - <<'EOF_SPEECH'
Text to speak.
EOF_SPEECH
```

## Providers

| Name | Where text goes | Setup |
| --- | --- | --- |
| `say` (default) | Stays on your Mac | none |
| `elevenlabs` | ElevenLabs API | key + voice ID ([setup](#elevenlabs-setup)) |
| `openai` | OpenAI API | key; voice optional ([setup](#openai-setup)) |

Set the default provider with `YAP_PROVIDER` (e.g. `export YAP_PROVIDER=elevenlabs`).
Cloud providers are bring-your-own-key. Keys are never accepted as
arguments and never printed. `yap` reads a key from, in order:

1. `<PROVIDER>_API_KEY` (environment variable), else
2. the macOS Keychain item named by `<PROVIDER>_KEYCHAIN_SERVICE` and
   `<PROVIDER>_KEYCHAIN_ACCOUNT` (recommended).

### ElevenLabs setup

1. Store your API key in the Keychain. This prompts for the key, so it
   never lands in shell history:

   ```sh
   security add-generic-password -s yap-elevenlabs -a "$USER" -w
   ```

   Stricter option: add `-T ''` so **every** read asks for your login
   password (no app is pre-approved):

   ```sh
   security add-generic-password -s yap-elevenlabs -a "$USER" -T '' -w
   ```

   When macOS asks whether `security` may read the item, click **Allow**,
   not **Always Allow**. "Always Allow" lets that tool read the key
   silently from then on.

2. Find a voice ID: in ElevenLabs, open **Voices** (My Voices or the
   Voice Library), choose a voice, and use **Copy voice ID** from its menu
   or details panel. It's a string like `21m00Tcm4TlvDq8ikWAM`.

3. Point `yap` at the key and voice. Add these lines to `~/.zshrc` so
   new terminals have them, then run `source ~/.zshrc`:

   ```sh
   export ELEVENLABS_KEYCHAIN_SERVICE=yap-elevenlabs
   export ELEVENLABS_KEYCHAIN_ACCOUNT="$USER"
   export ELEVENLABS_VOICE_ID=your-voice-id
   ```

   These are lookup names, not secrets. Then test:

   ```sh
   yap -p elevenlabs "Hello from ElevenLabs"
   ```

`--voice` overrides `ELEVENLABS_VOICE_ID`; `--model` overrides the
default model (`eleven_v4`).

### OpenAI setup

1. Store your API key (create one at platform.openai.com → API keys):

   ```sh
   security add-generic-password -s yap-openai -a "$USER" -w
   # stricter, prompts on every read:
   security add-generic-password -s yap-openai -a "$USER" -T '' -w
   ```

   Same rule: click **Allow**, not **Always Allow**.

2. Add to `~/.zshrc`, then `source ~/.zshrc`:

   ```sh
   export OPENAI_KEYCHAIN_SERVICE=yap-openai
   export OPENAI_KEYCHAIN_ACCOUNT="$USER"
   export OPENAI_VOICE=alloy   # optional; e.g. alloy, nova, echo
   ```

3. Test: `yap -p openai "Hello from OpenAI"`

`--voice` overrides `OPENAI_VOICE`; `--model` overrides the default
model (`gpt-4o-mini-tts`).

### Environment-variable fallback

Not on macOS, or no Keychain? Set the key directly:

```sh
read -rs ELEVENLABS_API_KEY && export ELEVENLABS_API_KEY   # paste, Enter
read -rs OPENAI_API_KEY && export OPENAI_API_KEY
```

`read -s` keeps the key out of shell history and off the screen. Avoid
`export KEY=sk-...` typed on the command line (it is saved in history),
and avoid putting raw keys in `~/.zshrc` or other profiles: they are
plain-text files that backups, dotfile repos, and other tools can read.
If you must, use a secrets manager or the Keychain instead. If a key is
exposed, revoke it with the provider.

## Output routing and private mode

`yap` never changes your audio output. It plays on the current macOS
default output. `--private` and `--device` add a gate on that output:

- The output is checked **before** credentials are read or text is sent to
  a provider, again just before playback, and every 0.25 s during playback.
- `--private` checks the device type through CoreAudio. It allows wired
  headphones on the built-in jack, and Bluetooth devices whose name
  contains AirPods, Headphones, Earbuds, or Buds and does not contain
  Speaker or Pill. Everything else, including anything whose type cannot be
  read, is refused (exit 2). Renamed Bluetooth devices are matched by name,
  so give speakers names that don't look like headphones.
- If the output changes or disappears mid-playback, playback stops
  (exit 3). This is polling, not device-bound routing, so a fraction of a
  second may still play on the new output.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Spoken (or written, or dry run passed) |
| 1 | Usage or input error |
| 2 | Output refused by `--private` / `--device`, or undetectable |
| 3 | Output changed during playback; stopped |
| 4 | API key missing or unreadable |
| 5 | Provider failed |
| 6 | Missing dependency (`say`, `afplay`) |
| 7 | Player failed |
| 8 | `--out` path is a directory, missing, or unwritable (checked before any provider call) |
| 130 | Cancelled (SIGINT or SIGTERM); playback stopped |

Text is limited to 5,000 characters. Stdin must be valid UTF-8. `--out FILE` overwrites an existing
file. Cloud responses are capped at 25 MB and the `--timeout` applies to
the whole request.

## Roadmap

- Sonos output (port the safety model from the Sonos Say skill).
- Streaming playback for lower first-audio latency on cloud providers.
- More local engines (e.g. Piper) and Linux playback.

## Development

```sh
python3 -m unittest discover -s tests -t .
```

See [AGENTS.md](AGENTS.md) and [SECURITY.md](SECURITY.md). MIT licensed.
