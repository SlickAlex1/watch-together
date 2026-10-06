# Changelog

## 1.3.0: first public release (beta)

- Released as free software under the GNU GPL v3. The source is readable and the app ships unpacked.
- The first-launch screen is now an informational notice ("I understand") pointing to LICENSE and NOTICE.
- Added a smoke test, a test media generator and a local test relay for contributors.

## 1.2.1

- Fixed: connecting could fail with "Failed to parse codecs correctly" between different browsers. The app now:
  - repairs mismatched format entries;
  - checks its own invitations before sending them, and falls back to a compatibility invitation;
  - shows a clear message with a "Copy details" report.
- Fixed: very rarely, autoplay of the next item could stop when one side reached the end first.

## 1.2.0

- Invitations with a preview picture and a friendly message; the whole message can be pasted.
- The person joining sees who invited them and what to watch before replying.

## 1.1.0

- Relay sharing is off by default. Shared access is time-limited, sealed in the invitation and never stored.
- Optional temporary relay logins (TURN REST API).
- Animations for tabs, dialogs, lists and messages (respects "reduce motion").

## 1.0.0

- Bullet chat, signal strength, a shared and editable playlist, and picture-in-picture with an Android fallback.
- Hidden IP addresses through a relay, shorter connection codes, and sound on phones after the first tap.
- Version check between devices.

## Before 1.0

- Sync, streaming, playlists, music with cover art, loop/shuffle and likes.
- Chat with replies, reactions with sound, notifications and continue watching.
- Relay support, connection check, notice screen.
