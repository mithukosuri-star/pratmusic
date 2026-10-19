/* PratMusic — offline-first service worker.
   Precaches the app shell, library metadata, cover art and bundled audio
   with bounded concurrency so initial page load & playback stay fast.
   Supports zero-copy HTTP Range requests from cache via Blob.slice(). */
const VERSION = 'pratmusic-v6';
const CORE = [
  './', './index.html', './manifest.webmanifest',
  './css/style.css', './js/db.js', './js/online.js', './js/app.js', './library.json', './free-catalog.json',
  './icons/icon-192.png', './icons/icon-512.png', './icons/maskable-512.png'
];

async function cacheInBatches(cache, urls, concurrency = 3) {
  let idx = 0;
  async function worker() {
    while (idx < urls.length) {
      const u = urls[idx++];
      try {
        const hit = await cache.match(u, { ignoreSearch: true });
        if (hit) continue;
        const resp = await fetch(u);
        if (resp.status === 200) await cache.put(u, resp);
      } catch (err) {
        console.warn('[sw] failed to cache', u, err);
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, urls.length) }, () => worker()));
}

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    await cache.addAll(CORE);
    try {
      const res = await fetch('./library.json');
      const lib = await res.json();
      const covers = lib.map((t) => './' + t.cover);
      const audio = lib.map((t) => './' + t.file);
      // Cache small cover images first so UI renders immediately, then audio with low concurrency
      await cacheInBatches(cache, covers, 4);
      await cacheInBatches(cache, audio, 2);
    } catch (err) {
      console.warn('[sw] media precache partial:', err);
    }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', (e) => {
  if (e.data === 'skip-waiting') self.skipWaiting();
});

async function rangedResponse(cached, headers) {
  const range = headers.get('range');
  if (!range) return cached;
  const m = /bytes=(\d*)-(\d*)/.exec(range);
  if (!m) return cached;
  const blob = await cached.blob();
  const size = blob.size;
  if (!size) return cached;
  let start = m[1] === '' ? 0 : parseInt(m[1], 10);
  let end = m[2] === '' ? size - 1 : parseInt(m[2], 10);
  if (m[1] === '' && m[2] !== '') {
    start = Math.max(0, size - parseInt(m[2], 10));
    end = size - 1;
  }
  start = Math.max(0, start);
  end = Math.min(end, size - 1);
  if (start > end) {
    return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
  }
  const ctype = cached.headers.get('Content-Type') || (cached.url.endsWith('.wav') ? 'audio/wav' : 'audio/mpeg');
  const slice = blob.slice(start, end + 1, ctype);
  return new Response(slice, {
    status: 206,
    headers: {
      'Content-Range': `bytes ${start}-${end}/${size}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': String(slice.size),
      'Content-Type': ctype,
      'Access-Control-Allow-Origin': '*'
    }
  });
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  e.respondWith((async () => {
    const cache = await caches.open(VERSION);
    if (url.pathname.endsWith('.html') || url.pathname.endsWith('.js') || url.pathname.endsWith('.css') || url.pathname.endsWith('.json') || req.mode === 'navigate') {
      try {
        const fresh = await fetch(req);
        if (fresh.ok) { await cache.put(req, fresh.clone()); return fresh; }
      } catch { /* use offline copy */ }
    }
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) {
      if (req.headers.has('range')) {
        try { return await rangedResponse(hit, req.headers); } catch (err) { /* fall through */ }
      }
      return hit;
    }
    try {
      const res = await fetch(req);
      if (res.status === 200 && url.origin === self.location.origin) {
        cache.put(req, res.clone());
      }
      return res;
    } catch (err) {
      const fallback = await cache.match(req, { ignoreSearch: true });
      if (fallback) return fallback;
      if (req.mode === 'navigate') return cache.match('./index.html');
      return new Response('offline', { status: 503, statusText: 'Offline' });
    }
  })());
});
