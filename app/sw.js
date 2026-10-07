// Watch together: offline copy and notification helper (service worker).
// Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
//
// Only used when the app is opened from a web address (http or https), not as a file.
// - Keeps a copy of the app's own files, so the installed app opens without internet.
//   It always tries the network first, so you get updates as soon as they're published.
// - Shows notifications and brings the app back when one is tapped.
// It never stores or sees your videos, music or chat, and only fetches the app's own files.
const VERSION = '1.5.0';
const PREFIX = 'watch-together-';
const CACHE = PREFIX + VERSION;
const FILES = ['./', 'index.html', 'audio-decoder.js', 'manifest.webmanifest',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE)
    .then((c) => Promise.all(FILES.map((f) => c.add(new Request(f, { cache: 'reload' })).catch(() => {}))))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k.startsWith(PREFIX) && k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || !req.url.startsWith(self.registration.scope)) return;
  e.respondWith(fetch(req).then((res) => {
    if (res.ok && res.type === 'basic') {
      const copy = res.clone();
      e.waitUntil(caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {}));
    }
    return res;
  }).catch(() => caches.match(req, { ignoreSearch: true })
    .then((hit) => hit || (req.mode === 'navigate' ? caches.match('./') : undefined))
    .then((hit) => hit || Response.error())));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const tag = e.notification.tag;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const c of list) { c.postMessage({ type: 'open', tag }); if ('focus' in c) return c.focus(); }
    return self.clients.openWindow ? self.clients.openWindow('./') : undefined;
  }));
});
