import os, re, sys
src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()

REPL = [
    ('const DONATE_URL = "";', 'const DONATE_URL = (window.TFILAH_CONFIG && window.TFILAH_CONFIG.donateUrl) || "";'),
    ('<b>קיר הנרות זמין למחוברים</b>כדי לראות נרות ולהדליק נר צריך להיות מחוברים.', '<b>תהילים יחד ייפתח בקרוב</b>הקריאה המשותפת עוד לא מחוברת. בינתיים אפשר לקרוא תהילים באתר.'),
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

DESC = "סידור תפילה אונליין בניקוד מלא, בנוסח עדות המזרח, ספרד ואשכנז, עם ספר תהילים, פרשת השבוע, זמני היום ותהילים יחד. בלי פרסומות, נוח לקריאה בנייד."
BEACON = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "beacon.js"), encoding="utf-8").read().strip()
TITLE = "סידור תפילה אונליין ותהילים בניקוד מלא | תפילה Tfilah"

head = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8"><script>try{{if(JSON.parse(localStorage.getItem("dark")||"false"))document.documentElement.dataset.theme="dark"}}catch(e){{}}</script>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta name="theme-color" content="#FFFFFF">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="תפילה">
<meta property="og:image" content="https://tfilah.com/icons/og.png?v=5">
<link rel="canonical" href="https://tfilah.com/">
<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" href="/icons/favicon-96.png" type="image/png" sizes="96x96"><link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/icons/icon-192.png" type="image/png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="תפילה">
<meta property="og:title" content="{TITLE}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="https://tfilah.com/">
<meta property="og:locale" content="he_IL">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"תפילה","alternateName":["Tfilah","Tfilah.com","תפילה Tfilah"],"url":"https://tfilah.com/","inLanguage":"he","description":"{DESC}","publisher":{{"@type":"Organization","name":"תפילה","alternateName":"Tfilah","contactPoint":[{{"@type":"ContactPoint","contactType":"donations","email":"team@tfilah.com"}},{{"@type":"ContactPoint","contactType":"business inquiries","email":"business@tfilah.com"}}],"url":"https://tfilah.com/","logo":"https://tfilah.com/icons/icon-512.png","sameAs":["https://www.facebook.com/tfilahcom"]}}}}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"תפילה: סידור תפילה אונליין ותהילים","url":"https://tfilah.com/","inLanguage":"he","isPartOf":{{"@type":"WebSite","url":"https://tfilah.com/"}},"primaryImageOfPage":{{"@type":"ImageObject","url":"https://tfilah.com/icons/thumb.png?v=1","width":1200,"height":1200}}}}</script>
{''.join(links)}<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
<script defer src="/config.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>
<script defer src="/shim.js"></script>
<script>if("serviceWorker" in navigator)addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{{}}));</script>
<script>{BEACON}</script>
<noscript><style>.boot{{visibility:visible!important;animation:none!important}}</style></noscript>
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
_urls = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "urls.json"), encoding="utf-8"))


def _prayer(title, nus="mizrach"):
    norm = lambda t: t.replace("תפלת", "תפילת")
    # readable addresses come from data/urls.json, which tools/prerender.py writes (run it first)
    return next(_urls[p["id"]] for p in _idx["prayers"] if p["n"] == nus and norm(p["t"]) == title)
_groups = [
    ("סידור", [("/siddur/", "סידור תפילה")] + [("/siddur/%s/" % n, "סידור נוסח " + t) for n, t in _idx["nusachim"].items()]
        + [("/siddur/%s/%s/" % (n, k), "%s נוסח %s" % (l, t)) for k, l in (("shacharit", "שחרית"), ("mincha", "מנחה"), ("arvit", "ערבית")) for n, t in _idx["nusachim"].items()]
        + [(_prayer("ברכת המזון"), "ברכת המזון"), (_prayer("תפילת הדרך"), "תפילת הדרך"), (_prayer("קריאת שמע שעל המיטה"), "קריאת שמע שעל המיטה")]),
    ("תהילים", [("/tehillim/", "ספר תהילים"), ("/tehillim/yomi/", "תהילים יומי"), ("/tehillim-yachad/", "תהילים יחד")]
        + [("/tehillim/%s/" % k, "תיקון הכללי" if k == "tikkun" else "תהילים " + t) for k, t in _needs]
        + [("/tehillim/%s/" % k, "תהילים ליום " + t) for k, t in (("yom-rishon", "ראשון"), ("yom-sheni", "שני"), ("yom-shlishi", "שלישי"),
            ("yom-revii", "רביעי"), ("yom-chamishi", "חמישי"), ("yom-shishi", "שישי"), ("yom-shabbat", "שבת"))]
        + [("/tehillim/%d/" % c, "תהילים " + g) for c, g in ((86, "פו"), (84, "פד"), (1, "א"), (20, "כ"), (23, "כג"), (130, "קל"), (90, "צ"), (100, "ק"),
            (27, "כז"), (30, "ל"), (91, "צא"), (121, "קכא"), (119, "קיט"), (13, "יג"), (145, "קמה"), (142, "קמב"), (24, "כד"), (16, "טז"), (67, "סז"), (51, "נא"))]),
    ("ספרייה וכלים", [("/sefer/", "ספרייה"), ("/sefer/avot/", "פרקי אבות"), ("/sefer/shir/", "שיר השירים"), ("/sefer/esther/", "מגילת אסתר"),
        ("/sefer/perek/", "פרק שירה"), ("/kelim/", "כלים אישיים"), ("/kelim/yahr/", "חישוב יום השנה לפטירה"),
        ("/tisha-beav/", "תשעה באב: מגילת איכה ונחם"), ("/kelim/bday/", "יום הולדת עברי לפי לועזי"), ("/kelim/kivun/", "כיוון תפילה לירושלים"), ("/kelim/shem/", "תהילים קיט לפי שם"), ("/perek-shira/", "פרק שירה"), ("/kotel/", "תפילה בכותל המערבי"), ("/birkat-kala/", "ברכת כלה להדפסה"), ("/mizmor-letoda/", "מזמור לתודה"), ("/nishmat-kol-chai/", "נשמת כל חי"), ("/kaddish/", "קדיש"), ("/leiluy-nishmat/", "תהילים אותיות נשמה"), ("/sefer/haman/", "פרשת המן"), ("/segulat-rachel-imenu/", "סגולת רחל אמנו"), ("/tikun-rachel/", "תיקון רחל"), ("/parasha/", "פרשת השבוע"), ("/ma-mevarchim/", "מה מברכים על"), ("/zmanei-hayom/", "זמני היום לפי עיר"), ("/zmanei-hayom/jerusalem/", "זמני היום בירושלים"), ("/zmanei-hayom/tel-aviv/", "זמני היום בתל אביב"), ("/zmanei-shabbat/", "זמני שבת"), ("/stickers/", "סטיקרים לוואטסאפ"), ("/chanukah/", "ברכות הדלקת נרות חנוכה"), ("/odot/", "אודות ומקורות"), ("/pratiyut/", "פרטיות"), ("/tnaim/", "תנאי שימוש"), ("/negishut/", "הצהרת נגישות"),
        ("/zmanei-shabbat/jerusalem/", "זמני שבת בירושלים"), ("/zmanei-shabbat/tel-aviv/", "זמני שבת בתל אביב"), ("/zmanei-shabbat/haifa/", "זמני שבת בחיפה")]),
]
SEO_NAV = ('<nav class="seo-links" aria-label="מפת האתר"><details><summary><span>מפת האתר</span><small>כל התפילות, הפרקים והדפים במקום אחד</small></summary><div class="seo-cols">'
  + "".join('<section><h3>%s</h3><ul>' % g + "".join('<li><a href="%s">%s</a></li>' % (h, t_) for h, t_ in links) + "</ul></section>"
            for g, links in _groups) + "</div><p class=\"dclose\"><button type=\"button\" data-dclose><svg viewBox=\"0 0 24 24\" width=\"18\" height=\"18\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.4\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"m6 15 6-6 6 6\"/></svg>סגירה</button></p></details></nav>")
BOOT = ('<main class="wrap" id="app"><div class="boot"><h1>תפילה: סידור תפילה ותהילים אונליין</h1>'
        '<p>סידור מלא בניקוד בנוסח עדות המזרח, ספרד ואשכנז, ספר תהילים, זמני היום וקריאת תהילים משותפת.</p><ul>'
        + "".join('<li><a href="%s">%s</a></li>' % x for x in [
            ("/siddur/mizrach/shacharit/", "תפילת שחרית"), ("/siddur/mizrach/mincha/", "תפילת מנחה"), ("/siddur/mizrach/arvit/", "תפילת ערבית"),
            ("/siddur/", "כל הסידור"), ("/tehillim/", "ספר תהילים"), ("/kelim/shem/", "תהילים לפי שם"),
            ("/zmanei-hayom/", "זמני היום"), ("/zmanei-shabbat/", "זמני שבת")])
        + '</ul></div></main>')
_ph = '<main class="wrap" id="app"><p class="loading">פותחים את הסידור…</p></main>'
assert s.count(_ph) == 1, "home placeholder"
s = s.replace(_ph, BOOT)
if not re.search(r'supabaseUrl:\s*"[^"]+"', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.js"), encoding="utf-8").read()):
    # the shared-reading service is not connected: its library is not requested at all
    head = head.replace('<script defer src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>\n', "")
s = head + s.strip() + "\n" + SEO_NAV + "\n</body>\n</html>\n"
# the styles are shipped without their comments and indentation (the source keeps them)
def _slim_css(m):
    c = re.sub(r"/\*.*?\*/", "", m.group(2), flags=re.S)
    return m.group(1) + re.sub(r"\s*\n\s*", "\n", c).strip() + "</style>"
s = re.sub(r"(<style[^>]*>)(.*?)</style>", _slim_css, s, flags=re.S)
s = s.replace("קוראים לעילוי נשמת", "קוראים לעילוי נשמת")  # no-op, keeps file stable
open(out, "w", encoding="utf-8").write(s)
print("ok", len(s))
