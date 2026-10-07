"""Automated smoke test for Watch together: two browser windows connect and use the main features.

    sh make_test_media.sh                # once, needs ffmpeg
    pip install playwright && python -m playwright install chromium
    python3 smoke_test.py                # tests ../app/index.html

Set CHROMIUM=/path/to/chrome to use a specific browser. Exits with code 1 if anything fails.
Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
"""
import asyncio, os, pathlib, sys
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
APP = (HERE.parent / 'app' / 'index.html').as_uri()
MEDIA = HERE / 'media'
EPS = [str(MEDIA / f'Demo.S01E0{i}.webm') for i in (1, 2, 3)] + [str(MEDIA / 'Demo.S01E01.en.srt')]
results = []

def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail else ''))

async def open_page(browser, strict=False, errors=None):
    ctx = await browser.new_context(viewport={'width': 1360, 'height': 900}, bypass_csp=not strict)
    page = await ctx.new_page()
    if errors is not None:
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    await page.goto(APP)
    await page.locator('#termsAccept').click()                       # first-launch notice
    await page.locator('#terms').wait_for(state='hidden')
    await page.click('label:has(input[name=where][value=local])')     # both windows are on this machine
    await page.uncheck('#stun')                                       # no internet needed for the test
    return page

async def connect(host, guest):
    await host.click('#startBtn')
    await host.wait_for_function("document.getElementById('offerOut').value.length > 0", timeout=20000)
    await guest.click('#joinBtn')
    await guest.fill('#offerIn', await host.input_value('#offerOut'))  # the whole message, as people paste it
    await guest.click('#replyBtn')
    await guest.wait_for_function("document.getElementById('answerOut').value.length > 0", timeout=20000)
    await host.fill('#answerIn', await guest.input_value('#answerOut'))
    await host.click('#connectBtn')
    for p in (host, guest):
        await p.wait_for_function("document.getElementById('status').textContent === 'Connected'", timeout=20000)

STATE = "(() => { const v = document.getElementById('v'); return [document.getElementById('nowTitle').textContent, v.currentTime, v.paused, !!v.srcObject]; })()"

async def main():
    if not MEDIA.exists():
        sys.exit('Run "sh make_test_media.sh" first.')
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None,
                                          args=['--autoplay-policy=no-user-gesture-required'])
        errors = []
        host, guest = await open_page(browser, errors=errors), await open_page(browser, errors=errors)
        await host.fill('#myName', 'Host'); await guest.fill('#myName', 'Guest')
        await connect(host, guest)
        await asyncio.sleep(0.8)
        check('connect with copy-pasted messages', True)
        sh, sg = await host.text_content('#safety'), await guest.text_content('#safety')
        check('both sides show the same safety code', sh == sg and sh.strip() != '— — —', sh)

        # both have the files: local playback in sync
        for page in (host, guest):
            await page.click('[data-tab=playlist]'); await page.set_input_files('#files', EPS)
        await asyncio.sleep(2)
        await host.click('#playBtn'); await asyncio.sleep(2.5)
        h, g = await host.evaluate(STATE), await guest.evaluate(STATE)
        check('playback starts on both', not h[2] and not g[2] and h[0] == g[0], f'{h[0]}')
        check('positions within 0.5 s', abs(h[1] - g[1]) < 0.5, f'{abs(h[1] - g[1]):.2f} s apart')
        check('subtitles shown', 'Hello there' in (await guest.text_content('#subtitle')))
        await guest.click('#playBtn'); await asyncio.sleep(1)
        check('pause from the other side', (await host.evaluate(STATE))[2])

        # chat opens after both confirm the safety code
        for page in (host, guest):
            await page.click('[data-tab=connect]'); await page.click('#matchBtn')
        await host.click('[data-tab=chat]'); await guest.click('[data-tab=chat]')
        await host.fill('#chatInput', 'hello <b>not html</b>'); await host.press('#chatInput', 'Enter')
        await asyncio.sleep(0.6)
        bubbles = await guest.eval_on_selector_all('#chatLog .bubble', 'e => e.map(x => x.textContent)')
        bold = await guest.evaluate("document.querySelectorAll('#chatLog b').length")
        check('chat message arrives as plain text', any('hello <b>not html</b>' in b for b in bubbles) and bold == 0)

        # streaming to someone without the files
        third = await open_page(browser, errors=errors)
        host2 = await open_page(browser, errors=errors)
        await connect(host2, third)
        await host2.click('[data-tab=playlist]'); await host2.set_input_files('#files', EPS[:1])
        await asyncio.sleep(1.2); await host2.click('#playBtn'); await asyncio.sleep(4)
        t = await third.evaluate(STATE)
        frames = await third.evaluate("document.getElementById('v').getVideoPlaybackQuality().totalVideoFrames")
        check('streams to someone without the file', t[3] and frames > 10, f'{frames} frames received')

        # strict security policy: the real page runs with no violations
        strict_errors = []
        strict = await open_page(browser, strict=True, errors=strict_errors)
        await strict.click('[data-tab=playlist]'); await strict.set_input_files('#files', EPS[:1])
        await asyncio.sleep(1); await strict.click('#playBtn'); await asyncio.sleep(1.5)
        check('runs under its strict security policy', not strict_errors, '; '.join(strict_errors)[:120])

        # sound the browser can't play (AC-3, DTS) is converted by the built-in decoder
        await strict.set_input_files('#files', [str(MEDIA / 'Demo.Surround.mkv')])
        await strict.locator('.pl-main', has_text='Surround').click()
        try:
            await strict.locator('#audioNote', has_text='Converted').wait_for(timeout=15000)
            tracks = await strict.eval_on_selector_all('#audioTrack option', 'e => e.map(o => o.textContent)')
            check('converts AC-3 / DTS sound', len(tracks) == 2 and await strict.evaluate("document.getElementById('v').muted"), ' | '.join(tracks))
        except Exception as e:
            check('converts AC-3 / DTS sound', False, str(e)[:120])
        check('converter runs under the strict security policy', not strict_errors, '; '.join(strict_errors)[:120])

        check('no page errors', not errors, '; '.join(errors)[:160])
        await browser.close()
    print(f'\n{sum(results)} of {len(results)} checks passed')
    sys.exit(0 if all(results) else 1)

asyncio.run(main())
