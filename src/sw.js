// Watch together: notification helper.
// Copyright (C) 2026 SlickAlex. Licensed under the GNU GPL v3 or later (see LICENSE).
// Only shows notifications and brings the app back when one is tapped.
// It doesn't cache anything or make network requests.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const tag = e.notification.tag;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const c of list) {
      c.postMessage({ type: 'open', tag });
      if ('focus' in c) return c.focus();
    }
    return undefined;
  }));
});
