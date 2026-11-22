// Cloudflare Pages Function: /api/yachad
// The shared Psalms reading ("תהילים יחד"), kept in the site's own Cloudflare D1 database.
// Needs a D1 database bound to the Pages project under the name DB
// (Cloudflare Pages -> Settings -> Bindings -> Add -> D1 database -> Variable name: DB).
// The tables are created on first use; nothing has to be run by hand.
// Tests: node tools/test-yachad.mjs
//
//   GET  /api/yachad?list=1              the public list (only readings marked "listed")
//   POST /api/yachad  {fn, args}         fn is one of the six below; the answer is {data}
//
// The rules are the same ones the Postgres version enforced:
//   * a chapter key is  chapter + 150 * (round - 1); a new round opens only when all 150 are done
//   * a claim that was not finished within 24 hours can be taken by someone else
//   * "done" is counted by the server, never taken from the browser
//   * hidden readings (set hidden = 1 in the D1 console) are invisible and cannot be written to
//   * dampers: 30 new readings per 10 minutes for the whole site, 600 candles per hour and
//     3000 finished chapters per hour per reading. A WAF rate limiting rule on this path is the real limit.

const SITE_ORIGINS = ["https://tfilah.com", "https://www.tfilah.com"];
const MAX_BODY_BYTES = 4096;
const DAY_MS = 24 * 3600e3, HOUR_MS = 3600e3;
const KINDS = ["neshama", "refuah", "zivug", "hatzlacha", "general"];
const SCHEMA = [
  `create table if not exists memorials (
     id text primary key, name text not null, parent text not null default '', kind text not null default 'neshama',
     rel text not null, by_name text not null default '', msg text not null default '',
     candles integer not null default 1, done integer not null default 0, hidden integer not null default 0,
     listed integer not null default 0, created_at text not null, candle_win text not null, candle_n integer not null default 0)`,
  `create table if not exists chapters (
     memorial_id text not null, n integer not null, s text not null, by_name text not null default '', at text not null,
     primary key (memorial_id, n))`,
  `create index if not exists memorials_created_at_idx on memorials (created_at desc)`
];
let ready = null;

export async function onRequest(context) {
  try {
    return await handle(context);
  } catch (e) {
    console.error("yachad: unexpected error", e && e.name, e && String(e.message).slice(0, 120));
    return json({ error: "internal error" }, 500);
  }
}

async function handle({ request, env }) {
  if (!env || !env.DB) return json({ error: "not configured" }, 503);
  const db = env.DB;
  if (!ready) ready = db.batch(SCHEMA.map(s => db.prepare(s))).catch(e => { ready = null; throw e; });
  await ready;
  const now = () => new Date(typeof env.NOW === "function" ? env.NOW() : Date.now());

  if (request.method === "GET") {
    const u = new URL(request.url);
    if (!u.searchParams.has("list")) return json({ error: "bad request" }, 400);
    const r = await db.prepare(
      `select id, name, parent, rel, kind, by_name, msg, candles, done, listed, created_at from memorials
        where hidden = 0 and listed = 1 order by created_at desc limit 200`).all();
    return json({ data: (r.results || []).map(pub) }, 200, { "cache-control": "public, max-age=15" });
  }
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405, { allow: "GET, POST" });
  if (!sameSite(request, env)) return json({ error: "forbidden" }, 403);
  const type = (request.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
  if (type !== "application/json") return json({ error: "content-type must be application/json" }, 415);
  const raw = await request.text();
  if (raw.length > MAX_BODY_BYTES) return json({ error: "too long" }, 413);
  let b;
  try { b = JSON.parse(raw); } catch { return json({ error: "bad json" }, 400); }
  const a = (b && typeof b.args === "object" && b.args) || {};
  const fn = FN[b && b.fn];
  if (!fn) return json({ error: "unknown function" }, 400);
  const out = await fn(db, a, now);
  if (out && out.error) return json({ error: out.error }, out.status || 400);
  return json({ data: out === undefined ? null : out });
}

const FN = {
  async create_memorial(db, a, now) {
    const name = clean(a.p_name), parent = clean(a.p_parent), by = clean(a.p_by), msg = clean(a.p_msg);
    const rel = a.p_rel, kind = a.p_kind == null ? "neshama" : a.p_kind;
    if (!name || name.length > 60 || parent.length > 40 || by.length > 60 || msg.length > 200) return { error: "bad fields" };
    if (rel !== "בן" && rel !== "בת") return { error: "bad fields" };
    if (!KINDS.includes(kind)) return { error: "bad fields" };
    const t = now(), since = new Date(t - 10 * 60e3).toISOString();
    const c = await db.prepare(`select count(*) as c from memorials where created_at > ?`).bind(since).first();
    if (c && c.c >= 30) return { error: "too many new pages, try again later", status: 429 };
    const id = newId(), iso = t.toISOString();
    await db.prepare(`insert into memorials (id, name, parent, rel, kind, by_name, msg, listed, created_at, candle_win)
                      values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).bind(id, name, parent, rel, kind, by, msg, a.p_listed === true ? 1 : 0, iso, iso).run();
    return id;
  },

  async get_memorial(db, a) {
    const id = key(a.p_id);
    if (!id) return null;
    const m = await db.prepare(`select id, name, parent, rel, kind, by_name, msg, candles, done, listed, created_at
                                  from memorials where id = ? and hidden = 0`).bind(id).first();
    if (!m) return null;
    const c = await db.prepare(`select n, s, by_name, at from chapters where memorial_id = ? order by n`).bind(id).all();
    return { memorial: pub(m), chapters: c.results || [] };
  },

  async light_candle(db, a, now) {
    const id = key(a.p_mid);
    if (!id) return null;
    const t = now(), iso = t.toISOString(), hourAgo = new Date(t - HOUR_MS).toISOString();
    await db.prepare(
      `update memorials set candles = candles + 1,
              candle_n = case when candle_win > ?2 then candle_n + 1 else 1 end,
              candle_win = case when candle_win > ?2 then candle_win else ?3 end
        where id = ?1 and hidden = 0 and (candle_win <= ?2 or candle_n < 600)`).bind(id, hourAgo, iso).run();
    return null;
  },

  async claim_chapter(db, a, now) {
    const id = key(a.p_mid), n = int(a.p_n);
    if (!id || n === null) return false;
    if (!(await visible(db, id))) return false;
    if (Math.floor((n - 1) / 150) + 1 > await round(db, id)) return false;
    return (await claim(db, id, n, by40(a.p_by), now())) === n;
  },

  async take_chapter(db, a, now) {
    const id = key(a.p_mid);
    if (!id || !(await visible(db, id))) return null;
    const by = by40(a.p_by);
    for (let attempt = 0; attempt < 40; attempt++) {
      const r = await round(db, id);
      if (r > 100) return null;
      const base = (r - 1) * 150, t = now(), stale = new Date(t - DAY_MS).toISOString();
      const rows = (await db.prepare(`select n, s, at from chapters where memorial_id = ? and n between ? and ?`).bind(id, base + 1, base + 150).all()).results || [];
      const taken = new Set(rows.filter(x => x.s === "done" || x.at >= stale).map(x => x.n));
      let n = null;
      for (let g = base + 1; g <= base + 150; g++) if (!taken.has(g)) { n = g; break; }
      if (n === null) return null;
      if ((await claim(db, id, n, by, t)) === n) return n;       // lost a race for this one: look again
    }
    return null;
  },

  async finish_chapter(db, a, now) {
    const id = key(a.p_mid), n = int(a.p_n);
    if (!id || n === null) return null;
    if (!(await visible(db, id))) return null;
    if (Math.floor((n - 1) / 150) + 1 > await round(db, id)) return null;
    const t = now(), iso = t.toISOString(), hourAgo = new Date(t - HOUR_MS).toISOString(), by = by40(a.p_by);
    const cur = await db.prepare(`select s from chapters where memorial_id = ? and n = ?`).bind(id, n).first();
    if (!cur || cur.s !== "done") {
      const c = await db.prepare(`select count(*) as c from chapters where memorial_id = ? and s = 'done' and at > ?`).bind(id, hourAgo).first();
      if (c && c.c >= 3000) return null;
    }
    // one batch = one transaction: mark it, then store the server's own count
    const res = await db.batch([
      db.prepare(`insert into chapters (memorial_id, n, s, by_name, at) values (?1, ?2, 'done', ?3, ?4)
                  on conflict (memorial_id, n) do update set s = 'done', at = excluded.at,
                     by_name = case when excluded.by_name <> '' then excluded.by_name else chapters.by_name end
                  where chapters.s <> 'done'`).bind(id, n, by, iso),
      db.prepare(`update memorials set done = (select count(*) from chapters where memorial_id = ?1 and s = 'done') where id = ?1`).bind(id),
      db.prepare(`select done from memorials where id = ?`).bind(id)
    ]);
    const row = res[2] && res[2].results && res[2].results[0];
    return row ? row.done : null;
  }
};

// Insert the claim, or take over one that was left unfinished for a day. Returns n when it is ours.
async function claim(db, id, n, by, t) {
  const stale = new Date(t - DAY_MS).toISOString();
  const r = await db.prepare(
    `insert into chapters (memorial_id, n, s, by_name, at) values (?1, ?2, 'claimed', ?3, ?4)
     on conflict (memorial_id, n) do update set by_name = excluded.by_name, at = excluded.at
     where chapters.s = 'claimed' and chapters.at < ?5
     returning n`).bind(id, n, by, t.toISOString(), stale).first();
  return r ? r.n : null;
}

async function visible(db, id) {
  return !!(await db.prepare(`select 1 as x from memorials where id = ? and hidden = 0`).bind(id).first());
}

// The round being read now: the first one that does not yet have all 150 chapters done.
async function round(db, id) {
  const rows = (await db.prepare(
    `select (n - 1) / 150 + 1 as r, count(*) as c from chapters where memorial_id = ? and s = 'done' group by r order by r`).bind(id).all()).results || [];
  const full = new Set(rows.filter(x => x.c >= 150).map(x => x.r));
  let r = 1;
  while (r <= 100 && full.has(r)) r++;
  return r;
}

const pub = m => ({ id: m.id, name: m.name, parent: m.parent, rel: m.rel, kind: m.kind, by_name: m.by_name, msg: m.msg,
  candles: m.candles, done: m.done, listed: !!m.listed, created_at: m.created_at });
const clean = t => String(t == null ? "" : t).replace(/[​-‏‪-‮⁠-⁩﻿]/g, "").replace(/[\u0001-\u001F\u007F-\u009F]/g, " ").replace(/\s+/g, " ").trim();
const by40 = t => clean(t).slice(0, 40);
const key = v => (typeof v === "string" && /^[A-Za-z0-9_-]{1,40}$/.test(v) ? v : null);
const int = v => (Number.isInteger(v) && v >= 1 && v <= 15000 ? v : null);
function newId() { const a = new Uint8Array(8); crypto.getRandomValues(a); return [...a].map(x => x.toString(16).padStart(2, "0")).join(""); }

function sameSite(request, env) {
  const allowed = new Set(SITE_ORIGINS);
  try { allowed.add(new URL(request.url).origin); } catch {}
  for (const o of String((env && env.ALLOWED_ORIGINS) || "").split(",")) if (o.trim()) allowed.add(o.trim().replace(/\/+$/, ""));
  const origin = request.headers.get("origin");
  if (origin) return allowed.has(origin);
  const ref = request.headers.get("referer");
  if (!ref) return false;
  try { return allowed.has(new URL(ref).origin); } catch { return false; }
}

export function _reset() { ready = null; }

function json(obj, status, extra) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "cache-control": "no-store", "x-content-type-options": "nosniff", vary: "Origin", "content-type": "application/json; charset=utf-8", ...(extra || {}) }
  });
}
