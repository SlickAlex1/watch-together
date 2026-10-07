"""Draws the app icons (a gold play button on the app's dark background) into src/icons/.

    python3 tools/make_icons.py      (needs Pillow: pip install pillow)

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
The icons match the tab icon drawn in src/index.template.html. build.py copies them into app/icons/.
"""
import pathlib
from PIL import Image, ImageDraw

BG, GOLD = (0x16, 0x13, 0x1B, 255), (0xD6, 0xB4, 0x7A, 255)
out = pathlib.Path(__file__).resolve().parent.parent / "src" / "icons"
out.mkdir(exist_ok=True)
SS = 8  # draw large, then shrink, for smooth edges


def icon(size, rounded, scale=1.0):
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:   # same shape as the tab icon: 64x64 with 14px corners
        d.rounded_rectangle((0, 0, n - 1, n - 1), radius=round(n * 14 / 64), fill=BG)
    else:         # full square: the system cuts its own shape (maskable, Apple)
        d.rectangle((0, 0, n, n), fill=BG)
    # Play triangle from the tab icon (M25 18 l22 14 -22 14 z on a 64 grid), scaled around the centre.
    pts = [(25, 18), (47, 32), (25, 46)]
    cx, cy = 32, 32
    d.polygon([((cx + (x - cx) * scale) * n / 64, (cy + (y - cy) * scale) * n / 64) for x, y in pts], fill=GOLD)
    return img.resize((size, size), Image.LANCZOS)


icon(192, True).save(out / "icon-192.png", optimize=True)
icon(512, True).save(out / "icon-512.png", optimize=True)
icon(512, False, 0.9).save(out / "icon-maskable-512.png", optimize=True)    # stays inside the safe zone
icon(180, False, 1.1).convert("RGB").save(out / "apple-touch-icon.png", optimize=True)
print("Wrote", ", ".join(sorted(p.name for p in out.glob("*.png"))), "to", out)
