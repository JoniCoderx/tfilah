#!/usr/bin/env python3
"""Builds the draft page /ma-mevarchim/ from tools/brachot/data.py.

  python3 tools/prerender.py          (first: the page borrows the site's shell from a generated page)
  python3 tools/brachot/build.py

Writes ma-mevarchim/index.html (noindex, kept out of the sitemap: see tools/drafts.json), tools/brachot/out.json (what the
tests read) and tools/brachot/REVIEW.md (the table that goes to the rabbi)."""
import json, os, re, sys
H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, H)
from custom import CUSTOM
import data

PATH = "/ma-mevarchim/"
TITLE = "מה מברכים על? ברכה ראשונה ואחרונה לכל מאכל | תפילה"
DESC = "מה מברכים על כל מאכל ומשקה: כותבים את שם המאכל ומקבלים את הברכה הראשונה, את הברכה האחרונה ואת התנאי שמשנה את התשובה, עם מקור לכל הוראה."


def icon(key):
    if key in CUSTOM:
        return CUSTOM[key]
    cp = "-".join(f"{ord(c):x}" for c in key if ord(c) != 0xfe0f)
    f = os.path.join(H, "icons", cp + ".svg")
    assert os.path.exists(f), f"no illustration for {key!r} ({cp}.svg): add it to tools/brachot/icons/ (Twemoji 15.1.0, CC-BY 4.0)"
    return open(f, encoding="utf-8").read().strip()


BEFORE = ("etz", "adama", "mezonot", "motzi", "shehakol", "gefen")
AFTER = ("nefashot", "michya", "haetz", "hagefen", "mazon", "none", "review")
foods, icons, ids = [], {}, set()
for r in data.RECORDS:
    assert re.fullmatch(r"[a-z0-9-]+", r["id"]) and r["id"] not in ids, r["id"]
    ids.add(r["id"])
    assert r.get("before") in BEFORE + (None,), r
    assert r.get("after") in AFTER + (None,), r
    for o in r.get("ops", []):
        assert o.get("who") and o.get("before") in BEFORE + (None,) and o.get("after") in AFTER + (None,), (r["id"], o)
    assert not (r.get("before") and r.get("ops")), r["id"]          # one answer, or opinions, never both
    for k in r.get("src", []):
        assert k in data.SOURCES, (r["id"], k)
    # an answer without a source is never shown as settled
    if (r.get("before") or r.get("ops")) and not r.get("src"):
        assert r.get("status") == "review", f"{r['id']}: a ruling with no source must be marked review"
    icons.setdefault(r["icon"], icon(r["icon"]))
    foods.append({**{k: v for k, v in r.items() if v not in (None, "", [], ())}, "icon": list(icons).index(r["icon"])})
for c in data.CHOICES:
    assert all(i in ids for i in c["ids"]), c
OUT = {"foods": foods, "choices": data.CHOICES, "sources": data.SOURCES, "start": data.START, "tryThese": data.TRY}
assert data.START in ids
json.dump(OUT, open(os.path.join(H, "out.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)

# ---- the page: the site's shell (header, footer, styles) from a generated page, with its own head and body ----
shell = open(os.path.join(ROOT, "odot", "index.html"), encoding="utf-8").read()
head, rest = shell.split('<main id="main">', 1)
tail = rest.split("</main>", 1)[1]
tail = re.sub(r"<script>.*?</script>", lambda m: m.group(0) if "data-taut" in m.group(0) and "kesher" not in m.group(0) else "", tail, flags=re.S)
head = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", head, count=1, flags=re.S)
head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{DESC}">', head, count=1)
head = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>https://tfilah.com" + PATH, head, count=1)
head = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>https://tfilah.com" + PATH, head, count=1)
head = re.sub(r'(<meta property="og:title" content=")[^"]*', r"\g<1>" + TITLE, head, count=1)
head, _n = re.subn(r'(<meta property="og:image" content="https://tfilah\.com/icons/)[a-z-]+(\.png)', r"\g<1>og-brachot\g<2>", head, count=1)
assert _n == 1, "the share picture line changed"
head = re.sub(r'(<meta property="og:description" content=")[^"]*', r"\g<1>" + DESC, head, count=1)
LD = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "תפילה", "item": "https://tfilah.com/"},
                                                                              {"@type": "ListItem", "position": 2, "name": "מה מברכים על", "item": "https://tfilah.com" + PATH}]},
      {"@context": "https://schema.org", "@type": "WebApplication", "name": "מה מברכים על", "url": "https://tfilah.com" + PATH, "inLanguage": "he", "applicationCategory": "ReferenceApplication",
       "operatingSystem": "Any", "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "ILS"}, "description": DESC}]
head = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", head, flags=re.S)
head = head.replace("</head>", "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "</script>" for x in LD) + "\n</head>", 1)
body = open(os.path.join(H, "page.html"), encoding="utf-8").read()
js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
search_js = open(os.path.join(H, "search.js"), encoding="utf-8").read().split("if (typeof module")[0]
for k, v in (("/*SEARCH*/", search_js), ("/*DATA*/", js(OUT)), ("/*ICONS*/", js(list(icons.values()))), ("__N__", str(len(foods)))):
    assert body.count(k) == 1, k
    body = body.replace(k, v)
os.makedirs(os.path.join(ROOT, "ma-mevarchim"), exist_ok=True)
crumbs = '<div class="rhead" style="padding-block-end:0"><nav class="crumbs" aria-label="מיקום באתר"><a href="/">תפילה</a></nav></div>'
open(os.path.join(ROOT, "ma-mevarchim", "index.html"), "w", encoding="utf-8").write(head + '<main id="main">' + crumbs + body + "</main>" + tail)

# ---- the table for the rabbi ----
BN = {"etz": "העץ", "adama": "האדמה", "mezonot": "מזונות", "motzi": "המוציא", "shehakol": "שהכל", "gefen": "הגפן", None: "-"}
AN = {"nefashot": "בורא נפשות", "michya": "על המחיה", "haetz": "על העץ", "hagefen": "על הגפן", "mazon": "ברכת המזון", "none": "אין ברכה אחרונה", "review": "צריך בדיקה", None: "-"}
cell = lambda s: (s or "-").replace("|", "/").replace("\n", " ")
srcs = lambda r: ", ".join(f"[{data.SOURCES[k][0]}]({data.SOURCES[k][1]})" if data.SOURCES[k][1] else data.SOURCES[k][0] for k in r.get("src", [])) or "אין מקור"
rv = [r for r in data.RECORDS if r.get("status") == "review"]
L = ["# מה מברכים על: טבלת ביקורת לרב", "",
     f"{len(data.RECORDS)} רשומות. {len(rv)} מהן מסומנות ”צריך בדיקה”: {len([r for r in rv if not r.get('before') and not r.get('ops')])} בלי תשובה כלל (אין מקור), והשאר עם תשובה שמחכה לאישור.", "",
     "הקובץ נוצר אוטומטית מ-`tools/brachot/data.py`. אין לערוך אותו ביד.", "",
     "## שאלות פתוחות לרב", ""]
L += [f"- **{r['name']}**: {r['ask']}" for r in data.RECORDS if r.get("ask")] or ["- אין."]
L += ["", "## כל הרשומות", "", "| מאכל | שמות נוספים | ראשונה | אחרונה | תנאי או מחלוקת | מקור | מצב |", "|---|---|---|---|---|---|---|"]
for r in data.RECORDS:
    if r.get("ops"):
        cond = " ".join(f"{o['who']}: {BN[o.get('before')]}{' / ' + AN[o['after']] if o.get('after') else ''}{'. ' + o['text'] if o.get('text') else ''}." for o in r["ops"])
        b, a = "כמה דעות", "כמה דעות"
    else:
        cond = " ".join(x for x in (r.get("cond"), r.get("after_cond"), r.get("note")) if x)
        b, a = BN[r.get("before")], AN[r.get("after")]
    L.append(f"| {r['name']} | {cell('، '.join(r.get('alias', [])))} | {b} | {a} | {cell(cond)} | {srcs(r)} | {'צריך בדיקה' if r.get('status') == 'review' else 'ממקור'} |")
open(os.path.join(H, "REVIEW.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
# ---- the sitemap: prerender.py rewrites it without this page, so the page adds itself (the date changes only when the page does) ----
import hashlib, datetime
doc = open(os.path.join(ROOT, "ma-mevarchim", "index.html"), encoding="utf-8").read()
fp = hashlib.sha1(doc.encode()).hexdigest()[:16]
lm_file = os.path.join(H, "lastmod.json")
lm = json.load(open(lm_file)) if os.path.exists(lm_file) else {}
if lm.get("fp") != fp:
    lm = {"fp": fp, "date": datetime.date.today().isoformat()}
    json.dump(lm, open(lm_file, "w"))
sm_path = os.path.join(ROOT, "sitemap.xml")
sm = open(sm_path, encoding="utf-8").read()
sm = re.sub(r"\s*<url><loc>https://tfilah\.com/ma-mevarchim/</loc>.*?</url>", "", sm, flags=re.S)
sm = sm.replace("</urlset>", f"<url><loc>https://tfilah.com{PATH}</loc><lastmod>{lm['date']}</lastmod><priority>0.8</priority></url>\n</urlset>")
open(sm_path, "w", encoding="utf-8").write(sm)
print(f"ma-mevarchim: {len(foods)} foods, {len(icons)} illustrations, {len(rv)} waiting for review, {len(data.CHOICES)} choosers")
