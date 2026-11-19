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
  function memRow(r) { return { __id: r.id, name: r.name, parent: r.parent, rel: r.rel, kind: r.kind || "neshama", by: r.by_name || "", msg: r.msg || "", candles: r.candles || 0, done: r.done || 0, createdAt: new Date(r.created_at).getTime() }; }
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

  function fetchQuery(q) {
    if (q.kind === "memorials") {
      var r = sb.from("memorials").select("*").order("created_at", { ascending: false }).limit(q.limit || 200);
      return r.then(function (res) { if (res.error) throw res.error; return res.data.map(memRow); });
    }
    return sb.from("chapters").select("*").eq("memorial_id", q.mid).then(function (res) { if (res.error) throw res.error; return res.data.map(chRow); });
  }

  function query(path) {
    var q = parse(path);
    var api = {
      orderBy: function () { return api; },
      limit: function (n) { q.limit = n; return api; },
      where: function () { return api; },
      get: function () { return fetchQuery(q).then(snapQuery); },
      add: function (d) {
        return sb.rpc("create_memorial", { p_name: d.name, p_parent: d.parent || "", p_rel: d.rel, p_by: d.by || "", p_msg: d.msg || "", p_kind: d.kind || "neshama" })
          .then(function (res) { if (res.error) throw err(res.error); return { id: String(res.data) }; });
      },
      doc: function (id) { return docRef(path + "/" + id); },
      onSnapshot: function (next, onErr) {
        var alive = true, timer = null;
        function load() { fetchQuery(q).then(function (rows) { if (alive) next(snapQuery(rows)); }, function (e) { if (alive && onErr) onErr(err(e)); }); }
        function soon() { clearTimeout(timer); timer = setTimeout(load, 250); }
        load();
        var table = q.kind === "memorials" ? "memorials" : "chapters";
        var opts = { event: "*", schema: "public", table: table };
        if (q.kind === "chapters") opts.filter = "memorial_id=eq." + q.mid;
        var ch = sb.channel(table + "-" + (q.mid || "all") + "-" + Math.random().toString(36).slice(2)).on("postgres_changes", opts, soon).subscribe();
        var poll = setInterval(load, 30000); // גיבוי אם realtime כבוי
        return function () { alive = false; clearInterval(poll); sb.removeChannel(ch); };
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
          return sb.from("chapters").select("*").eq("memorial_id", q.mid).eq("n", q.n).maybeSingle()
            .then(function (res) { if (res.error) throw err(res.error); return snapDoc(q.n, res.data ? chRow(res.data) : null); });
        }
        return sb.from("memorials").select("*").eq("id", q.id).maybeSingle()
          .then(function (res) { if (res.error) throw err(res.error); return snapDoc(q.id, res.data ? memRow(res.data) : null); });
      },
      set: function (d) {
        if (q.kind !== "chapter") return Promise.reject(err({ message: "unsupported" }));
        var fn = d.s === "done" ? "finish_chapter" : "claim_chapter";
        return sb.rpc(fn, { p_mid: q.mid, p_n: q.n, p_by: d.by || "" }).then(function (res) { if (res.error) throw err(res.error); });
      },
      update: function (d) {
        if (q.kind !== "memorial") return Promise.reject(err({ message: "unsupported" }));
        if ("candles" in d) return sb.rpc("light_candle", { p_mid: q.id }).then(function (res) { if (res.error) throw err(res.error); });
        return Promise.resolve(); // "done" מחושב בשרת
      },
      delete: function () { return Promise.reject(err({ message: "unsupported" })); },
      onSnapshot: function () { return function () {}; },
      collection: function (sub) { return query(path + "/" + sub); }
    };
  }

  var db = sb ? { collection: query, doc: docRef } : null;
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
