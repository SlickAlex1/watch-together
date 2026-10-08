#!/bin/sh
# Rebuilds wt_audio.wasm from source: FFmpeg 7.1 (demuxers, audio decoders, MP4 packager) + wt_audio.c.
# Needs: git, make, clang 18+ with wasm-ld, llvm-ar/llvm-ranlib/llvm-nm, curl.
# Copyright (C) 2026 SlickAlex. GPL-3.0-or-later. FFmpeg itself is LGPL 2.1 or later.
set -e
cd "$(dirname "$0")"
W=${WORK:-$PWD/.work}
mkdir -p "$W"
SDK=wasi-sdk-25
if [ ! -d "$W/wasi-sysroot-25.0" ]; then
  curl -sSfL "https://github.com/WebAssembly/wasi-sdk/releases/download/$SDK/wasi-sysroot-25.0.tar.gz" | tar xz -C "$W"
  curl -sSfL "https://github.com/WebAssembly/wasi-sdk/releases/download/$SDK/libclang_rt.builtins-wasm32-wasi-25.0.tar.gz" | tar xz -C "$W"
fi
S="$W/wasi-sysroot-25.0"
RT="$W/libclang_rt.builtins-wasm32-wasi-25.0/libclang_rt.builtins-wasm32.a"
# clang looks for the WebAssembly runtime in its own folder, which system packages leave out:
# give it a resource folder of its own (clang's headers + the runtime downloaded above).
RES="$W/clang-resource"
if [ ! -f "$RES/lib/wasip1/libclang_rt.builtins-wasm32.a" ]; then
  mkdir -p "$RES/lib/wasip1"
  ln -sfn "$(clang -print-resource-dir)/include" "$RES/include"
  cp "$RT" "$RES/lib/wasip1/"
fi
[ -d "$W/ffmpeg" ] || git clone --depth 1 --branch n7.1 https://github.com/FFmpeg/FFmpeg.git "$W/ffmpeg"
mkdir -p "$W/build"
cd "$W/build"
if [ ! -f libavcodec/libavcodec.a ]; then
  ../ffmpeg/configure \
    --target-os=none --arch=wasm32 --enable-cross-compile --cc=clang --cxx=clang++ \
    --ar=llvm-ar --ranlib=llvm-ranlib --nm=llvm-nm --strip=llvm-strip \
    --extra-cflags="--target=wasm32-wasip1 --sysroot=$S -resource-dir=$RES -D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS" \
    --extra-ldflags="--target=wasm32-wasip1 --sysroot=$S -resource-dir=$RES" --optflags=-O2 \
    --disable-everything --disable-programs --disable-doc --disable-network --disable-pthreads \
    --disable-w32threads --disable-os2threads --disable-asm --disable-inline-asm --disable-x86asm \
    --disable-debug --disable-autodetect --disable-runtime-cpudetect \
    --disable-avdevice --disable-avfilter --disable-swscale --disable-postproc --enable-swresample --enable-small \
    --enable-demuxer=matroska,mov,avi,mpegts,mpegps,flv,ogg,asf,mp3,aac,ac3,eac3,dts,dtshd,truehd,mlp,flac,wav,w64,rm,wv,ape,tta,aiff,caf,amr \
    --enable-decoder=ac3,eac3,dca,truehd,mlp,aac,aac_latm,mp3,mp3float,mp2,mp2float,mp1,mp1float,flac,opus,vorbis,alac,wmav1,wmav2,wmapro,wmalossless,wmavoice,wavpack,tta,ape,amrnb,amrwb,adpcm_ms,adpcm_ima_wav,cook,atrac3,ra_144,ra_288,pcm_s16le,pcm_s16be,pcm_s24le,pcm_s24be,pcm_s32le,pcm_f32le,pcm_f32be,pcm_f64le,pcm_u8,pcm_s8,pcm_alaw,pcm_mulaw,pcm_bluray,pcm_dvd \
    --enable-parser=ac3,dca,mlp,aac,aac_latm,mpegaudio,flac,opus,vorbis,h264,hevc,vp9,av1 \
    --enable-muxer=mp4
  make -j"$(nproc)"
fi
cd - >/dev/null
clang --target=wasm32-wasip1 --sysroot="$S" -resource-dir="$RES" -O2 -mexec-model=reactor -D_WASI_EMULATED_SIGNAL \
  -I"$W/build" -I"$W/ffmpeg" wt_audio.c \
  "$W/build/libavformat/libavformat.a" "$W/build/libavcodec/libavcodec.a" \
  "$W/build/libswresample/libswresample.a" "$W/build/libavutil/libavutil.a" "$RT" \
  -lm -lwasi-emulated-signal -lwasi-emulated-process-clocks -nodefaultlibs -lc \
  -Wl,--export=malloc -Wl,--export=free -Wl,--strip-all -Wl,-z,stack-size=1048576 \
  -Wl,--initial-memory=33554432 -Wl,--max-memory=1073741824 -o wt_audio.wasm
ls -la wt_audio.wasm
echo "Now run: python3 ../../src/build.py"
