# Yap Permit

An open-source, agent-friendly text-to-speech CLI. `yap` speaks text through
your current audio output, can write audio to a file or stdout, and has a
**private mode** that only plays through AirPods or headphones and refuses
otherwise.

> Status: early MVP. Playback is macOS-only (`afplay`); `--out` works
> anywhere the provider works.

## Install

```sh
pipx install git+https://github.com/KyleMyers001/yap-permit
# or, from a checkout:
python3 -m yap_permit "hello"
```

Requires Python 3.9+. No third-party Python packages.

## Usage

```sh
yap "Build finished."                       # macOS say, current output
echo "Tests passed" | yap                   # stdin (default when no text)
yap --private "Your 3pm moved to 4."        # headphones only, or exit 2
yap --device "Studio Display" "hello"       # require a named output
yap -p elevenlabs -v VOICE_ID "hello"       # cloud provider
yap -p openai -o hello.mp3 "hello"          # write a file, don't play
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
| `elevenlabs` | ElevenLabs API | `ELEVENLABS_VOICE_ID` or `--voice`, plus a key |
| `openai` | OpenAI API | a key; voice defaults to `alloy` |

Set the default with `YAP_PROVIDER`. Cloud providers are bring-your-own-key.
Supply a key with either:

- `ELEVENLABS_API_KEY` / `OPENAI_API_KEY`, or
- `<PROVIDER>_KEYCHAIN_SERVICE` and `<PROVIDER>_KEYCHAIN_ACCOUNT`, naming an
  existing macOS Keychain item (`ELEVENLABS_…`, `OPENAI_…`).

Keys are never accepted as arguments and never printed.

## Output routing and private mode

`yap` never changes your audio output. It plays on the current macOS
default output. `--private` and `--device` add a gate on that output:

- The output is checked **before** credentials are read or text is sent to
  a provider, again just before playback, and every 0.25 s during playback.
- `--private` allows outputs whose name contains AirPods, Headphones,
  Beats, Earbuds, or Buds. Anything else, or a failure to detect the output,
  is refused (exit 2).
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
| 130 | Cancelled (SIGINT or SIGTERM); playback stopped |

Text is limited to 5,000 characters.

## Roadmap

- Sonos output (port the safety model from the Sonos Say skill).
- Streaming playback for lower first-audio latency on cloud providers.
- More local engines (e.g. Piper) and Linux playback.

## Development

```sh
python3 -m unittest discover -s tests -t .
```

See [AGENTS.md](AGENTS.md). MIT licensed.
