# Watch together

[![Status: beta](https://img.shields.io/badge/status-beta-orange)](CHANGELOG.md)
[![Version 1.4.0](https://img.shields.io/badge/version-1.4.0-d6b47a)](CHANGELOG.md)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Runs in: Chrome, Edge, Firefox](https://img.shields.io/badge/runs%20in-Chrome%20%7C%20Edge%20%7C%20Firefox-555)](#quick-start)
[![Works on: desktop and Android](https://img.shields.io/badge/works%20on-desktop%20%7C%20Android-555)](#quick-start)
[![Sound: AC-3, E-AC-3, DTS, TrueHD](https://img.shields.io/badge/sound-AC--3%20%7C%20E--AC--3%20%7C%20DTS%20%7C%20TrueHD-8a63d2)](#video-and-music-formats)
[![WebRTC, end-to-end encrypted](https://img.shields.io/badge/WebRTC-end--to--end%20encrypted-2ea44f)](#privacy-and-security)
[![No server, no account](https://img.shields.io/badge/server-none-2ea44f)](#privacy-and-security)
[![Last commit](https://img.shields.io/github/last-commit/slickalex1/watch-together)](../../commits)
[![Built with Claude](https://img.shields.io/badge/built%20with-Claude-d97757)](#credits)

**Watch videos and listen to music in sync with a friend, browser to browser.**
End-to-end encrypted. No server, no account, nothing to install.

*Made by SlickAlex · powered by Claude · version 1.4.0 (beta) · [GPL-3.0](LICENSE)*

![Watch together playing a video, with a chat message flying across it and the shared playlist](docs/screenshots/player.png)

> **Beta:** Watch together works and is tested, but it hasn't been used on many devices yet. If something breaks, please [open an issue](../../issues/new/choose).

## What it does

- **Watch in sync.** Play, pause, seek, skip and change speed, and the other person follows. Small drifts are corrected automatically.
- **Your files, or streamed.**
  - If you both have the episode, each plays your own copy at full quality.
  - If only you have it, it streams live to the other person.
  - The **playback mode** lets you choose between these.
- **Movie sound browsers can't play.** AC-3, E-AC-3, DTS, TrueHD and more (common in MKV movies) are converted on your device and played in sync. Files with several sound tracks get a menu to pick the language.
- **Music too.** MP3, M4A, FLAC, OGG and WAV, with cover art, title and artist read from the file.
- **Playlists.** Episodes and songs play in order. There's loop, shuffle, like/dislike and "continue watching". You can also share your playlist so the other person can pick (and optionally edit).
- **Chat.**
  - Encrypted messages, with replies.
  - **Bullet chat**: messages fly across the video.
  - **Reactions with sound**: applause, boo, laughter and more.
- **Subtitles.** `.srt` and `.vtt`, with adjustable size and timing.
- **Invitations with a preview.** A picture and a friendly message that the other person pastes into the app.
- **Works over the internet.** It connects directly when possible, or through a relay you choose. With a relay, IP addresses stay hidden.
- **Notifications, picture-in-picture**, signal strength and data usage display, and keyboard shortcuts.

| Music with cover art | On a phone | Invitation picture |
|---|---|---|
| ![Music playing with its cover art](docs/screenshots/music.png) | ![The app on a phone](docs/screenshots/phone.png) | ![The picture sent with an invitation](docs/screenshots/invitation.jpg) |

## Quick start

1. **Open the app.** Download the latest release (or this repository) and open **`app/index.html`** in Chrome, Edge or Firefox. On Android, open it through a file manager such as Cx File Explorer. Keep all the files of the `app` folder together.
2. **Add something to watch.** In the **Playlist** tab, add your videos or music.
3. **Choose where the other person is** (Connect tab):
   - **Somewhere else (over the internet).** First set up a relay (**Step 1**, below). Between two homes, phones or countries, a direct connection fails more often than it works, and the relay also hides your IP address. You do this once.
   - **Next to me (same Wi-Fi).** No relay needed; go straight to Step 2.
4. **Connect (Step 2).**
   1. One person taps **Start a session** and sends the invitation (Share… or Copy) in any chat app.
   2. The other taps **Join a session**, pastes the whole message, and sends the reply back.
   3. The first person pastes the reply and taps **Connect**.
5. **Compare the safety code** on a call. If it matches, nobody is in the middle, and chat unlocks.

Both people should use the same version of the app; it's shown at the bottom of the page.

## Step 1: set up a free relay (over the internet)

A relay (a "TURN server") passes your encrypted connection along when networks block a direct one, which mobile data and most home, school and office networks do. It can't see what you share. Only the person who starts the session needs one.

1. Create a free account with a TURN provider, for example ExpressTURN or Metered (both have free plans; check their current limits).
2. In the provider's dashboard, copy the **server address** (for example `free.expressturn.com:3478`), the **username** and the **password**. A "secret key" isn't needed.
3. Paste them into **Relay for internet connections** in the Connect tab and tap **Test relay**. It should say "Relay works".
4. Tick **Remember these relay details** so you don't have to type them again.

With a relay:

- **Your IP address stays hidden** from the other person.
- **Your relay isn't shared by default.** You can let the other person use it for one session; the invitation then carries time-limited, encrypted access, and their IP is hidden too.
- **Temporary logins:** if your relay supports them (TURN REST API, e.g. a secret key), the relay itself refuses the shared login once the time is up.

Not sure whether you need one? Tap **Check my connection**. If the app says your network is "hard" (typical of mobile data), you do.

## Privacy and security

- **Everything between the two of you is encrypted end to end** (WebRTC: DTLS/SRTP): chat, reactions, playback commands and streams. The safety code proves no one is in the middle.
- **No servers, no accounts, no tracking.** Videos never leave your device unless you stream them to the person you're connected to.
- **Locked-down page:** a strict Content Security Policy only allows the app's own code. The page can't contact any website.
- **What others can see:**
  - The other person sees your IP address unless you use a relay.
  - Your relay provider and the optional STUN services see that two addresses are talking, but never what you share.
- **Saved in your browser only:**
  - settings, watch positions and likes;
  - relay details, if you choose.

  **Settings → Data saved in this browser** lists exactly what's stored right now and deletes all of it with one button. Your videos, music and chat are never saved, so there's nothing of them to delete.

To report a security problem, see [SECURITY.md](SECURITY.md).

## Video and music formats

**Pictures:** whatever your browser can decode: H.264, VP8, VP9 and AV1 everywhere; HEVC/x265 only on some devices.

**Sound:** the app plays every common format. When the browser can't play a file's sound itself, the app converts it **on your device** (nothing is uploaded) and plays it in sync with the picture:

| Plays everywhere | Converted by the app (sound inside video files) |
|---|---|
| AAC, MP3, Opus, Vorbis, FLAC | AC-3 (Dolby Digital), E-AC-3 (Dolby Digital Plus), DTS and DTS-HD, TrueHD, ALAC, WMA, PCM |

Video files: MKV, MP4/M4V, MOV, AVI, WebM, MPEG-TS/M2TS, WMV and FLV. Plain music files play as the browser allows (MP3, AAC/M4A, FLAC, OGG/Opus and WAV work everywhere).

- **Several sound tracks** (for example English, Romanian and a commentary): pick one in the **Audio** menu under the title.
- **Surround** is mixed down to stereo.
- **At speeds other than 1×**, converted sound plays slightly higher or lower in pitch.
- **When streaming**, the converted sound is sent along, so the other person hears it too.
- **Turning it off:** Settings → "Convert sound the browser can't play".

The converter is FFmpeg compiled to WebAssembly (see [tools/audio-decoder](tools/audio-decoder/README.md)).

**If a video isn't playing smoothly**, the app tells you. Firefox's support for MKV files is newer than Chrome's: if an MKV stutters in Firefox, Chrome or Edge usually play it more smoothly. HEVC and 10-bit videos are heavy for many devices. Converting to MP4 with H.264 always helps:

    ffmpeg -i movie.mkv -c:v libx264 -crf 20 -c:a aac movie.mp4

When streaming, only the person who has the file needs a browser that can play it.

## Troubleshooting

- **Connection fails:** over the internet, set up a relay first (Step 1). Tap **Check my connection** on both devices to see why a direct connection doesn't work.
- **"Couldn't agree on video and audio formats":**
  1. Update both browsers.
  2. Use the same app version on both devices.
  3. Make a new invitation.
  4. If it still fails, tap **Copy details for the developer** and paste the result into a [bug report](../../issues/new/choose). It contains no addresses or passwords.
- **No sound from reactions on a phone:** tap the page once; phones only allow sound after a tap.
- **Notifications on Android:** they need the page opened through an `http://localhost` address (Cx File Explorer does this).

## For developers

    src/index.template.html   the whole app: HTML, CSS and JavaScript
    src/build.py              builds app/index.html (python3 build.py; add --min for a smaller file)
    src/minify.py             small minifier used by --min
    src/sw.js                 notification helper (service worker)
    src/audio-decoder.worker.js  background worker that converts sound (packed into app/audio-decoder.js)
    tools/audio-decoder/      the sound converter: C source, compiled WebAssembly, build script, test
    tests/                    smoke test, test media generator and a local test relay

Always edit `src/index.template.html` and rebuild. The page's security policy contains hashes of its own code, so a hand-edited `app/index.html` won't run. See [CONTRIBUTING.md](CONTRIBUTING.md) and [tests/README.md](tests/README.md).

## Legal

Watch together is free software under the **GNU General Public License v3** (or any later version): see [LICENSE](LICENSE). It comes **without any warranty**, and the authors aren't liable for how it's used.

**You're responsible for what you play, stream and share with it.** Only share content you have the right to share, and follow the laws where you live. More in [NOTICE.md](NOTICE.md).

The sound converter contains FFmpeg, licensed under the [LGPL 2.1 or later](licenses/LGPL-2.1.txt).

## Credits

Made by **SlickAlex**. Built with the help of Claude, an AI model by Anthropic. Anthropic isn't affiliated with this project. Sound conversion uses [FFmpeg](https://ffmpeg.org).
