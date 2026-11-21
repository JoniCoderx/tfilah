import re, sys
src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()

REPL = [
    ('const DONATE_URL = "";', 'const DONATE_URL = (window.TFILAH_CONFIG && window.TFILAH_CONFIG.donateUrl) || "";'),
    ('<b>קיר הנרות זמין למחוברים</b>כדי לראות נרות ולהדליק נר צריך להיות מחוברים.', '<b>תהילים יחד ייפתח בקרוב</b>הקריאה המשותפת עוד לא מחוברת. בינתיים אפשר לקרוא תהילים באתר.'),
    ("'כדי לפתוח תפילת רבים צריך להיות מחוברים עם הרשאת השתתפות בדף.'", "'הקריאה המשותפת עוד לא נפתחה באתר. ייפתח בקרוב.'"),
    ('<b>התפילה זמינה למחוברים</b>היכנסו לחשבון כדי לראות את הדף ולהשתתף.', '<b>תהילים יחד ייפתח בקרוב</b>הקריאה המשותפת עוד לא מחוברת. בינתיים אפשר לקרוא תהילים באתר.'),
    ("toast('מורה הדרך זמין לצופים מחוברים ב-Claude')", "toast('מורה הדרך אינו פעיל כרגע')"),
    ("e.code==='not_granted'?'צריך לאשר את השימוש ב-Claude כדי לשאול'", "e.code==='not_granted'?'מורה הדרך לא זמין כרגע'"),
    ("placeholder='מורה הדרך זמין לצופים מחוברים ב-Claude'", "placeholder='מורה הדרך אינו פעיל כרגע'"),
]
for a, b in REPL:
    assert a in s, a[:60]
    s = s.replace(a, b)

# pull <title>/<meta>/<link> lines out of the body top; they go into <head>
title = re.search(r"<title>.*?</title>", s).group(0)
s = s.replace(title, "", 1)
s = re.sub(r'<meta name="claude:viewport-fit-sides"[^>]*>\n?', "", s, count=1)
s = re.sub(r'<meta name="description"[^>]*>\n?', "", s, count=1)
links = re.findall(r"<link [^>]+>\n?", s[:2000])
for l in links:
    s = s.replace(l, "", 1)

DESC = "סידור תפילה מלא בניקוד בנוסח עדות המזרח, ספרד ואשכנז, ספר תהילים וקריאה משותפת: כל אחד פרק, ביחד ספר שלם."
TITLE = "תפילה | סידור, תהילים וקריאת תהילים משותפת"

head = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta name="theme-color" content="#FFFFFF">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="תפילה">
<meta property="og:image" content="https://tfilah.com/icons/og.png">
<link rel="canonical" href="https://tfilah.com/">
<link rel="icon" href="brand/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="icons/icon-192.png" type="image/png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="תפילה">
<meta property="og:title" content="{TITLE}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="https://tfilah.com/">
<meta property="og:locale" content="he_IL">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"תפילה","alternateName":"Tfilah.com","url":"https://tfilah.com/","inLanguage":"he","description":"{DESC}"}}</script>
{''.join(links)}<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
<script src="config.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>
<script src="shim.js"></script>
<script>if("serviceWorker" in navigator)addEventListener("load",()=>navigator.serviceWorker.register("sw.js").catch(()=>{{}}));</script>
</head>
<body>
"""
# Static, crawlable links to every hub and the main landing pages (the app itself is rendered by script).
# Kept compact: small muted text under the app. Prayer ids are looked up in data/index.json, never hard-coded.
import json, os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_idx = json.load(open(os.path.join(_root, "data", "index.json"), encoding="utf-8"))
_app = open(os.path.join(_root, "src", "app.html"), encoding="utf-8").read()
_needs = re.findall(r"\['([a-z]+)','[a-z]+','([^']+)','[^']*',\[[\d,]+\]\]", re.search(r"const NEEDS=(\[.*?\]);", _app, flags=re.S).group(1))
def _prayer(title, nus="mizrach"):
    norm = lambda t: t.replace("תפלת", "תפילת")
    return next("/tefila/%s/" % p["id"] for p in _idx["prayers"] if p["n"] == nus and norm(p["t"]) == title)
_groups = [
    ("סידור", [("/tefila/", "סידור תפילה")] + [("/tefila/%s/" % n, "סידור נוסח " + t) for n, t in _idx["nusachim"].items()]
        + [("/tefila/%s/%s/" % (n, k), "%s נוסח %s" % (l, t)) for k, l in (("shacharit", "שחרית"), ("mincha", "מנחה"), ("arvit", "ערבית")) for n, t in _idx["nusachim"].items()]
        + [(_prayer("ברכת המזון"), "ברכת המזון"), (_prayer("תפילת הדרך"), "תפילת הדרך"), (_prayer("קריאת שמע שעל המיטה"), "קריאת שמע שעל המיטה")]),
    ("תהילים", [("/tehillim/", "ספר תהילים"), ("/tehillim/yomi/", "תהילים יומי"), ("/tehillim-yachad/", "תהילים יחד")]
        + [("/tehillim/%s/" % k, "תיקון הכללי" if k == "tikkun" else "תהילים " + t) for k, t in _needs]
        + [("/tehillim/%s/" % k, "תהילים ליום " + t) for k, t in (("yom-rishon", "ראשון"), ("yom-sheni", "שני"), ("yom-shlishi", "שלישי"),
            ("yom-revii", "רביעי"), ("yom-chamishi", "חמישי"), ("yom-shishi", "שישי"), ("yom-shabbat", "שבת"))]
        + [("/tehillim/%d/" % c, "תהילים " + g) for c, g in ((86, "פו"), (84, "פד"), (1, "א"), (20, "כ"), (23, "כג"), (130, "קל"), (90, "צ"), (100, "ק"),
            (27, "כז"), (30, "ל"), (91, "צא"), (121, "קכא"), (119, "קיט"), (13, "יג"), (145, "קמה"), (142, "קמב"), (24, "כד"), (16, "טז"), (67, "סז"), (51, "נא"))]),
    ("ספרייה וכלים", [("/sefer/", "ספרייה"), ("/sefer/avot/", "פרקי אבות"), ("/sefer/shir/", "שיר השירים"), ("/sefer/esther/", "מגילת אסתר"),
        ("/sefer/perek/", "פרק שירה"), ("/kelim/", "כלים אישיים"), ("/kelim/yahr/", "חישוב יום השנה לפטירה"),
        ("/kelim/bday/", "יום הולדת עברי לפי לועזי"), ("/kelim/kivun/", "כיוון תפילה לירושלים"), ("/kelim/shem/", "תהילים קיט לפי שם"), ("/zmanei-shabbat/", "זמני כניסת ויציאת שבת"),
        ("/zmanei-shabbat/jerusalem/", "זמני שבת בירושלים"), ("/zmanei-shabbat/tel-aviv/", "זמני שבת בתל אביב"), ("/zmanei-shabbat/haifa/", "זמני שבת בחיפה")]),
]
SEO_NAV = ('<nav class="seo-links" aria-label="כל חלקי האתר" style="max-width:860px;margin:0 auto;padding:0 16px 96px;font-size:.88rem;line-height:1.5;color:#46677F">'
  '<details><summary style="cursor:pointer;display:inline-block;padding:12px 0;font-weight:700;color:#0B2E4F">כל הדפים באתר</summary>'
  + "".join('<p style="margin:0 0 6px"><b style="color:#0B2E4F">%s:</b> ' % g
            + " · ".join('<a href="%s" style="color:#46677F;display:inline-block;padding:4px 0">%s</a>' % (h, t) for h, t in links) + "</p>"
            for g, links in _groups) + "</details></nav>")
s = head + s.strip() + "\n" + SEO_NAV + "\n</body>\n</html>\n"
s = s.replace("קוראים לעילוי נשמת", "קוראים לעילוי נשמת")  # no-op, keeps file stable
open(out, "w", encoding="utf-8").write(s)
print("ok", len(s))
