# Security policy

## Reporting a vulnerability

Please report security issues privately. Do not open a public issue.

- Use GitHub's **private vulnerability reporting**: on the repository page,
  go to **Security → Report a vulnerability**.
- If that is unavailable, contact the repository owner,
  [@KyleMyers001](https://github.com/KyleMyers001), directly on GitHub.

Include the version or commit, steps to reproduce, and the impact. Please
do not include real API keys in reports.

## Scope

In scope: leaking API keys or Keychain selectors, sending credentials to
the wrong host (for example via redirects), `--private` playing on a
non-private output, and unsafe file handling with `--out`.

Out of scope: vulnerabilities in third-party TTS providers or in macOS
itself.

## Supported versions

Only the latest commit on the default branch receives fixes.
