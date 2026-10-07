# Changelog

## 1.5.0

- **Online version:** the app is published at https://slickalex1.github.io/watch-together/, automatically, every time it changes. Nothing to download; you can still use it from a folder, and mix both.
- **Install as an app:** opened online, it can be installed on phones and computers, with its own icon and full-screen window. Settings → **Install as an app** has a button or the steps for your device.
- **Works offline:** the online version keeps a copy of its own files in your browser, so the installed app opens without internet. It always checks for a newer version first.
- **Invitations include the link** to the online version, and the link shows a preview picture in chat apps.
- **Notifications** now also work on Android in the online version and the installed app.
- **Data saved in this browser** now also lists the offline copy, and deleting removes it too.

## 1.4.0

- **Sound browsers can't play:**
  - AC-3, E-AC-3, DTS/DTS-HD, TrueHD, ALAC, WMA and PCM are converted on the device by a built-in decoder (FFmpeg compiled to WebAssembly) and played in sync with the picture.
  - When streaming, the converted sound is sent along.
- **Several sound tracks:** an **Audio** menu to pick the language or commentary track.
- **Relay first over the internet:** the Connect tab asks where the other person is. Over the internet it guides you to set up a relay first (Step 1) and warns before starting without one; on the same Wi-Fi no relay is needed.
- **Settings → Data saved in this browser:** lists exactly what the app has stored right now and deletes all of it with one button. It also says what is never stored.
- **Smoother sync:** gentler speed corrections. In Firefox, and while converted sound plays, sync corrects by jumping only, avoiding constant speed changes.
- **Smoothness warning:** the app tells you when a video keeps skipping frames, and what helps.
- The volume setting is remembered.

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
