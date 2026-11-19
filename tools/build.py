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
<meta name="theme-color" content="#F6F0E4">
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
SEO_NAV = ('<nav class="seo-links" aria-label="כל הדפים" style="max-width:860px;margin:0 auto;padding:8px 16px 96px;font-size:.9rem;display:flex;flex-wrap:wrap;gap:6px 16px">'
  '<a href="/tefila/" style="color:#6B5560">סידור תפילה</a><a href="/tehillim/" style="color:#6B5560">ספר תהילים</a>'
  '<a href="/tehillim/20/" style="color:#6B5560">תהילים כ</a><a href="/tehillim/91/" style="color:#6B5560">תהילים צא</a>'
  '<a href="/tehillim/121/" style="color:#6B5560">תהילים קכא</a><a href="/sefer/" style="color:#6B5560">ספרייה</a>'
  '<a href="/sefer/perek/" style="color:#6B5560">פרק שירה</a><a href="/sefer/avot/" style="color:#6B5560">פרקי אבות</a></nav>')
s = head + s.strip() + "\n" + SEO_NAV + "\n</body>\n</html>\n"
s = s.replace("קוראים לעילוי נשמת", "קוראים לעילוי נשמת")  # no-op, keeps file stable
open(out, "w", encoding="utf-8").write(s)
print("ok", len(s))
