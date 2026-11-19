// Runs shim.js in node against a local Postgres that already has supabase.sql applied.
// The Supabase client is replaced by a small stand-in that sends every rpc / select through
// psql as role anon, using the same named parameters PostgREST would use, so a wrong
// parameter name or return shape in shim.js fails here.
// Normally started by tools/test-supabase.py; alone: PGDATABASE=<db> node tools/test-supabase-shim.js
var cp = require("child_process"), fs = require("fs"), path = require("path"), vm = require("vm");

function psql(sql, role) {
  return new Promise(function (resolve) {
    var env = Object.assign({}, process.env);
    if (role) env.PGOPTIONS = "-c role=" + role;
    var p = cp.execFile("psql", ["-X", "-q", "-At", "-v", "ON_ERROR_STOP=1", "-f", "-"], { env: env }, function (e, out, errText) {
      if (e) resolve({ data: null, error: { message: String(errText || e.message).trim() } });
      else resolve({ data: out.trim() === "" ? null : JSON.parse(out), error: null });
    });
    p.stdin.end(sql);
  });
}
function lit(v) {
  if (v === null || v === undefined) return "null";
  if (typeof v === "boolean" || typeof v === "number") return String(v);
  return "'" + String(v).replace(/'/g, "''") + "'";
}
var rpcLog = [];
var sb = {
  rpc: function (fn, args) {
    rpcLog.push(fn);
    var a = Object.keys(args).map(function (k) { return k + " => " + lit(args[k]); }).join(", ");
    return psql("select to_json(public." + fn + "(" + a + "));", "anon");
  },
  from: function (table) {
    var lim = 200;
    var b = {
      select: function () { return b; }, order: function () { return b; }, eq: function () { return b; },
      limit: function (n) { lim = n; return b; },
      then: function (ok, bad) {
        return psql("select coalesce(json_agg(t), '[]'::json) from (select * from public." + table + " order by created_at desc limit " + lim + ") t;", "anon").then(ok, bad);
      }
    };
    return b;
  },
  channel: function () { var c = { on: function () { return c; }, subscribe: function () { return c; } }; return c; },
  removeChannel: function () {}
};

var win = { TFILAH_CONFIG: { supabaseUrl: "x", supabaseAnonKey: "y" }, supabase: { createClient: function () { return sb; } } };
var ctx = { window: win, setTimeout: setTimeout, clearTimeout: clearTimeout, setInterval: setInterval, clearInterval: clearInterval, Promise: Promise, JSON: JSON, Date: Date, Math: Math, Object: Object, String: String, Error: Error };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "shim.js"), "utf8"), ctx);

var fails = 0, total = 0;
function check(name, ok, detail) {
  total++; if (!ok) fails++;
  console.log("  " + (ok ? "PASS" : "FAIL") + "  shim: " + name + (detail !== undefined ? "   [" + detail + "]" : ""));
}
function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

(async function () {
  var db = await win.claude.use("db");
  check("db.features", db.features && db.features.takeChapter === true && db.features.listed === true);
  check("use('user') present, use('sample') null without aiEnabled", !!(await win.claude.use("user")) && (await win.claude.use("sample")) === null);

  var ref = await db.collection("memorials").add({ name: "שים", parent: "", rel: "בן", by: "בודק", msg: "" });
  var pub = await db.collection("memorials").add({ name: "שים גלוי", parent: "", rel: "בת", listed: true });
  check("add() returns ids", /^[0-9a-f]{10}$/.test(ref.id) && /^[0-9a-f]{10}$/.test(pub.id), ref.id);

  var list = (await db.collection("memorials").orderBy("createdAt", "desc").limit(200).get()).docs.map(function (d) { return d.id; });
  check("public list has the listed reading and not the default one", list.indexOf(pub.id) >= 0 && list.indexOf(ref.id) < 0);

  var doc = db.doc("memorials/" + ref.id), snap = await doc.get();
  check("doc.get() reads the unlisted reading", snap.exists && snap.data().name === "שים" && snap.data().listed === false && snap.data().by === "בודק" && snap.data().createdAt > 0);
  check("listed flag exposed", (await db.doc("memorials/" + pub.id).get()).data().listed === true);
  check("doc.get() of unknown id: exists=false", (await db.doc("memorials/nosuchid").get()).exists === false);

  var docSnaps = [], chSnaps = [], errs = [];
  var un1 = doc.onSnapshot(function (s) { docSnaps.push(s); }, function (e) { errs.push(e); });
  var un2 = doc.collection("chapters").onSnapshot(function (s) { chSnaps.push(s); }, function (e) { errs.push(e); });
  await sleep(1500);
  check("onSnapshot delivers immediately (doc and chapters)", docSnaps.length === 1 && chSnaps.length === 1 && docSnaps[0].exists && chSnaps[0].size === 0, docSnaps.length + "/" + chSnaps.length);
  var calls = rpcLog.filter(function (f) { return f === "get_memorial"; }).length;

  var k = await doc.takeChapter("רות");
  check("takeChapter() resolves to key 1", k === 1, k);
  var c1 = await db.doc("memorials/" + ref.id + "/chapters/1").set({ s: "claimed", by: "אחר" });
  var c2 = await doc.collection("chapters").doc("2").set({ s: "claimed", by: "אחר" });
  check("set claimed on taken key -> {ok:false}; on free key -> {ok:true}", c1.ok === false && c2.ok === true, JSON.stringify([c1, c2]));
  var d1 = await db.doc("memorials/" + ref.id + "/chapters/1").set({ s: "done", by: "רות" });
  var d2 = await db.doc("memorials/" + ref.id + "/chapters/1").set({ s: "done", by: "רות" });
  check("set done -> {done:1}, repeated -> {done:1}", d1.done === 1 && d2.done === 1, JSON.stringify([d1, d2]));
  await doc.update({ candles: 2 });

  var chs = await doc.collection("chapters").get();
  var m = {}; chs.docs.forEach(function (d) { m[d.id] = d.data(); });
  check("chapters.get() on unlisted reading", chs.size === 2 && m["1"].s === "done" && m["1"].by === "רות" && m["2"].s === "claimed" && m["2"].by === "אחר" && m["2"].at > 0);
  var one = await db.doc("memorials/" + ref.id + "/chapters/2").get(), none = await db.doc("memorials/" + ref.id + "/chapters/77").get();
  check("chapter doc.get()", one.exists && one.data().s === "claimed" && none.exists === false);

  await sleep(1500);
  var lastDoc = docSnaps[docSnaps.length - 1].data(), lastCh = chSnaps[chSnaps.length - 1];
  check("listeners refreshed right after writes (done=1, candles=2, 2 chapters)", lastDoc.done === 1 && lastDoc.candles === 2 && lastCh.size === 2, JSON.stringify([lastDoc.done, lastDoc.candles, lastCh.size]));

  // a change made by somebody else must arrive through the 8 second poll
  var nDoc = docSnaps.length, nCh = chSnaps.length;
  await psql("select to_json(public.finish_chapter('" + ref.id + "', 2, 'אחר'));", "anon");
  await sleep(9500);
  check("foreign change arrives by polling within ~8s", docSnaps.length === nDoc + 1 && chSnaps.length === nCh + 1 && docSnaps[docSnaps.length - 1].data().done === 2, (docSnaps.length - nDoc) + "/" + (chSnaps.length - nCh));
  var nDoc2 = docSnaps.length, nCh2 = chSnaps.length, before = rpcLog.length;
  await sleep(9000);
  check("no snapshot when nothing changed, but polling goes on", docSnaps.length === nDoc2 && chSnaps.length === nCh2 && rpcLog.length > before);
  var polls = rpcLog.slice(before).filter(function (f) { return f === "get_memorial"; }).length;
  check("one shared poller for both listeners (1 call per tick)", polls === 1, polls + " get_memorial calls in 9s");

  un1(); un2(); un1();
  await psql("select to_json(public.light_candle('" + ref.id + "'));", "anon");
  var n3 = docSnaps.length, b3 = rpcLog.length;
  await sleep(9000);
  check("unsubscribe stops snapshots and polling", docSnaps.length === n3 && rpcLog.length === b3);
  check("no listener errors", errs.length === 0, JSON.stringify(errs));

  var rej = null;
  try { await db.collection("memorials").add({ name: "", rel: "בן" }); } catch (e) { rej = e; }
  check("server error becomes {code,message} rejection", rej && rej.code === "unavailable" && /check constraint/.test(rej.message));

  console.log("  shim: " + total + " checks, " + (total - fails) + " passed, " + fails + " failed (" + calls + " get_memorial calls for the two initial listeners)");
  process.exit(fails ? 1 : 0);
})().catch(function (e) { console.log("  FAIL  shim: crashed: " + (e && e.stack || JSON.stringify(e))); process.exit(1); });
