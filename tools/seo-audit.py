"""SEO audit of the generated static pages (output of tools/prerender.py).

Checks what is on disk, not what the generator intended:
  sitemap <-> pages, one <h1>, title, description, self canonical, lang/dir,
  duplicate titles, internal links, empty prayer texts.

Run from the site root:  python3 tools/seo-audit.py
Exit code is non-zero when there are failures. Standard library only.
"""
import os, re, sys, html, collections

ROOT = os.getcwd()
SITE = "https://tfilah.com"
SECTIONS = ("tehillim", "tefila", "sefer")
MAX_EXAMPLES = 5

fails = collections.OrderedDict()   # check name -> list of messages
infos = collections.OrderedDict()

def fail(check, msg):
    fails.setdefault(check, []).append(msg)

def info(check, msg):
    infos.setdefault(check, []).append(msg)

def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def attr(tag, name):
    m = re.search(r'\b' + name + r'\s*=\s*"([^"]*)"', tag) or re.search(r"\b" + name + r"\s*=\s*'([^']*)'", tag)
    return html.unescape(m.group(1)) if m else None

def page_file(path):
    """/tefila/x/ -> <root>/tefila/x/index.html"""
    return os.path.join(ROOT, path.strip("/"), "index.html")

# ---------- pages on disk ----------
disk = {}   # url path -> file
for sec in SECTIONS:
    for d, _, files in os.walk(os.path.join(ROOT, sec)):
        if "index.html" in files:
            rel = os.path.relpath(d, ROOT).replace(os.sep, "/")
            disk["/" + rel + "/"] = os.path.join(d, "index.html")

# ---------- sitemap ----------
sm_path = os.path.join(ROOT, "sitemap.xml")
locs = []
if not os.path.exists(sm_path):
    fail("sitemap", "sitemap.xml is missing")
else:
    locs = [html.unescape(x.strip()) for x in re.findall(r"<loc>(.*?)</loc>", open(sm_path, encoding="utf-8").read(), flags=re.S)]
dups = [u for u, c in collections.Counter(locs).items() if c > 1]
for u in dups:
    fail("sitemap: duplicate <loc>", u)
sm_paths = set()
for u in set(locs):
    if not u.startswith(SITE + "/"):
        fail("sitemap: <loc> outside the site", u)
        continue
    path = u[len(SITE):]
    sm_paths.add(path)
    if not path.endswith("/"):
        fail("sitemap: <loc> without trailing slash", u)
    if not os.path.isfile(page_file(path)):
        fail("sitemap: <loc> has no index.html on disk", u)
for path in sorted(disk):
    if path not in sm_paths:
        fail("page on disk missing from sitemap", path)

# ---------- per page ----------
titles = collections.defaultdict(list)
h1nus = collections.defaultdict(list)
prayer_titles = collections.defaultdict(list)   # (nusach, h1 text without context) -> paths
link_cache = {}
n_links = 0

def link_ok(href):
    """internal href starting with "/" resolves to a page or a file on disk"""
    target = href.split("#", 1)[0].split("?", 1)[0]
    if target in link_cache:
        return link_cache[target]
    fs = os.path.join(ROOT, target.lstrip("/"))
    if target.endswith("/"):
        ok = os.path.isfile(os.path.join(fs, "index.html"))
    else:
        ok = os.path.isfile(fs)   # /brand/..., /icons/..., /manifest.webmanifest; a page link without "/" is a failure
    link_cache[target] = ok
    return ok

for path, f in sorted(disk.items()):
    doc = open(f, encoding="utf-8").read()
    own = SITE + path

    m = re.search(r"<html\b[^>]*>", doc, flags=re.I)
    tag = m.group(0) if m else ""
    if attr(tag, "lang") != "he": fail("html lang is not he", path)
    if attr(tag, "dir") != "rtl": fail("html dir is not rtl", path)

    h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", doc, flags=re.S | re.I)
    if len(h1s) != 1:
        fail("page does not have exactly one <h1>", f"{path} ({len(h1s)})")
    h1_full = strip_tags(h1s[0]) if h1s else ""
    if h1s and not h1_full:
        fail("empty <h1>", path)
    h1_main = strip_tags(re.sub(r'<span class="ctx">.*?</span>', "", h1s[0], flags=re.S)) if h1s else ""

    ts = re.findall(r"<title\b[^>]*>(.*?)</title>", doc.split("</head>", 1)[0], flags=re.S | re.I)
    title = strip_tags(ts[0]) if ts else ""
    if len(ts) != 1 or not title:
        fail("missing or empty <title>", path)
    else:
        titles[title].append(path)

    dm = re.search(r'<meta\s+name="description"[^>]*>', doc, flags=re.I)
    if not dm or not (attr(dm.group(0), "content") or "").strip():
        fail("missing or empty meta description", path)

    cans = re.findall(r'<link\b[^>]*rel="canonical"[^>]*>', doc, flags=re.I)
    can = attr(cans[0], "href") if cans else None
    if len(cans) != 1:
        fail("page does not have exactly one canonical", f"{path} ({len(cans)})")
    elif can != own:
        kind = "canonical points to the home page" if can in (SITE, SITE + "/") else "canonical is not the page's own URL"
        fail(kind, f"{path} -> {can}")

    for prop, want in (("og:url", own), ("og:image", SITE + "/icons/og.png"), ("og:site_name", "תפילה")):
        om = re.search(r'<meta\s+property="' + prop + r'"[^>]*>', doc, flags=re.I)
        if not om or attr(om.group(0), "content") != want:
            fail("Open Graph " + prop + " missing or wrong", path)
    for prop in ("og:title", "og:description"):
        om = re.search(r'<meta\s+property="' + prop + r'"[^>]*>', doc, flags=re.I)
        if not om or not (attr(om.group(0), "content") or "").strip():
            fail("Open Graph " + prop + " missing", path)
    if '"BreadcrumbList"' not in doc:
        fail("breadcrumb JSON-LD missing", path)

    # nusach of a prayer page comes from its URL: /tefila/<nusach>-<n>/
    parts = path.strip("/").split("/")
    nus = ""
    if parts[0] == "tefila" and len(parts) == 2:
        nus = parts[1].rsplit("-", 1)[0]
        prayer_titles[(nus, h1_main)].append(path)
    h1nus[(h1_full, nus)].append(path)

    # reading pages must carry text
    if len(parts) == 2:
        am = re.search(r'<article\b[^>]*id="text"[^>]*>(.*?)</article>', doc, flags=re.S | re.I)
        if not am or len(strip_tags(am.group(1))) < 10:
            fail("reading page with an empty text body", path)

    # internal links
    body_and_head = doc
    for href in set(re.findall(r'<(?:a|link)\b[^>]*?\bhref="([^"]*)"', body_and_head, flags=re.I)):
        href = html.unescape(href)
        if not href.startswith("/") or href.startswith("//"):
            continue
        if href == "/" or href.startswith("/#"):
            continue   # the app itself and its hash routes
        n_links += 1
        if not link_ok(href):
            fail("broken internal link", f"{path} -> {href}")

if not os.path.isfile(os.path.join(ROOT, "index.html")):
    fail("home page", "index.html is missing at the root (target of / and /#... links)")

for t, ps in titles.items():
    if len(ps) > 1:
        fail("duplicate <title>", f"{t!r}: {', '.join(ps[:4])}{' …' if len(ps) > 4 else ''} ({len(ps)} pages)")
for (h, nus), ps in h1nus.items():
    if len(ps) > 1:
        info("duplicate H1 + nusach", f"{h!r} [{nus or '-'}]: {', '.join(ps[:4])}{' …' if len(ps) > 4 else ''} ({len(ps)} pages)")
for (nus, h), ps in prayer_titles.items():
    if len(ps) > 1:
        info("same prayer title in one nusach (compete for one search intent)", f"{h!r} [{nus}]: {len(ps)} pages, e.g. {', '.join(ps[:3])}")

# ---------- report ----------
count = collections.Counter(p.strip("/").split("/")[0] + ("" if p.count("/") > 2 else " (hub)") for p in disk)
print("SEO audit of", ROOT)
print(f"  pages on disk: {len(disk)}  (" + ", ".join(f"{k}: {v}" for k, v in sorted(count.items())) + ")")
print(f"  sitemap: {len(locs)} <loc>, {len(set(locs))} unique, {len(dups)} duplicated")
print(f"  unique titles: {len(titles)}   internal link targets checked: {len(link_cache)} ({n_links} links)")

print(f"  duplicate titles: {sum(1 for v in titles.values() if len(v) > 1)}   duplicate H1+nusach combinations: {sum(1 for v in h1nus.values() if len(v) > 1)}"
      f"   same-title groups within a nusach: {sum(1 for v in prayer_titles.values() if len(v) > 1)}")

def show(groups, label):
    for check, msgs in groups.items():
        print(f"  [{label}] {check}: {len(msgs)}")
        for m in msgs[:MAX_EXAMPLES]:
            print("      " + m)
        if len(msgs) > MAX_EXAMPLES:
            print(f"      … and {len(msgs) - MAX_EXAMPLES} more")

if infos:
    print("Informational:")
    show(infos, "info")
if fails:
    print("Failures:")
    show(fails, "FAIL")
    print(f"RESULT: FAILED, {sum(len(v) for v in fails.values())} problems in {len(fails)} checks")
    sys.exit(1)
print("RESULT: OK, no failures")
