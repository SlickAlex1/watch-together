#!/bin/sh
# Creates synthetic test media in tests/media/ (test patterns and tones only, nothing copyrighted).
# Needs ffmpeg. Copyright (C) 2026 SlickAlex. GPL-3.0-or-later.
set -e
cd "$(dirname "$0")"
mkdir -p media
L="-loglevel error -y"
for i in 1 2 3; do
  ffmpeg $L -f lavfi -i "testsrc2=duration=12:size=320x180:rate=25" -f lavfi -i "sine=frequency=$((300 * i)):duration=12" \
    -c:v libvpx -b:v 150k -c:a libopus "media/Demo.S01E0$i.webm"
done
printf '1\n00:00:01,000 --> 00:00:04,000\nHello there\n\n2\n00:00:05,000 --> 00:00:08,000\nSecond line\n' > media/Demo.S01E01.en.srt
ffmpeg $L -f lavfi -i "testsrc2=size=600x600:duration=1" -frames:v 1 media/cover.png
ffmpeg $L -f lavfi -i "sine=frequency=330:duration=15" -i media/cover.png -map 0:a -map 1:v -c:a libmp3lame -b:a 128k \
  -c:v png -id3v2_version 3 -disposition:v attached_pic -metadata title="Test Song" -metadata artist="Test Artist" "media/01 - test song.mp3"
echo "Test media written to tests/media/"
