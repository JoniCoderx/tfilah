// Cloudflare Pages Function: POST /api/shem  {name, neshama} -> {id}
// Gives a short address for "Psalm 119 by the letters of a name": tfilah.com/n/<id>. The id is derived from the name
// itself, so the same name always gets the same address and asking twice stores nothing new.
// Only a name in Hebrew letters (40 at most) and one yes/no are stored. Nothing about the person who asked.
import { cleanName } from "../shem/[name].js";

const SCHEMA = `create table if not exists names (id text primary key, name text not null, neshama integer not null default 0, created_at text not null)`;
const A = "abcdefghijkmnpqrstuvwxyz23456789";
let ready = null;

export async function idFor(name, neshama, len) {
  const h = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode((neshama ? "n|" : "r|") + name)));
  return [...h.slice(0, len || 6)].map(x => A[x % A.length]).join("");
}

export async function lookup(env, id) {
  if (!env || !env.DB || !/^[a-z0-9]{6,10}$/.test(String(id || ""))) return null;
  try {
    if (!ready) ready = env.DB.prepare(SCHEMA).run().catch(e => { ready = null; throw e; });
    await ready;
    const r = await env.DB.prepare(`select name, neshama from names where id = ?`).bind(id).first();
    return r ? { name: r.name, neshama: !!r.neshama } : null;
  } catch { return undefined; }   // undefined: could not ask
}

const json = (o, s) => new Response(JSON.stringify(o), { status: s || 200, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff" } });

export async function onRequestPost({ request, env }) {
  if (!env || !env.DB) return json({ error: "not configured" }, 503);
  const here = new URL(request.url).origin, origin = request.headers.get("origin");
  if (origin && origin !== here && origin !== "https://tfilah.com") return json({ error: "forbidden" }, 403);
  const raw = await request.text();
  if (raw.length > 400) return json({ error: "too long" }, 413);
  let b; try { b = JSON.parse(raw); } catch { return json({ error: "bad json" }, 400); }
  const name = cleanName(b && b.name), neshama = !!(b && b.neshama);
  if (!name) return json({ error: "bad name" }, 400);
  try {
    if (!ready) ready = env.DB.prepare(SCHEMA).run().catch(e => { ready = null; throw e; });
    await ready;
    for (const len of [6, 8, 10]) {          // a longer id only if a different name already holds the short one
      const id = await idFor(name, neshama, len);
      const got = await env.DB.prepare(`select name, neshama from names where id = ?`).bind(id).first();
      if (got && got.name === name && !!got.neshama === neshama) return json({ id });
      if (!got) {
        await env.DB.prepare(`insert or ignore into names (id, name, neshama, created_at) values (?, ?, ?, ?)`).bind(id, name, neshama ? 1 : 0, new Date().toISOString()).run();
        return json({ id });
      }
    }
    return json({ error: "busy" }, 503);
  } catch (e) {
    console.error("shem: unexpected error", e && e.name);
    return json({ error: "internal error" }, 500);
  }
}
