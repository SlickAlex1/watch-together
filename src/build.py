"""Builds Watch together into ../app/.

    python3 build.py          readable build (recommended)
    python3 build.py --min    smaller build without comments or extra whitespace

Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).

The page gets a strict Content-Security-Policy containing the SHA-256 hashes of its own inline
style and script, so only this code can run in it and it can't contact any website.
Always edit src/index.template.html and rebuild: an edited app/index.html won't run because its
hashes no longer match.
"""
import base64, hashlib, pathlib, re, sys
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
    "script-src " + h(script),
    "style-src " + h(style),
    "media-src blob:",
    "img-src blob:",
    "worker-src 'self'",
    "connect-src 'none'",
    "font-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
])
page = page.replace("__CSP__", csp)
(app / "index.html").write_text(page, encoding="utf-8")
(app / "sw.js").write_text((here / "sw.js").read_text(encoding="utf-8"), encoding="utf-8")
print(f"Built Watch together {version}{' (small)' if small else ''}: app/index.html {len(page):,} bytes, app/sw.js")
