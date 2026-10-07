"""Builds Watch together into ../app/.

    python3 build.py          readable build (recommended)
    python3 build.py --min    smaller build without comments or extra whitespace

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).

The page gets a strict Content-Security-Policy containing the SHA-256 hashes of its own inline
style and script, so only this code can run in it and it can't contact any website.
Always edit src/index.template.html and rebuild: an edited app/index.html won't run because its
hashes no longer match.
"""
import base64, hashlib, json, pathlib, re, sys, zlib
from minify import minify_js, minify_css, minify_html

here = pathlib.Path(__file__).parent
app = here.parent / "app"
app.mkdir(exist_ok=True)
src = (here / "index.template.html").read_text(encoding="utf-8")
small = "--min" in sys.argv

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
    "img-src blob:",
    "worker-src 'self' blob:",
    "connect-src 'none'",
    "font-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
])
page = page.replace("__CSP__", csp)
(app / "index.html").write_text(page, encoding="utf-8")
(app / "sw.js").write_text((here / "sw.js").read_text(encoding="utf-8"), encoding="utf-8")

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
print(f"Built Watch together {version}{' (small)' if small else ''}: app/index.html {len(page):,} bytes, app/sw.js")
