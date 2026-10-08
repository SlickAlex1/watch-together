"""Builds Watch together into ../app/.

    python3 build.py          readable build (recommended)
    python3 build.py --min    smaller build without comments or extra whitespace
    python3 build.py --site-url https://example.github.io/watch-together/
                              where the online version lives (used in invitations and link
                              previews); the default is the official site below. "--site-url none"
                              leaves it out.

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).

The page gets a strict Content-Security-Policy containing the SHA-256 hashes of its own inline
style and script, so only this code can run in it and it can't contact any website.
Always edit src/index.template.html and rebuild: an edited app/index.html won't run because its
hashes no longer match.
"""
import base64, hashlib, html, json, pathlib, re, shutil, sys, zlib
from minify import minify_js, minify_css, minify_html

OFFICIAL_SITE = "https://slickalex1.github.io/watch-together/"

here = pathlib.Path(__file__).parent
app = here.parent / "app"
app.mkdir(exist_ok=True)
src = (here / "index.template.html").read_text(encoding="utf-8")
small = "--min" in sys.argv

site = OFFICIAL_SITE
if "--site-url" in sys.argv:
    i = sys.argv.index("--site-url")
    site = sys.argv[i + 1].strip() if i + 1 < len(sys.argv) else ""
    site = "" if site in ("", "none") else site.rstrip("/") + "/"
if site and not re.fullmatch(r"https://[A-Za-z0-9.\-]+(:\d+)?(/[A-Za-z0-9._~\-/]*)?", site):
    print(f"warning: --site-url must be a plain https:// address, so {site!r} is left out")
    site = ""
src = src.replace("__SITE_URL__", site)
DESCRIPTION = ("Watch videos and listen to music in sync with a friend, browser to browser. "
               "End-to-end encrypted, no account.")
social = ""
if site:   # link previews (Open Graph) when the address is shared in a chat app
    social = "\n".join(f'<meta property="{k}" content="{html.escape(v)}">' for k, v in [
        ("og:type", "website"), ("og:site_name", "Watch together"), ("og:title", "Watch together"),
        ("og:description", DESCRIPTION), ("og:url", site), ("og:image", site + "og-image.jpg"),
        ("og:image:width", "1200"), ("og:image:height", "630"),
        ("og:image:alt", "Watch together: watch videos and listen to music in sync with a friend"),
    ]) + '\n<meta name="twitter:card" content="summary_large_image">'
src = src.replace("<!--SOCIAL-->", social)

# Fonts (Newsreader and Hanken Grotesk, SIL Open Font License; see licenses/) are embedded in the
# page itself, so it needs nothing from other websites and works as a file too.
FONTS = [("Newsreader", "normal", "400 500", "newsreader.woff2"), ("Newsreader", "italic", "400 500", "newsreader-italic.woff2"),
         ("Hanken Grotesk", "normal", "400 700", "hanken.woff2")]
faces = "".join(
    "@font-face{font-family:'%s';font-style:%s;font-weight:%s;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}\n"
    % (fam, sty, wt, base64.b64encode((here / "fonts" / f).read_bytes()).decode()) for fam, sty, wt, f in FONTS)
src = src.replace("/*__FONTS__*/", faces)

def h(block):
    return "'sha256-" + base64.b64encode(hashlib.sha256(block.encode("utf-8")).digest()).decode() + "'"

style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
script = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
version = re.search(r"const APP_VERSION = '([^']+)'", script).group(1)

if small:
    licence_header = re.search(r"<!--.*?-->", src, re.S).group(0)   # keep the copyright notice
    mstyle, mscript = minify_css(style), minify_js(script)
    page = src.replace(style, "\0STYLE\0").replace(script, "\0SCRIPT\0")
    page = minify_html(page).replace("\0STYLE\0", mstyle).replace("\0SCRIPT\0", mscript)
    page = page.replace("<!doctype html>", "<!doctype html>\n" + licence_header, 1)
    style, script = mstyle, mscript
else:
    page = src

csp = "; ".join([
    "default-src 'none'",
    # 'strict-dynamic' lets the app load its own audio-decoder.js on demand; 'wasm-unsafe-eval'
    # allows WebAssembly (the audio decoder). No other code and no remote scripts can run.
    "script-src " + h(script) + " 'strict-dynamic' 'wasm-unsafe-eval'",
    "style-src " + h(style),
    "media-src blob:",
    "img-src blob: 'self'",
    "manifest-src 'self'",
    "worker-src 'self' blob:",
    "connect-src 'none'",
    "font-src data:",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
])
page = page.replace("__CSP__", csp)
(app / "index.html").write_text(page, encoding="utf-8")
(app / "sw.js").write_text((here / "sw.js").read_text(encoding="utf-8").replace("__VERSION__", version),
                          encoding="utf-8")
# Files for installing the app from a website (ignored when it's opened as a file).
shutil.copyfile(here / "manifest.webmanifest", app / "manifest.webmanifest")
shutil.copyfile(here / "og-image.jpg", app / "og-image.jpg")
(app / "icons").mkdir(exist_ok=True)
for f in sorted((here / "icons").glob("*.png")):
    shutil.copyfile(f, app / "icons" / f.name)

# Audio decoder: the WebAssembly module (compressed) and its worker, in one file loaded on demand.
wasm_file = here.parent / "tools" / "audio-decoder" / "wt_audio.wasm"
if wasm_file.exists():
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = comp.compress(wasm_file.read_bytes()) + comp.flush()
    worker = (here / "audio-decoder.worker.js").read_text(encoding="utf-8")
    (app / "audio-decoder.js").write_text(
        "/* Watch together audio decoder. Copyright (C) 2026 SlickAlex, GPL-3.0-or-later.\n"
        " * Contains FFmpeg 7.1 demuxers and audio decoders compiled to WebAssembly (LGPL-2.1-or-later).\n"
        " * Source and build steps: tools/audio-decoder/ in the Watch together repository. */\n"
        "self.WTAudioDecoder = { wasm: '" + base64.b64encode(packed).decode() + "',\n  worker: "
        + json.dumps(worker) + " };\n", encoding="utf-8")
    print(f"app/audio-decoder.js: wasm {wasm_file.stat().st_size:,} bytes -> packed {len(packed):,}")
else:
    print("note: tools/audio-decoder/wt_audio.wasm not found, so app/audio-decoder.js wasn't updated")
print(f"Built Watch together {version}{' (small)' if small else ''}: app/index.html {len(page):,} bytes, "
      f"sw.js, manifest, icons; site address: {site or 'none'}")
