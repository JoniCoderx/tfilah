#!/usr/bin/env python3
"""The SEO face of every built page, as Google reads it: title, description, canonical, robots, H1 and structured-data types.

  python3 tools/seo-snapshot.py write tools/seo-baseline.json   # record the current pages as the baseline
  python3 tools/seo-snapshot.py check tools/seo-baseline.json   # compare the current build with the baseline

`check` lists every page whose SEO changed, was added or was removed, and exits 1 if any did. It reads the built
files in the repository, so run it after tools/prerender.py, tools/build.py and tools/brachot/build.py."""
import glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def face(s):
    g = lambda rx: (lambda m: html.unescape(m.group(1)).strip() if m else "")(re.search(rx, s, re.S))
    types = []
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            x = json.loads(b); types.append(x.get("@type", "?") if isinstance(x, dict) else "list")
        except ValueError:
            types.append("INVALID")
    return {"title": g(r"<title>(.*?)</title>"), "desc": g(r'<meta name="description" content="([^"]*)"'),
            "canonical": g(r'<link rel="canonical" href="([^"]*)"'), "robots": g(r'<meta name="robots" content="([^"]*)"'),
            "h1": re.sub(r"<[^>]+>", "", g(r"<h1[^>]*>(.*?)</h1>")), "ld": sorted(types)}

def snapshot():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(("tools" + os.sep, "src" + os.sep, "admin" + os.sep, "node_modules" + os.sep)):
            continue
        path = "/" + rel[: -len("index.html")].replace(os.sep, "/")
        out[path] = face(open(f, encoding="utf-8").read())
    return out

if __name__ == "__main__":
    mode, file = sys.argv[1], sys.argv[2]
    now = snapshot()
    if mode == "write":
        json.dump(now, open(file, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
        print(f"wrote {len(now)} pages to {file}")
        sys.exit(0)
    base = json.load(open(file, encoding="utf-8"))
    changed = [p for p in now if p in base and now[p] != base[p]]
    added, removed = [p for p in now if p not in base], [p for p in base if p not in now]
    for p in changed[:30]:
        diff = {k: (base[p][k], now[p][k]) for k in now[p] if now[p][k] != base[p].get(k)}
        print("CHANGED", p, json.dumps(diff, ensure_ascii=False)[:300])
    for p in added[:30]: print("ADDED", p)
    for p in removed[:30]: print("REMOVED", p)
    print(f"pages {len(now)} · changed {len(changed)} · added {len(added)} · removed {len(removed)}")
    sys.exit(1 if changed or added or removed else 0)
