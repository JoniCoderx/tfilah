// מתאם: נותן לאתר את אותו ממשק שהיה לו בתוך Claude (db / user / sample),
// אבל על בסיס Supabase ופונקציית /api/ask משלכם.
(function () {
  var C = window.TFILAH_CONFIG || {};
  var sb = null;
  if (C.supabaseUrl && C.supabaseAnonKey && window.supabase) {
    sb = window.supabase.createClient(C.supabaseUrl, C.supabaseAnonKey);
  }

  function snapDoc(id, data) {
    return { id: String(id), exists: !!data, data: function () { return data || undefined; }, metadata: { fromCache: false, hasPendingWrites: false } };
  }
  function snapQuery(rows) {
    var docs = rows.map(function (r) { return snapDoc(r.__id, r); });
    return { docs: docs, size: docs.length, empty: !docs.length, docChanges: function () { return []; }, metadata: { fromCache: false, hasPendingWrites: false } };
  }
  function err(e) { return { code: "unavailable", message: (e && e.message) || "error" }; }
  function memRow(r) { return { __id: r.id, name: r.name, parent: r.parent, rel: r.rel, kind: r.kind || "neshama", by: r.by_name || "", msg: r.msg || "", candles: r.candles || 0, done: r.done || 0, listed: !!r.listed, createdAt: new Date(r.created_at).getTime() }; }
  function chRow(r) { return { __id: String(r.n), s: r.s, by: r.by_name || "", at: new Date(r.at).getTime() }; }

  // path helpers: "memorials" | "memorials/<id>/chapters"
  function parse(path) {
    var p = path.split("/");
    if (p[0] !== "memorials") throw new Error("unknown path " + path);
    if (p.length === 1) return { kind: "memorials" };
    if (p.length === 2) return { kind: "memorial", id: p[1] };
    if (p.length === 3 && p[2] === "chapters") return { kind: "chapters", mid: p[1] };
    if (p.length === 4 && p[2] === "chapters") return { kind: "chapter", mid: p[1], n: +p[3] };
    throw new Error("unknown path " + path);
  }

  function rpc(fn, args) {
    return sb.rpc(fn, args).then(function (res) { if (res.error) throw err(res.error); return res.data; });
  }

  // קריאה אחת מביאה את הקריאה כולה (גם כשאינה ברשימה הציבורית): {mem, chapters} או {mem:null, chapters:[]}
  function loadMem(id) {
    return rpc("get_memorial", { p_id: id }).then(function (d) {
      if (!d || !d.memorial) return { mem: null, chapters: [] };
      return { mem: memRow(d.memorial), chapters: (d.chapters || []).map(chRow) };
    });
  }

  // poller אחד לכל קריאה, משותף למאזיני המסמך והפרקים. מודיע רק כשמשהו השתנה.
  var POLL_MS = 8000, pollers = {};
  function part(sub, state) {
    return sub.what === "chapters" ? snapQuery(state.chapters) : snapDoc(sub.id, state.mem);
  }
  function partKey(sub, state) { return JSON.stringify(sub.what === "chapters" ? state.chapters : state.mem); }
  function deliver(p, sub) {
    if (sub.dead || !p.state) return;
    var k = partKey(sub, p.state);
    if (k === sub.key) return;
    sub.key = k;
    sub.next(part(sub, p.state));
  }
  function refresh(id) {
    var p = pollers[id];
    if (!p) return;
    if (p.busy) { p.again = true; return; }
    p.busy = true;
    loadMem(id).then(function (state) {
      p.state = state;
      p.subs.slice().forEach(function (sub) { deliver(p, sub); });
    }, function (e) {
      p.subs.slice().forEach(function (sub) { if (!sub.dead && sub.onErr) sub.onErr(e && e.code ? e : err(e)); });
    }).then(function () {
      p.busy = false;
      if (p.again) { p.again = false; refresh(id); }
    });
  }
  function watch(id, what, next, onErr) {
    var p = pollers[id];
    if (!p) {
      p = pollers[id] = { subs: [], state: null, busy: false, again: false, timer: null };
      p.timer = setInterval(function () { if (typeof document === "undefined" || !document.hidden) refresh(id); }, POLL_MS);
    }
    var sub = { id: id, what: what, next: next, onErr: onErr, key: null, dead: false };
    p.subs.push(sub);
    if (p.state) setTimeout(function () { deliver(p, sub); }, 0); // מה שכבר ידוע, מיד
    refresh(id);
    return function () {
      if (sub.dead) return;
      sub.dead = true;
      p.subs.splice(p.subs.indexOf(sub), 1);
      if (!p.subs.length && pollers[id] === p) { clearInterval(p.timer); delete pollers[id]; }
    };
  }
  if (typeof document !== "undefined" && document.addEventListener) {
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) Object.keys(pollers).forEach(refresh);
    });
  }

  function fetchQuery(q) {
    if (q.kind === "memorials") {
      // הרשימה הציבורית: השרת מחזיר רק קריאות שסומנו listed
      var r = sb.from("memorials").select("*").order("created_at", { ascending: false }).limit(q.limit || 200);
      return r.then(function (res) { if (res.error) throw res.error; return res.data.map(memRow); });
    }
    return loadMem(q.mid).then(function (state) { return state.chapters; });
  }

  function query(path) {
    var q = parse(path);
    var api = {
      orderBy: function () { return api; },
      limit: function (n) { q.limit = n; return api; },
      where: function () { return api; },
      get: function () { return fetchQuery(q).then(snapQuery, function (e) { throw e && e.code ? e : err(e); }); },
      add: function (d) {
        return rpc("create_memorial", { p_name: d.name, p_parent: d.parent || "", p_rel: d.rel, p_by: d.by || "", p_msg: d.msg || "", p_kind: d.kind || "neshama", p_listed: !!d.listed })
          .then(function (id) { return { id: String(id) }; });
      },
      doc: function (id) { return docRef(path + "/" + id); },
      onSnapshot: function (next, onErr) {
        if (q.kind === "chapters") return watch(q.mid, "chapters", next, onErr);
        var alive = true, timer = null;
        function load() { fetchQuery(q).then(function (rows) { if (alive) next(snapQuery(rows)); }, function (e) { if (alive && onErr) onErr(err(e)); }); }
        function soon() { clearTimeout(timer); timer = setTimeout(load, 250); }
        load();
        var opts = { event: "*", schema: "public", table: "memorials" };
        var ch = sb.channel("memorials-all-" + Math.random().toString(36).slice(2)).on("postgres_changes", opts, soon).subscribe();
        var poll = setInterval(load, 30000); // גיבוי אם realtime כבוי
        return function () { alive = false; clearTimeout(timer); clearInterval(poll); sb.removeChannel(ch); };
      }
    };
    return api;
  }

  function docRef(path) {
    var q = parse(path);
    return {
      id: path.split("/").pop(), path: path,
      get: function () {
        if (q.kind === "chapter") {
          return loadMem(q.mid).then(function (state) {
            var hit = null;
            state.chapters.forEach(function (c) { if (c.__id === String(q.n)) hit = c; });
            return snapDoc(q.n, hit);
          });
        }
        return loadMem(q.id).then(function (state) { return snapDoc(q.id, state.mem); });
      },
      // פרק: {s:'claimed',by} -> {ok:true|false} ; {s:'done',by} -> {done:<מספר>|null}
      set: function (d) {
        if (q.kind !== "chapter") return Promise.reject(err({ message: "unsupported" }));
        var done = d.s === "done";
        return rpc(done ? "finish_chapter" : "claim_chapter", { p_mid: q.mid, p_n: q.n, p_by: d.by || "" }).then(function (v) {
          refresh(q.mid);
          return done ? { done: typeof v === "number" ? v : null } : { ok: v === true };
        });
      },
      // פרק פנוי כלשהו בסבב הנוכחי: מחזיר את המפתח (פרק + 150*(סבב-1)) או null כשאין פנוי
      takeChapter: function (by) {
        if (q.kind !== "memorial") return Promise.reject(err({ message: "unsupported" }));
        return rpc("take_chapter", { p_mid: q.id, p_by: by || "" }).then(function (v) {
          refresh(q.id);
          return typeof v === "number" ? v : null;
        });
      },
      update: function (d) {
        if (q.kind !== "memorial") return Promise.reject(err({ message: "unsupported" }));
        if ("candles" in d) return rpc("light_candle", { p_mid: q.id }).then(function () { refresh(q.id); });
        return Promise.resolve(); // "done" מחושב בשרת
      },
      delete: function () { return Promise.reject(err({ message: "unsupported" })); },
      onSnapshot: function (next, onErr) {
        if (q.kind === "memorial") return watch(q.id, "memorial", next, onErr);
        return function () {}; // פרק בודד: לא נדרש באתר
      },
      collection: function (sub) { return query(path + "/" + sub); }
    };
  }

  var db = sb ? { collection: query, doc: docRef, features: { takeChapter: true, listed: true } } : null;
  var user = sb ? { can: function () { return true; }, isOwner: function () { return false; }, canEdit: function () { return false; } } : null;

  // ---- AI: streams from /api/ask (Cloudflare Pages Function) ----
  function sample(input, opts) {
    opts = opts || {};
    return new Promise(function (resolve, reject) {
      var messages = typeof input === "string" ? [{ role: "user", content: input }] : input;
      fetch("/api/ask", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ messages: messages }), signal: opts.signal })
        .then(function (res) {
          if (res.status === 429) throw { code: "rate_limited", message: "rate limited" };
          if (!res.ok || !res.body) throw { code: "unavailable", message: "HTTP " + res.status };
          var reader = res.body.getReader(), dec = new TextDecoder(), buf = "", text = "";
          function pump() {
            return reader.read().then(function (r) {
              if (r.done) { resolve({ text: text, truncated: false }); return; }
              buf += dec.decode(r.value, { stream: true });
              var lines = buf.split("\n"); buf = lines.pop();
              lines.forEach(function (line) {
                if (line.indexOf("data:") !== 0) return;
                try {
                  var ev = JSON.parse(line.slice(5));
                  if (ev.type === "content_block_delta" && ev.delta && ev.delta.type === "text_delta") {
                    text += ev.delta.text;
                    if (opts.onText) opts.onText({ text: text, delta: ev.delta.text });
                  }
                  if (ev.type === "error") throw { code: "unavailable", message: "upstream", text: text };
                } catch (e) { if (e && e.code) throw e; }
              });
              return pump();
            });
          }
          return pump();
        })
        .catch(function (e) {
          if (e && e.name === "AbortError") reject({ code: "cancelled", message: "cancelled", text: "" });
          else reject({ code: (e && e.code) || "unavailable", message: (e && e.message) || "error", text: e && e.text });
        });
    });
  }

  var caps = { db: db, user: user, sample: C.aiEnabled ? sample : null };
  window.claude = { use: function (name) { return Promise.resolve(caps[name] || null); } };
})();
