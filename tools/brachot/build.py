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
CHEV = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
pages_nav = ('<details class="mm-dd mm-pages"><summary><b>עמוד לכל מאכל</b><span>' + str(sum(1 for f in foods if f.get("status") == "ok")) + ' עמודים</span>' + CHEV + '</summary><ul>'
             + "".join(f'<li><a href="/ma-mevarchim/{f["id"]}/">{f["name"]}</a></li>' for f in foods if f.get("status") == "ok") + "</ul></details>")
for k, v in (("<!--PAGES-->", pages_nav), ("/*SEARCH*/", search_js), ("/*DATA*/", js(OUT)), ("/*ICONS*/", js(list(icons.values()))), ("__N__", str(len(foods)))):
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
    lm = {"fp": fp, "date": datetime.date.today().isoformat(), "pages": lm.get("pages", {})}
    json.dump(lm, open(lm_file, "w"))
sm_path = os.path.join(ROOT, "sitemap.xml")
sm = open(sm_path, encoding="utf-8").read()
sm = re.sub(r"\s*<url><loc>https://tfilah\.com/ma-mevarchim/</loc>.*?</url>", "", sm, flags=re.S)
sm = sm.replace("</urlset>", f"<url><loc>https://tfilah.com{PATH}</loc><lastmod>{lm['date']}</lastmod><priority>0.8</priority></url>\n</urlset>")
open(sm_path, "w", encoding="utf-8").write(sm)
print(f"ma-mevarchim: {len(foods)} foods, {len(icons)} illustrations, {len(rv)} waiting for review, {len(data.CHOICES)} choosers")


# ---- a page of its own for every food that has a sourced answer: /ma-mevarchim/<id>/ ----
# Everything on these pages comes from data.py as it is: the ruling, the conditions, the named opinions and the sources.
# No sentence here adds a ruling. Foods that wait for a source ("review") get no page.
import html as _html
E = lambda s: _html.escape(str(s), quote=True)
BT = {"etz": ("בורא פרי העץ", "בָּרוּךְ אַתָּה יְהֹוָה, אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם, בּוֹרֵא פְּרִי הָעֵץ:", "/borei-pri-haetz/"),
      "adama": ("בורא פרי האדמה", "בָּרוּךְ אַתָּה יְהֹוָה, אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם, בּוֹרֵא פְּרִי הָאֲדָמָה:", "/borei-pri-haadama/"),
      "mezonot": ("בורא מיני מזונות", "בָּרוּךְ אַתָּה יְהֹוָה, אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם, בּוֹרֵא מִינֵי מְזוֹנוֹת:", "/brachot-hanehenin/"),
      "gefen": ("בורא פרי הגפן", "בָּרוּךְ אַתָּה יְהֹוָה, אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם, בּוֹרֵא פְּרִי הַגֶּפֶן:", "/brachot-hanehenin/"),
      "shehakol": ("שהכל נהיה בדברו", "בָּרוּךְ אַתָּה יְהֹוָה אֱלֹהֵינוּ מֶלֶךְ הָעוֹלָם שֶׁהַכֹּל נִהְיָה בִּדְבָרוֹ:", "/birkat-shehakol/"),
      "motzi": ("המוציא לחם מן הארץ", "בָּרוּךְ אַתָּה יְ‑יָ אֱ‑לֹהֵינוּ מֶלֶךְ הָעוֹלָם הַמּוֹצִיא לֶחֶם מִן הָאָרֶץ:", "/brachot-rishonot/")}
# the wording of the blessings must stay the one the tool shows
for _k, _v in BT.items():
    assert _v[1] in body and _v[2] in body, f"blessing text for {_k} differs from page.html"
AT = {"nefashot": ("בורא נפשות", "/borei-nefashot/"), "michya": ("על המחיה", "/birkat-meein-shalosh/"), "haetz": ("על העץ", "/birkat-meein-shalosh/"),
      "hagefen": ("על הגפן", "/birkat-meein-shalosh/"), "mazon": ("ברכת המזון", "/birkat-hamazon/"), "none": ("אין ברכה אחרונה", ""), "review": ("צריך בדיקה", "")}
KLONG = {"motzi": "המוציא לחם מן הארץ", "mezonot": "בורא מיני מזונות", "gefen": "בורא פרי הגפן", "etz": "בורא פרי העץ", "adama": "בורא פרי האדמה", "shehakol": "שהכל נהיה בדברו"}
style = body.split("</style>", 1)[0] + (
    ".mmf-links{display:flex;flex-wrap:wrap;gap:.5rem;margin:0;padding:0;list-style:none}"
    ".mmf-links a{display:inline-flex;align-items:center;min-height:44px;padding:0 .95rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);text-decoration:none;font:700 .95rem var(--f-ui)}"
    ".mmf-links a:hover{border-color:var(--stamp)}.mmf h2.mmf-h{margin:.4rem 0 0;font:900 1.2rem var(--f-disp);color:var(--ink)}"
    ".mmf-back{justify-self:start;display:inline-flex;align-items:center;gap:.5rem;min-height:48px;padding:0 1.3rem;border-radius:999px;background:var(--stamp);color:#fff;text-decoration:none;font:700 1rem var(--f-ui)}"
    ".mmf .mm-head{grid-template-columns:auto minmax(0,1fr)}.mmf-alias{margin:0;color:var(--muted);font-size:.92rem}"
    "</style>")
foot_html = re.search(r'<div class="mm-foot">.*?</div>', body, re.S).group(0)
okf = [f for f in foods if f.get("status") == "ok"]
by_id = {f["id"]: f for f in foods}
icon_list = list(icons.values())
shelf_of = lambda f: f.get("before") or "multi"
sib = {}
for c in data.CHOICES:
    for i in c["ids"]:
        sib.setdefault(i, []).extend(x for x in c["ids"] if x != i)
heb_only = lambda s: re.fullmatch(r"[א-ת׳״'\" \-0-9]+", s) is not None


def cut(s, n):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def food_page(f):
    name, ops = f["name"], f.get("ops") or []
    if ops:
        cases = f.get("kind") == "cases"
        lead = (f"הברכה על {name} תלויה במקרה. המקרים מובאים כאן כפי שהם במקורות, כל אחד בשם אומרו." if cases
                else f"על {name} יש יותר מדעה אחת. הדעות מובאות כאן זו לצד זו, כל אחת בשם אומרה, בלי להכריע ביניהן.")
        title = f"מה מברכים על {name}? " + ("תלוי במקרה" if cases else "הדעות והמקורות")
        ans = (f'<p class="mm-tag">{"התשובה תלויה במקרה" if cases else "יש יותר מדעה אחת"}</p>' + (f'<p class="mm-cond">{E(f["cond"])}</p>' if f.get("cond") else "")
               + '<ul class="mm-ops">' + "".join(
                   '<li><span class="who">' + E(o["who"]) + '</span><span class="rul">'
                   + (f'לפני: <span class="k-{o["before"]}">{BN[o["before"]]}</span>' if o.get("before") else "") + (" · " if o.get("before") and o.get("after") else "")
                   + (f'אחרי: {AT[o["after"]][0]}' if o.get("after") else "") + "</span>" + (f'<span class="mm-note">{E(o["text"])}</span>' if o.get("text") else "") + "</li>" for o in ops) + "</ul>")
        desc = cut(lead + " " + " ".join(f"{o['who']}: {BN[o['before']] if o.get('before') else ''}{' ' + o['text'] if o.get('text') else ''}".strip() for o in ops), 156)
    else:
        b, a = BT[f["before"]], AT[f.get("after") or "review"]
        tail_s = {"none": "אין אחריו ברכה אחרונה.", "review": "הברכה האחרונה מחכה לבדיקה."}.get(f.get("after") or "review", f"הברכה האחרונה: {a[0]}.")
        paren = f" ({f['cond'].rstrip('. ')})" if f.get("cond") else ""
        lead = f"על {name} מברכים ”{b[0]}”{paren}. " + (f"לגבי ברכה אחרונה: {f['after_cond']}" if f.get("after") == "none" and f.get("after_cond") else tail_s + (f" {f['after_cond']}" if f.get("after_cond") else ""))
        title = f"מה מברכים על {name}? {b[0]}"
        ans = ('<div class="mm-pair"><div class="mm-box"><small>לפני האכילה</small>' + f'<b class="k-{f["before"]}">{b[0]}</b><p class="mm-txt">{b[1]}</p>'
               + (f'<p class="mm-cond">{E(f["cond"])}</p>' if f.get("cond") else "") + f'<a href="{b[2]}">לברכה באתר</a></div>'
               + f'<div class="mm-box"><small>אחרי האכילה</small><b>{a[0]}</b>' + (f'<p class="mm-cond">{E(f["after_cond"])}</p>' if f.get("after_cond") else "")
               + (f'<a href="{a[1]}">לנוסח המלא באתר</a>' if a[1] else "") + "</div></div>" + (f'<p class="mm-note">{E(f["note"])}</p>' if f.get("note") else ""))
        desc = cut(" ".join(x for x in (lead, f.get("note"), "עם מקור ההוראה ונוסח הברכה המלא בניקוד.") if x), 156)
    for extra in ("מתוך הכלי ”מה מברכים על”, באתר תפילה.", "חינם ובלי פרסומות."):
        if len(desc) < 120 and not desc.endswith("…"):
            desc += " " + extra
    if len(title) > 58:
        title = f"מה מברכים על {name}?"
    # only a true second name of the same food goes in the title; most aliases are related foods, not synonyms
    aka = {"pilpel": "גמבה", "chamin": "צ׳ולנט"}.get(f["id"])
    if aka and aka in f.get("alias", []):
        t2 = title.replace(f"על {name}?", f"על {name} ({aka})?", 1)
        if len(t2) <= 58:
            title = t2
    title += " | תפילה"
    src = "מקור: " + " · ".join(f'<a href="{E(data.SOURCES[k][1])}" rel="noopener" target="_blank">{E(data.SOURCES[k][0])}</a>' if data.SOURCES[k][1] else E(data.SOURCES[k][0]) for k in f["src"])
    alias = [x for x in f.get("alias", []) if heb_only(x)]
    k = shelf_of(f)
    same = [x for x in okf if shelf_of(x) == k and x["id"] != f["id"]]
    i = next((n for n, x in enumerate(okf) if x["id"] == f["id"]), 0)
    near = sorted(same, key=lambda x: abs(okf.index(x) - i))[:8]
    near = [by_id[s] for s in sib.get(f["id"], []) if by_id[s].get("status") == "ok"] + [x for x in near if x["id"] not in sib.get(f["id"], [])]
    link = lambda x: f'<li><a href="/ma-mevarchim/{x["id"]}/">{E(x["name"])}</a></li>'
    more_h = f"עוד מאכלים שמברכים עליהם ”{KLONG[k]}”" if k in KLONG else "עוד מאכלים שהתשובה עליהם תלויה במקרה או בדעה"
    page_body = (style + '<div class="mm mmf">' + f"<h1>מה מברכים על <span>{E(name)}</span>?</h1>" + f'<p class="mm-lead">{E(lead)}</p>'
                 + f'<section class="mm-ans"><div class="mm-head"><div class="mm-pic" aria-hidden="true">{icon_list[f["icon"]]}</div><h2>הברכה על<b>{E(name)}</b></h2></div>' + ans + f'<p class="mm-src">{src}</p></section>'
                 + (f'<p class="mmf-alias">בכלי החיפוש המאכל מופיע גם בשמות: {E(", ".join(alias))}.</p>' if alias else "")
                 + '<a class="mmf-back" href="/ma-mevarchim/">חיפוש מאכל אחר</a>'
                 + f'<h2 class="mmf-h">{more_h}</h2><ul class="mmf-links">' + "".join(link(x) for x in near[:9]) + "</ul>" + foot_html + "</div>")
    p = f"/ma-mevarchim/{f['id']}/"
    h = shell_head
    h = re.sub(r"<title>.*?</title>", lambda m: f"<title>{E(title)}</title>", h, count=1, flags=re.S)
    for rx, val in ((r'(<meta name="description" content=")[^"]*', E(desc)), (r'(<link rel="canonical" href=")[^"]*', "https://tfilah.com" + p), (r'(<meta property="og:url" content=")[^"]*', "https://tfilah.com" + p),
                    (r'(<meta property="og:title" content=")[^"]*', E(title)), (r'(<meta property="og:description" content=")[^"]*', E(desc))):
        h, n = re.subn(rx, lambda m, v=val: m.group(1) + v, h, count=1)
        assert n == 1, rx
    h, n = re.subn(r'(<meta property="og:image" content="https://tfilah\.com/icons/)[a-z-]+(\.png)', r"\g<1>og-brachot\g<2>", h, count=1)
    assert n == 1
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "תפילה", "item": "https://tfilah.com/"}, {"@type": "ListItem", "position": 2, "name": "מה מברכים על", "item": "https://tfilah.com/ma-mevarchim/"},
              {"@type": "ListItem", "position": 3, "name": name, "item": "https://tfilah.com" + p}]},
          {"@context": "https://schema.org", "@type": "WebPage", "name": title.replace(" | תפילה", ""), "url": "https://tfilah.com" + p, "inLanguage": "he", "description": desc,
           "isPartOf": {"@type": "WebSite", "name": "תפילה", "url": "https://tfilah.com/"}}]
    h = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", h, flags=re.S)
    h = h.replace("</head>", "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "</script>" for x in ld) + "\n</head>", 1)
    cr = '<div class="rhead" style="padding-block-end:0"><nav class="crumbs" aria-label="מיקום באתר"><a href="/">תפילה</a><span aria-hidden="true">›</span><a href="/ma-mevarchim/">מה מברכים על</a></nav></div>'
    return p, h + '<main id="main">' + cr + page_body + "</main>" + tail, title, desc


shell_head = open(os.path.join(ROOT, "odot", "index.html"), encoding="utf-8").read().split('<main id="main">', 1)[0]
assert "—" not in "".join(json.dumps(f, ensure_ascii=False) for f in okf)
pages_lm = lm.get("pages", {})
titles_seen, entries, today = set(), [], datetime.date.today().isoformat()
for f in okf:
    p, doc_f, t, d = food_page(f)
    assert t not in titles_seen, t
    titles_seen.add(t)
    assert 60 <= len(d) <= 160, (f["id"], len(d), d)
    os.makedirs(os.path.join(ROOT, "ma-mevarchim", f["id"]), exist_ok=True)
    open(os.path.join(ROOT, "ma-mevarchim", f["id"], "index.html"), "w", encoding="utf-8").write(doc_f)
    fpf = hashlib.sha1(doc_f.encode()).hexdigest()[:16]
    if pages_lm.get(f["id"], {}).get("fp") != fpf:
        pages_lm[f["id"]] = {"fp": fpf, "date": today}
    entries.append(f"<url><loc>https://tfilah.com{p}</loc><lastmod>{pages_lm[f['id']]['date']}</lastmod><priority>0.6</priority></url>")
stale = sorted(set(x for x in os.listdir(os.path.join(ROOT, "ma-mevarchim")) if os.path.isdir(os.path.join(ROOT, "ma-mevarchim", x))) - {f["id"] for f in okf})
assert not stale, f"food folders with no record behind them (remove them by hand): {stale}"
lm["pages"] = {k: v for k, v in pages_lm.items() if k in {f["id"] for f in okf}}
json.dump(lm, open(lm_file, "w"), ensure_ascii=False, sort_keys=True)
sm = open(sm_path, encoding="utf-8").read()
sm = re.sub(r"\s*<url><loc>https://tfilah\.com/ma-mevarchim/[a-z0-9-]+/</loc>.*?</url>", "", sm, flags=re.S)
sm = sm.replace("</urlset>", "\n".join(entries) + "\n</urlset>")
open(sm_path, "w", encoding="utf-8").write(sm)
print(f"ma-mevarchim: {len(okf)} food pages")
