#!/usr/bin/env python3
"""Tests for supabase.sql against a local Postgres (not against Supabase itself).

Needs: psql on PATH and a running Postgres you can connect to as a superuser.
Connection comes from the usual PG* variables; defaults: 127.0.0.1:54329 user postgres.

    python3 tools/test-supabase.py

It creates the roles anon/authenticated if missing, creates throwaway databases named
tfilah_test_*, and drops them at the end (pass --keep to leave them for inspection).
If node is installed it also runs tools/test-supabase-shim.js (shim.js against the same db).
Exit code 0 only if every check passed.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL = os.path.join(ROOT, "supabase.sql")
os.environ.setdefault("PGHOST", "127.0.0.1")
os.environ.setdefault("PGPORT", "54329")
os.environ.setdefault("PGUSER", "postgres")
KEEP = "--keep" in sys.argv

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("   [" + str(detail) + "]") if detail != "" else ""))


def psql_cmd(db, role=None):
    cmd = ["psql", "-X", "-q", "-At", "-d", db]
    if role:
        cmd = ["env", "PGOPTIONS=-c role=" + role] + cmd
    return cmd


def run(db, sql, role=None, stop=True):
    """Run sql in one psql session. Returns (stdout lines, stderr text, exit code)."""
    cmd = psql_cmd(db, role) + ["-v", "ON_ERROR_STOP=%d" % (1 if stop else 0), "-f", "-"]
    p = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    return p.stdout.split("\n")[:-1] if p.stdout else [], p.stderr.strip(), p.returncode


def q(db, sql, role=None):
    out, err, rc = run(db, sql, role)
    if rc != 0:
        raise RuntimeError("psql failed: %s\n%s" % (err, sql))
    return out


def one(db, sql, role=None):
    out = q(db, sql, role)
    return out[-1] if out else ""


def parallel(db, scripts, role=None):
    """Start one psql session per script, all at once; every statement autocommits."""
    procs = []
    for s in scripts:
        p = subprocess.Popen(psql_cmd(db, role) + ["-f", "-"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        procs.append((p, s))
    for p, s in procs:          # feed all sessions before waiting on any
        p.stdin.write(s)
        p.stdin.close()
    outs, errs = [], []
    for p, _ in procs:
        o = p.stdout.read()
        e = p.stderr.read()
        p.wait()
        outs.append(o.split("\n")[:-1] if o else [])
        if e.strip():
            errs.append(e.strip())
    return outs, errs


def apply_file(db, text):
    out, err, rc = run(db, text)
    # psql -q still prints NOTICE lines on stderr; only ERROR/FATAL count
    bad = [l for l in err.split("\n") if "ERROR" in l or "FATAL" in l]
    return rc == 0 and not bad, "" if rc == 0 and not bad else err


def fresh_db(name, publication=True):
    # UTF8 like Supabase. (In an SQL_ASCII database char_length counts bytes and the
    # character classes of tfilah_clean would cut Hebrew letters in half.)
    q("postgres", "drop database if exists %s;" % name)
    q("postgres", "create database %s encoding 'UTF8' template template0 lc_collate 'C.utf8' lc_ctype 'C.utf8';" % name)
    if publication:
        q(name, "create publication supabase_realtime;")
    # Supabase hands ALL on new public tables to the API roles; reproduce that.
    q(name, "alter default privileges in schema public grant all on tables to anon, authenticated;"
            "grant usage on schema public to anon, authenticated;")


def new_memorial(db, name, listed=False):
    # the tests create more than 30 readings; age the earlier ones past the 10-minute flood guard
    q(db, "update memorials set created_at = created_at - interval '11 minutes' where created_at > now() - interval '10 minutes';")
    return one(db, "select create_memorial('%s','אב','בן','מי','', 'neshama', %s);" % (name, "true" if listed else "false"))


def main():
    new_sql = open(SQL, encoding="utf-8").read()
    # Every older version of the file found in git history is an upgrade starting point.
    olds = []
    try:
        revs = subprocess.run(["git", "-C", ROOT, "log", "--format=%h", "--", "supabase.sql"],
                              capture_output=True, text=True, check=True).stdout.split()
        for rev in reversed(revs):
            text = subprocess.run(["git", "-C", ROOT, "show", rev + ":supabase.sql"], capture_output=True, text=True, check=True).stdout
            if text != new_sql and text not in [t for _, t in olds]:
                olds.append(("commit " + rev, text))
    except Exception:
        olds = []

    print("server:", one("postgres", "select version();"))
    q("postgres", """do $$ begin
      if not exists (select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
      if not exists (select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
    end $$;""")

    A, B, C = "tfilah_test_fresh", "tfilah_test_upgrade", "tfilah_test_nopub"

    # ------------------------------------------------------------ 0. applying the file
    print("\n[0] applying supabase.sql")
    fresh_db(A)
    ok, err = apply_file(A, new_sql)
    check("fresh database: first run", ok, err)
    ok, err = apply_file(A, new_sql)
    check("fresh database: second run (re-run)", ok, err)
    pubs = q(A, "select tablename from pg_publication_tables where pubname='supabase_realtime' order by 1;")
    check("realtime publication holds chapters and memorials once each", pubs == ["chapters", "memorials"], pubs)

    fresh_db(C, publication=False)
    ok, err = apply_file(C, new_sql)
    check("database without supabase_realtime publication", ok, err)

    if not olds:
        print("  SKIP  upgrade path (no older supabase.sql in git)")
    for label, old_sql in olds:
        fresh_db(B)
        ok, err = apply_file(B, old_sql)
        check("upgrade from %s: old file applies" % label, ok, err)
        old_id = one(B, "select create_memorial('ישן','אב','בן','מי','','neshama');")
        q(B, "select claim_chapter('%s',1,'א'); select finish_chapter('%s',2,'ב'); select light_candle('%s');" % (old_id, old_id, old_id))
        ok, err = apply_file(B, new_sql)
        check("upgrade from %s: new file on top" % label, ok, err)
        ok, err = apply_file(B, new_sql)
        check("upgrade from %s: new file again" % label, ok, err)
        row = one(B, "select listed::text||'|'||done||'|'||candles||'|'||candle_n from memorials where id='%s';" % old_id)
        check("upgrade from %s: existing reading kept (10-char id, listed=false, done=1, candles=2)" % label, len(old_id) == 10 and row == "false|1|2|0", old_id + " " + row)
        j = one(B, "select get_memorial('%s') is not null;" % old_id, role="anon")
        check("upgrade from %s: the old link still opens through get_memorial" % label, j == "t", j)
        sigs = q(B, """select proname||'('||pg_get_function_identity_arguments(oid)||') -> '||pg_get_function_result(oid)
                       from pg_proc where pronamespace='public'::regnamespace order by 1;""")
        want = [
            "claim_chapter(p_mid text, p_n integer, p_by text) -> boolean",
            "create_memorial(p_name text, p_parent text, p_rel text, p_by text, p_msg text, p_kind text, p_listed boolean) -> text",
            "finish_chapter(p_mid text, p_n integer, p_by text) -> integer",
            "get_memorial(p_id text) -> json",
            "light_candle(p_mid text) -> void",
            "take_chapter(p_mid text, p_by text) -> integer",
            "tfilah_clean(t text) -> text",
            "tfilah_round(p_mid text) -> integer",
        ]
        check("upgrade from %s: exactly the 6 API functions and 2 helpers (old 6-arg create_memorial gone)" % label, sigs == want, sigs if sigs != want else "")
        r = one(B, "select take_chapter('%s','ג');" % old_id)
        check("upgrade from %s: take_chapter skips old claim 1 and done 2, gives 3" % label, r == "3", r)
        new_id = one(B, "select create_memorial('חדש','אב','בן','מי','','neshama');")
        check("upgrade from %s: a reading created after the upgrade gets a 16-char id" % label, len(new_id) == 16, new_id)

    db = A

    # ------------------------------------------------------------ 1. take_chapter
    print("\n[1] take_chapter: 40 concurrent sessions x 5 calls = 200 calls on one reading")
    m1 = new_memorial(db, "אחד")
    outs, errs = parallel(db, ["".join("select take_chapter('%s','s%d');\n" % (m1, i) for _ in range(5)) for i in range(40)])
    got = [l for o in outs for l in o]
    keys = [int(l) for l in got if l != ""]
    nulls = [l for l in got if l == ""]
    check("no error surfaced in any session", not errs, errs[:2])
    check("200 answers received", len(got) == 200, len(got))
    check("150 keys handed out", len(keys) == 150, len(keys))
    check("all keys distinct (no chapter given twice)", len(set(keys)) == len(keys), "%d distinct of %d" % (len(set(keys)), len(keys)))
    check("keys are exactly 1..150", sorted(keys) == list(range(1, 151)), "min %s max %s" % (min(keys or [0]), max(keys or [0])))
    check("the 50 calls past 150 got null", len(nulls) == 50, len(nulls))
    rows = one(db, "select count(*)||'|'||count(distinct by_name) from chapters where memorial_id='%s' and s='claimed';" % m1)
    check("table holds 150 claimed rows", rows.split("|")[0] == "150", rows + " (rows|distinct sessions that got one)")

    # ------------------------------------------------------------ 2. claim_chapter
    print("\n[2] claim_chapter: 20 concurrent sessions on the same key")
    m2 = new_memorial(db, "שתיים")
    outs, errs = parallel(db, ["select claim_chapter('%s',7,'c%d');\n" % (m2, i) for i in range(20)])
    got = [l for o in outs for l in o]
    check("no error surfaced", not errs, errs[:2])
    check("exactly one true, 19 false", got.count("t") == 1 and got.count("f") == 19, "true=%d false=%d" % (got.count("t"), got.count("f")))
    winner = one(db, "select by_name from chapters where memorial_id='%s' and n=7;" % m2)
    win_idx = [i for i, o in enumerate(outs) if o == ["t"]]
    check("the row belongs to the session that got true", len(win_idx) == 1 and winner == "c%d" % win_idx[0], winner)

    # ------------------------------------------------------------ 3. finish_chapter
    print("\n[3] finish_chapter: 30 concurrent sessions, 150 keys, each sent twice by its session and once by another")
    scripts = []
    for i in range(30):
        mine = range(i * 5 + 1, i * 5 + 6)
        other = range(((i + 1) % 30) * 5 + 1, ((i + 1) % 30) * 5 + 6)
        s = ""
        for n in mine:
            s += "select finish_chapter('%s',%d,'f%d');\n" % (m1, n, i) * 2
        for n in other:
            s += "select finish_chapter('%s',%d,'f%d');\n" % (m1, n, i)
        scripts.append(s)
    outs, errs = parallel(db, scripts)
    vals = [int(l) for o in outs for l in o if l != ""]
    check("no error surfaced", not errs, errs[:2])
    check("450 calls answered with a count", len(vals) == 450, len(vals))
    done = int(one(db, "select done from memorials where id='%s';" % m1))
    real = int(one(db, "select count(*) from chapters where memorial_id='%s' and s='done';" % m1))
    check("memorials.done = 150", done == 150, done)
    check("memorials.done equals real count of done rows", done == real, "done=%d rows=%d" % (done, real))
    check("returned counts stay within 1..150 and reach 150", vals and min(vals) >= 1 and max(vals) == 150, "min %s max %s" % (min(vals or [0]), max(vals or [0])))
    r = one(db, "select finish_chapter('%s',10,'again');" % m1)
    check("repeat after everything is done still returns 150", r == "150", r)
    r2 = one(db, "select take_chapter('%s','round2');" % m1)
    check("take_chapter now gives a round-2 key (151..300)", r2.isdigit() and 151 <= int(r2) <= 300, r2)

    # ------------------------------------------------------------ 4. stale claims
    print("\n[4] stale claims (24 hours)")
    m4 = new_memorial(db, "ארבע")
    r = q(db, "select claim_chapter('%s',3,'A'); select claim_chapter('%s',3,'B');" % (m4, m4))
    check("fresh claim: first true, second false", r == ["t", "f"], r)
    n_ok = one(db, "select count(*) filter (where claim_chapter('%s',g,'fill')) from generate_series(1,150) g;" % m4)
    check("filling the round: 149 new claims (key 3 already taken)", n_ok == "149", n_ok)
    r = one(db, "select take_chapter('%s','B');" % m4)
    check("take_chapter with all 150 freshly claimed: null", r == "", repr(r))
    q(db, "update chapters set at = now() - interval '23 hours' where memorial_id='%s' and n=6;" % m4)
    r = q(db, "select claim_chapter('%s',6,'B'); select take_chapter('%s','B');" % (m4, m4))
    check("23h old claim is not stale: claim false, take null", r == ["f", ""], r)
    q(db, "update chapters set at = now() - interval '25 hours' where memorial_id='%s' and n=3;" % m4)
    r = one(db, "select take_chapter('%s','B');" % m4)
    row = one(db, "select by_name||'|'||s||'|'||(at > now() - interval '1 minute') from chapters where memorial_id='%s' and n=3;" % m4)
    check("25h old claim: take_chapter takes it over (key 3)", r == "3", r)
    check("taken-over row now belongs to B with a fresh time", row == "B|claimed|true", row)
    r = one(db, "select take_chapter('%s','C');" % m4)
    check("and it cannot be taken again right away: null", r == "", repr(r))
    q(db, "update chapters set at = now() - interval '25 hours' where memorial_id='%s' and n=5;" % m4)
    r = q(db, "select claim_chapter('%s',5,'C'); select claim_chapter('%s',5,'D');" % (m4, m4))
    row = one(db, "select by_name from chapters where memorial_id='%s' and n=5;" % m4)
    check("25h old claim: claim_chapter takes it over once (true, then false)", r == ["t", "f"] and row == "C", "%s owner=%s" % (r, row))
    q(db, "select finish_chapter('%s',9,'E'); update chapters set at = now() - interval '25 hours' where memorial_id='%s' and n=9;" % (m4, m4))
    r = q(db, "select claim_chapter('%s',9,'X'); select take_chapter('%s','X');" % (m4, m4))
    row = one(db, "select s||'|'||by_name from chapters where memorial_id='%s' and n=9;" % m4)
    check("an old DONE chapter is never taken over", r == ["f", ""] and row == "done|E", "%s row=%s" % (r, row))
    q(db, "update chapters set at = now() - interval '25 hours' where memorial_id='%s' and n=20;" % m4)
    outs, errs = parallel(db, ["select take_chapter('%s','t%d');\n" % (m4, i) for i in range(10)] +
                              ["select claim_chapter('%s',20,'k%d');\n" % (m4, i) for i in range(10)])
    got = [l for o in outs for l in o]
    wins = got.count("20") + got.count("t")
    check("one stale key, 10 take + 10 claim at once: exactly one winner, no error", wins == 1 and not errs, "winners=%d errs=%d" % (wins, len(errs)))

    # ------------------------------------------------------------ 5. privacy / role anon
    print("\n[5] privacy, as role anon")
    L = new_memorial(db, "גלוי", listed=True)
    U = new_memorial(db, "נסתר", listed=False)
    H = new_memorial(db, "חסום", listed=True)
    q(db, "select claim_chapter('%s',1,'x'); select claim_chapter('%s',1,'x'); select finish_chapter('%s',2,'y'); select claim_chapter('%s',1,'x');" % (L, U, U, H))
    q(db, "update memorials set hidden = true where id='%s';" % H)
    total = one(db, "select count(*) from memorials;")
    r = q(db, "select id from memorials;", role="anon")
    check("direct select on memorials returns only the listed, non-hidden row", r == [L], "%d of %s rows visible" % (len(r), total))
    r = q(db, "select distinct memorial_id from chapters;", role="anon")
    check("direct select on chapters returns only chapters of listed readings", r == [L], r)
    j = one(db, "select get_memorial('%s');" % U, role="anon")
    d = json.loads(j) if j else None
    shape = bool(d) and sorted(d["memorial"].keys()) == sorted(["id", "name", "parent", "rel", "kind", "by_name", "msg", "candles", "done", "listed", "created_at"]) \
        and [sorted(c.keys()) for c in d["chapters"]] == [["at", "by_name", "n", "s"]] * 2
    check("get_memorial returns the unlisted reading with the documented shape", shape and d["memorial"]["id"] == U and d["memorial"]["listed"] is False and d["memorial"]["done"] == 1
          and [(c["n"], c["s"]) for c in d["chapters"]] == [(1, "claimed"), (2, "done")], j[:80])
    r = q(db, "select get_memorial('%s') is null; select get_memorial('nosuchid') is null;" % H, role="anon")
    check("get_memorial is null for hidden and for unknown id", r == ["t", "t"], r)

    def denied(sql):
        out, err, rc = run(db, sql, role="anon")
        return rc != 0 and "permission denied" in err, err.split("\n")[0]
    for label, sql in [("insert into memorials", "insert into memorials(name,rel) values ('x','בן');"),
                       ("update memorials", "update memorials set listed = true;"),
                       ("delete from memorials", "delete from memorials;"),
                       ("insert into chapters", "insert into chapters(memorial_id,n,s) values ('%s',50,'done');" % L),
                       ("update chapters", "update chapters set s='done';"),
                       ("truncate chapters", "truncate chapters;")]:
        ok, err = denied(sql)
        check("direct %s denied" % label, ok, err)
    # Second line of defence: even if the table privileges were ALL (Supabase default), RLS holds.
    q(db, "grant all on memorials, chapters to anon;")
    out, err, rc = run(db, "insert into memorials(name,rel) values ('x','בן');", role="anon")
    check("with ALL table privileges: insert blocked by row level security", rc != 0 and "row-level security" in err, err.split("\n")[0])
    before = one(db, "select md5(string_agg(m::text, ',' order by id)) from memorials m;")
    cmd = psql_cmd(db, "anon")
    cmd.remove("-q")
    p = subprocess.run(cmd + ["-c", "update memorials set listed = true, hidden = false", "-c", "delete from chapters"], capture_output=True, text=True)
    after = one(db, "select md5(string_agg(m::text, ',' order by id)) from memorials m;")
    check("with ALL table privileges: update/delete change 0 rows", p.stdout.split() == ["UPDATE", "0", "DELETE", "0"] and before == after, p.stdout.split())
    q(db, "revoke all on memorials, chapters from anon; grant select on memorials, chapters to anon;")

    r = q(db, """select create_memorial(p_name => 'דרך anon', p_parent => '', p_rel => 'בת', p_by => '', p_msg => '') as id \\gset
                 select listed from memorials where id = :'id';""")
    a_id = one(db, "select create_memorial(p_name => 'anon', p_parent => '', p_rel => 'בת', p_by => '', p_msg => '');", role="anon")
    a_listed = one(db, "select listed from memorials where id='%s';" % a_id)
    b_id = one(db, "select create_memorial(p_name => 'anon', p_parent => '', p_rel => 'בת', p_by => '', p_msg => '', p_kind => 'refuah', p_listed => true);", role="anon")
    b_row = one(db, "select listed::text||'|'||kind from memorials where id='%s';" % b_id)
    check("anon create_memorial without p_listed: link-only", len(a_id) == 16 and a_listed == "f", a_listed)
    check("anon create_memorial with p_listed => true: listed", b_row == "true|refuah", b_row)
    r = q(db, "select take_chapter('%s','a'); select claim_chapter('%s',1,'b'); select claim_chapter('%s',2,'b'); select finish_chapter('%s',1,'a'); select finish_chapter('%s',1,'a');"
          % (a_id, a_id, a_id, a_id, a_id), role="anon")
    check("anon on a link-only reading: take=1, claim 1=false, claim 2=true, finish=1, finish again=1", r == ["1", "f", "t", "1", "1"], r)
    c0 = int(one(db, "select candles from memorials where id='%s';" % a_id))
    q(db, "select light_candle('%s');" % a_id, role="anon")
    c1 = int(one(db, "select candles from memorials where id='%s';" % a_id))
    check("light_candle adds one candle", c1 == c0 + 1, "%d -> %d" % (c0, c1))
    out, err, rc = run(db, "select take_chapter('%s','z'); select claim_chapter('%s',5,'z'); select finish_chapter('%s',5,'z');"
                           "select take_chapter('nosuchid','z'); select claim_chapter('nosuchid',5,'z'); select finish_chapter('nosuchid',5,'z');"
                           "select finish_chapter('%s',0,'z'); select claim_chapter('%s',15001,'z');" % (H, H, H, a_id, a_id), role="anon")
    hrows = one(db, "select count(*)||'|'||(select done from memorials where id='%s') from chapters where memorial_id='%s';" % (H, H))
    check("hidden / unknown reading / bad key: null or false, no error, nothing written",
          rc == 0 and err == "" and out == ["", "f", "", "", "f", "", "", "f"] and hrows == "1|0", "%s err=%r rows|done=%s" % (out, err, hrows))

    # ------------------------------------------------------------ 7. abuse, as role anon
    print("\n[7] abuse with only the public key (role anon)")
    import re
    ids = [new_memorial(db, "מזהה%d" % i) for i in range(20)]
    check("ids: 16 lowercase hex characters, all distinct", all(re.fullmatch("[0-9a-f]{16}", x) for x in ids) and len(set(ids)) == 20, ids[0])
    dflt = one(db, "select pg_get_expr(adbin, adrelid) from pg_attrdef d join pg_attribute a on a.attrelid=d.adrelid and a.attnum=d.adnum where a.attrelid='memorials'::regclass and a.attname='id';")
    check("id default uses gen_random_uuid (cryptographic), not random()", "gen_random_uuid" in dflt and "random()" not in dflt, dflt)
    out, err, rc = run(db, "select tfilah_round('%s');" % ids[0], role="anon")
    out2, err2, rc2 = run(db, "select tfilah_clean('x');", role="anon")
    check("helpers tfilah_round / tfilah_clean are not callable by anon", rc != 0 and "permission denied" in err and rc2 != 0 and "permission denied" in err2, err.split("\n")[0])
    cfg = q(db, "select proname||':'||prosecdef||':'||array_to_string(proconfig, ',') from pg_proc where pronamespace='public'::regnamespace order by 1;")
    check("every function pins search_path = public, pg_temp", all(c.endswith("search_path=public, pg_temp") for c in cfg), [c for c in cfg if not c.endswith("search_path=public, pg_temp")])

    # enumeration: nothing but listed rows through any direct read
    r = q(db, "select count(*) from memorials where not listed; select count(*) from memorials where hidden; select count(*) from chapters c join memorials m on m.id=c.memorial_id where not m.listed or m.hidden;", role="anon")
    check("anon cannot see any unlisted or hidden row, even by filtering on those columns", r == ["0", "0", "0"], r)
    r = q(db, "select get_memorial(null) is null; select get_memorial('') is null; select get_memorial('%') is null; select get_memorial(left('" + U + "', 9)) is null; select get_memorial('" + U + "' || ' ') is null;", role="anon")
    check("get_memorial needs the exact id (null, empty, wildcard, prefix, padded: all null)", r == ["t"] * 5, r)

    # out-of-range and out-of-round keys
    K = new_memorial(db, "מפתחות")
    r = q(db, "select claim_chapter('%s',151,'x'); select claim_chapter('%s',15000,'x'); select finish_chapter('%s',151,'x') is null; select finish_chapter('%s',15000,'x') is null;"
              "select finish_chapter('%s',-5,'x') is null; select claim_chapter('%s',2147483647,'x'); select claim_chapter('%s',null,'x'); select finish_chapter('%s',null,'x') is null;" % ((K,) * 8), role="anon")
    rows = one(db, "select count(*)||'|'||(select done from memorials where id='%s') from chapters where memorial_id='%s';" % (K, K))
    check("keys beyond the current round (151, 15000) and invalid keys: refused, nothing written", r == ["f", "f", "t", "t", "t", "f", "f", "t"] and rows == "0|0", "%s rows|done=%s" % (r, rows))
    out, err, rc = run(db, "select claim_chapter('%s', 99999999999, 'x');" % K, role="anon")
    check("key too large for an integer: an error, nothing written", rc != 0 and one(db, "select count(*) from chapters where memorial_id='%s';" % K) == "0", err.split("\n")[0][:60])
    r = q(db, "select claim_chapter('%s',150,'x'); select finish_chapter('%s',1,'x');" % (K, K), role="anon")
    check("keys inside round 1 still work (claim 150 -> true, finish 1 -> 1)", r == ["t", "1"], r)
    q(db, "select finish_chapter('%s', g, 'r1') from generate_series(1,150) g;" % K)
    r = q(db, "select claim_chapter('%s',151,'x'); select finish_chapter('%s',300,'x'); select claim_chapter('%s',301,'x'); select finish_chapter('%s',301,'x') is null; select finish_chapter('%s',7,'again');" % ((K,) * 5), role="anon")
    check("after round 1 is complete: round 2 keys open (151 true, 300 -> 151), round 3 still closed, old key idempotent (151)", r == ["t", "151", "f", "t", "151"], r)

    # marking chapters en masse: bounded per hour
    V = new_memorial(db, "ונדל")
    got = q(db, "select count(*) filter (where x is not null) from (select finish_chapter('%s', g, 'v') x from generate_series(1,3300) g) t;" % V, role="anon")
    state = one(db, "select done||'|'||(select count(*) from chapters where memorial_id='%s') from memorials where id='%s';" % (V, V))
    check("3300 finish calls in a row on one reading: 3000 accepted, the rest refused, done = rows", got == ["3000"] and state == "3000|3000", "%s accepted, done|rows=%s" % (got, state))
    r = q(db, "select finish_chapter('%s', 5, 'again'); select finish_chapter('%s', 3001, 'v') is null;" % (V, V), role="anon")
    check("at the cap: repeating an already-done key still answers (3000), a new key is refused", r == ["3000", "t"], r)
    q(db, "update chapters set at = now() - interval '61 minutes' where memorial_id='%s' and n <= 10;" % V)
    r = q(db, "select finish_chapter('%s', 3001, 'v'); " % V, role="anon")
    check("an hour later the cap lets marks through again", r == ["3001"], r)

    # candles
    Cn = new_memorial(db, "נרות")
    q(db, "select light_candle('%s') from generate_series(1,700);" % Cn, role="anon")
    c = one(db, "select candles||'|'||candle_n from memorials where id='%s';" % Cn)
    check("700 candles in a row on one reading: 600 counted (1 + 600 = 601), no error", c == "601|600", c)
    q(db, "update memorials set candle_win = now() - interval '61 minutes' where id='%s';" % Cn)
    q(db, "select light_candle('%s'); select light_candle('%s');" % (Cn, Cn), role="anon")
    c = one(db, "select candles||'|'||candle_n from memorials where id='%s';" % Cn)
    check("an hour later candles count again (603, window restarted at 2)", c == "603|2", c)
    q(db, "update memorials set candles = 2147483647, candle_n = 0 where id='%s';" % Cn)
    out, err, rc = run(db, "select light_candle('%s');" % Cn, role="anon")
    check("(candles at the integer maximum raises 'out of range' rather than wrapping)", rc != 0 and "out of range" in err, err.split("\n")[0][:60])

    # text fields
    def mk(name="שם", parent="", by="", msg="", rel="בן", kind="neshama"):
        o, e, rc_ = run(db, "select create_memorial(%s,%s,%s,%s,%s,%s);" % tuple("E'%s'" % x.replace("'", "''") for x in (name, parent, rel, by, msg, kind)), role="anon")
        return (o[-1] if o and rc_ == 0 else None), e
    ok_all = True; detail = []
    for label, kw in [("name 61 chars", dict(name="א" * 61)), ("parent 41", dict(parent="א" * 41)), ("by 61", dict(by="א" * 61)), ("msg 201", dict(msg="א" * 201)),
                      ("name 1 MB", dict(name="א" * 500000)), ("empty name", dict(name="")), ("spaces only", dict(name="   ")), ("newlines/tabs only", dict(name="\\n\\t\\r")),
                      ("zero-width only", dict(name="\\u200B\\u200F\\u202E\\uFEFF")), ("bad rel", dict(rel="x")), ("bad kind", dict(kind="spam"))]:
        mid, e = mk(**kw)
        if mid is not None or "check constraint" not in e:
            ok_all = False; detail.append(label + ": " + (mid or e[:60]))
    check("oversized / empty / invisible-only / invalid fields are all refused (11 cases)", ok_all, detail)
    mid, e = mk(name="א" * 60, parent="ב" * 40, by="ג" * 60, msg="ד" * 200)
    check("fields exactly at their limits, in Hebrew, are accepted (limits count characters, not bytes)", mid is not None, e[:80])
    mid, e = mk(name="  דוד\\n\\n  בן\\tישי  ", by="\\u202Eevil\\u202C", msg="שורה\\r\\nשנייה \\u200F<b>")
    row = one(db, "select name||'|'||by_name||'|'||msg from memorials where id='%s';" % mid) if mid else ""
    check("control characters become spaces, direction overrides are removed, HTML is stored as plain text", row == "דוד בן ישי|evil|שורה שנייה <b>", row)
    q(db, "select claim_chapter('%s', 1, E'  \\u202Eרע\\n\\nמאוד  %s');" % (K2 := new_memorial(db, "שמות"), "x" * 100), role="anon")
    row = one(db, "select by_name from chapters where memorial_id='%s' and n=1;" % K2)
    check("chapter reader name: cleaned and cut to 40 characters", row == ("רע מאוד " + "x" * 100)[:40], row)
    out, err, rc = run(db, "select create_memorial('a''); drop table memorials; --','','בן','','');", role="anon")
    check("SQL metacharacters in a name are stored as text", rc == 0 and one(db, "select name from memorials where id='%s';" % out[-1]) == "a'); drop table memorials; --")

    # hidden really hides everywhere
    Hd = new_memorial(db, "להסתרה", listed=True)
    q(db, "select claim_chapter('%s',1,'x'); select finish_chapter('%s',2,'x'); update memorials set hidden = true where id='%s';" % (Hd, Hd, Hd))
    before = one(db, "select md5(row(m.*)::text) || (select md5(string_agg(c::text, ',' order by n)) from chapters c where memorial_id=m.id) from memorials m where id='%s';" % Hd)
    r = q(db, "select count(*) from memorials where id='%s'; select count(*) from chapters where memorial_id='%s'; select get_memorial('%s') is null;"
              "select take_chapter('%s','z') is null; select claim_chapter('%s',3,'z'); select finish_chapter('%s',1,'z') is null; select light_candle('%s') is null;" % ((Hd,) * 7), role="anon")
    after = one(db, "select md5(row(m.*)::text) || (select md5(string_agg(c::text, ',' order by n)) from chapters c where memorial_id=m.id) from memorials m where id='%s';" % Hd)
    check("hidden reading: invisible in both tables and get_memorial; take/claim/finish/candle change nothing", r == ["0", "0", "t", "t", "f", "t", "t"] and before == after, r)

    # creation flood guard under concurrency (last: it fills the 10-minute quota)
    q(db, "update memorials set created_at = now() - interval '11 minutes';")
    outs, errs = parallel(db, ["select create_memorial('הצפה %d','','בן','','');\n" % i * 2 for i in range(40)], role="anon")
    made = sum(len(o) for o in outs)
    n_new = one(db, "select count(*) from memorials where created_at > now() - interval '10 minutes';")
    check("80 concurrent create_memorial calls: exactly 30 get in, 50 are refused", made == 30 and n_new == "30" and len(errs) > 0 and all("too many new pages" in e for e in errs), "created=%d in table=%s" % (made, n_new))
    q(db, "update memorials set created_at = now() - interval '11 minutes';")

    # ------------------------------------------------------------ 6. shim.js
    shim_test = os.path.join(ROOT, "tools", "test-supabase-shim.js")
    if shutil.which("node") and os.path.exists(shim_test):
        print("\n[6] shim.js against the same database (tools/test-supabase-shim.js)")
        p = subprocess.run(["node", shim_test], env=dict(os.environ, PGDATABASE=db), capture_output=True, text=True)
        sys.stdout.write(p.stdout)
        if p.stderr.strip():
            sys.stdout.write(p.stderr)
        check("shim.js test run", p.returncode == 0, "exit %d" % p.returncode)
    else:
        print("\n[6] SKIP shim.js test (node not found)")

    if not KEEP:
        q("postgres", "".join("drop database if exists %s;" % n for n in (A, B, C)))

    failed = [n for n, ok in results if not ok]
    print("\n%d checks, %d passed, %d failed" % (len(results), len(results) - len(failed), len(failed)))
    for n in failed:
        print("  FAILED:", n)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
