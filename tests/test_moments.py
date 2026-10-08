"""Checks the moments, the paused title card and the reactions of the Ambient design.

    python3 test_moments.py [screenshot-folder]

Needs Playwright with Chromium and the test media (sh make_test_media.sh).
Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
"""
import asyncio, os, pathlib, sys
from playwright.async_api import async_playwright
from smoke_test import open_page, connect, EPS, MEDIA

SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
results = []
def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail else ''))

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None,
                                          args=['--autoplay-policy=no-user-gesture-required'])
        errors = []
        host, guest = await open_page(browser, errors=errors), await open_page(browser, errors=errors)
        await host.set_viewport_size({'width': 1440, 'height': 900})
        await host.fill('#myName', 'Ana'); await guest.fill('#myName', 'Mihai')
        check('connect page fills the window before connecting', await host.evaluate("document.body.classList.contains('connect-view')"))
        await connect(host, guest)
        check('steps make way for the player once connected', not await host.evaluate("document.body.classList.contains('connect-view')"))
        for page in (host, guest):
            await page.click('#matchBtn')
        await asyncio.sleep(0.4)
        for page in (host, guest):
            await page.click('[data-tab=playlist]'); await page.set_input_files('#files', EPS)
        await asyncio.sleep(1.5)
        check('seats show who is here', await host.text_content('#seatsLabel') == 'Send Mihai —' and await host.is_visible('#reacts'))
        await host.click('#playBtn'); await asyncio.sleep(1.5)
        await guest.click('.react:has-text("Ha!")'); await asyncio.sleep(0.5)
        check('reaction floats as a word in their colour', await host.evaluate("!!document.querySelector('#floats .float.them')"),
              await host.evaluate("(document.querySelector('#floats .float') || {}).textContent"))
        await host.click('[data-tab=chat]')
        await host.fill('#chatInput', 'look at the lights'); await host.press('#chatInput', 'Enter'); await asyncio.sleep(0.6)
        pins_h = await host.evaluate("document.querySelectorAll('#pins .pin').length")
        pins_g = await guest.evaluate("document.querySelectorAll('#pins .pin').length")
        check('moments are pinned on both timelines', pins_h >= 1 and pins_g >= 1, f'{pins_h} and {pins_g} pins')
        chip = await guest.evaluate("(document.querySelector('#chatLog .at') || {}).textContent || ''")
        check('chat messages say when they were said', chip.startswith('at 0:0'), chip)
        await asyncio.sleep(1)
        await guest.click('#playBtn'); await asyncio.sleep(1.4)
        card = await host.is_visible('#pauseCard')
        who = await host.text_content('#pcWhoText')
        check('paused title card says who paused', card and who.startswith('Mihai paused at'), who)
        n = await host.evaluate("document.querySelectorAll('#pcList .moment').length")
        check('the card lists the moments so far', n == 2, f'{n} moments')
        nxt = await host.evaluate("Array.from(document.querySelectorAll('#pcNext .pc-tile-name'), e => e.textContent)")
        check('up next shows the following episodes', nxt[:1] == ['Demo.S01E02'], ', '.join(nxt))
        if SHOTS:
            await host.mouse.move(10, 10)
            await host.screenshot(path=str(SHOTS / 'moments-paused.png'))
        t_before = await guest.evaluate("document.getElementById('v').currentTime")
        await host.locator('#pcList .moment').first.click(); await asyncio.sleep(0.8)
        t_h = await host.evaluate("document.getElementById('v').currentTime")
        t_g = await guest.evaluate("document.getElementById('v').currentTime")
        check('tapping a moment takes both of you back there', t_h < t_before and abs(t_h - t_g) < 0.3, f'{t_before:.1f} -> {t_h:.1f} / {t_g:.1f}')
        await host.fill('#pcInput', 'wait for it'); await host.press('#pcInput', 'Enter'); await asyncio.sleep(0.6)
        bubbles = await guest.eval_on_selector_all('#chatLog .bubble', 'e => e.map(x => x.textContent)')
        check('saying something on the card sends it as a message', any('wait for it' in b for b in bubbles))
        await host.click('#pcResume'); await asyncio.sleep(1.2)
        check('resume from the card plays for both', not await guest.evaluate("document.getElementById('v').paused") and await host.is_hidden('#pauseCard'))
        # Day and night
        await host.click('[data-tab=settings]'); await host.select_option('#themeSel', 'day')
        check('day look can be chosen', await host.evaluate("document.documentElement.dataset.theme") == 'day')
        await host.select_option('#themeSel', 'night')
        check('night look can be chosen', await host.evaluate("document.documentElement.dataset.theme") == 'night')
        check('no page errors', not errors, '; '.join(errors)[:160])
        await browser.close()
    print(f'\n{sum(results)} of {len(results)} checks passed')
    sys.exit(0 if all(results) else 1)

asyncio.run(main())
