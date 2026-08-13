# Digr — Releases

Downloads and update metadata for **Digr**, a local-first desktop music player.

This repository contains **no source code**. It exists only so that release
artifacts and the updater manifest are publicly reachable without a GitHub
account. Digr's source lives in a separate private repository.

## Downloads

Grab the latest `.dmg` from the [Releases](../../releases) page.

Digr is currently a **macOS alpha** (Apple silicon). It is not built or tested
for Windows or Linux.

## What's in a release

| Asset                    | What it is                                            |
| ------------------------ | ----------------------------------------------------- |
| `Digr_<version>_aarch64.dmg` | The installer. This is the one you want.          |
| `Digr.app.tar.gz`        | Update payload, fetched by Digr's built-in updater.   |
| `Digr.app.tar.gz.sig`    | Detached signature for the payload.                   |
| `latest.json`            | Update manifest the app checks.                       |

`latest.json` is what Digr's updater reads. Every update payload is signed, and
the app verifies that signature against a public key compiled into it before
installing anything — so an artifact that wasn't signed with the matching
private key is refused.

Please leave `latest.json` attached to the newest release; removing it breaks
in-app updates for everyone already running Digr.

## Alpha status

This is early software. Expect rough edges, and expect to report bugs.

**Builds are not yet signed with an Apple Developer ID.** macOS will refuse to
open an unsigned app downloaded from the internet, usually with a misleading
*"Digr is damaged and can't be opened"* message. It is not damaged. Until
signing is in place, open it the first time with **right-click → Open**, or
clear the quarantine flag:

```bash
xattr -dr com.apple.quarantine /Applications/Digr.app
```

Only do that for software you actually trust the source of.

## Issues

Bug reports and feature requests belong on the issue tracker here. Digr can
export a diagnostics log from **Settings ▸ About** — attaching one makes a
report far easier to act on.
