"""Makes the app's two typefaces small enough to embed in the page: src/fonts/*.woff2.

    python3 tools/make_fonts.py path/to/google-fonts/ofl

Needs fontTools and Brotli (pip install fonttools brotli). The source fonts are in Google's font
repository (https://github.com/google/fonts): ofl/newsreader and ofl/hankengrotesk. Both are under
the SIL Open Font License 1.1 (licenses/OFL-Newsreader.txt, licenses/OFL-HankenGrotesk.txt).

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
"""
import pathlib, subprocess, sys, tempfile
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ofl = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "ofl")
out = pathlib.Path(__file__).resolve().parent.parent / "src" / "fonts"
out.mkdir(exist_ok=True)
# Latin, Latin-1, Latin Extended-A (Romanian ă â î ş ţ), ș ț, and the typographic punctuation used.
UNICODES = ("U+0020-007E,U+00A0-00FF,U+0100-017F,U+0218-021B,U+02C6,U+02DA,U+02DC,U+2013-2014,U+2018-201E,"
            "U+2022,U+2026,U+2032-2033,U+2039-203A,U+20AC,U+2122,U+2190-2193,U+2212,U+00D7")
JOBS = [
    # Newsreader: titles at display size, the italic lines at reading size (one optical size each).
    ("newsreader/Newsreader[opsz,wght].ttf", "newsreader.woff2", {"wght": (400, 500), "opsz": 60}),
    ("newsreader/Newsreader-Italic[opsz,wght].ttf", "newsreader-italic.woff2", {"wght": (400, 500), "opsz": 24}),
    ("hankengrotesk/HankenGrotesk[wght].ttf", "hanken.woff2", {"wght": (400, 700)}),
]
with tempfile.TemporaryDirectory() as tmp:
    for src, dst, axes in JOBS:
        part = pathlib.Path(tmp) / "part.ttf"
        instancer.instantiateVariableFont(TTFont(ofl / src), axes).save(part)
        subprocess.run(["pyftsubset", str(part), f"--unicodes={UNICODES}",
                        "--layout-features=kern,liga,calt,ccmp,locl,mark,mkmk,onum,lnum,tnum,pnum",
                        "--flavor=woff2", f"--output-file={out / dst}", "--no-hinting", "--desubroutinize"], check=True)
        print(dst, (out / dst).stat().st_size, "bytes")
