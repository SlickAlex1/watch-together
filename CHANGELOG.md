# Changelog

## 1.6.0

- **Subtitles inside the video file.** MKV and MP4 subtitles (SRT, ASS/SSA, WebVTT, MP4 text) now appear in a **Subtitles** menu next to Audio, and the CC button (or C) turns on the first one. A track marked as default in the file is turned on by itself. They're read in the background from where you're watching, so they show up within a second or two. Picture subtitles (PGS, VobSub) are listed but can't be shown yet.
- **More sound formats:** WavPack, TTA, Monkey's Audio, WMA Lossless and Voice, MP1, AMR, ADPCM, A-law/µ-law and RealAudio are now converted too, so every sound track in a file can be picked from the Audio menu.
- **More reliable reaction sounds on phones:** if the phone or browser pauses sound (screen off, another app, a call), it now comes back on the next tap; newer browsers' "interrupted" state is handled; and sounds that can't play right away are skipped rather than all playing at once later. (Tip: video-call apps' noise cancellation can filter out reaction sounds if you're in a call on the same device.)
- **Smoother MKV videos in Firefox.** Firefox's MKV support is new and plays MKV files less smoothly than MP4. The app now repackages MKV videos (H.264 and HEVC) as MP4 while they play and uses the browser's MediaSource player, the one streaming sites use. The picture is copied unchanged, not re-encoded, and nothing is uploaded. The sound comes from the app's converter. It's a setting, **Smoother MKV videos**, on by default in Firefox and available in other browsers. If repackaging fails for a file, it plays the usual way.
- The relay setup no longer names a specific provider's server: the example address is now `relay.example.com:3478`, and Metered Open Relay is suggested as one free option.
- The sound converter's build script works on a clean machine (it brings its own copy of clang's WebAssembly runtime), and there's a new test for the repackager.

## 1.5.1

- **Fixed: no sound for the other person when streaming.** In Chrome and Edge, only the first song or video streamed with sound; every file after it reached the other person silent (only sound converted by the app came through). The app now captures the video once, so every file's sound is sent.
- **Fixed: sound stopping for good after jumping (seen on Android with MKV videos).**
  - Converted sound: if the converter gets stuck or stops, which phones short of memory can cause, it now restarts by itself and carries on from the same spot, instead of staying silent until the app was restarted.
  - A video's own sound: if it was playing before a jump and stays completely silent after it, the app switches to converting the sound itself, and says so.
  - On Android, AC-3 and E-AC-3 sound is always converted by the app instead of the phone's own decoder.
- **Fixed: choppy video in Firefox while watching together** (especially on phones). Firefox keeps in sync by jumping; when a jump landed late, as it can on phones in big MKV files, the app jumped again about every second. It now waits between jumps, aims ahead by how late the last one landed, and allows a slightly bigger gap if the device keeps falling behind.
- Converted sound reads the file in larger pieces, which is faster on phones.
- Subtitles are timed every frame only when a file has subtitles, so the page does less work otherwise.
- If the phone pauses sound (a call, another app), the next tap brings it back.
- The smoke test now also checks that streamed sound arrives after the next file starts.

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
