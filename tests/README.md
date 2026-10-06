# Tests

Everything here runs locally, with no internet and no relay account needed.

## Smoke test

Two browser windows connect and check the main features:

- connecting and the safety code;
- synchronised playback, pausing from the other side and subtitles;
- chat (as plain text);
- streaming to someone without the file;
- the strict security policy.

    sh make_test_media.sh                              # once; needs ffmpeg
    pip install playwright
    python -m playwright install chromium
    python3 smoke_test.py

It prints PASS/FAIL for each check and exits with code 1 if anything fails. Set `CHROMIUM=/path/to/chrome` to test a particular browser.

## Test media

`make_test_media.sh` creates `tests/media/` (ignored by git), using only test patterns, tones and generated cover art, nothing copyrighted:

- three short videos with a subtitle file;
- an MP3 with cover art.

## Test relay

`test_relay.py` is a tiny TURN relay for trying the relay features on your own network:

    python3 test_relay.py 192.168.1.20      # your computer's local IP address

Then, in the app:

- **Relay address:** `192.168.1.20:3478`
- **Login:** username `tester`, password `secret`
- **Temporary logins:** secret key `restsecret`

It's for testing only, not for real use.
