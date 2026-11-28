// Cloudflare Pages Function: POST /api/ev
// First-party, anonymous page analytics for the admin dashboard (/admin/). What a page sends, and all it can send:
//   {k: "pv" | "hb" | "print" | "share" | "stk" | "dl", p: public page path, c: source category, d: "m" | "t" | "d", v: random page-view id}
// Nothing else is accepted. No cookie, no IP, no user agent, no full referrer, no query string and nothing a visitor typed
// is stored. `v` is a random number made fresh on every page opening and never saved in the browser; it only lets a
// heartbeat ("the page is still open") find its page view, so the dashboard can count pages open right now.
// Raw events are kept 30 days; daily totals are kept for trends. Pages do not send anything when the browser asks
// not to be tracked (Do Not Track / Global Privacy Control), for automated browsers, or from an admin's own browser.
// Needs the D1 binding DB (the same database as /api/yachad). Without it the answer is 204 and nothing is stored.
// Tests: node tools/test-analytics.mjs

const KINDS = new Set(["pv", "hb", "print", "share", "stk", "dl"]);
// "stk" (a sticker sent) and "dl" (a sticker or the whole pack downloaded) name the sticker, never the person:
// their path is /stickers/<sticker>/ or /stickers/all/, and no other kind may use such a path
const STICKER = /^\/stickers\/(?:[a-z]{2,16}(?:-[a-z]{2,16}){0,3})\/$/;
const STK_KINDS = new Set(["stk", "dl"]);
const PATH = /^\/(?:[a-z0-9][a-z0-9\-\/]{0,90}\/|#[a-z]{1,12})?$/;          // "/", "/#tehillim" (the app), "/siddur/mizrach/"
const CHANNEL = /^(?:direct|internal|referral|(?:ai|search|social):[a-z]{1,16}|utm:[a-z0-9_-]{1,24})$/;
const DEVICE = /^[mtd]$/;
const VIEW = /^[a-z0-9]{4,12}$/;
const BOT = /bot|crawl|spider|slurp|lighthouse|headless|preview|facebookexternalhit|whatsapp|python|curl|wget|httpclient|java\//i;
const MAX_BODY = 400;
const MAX_PATHS_PER_DAY = 3000;          // the site has about 1,400 pages; made-up addresses stop here
const RAW_DAYS = 30;
const LIVE_SECONDS = 3600;

let ready = null;
export const ensureAnalytics = db => ready || (ready = db.batch([
  db.prepare("create table if not exists ev (t integer not null, k text not null, p text not null, c text not null, d text not null)"),
  db.prepare("create index if not exists ev_t on ev (t)"),
  db.prepare("create table if not exists live (v text primary key, p text not null, c text not null, d text not null, s integer not null, t integer not null)"),
  db.prepare("create index if not exists live_t on live (t)"),
  db.prepare("create table if not exists day (day text not null, k text not null, p text not null, c text not null, d text not null, n integer not null default 0, primary key (day, k, p, c, d))")
]).catch(e => { ready = null; throw e; }));

const done = () => new Response(null, { status: 204, headers: { "cache-control": "no-store" } });

export async function onRequest({ request, env }) {
  if (request.method !== "POST") return new Response(null, { status: 405, headers: { allow: "POST" } });
  const db = env && env.DB;
  if (!db) return done();
  const url = new URL(request.url);
  const origin = request.headers.get("origin");
  if (origin && origin !== url.origin) return new Response(null, { status: 403 });
  if (BOT.test(request.headers.get("user-agent") || "")) return done();
  let e;
  try {
    const text = await request.text();
    if (text.length > MAX_BODY) return new Response(null, { status: 413 });
    e = JSON.parse(text);
  } catch (err) { return new Response(null, { status: 400 }); }
  if (!e || typeof e !== "object" || Array.isArray(e)) return new Response(null, { status: 400 });
  const keys = Object.keys(e);
  if (keys.some(k => !["k", "p", "c", "d", "v"].includes(k))) return new Response(null, { status: 400 });   // no extra fields, ever
  const { k, p, c, d, v } = e;
  if (!KINDS.has(k) || typeof p !== "string" || !PATH.test(p) || p.startsWith("/api/") || p.startsWith("/admin/") || (p.startsWith("/y/") && p !== "/y/")
      || STK_KINDS.has(k) !== STICKER.test(p)
      || typeof c !== "string" || !CHANNEL.test(c) || typeof d !== "string" || !DEVICE.test(d) || typeof v !== "string" || !VIEW.test(v)) {
    return new Response(null, { status: 400 });
  }
  const nowMs = typeof env.NOW === "function" ? env.NOW() : Date.now();
  const t = Math.floor(nowMs / 1000), day = new Date(nowMs).toISOString().slice(0, 10);
  try {
    await ensureAnalytics(db);
    if (k === "hb") {                        // a heartbeat only refreshes a page view that was really opened
      await db.prepare("update live set t = ?1 where v = ?2 and t > ?3").bind(t, v, t - LIVE_SECONDS).run();
      return done();
    }
    const known = await db.prepare("select 1 as x from day where day = ?1 and p = ?2 limit 1").bind(day, p).first();
    if (!known) {
      const n = await db.prepare("select count(distinct p) as n from day where day = ?1").bind(day).first();
      if (n && n.n >= MAX_PATHS_PER_DAY) return done();
    }
    const writes = [
      db.prepare("insert into ev (t, k, p, c, d) values (?1, ?2, ?3, ?4, ?5)").bind(t, k, p, c, d),
      db.prepare("insert into day (day, k, p, c, d, n) values (?1, ?2, ?3, ?4, ?5, 1) on conflict (day, k, p, c, d) do update set n = n + 1").bind(day, k, p, c, d)
    ];
    if (k === "pv") writes.push(db.prepare("insert into live (v, p, c, d, s, t) values (?1, ?2, ?3, ?4, ?5, ?5) on conflict (v) do nothing").bind(v, p, c, d, t));
    if ((typeof env.RAND === "function" ? env.RAND() : Math.random()) < 0.02) {          // housekeeping on about one request in fifty
      writes.push(db.prepare("delete from ev where t < ?1").bind(t - RAW_DAYS * 86400));
      writes.push(db.prepare("delete from live where t < ?1").bind(t - LIVE_SECONDS));
    }
    await db.batch(writes);
  } catch (err) { /* analytics must never break a page */ }
  return done();
}
