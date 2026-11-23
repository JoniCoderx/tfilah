"""SEO audit of the generated static pages (output of tools/prerender.py and tools/build.py).

Checks what is on disk, not what the generator intended:
  sitemap <-> pages (both directions), one <h1>, unique title, description (present,
  120 to 160 characters, unique), self canonical with trailing slash, lang/dir, viewport,
  Open Graph and twitter card, no accidental noindex, JSON-LD parses, internal links resolve,
  every page has at least one inbound internal link, app hash routes exist,
  404.html, robots.txt, fonts (preconnect + display=swap), no em dash in generated copy,
  reading pages carry text.

Run from the site root:  python3 tools/seo-audit.py
Exit code is non-zero when there are failures. Standard library only.
"""
import os, re, sys, html, json, collections

ROOT = os.getcwd()
SITE = "https://tfilah.com"
NOT_PAGES = {"data", "brand", "icons", "src", "tools", "functions", "node_modules"}
MAX_EXAMPLES = 5
DESC_MIN, DESC_MAX = 120, 160

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

def read(*parts):
    f = os.path.join(ROOT, *parts)
    return open(f, encoding="utf-8").read() if os.path.isfile(f) else None

def page_file(path):
    """/tefila/x/ -> <root>/tefila/x/index.html"""
    return os.path.join(ROOT, path.strip("/"), "index.html")

# ---------- drafts: pages that exist but are not published (waiting for a review). They must say noindex, carry no
# canonical, and stay out of the sitemap; none of the publishing checks below apply to them. ----------
DRAFTS = json.load(open(os.path.join(ROOT, "tools", "drafts.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "tools", "drafts.json")) else []
_sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "sitemap.xml")) else ""
for _d in DRAFTS:
    _f = os.path.join(ROOT, _d.strip("/"), "index.html")
    if not os.path.exists(_f):
        continue
    _h = open(_f, encoding="utf-8").read()
    if '<meta name="robots" content="noindex">' not in _h:
        fail("a draft page does not say noindex", _d)
    if 'rel="canonical"' in _h:
        fail("a draft page carries a canonical", _d)
    if f"{SITE}{_d}</loc>" in _sm:
        fail("a draft page is listed in the sitemap", _d)

# ---------- pages on disk ----------
disk = {}   # url path -> file
for top in sorted(os.listdir(ROOT)):
    if top.startswith(".") or top in NOT_PAGES or not os.path.isdir(os.path.join(ROOT, top)):
        continue
    for d, _, files in os.walk(os.path.join(ROOT, top)):
        if "index.html" in files:
            rel = os.path.relpath(d, ROOT).replace(os.sep, "/")
            if "/" + rel + "/" in DRAFTS:
                continue
            disk["/" + rel + "/"] = os.path.join(d, "index.html")

# ---------- what the app can route to ----------
routes = {"t": set(str(i) for i in range(1, 151)), "p": set(), "b": set(), "k": set(), "kli": set(),
          "named": {"home", "siddur", "search", "tehillim", "favorites", "zikaron", "znew", "rav", "sifriya", "kelim", "tmicha"}}
try:
    routes["p"] = {p["id"] for p in json.loads(read("data", "index.json"))["prayers"]}
    routes["b"] = set(json.loads(read("data", "books.json")))
except Exception as e:
    fail("data", f"cannot read data/index.json or data/books.json: {e}")
app = read("src", "app.html")
if app is None:
    fail("app source", "src/app.html is missing (needed to validate hash routes)")
else:
    m = re.search(r"const NEEDS=(\[.*?\]);", app, flags=re.S)
    routes["k"] = set(re.findall(r"\['([a-z]+)','[a-z]+','", m.group(1))) if m else set()
    m = re.search(r"const KELIM=(\[.*?\]);", app, flags=re.S)
    routes["kli"] = set(re.findall(r"\['([a-z]+)','", m.group(1))) if m else set()
    m = re.search(r"\(\{((?:[a-z]+:[^,}]+,?)+)\}\[h\]", app)
    if m:
        routes["named"] = {"home"} | set(re.findall(r"([a-z]+):", m.group(1)))
    if not routes["k"] or not routes["kli"]:
        fail("app source", "NEEDS or KELIM not found in src/app.html")

def hash_ok(h):
    """h = the part after '/#'"""
    m = re.fullmatch(r"t-(\d+)(?:-(\d+))?", h)
    if m:
        return m.group(1) in routes["t"] and (m.group(2) is None or (m.group(2) in routes["t"] and int(m.group(2)) >= int(m.group(1))))
    for pre in ("kli", "p", "b", "k"):
        if h.startswith(pre + "-"):
            return h[len(pre) + 1:] in routes[pre]
    return h in routes["named"]

# ---------- sitemap ----------
sm_raw = read("sitemap.xml")
locs = []
if sm_raw is None:
    fail("sitemap", "sitemap.xml is missing")
else:
    locs = [html.unescape(x.strip()) for x in re.findall(r"<loc>(.*?)</loc>", sm_raw, flags=re.S)]
    for lm in re.findall(r"<lastmod>(.*?)</lastmod>", sm_raw):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm):
            fail("sitemap: bad <lastmod>", lm)
    if sm_raw.count("<url>") != sm_raw.count("<lastmod>"):
        fail("sitemap", "not every <url> has a <lastmod>")
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
    if not os.path.isfile(os.path.join(ROOT, "index.html") if path == "/" else page_file(path)):
        fail("sitemap: <loc> has no index.html on disk", u)
if locs and "/" not in sm_paths:
    fail("sitemap", "the home page is missing")
# exact repeats of a text inside one nusach: readable at their own address, canonical to the first, not in the sitemap
DUPC = json.load(open(os.path.join(ROOT, "tools", "dup-canon.json"), encoding="utf-8"))
for a, b in DUPC.items():
    if a in sm_paths:
        fail("a repeat page is listed in the sitemap", a)
    if b not in sm_paths or b in DUPC:
        fail("a repeat page names a canonical that is not an indexable page", f"{a} -> {b}")
for path in sorted(disk):
    if path not in sm_paths and path not in DUPC:
        fail("page on disk missing from sitemap", path)

# ---------- per page ----------
titles = collections.defaultdict(list)
descs = collections.defaultdict(list)
h1nus = collections.defaultdict(list)
prayer_titles = collections.defaultdict(list)   # (nusach, h1 text without context) -> paths
inbound = collections.Counter()
link_cache = {}
n_links = n_hash = n_ld = 0
desc_len = []
_PURLS = json.load(open(os.path.join(ROOT, "data", "urls.json"), encoding="utf-8"))          # prayer id -> address
_PNUS = {v: k.split("-")[0] for k, v in _PURLS.items()}                                          # address -> nusach
READING = re.compile(r"/tehillim/(?!yomi/)[a-z0-9-]+/|/sefer/[a-z]+/|" + "|".join(sorted((re.escape(v) for v in _PNUS), key=len, reverse=True)))

def link_ok(target):
    """internal path resolves to a page or a file on disk"""
    if target in link_cache:
        return link_cache[target]
    fs = os.path.join(ROOT, target.lstrip("/"))
    if target.endswith("/"):
        ok = os.path.isfile(os.path.join(fs, "index.html"))
    else:
        ok = os.path.isfile(fs)   # /brand/..., /icons/..., /manifest.webmanifest; a page link without "/" is a failure
    link_cache[target] = ok
    return ok

def check_links(path, doc, anchors_only=False):
    """internal links of one document: existence, hash routes, inbound counts"""
    global n_links, n_hash
    pat = r'<a\b[^>]*?\bhref="([^"]*)"' if anchors_only else r'<(?:a|link)\b[^>]*?\bhref="([^"]*)"'
    for href in set(re.findall(pat, doc, flags=re.I)):
        href = html.unescape(href)
        if href.startswith("/#"):
            n_hash += 1
            if not hash_ok(href[2:]):
                fail("link to an app route that does not exist", f"{path} -> {href}")
            continue
        if not href.startswith("/") or href.startswith("//") or href == "/":
            continue
        target = href.split("#", 1)[0].split("?", 1)[0]
        n_links += 1
        if not link_ok(target):
            fail("broken internal link", f"{path} -> {href}")
        elif target in disk and target != path:
            inbound[target] += 1
        if "#" in href and target in disk:
            frag = href.split("#", 1)[1]
            tdoc = doc if target == path else frag_docs(target)
            if frag and f'id="{frag}"' not in tdoc:
                fail("link to an anchor that does not exist", f"{path} -> {href}")

_docs = {}
def frag_docs(target):
    if target not in _docs:
        _docs[target] = open(disk[target], encoding="utf-8").read()
    return _docs[target]

def check_jsonld(path, doc, need_breadcrumb=True):
    global n_ld
    types = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, flags=re.S):
        n_ld += 1
        try:
            obj = json.loads(raw)
        except Exception as e:
            fail("JSON-LD does not parse", f"{path}: {e}")
            continue
        for o in (obj if isinstance(obj, list) else [obj]):
            if not isinstance(o, dict) or "@type" not in o or "schema.org" not in str(o.get("@context", "")):
                fail("JSON-LD without @context/@type", path)
                continue
            types.append(o["@type"])
            blob = json.dumps(o, ensure_ascii=False)
            for banned in ("aggregateRating", "Review", "FAQPage", '"author"', "SearchAction"):
                if banned in blob:
                    fail("JSON-LD carries a claim the site cannot support", f"{path}: {banned}")
            if o["@type"] == "BreadcrumbList":
                items = o.get("itemListElement", [])
                if not items or items[-1].get("item") != SITE + path:
                    fail("breadcrumb JSON-LD does not end at the page", path)
                for it in items:
                    u = it.get("item", "")
                    if not u.startswith(SITE + "/") or not (u == SITE + "/" or link_ok(u[len(SITE):].split("#")[0])):
                        fail("breadcrumb JSON-LD points to a missing page", f"{path} -> {u}")
            elif o.get("url") not in (None, SITE + path):
                fail("JSON-LD url is not the page's own URL", f"{path} -> {o.get('url')}")
    if need_breadcrumb and "BreadcrumbList" not in types:
        fail("breadcrumb JSON-LD missing", path)
    if need_breadcrumb and len(types) < 2:
        fail("page has no JSON-LD besides the breadcrumb", path)
    return types

def check_copy(path, doc):
    """no em dash in generated Hebrew copy; the source text inside <article id="text"> is not ours to change"""
    ours = re.sub(r'<article\b[^>]*id="text"[^>]*>.*?</article>', "", doc, flags=re.S)
    ours = re.sub(r"<(script|style)\b.*?</\1>", "", ours, flags=re.S)
    if "—" in ours:
        i = ours.index("—")
        fail("em dash in generated copy", f"{path}: …{strip_tags(ours[max(0, i - 40):i + 20])}…")

def check_head_basics(path, doc):
    m = re.search(r"<html\b[^>]*>", doc, flags=re.I)
    tag = m.group(0) if m else ""
    if attr(tag, "lang") != "he": fail("html lang is not he", path)
    if attr(tag, "dir") != "rtl": fail("html dir is not rtl", path)
    vp = re.search(r'<meta\s+name="viewport"[^>]*>', doc, flags=re.I)
    if not vp or "width=device-width" not in (attr(vp.group(0), "content") or ""):
        fail("viewport meta missing", path)
    for host in ("https://fonts.googleapis.com", "https://fonts.gstatic.com"):
        # only a font host the page loads from at start needs a preconnect; one fetched on demand by script does not
        if re.search(r'<link\b[^>]*rel="stylesheet"[^>]*href="' + re.escape(host), doc) and not re.search(r'<link\b[^>]*rel="preconnect"[^>]*href="' + re.escape(host) + '"', doc):
            fail("font host without preconnect", f"{path}: {host}")
    for href in re.findall(r'href="(https://fonts\.googleapis\.com/css2[^"]*)"', doc):
        if "display=swap" not in href:
            fail("web fonts without display=swap", path)

for path, f in sorted(disk.items()):
    doc = open(f, encoding="utf-8").read()
    _docs[path] = doc
    own = SITE + path
    head = doc.split("</head>", 1)[0]
    check_head_basics(path, doc)

    h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", doc, flags=re.S | re.I)
    if len(h1s) != 1:
        fail("page does not have exactly one <h1>", f"{path} ({len(h1s)})")
    h1_full = strip_tags(h1s[0]) if h1s else ""
    if h1s and not h1_full:
        fail("empty <h1>", path)
    h1_main = strip_tags(re.sub(r'<span class="ctx">.*?</span>', "", h1s[0], flags=re.S)) if h1s else ""

    ts = re.findall(r"<title\b[^>]*>(.*?)</title>", head, flags=re.S | re.I)
    title = strip_tags(ts[0]) if ts else ""
    if len(ts) != 1 or not title:
        fail("missing or empty <title>", path)
    else:
        titles[title].append(path)

    dm = re.search(r'<meta\s+name="description"[^>]*>', head, flags=re.I)
    desc = (attr(dm.group(0), "content") or "").strip() if dm else ""
    if not desc:
        fail("missing or empty meta description", path)
    else:
        descs[desc].append(path)
        desc_len.append(len(desc))
        if not DESC_MIN <= len(desc) <= DESC_MAX:
            fail(f"meta description outside {DESC_MIN} to {DESC_MAX} characters", f"{path} ({len(desc)})")
        if h1_main and not desc.startswith(h1_main[:4]) and READING.fullmatch(path):
            info("description does not start with the H1 wording (common spelling leads instead)", f"{path}: {desc[:40]}…")

    rm = re.search(r'<meta\s+name="robots"[^>]*>', head, flags=re.I)
    if rm and re.search(r"noindex|none", attr(rm.group(0), "content") or "", flags=re.I):
        fail("page is blocked from indexing (robots meta)", path)

    cans = re.findall(r'<link\b[^>]*rel="canonical"[^>]*>', doc, flags=re.I)
    can = attr(cans[0], "href") if cans else None
    if len(cans) != 1:
        fail("page does not have exactly one canonical", f"{path} ({len(cans)})")
    elif path in DUPC and can == SITE + DUPC[path]:
        pass
    elif can != own:
        kind = "canonical points to the home page" if can in (SITE, SITE + "/") else "canonical is not the page's own URL"
        fail(kind, f"{path} -> {can}")
    elif not can.endswith("/"):
        fail("canonical without trailing slash", path)

    for prop, want in (("og:url", own), ("og:site_name", "תפילה"), ("og:locale", "he_IL"),
                       ("og:image:width", "1200"), ("og:image:height", "630")):
        om = re.search(r'<meta\s+property="' + prop + r'"[^>]*>', head, flags=re.I)
        if not om or attr(om.group(0), "content") != want:
            fail("Open Graph " + prop + " missing or wrong", path)
    om = re.search(r'<meta\s+property="og:image"[^>]*>', head, flags=re.I)
    img = attr(om.group(0), "content") if om else ""
    # the address may carry ?v=N (so chat apps fetch a redrawn picture again); the file itself must still exist
    if not re.fullmatch(re.escape(SITE) + r"/icons/og(-[a-z]+)?\.png(\?v=\d+)?", img or "") or not os.path.exists(os.path.join(ROOT, img[len(SITE) + 1:].split("?")[0])):
        fail("Open Graph og:image missing or not a file", path)
    for prop in ("og:title", "og:description", "og:type"):
        om = re.search(r'<meta\s+property="' + prop + r'"[^>]*>', head, flags=re.I)
        if not om or not (attr(om.group(0), "content") or "").strip():
            fail("Open Graph " + prop + " missing", path)
    tw = re.search(r'<meta\s+name="twitter:card"[^>]*>', head, flags=re.I)
    if not tw or attr(tw.group(0), "content") != "summary_large_image":
        fail("twitter card missing", path)

    check_jsonld(path, doc)
    check_copy(path, doc)

    # nusach of a prayer page comes from its URL: /tefila/<nusach>-<n>/
    pm = path in _PNUS
    nus = _PNUS.get(path, "")
    if pm:
        prayer_titles[(nus, h1_main)].append(path)
    h1nus[(h1_full, nus)].append(path)

    # reading pages must carry text
    if READING.fullmatch(path):
        am = re.search(r'<article\b[^>]*id="text"[^>]*>(.*?)</article>', doc, flags=re.S | re.I)
        if not am or len(strip_tags(am.group(1))) < 10:
            fail("reading page with an empty text body", path)
        if 'rel="prev"' not in doc and 'rel="next"' not in doc:
            fail("reading page without previous/next links", path)

    check_links(path, doc)

# ---------- home page, 404, robots ----------
home = read("index.html")
if home is None:
    fail("home page", "index.html is missing at the root (target of / and /#... links)")
else:
    check_head_basics("/", home)
    hh = home.split("</head>", 1)[0]
    if f'<link rel="canonical" href="{SITE}/">' not in hh:
        fail("home page", "canonical is not " + SITE + "/")
    if re.search(r'<meta\s+name="robots"[^>]*noindex', hh, flags=re.I):
        fail("home page", "blocked from indexing")
    check_jsonld("/", hh, need_breadcrumb=False)
    nav = re.search(r'<nav class="seo-links".*?</nav>', home, flags=re.S)
    if not nav:
        fail("home page", "static link block (nav.seo-links) is missing")
    else:
        check_copy("/", nav.group(0))
        check_links("/", nav.group(0), anchors_only=True)
        for hubp in sorted(p for p in disk if p.count("/") == 2 and p not in _PNUS):      # prayer pages sit at the top level but are not hubs
            if f'href="{hubp}"' not in nav.group(0):
                fail("home page does not link to a hub", hubp)

nf = read("404.html")
if nf is None:
    fail("404", "404.html is missing")
else:
    check_head_basics("/404.html", nf)
    if len(re.findall(r"<h1\b", nf)) != 1:
        fail("404", "404.html does not have exactly one <h1>")
    if not re.search(r'<meta\s+name="robots"[^>]*noindex', nf, flags=re.I):
        fail("404", "404.html should carry robots noindex")
    if 'rel="canonical"' in nf:
        fail("404", "404.html must not carry a canonical")
    if re.search(r'(?:href|src)="(?!/|https?:|#|data:)', nf):
        fail("404", "404.html has a relative URL (it is served on any path)")
    check_copy("/404.html", nf)
    check_links("/404.html", nf)
    for hubp in ("/siddur/", "/tehillim/", "/sefer/"):
        if f'href="{hubp}"' not in nf:
            fail("404", f"404.html does not link to {hubp}")

rb = read("robots.txt")
if rb is None:
    fail("robots.txt", "robots.txt is missing")
else:
    lines = [l.strip() for l in rb.splitlines() if l.strip() and not l.strip().startswith("#")]
    if f"Sitemap: {SITE}/sitemap.xml" not in lines:
        fail("robots.txt", f"missing the line 'Sitemap: {SITE}/sitemap.xml'")
    if not any(l.lower().startswith("user-agent:") for l in lines):
        fail("robots.txt", "no User-agent group")
    for l in lines:
        if l.lower().startswith("disallow:"):
            rule = l.split(":", 1)[1].strip()
            blocked = [p for p in disk if rule and p.startswith(rule)]
            if rule == "/" or blocked:
                fail("robots.txt blocks pages", f"{l} ({len(blocked) or 'all'} pages)")

# ---------- cross-page ----------
for path in sorted(disk):
    if inbound[path] < 1:
        fail("orphan page (no inbound internal link)", path)
for t, ps in titles.items():
    if len(ps) > 1:
        fail("duplicate <title>", f"{t!r}: {', '.join(ps[:4])}{' …' if len(ps) > 4 else ''} ({len(ps)} pages)")
for d, ps in descs.items():
    if len(ps) > 1:
        fail("duplicate meta description", f"{d[:60]!r}…: {', '.join(ps[:4])}{' …' if len(ps) > 4 else ''} ({len(ps)} pages)")
for (h, nus), ps in h1nus.items():
    if len(ps) > 1:
        info("duplicate H1 + nusach", f"{h!r} [{nus or '-'}]: {', '.join(ps[:4])}{' …' if len(ps) > 4 else ''} ({len(ps)} pages)")
for (nus, h), ps in prayer_titles.items():
    if len(ps) > 1:
        info("same prayer title in one nusach (compete for one search intent)", f"{h!r} [{nus}]: {len(ps)} pages, e.g. {', '.join(ps[:3])}")

# ---------- report ----------
def kind(p):
    parts = p.strip("/").split("/")
    if len(parts) == 1: return parts[0] + " (hub)"
    if re.fullmatch(r"/tehillim/\d+/", p): return "tehillim chapter"
    if p == "/tehillim/yomi/": return "tehillim schedule"
    if re.fullmatch(r"/tehillim/(yom|chodesh)-[a-z0-9]+/", p): return "tehillim by day"
    if parts[0] == "tehillim": return "tehillim by need"
    if parts[0] == "kelim": return "tool"
    if p in _PNUS: return "prayer"
    if parts[0] == "siddur": return "nusach hub" if len(parts) == 2 else "service"
    return parts[0] + " page"
count = collections.Counter(kind(p) for p in disk)
print("SEO audit of", ROOT)
print(f"  pages on disk: {len(disk)}  (" + ", ".join(f"{k}: {v}" for k, v in sorted(count.items())) + ")")
print(f"  sitemap: {len(locs)} <loc>, {len(set(locs))} unique, {len(dups)} duplicated")
print(f"  unique titles: {len(titles)}   unique descriptions: {len(descs)}"
      + (f"   description length: {min(desc_len)} to {max(desc_len)}, median {sorted(desc_len)[len(desc_len) // 2]}" if desc_len else ""))
print(f"  internal link targets checked: {len(link_cache)} ({n_links} links)   app hash links checked: {n_hash}   JSON-LD blocks parsed: {n_ld}")
if disk:
    low = sorted(inbound[p] for p in disk)
    print(f"  inbound internal links per page: min {low[0]}, median {low[len(low) // 2]}, max {low[-1]}   pages with fewer than 3: {sum(1 for x in low if x < 3)}")
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
