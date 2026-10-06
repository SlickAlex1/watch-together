# Security policy

## Reporting a problem

Please **don't open a public issue** for security problems. Instead, use GitHub's private reporting: the **Security** tab of this repository → **Report a vulnerability**. Describe what you found, how to reproduce it, and which browser and app version you used (shown at the bottom of the page).

This is a hobby project maintained in spare time, so replies may take a few days. There is no bug bounty.

## Supported versions

Only the latest release gets fixes. Both people in a session should use the same version.

## What's in scope

- Anything that lets someone read or alter what two connected people share (chat, playback, streams), or connect without the safety codes matching.
- Ways for the other person, or anyone handling an invitation, to run code in your page, read your files or playlist beyond what you share, or obtain your relay password or secret key.
- Bypasses of the page's Content Security Policy.

Out of scope:

- Weaknesses in browsers or relay services themselves.
- Someone who controls your device.
- The other person seeing your IP address without a relay. This is how direct connections work, and it's documented.

## Protections already in place

- **Encryption:** all traffic is end-to-end encrypted by WebRTC (DTLS/SRTP), and a safety code derived from both sides' certificates lets people detect someone in the middle.
- **Content Security Policy:** a strict policy with SHA-256 hashes only allows the app's own code. The page can't load remote content or contact websites.
- **Untrusted messages:** everything from the other side is validated, size-limited and rate-limited, and is never inserted as HTML.
- **Relay access in invitations:** it's encrypted, time-limited and never stored. With TURN REST temporary logins, the password and secret key never leave your device.
