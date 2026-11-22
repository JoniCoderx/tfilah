// How many times a page was opened. One row per page address, one number. Nothing about the visitor is stored:
// no IP, no cookie, no identifier. The browser reports a page once per visit (sessionStorage), so a reload is not a second opening.
//   POST /api/views {p:"/perek-shira/"}  -> counts one opening, answers {n}
//   GET  /api/views?p=/perek-shira/      -> answers {n} without counting
// Needs the D1 binding `DB` (the same database as /api/yachad). Without it the answer is {n:0} and the page shows nothing.

const PATH = /^\/[a-z0-9][a-z0-9\-\/]{0,90}\/$/;
const BOT = /bot|crawl|spider|slurp|lighthouse|headlesschrome|preview|facebookexternalhit|whatsapp/i;
const MAX_ROWS = 3000;            // the site has about 1,100 pages; a flood of made-up addresses stops here
const H = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const out = (n, status = 200) => new Response(JSON.stringify({ n }), { status, headers: H });

let ready = null;
const ensure = db => ready || (ready = db.prepare("create table if not exists views (path text primary key, n integer not null default 0)").run().catch(e => { ready = null; throw e; }));

export async function onRequest({ request, env }) {
  const db = env && env.DB;
  if (!db) return out(0, 503);
  const url = new URL(request.url);
  const post = request.method === "POST";
  if (!post && request.method !== "GET") return out(0, 405);
  let p = url.searchParams.get("p") || "";
  if (post) { try { p = String((await request.json()).p || ""); } catch (e) { p = ""; } }
  if (!PATH.test(p) || p.startsWith("/api/") || p.startsWith("/y/")) return out(0, 400);
  try {
    await ensure(db);
    if (post) {
      const origin = request.headers.get("origin");
      const bot = BOT.test(request.headers.get("user-agent") || "");
      if (!bot && (!origin || origin === url.origin)) {
        const row = await db.prepare("select n from views where path = ?1").bind(p).first();
        let ok = !!row;
        if (!row) {                 // a new address is counted only if it is a real page, and only while the table is small
          const c = await db.prepare("select count(*) as c from views").first();
          ok = (c ? c.c : 0) < MAX_ROWS;
          if (ok && env.ASSETS) { try { const r = await env.ASSETS.fetch(new URL(p, url.origin)); ok = r.status === 200; } catch (e) { ok = false; } }
        }
        if (ok) await db.prepare("insert into views (path, n) values (?1, 1) on conflict(path) do update set n = n + 1").bind(p).run();
      }
    }
    const r = await db.prepare("select n from views where path = ?1").bind(p).first();
    return out(r ? r.n : 0);
  } catch (e) {
    return out(0, 500);
  }
}
