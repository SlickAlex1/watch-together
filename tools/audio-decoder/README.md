# Audio decoder and MP4 repackager

Browsers can't play several audio formats common in movie files: AC-3 (Dolby Digital), E-AC-3 (Dolby Digital Plus), DTS (including DTS-HD), TrueHD, and in some browsers others too. When a video has such a track, Watch together decodes it itself with this module and plays it in sync with the picture.

The same module also **repackages MKV videos as fragmented MP4** for Firefox, whose MKV support is new and less smooth than its MP4 support. The video track is copied unchanged (not re-encoded) and played through the browser's MediaSource player. MKV only stores display times, so the decode times MP4 needs are worked out from the display times of the next frames.

- `wt_audio.c`: a small C interface around FFmpeg: open a file, list its tracks, pick one, seek, decode to stereo; and repackage the video track (`wt_vstart`, `wt_vread`).
- `wt_audio.wasm`: the compiled module, built from FFmpeg 7.1 with only demuxers, parsers, audio decoders and the MP4 muxer enabled. `src/build.py` packs it into `app/audio-decoder.js`.
- `build.sh`: rebuilds `wt_audio.wasm` from source (downloads FFmpeg 7.1, the WASI sysroot and clang's WebAssembly runtime from GitHub).
- `test_decoder.mjs`: decodes every audio track of a file with the module and compares it with FFmpeg's own output: `node test_decoder.mjs wt_audio.wasm movie.mkv`.
- `test_repack.mjs`: repackages a file's video from the start and after a jump: `node test_repack.mjs wt_audio.wasm movie.mkv out-folder`. Compare the results with the original using `ffmpeg -i ... -f framemd5 -`; the pictures should be identical.

**Formats:**

- Containers: MKV/WebM, MP4/MOV, AVI, MPEG-TS/M2TS, MPEG-PS, FLV, OGG, ASF/WMV, RealMedia, and plain audio files (including WavPack, TTA, APE, AIFF, CAF and AMR).
- Audio: AC-3, E-AC-3, DTS/DTS-HD, TrueHD/MLP, AAC, MP3, MP2, MP1, FLAC, Opus, Vorbis, ALAC, WMA (Pro, Lossless, Voice), WavPack, TTA, Monkey's Audio, AMR, ADPCM, RealAudio, A-law/µ-law and PCM.
- Subtitles (read, not decoded): the text ones inside a file, SRT, ASS/SSA, WebVTT and MP4 timed text (`wt_sstart`, `wt_sread`; test with `node test_subtitles.mjs wt_audio.wasm movie.mkv`).

The file is read locally in a background worker; nothing is uploaded.

## License

FFmpeg is licensed under the GNU Lesser General Public License 2.1 or later ([licenses/LGPL-2.1.txt](../../licenses/LGPL-2.1.txt)). This build uses no GPL-only FFmpeg parts (no encoders at all). The FFmpeg source is at <https://github.com/FFmpeg/FFmpeg>, tag `n7.1`, and `build.sh` reproduces the build. `wt_audio.c` is part of Watch together (GPL-3.0-or-later).

Some of these audio formats may be covered by patents in some countries; most of the relevant patents have expired.
