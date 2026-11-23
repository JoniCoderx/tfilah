// Tests for functions/api/yachad.js against a local SQLite stand-in for D1 (no network).
//   node --no-warnings tools/test-yachad.mjs
import { onRequest, _reset, readPublic } from "../functions/api/yachad.js";
import { onRequest as sharePage } from "../functions/y/[id].js";
import { fakeD1 } from "./d1-fake.mjs";

const SITE = "https://tfilah.com";
let pass = 0, fail = 0, clock = Date.parse("2026-11-22T10:00:00Z");
const ok = (name, cond, extra) => { cond ? pass++ : fail++; if (!cond) console.log("FAIL ", name, extra === undefined ? "" : JSON.stringify(extra)); };
let DB = fakeD1(); _reset();
let dice = () => 0;                      // which free chapter a reader gets: 0 = the lowest, so the checks below can name chapters
const env = () => ({ DB, NOW: () => clock, RAND: () => dice() });
const post = async (fn, args, { headers = {}, e = env(), raw } = {}) => {
  const r = await onRequest({ request: new Request(SITE + "/api/yachad", { method: "POST", headers: { "content-type": "application/json", origin: SITE, ...headers }, body: raw !== undefined ? raw : JSON.stringify({ fn, args }) }), env: e });
  let j = null; try { j = await r.json(); } catch {} return { s: r.status, j, d: j && j.data };
};
const list = async () => (await (await onRequest({ request: new Request(SITE + "/api/yachad?list=1"), env: env() })).json()).data;
const mk = (over = {}) => post("create_memorial", { p_name: "שרה", p_parent: "רחל", p_rel: "בת", p_by: "דוד", p_msg: "", p_kind: "refuah", p_listed: false, ...over });

// ---- create and read ----
let a = await mk();
const id = a.d;
ok("create returns a short id that is easy to read out", a.s === 200 && /^[a-z2-9]{10}$/.test(id) && !/[lo01]/.test(id), a.j);
let g = (await post("get_memorial", { p_id: id })).d;
ok("get returns the reading with no chapters", g && g.memorial.name === "שרה" && g.memorial.kind === "refuah" && g.memorial.done === 0 && g.chapters.length === 0 && g.memorial.listed === false, g);
ok("an unlisted reading is not in the public list", (await list()).length === 0);
const pubId = (await mk({ p_name: "יעקב", p_rel: "בן", p_listed: true })).d;
ok("a listed reading is in the public list", (await list()).some(m => m.id === pubId) && (await list()).length === 1);
ok("unknown id gives null", (await post("get_memorial", { p_id: "nope" })).d === null);
ok("the hidden flag never leaves the server", !("hidden" in g.memorial) && !("candle_n" in g.memorial));

// ---- validation ----
for (const [name, over] of [["empty name", { p_name: "  " }], ["long name", { p_name: "א".repeat(61) }], ["bad rel", { p_rel: "x" }], ["bad kind", { p_kind: "x" }], ["long message", { p_msg: "א".repeat(201) }]])
  ok(name + " is refused", (await mk(over)).s === 400);
a = await mk({ p_name: " שם‏ עם\u0007  רווחים " });
ok("names are cleaned", (await post("get_memorial", { p_id: a.d })).d.memorial.name === "שם עם רווחים");
ok("unknown function", (await post("drop_everything", {})).s === 400);
ok("another site is refused", (await post("get_memorial", { p_id: id }, { headers: { origin: "https://evil.example" } })).s === 403);
ok("bad json", (await post("", {}, { raw: "{" })).s === 400);
ok("too long", (await post("", {}, { raw: JSON.stringify({ fn: "get_memorial", args: { p_id: "x".repeat(5000) } }) })).s === 413);
ok("no database bound: 503", (await post("get_memorial", { p_id: id }, { e: {} })).s === 503);
ok("sql in an id is just a bad id", (await post("get_memorial", { p_id: "x' or '1'='1" })).d === null);

// ---- taking and finishing chapters ----
const t1 = (await post("take_chapter", { p_mid: id, p_by: "אבי" })).d, t2 = (await post("take_chapter", { p_mid: id, p_by: "בני" })).d;
ok("take gives chapter 1, then 2", t1 === 1 && t2 === 2, [t1, t2]);
ok("claiming a taken chapter fails", (await post("claim_chapter", { p_mid: id, p_n: 1, p_by: "גד" })).d === false);
ok("claiming a free chapter works", (await post("claim_chapter", { p_mid: id, p_n: 23, p_by: "גד" })).d === true);
ok("a chapter of a round not yet open is refused", (await post("claim_chapter", { p_mid: id, p_n: 151, p_by: "גד" })).d === false && (await post("finish_chapter", { p_mid: id, p_n: 151, p_by: "" })).d === null);
ok("finish returns the count", (await post("finish_chapter", { p_mid: id, p_n: 1, p_by: "אבי" })).d === 1);
ok("finishing twice does not count twice", (await post("finish_chapter", { p_mid: id, p_n: 1, p_by: "אבי" })).d === 1);
ok("finishing an unclaimed chapter counts", (await post("finish_chapter", { p_mid: id, p_n: 40, p_by: "" })).d === 2);
g = (await post("get_memorial", { p_id: id })).d;
ok("done is the server's count", g.memorial.done === 2 && g.chapters.filter(c => c.s === "done").length === 2, g.memorial);
ok("the finisher's name is kept", g.chapters.find(c => c.n === 1).by_name === "אבי" && g.chapters.find(c => c.n === 2).by_name === "בני");
const both = await Promise.all([post("take_chapter", { p_mid: id, p_by: "x" }), post("take_chapter", { p_mid: id, p_by: "y" })]);
ok("two people at once get different chapters", both[0].d !== both[1].d && both[0].d > 2 && both[1].d > 2, [both[0].d, both[1].d]);
for (const bad of [0, 15001, 1.5, "7", null]) ok("bad chapter number " + JSON.stringify(bad), (await post("finish_chapter", { p_mid: id, p_n: bad, p_by: "" })).d === null && (await post("claim_chapter", { p_mid: id, p_n: bad, p_by: "" })).d === false);

// ---- readers are counted per browser, not per chapter ----
{ const r = (await mk({ p_name: "קוראים" })).d;
  for (const n of [1, 2, 3]) await post("finish_chapter", { p_mid: r, p_n: n, p_by: "", p_rid: "aaaaaaaa11" });
  await post("take_chapter", { p_mid: r, p_by: "רות", p_rid: "bbbbbbbb22" });
  await post("finish_chapter", { p_mid: r, p_n: 9, p_by: "נעמי" });                       // no id: counted by name
  await post("finish_chapter", { p_mid: r, p_n: 10, p_by: "", p_rid: "<script>" });        // a bad id is dropped: anonymous
  const m = (await post("get_memorial", { p_id: r })).d.memorial;
  ok("six chapters from four readers", m.done === 5 && m.readers === 4, m);
  const pubm = await readPublic(env(), r);
  ok("the share page reads only public fields", pubm && pubm.name === "קוראים" && pubm.done === 5 && !("hidden" in pubm) && !("by_name" in pubm));
  ok("the share page gets nothing for a bad or unknown id", (await readPublic(env(), "x' or 1=1")) === null && (await readPublic(env(), "zzzzzzzzzz")) === null);
}

// ---- a claim left for a day can be taken over ----
clock += 23 * 3600e3;
ok("after 23 hours the claim still holds", (await post("claim_chapter", { p_mid: id, p_n: 2, p_by: "חדש" })).d === false);
clock += 2 * 3600e3;
ok("after 25 hours it can be taken over", (await post("claim_chapter", { p_mid: id, p_n: 2, p_by: "חדש" })).d === true);
ok("a finished chapter is never taken over", (await post("claim_chapter", { p_mid: id, p_n: 1, p_by: "חדש" })).d === false);
ok("take prefers the lowest free or stale chapter", (await post("take_chapter", { p_mid: id, p_by: "z" })).d === 3);

// ---- rounds ----
const rid = (await mk({ p_name: "סבב" })).d;
for (let n = 1; n <= 149; n++) await post("finish_chapter", { p_mid: rid, p_n: n, p_by: "" });
ok("round 2 is closed while one chapter is missing", (await post("claim_chapter", { p_mid: rid, p_n: 151, p_by: "" })).d === false);
ok("take gives the last missing chapter", (await post("take_chapter", { p_mid: rid, p_by: "" })).d === 150);
ok("the 150th closes the book", (await post("finish_chapter", { p_mid: rid, p_n: 150, p_by: "" })).d === 150);
ok("the next take opens round 2", (await post("take_chapter", { p_mid: rid, p_by: "" })).d === 151);
ok("round 2 counts on", (await post("finish_chapter", { p_mid: rid, p_n: 151, p_by: "" })).d === 151);
ok("round 3 is still closed", (await post("claim_chapter", { p_mid: rid, p_n: 301, p_by: "" })).d === false);

// ---- candles ----
await post("light_candle", { p_mid: id });
ok("a candle is counted", (await post("get_memorial", { p_id: id })).d.memorial.candles === 2);
DB._raw.exec(`update memorials set candle_n = 600 where id = '${id}'`);
await post("light_candle", { p_mid: id });
ok("the hourly candle cap holds", (await post("get_memorial", { p_id: id })).d.memorial.candles === 2);
clock += 61 * 60e3; await post("light_candle", { p_mid: id });
ok("and lifts after an hour", (await post("get_memorial", { p_id: id })).d.memorial.candles === 3);

// ---- hidden readings ----
DB._raw.exec(`update memorials set hidden = 1 where id = '${pubId}'`);
ok("a hidden reading disappears from the list and from get", (await list()).every(m => m.id !== pubId) && (await post("get_memorial", { p_id: pubId })).d === null);
ok("and cannot be written to", (await post("take_chapter", { p_mid: pubId, p_by: "" })).d === null && (await post("finish_chapter", { p_mid: pubId, p_n: 1, p_by: "" })).d === null && (await post("claim_chapter", { p_mid: pubId, p_n: 1, p_by: "" })).d === false);

// ---- the site-wide damper on new readings ----
DB = fakeD1(); _reset(); let last;
for (let i = 0; i < 31; i++) last = await mk({ p_name: "מס " + i });
ok("the 31st new reading within ten minutes is refused", last.s === 429, last.s);
clock += 11 * 60e3;
ok("and allowed again later", (await mk()).s === 200);

// ---- the address people send ----
{ const r = (await mk({ p_name: "שרה", p_parent: "רחל", p_rel: "בת", p_kind: "refuah" })).d;
  const res = await sharePage({ params: { id: r }, env: env(), request: new Request(SITE + "/y/" + r) }), h = await res.text();
  ok("share page says who the reading is for", res.status === 200 && h.includes("<title>תהילים יחד לרפואה שלמה של שרה בת רחל | תפילה</title>") && h.includes('property="og:title" content="תהילים יחד לרפואה שלמה של שרה בת רחל"'));
  ok("share page opens the reading and is not indexed", h.includes('location.replace("/#m-' + r + '")') && h.includes('content="noindex"') && h.includes("og-yachad.png"));
  const x = (await mk({ p_name: '<img src=x onerror=1>"', p_kind: "general" })).d;
  const hx = await (await sharePage({ params: { id: x }, env: env(), request: new Request(SITE + "/y/" + x) })).text();
  ok("names are escaped on the share page", !hx.includes("<img src=x") && hx.includes("&lt;img"));
  const nf = await sharePage({ params: { id: "nosuchid22" }, env: env(), request: new Request(SITE + "/y/nosuchid22") });
  ok("unknown reading: generic page, 404", nf.status === 404 && (await nf.text()).includes("קריאת תהילים משותפת"));
  const bad = await sharePage({ params: { id: "a b<c" }, env: env(), request: new Request(SITE + "/y/x") });
  ok("a malformed id is sent to the explanation page", bad.status === 302 && bad.headers.get("location").endsWith("/tehillim-yachad/"));
}

// ---- an older private reading can be put on the list by whoever holds its id; a newer one keeps its opener's choice ----
{
  const keep = clock;
  DB = fakeD1(); _reset();          // a fresh database: the checks above leave the rate limit used up
  clock = Date.parse("2026-11-22T20:00:00Z");
  const mkOld = await mk({ p_name: "ישן" }); const oldId = mkOld.d;
  ok("the older reading was created", typeof oldId === "string", mkOld.j);
  clock = Date.parse("2026-11-23T12:00:00Z");
  const newId2 = (await mk({ p_name: "חדש" })).d;
  ok("an older private reading starts unlisted", !(await list()).some(m => m.id === oldId));
  ok("listing an older private reading works", (await post("list_legacy", { p_id: oldId })).d === true && (await list()).some(m => m.id === oldId));
  ok("listing it again still answers yes", (await post("list_legacy", { p_id: oldId })).d === true);
  ok("a newer private reading cannot be listed this way", (await post("list_legacy", { p_id: newId2 })).d === false && !(await list()).some(m => m.id === newId2));
  ok("an unknown id is not listed", (await post("list_legacy", { p_id: "nope" })).d === false);
  ok("a missing id is refused", (await post("list_legacy", {})).s === 400);
  clock = keep;
}

// ---- a reader gets any free chapter, not the next in order ----
{
  DB = fakeD1(); _reset(); clock = Date.parse("2026-11-23T12:00:00Z");
  const r = (await mk({ p_name: "אקראי" })).d;
  dice = () => 0.999; ok("the draw can give the last chapter", (await post("take_chapter", { p_mid: r, p_by: "" })).d === 150);
  dice = () => 0.5; const mid = (await post("take_chapter", { p_mid: r, p_by: "" })).d; ok("the draw can give a chapter from the middle", mid > 60 && mid < 90, mid);
  dice = Math.random; const got = new Set(); for (let i = 0; i < 40; i++) got.add((await post("take_chapter", { p_mid: r, p_by: "" })).d);
  ok("forty draws give forty different free chapters", got.size === 40 && !got.has(150) && !got.has(mid) && [...got].every(n => n >= 1 && n <= 150));
  ok("the draws are not in order", [...got].some((n, i, a) => i && n < a[i - 1]));
  dice = () => 0;
}

console.log(`${pass + fail} checks, ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
