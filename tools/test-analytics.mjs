// Tests for the first-party analytics (/api/ev) and the admin server (/api/admin/*). Run: node --no-warnings tools/test-analytics.mjs
import { fakeD1 } from "./d1-fake.mjs";
import { onRequest as ev } from "../functions/api/ev.js";
import { onRequest as admin } from "../functions/api/admin/[[path]].js";
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SITE = "https://tfilah.com";
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log("FAIL:", m); } };

let clock = Date.parse("2026-11-27T10:00:00Z");
const assets = { fetch: async req => { const p = new URL(req.url).pathname; const f = join(ROOT, p.endsWith("/") ? p + "index.html" : p);
  return existsSync(f) ? new Response(readFileSync(f)) : new Response("nf", { status: 404 }); } };
const env = (over = {}) => ({ DB: db, NOW: () => clock, RAND: () => 0.5, ASSETS: assets, ADMIN_EMAIL: "admin@tfilah.com", ADMIN_PASSWORD: "a-long-test-password-123", ...over });
let db = fakeD1();
const post = (body, h = {}) => ev({ request: new Request(SITE + "/api/ev", { method: "POST", headers: { "content-type": "application/json", origin: SITE, "user-agent": "Mozilla/5.0 (iPhone)", ...h }, body: typeof body === "string" ? body : JSON.stringify(body) }), env: env() });
const n = async sql => (await db.prepare(sql).first()).n;

// ---------- /api/ev ----------
ok((await post({ k: "pv", p: "/siddur/", c: "search:google", d: "m", v: "abc12345" })).status === 204, "page view accepted");
ok(await n("select count(*) as n from ev") === 1 && await n("select count(*) as n from live") === 1, "page view stored in ev and live");
ok(await n("select sum(n) as n from day") === 1, "page view rolled up into day");
for (const [bad, why] of [
  [{ k: "pv", p: "/siddur/", c: "search:google", d: "m", v: "abc12345", name: "דוד" }, "extra field"],
  [{ k: "pv", p: "/siddur/?q=1", c: "direct", d: "m", v: "abc12345" }, "query string in path"],
  [{ k: "pv", p: "/y/abcdef1234/", c: "direct", d: "m", v: "abc12345" }, "a private reading id"],
  [{ k: "pv", p: "/admin/", c: "direct", d: "m", v: "abc12345" }, "admin path"],
  [{ k: "pv", p: "/siddur/", c: "https://www.google.com/search?q=x", d: "m", v: "abc12345" }, "full referrer"],
  [{ k: "type", p: "/siddur/", c: "direct", d: "m", v: "abc12345" }, "unknown kind"],
  [{ k: "pv", p: "/siddur/", c: "direct", d: "phone", v: "abc12345" }, "device not a class"],
  ["x".repeat(500), "oversized body"]]) {
  const r = await post(bad);
  ok(r.status === 400 || r.status === 413, "rejected: " + why + " (" + r.status + ")");
}
ok(await n("select count(*) as n from ev") === 1, "nothing stored from rejected events");
ok((await post({ k: "pv", p: "/", c: "direct", d: "d", v: "bot00001" }, { "user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1)" })).status === 204
   && await n("select count(*) as n from ev") === 1, "crawler page views are not counted");
ok((await post({ k: "pv", p: "/", c: "direct", d: "d", v: "xx000001" }, { origin: "https://evil.example" })).status === 403, "other origins refused");
clock += 120e3;
await post({ k: "hb", p: "/siddur/", c: "search:google", d: "m", v: "abc12345" });
ok((await db.prepare("select t from live where v = 'abc12345'").first()).t === Math.floor(clock / 1000), "heartbeat refreshes its page view");
await post({ k: "hb", p: "/siddur/", c: "direct", d: "m", v: "nothere1" });
ok(await n("select count(*) as n from live") === 1, "a heartbeat with no page view creates nothing");
await post({ k: "share", p: "/tehillim-yachad/", c: "internal", d: "m", v: "abc12346" });
ok(await n("select count(*) as n from ev where k = 'share'") === 1, "share event stored");
ok((await ev({ request: new Request(SITE + "/api/ev", { method: "POST", body: "{}" }), env: {} })).status === 204, "no database: quietly accepted, nothing breaks");

ok((await post({ k: "stk", p: "/stickers/amen/", c: "internal", d: "m", v: "abc12347" })).status === 204, "a sent sticker is counted");
ok((await post({ k: "dl", p: "/stickers/all/", c: "internal", d: "m", v: "abc12347" })).status === 204, "a pack download is counted");
for (const [bad, why] of [[{ k: "stk", p: "/siddur/" }, "a sticker event on another page"], [{ k: "pv", p: "/stickers/amen/" }, "a page view of a sticker path"],
  [{ k: "dl", p: "/stickers/../" }, "a made-up sticker path"], [{ k: "stk", p: "/stickers/" }, "a sticker event with no sticker"]])
  ok((await post({ c: "internal", d: "m", v: "abc12348", ...bad })).status === 400, "rejected: " + why);
ok(await n("select count(*) as n from ev where k in ('stk', 'dl')") === 2, "only the two good sticker events stored");

// ---------- /api/admin ----------
const call = (path, opt = {}, e = env()) => admin({ request: new Request(SITE + path, { headers: { origin: SITE, ...(opt.headers || {}) }, method: opt.method || "GET", body: opt.body }), env: e });
ok((await call("/api/admin/data?q=live")).status === 401, "data without a session: 401");
ok((await call("/api/admin/data?q=live", {}, env({ ADMIN_PASSWORD: "" }))).status === 503, "not configured: 503");
ok((await call("/api/admin/data?q=live", {}, env({ ADMIN_PASSWORD: "short1234" }))).status === 503, "password under 12 characters counts as not configured");
const login = (email, password, h = {}) => call("/api/admin/login", { method: "POST", body: JSON.stringify({ email, password }), headers: { "content-type": "application/json", "cf-connecting-ip": "203.0.113.9", ...h } });
ok((await login("admin@tfilah.com", "wrong-password-123")).status === 401, "wrong password refused");
ok((await login("someone@tfilah.com", "a-long-test-password-123")).status === 401, "wrong email refused");
ok((await login("admin@tfilah.com", "a-long-test-password-123", { origin: "https://evil.example" })).status === 403, "login from another site refused");
const good = await login("Admin@Tfilah.com", "a-long-test-password-123");
const cookie = (good.headers.get("set-cookie") || "").split(";")[0];
ok(good.status === 200 && /^tf_admin=/.test(cookie), "right email (any case) and password: session cookie");
ok(/HttpOnly/.test(good.headers.get("set-cookie")) && /SameSite=Strict/.test(good.headers.get("set-cookie")) && /Secure/.test(good.headers.get("set-cookie")), "cookie is HttpOnly, Secure, SameSite=Strict");
const auth = q => call("/api/admin/data?q=" + q, { headers: { cookie } });
const me = await (await auth("me")).json();
ok(me.email === "admin@tfilah.com", "session reads back the admin");
const live = await (await auth("live")).json();
ok(live.active === 1 && live.pv.h24 === 1 && live.recent.length === 4, "live numbers match the stored events (" + JSON.stringify({ a: live.active, h: live.pv.h24, r: live.recent.length }) + ")");
const tr = await (await auth("trend&days=7")).json();
ok(tr.total === 1 && tr.pages[0].p === "/siddur/" && tr.channels[0].c === "search:google", "trend sums the daily rollup");
ok(tr.stickers.length === 2 && tr.stickers.some(r => r.k === "stk" && r.p === "/stickers/amen/" && r.n === 1), "trend lists sticker sends and downloads");
const forged = cookie.slice(0, -3) + "AAA";
ok((await call("/api/admin/data?q=me", { headers: { cookie: forged } })).status === 401, "forged signature refused");
ok((await call("/api/admin/data?q=me", { headers: { cookie } }, env({ ADMIN_PASSWORD: "a-new-long-password-456" }))).status === 401, "changing the password signs sessions out");
clock += 13 * 3600e3;
ok((await auth("me")).status === 401, "session expires after 12 hours");
for (let i = 0; i < 8; i++) await login("admin@tfilah.com", "nope-nope-nope-1", { "cf-connecting-ip": "198.51.100.7" });
ok((await login("admin@tfilah.com", "a-long-test-password-123", { "cf-connecting-ip": "198.51.100.7" })).status === 429, "8 failures in 15 minutes lock that address");
ok((await login("admin@tfilah.com", "a-long-test-password-123", { "cf-connecting-ip": "203.0.113.50" })).status === 200, "other addresses are not locked");
const c2 = ((await login("admin@tfilah.com", "a-long-test-password-123", { "cf-connecting-ip": "203.0.113.51" })).headers.get("set-cookie") || "").split(";")[0];
const au = await (await call("/api/admin/data?q=audit", { headers: { cookie: c2 } })).json();
ok(au.checked >= 8 && au.sitemapUrls > 1000 && !au.blocksAll, "SEO audit reads the built site (" + au.checked + " pages, " + au.issues.length + " issues)");
ok(au.issues.filter(x => x.sev === "P0").length === 0, "no P0 issues in the built site: " + JSON.stringify(au.issues.filter(x => x.sev === "P0").slice(0, 3)));
const st = await (await call("/api/admin/data?q=status", { headers: { cookie: c2 } })).json();
ok(st.integrations.some(x => x.name === "IndexNow" && x.state === "key published"), "IndexNow key file is published");
ok((await call("/api/admin/logout", { method: "POST" })).headers.get("set-cookie").includes("Max-Age=0"), "logout clears the cookie");

console.log(`${pass + fail} checks, ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
