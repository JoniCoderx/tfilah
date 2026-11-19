"""Static SEO pages for Tfilah.com.

Generates a real, crawlable HTML page for every Tehillim chapter, every prayer
(per nusach) and every library book, plus hub pages and sitemap.xml.
The interactive app stays at "/"; each static page links into it.

Run from the site root:  python3 tools/prerender.py
"""
import json, os, re, html, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = "https://tfilah.com"
TODAY = datetime.date.today().isoformat()

NIK = re.compile(r"[֑-ׇ]")
TAG = re.compile(r"<[^>]+>")
OK_TAGS = re.compile(r"</?(b|i|small|big|br)\s*/?>", re.I)

def gem(n):
    out = ""
    for v, c in [(400,'ת'),(300,'ש'),(200,'ר'),(100,'ק'),(90,'צ'),(80,'פ'),(70,'ע'),(60,'ס'),(50,'נ'),(40,'מ'),(30,'ל'),(20,'כ'),(10,'י'),(9,'ט'),(8,'ח'),(7,'ז'),(6,'ו'),(5,'ה'),(4,'ד'),(3,'ג'),(2,'ב'),(1,'א')]:
        while n >= v:
            if n in (15, 16) and v == 10:
                out += 'ט' + ('ו' if n == 15 else 'ז'); n = 0; break
            out += c; n -= v
    return out

def clean(s):
    """keep only harmless formatting tags from the source text"""
    s = html.escape(TAG.sub(lambda m: m.group(0) if OK_TAGS.fullmatch(m.group(0)) else "", s), quote=False)
    return re.sub(r"&lt;(/?(?:b|i|small|big|br)\s*/?)&gt;", r"<\1>", s, flags=re.I)

def plain(s):
    return re.sub(r"\s+", " ", NIK.sub("", TAG.sub(" ", s))).replace("יהוה", "ה'").strip()

def snippet(s, n=150):
    s = plain(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def esc(s):
    return html.escape(s, quote=True)

CSS = """
:root{--bg:#fdfbf6;--card:#fff;--ink:#17140f;--muted:#6f685c;--line:#ece4d3;--gold:#b8892f;--gold-d:#8a6420}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Assistant",system-ui,sans-serif;line-height:1.6}
a{color:var(--gold-d)}
.top{position:sticky;top:0;z-index:5;background:rgba(253,251,246,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top .in{max-width:860px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:14px}
.logo{font-weight:800;font-size:1.15rem;text-decoration:none;color:var(--ink);direction:ltr}.logo span{color:var(--gold)}
.top nav{display:flex;gap:4px;margin-inline-start:auto;flex-wrap:wrap}
.top nav a{text-decoration:none;color:var(--muted);padding:6px 10px;border-radius:10px;font-weight:600;font-size:.95rem}
.top nav a:hover{background:#f3ecdc;color:var(--ink)}
main{max-width:860px;margin:0 auto;padding:22px 16px 40px}
.crumbs{font-size:.88rem;color:var(--muted)}.crumbs a{color:var(--muted);text-decoration:none}
h1{font-family:"Frank Ruhl Libre",serif;font-size:clamp(2rem,6vw,3rem);line-height:1.1;margin:10px 0 6px}
.lead{color:var(--muted);margin:0 0 18px;max-width:40rem}
.cta{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:11px 16px;border-radius:12px;background:var(--ink);color:#fff;text-decoration:none;font-weight:700}
.btn.alt{background:#f3ecdc;color:var(--ink)}
.text{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:clamp(18px,4vw,34px);font-family:"Frank Ruhl Libre",serif;font-size:1.32rem;line-height:2}
.text p{margin:0 0 .7em}.text sup{color:var(--gold);font-family:"Assistant",sans-serif;font-size:.62em;margin-inline-end:4px}
.text h2{font-family:"Assistant",sans-serif;font-size:1.05rem;color:var(--gold-d);margin:1.2em 0 .4em}
.text small{color:var(--muted);font-size:.78em}
.pager{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:22px 0}
.pager a{display:block;padding:14px 16px;border:1px solid var(--line);border-radius:16px;background:var(--card);text-decoration:none;color:var(--ink)}
.pager small{display:block;color:var(--muted)}.pager .next{text-align:left}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(64px,1fr));gap:6px}
.grid a{display:grid;place-items:center;height:52px;border-radius:12px;background:var(--card);border:1px solid var(--line);text-decoration:none;color:var(--ink);font-weight:700;font-family:"Frank Ruhl Libre",serif;font-size:1.15rem}
.list{columns:2 15rem;column-gap:24px;padding:0;list-style:none}.list li{break-inside:avoid;padding:5px 0;border-bottom:1px solid var(--line)}
.list a{text-decoration:none;color:var(--ink)}.list small{color:var(--muted)}
h2.sec{font-size:1.25rem;margin:28px 0 10px}
.related{display:flex;flex-wrap:wrap;gap:6px}.related a{padding:7px 12px;border-radius:99px;background:#f3ecdc;text-decoration:none;color:var(--ink);font-size:.93rem}
footer{max-width:860px;margin:0 auto;padding:22px 16px 40px;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line)}
footer a{color:var(--muted)}
@media (max-width:560px){.top nav a{padding:6px 7px;font-size:.88rem}.text{font-size:1.22rem}}
"""

def page(path, title, desc, h1, body, crumbs, app_hash="", lead="", extra_ld=None):
    url = SITE + path
    bc = [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate([("Tfilah", "/")] + crumbs)]
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": bc}]
    if extra_ld: ld.append(extra_ld)
    crumb_html = " · ".join(f'<a href="{u}">{esc(n)}</a>' for n, u in [("Tfilah", "/")] + crumbs[:-1])
    cta = (f'<div class="cta"><a class="btn" href="/#{app_hash}">פתיחה בסידור החכם</a>'
           f'<a class="btn alt" href="/#zikaron">תפילת רבים: תהילים משותפים</a></div>') if app_hash else ""
    doc = f"""<!doctype html>
<html lang="he" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Tfilah.com"><meta property="og:locale" content="he_IL">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/icons/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#fdfbf6"><link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&family=Frank+Ruhl+Libre:wght@400;700&display=swap">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style></head><body>
<header class="top"><div class="in"><a class="logo" href="/">Tfilah<span>.com</span></a>
<nav aria-label="ניווט"><a href="/tefila/">סידור</a><a href="/tehillim/">תהילים</a><a href="/sefer/">ספרייה</a><a href="/#zikaron">תפילת רבים</a></nav></div></header>
<main><div class="crumbs">{crumb_html}</div><h1>{esc(h1)}</h1>{f'<p class="lead">{esc(lead)}</p>' if lead else ''}{cta}{body}</main>
<footer>Tfilah.com · סידור תפילה, תהילים וזמני היום. הטקסטים מתוך מאגרי Sefaria ותורת אמת, ברשיונות חופשיים. · <a href="/">לאתר המלא</a></footer>
</body></html>
"""
    out = os.path.join(ROOT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(doc)
    URLS.append(path)

URLS = []

# ---------- Tehillim ----------
P = json.load(open(os.path.join(DATA, "tehillim.json"), encoding="utf-8"))
def ch_title(c):
    first = snippet(P[c - 1][0], 40)
    return first
for c in range(1, 151):
    vs = P[c - 1]
    body = '<article class="text">' + "".join(f'<p><sup>{gem(i+1)}</sup>{clean(v)}</p>' for i, v in enumerate(vs)) + "</article>"
    prev = f'<a href="/tehillim/{c-1}/"><small>→ הקודם</small>פרק {gem(c-1)}</a>' if c > 1 else "<span></span>"
    nxt = f'<a class="next" href="/tehillim/{c+1}/"><small>הבא ←</small>פרק {gem(c+1)}</a>' if c < 150 else "<span></span>"
    body += f'<nav class="pager">{prev}{nxt}</nav>'
    body += ('<h2 class="sec">עוד בתהילים</h2><div class="related">'
             '<a href="/tehillim/">כל 150 הפרקים</a><a href="/tehillim/20/">פרק כ (למצוקה)</a><a href="/tehillim/23/">פרק כג</a>'
             '<a href="/tehillim/91/">פרק צא (לשמירה)</a><a href="/tehillim/121/">פרק קכא (לדרך)</a><a href="/tehillim/130/">פרק קל (לרפואה)</a></div>')
    first = ch_title(c)
    page(f"/tehillim/{c}/",
         f"תהילים פרק {gem(c)} ({c}) | {first} | ניקוד מלא",
         f"תהילים פרק {gem(c)} בניקוד מלא, {len(vs)} פסוקים: {snippet(vs[0], 110).rstrip('…')}… קריאה אונליין, חלוקת תהילים ותפילה לעילוי נשמה.",
         f"תהילים פרק {gem(c)}", body, [("תהילים", "/tehillim/"), (f"פרק {gem(c)}", f"/tehillim/{c}/")],
         app_hash=f"t-{c}", lead=f"{first} · {len(vs)} פסוקים, בניקוד מלא.")

grid = '<div class="grid">' + "".join(f'<a href="/tehillim/{c}/" title="תהילים פרק {gem(c)}">{gem(c)}</a>' for c in range(1, 151)) + "</div>"
grid += ('<h2 class="sec">פרקים לפי בקשה</h2><div class="related"><a href="/tehillim/20/">ליום צרה: כ</a><a href="/tehillim/121/">לדרך: קכא</a>'
         '<a href="/tehillim/91/">לשמירה: צא</a><a href="/tehillim/130/">לרפואה: קל</a><a href="/tehillim/119/">קיט (אותיות השם)</a><a href="/#kelim">כלים: תהילים לפי השם</a></div>')
page("/tehillim/", "ספר תהילים אונליין | כל 150 הפרקים בניקוד מלא | Tfilah",
     "ספר תהילים המלא אונליין בניקוד: כל 150 הפרקים, תהילים יומי וחודשי, חלוקת תהילים משותפת לרפואה ולעילוי נשמה.",
     "ספר תהילים", grid, [("תהילים", "/tehillim/")], app_hash="tehillim",
     lead="כל 150 הפרקים בניקוד מלא. בחרו פרק, או פתחו חלוקת תהילים משותפת ושלחו לחברים.")

# ---------- Prayers ----------
I = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
NUS = I["nusachim"]
TEXTS = {n: json.load(open(os.path.join(DATA, f"{n}.json"), encoding="utf-8")) for n in NUS}
by_nus = {n: [p for p in I["prayers"] if p["n"] == n] for n in NUS}
for n, plist in by_nus.items():
    for i, p in enumerate(plist):
        paras = TEXTS[n].get(p["id"]) or []
        if not paras: continue
        body = '<article class="text">' + "".join(f"<p>{clean(x)}</p>" for x in paras) + "</article>"
        prev = f'<a href="/tefila/{plist[i-1]["id"]}/"><small>→ הקודם</small>{esc(plist[i-1]["t"])}</a>' if i > 0 else "<span></span>"
        nxt = f'<a class="next" href="/tefila/{plist[i+1]["id"]}/"><small>הבא ←</small>{esc(plist[i+1]["t"])}</a>' if i + 1 < len(plist) else "<span></span>"
        body += f'<nav class="pager">{prev}{nxt}</nav>'
        same = [q for q in I["prayers"] if q["t"] == p["t"] and q["n"] != n and q.get("s") == p.get("s")]
        if same:
            body += '<h2 class="sec">בנוסחים אחרים</h2><div class="related">' + "".join(f'<a href="/tefila/{q["id"]}/">{esc(p["t"])} · נוסח {esc(NUS[q["n"]])}</a>' for q in same) + "</div>"
        sec = " · ".join(p.get("s") or [])
        dup = sum(1 for q in plist if q["t"] == p["t"]) > 1
        name = f"{p['t']} {sec.split(' · ')[-1]}" if dup and sec else p["t"]
        page(f"/tefila/{p['id']}/",
             f"{name} | נוסח {NUS[n]} | בניקוד מלא | Tfilah",
             f"{p['t']} בנוסח {NUS[n]}, טקסט מלא בניקוד{(' (' + sec + ')') if sec else ''}: {snippet(' '.join(paras[:2]), 100)}",
             name, body, [("סידור", "/tefila/"), (f"נוסח {NUS[n]}", f"/tefila/#{n}"), (name, f"/tefila/{p['id']}/")],
             app_hash=f"p-{p['id']}", lead=f"נוסח {NUS[n]}{(' · ' + sec) if sec else ''}. טקסט מלא בניקוד.")

hub = ""
for n, plist in by_nus.items():
    hub += f'<h2 class="sec" id="{n}">נוסח {esc(NUS[n])}</h2><ul class="list">'
    hub += "".join(f'<li><a href="/tefila/{p["id"]}/">{esc(p["t"])}</a> <small>{esc(" · ".join(p.get("s") or []))}</small></li>' for p in plist if TEXTS[n].get(p["id"]))
    hub += "</ul>"
page("/tefila/", "סידור תפילה אונליין | עדות המזרח, ספרד ואשכנז | Tfilah",
     "סידור תפילה מלא אונליין בניקוד: שחרית, מנחה, ערבית, ברכת המזון, קריאת שמע על המיטה, שבת וחגים, בנוסח עדות המזרח, ספרד ואשכנז.",
     "סידור תפילה", hub, [("סידור", "/tefila/")], app_hash="siddur",
     lead="כל התפילות בשלושה נוסחים, בניקוד מלא. בסידור החכם רואים רק מה שאומרים היום.")

# ---------- Library ----------
B = json.load(open(os.path.join(DATA, "books.json"), encoding="utf-8"))
for k, b in B.items():
    body = '<article class="text">'
    for s in b["secs"]:
        if s.get("h"): body += f"<h2>{esc(s['h'])}</h2>"
        body += "".join(f'<p>{f"<sup>{gem(i+1)}</sup>" if b.get("num") else ""}{clean(v)}</p>' for i, v in enumerate(s["v"]))
    body += "</article>"
    page(f"/sefer/{k}/", f"{b['t']} | נוסח מלא בניקוד | Tfilah",
         f"{b['t']} בניקוד מלא אונליין. {b.get('sub','')}".strip(), b["t"], body,
         [("ספרייה", "/sefer/"), (b["t"], f"/sefer/{k}/")], app_hash=f"b-{k}", lead=b.get("sub", ""))
page("/sefer/", "ספרייה: פרקי אבות, מגילות, פרק שירה ועוד | Tfilah",
     "פרקי אבות, שיר השירים, רות, אסתר, איכה, קהלת, משלי, פרק שירה, סליחות, יזכור ועוד, בניקוד מלא.",
     "ספרייה", '<ul class="list">' + "".join(f'<li><a href="/sefer/{k}/">{esc(b["t"])}</a> <small>{esc(b.get("sub",""))}</small></li>' for k, b in B.items()) + "</ul>",
     [("ספרייה", "/sefer/")], app_hash="sifriya", lead="ספרים ופרקים שקוראים לאורך השנה.")

# ---------- sitemap ----------
def pri(u):
    return "0.9" if u.count("/") <= 2 else "0.7"
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f"  <url><loc>{SITE}/</loc><lastmod>{TODAY}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
sm += [f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{pri(u)}</priority></url>" for u in URLS]
sm.append("</urlset>")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm) + "\n")
print("pages:", len(URLS))
