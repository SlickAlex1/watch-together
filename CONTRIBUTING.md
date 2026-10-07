# Contributing

Thanks for wanting to help. Bug reports, testing on different phones and browsers, translations and code are all welcome.

## Reporting bugs

Use the **bug report** template under Issues. Include:

- your browser and system (for example "Chrome 130 on Android 14") and the other person's;
- the app version (bottom of the page);
- for connection errors, the text copied by **Copy details for the developer**. It contains no addresses or passwords.

Please don't post invitation or reply codes publicly. Report security problems privately (see [SECURITY.md](SECURITY.md)).

## Making changes

1. Edit **`src/index.template.html`**. It contains the whole app: HTML, CSS and JavaScript, with no build tools or libraries.
2. Rebuild:

       cd src
       python3 build.py

   This writes `app/index.html` with a fresh Content Security Policy (hashes of the inline style and script), and packs `tools/audio-decoder/wt_audio.wasm` with `src/audio-decoder.worker.js` into `app/audio-decoder.js`. An edited `app/index.html` won't run without rebuilding.

   To change the sound converter itself, edit `tools/audio-decoder/wt_audio.c` and run `tools/audio-decoder/build.sh` (see its README), then rebuild as above.
3. Test (see [tests/README.md](tests/README.md)):

       cd tests
       sh make_test_media.sh
       python3 smoke_test.py

## Guidelines

- **No external code or requests:** no libraries, CDNs, fonts, analytics or web requests. The page must keep working under its strict security policy.
- **Treat everything from the other side as untrusted:** validate it, limit its size, and never insert it as HTML (use `textContent`).
- **No real movies, shows or music:** don't put copyrighted titles, posters or clips in code, examples, tests or screenshots. Use the synthetic test media.
- **Plain language:** keep the interface text simple and clear.
- **Version:** raise `APP_VERSION` in the template for each release, and add an entry to [CHANGELOG.md](CHANGELOG.md).

## License

By contributing, you agree that your contributions are licensed under the GNU General Public License v3 or later, like the rest of the project.
