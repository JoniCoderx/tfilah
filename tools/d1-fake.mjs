// A stand-in for Cloudflare D1 on top of Node's built-in SQLite, for tests and for running the site locally.
// It covers what functions/api/yachad.js uses: prepare().bind().first()/all()/run() and batch() as one transaction.
import { DatabaseSync } from "node:sqlite";

export function fakeD1(file = ":memory:") {
  const db = new DatabaseSync(file);
  const stmt = (sql, args = []) => ({
    sql, args,
    bind: (...a) => stmt(sql, a),
    _all() { const s = db.prepare(sql); return /^\s*(select|with)/i.test(sql) || /\breturning\b/i.test(sql) ? s.all(...args).map(r => ({ ...r })) : (s.run(...args), []); },
    async first() { const r = this._all(); return r.length ? r[0] : null; },
    async all() { return { results: this._all(), success: true }; },
    async run() { this._all(); return { success: true }; }
  });
  return {
    prepare: sql => stmt(sql),
    async batch(list) {
      db.exec("begin");
      try { const out = list.map(s => ({ results: s._all(), success: true })); db.exec("commit"); return out; }
      catch (e) { db.exec("rollback"); throw e; }
    },
    _raw: db
  };
}
