// Cloudflare Pages Function: the admin dashboard's server side (/admin/ is the page).
//   POST /api/admin/login   {email, password}  -> sets a signed session cookie (HttpOnly, Secure, SameSite=Strict, 12 hours)
//   POST /api/admin/logout                     -> clears it
//   GET  /api/admin/data?q=me|live|trend|audit|status&days=7|30|90
// Every data request checks the session; there is no anonymous answer and no public registration.
//
// The login lives in Cloudflare secrets, never in the repository (Pages -> Settings -> Variables and Secrets):
//   ADMIN_EMAIL     the one super admin address, e.g. admin@tfilah.com
//   ADMIN_PASSWORD  at least 12 characters; changing it signs every session out
// Until both are set, login answers 503 "not configured".
// Failed logins are limited per address (8 in 15 minutes), using a keyed hash of the IP that is kept 1 day.
// Tests: node tools/test-analytics.mjs

import { ensureAnalytics } from "../ev.js";

const SITE = "https://tfilah.com";
const SESSION_HOURS = 12;
const FAIL_LIMIT = 8, FAIL_WINDOW = 15 * 60;
const BASELINE = { commit: "2d4fe6bd8787d11f9d7975a4bf689b1473c8992c", date: "2026-11-27", note: "SEO as it was before the admin and analytics work" };
const INDEXNOW_KEY = "6b8fa3ba14982f01f78af96dab6e238c";
const J = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex, nofollow" };
const json = (o, s = 200, h = {}) => new Response(JSON.stringify(o), { status: s, headers: { ...J, ...h } });
const enc = new TextEncoder();
const b64u = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const fromB64u = s => atob(s.replace(/-/g, "+").replace(/_/g, "/"));

async function hmacKey(env) {
  const raw = await crypto.subtle.digest("SHA-256", enc.encode("tfilah-admin|" + env.ADMIN_PASSWORD + "|" + (env.ADMIN_SESSION_SECRET || "")));
  return crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}
const sign = async (key, s) => b64u(await crypto.subtle.sign("HMAC", key, enc.encode(s)));
async function same(key, a, b) {             // constant-time comparison: compare keyed digests, not the strings
  const [x, y] = await Promise.all([sign(key, "c|" + a), sign(key, "c|" + b)]);
  let d = x.length ^ y.length;
  for (let i = 0; i < Math.min(x.length, y.length); i++) d |= x.charCodeAt(i) ^ y.charCodeAt(i);
  return d === 0;
}
const configured = env => !!(env && env.ADMIN_EMAIL && env.ADMIN_PASSWORD && String(env.ADMIN_PASSWORD).length >= 12);
const nowMs = env => (typeof env.NOW === "function" ? env.NOW() : Date.now());

async function session(request, env) {
  if (!configured(env)) return null;
  const m = (request.headers.get("cookie") || "").match(/(?:^|;\s*)tf_admin=([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)/);
  if (!m) return null;
  const [payload, sig] = m[1].split(".");
  const key = await hmacKey(env);
  if (!(await same(key, sig, await sign(key, payload)))) return null;
  try {
    const p = JSON.parse(fromB64u(payload));
    if (p.e !== String(env.ADMIN_EMAIL).toLowerCase() || !(p.x > nowMs(env))) return null;
    return p;
  } catch (e) { return null; }
}

async function audit(db, env, action, ok) {
  try {
    await db.batch([
      db.prepare("create table if not exists admin_audit (t integer not null, action text not null, ok integer not null)"),
      db.prepare("insert into admin_audit (t, action, ok) values (?1, ?2, ?3)").bind(Math.floor(nowMs(env) / 1000), action, ok ? 1 : 0)
    ]);
  } catch (e) { /* the audit log must not block a login */ }
}

async function login(request, env) {
  if (!configured(env)) return json({ error: "not configured" }, 503);
  const url = new URL(request.url), origin = request.headers.get("origin");
  if (origin && origin !== url.origin) return json({ error: "forbidden" }, 403);
  const db = env.DB, key = await hmacKey(env), t = Math.floor(nowMs(env) / 1000);
  const who = await sign(key, "ip|" + (request.headers.get("cf-connecting-ip") || "unknown") + "|" + new Date(nowMs(env)).toISOString().slice(0, 10));
  if (db) {
    await db.prepare("create table if not exists admin_fail (h text not null, t integer not null)").run();
    const f = await db.prepare("select count(*) as n from admin_fail where h = ?1 and t > ?2").bind(who, t - FAIL_WINDOW).first();
    if (f && f.n >= FAIL_LIMIT) return json({ error: "too many attempts" }, 429, { "retry-after": String(FAIL_WINDOW) });
  }
  let b = {};
  try { b = await request.json(); } catch (e) { /* treated as empty */ }
  const email = String(b.email || "").trim().toLowerCase(), password = String(b.password || "");
  const ok = (await same(key, email, String(env.ADMIN_EMAIL).toLowerCase())) & (await same(key, password, String(env.ADMIN_PASSWORD)));
  if (!ok) {
    if (db) await db.batch([
      db.prepare("insert into admin_fail (h, t) values (?1, ?2)").bind(who, t),
      db.prepare("delete from admin_fail where t < ?1").bind(t - 86400)
    ]);
    if (db) await audit(db, env, "login", false);
    await new Promise(r => setTimeout(r, 400));
    return json({ error: "wrong email or password" }, 401);
  }
  const payload = b64u(enc.encode(JSON.stringify({ e: email, x: nowMs(env) + SESSION_HOURS * 3600e3 })));
  if (db) await audit(db, env, "login", true);
  return json({ ok: true, email }, 200, {
    "set-cookie": `tf_admin=${payload}.${await sign(key, payload)}; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_HOURS * 3600}`
  });
}

// ---------- data ----------
async function live(db, env) {
  await ensureAnalytics(db);
  const t = Math.floor(nowMs(env) / 1000), q = (sql, ...a) => db.prepare(sql).bind(...a);
  const cnt = async (from) => ((await q("select count(*) as n from ev where k = 'pv' and t > ?1", t - from).first()) || {}).n || 0;
  const [active, pages, channels, devices, recent, series, last] = await Promise.all([
    q("select count(*) as n from live where t > ?1", t - 300).first(),
    q("select p, count(*) as n from live where t > ?1 group by p order by n desc limit 12", t - 300).all(),
    q("select c, count(*) as n from live where t > ?1 group by c order by n desc", t - 300).all(),
    q("select d, count(*) as n from live where t > ?1 group by d order by n desc", t - 300).all(),
    q("select t, k, p, c, d from ev where t > ?1 order by t desc limit 40", t - 86400).all(),
    q("select (t / 60) * 60 as m, count(*) as n from ev where k = 'pv' and t > ?1 group by m order by m", t - 3600).all(),
    q("select max(t) as t from ev").first()
  ]);
  const pv = { m5: await cnt(300), m15: await cnt(900), m30: await cnt(1800), h24: await cnt(86400) };
  const prev24 = ((await q("select count(*) as n from ev where k = 'pv' and t > ?1 and t <= ?2", t - 172800, t - 86400).first()) || {}).n || 0;
  return { now: t, active: (active && active.n) || 0, pv, prev24, pages: pages.results, channels: channels.results, devices: devices.results,
           recent: recent.results, series: series.results, lastEvent: (last && last.t) || null };
}

async function trend(db, env, days) {
  await ensureAnalytics(db);
  const end = new Date(nowMs(env)), d0 = new Date(end - (days - 1) * 864e5).toISOString().slice(0, 10), p0 = new Date(end - (2 * days - 1) * 864e5).toISOString().slice(0, 10);
  const q = (sql, ...a) => db.prepare(sql).bind(...a).all().then(r => r.results);
  const [daily, pages, channels, devices, events, prev, stickers] = await Promise.all([
    q("select day, sum(n) as n from day where k = 'pv' and day >= ?1 group by day order by day", d0),
    q("select p, sum(n) as n from day where k = 'pv' and day >= ?1 group by p order by n desc limit 50", d0),
    q("select c, sum(n) as n from day where k = 'pv' and day >= ?1 group by c order by n desc", d0),
    q("select d, sum(n) as n from day where k = 'pv' and day >= ?1 group by d order by n desc", d0),
    q("select k, sum(n) as n from day where k != 'pv' and day >= ?1 group by k", d0),
    q("select sum(n) as n from day where k = 'pv' and day >= ?1 and day < ?2", p0, d0),
    q("select k, p, sum(n) as n from day where k in ('stk', 'dl') and day >= ?1 group by k, p order by n desc", d0)
  ]);
  return { days, from: d0, daily, pages, channels, devices, events, stickers, total: daily.reduce((s, r) => s + r.n, 0), previous: (prev[0] && prev[0].n) || 0 };
}

async function seoAudit(env) {
  if (!env.ASSETS) return { error: "assets binding unavailable" };
  const get = async p => { try { const r = await env.ASSETS.fetch(new Request(SITE + p)); return { status: r.status, body: r.status === 200 ? await r.text() : "" }; } catch (e) { return { status: 0, body: "" }; } };
  const sm = await get("/sitemap.xml");
  const urls = [...sm.body.matchAll(/<loc>https:\/\/tfilah\.com(\/[^<]*)<\/loc>/g)].map(m => m[1]);
  const key = ["/", "/siddur/", "/tehillim/", "/tehillim-yachad/", "/ma-mevarchim/", "/zmanei-shabbat/", "/chanukah/", "/perek-shira/"];
  const pick = [...new Set([...key, ...urls.slice().sort(() => Math.random() - 0.5).slice(0, 32)])];
  const issues = [], rows = [];
  for (let i = 0; i < pick.length; i += 8) {
    await Promise.all(pick.slice(i, i + 8).map(async p => {
      const r = await get(p), s = r.body, has = rx => rx.test(s);
      const canon = (s.match(/<link rel="canonical" href="([^"]*)"/) || [])[1] || "";
      const h1 = (s.match(/<h1[ >]/g) || []).length, title = (s.match(/<title>([^<]*)/) || [])[1] || "";
      let ld = 0, bad = 0;
      for (const m of s.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) { ld++; try { JSON.parse(m[1]); } catch (e) { bad++; } }
      const row = { p, status: r.status, title, canonical: canon, h1, ld, noindex: has(/<meta name="robots" content="[^"]*noindex/) };
      rows.push(row);
      const add = (sev, what) => issues.push({ p, sev, what });
      if (r.status !== 200) add("P0", "status " + r.status);
      else {
        if (!title) add("P1", "missing title");
        if (!canon) add("P1", "missing canonical"); else if (canon !== SITE + p && p !== "/") add("P2", "canonical points elsewhere: " + canon);
        if (row.noindex) add("P0", "noindex on a sitemap page");
        if (p !== "/" && h1 !== 1) add("P2", h1 + " H1 elements");
        if (bad) add("P1", bad + " invalid JSON-LD blocks");
      }
    }));
  }
  const robots = (await get("/robots.txt")).body;
  return { checked: rows.length, sitemapUrls: urls.length, robots, blocksAll: /Disallow:\s*\/\s*$/m.test(robots), issues, rows: rows.sort((a, b) => a.p.localeCompare(b.p)) };
}

async function status(db, env) {
  const ok = async p => { try { return env.ASSETS ? (await env.ASSETS.fetch(new Request(SITE + p))).status === 200 : null; } catch (e) { return false; } };
  let dbOk = false, readings = null;
  try { await db.prepare("select 1").first(); dbOk = true; } catch (e) { /* shown as not connected */ }
  try {
    const s = await db.prepare("select coalesce(sum(done), 0) as chapters, count(*) as readings from memorials where hidden = 0").first();
    readings = s || null;
  } catch (e) { /* the shared-reading table may not exist in a test database */ }
  return {
    baseline: BASELINE,
    integrations: [
      { name: "Database (D1)", state: dbOk ? "connected" : "not connected" },
      { name: "Admin login", state: configured(env) ? "configured" : "not configured" },
      { name: "IndexNow", state: (await ok("/" + INDEXNOW_KEY + ".txt")) ? "key published" : "key missing", note: "submissions run with tools/indexnow.py" },
      { name: "Google Search Console", state: "not connected", note: "needs OAuth credentials; open search.google.com/search-console" },
      { name: "Bing Webmaster Tools", state: "not connected", note: "needs an API key; open bing.com/webmasters" },
      { name: "Contact mail (Resend)", state: env.RESEND_API_KEY ? "configured" : "not configured" },
      { name: "Tfilah Mail (inbox)", state: "not built", note: "needs an inbound mail provider; see docs/seo/REQUIRED_CREDENTIALS.md" }
    ],
    readings
  };
}

export async function onRequest(context) {
  const { request, env } = context;
  const path = new URL(request.url).pathname.replace(/\/+$/, "");
  if (path === "/api/admin/login") return request.method === "POST" ? login(request, env) : json({ error: "method" }, 405);
  if (path === "/api/admin/logout") {
    if (request.method !== "POST") return json({ error: "method" }, 405);
    return json({ ok: true }, 200, { "set-cookie": "tf_admin=; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=0" });
  }
  if (path !== "/api/admin/data" || request.method !== "GET") return json({ error: "not found" }, 404);
  if (!configured(env)) return json({ error: "not configured" }, 503);
  const s = await session(request, env);
  if (!s) return json({ error: "unauthorized" }, 401);
  const u = new URL(request.url), q = u.searchParams.get("q"), db = env.DB;
  try {
    if (q === "me") return json({ email: s.e, expires: s.x });
    if (q === "status") return json(await status(db, env));
    if (q === "audit") return json(await seoAudit(env));
    if (!db) return json({ error: "database not connected" }, 503);
    if (q === "live") return json(await live(db, env));
    if (q === "trend") { const d = [7, 30, 90].includes(+u.searchParams.get("days")) ? +u.searchParams.get("days") : 30; return json(await trend(db, env, d)); }
    return json({ error: "unknown query" }, 400);
  } catch (e) {
    return json({ error: "server error" }, 500);
  }
}
