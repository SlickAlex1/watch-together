# Audio decoder

Browsers can't play several audio formats common in movie files: AC-3 (Dolby Digital), E-AC-3 (Dolby Digital Plus), DTS (including DTS-HD), TrueHD, and in some browsers others too. When a video has such a track, Watch together decodes it itself with this module and plays it in sync with the picture.

- `wt_audio.c`: a small C interface around FFmpeg: open a file, list its tracks, pick one, seek, and decode to stereo.
- `wt_audio.wasm`: the compiled module, built from FFmpeg 7.1 with only demuxers and audio decoders enabled. `src/build.py` packs it into `app/audio-decoder.js`.
- `build.sh`: rebuilds `wt_audio.wasm` from source (downloads FFmpeg 7.1 and the WASI sysroot from GitHub).
- `test_decoder.mjs`: decodes every audio track of a file with the module and compares it with FFmpeg's own output: `node test_decoder.mjs wt_audio.wasm movie.mkv`.

**Formats:**

- Containers: MKV/WebM, MP4/MOV, AVI, MPEG-TS/M2TS, MPEG-PS, FLV, OGG, ASF/WMV, and plain audio files.
- Audio: AC-3, E-AC-3, DTS/DTS-HD, TrueHD/MLP, AAC, MP3, MP2, FLAC, Opus, Vorbis, ALAC, WMA, WMA Pro and PCM.

The file is read locally in a background worker; nothing is uploaded.

## License

FFmpeg is licensed under the GNU Lesser General Public License 2.1 or later ([licenses/LGPL-2.1.txt](../../licenses/LGPL-2.1.txt)). This build uses no GPL-only FFmpeg parts. The FFmpeg source is at <https://github.com/FFmpeg/FFmpeg>, tag `n7.1`, and `build.sh` reproduces the build. `wt_audio.c` is part of Watch together (GPL-3.0-or-later).

Some of these audio formats may be covered by patents in some countries; most of the relevant patents have expired.
