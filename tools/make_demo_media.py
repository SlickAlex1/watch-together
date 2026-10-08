"""Makes the invented demo episodes and song used for the README screenshots.

    python3 tools/make_demo_media.py [folder]        # default: tests/demo-media (ignored by git)

Draws three abstract harbour scenes and a cover with Pillow, then uses ffmpeg to turn them into
long, tiny "episodes" of an invented show (Harbour Lights), a subtitle file and a song by an
invented artist. Nothing in them is taken from a real film, show or record.

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
"""
import pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'tests' / 'demo-media')
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1280, 720
lerp = lambda a, b, t: tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def scene(path, stops, sun, hill, sea_top, sea_bot, boat, lights, glow):
    im = Image.new('RGB', (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        f = y / H
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= f <= p1: d.line([(0, y), (W, y)], fill=lerp(hexc(c0), hexc(c1), (f - p0) / (p1 - p0))); break
    if sun:
        x, y, r, c = sun
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([x - r * 3, y - r * 3, x + r * 3, y + r * 3], fill=hexc(glow) + (90,))
        g = g.filter(ImageFilter.GaussianBlur(60)); im.paste(g, (0, 0), g)
        ImageDraw.Draw(im).ellipse([x - r, y - r, x + r, y + r], fill=hexc(c))
    d = ImageDraw.Draw(im, 'RGBA')
    d.ellipse([-80, int(H * .57), int(W * .46), int(H * .78)], fill=hexc(hill))
    d.ellipse([int(W * .3), int(H * .605), int(W * .72), int(H * .72)], fill=lerp(hexc(hill), (255, 255, 255), .06))
    top = int(H * .66)
    for y in range(top, H): d.line([(0, y), (W, y)], fill=lerp(hexc(sea_top), hexc(sea_bot), (y - top) / (H - top)))
    for i in range(14):
        y = top + 18 + i * 14; x = int(W * .58) + (i % 3) * 30
        d.rounded_rectangle([x, y, x + 200 - i * 9, y + 4], 2, fill=hexc(glow) + (70 - i * 4,))
    bx, by = int(W * .18), int(H * .615)
    d.polygon([(bx, by), (bx + int(W * .23), by), (bx + int(W * .21), by + int(H * .045)), (bx + int(W * .02), by + int(H * .045))], fill=hexc(boat))
    d.rectangle([bx + int(W * .05), by - int(H * .04), bx + int(W * .16), by], fill=hexc(boat))
    d.rectangle([bx + int(W * .095), by - int(H * .078), bx + int(W * .11), by - int(H * .04)], fill=hexc(boat))
    for k in range(9): d.rectangle([bx + int(W * .02) + k * 28, by + 10, bx + int(W * .02) + k * 28 + 12, by + 16], fill=hexc(lights))
    for k in range(4): d.rectangle([bx + int(W * .06) + k * 32, by - 20, bx + int(W * .06) + k * 32 + 12, by - 12], fill=hexc(lights))
    im.save(path)

EPISODES = [
    ('The Lighthouse Keeper', 2712, [(0, '#24324F'), (.45, '#3E5875'), (.66, '#6E86A0'), (1, '#0E131D')], (900, 300, 34, '#E8EEF5'), '#1A2232', '#1C2738', '#0B0F18', '#0D1119', '#FFE2A8', '#9DB6D6'),
    ('Salt and Signal', 2934, [(0, '#6B7C8C'), (.5, '#A9B4B6'), (.66, '#C9CDC8'), (1, '#2B3036')], None, '#49505A', '#5A626B', '#2B3036', '#262A30', '#FFD28A', '#E3E6E2'),
    ('The Night Ferry', 2830, [(0, '#1F2A44'), (.38, '#5B4A6A'), (.58, '#C27A62'), (.66, '#F0B27A'), (1, '#121521')], (820, 418, 50, '#FFD9A3'), '#3B3247', '#2A2738', '#121521', '#14131C', '#FFCF87', '#F2B488'),
]
ff = lambda *a: subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
for n, (title, secs, *look) in enumerate(EPISODES, 1):
    still = OUT / f'scene{n}.png'
    scene(still, *look)
    # Two frames a second keeps a 45-minute "episode" quick to make and small.
    ff('-framerate', '2', '-loop', '1', '-i', str(still), '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(secs),
       '-vf', 'format=yuv420p', '-c:v', 'libvpx-vp9', '-b:v', '60k', '-deadline', 'realtime', '-cpu-used', '8', '-g', '20',
       '-c:a', 'libopus', '-b:a', '16k', str(OUT / f'Harbour Lights - 0{n} - {title}.webm'))
(OUT / 'Harbour Lights - 03 - The Night Ferry.en.srt').write_text(
    '1\n00:18:30,000 --> 00:18:50,000\nI told you the ferry never waits.\n\n2\n00:18:52,000 --> 00:18:58,000\nThen we swim.\n', encoding='utf-8')
cover = Image.new('RGB', (600, 600)); cd = ImageDraw.Draw(cover)
for y in range(600): cd.line([(0, y), (600, y)], fill=lerp(hexc('#2A2219'), hexc('#8A5A3E'), y / 600))
cd.ellipse([170, 150, 430, 410], fill=hexc('#E9B872'))
for i in range(6): cd.rectangle([0, 420 + i * 30, 600, 432 + i * 30], fill=lerp(hexc('#1A1410'), hexc('#3E2C25'), i / 6))
cover.save(OUT / 'cover.png')
ff('-f', 'lavfi', '-i', 'sine=f=330:d=232', '-i', str(OUT / 'cover.png'), '-map', '0', '-map', '1', '-af', 'volume=0.03',
   '-c:a', 'libmp3lame', '-b:a', '64k', '-c:v', 'png', '-disposition:v', 'attached_pic', '-id3v2_version', '3',
   '-metadata', 'artist=Mara Voss', '-metadata', 'title=Low Tide', '-metadata', 'album=Harbour Songs', str(OUT / 'Mara Voss - Low Tide.mp3'))
print('Demo media in', OUT)
