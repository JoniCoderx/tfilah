// Tfilah.com offline support: the siddur and Tehillim keep working without internet.
// Raise VERSION on every deploy (README, "אפליקציה בטלפון"); that is what tells phones to update.
const VERSION = "tfilah-v27";
const SHELL = VERSION;              // the app and its prayer texts; replaced as a whole on every VERSION
const PAGES = "tfilah-pages";       // static reading pages (/tehillim/23/ ...) the reader has opened
const EXT = "tfilah-ext-v1";        // fonts and libraries from other hosts (their URLs carry a version)
const KEEP = [SHELL, PAGES, EXT];
const MAX_PAGES = 100;              // 960 pages exist; only the last 100 opened are kept
const MAX_EXT = 80;
const NET_TIMEOUT = 4000;           // weak signal: after 4 s use the saved copy, if there is one

// Must all exist: one missing file fails the whole install. "/" is the app (index.html);
// "/index.html" is not listed because Cloudflare Pages answers it with a redirect to "/".
const CORE = ["/", "/config.js", "/shim.js", "/manifest.webmanifest",
  "/data/index.json", "/data/tehillim.json", "/data/books.json", "/icons/icon-192.png", "/brand/favicon.svg"];

const EXT_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net"];
const STATIC_PAGE = /^\/(tehillim|tefila|sefer|kelim|tehillim-yachad)(\/|$)/;

// A response is stored only if it is a complete, successful one. Redirected responses are
// rebuilt, because a browser refuses a "redirected" response as the answer to a page navigation.
const storable = res => res && res.status === 200 && (res.type === "basic" || res.type === "cors");
async function clean(res) {
  if (!res.redirected) return res;
  return new Response(await res.blob(), { status: res.status, statusText: res.statusText, headers: res.headers });
}
async function put(cacheName, key, res, max) {
  try {
    const cache = await caches.open(cacheName);
    await cache.put(key, await clean(res));
    if (max) {
      const keys = await cache.keys();
      for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);   // oldest first
    }
  } catch (e) { /* storage full or blocked: the site still works online */ }
}

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    // "reload" skips the browser's HTTP cache, so a new VERSION never pins an old file
    await Promise.all(CORE.map(async url => {
      const res = await fetch(new Request(url, { cache: "reload" }));
      if (!storable(res)) throw new Error("precache failed: " + url + " " + res.status);
      await cache.put(url, await clean(res));
    }));
    // The nusach texts the reader already had offline (data/ashkenaz.json ...) must survive the
    // update: fetch them fresh, and if that fails carry the old copy over.
    for (const name of await caches.keys()) {
      if (KEEP.includes(name) || !name.startsWith("tfilah-")) continue;
      const old = await caches.open(name);
      for (const req of await old.keys()) {
        const u = new URL(req.url);
        if (u.origin !== location.origin || !u.pathname.startsWith("/data/") || await cache.match(u.pathname)) continue;
        try {
          const res = await fetch(new Request(u.pathname, { cache: "reload" }));
          if (!storable(res)) throw new Error("status " + res.status);
          await cache.put(u.pathname, await clean(res));
        } catch (err) {
          const prev = await old.match(req);
          if (storable(prev)) await cache.put(u.pathname, prev);
        }
      }
    }
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(n => n.startsWith("tfilah-") && !KEEP.includes(n)).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

// Network first. When a saved copy exists and the network is slow, the copy wins after NET_TIMEOUT.
// Resolves to { res, fromNet } or null when neither network nor copy is available.
async function networkFirst(request, cacheName, key, max) {
  const cache = await caches.open(cacheName);
  const saved = await cache.match(key);
  const net = fetch(request).then(res => {
    if (storable(res)) put(cacheName, key, res.clone(), max);
    return res;
  });
  if (!saved) {
    try { return { res: await net, fromNet: true }; } catch (e) { return null; }
  }
  let timer;
  const slow = new Promise(resolve => { timer = setTimeout(() => resolve(null), NET_TIMEOUT); });
  try {
    const res = await Promise.race([net, slow]);
    if (res) return { res, fromNet: true };
  } catch (e) { /* offline */ } finally { clearTimeout(timer); }
  net.catch(() => {});
  return { res: saved, fromNet: false };
}

// Saved copy at once, refreshed in the background for next time.
async function staleWhileRevalidate(e, request, cacheName, key, max) {
  const cache = await caches.open(cacheName);
  const saved = await cache.match(key);
  const net = fetch(request).then(res => {
    if (storable(res)) return put(cacheName, key, res.clone(), max).then(() => res);
    return res;
  });
  if (saved) { e.waitUntil(net.catch(() => {})); return saved; }
  return net;
}

async function cacheFirst(request, cacheName, key, max) {
  const cache = await caches.open(cacheName);
  const saved = await cache.match(key);
  if (saved) return saved;
  const res = await fetch(request);
  if (storable(res)) put(cacheName, key, res.clone(), max);
  return res;
}

// Where the same text lives inside the app, for a static page that was never opened online.
// null when the app would need a file that is not saved on this device.
async function appEquivalent(pathname) {
  const shell = await caches.open(SHELL);
  if (!await shell.match("/")) return null;
  let m;
  if ((m = pathname.match(/^\/tehillim\/(\d{1,3})\/?$/))) return "/#t-" + m[1];
  if (/^\/tehillim\/?$/.test(pathname)) return "/#tehillim";
  if (/^\/tefila\/?$/.test(pathname)) return "/#siddur";
  if (/^\/sefer\/?$/.test(pathname)) return "/#sifriya";
  if (/^\/kelim\/?$/.test(pathname)) return "/#kelim";
  if (/^\/tehillim-yachad\/?$/.test(pathname)) return "/#zikaron";
  if ((m = pathname.match(/^\/tefila\/(([a-z]+)-\d+)\/?$/))) return await shell.match("/data/" + m[2] + ".json") ? "/#p-" + m[1] : null;
  if ((m = pathname.match(/^\/sefer\/([a-z]+)\/?$/))) return "/#b-" + m[1];
  return null;
}

function offlinePage() {
  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>אין חיבור לאינטרנט · תפילה</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#FBF7F5;color:#2B1A1F;font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif;line-height:1.7}
main{max-width:30rem;padding:2rem 1.5rem;text-align:center}h1{font-size:1.5rem;margin:0 0 .75rem}p{margin:0 0 1.25rem}
a,button{display:inline-block;margin:.25rem;padding:.7rem 1.4rem;border-radius:999px;border:1px solid #2B1A1F;font:inherit;text-decoration:none;cursor:pointer}
a{background:#2B1A1F;color:#FBF7F5}button{background:transparent;color:#2B1A1F}</style></head>
<body><main><h1>אין כרגע חיבור לאינטרנט</h1>
<p>הדף הזה עוד לא נשמר במכשיר, ולכן אי אפשר להציג אותו בלי חיבור. הסידור והתהילים שבאפליקציה זמינים גם עכשיו.</p>
<a href="/">לסידור ולתהילים</a><button type="button" id="again">לנסות שוב</button></main>
<script>document.getElementById("again").onclick=function(){location.reload()};addEventListener("online",function(){location.reload()})</script>
</body></html>`;
  return new Response(html, { status: 503, statusText: "Offline",
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}

async function navigate(e) {
  const request = e.request, url = new URL(request.url);
  // The app: one saved copy under "/", whatever the query string says.
  if (url.pathname === "/" || url.pathname === "/index.html") {
    const got = await networkFirst(request, SHELL, "/");
    return got ? got.res : offlinePage();
  }
  // Static reading pages: saved when opened, so they can be reopened offline as themselves.
  if (STATIC_PAGE.test(url.pathname)) {
    const key = url.pathname.endsWith("/") ? url.pathname : url.pathname + "/";
    const got = await networkFirst(request, PAGES, key, MAX_PAGES);
    if (got) return got.res;
    const inApp = await appEquivalent(url.pathname);
    return inApp ? Response.redirect(inApp, 302) : offlinePage();
  }
  // Anything else (sitemap, unknown paths): network only, with a readable page when offline.
  try { return await fetch(request); } catch (err) { return offlinePage(); }
}

self.addEventListener("fetch", e => {
  const request = e.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.protocol !== "https:" && url.protocol !== "http:") return;

  if (url.origin === location.origin) {
    if (url.pathname.startsWith("/api/")) return;                  // AI: always live, never saved
    if (request.mode === "navigate") { e.respondWith(navigate(e)); return; }
    if (request.headers.has("range")) return;
    if (url.pathname.startsWith("/data/")) {                       // prayer texts
      e.respondWith(staleWhileRevalidate(e, request, SHELL, url.pathname));
      return;
    }
    // the app's own small files: fresh when possible, saved copy when not
    if (CORE.includes(url.pathname) || url.pathname.startsWith("/icons/") || url.pathname.startsWith("/brand/")) {
      e.respondWith(networkFirst(request, SHELL, url.pathname).then(got => got ? got.res : Response.error()));
    }
    return;                                                        // everything else: the browser's default
  }

  // Supabase (shared readings, candles) and every host not listed below: always live, never saved.
  if (!EXT_HOSTS.includes(url.hostname)) return;
  // Fonts and libraries. Asked for with CORS so the real status is visible: an error page is
  // never saved, and nothing is stored as an "opaque" response (those cost megabytes of quota each).
  const cors = new Request(url.href, { mode: "cors", credentials: "omit" });
  if (url.hostname === "fonts.googleapis.com") e.respondWith(staleWhileRevalidate(e, cors, EXT, url.href, MAX_EXT));
  else e.respondWith(cacheFirst(cors, EXT, url.href, MAX_EXT));
});
