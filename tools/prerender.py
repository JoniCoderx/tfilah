"""Static reading pages for תפילה (tfilah.com).

Generates a real, crawlable HTML page for every Tehillim chapter, every prayer
(per nusach) and every library book, plus hub pages and sitemap.xml.
These are first-class reading pages: the text starts right under a compact
header, with font-size and nikud tools that share the app's localStorage keys.
The interactive app stays at "/".

Run from the site root:  python3 tools/prerender.py
Then check the output:   python3 tools/seo-audit.py
"""
import json, os, re, html, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = "https://tfilah.com"
BRAND = "תפילה"
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

# ---------- brand ----------
def load_logo():
    """inline the header wordmark; the wrapping link carries the accessible name"""
    svg = open(os.path.join(ROOT, "brand", "logo-header.svg"), encoding="utf-8").read().strip()
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    svg = re.sub(r"<title>.*?</title>", "", svg, flags=re.S)
    head, rest = svg.split(">", 1)
    head = re.sub(r'\s(role|aria-label|width|height)="[^"]*"', "", head)
    return head + ' aria-hidden="true" focusable="false">' + rest

LOGO = load_logo()

CSS = """
:root{--paper:#F7F4EC;--surface:#FDFCF8;--ink:#18233F;--ink2:#2C3857;--muted:#586078;--line:#DAD6CA;--sunk:#ECE9E0;--stamp:#2456C8;
--reading:1.32rem;--f-head:"Frank Ruhl Libre","Noto Serif Hebrew",serif;--f-ui:"Heebo",system-ui,"Segoe UI",Arial,sans-serif;--f-read:"Noto Serif Hebrew","Frank Ruhl Libre","Times New Roman",serif;--top:3.25rem}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:calc(var(--top) + .75rem)}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f-ui);font-size:1rem;line-height:1.6;overflow-wrap:break-word}
a{color:var(--ink);text-underline-offset:.2em;text-decoration-thickness:1px}
a:hover{color:var(--stamp)}
:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
[hidden]{display:none!important}
.skip{position:absolute;inset-block-start:-5rem;inset-inline-start:.5rem;z-index:10;background:var(--ink);color:var(--paper);padding:.7rem 1rem;font-weight:700;text-decoration:none}
.skip:focus{inset-block-start:.5rem;color:var(--paper)}
.top{position:sticky;inset-block-start:0;z-index:5;background:var(--paper);border-block-end:1px solid var(--line)}
.top .in{max-width:40rem;margin-inline:auto;padding-inline:1rem;min-height:var(--top);display:flex;align-items:center;gap:.5rem}
.logo{display:inline-flex;align-items:center;min-height:2.75rem;flex:none}
.logo svg{display:block;height:1.875rem;width:auto}
.top nav{display:flex;margin-inline-start:auto;margin-inline-end:-.5rem}
.top nav a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.5rem;text-decoration:none;color:var(--ink2);font-weight:500;font-size:.95rem;white-space:nowrap}
.top nav a:hover{color:var(--stamp)}
main{max-width:40rem;margin-inline:auto;padding:1rem 1rem 3rem}
.hub main,.hub .top .in,.hub footer .in{max-width:60rem}
.crumbs{font-size:.84rem;color:var(--muted);line-height:1.4}
.crumbs a{color:var(--muted);text-decoration:none;display:inline-block;padding-block:.3rem}
.crumbs a:hover{color:var(--stamp);text-decoration:underline}
.crumbs span{padding-inline:.15rem}
h1{font-family:var(--f-head);font-weight:900;font-size:clamp(1.9rem,6.4vw,2.9rem);line-height:1.12;margin:.2rem 0 .3rem;letter-spacing:-.005em}
h1 .ctx{display:block;font-family:var(--f-ui);font-weight:500;font-size:.95rem;line-height:1.4;color:var(--ink2);letter-spacing:0;margin-block-start:.3rem}
.meta{margin:0 0 .5rem;color:var(--muted);font-size:.93rem}
.meta b{color:var(--ink);font-weight:700}
.lead{margin:0 0 1.5rem;color:var(--ink2);max-width:36rem}
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .5rem;margin:0 0 .5rem;min-height:0}
.tools{display:flex;gap:.375rem}
.tools button{min-width:2.75rem;min-height:2.75rem;padding-inline:.7rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:500 .95rem var(--f-ui);cursor:pointer;border-radius:2px}
.tools button:hover{border-color:var(--ink)}
.tools button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.tools button:disabled{color:var(--muted);cursor:default;border-color:var(--line)}
.tools .az{font-family:var(--f-head);font-weight:700;font-size:1.1rem}
.tools .az.sm{font-size:.9rem}
.nus{display:flex;align-items:center;flex-wrap:wrap;margin-inline-start:auto;font-size:.93rem;color:var(--muted)}
.nus a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.45rem;font-weight:500}
.text{background:var(--surface);border:1px solid var(--line);padding:1.25rem clamp(1rem,4.5vw,2.25rem) 1.5rem;font-family:var(--f-read);font-size:var(--reading);line-height:1.9;text-align:start;max-width:38rem;margin-inline:auto}
.text p{margin:0 0 .65em}.text p:last-child{margin-block-end:0}
.text sup{color:var(--stamp);font-family:var(--f-ui);font-weight:500;font-size:.58em;margin-inline-end:.4em;vertical-align:.5em;line-height:1}
.text h2{font-family:var(--f-head);font-weight:700;font-size:1.05em;line-height:1.3;margin:1.5em 0 .5em;padding-block-end:.3em;border-block-end:1px solid var(--line)}
.text h2:first-child{margin-block-start:0}
.text small{color:var(--ink2);font-size:.8em}
.text big{font-size:1.15em}
h1,h2,h3,[id]{scroll-margin-top:calc(var(--top) + .75rem)}
.pager{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:1.5rem 0 0}
.pager a{display:block;padding:.7rem .9rem;border:1px solid var(--line);text-decoration:none;color:var(--ink);font-family:var(--f-head);font-weight:700;font-size:1.05rem;line-height:1.35;min-height:2.75rem}
.pager a:hover{border-color:var(--ink);color:var(--ink)}
.pager small{display:block;color:var(--muted);font-family:var(--f-ui);font-weight:400;font-size:.8rem}
.pager .next{text-align:end}
h2.sec{font-family:var(--f-head);font-weight:700;font-size:1.4rem;line-height:1.25;margin:2.25rem 0 .6rem}
h2.sec.big{font-size:1.75rem;font-weight:900;border-block-start:1px solid var(--ink);padding-block-start:1.1rem;margin-block-start:3rem}
h3.grp{font-family:var(--f-ui);font-weight:700;font-size:.95rem;color:var(--ink2);margin:1.5rem 0 .2rem}
.related{display:flex;flex-wrap:wrap;gap:.4rem}
.related a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.85rem;border:1px solid var(--line);text-decoration:none;color:var(--ink);font-size:.95rem;border-radius:2px}
.related a:hover{border-color:var(--ink);color:var(--ink)}
.together{margin:2rem 0 0;padding:1.1rem 1.1rem 1.2rem;background:var(--sunk)}
.together h2{font-family:var(--f-head);font-weight:900;font-size:1.3rem;margin:0 0 .15rem}
.together p{margin:0 0 .8rem;color:var(--ink2)}
.btn{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:1.1rem;background:var(--ink);color:var(--paper);text-decoration:none;font-weight:700;border-radius:2px}
.btn:hover{background:var(--ink2);color:var(--paper)}
.applink{margin:1.5rem 0 0}
.applink a{display:inline-flex;align-items:center;min-height:2.75rem;font-weight:500}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(3.4rem,1fr));gap:.375rem}
.grid a{display:grid;place-items:center;min-height:3rem;border:1px solid var(--line);background:var(--surface);text-decoration:none;color:var(--ink);font-family:var(--f-head);font-weight:700;font-size:1.15rem}
.grid a:hover{border-color:var(--ink)}
.list{columns:2 16rem;column-gap:2rem;padding:0;margin:0;list-style:none}
.list li{break-inside:avoid;border-block-end:1px solid var(--line)}
.list a{display:block;padding-block:.6rem;text-decoration:none;color:var(--ink)}
.list a:hover{color:var(--stamp)}
.list small{display:block;color:var(--muted);font-size:.84rem}
.want{list-style:none;margin:0;padding:0;border-block-start:1px solid var(--line)}
.want li{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0 1rem;border-block-end:1px solid var(--line);padding-block:.25rem}
.want b{font-family:var(--f-head);font-weight:700;font-size:1.2rem}
.want span{display:flex;flex-wrap:wrap;margin-inline:-.5rem}
.want a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.5rem;font-size:.95rem}
.jump{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 .5rem}
footer{border-block-start:1px solid var(--line);color:var(--muted);font-size:.88rem}
footer .in{max-width:40rem;margin-inline:auto;padding:1.25rem 1rem 2.5rem}
footer p{margin:0 0 .4rem}
footer .sig{font-family:var(--f-head);font-weight:700;font-size:1.05rem;color:var(--ink)}
footer .sig span{font-family:var(--f-ui);font-weight:400;font-size:.88rem;color:var(--muted)}
footer nav{display:flex;flex-wrap:wrap;margin-inline:-.5rem}
footer nav a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.5rem;color:var(--ink2)}
@media (max-width:34rem){.want b{flex-basis:100%;padding-block-start:.4rem}}
@media (max-width:26rem){.top .in{padding-inline:.75rem;gap:.25rem}.logo svg{height:1.625rem}.top nav a{padding-inline:.4rem;font-size:.9rem}main{padding-inline:.75rem}}
@media (max-width:21.5rem){.logo svg{height:1.4rem}.top nav a{padding-inline:.3rem;font-size:.84rem}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
@media print{.top,.bar,.pager,.together,.applink,.related,footer nav,.skip{display:none}.text{border:0;padding:0}}
"""

# Runs in <head>: applies the reader's saved text size before first paint.
# Same key and format as the app: localStorage "fs" = JSON number in rem.
JS_HEAD = ("(function(){try{var v=JSON.parse(localStorage.getItem('fs'));"
           "if(typeof v==='number'&&v>=.95&&v<=2.6)document.documentElement.style.setProperty('--reading',v+'rem')}catch(e){}})()")

# Runs right after the text: size and nikud tools. Keys shared with the app:
# "fs" = JSON number (rem, .95 to 2.6, step .12, default 1.32); "nikud" = JSON true/false.
JS_TOOLS = r"""(function(){
var art=document.getElementById('text'),bar=document.getElementById('tools');if(!art||!bar)return;
var NIK=/[֑-ֽֿ-ׇ]/g,orig=art.innerHTML,MIN=.95,MAX=2.6,STEP=.12;
function get(k,d){try{var v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}}
function set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
var fs=get('fs',1.32),nik=get('nikud',true);
if(typeof fs!=='number'||!(fs>=MIN&&fs<=MAX))fs=1.32;
nik=nik!==false;
var fm=document.getElementById('fm'),fp=document.getElementById('fp'),nk=document.getElementById('nk');
function size(){document.documentElement.style.setProperty('--reading',fs+'rem');fm.disabled=fs<=MIN;fp.disabled=fs>=MAX}
function nikud(){art.innerHTML=nik?orig:orig.replace(NIK,'');nk.setAttribute('aria-pressed',nik?'true':'false');nk.setAttribute('aria-label',nik?'הסתרת הניקוד':'הצגת הניקוד')}
fm.onclick=function(){fs=Math.max(MIN,+(fs-STEP).toFixed(2));set('fs',fs);size()};
fp.onclick=function(){fs=Math.min(MAX,+(fs+STEP).toFixed(2));set('fs',fs);size()};
nk.onclick=function(){nik=!nik;set('nikud',nik);nikud()};
size();if(!nik)nikud();else nk.setAttribute('aria-pressed','true');
bar.hidden=false;
})()"""

TOOLS_HTML = ('<div class="tools" id="tools" role="group" aria-label="כלי קריאה" hidden>'
              '<button type="button" id="fm" class="az sm" aria-label="הקטנת הטקסט">א−</button>'
              '<button type="button" id="fp" class="az" aria-label="הגדלת הטקסט">א+</button>'
              '<button type="button" id="nk" aria-pressed="true" aria-label="הסתרת הניקוד">ניקוד</button></div>')

NAV = ('<nav aria-label="ניווט ראשי"><a href="/tefila/">סידור</a><a href="/tehillim/">תהילים</a>'
       '<a href="/sefer/">ספרייה</a><a href="/#zikaron">תהילים יחד</a></nav>')

URLS = []
TITLES = {}

def page(path, title, desc, h1, crumbs, text="", meta="", bar_extra="", after="", before="", lead="", app_hash="", h1_ctx="", hub=False):
    """text = the sacred text as an <article> body (reading pages); before/after = page chrome around it."""
    url = SITE + path
    assert path.startswith("/") and path.endswith("/"), path
    assert title not in TITLES, f"duplicate title: {title!r} ({path} and {TITLES[title]})"
    TITLES[title] = path
    allc = [(BRAND, "/")] + crumbs
    bc = [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(allc)]
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": bc}]
    crumb_html = "<span>›</span>".join(f'<a href="{u}">{esc(n)}</a>' for n, u in allc[:-1])
    h1_html = esc(h1) + (f' <span class="ctx">{esc(h1_ctx)}</span>' if h1_ctx else "")
    reading = ""
    if text:
        bar = f'<div class="bar">{TOOLS_HTML}{bar_extra}</div>'
        reading = f'{bar}<article class="text" id="text">{text}</article><script>{JS_TOOLS}</script>'
    applink = f'<p class="applink"><a href="/#{app_hash}">לפתיחה באפליקציה</a></p>' if app_hash else ""
    doc = f"""<!doctype html>
<html lang="he" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{'website' if hub else 'article'}"><meta property="og:site_name" content="{BRAND}"><meta property="og:locale" content="he_IL">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/icons/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#F7F4EC"><link rel="icon" href="/brand/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@700;900&family=Heebo:wght@400;500;700&family=Noto+Serif+Hebrew:wght@400;700&display=swap">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style><script>{JS_HEAD}</script></head><body{' class="hub"' if hub else ''}>
<a class="skip" href="#{'text' if text else 'main'}">{'דילוג לטקסט' if text else 'דילוג לתוכן'}</a>
<header class="top"><div class="in"><a class="logo" href="/" aria-label="תפילה, לדף הבית">{LOGO}</a>
{NAV}</div></header>
<main id="main"><nav class="crumbs" aria-label="מיקום באתר">{crumb_html}</nav><h1>{h1_html}</h1>{f'<p class="meta">{meta}</p>' if meta else ''}{f'<p class="lead">{esc(lead)}</p>' if lead else ''}{before}{reading}{after}{applink}</main>
<footer><div class="in"><p class="sig">תפילה <span>· tfilah.com</span></p><p>סידור תפילה, תהילים וזמני היום. הטקסטים מתוך מאגרי Sefaria ותורת אמת, ברשיונות חופשיים.</p>
<nav aria-label="קישורי תחתית"><a href="/tefila/">סידור</a><a href="/tehillim/">תהילים</a><a href="/sefer/">ספרייה</a></nav></div></footer>
</body></html>
"""
    out = os.path.join(ROOT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    URLS.append(path)

def pager(prev, nxt):
    """prev / nxt = (href, label) or None"""
    a = f'<a href="{prev[0]}" rel="prev"><small>הקודם</small>{esc(prev[1])}</a>' if prev else "<span></span>"
    b = f'<a class="next" href="{nxt[0]}" rel="next"><small>הבא</small>{esc(nxt[1])}</a>' if nxt else "<span></span>"
    return f'<nav class="pager" aria-label="הקודם והבא">{a}{b}</nav>'

# ---------- Tehillim ----------
P = json.load(open(os.path.join(DATA, "tehillim.json"), encoding="utf-8"))
TOGETHER = ('<aside class="together" aria-labelledby="tg"><h2 id="tg">תהילים יחד</h2>'
            '<p>כל אחד פרק. ביחד ספר שלם.</p><a class="btn" href="/#zikaron">לקריאה משותפת</a></aside>')
for c in range(1, 151):
    vs = P[c - 1]
    text = "".join(f'<p><sup>{gem(i+1)}</sup>{clean(v)}</p>' for i, v in enumerate(vs))
    after = pager((f"/tehillim/{c-1}/", f"פרק {gem(c-1)}") if c > 1 else None,
                  (f"/tehillim/{c+1}/", f"פרק {gem(c+1)}") if c < 150 else None)
    after += TOGETHER
    after += ('<h2 class="sec">עוד בתהילים</h2><div class="related">'
              '<a href="/tehillim/">כל 150 הפרקים</a><a href="/tehillim/20/">פרק כ (למצוקה)</a><a href="/tehillim/23/">פרק כג</a>'
              '<a href="/tehillim/91/">פרק צא (לשמירה)</a><a href="/tehillim/121/">פרק קכא (לדרך)</a><a href="/tehillim/130/">פרק קל (לרפואה)</a></div>')
    first = snippet(vs[0], 40)
    nv = "פסוק אחד" if len(vs) == 1 else f"{len(vs)} פסוקים"
    page(f"/tehillim/{c}/",
         f"תהילים פרק {gem(c)} ({c}) | {first} | {BRAND}",
         f"תהילים פרק {gem(c)} ({c}) בניקוד מלא, {nv}: {snippet(vs[0], 110).rstrip('…')}… קריאה נוחה בנייד, עם שליטה בגודל הטקסט ובניקוד.",
         f"תהילים פרק {gem(c)}", [("תהילים", "/tehillim/"), (f"פרק {gem(c)}", f"/tehillim/{c}/")],
         text=text, meta=f"{esc(first)} · {nv}", after=after, app_hash=f"t-{c}")

grid = '<div class="grid">' + "".join(f'<a href="/tehillim/{c}/" title="תהילים פרק {gem(c)} ({c})">{gem(c)}</a>' for c in range(1, 151)) + "</div>"
grid += ('<h2 class="sec">פרקים לפי בקשה</h2><div class="related"><a href="/tehillim/20/">ליום צרה: כ</a><a href="/tehillim/121/">לדרך: קכא</a>'
         '<a href="/tehillim/91/">לשמירה: צא</a><a href="/tehillim/130/">לרפואה: קל</a><a href="/tehillim/119/">קיט (אותיות השם)</a><a href="/#kelim">כלים: תהילים לפי השם</a></div>')
grid += TOGETHER
page("/tehillim/", f"ספר תהילים אונליין | כל 150 הפרקים בניקוד מלא | {BRAND}",
     "ספר תהילים המלא אונליין בניקוד: כל 150 הפרקים, פרק בכל עמוד, וקריאת תהילים משותפת לרפואה ולעילוי נשמה.",
     "ספר תהילים", [("תהילים", "/tehillim/")], after=grid, app_hash="tehillim", hub=True,
     lead="כל 150 הפרקים בניקוד מלא. בחרו פרק והתחילו לקרוא.")

# ---------- Prayers ----------
I = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
NUS = I["nusachim"]
TEXTS = {n: json.load(open(os.path.join(DATA, f"{n}.json"), encoding="utf-8")) for n in NUS}
by_nus = {n: [p for p in I["prayers"] if p["n"] == n and TEXTS[n].get(p["id"])] for n in NUS}

def sec_of(p):
    return [x for x in (p.get("s") or []) if x]

def norm_t(t):
    """title key for cross-nusach matching: spelling variants only, never meaning"""
    t = plain(t).replace('"', "").replace("״", "").replace("'", "").replace("׳", "")
    for a, b in (("תפלת", "תפילת"), ("שעל המיטה", "על המיטה"), ("על המטה", "על המיטה"), ("לימות החול", "לימי החול")):
        t = t.replace(a, b)
    return t.strip()

def norm_s(p):
    return tuple(norm_t(x) for x in sec_of(p))

# Disambiguate prayers that share a title inside one nusach (e.g. "עמידה" of
# shacharit / mincha) by their section path.
CTX = {}
for n, plist in by_nus.items():
    groups = {}
    for p in plist:
        groups.setdefault(p["t"], []).append(p)
    for t, g in groups.items():
        if len(g) == 1:
            continue
        seen = {}
        for p in g:
            # the full section path: "אבות (שבת · שחרית · עמידה)" is clear to a reader, a shorter tail is not
            s = sec_of(p)
            ctx = " · ".join(s)
            # identical title and identical section: number them in order
            clash = [q for q in g if sec_of(q) == s]
            if len(clash) > 1:
                ctx = (ctx + " · " if ctx else "") + f"חלק {gem(clash.index(p) + 1)}"
            if not ctx:
                continue  # the only one of its title without a section keeps the bare title
            assert ctx not in seen, (p["id"], ctx)
            seen[ctx] = 1
            CTX[p["id"]] = ctx

# Counterparts in the other nusachim. Only real ones:
#  1. same title and same section path (after spelling normalisation), or
#  2. same title where the title is unique in BOTH nusachim (no guessing between several), or
#  3. the hand-checked most-wanted prayers below (WANT), e.g. "מודה אני" of the weekday morning.
T_COUNT = {n: {} for n in NUS}
for n, plist in by_nus.items():
    for p in plist:
        T_COUNT[n].setdefault(norm_t(p["t"]), []).append(p)

def counterparts(p):
    out = []
    key = norm_t(p["t"])
    for m in NUS:
        if m == p["n"]:
            continue
        cands = T_COUNT[m].get(key, [])
        exact = [q for q in cands if norm_s(q) == norm_s(p)]
        if len(exact) == 1:
            out.append(exact[0])
        elif len(cands) == 1 and len(T_COUNT[p["n"]][key]) == 1:
            out.append(cands[0])
    return out

def pname(p):
    return p["t"] + (f" ({CTX[p['id']]})" if CTX.get(p["id"]) else "")

# Most-wanted prayers: plain links per nusach, ids looked up in the index (no new URLs).
def first_in(n, *prefixes):
    """first prayer of a service: section path starts with one of the given paths"""
    for p in by_nus[n]:
        s = sec_of(p)
        if any(s[:len(pre)] == list(pre) for pre in prefixes):
            return p
    return None

def by_title(n, *titles):
    keys = [norm_t(t) for t in titles]
    for p in by_nus[n]:
        if norm_t(p["t"]) in keys:
            return p
    return None

WANT = [
    ("שחרית", "לימי חול", lambda n: first_in(n, ["שחרית לימי החול"], ["שחרית לימות החול"], ["ימי חול", "תפילת שחרית"])),
    ("מנחה", "לימי חול", lambda n: first_in(n, ["מנחה לימי החול"], ["מנחה לימות החול"], ["ימי חול", "תפילת מנחה"])),
    ("ערבית", "לימי חול", lambda n: first_in(n, ["ערבית לימי החול"], ["ערבית לימות החול"], ["ימי חול", "מעריב"])),
    ("תפילת הדרך", "", lambda n: by_title(n, "תפילת הדרך")),
    ("ברכת המזון", "", lambda n: by_title(n, "ברכת המזון")),
    ("קריאת שמע שעל המיטה", "", lambda n: by_title(n, "קריאת שמע על המיטה")),
    ("מודה אני", "", lambda n: by_title(n, "מודה אני")),
    ("ברכות השחר", "", lambda n: by_title(n, "ברכות השחר")),
]
SAME = {p["id"]: counterparts(p) for plist in by_nus.values() for p in plist}
for label, note, find in WANT:
    if note: continue  # services: "first prayer of the service" is an entry point, not the same prayer
    grp = [q for q in (find(n) for n in NUS) if q]
    for q in grp:
        for r in grp:
            if r is not q and all(x["n"] != r["n"] for x in SAME[q["id"]]):
                SAME[q["id"]].append(r)
for v in SAME.values():
    v.sort(key=lambda q: list(NUS).index(q["n"]))

for n, plist in by_nus.items():
    for i, p in enumerate(plist):
        paras = TEXTS[n][p["id"]]
        text = "".join(f"<p>{clean(x)}</p>" for x in paras)
        assert plain(text), p["id"]
        after = pager((f'/tefila/{plist[i-1]["id"]}/', plist[i-1]["t"]) if i > 0 else None,
                      (f'/tefila/{plist[i+1]["id"]}/', plist[i+1]["t"]) if i + 1 < len(plist) else None)
        same = SAME[p["id"]]
        switch = ""
        if same:
            after += ('<h2 class="sec">אותה תפילה בנוסח אחר</h2><div class="related">'
                      + "".join(f'<a href="/tefila/{q["id"]}/">{esc(q["t"])} · נוסח {esc(NUS[q["n"]])}</a>' for q in same) + "</div>")
            switch = ('<nav class="nus" aria-label="אותה תפילה בנוסח אחר"><span>גם בנוסח</span>'
                      + "".join(f'<a href="/tefila/{q["id"]}/">{esc(NUS[q["n"]])}</a>' for q in same) + "</nav>")
        sec = " · ".join(sec_of(p))
        ctx = CTX.get(p["id"], "")
        name = pname(p)
        page(f"/tefila/{p['id']}/",
             f"{name} | נוסח {NUS[n]} | {BRAND}",
             f"{p['t']} בנוסח {NUS[n]}, טקסט מלא בניקוד{(' (' + sec + ')') if sec else ''}: {snippet(' '.join(paras[:2]), 100)}",
             p["t"], [("סידור", "/tefila/"), (f"נוסח {NUS[n]}", f"/tefila/#{n}"), (name, f"/tefila/{p['id']}/")],
             text=text, meta=f'<b>נוסח {esc(NUS[n])}</b>{(" · " + esc(sec)) if sec and not ctx else ""}',
             h1_ctx=ctx, bar_extra=switch, after=after, app_hash=f"p-{p['id']}")

want = '<h2 class="sec" id="mevukashot">התפילות המבוקשות</h2><ul class="want">'
WANT_REPORT = []
for label, note, find in WANT:
    links = ""
    for n in NUS:
        q = find(n)
        WANT_REPORT.append((label, n, q["id"] if q else None, q["t"] if q else None))
        if q:
            links += f'<a href="/tefila/{q["id"]}/" title="{esc(label)} בנוסח {esc(NUS[n])}: {esc(pname(q))}">נוסח {esc(NUS[n])}</a>'
    if links:
        want += f'<li><b>{esc(label)}</b><span>{links}</span></li>'
want += "</ul>"

hub = want + '<h2 class="sec">כל התפילות לפי נוסח</h2><div class="jump related">' + "".join(f'<a href="#{n}">נוסח {esc(NUS[n])}</a>' for n in NUS) + "</div>"
for n, plist in by_nus.items():
    hub += f'<h2 class="sec big" id="{n}">נוסח {esc(NUS[n])}</h2>'
    cur, opened = None, False
    for p in plist:
        s = " · ".join(sec_of(p))
        if s != cur or not opened:
            if opened: hub += "</ul>"
            hub += f'<h3 class="grp">{esc(s) if s else "תפילות וברכות"}</h3><ul class="list">'
            cur, opened = s, True
        hub += f'<li><a href="/tefila/{p["id"]}/">{esc(p["t"])}</a></li>'
    if opened: hub += "</ul>"
page("/tefila/", f"סידור תפילה אונליין | עדות המזרח, ספרד ואשכנז | {BRAND}",
     "סידור תפילה מלא אונליין בניקוד: שחרית, מנחה, ערבית, ברכת המזון, תפילת הדרך, קריאת שמע שעל המיטה, שבת וחגים, בנוסח עדות המזרח, ספרד ואשכנז.",
     "סידור תפילה", [("סידור", "/tefila/")], after=hub, app_hash="siddur", hub=True,
     lead="כל התפילות בשלושה נוסחים, בניקוד מלא. כל תפילה בעמוד קריאה משלה.")

# ---------- Library ----------
B = json.load(open(os.path.join(DATA, "books.json"), encoding="utf-8"))
for k, b in B.items():
    text = ""
    for j, s in enumerate(b["secs"]):
        if s.get("h"): text += f'<h2 id="s{j+1}">{esc(s["h"])}</h2>'
        text += "".join(f'<p>{f"<sup>{gem(i+1)}</sup>" if b.get("num") else ""}{clean(v)}</p>' for i, v in enumerate(s["v"]))
    after = '<h2 class="sec">עוד בספרייה</h2><div class="related"><a href="/sefer/">כל הספרים</a><a href="/tehillim/">ספר תהילים</a><a href="/tefila/">סידור תפילה</a></div>'
    page(f"/sefer/{k}/", f"{b['t']} | נוסח מלא בניקוד | {BRAND}",
         f"{b['t']} בניקוד מלא אונליין. {b.get('sub','')}".strip(), b["t"],
         [("ספרייה", "/sefer/"), (b["t"], f"/sefer/{k}/")],
         text=text, meta=esc(b.get("sub", "")), after=after, app_hash=f"b-{k}")
page("/sefer/", f"ספרייה: פרקי אבות, מגילות, פרק שירה ועוד | {BRAND}",
     "פרקי אבות, שיר השירים, רות, אסתר, איכה, קהלת, משלי, פרק שירה, סליחות, יזכור ועוד, בניקוד מלא.",
     "ספרייה", [("ספרייה", "/sefer/")],
     after='<ul class="list">' + "".join(f'<li><a href="/sefer/{k}/">{esc(b["t"])}<small>{esc(b.get("sub",""))}</small></a></li>' for k, b in B.items()) + "</ul>",
     app_hash="sifriya", hub=True, lead="ספרים ופרקים שקוראים לאורך השנה.")

# ---------- sitemap ----------
def pri(u):
    return "0.9" if u.count("/") <= 2 else "0.7"
assert len(set(URLS)) == len(URLS)
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f"  <url><loc>{SITE}/</loc><lastmod>{TODAY}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
sm += [f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{pri(u)}</priority></url>" for u in URLS]
sm.append("</urlset>")
with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write("\n".join(sm) + "\n")
print("pages:", len(URLS))
print("prayer pages with a counterpart in another nusach:", sum(1 for v in SAME.values() if v), "of", len(SAME))
print("most-wanted:")
for label, n, pid, t in WANT_REPORT:
    print(f"  {label} | {n} | {pid or 'NO COUNTERPART'} | {t or ''}")
