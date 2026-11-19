// Tfilah.com offline support: the siddur and Tehillim keep working without internet.
const VERSION = "tfilah-v15";
const CORE = ["/", "/index.html", "/config.js", "/shim.js", "/manifest.webmanifest",
  "/data/index.json", "/data/tehillim.json", "/data/books.json", "/icons/icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/api/")) return;              // AI: always live
  if (url.hostname.endsWith("supabase.co")) return;           // candles: always live

  // prayer texts and fonts: cache first, they rarely change
  if (url.pathname.startsWith("/data/") || url.hostname.includes("gstatic") || url.hostname.includes("googleapis") || url.hostname.includes("jsdelivr")) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
      if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); }
      return res;
    })));
    return;
  }
  // the page itself: network first, fall back to cache when offline
  if (url.origin === location.origin) {
    e.respondWith(fetch(e.request).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request).then(hit => hit || caches.match("/index.html"))));
  }
});
