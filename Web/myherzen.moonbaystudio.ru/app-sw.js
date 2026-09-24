// Cache only the public app shell. Account/API responses and credentials never enter CacheStorage.
const CACHE = 'myherzen-shell-20260924-v2';
const FILES = ['/app/', '/app/manifest.json', '/styles.css', '/workspace.css', '/auth.js', '/nav.js', '/client-core.js', '/workspace.js', '/img/logo.png', '/img/icon-192.png', '/img/icon-512.png', '/img/icon-maskable-512.png', '/favicon.ico'];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES))));
self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const key of await caches.keys()) if (key.startsWith('myherzen-shell-') && key !== CACHE) await caches.delete(key);
  await self.clients.claim();
})()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !FILES.includes(url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(event.request);
      if (response.ok) await cache.put(url.pathname, response.clone());
      return response;
    } catch (error) {
      const cached = await cache.match(url.pathname);
      if (cached) return cached;
      throw error;
    }
  })());
});
