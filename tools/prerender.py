"""Static reading pages for תפילה (tfilah.com).

Generates real, crawlable HTML for:
  /tehillim/<1-150>/            every Tehillim chapter
  /tehillim/<need>/             Tehillim by need (the app's NEEDS list), chapters in full
  /tehillim/yomi/               the monthly and weekly division of the book
  /siddur/<nusach>-<n>/         every prayer, per nusach
  /siddur/<nusach>/             nusach hub
  /siddur/<nusach>/<service>/   weekday shacharit / mincha / arvit: ordered contents
  /sefer/<key>/                 library books
  /tehillim-yachad/, /kelim/    explainers that lead into the app
  hubs, 404.html and sitemap.xml

The sacred texts come from data/ only and are never altered. Lists that the app
owns (NEEDS, MONTHLY, WEEKLY, KELIM) are read from src/app.html so the static
pages cannot drift from the app.

Run from the site root:  python3 tools/prerender.py
Then check the output:   python3 tools/seo-audit.py
"""
import json, os, re, html, datetime, hashlib
from urllib.parse import quote

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

def ungem(s):
    vals = dict(zip("אבגדהוזחטיכלמנסעפצקרשת", [1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100,200,300,400]))
    return sum(vals.get(c, 10**6) for c in s)

def clean(s):
    """keep only harmless formatting tags from the source text"""
    s = html.escape(TAG.sub(lambda m: m.group(0) if OK_TAGS.fullmatch(m.group(0)) else "", s), quote=False)
    return re.sub(r"&lt;(/?(?:b|i|small|big|br)\s*/?)&gt;", r"<\1>", s, flags=re.I)

def plain(s):
    """a derived, unpointed one-line rendering for titles, descriptions and opening lines (never shown as the text itself)"""
    s = re.sub(r"(?<=[\u0591-\u05EA])</?(?:b|big)>(?=[\u05D0-\u05EA])", "", s)
    s = re.sub(r"[\u200b-\u200d\u2060\ufeff]", "", s)
    return re.sub(r" ([,.:;])", r"\1", re.sub(r"\s+", " ", NIK.sub("", TAG.sub(" ", s).replace("־", " ")).replace("—", " "))).replace("יהוה", "ה'").strip()

def snippet(s, n=150):
    s = plain(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(" ,;:.(־-") + "…"

def esc(s):
    return html.escape(s, quote=True)

TAILS = ("טקסט מלא בניקוד.", "קריאה נוחה בנייד, עם שליטה בגודל הכתב ובהצגת הניקוד.", "באתר תפילה, כל התפילות במקום אחד.")

def fit_desc(head, body="", tails=TAILS):
    """meta description of 120 to 160 characters: the head, then as much of the opening as fits (whole words only)"""
    d = head
    room = 156 - len(head) - 2
    if body and room >= 18:
        d = head + ": " + snippet(body, room)
    if not d.endswith("…"):
        d = d.rstrip(" ,;:.") + "."
    for t in tails:
        if len(d) >= 120:
            break
        if len(d) + 1 + len(t) <= 160:
            d += " " + t
    return d

# ---------- lists owned by the app (read only) ----------
APP_SRC = open(os.path.join(ROOT, "src", "app.html"), encoding="utf-8").read()
PLAIN_T_EARLY = json.loads(re.search(r"^const PLAIN_T=(\{.*\});$", APP_SRC, re.M).group(1))

def app_const(name):
    m = re.search(r"const " + name + r"=(\[.*?\]);", APP_SRC, flags=re.S)
    assert m, f"{name} not found in src/app.html"
    return m.group(1)

NEEDS = [(k, t, [int(x) for x in ch.split(",")])
         for k, t, ch in re.findall(r"\['([a-z]+)','[a-z]+','([^']+)','[^']*',\[([\d,]+)\]\]", app_const("NEEDS"))]
assert len(NEEDS) >= 12 and all(1 <= c <= 150 for _, _, chs in NEEDS for c in chs), NEEDS
MONTHLY = json.loads(app_const("MONTHLY"))
WEEKLY = json.loads(app_const("WEEKLY"))
assert len(MONTHLY) == 30 and len(WEEKLY) == 7
KELIM = re.findall(r"\['([a-z]+)','([^']+)','([^']+)','[a-z]+'\]", app_const("KELIM"))
assert len(KELIM) >= 6, KELIM
DAYS = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']

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

# ---------- CSS: a small base plus blocks that ship only on pages that use them ----------
CSS_BASE = """
:root{--paper:#FFFFFF;--surface:#FFFFFF;--ink:#0B2E4F;--ink2:#27506F;--muted:#46677F;--line:#DDEEF9;--sunk:#F3F9FE;--stamp:#0A6CA8;--tint:#B3E0FA;--grad:linear-gradient(135deg,#1389D6,#0B79C0 50%,#0A6FB3);
--sh:0 1px 2px rgba(11,46,79,.05),0 10px 28px -16px rgba(11,46,79,.22);--r:1.375rem;
--reading:1.32rem;--f-disp:"Heebo","Assistant",system-ui,Arial,sans-serif;--f-ui:"Assistant",system-ui,"Segoe UI",Arial,sans-serif;--f-read:"Heebo","Assistant",system-ui,Arial,sans-serif;--top:3.5rem}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:calc(var(--top) + .75rem)}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f-ui);font-size:1rem;line-height:1.6;overflow-wrap:break-word}body::after{content:"";position:fixed;inset:0;z-index:-1;background:var(--paper);pointer-events:none}@media print{body::after{display:none}}
a{color:var(--stamp);text-underline-offset:.2em;text-decoration-thickness:1px}
a:hover{color:var(--ink)}
:focus-visible{outline:2px solid var(--stamp);outline-offset:2px;border-radius:.5rem}
[hidden]{display:none!important}
.skip{position:absolute;inset-block-start:-5rem;inset-inline-start:.5rem;z-index:10;background:var(--ink);color:#fff;padding:.7rem 1.1rem;font-weight:700;text-decoration:none;border-radius:999px}
.skip:focus{inset-block-start:.5rem;color:#fff}
.top{position:sticky;inset-block-start:0;z-index:5;background:rgba(255,255,255,.94);border-block-end:1px solid var(--line)}.dclose{margin:0;padding:6px 16px 16px;text-align:center}details:not([open])>.dclose{display:none}.dclose button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:46px;padding:0 22px;border-radius:999px;border:1px solid var(--line);background:var(--sunk,#F3F9FE);color:var(--ink);font:inherit;font-weight:700;cursor:pointer}.dkt{flex:none;display:inline-grid;place-items:center;inline-size:2.75rem;block-size:2.75rem;border:1px solid var(--line);border-radius:999px;background:none;color:inherit;cursor:pointer;margin-inline-start:.25rem}.dkt[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}header.top nav{margin-inline-end:0}@media(max-width:33rem){.dkt{inline-size:2.25rem;block-size:2.25rem;margin-inline-start:0}header.top .in{gap:.2rem}header.top nav a{padding-inline:.3rem;font-size:.86rem}header.top .logo svg{height:1.45rem}}@media(max-width:23.5rem){.dkt{inline-size:2rem;block-size:2rem}header.top .in{padding-inline:.5rem;gap:.1rem}header.top nav a{padding-inline:.17rem;font-size:.78rem}header.top .logo svg{height:1.25rem}}@media(max-width:21rem){header.top .in{padding-inline:.4rem;gap:0}header.top nav a{padding-inline:.1rem;font-size:.76rem}header.top .logo svg{height:1.15rem}}html::before{content:"";position:fixed;inset-inline:0;top:-240px;block-size:240px;background:#fff;z-index:2147483000;pointer-events:none}.totop{position:fixed;inset-inline-end:14px;bottom:calc(0px + 16px + env(safe-area-inset-bottom,0px));z-index:44;display:none;place-items:center;inline-size:48px;block-size:48px;border-radius:50%;border:1px solid var(--line);background:#fff;color:var(--ink);box-shadow:0 8px 22px -10px rgba(11,46,79,.45);cursor:pointer;opacity:0;visibility:hidden;transform:translateY(8px);transition:opacity .25s ease,transform .25s ease,visibility 0s .25s}.totop.on{opacity:1;visibility:visible;transform:none;transition:opacity .2s ease,transform .2s ease}@media (max-width:820px){.totop{display:grid}}@media (prefers-reduced-motion:reduce){.totop{transition:none}}@media print{.totop{display:none!important}}.top::before{content:"";position:absolute;inset-inline:0;inset-block-end:100%;block-size:160px;background:#fff;pointer-events:none}
.top .in{max-width:40rem;margin-inline:auto;padding-inline:1rem;min-height:var(--top);display:flex;align-items:center;gap:.5rem}
.logo{display:inline-flex;align-items:center;min-height:2.75rem;flex:none}
.logo svg{display:block;height:1.875rem;width:auto}
.top nav{display:flex;margin-inline-start:auto;margin-inline-end:-.5rem}
.top nav a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.6rem;text-decoration:none;color:var(--ink2);font-weight:600;font-size:.95rem;white-space:nowrap;border-radius:999px}
.top nav a:hover{background:var(--sunk);color:var(--ink)}
main{max-width:40rem;margin-inline:auto;padding:1rem 1rem 3rem}
.hub main,.hub .top .in,.hub footer .in{max-width:60rem}
.crumbs{font-size:.84rem;color:var(--muted);line-height:1.4}
.crumbs a{color:var(--muted);text-decoration:none;display:inline-block;padding-block:.3rem}
.crumbs a:hover{color:var(--stamp);text-decoration:underline}
.crumbs span{padding-inline:.15rem}
h1{font-family:var(--f-disp);font-weight:900;font-size:clamp(2.2rem,7.4vw,3.3rem);line-height:1.12;margin:.2rem 0 .3rem;letter-spacing:-.022em}
.hctx{margin:.3rem 0 0;font-family:var(--f-ui);font-weight:600;font-size:.95rem;line-height:1.4;color:var(--ink2)}.rd .hctx{font-size:1.1rem}h1 .ctx{display:block;font-family:var(--f-ui);font-weight:600;font-size:.95rem;line-height:1.4;color:var(--ink2);letter-spacing:0;margin-block-start:.3rem}
.meta{margin:0 0 .5rem;color:var(--muted);font-size:.93rem}
.meta b{color:var(--ink);font-weight:700}
.meta a{color:var(--ink2);display:inline-block;padding-block:.8rem;margin-block:-.8rem}
.lead{margin:0 0 1.25rem;color:var(--ink2);max-width:36rem;font-size:1.05rem}
h1,h2,h3,[id]{scroll-margin-top:calc(var(--top) + .75rem)}
h2.sec{font-family:var(--f-disp);font-weight:900;font-size:1.7rem;line-height:1.25;margin:2.25rem 0 .7rem}
.related{display:flex;flex-wrap:wrap;gap:.45rem}
.related.jr{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;padding-block:2px;margin-inline:-2px;padding-inline:2px}.related.jr::-webkit-scrollbar{display:none}.related.jr a{flex:none}
@media (max-width:480px){.related.jr{gap:.25rem}.related.jr a{padding:.3rem .5rem;font-size:.85rem}}
.related a{display:inline-flex;align-items:center;min-height:2.75rem;padding:.3rem 1rem;border:1px solid var(--line);background:var(--surface);text-decoration:none;color:var(--ink);font-size:.95rem;font-weight:600;line-height:1.3;border-radius:999px}
.related a:hover{border-color:var(--stamp);color:var(--stamp)}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:3rem;padding:.4rem 1.5rem;background:var(--grad);color:#fff;text-decoration:none;font-weight:700;border-radius:999px;box-shadow:var(--sh)}
.btn:hover{color:#fff;filter:brightness(1.08)}
.applink{margin:1.5rem 0 0}
.applink a{display:inline-flex;align-items:center;min-height:2.75rem;font-weight:600}
html[data-theme=dark]{background:#fff;filter:invert(1) hue-rotate(180deg)}.tint{display:none}html[data-theme=dark] .tint{display:block;position:fixed;inset:0 0 auto 0;block-size:6px;z-index:2147483000;background:#000;filter:invert(1) hue-rotate(180deg)}@media print{.tint{display:none!important}}html[data-theme=dark] img,html[data-theme=dark] .mm-pic svg,html[data-theme=dark] .mm-tile .ib svg,html[data-theme=dark] .mm-sug svg,html[data-theme=dark] .mm-pick svg,html[data-theme=dark] .mm-chip svg,html[data-theme=dark] canvas{filter:invert(1) hue-rotate(180deg)}.dkb{display:inline-flex;align-items:center;gap:.4rem;min-height:2.75rem;padding:.3rem .8rem;border:1px solid var(--line);border-radius:999px;background:none;color:inherit;font:inherit;font-weight:600;cursor:pointer}.dkb[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}footer.sitefoot{border-block-start:1px solid var(--line);margin-block-start:2rem;color:var(--muted);font-size:.9rem}.flegal{display:flex;flex-wrap:wrap;gap:.25rem .5rem;margin:.4rem 0 .5rem;font-size:.85rem}.flegal a{display:inline-flex;align-items:center;justify-content:center;min-height:2.75rem;min-width:2.75rem;padding-inline:.5rem;color:inherit}.fcredit a{display:inline-flex;align-items:center;min-height:2.75rem}.fcols{display:grid;gap:8px 32px;grid-template-columns:1.3fr 1fr 1fr;align-items:start}.fbrand .flogo{display:inline-flex;color:var(--ink)}.fbrand .flogo svg{display:block;block-size:28px;inline-size:auto}.fbrand b{display:block;margin-block-start:8px;color:var(--ink);font-weight:700}.fbrand p{margin:2px 0 0}.fbrand .fbtns{display:grid;gap:10px;margin-block-start:14px;max-inline-size:340px}.fbtns .ffb,.fbtns .fshare{justify-content:center;margin:0;min-block-size:48px;font-size:.95rem}.fbtns .fshare{background:linear-gradient(135deg,#1AA45B,#0E7F42);box-shadow:0 10px 20px -12px rgba(19,148,81,.8)}.fbtns .fshare:hover{background:linear-gradient(135deg,#16954F,#0B6F39)}.fbtns .ffb{background:#1877F2}.fbtns .ffb:hover{background:#166AD8}.fshare{display:inline-flex;align-items:center;gap:8px;min-block-size:44px;margin-block-start:10px;padding:0 16px;border-radius:999px;background:#127A3E;color:#fff;font-weight:700;font-size:.92rem;text-decoration:none}.fshare:hover{background:#0E6633}.fshare svg{flex:none}.ffb{display:inline-flex;align-items:center;gap:8px;min-block-size:44px;margin-block-start:10px;margin-inline-end:8px;padding:0 16px;border-radius:999px;background:#1565D8;color:#fff;font-weight:700;font-size:.92rem;text-decoration:none}.fbrand .ffb:hover{background:#0F55BF}.fbrand .ffb svg{flex:none}html[data-theme=dark] .fbrand .ffb,html[data-theme=dark] .fbrand .fshare{filter:invert(1) hue-rotate(180deg)}.fcols nav{display:grid;gap:0;margin:0}.fcols nav a{display:flex;align-items:center;min-block-size:44px;color:var(--ink);text-decoration:none;font-weight:600}.fcols nav a:hover{text-decoration:underline;text-underline-offset:4px}.fsup{margin:14px 0 0;color:var(--ink)}.fsup a{font-weight:700;color:#0A6FB3}.fmail{display:flex;flex-wrap:wrap;gap:4px 18px;margin:.4rem 0 0;font-size:.9rem}.fmail a{display:inline-flex;align-items:center;min-block-size:32px;color:inherit;text-decoration:underline;text-underline-offset:3px;word-break:break-all}.fcredit{margin:14px 0 0;font-size:.8rem;line-height:1.6}@media (max-width:700px){.fcols{grid-template-columns:1fr}.fcols nav{display:flex;flex-wrap:wrap;gap:0 18px}}
.fmap{margin-block-start:.6rem}.fmap summary{cursor:pointer;min-block-size:2.75rem;display:flex;align-items:center;font-weight:600;color:var(--ink2)}.fmap nav{display:flex;flex-wrap:wrap;gap:0 1rem}
footer{border-block-start:1px solid var(--line);color:var(--muted);font-size:.88rem}
footer .in{max-width:40rem;margin-inline:auto;padding:1.25rem 1rem 2.5rem}
footer p{margin:0 0 .4rem}
footer .sig{font-family:var(--f-disp);font-weight:900;font-size:1.15rem;color:var(--ink)}
footer .sig span{font-family:var(--f-ui);font-weight:400;font-size:.88rem;color:var(--muted)}
footer nav{display:flex;flex-wrap:wrap;margin-inline:-.5rem}
footer nav a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.5rem;color:var(--ink2)}
@media (max-width:28rem){.top .in{padding-inline:.75rem;gap:.25rem}.logo svg{height:1.625rem}.top nav{margin-inline-end:-.25rem}.top nav a{padding-inline:.4rem;font-size:.9rem}}
@media (max-width:26rem){main{padding-inline:.75rem}}
@media (max-width:23.9rem){.logo svg{height:1.45rem}.top nav{margin-inline-end:0}.top nav a{padding-inline:.28rem;font-size:.86rem}}
@media (max-width:21.5rem){.top .in{padding-inline:.6rem}.logo svg{height:1.3rem}.top nav a{padding-inline:.2rem;font-size:.8rem}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
@media print{.top,.bar,.pager,.together,.applink,.related,footer nav,.skip{display:none}.text{border:0;padding:0;box-shadow:none}}
"""

# class token that triggers the block -> css
CSS_BLOCKS = [
("stkgrid", """
.stkgrid{list-style:none;padding:0;margin:1rem 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr));gap:.75rem}
.stkgrid li{background:#F2F8FD;border:1px solid #DCEAF6;border-radius:1.1rem;padding:.6rem .6rem .7rem;display:flex;flex-direction:column;align-items:center;gap:.5rem}
.stkgrid img{width:100%;max-width:9rem;height:auto;aspect-ratio:1}
.stkgrid .sb{display:flex;gap:.4rem;width:100%}
.stkgrid .sb a,.stkgrid .sb button{flex:1;display:inline-flex;align-items:center;justify-content:center;gap:.3rem;min-block-size:2.5rem;border-radius:.75rem;font:inherit;font-weight:700;font-size:.92rem;cursor:pointer;text-decoration:none}
.stkgrid .sb button{border:0;background:linear-gradient(135deg,#1AA45B,#0E7F42);color:#fff}
.stkgrid .sb a{border:1px solid #C9DCEC;background:#fff;color:#0B2E4F}
.stkall{display:flex;flex-wrap:wrap;gap:.6rem;margin:.4rem 0 1.2rem}
.stkall a{display:inline-flex;align-items:center;gap:.45rem;min-block-size:3rem;padding:0 1.2rem;border-radius:999px;background:#0A5CA8;color:#fff;font-weight:700;text-decoration:none}
.stkall a.alt{background:#fff;color:#0A5CA8;border:1px solid #C9DCEC}
.stkcredit{font-size:.92rem;color:#4A6279;margin:.2rem 0 1rem}
html[data-theme=dark] .stkgrid img{filter:invert(1) hue-rotate(180deg)}
"""),
("text", """
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .5rem;margin:0 0 .6rem;min-height:2.75rem}
.tools{display:flex;gap:.375rem}
.tools button{min-width:2.75rem;min-height:2.75rem;padding-inline:.85rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:600 .95rem var(--f-ui);cursor:pointer;border-radius:999px}
.tools button:hover{border-color:var(--stamp)}
.tools button[aria-pressed="true"]{background:var(--grad);border-color:transparent;color:#fff}
.tools button:disabled{color:var(--muted);cursor:default;border-color:var(--line)}
.tools .az{font-weight:700;font-size:1.1rem}
.tools .az.sm{font-size:.9rem}
.nus{display:flex;align-items:center;flex-wrap:wrap;margin-inline-start:auto;font-size:.93rem;color:var(--muted)}
.nus a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.45rem;font-weight:600}
.bar{flex-wrap:nowrap}.nus{flex-wrap:nowrap;white-space:nowrap}
@media (max-width:30rem){.nus span{display:none}}
@media (max-width:30rem){.bar{flex-wrap:wrap}}
.text{background:var(--surface);border:1px solid var(--line);border-radius:1.75rem;box-shadow:var(--sh);padding:1.4rem clamp(1.1rem,4.5vw,2.25rem) 1.6rem;font-family:var(--f-read);font-size:var(--reading);font-weight:400;line-height:1.9;text-align:start;max-width:38rem;margin-inline:auto}
.text p{margin:0 0 .65em}.text p:last-child{margin-block-end:0}
.text sup{color:var(--stamp);font-family:var(--f-ui);font-weight:600;font-size:.58em;margin-inline-end:.4em;vertical-align:.5em;line-height:1}
.text h2{font-family:var(--f-ui);font-weight:700;font-size:1.05em;line-height:1.3;margin:1.5em 0 .5em;padding-block-end:.3em;border-block-end:1px solid var(--line)}
.text h2:first-child{margin-block-start:0}
.text h2 a{color:var(--ink);text-decoration:none;display:inline-block;padding-block:.5rem}
.text h2 a:hover{color:var(--stamp);text-decoration:underline}
.text small{color:var(--ink2);font-size:.8em}
.text big{font-size:1.15em}
"""),
("rgrid", """
.acts{display:flex;flex-wrap:nowrap;align-items:center;gap:.4rem;margin:0 0 .8rem}
.acts a,.acts button{display:inline-flex;align-items:center;gap:.4rem;min-height:2.75rem;padding:.3rem .9rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:600 .93rem var(--f-ui);text-decoration:none;cursor:pointer;border-radius:999px}
.acts a:hover,.acts button:hover{border-color:var(--stamp);color:var(--stamp)}.acts .wa{background:#0B6B38;border-color:#0B6B38;color:#fff}.acts .wa:hover{background:#08542C;border-color:#08542C;color:#fff}
.acts button.ok,.acts button[aria-pressed=true]{background:#E1F2FE;border-color:#9CC9E8;color:#0B3F6E}.acts button[aria-pressed=true] svg{fill:currentColor}
.vcount{font:600 .85rem var(--f-ui);color:var(--muted);margin:-.4rem 0 .8rem}
.acts a,.acts button{white-space:nowrap;justify-content:center}
@media print{.acts{display:none!important}}
/* phones: the buttons always share one row and never wrap */
@media (max-width:30rem){.acts{gap:.3rem}.acts a,.acts button{flex:1 1 auto;min-inline-size:0;padding-inline:.5rem;gap:.3rem;font-size:.9rem}.acts [data-act=print] span{position:absolute;inline-size:1px;block-size:1px;overflow:hidden;clip-path:inset(50%)}.acts [data-act=print]{flex:0 0 2.75rem;padding-inline:0}}
.sidebar{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem;margin:0 0 .6rem}.sidebar .bar{margin:0;min-height:0;flex:0 1 auto}
.sideacts{display:flex;gap:.35rem;margin:0}
.sideacts button,.sideacts a{display:grid;place-items:center;inline-size:2.75rem;block-size:2.75rem;padding:0;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer;border-radius:999px}
.sideacts button:hover,.sideacts a:hover{border-color:var(--stamp);color:var(--stamp)}.sideacts .wa{color:#128C4B;border-color:#BFE8D2;background:#F1FBF5}.sideacts .wa:hover{color:#0B6B38;border-color:#128C4B}
.sideacts button.ok{background:var(--grad);color:#fff;border-color:transparent}
.printhead,.printfoot{display:none}
@media (min-width:64rem){
.rd main{max-width:76rem;padding:0 2.5rem 4.5rem}.rd .top .in,.rd footer .in{max-width:76rem;padding-inline:2.5rem}
.rd .rhead{padding:2.25rem 0 2rem;margin-block-end:2.25rem;background:#F1F8FE;box-shadow:0 0 0 100vmax #F1F8FE;clip-path:inset(0 -100vmax)}
.rd h1{font-size:clamp(3rem,4.6vw,4.4rem);margin:.5rem 0 .4rem}.rd h1 .ctx{font-size:1.1rem}.rd .lead{font-size:1.2rem;max-width:44rem;margin-block-end:0}.rd .meta{font-size:1rem}
.rgrid{display:grid;grid-template-columns:minmax(0,1fr) 21rem;column-gap:3.5rem;align-items:start}
.rmain{grid-column:1;grid-row:1;min-width:0}
.rside{grid-column:2;grid-row:1;position:sticky;inset-block-start:calc(var(--top) + 1.5rem);max-block-size:calc(100vh - var(--top) - 3rem);overflow:auto;padding:1.25rem;border:1px solid var(--line);border-radius:1.75rem;background:var(--surface);box-shadow:var(--sh);scrollbar-width:thin}
.rside>*:last-child{margin-block-end:0}.rside .sidebar{flex-wrap:nowrap;justify-content:space-between;margin-block-end:0}.rside .tools{gap:.3rem}.rside .tools button{padding-inline:.7rem}.rside .svctoc{margin-block-start:0}
.rgrid{grid-template-columns:minmax(0,1fr) 22rem}
.rd .text{max-width:none;margin:0;font-size:calc(var(--reading)*1.14);line-height:2;padding:3rem clamp(2.25rem,4vw,4rem) 3.25rem;border-radius:2.25rem}
.rd .text p{margin-block-end:.8em}.rd .text h2{margin-block-start:1.8em}
}
@media print{@page{margin:16mm 14mm 18mm}
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.rside,.rhead .crumbs,.rhead .lead,footer,.plainx,.svctoc,.top,.skip,.pager,.related,.applink,.rmain h2.sec,.rmain .nusrow,.rmain .note{display:none!important}.rgrid{display:block}
.rd .rhead{background:none;box-shadow:none;clip-path:none;padding:0;margin:0 0 6mm}.rd h1{font-size:26pt;margin:0}
.rd main{display:table!important;inline-size:100%;max-width:none;padding:0}
.printhead{display:table-header-group!important}
.printhead .ph{display:flex;align-items:center;justify-content:space-between;gap:8mm;padding-block-end:3mm;margin-block-end:6mm;border-block-end:1.5pt solid #0B79C0;color:#0B2E4F;font:600 10pt var(--f-ui)}
.printhead svg{block-size:8mm;inline-size:auto}
.printfoot{display:block!important;margin:8mm 0 0;padding-block-start:3mm;border-block-start:.75pt solid #B3E0FA;color:#27506F;font:600 9pt var(--f-ui);text-align:center}
.rd .text{font-size:14pt;line-height:1.85;max-width:none;border:0;box-shadow:none;padding:0;border-radius:0}.text p{orphans:3;widows:3}.text h2{break-after:avoid}
}
"""),
("pager", """
.pager{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:1.5rem 0 0}
.pager a{display:block;padding:.75rem 1.2rem;border:1px solid var(--line);background:var(--surface);border-radius:var(--r);text-decoration:none;color:var(--ink);font-weight:700;font-size:1.05rem;line-height:1.35;min-height:2.75rem}
.pager a:hover{border-color:var(--stamp);color:var(--ink)}
.pager small{display:block;color:var(--muted);font-weight:400;font-size:.8rem}
.pager .next{text-align:end;background:var(--grad);border-color:transparent;color:#fff;box-shadow:var(--sh)}
.pager .next:hover{color:#fff;filter:brightness(1.08)}
.pager .next small{color:#B3E0FA}
"""),
("together", """
.together{margin:2rem 0 0;padding:1.3rem 1.4rem 1.5rem;background:var(--sunk);border-radius:1.75rem}
.together h2{font-family:var(--f-disp);font-weight:900;font-size:1.7rem;margin:0 0 .15rem}
.together p{margin:0 0 .9rem;color:var(--ink2)}
.together a:not(.btn){display:inline-flex;align-items:center;min-height:2.75rem;margin-inline-start:1rem;font-weight:600}
"""),
("grp", """
h2.big{border-block-start:1px solid var(--line);padding-block-start:1.4rem;margin-block-start:3rem}
h2.big a{color:inherit;text-decoration:none;display:inline-block;padding-block:.3rem}
h3.grp{font-family:var(--f-ui);font-weight:700;font-size:1rem;color:var(--ink2);margin:1.6rem 0 .4rem}
"""),
("grid", """
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(3.4rem,1fr));gap:.4rem}
.grid a{display:grid;place-items:center;min-height:3rem;border:1px solid var(--line);background:var(--surface);border-radius:1rem;text-decoration:none;color:var(--ink);font-weight:700;font-size:1.15rem}
.grid a:hover{border-color:var(--stamp);color:var(--stamp)}
"""),
("list", """
.list{columns:2 16rem;column-gap:2rem;padding:.2rem 1.2rem;margin:0;list-style:none;background:var(--surface);border:1px solid var(--line);border-radius:var(--r)}
.list li{break-inside:avoid;border-block-end:1px solid var(--line)}
.list a{display:block;padding-block:.65rem;text-decoration:none;color:var(--ink);font-weight:600}
.list a:hover{color:var(--stamp)}
.list small{display:block;color:var(--muted);font-size:.84rem;font-weight:400}
"""),
("want", """
.want{list-style:none;margin:0;padding:.2rem 1.2rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh)}
.want li{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0 1rem;border-block-end:1px solid var(--line);padding-block:.25rem}
.want li:last-child{border-block-end:0}
.want b{font-weight:700;font-size:1.12rem}
.want span{display:flex;flex-wrap:wrap;margin-inline:-.5rem}
.want a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.5rem;font-size:.95rem;font-weight:600}
@media (max-width:34rem){.want b{flex-basis:100%;padding-block-start:.5rem}}
"""),
("cards", """
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(14rem,1fr));gap:.7rem;list-style:none;margin:0;padding:0}
.cards a,.cards .card{display:block;height:100%;padding:1rem 1.2rem 1.1rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh);text-decoration:none;color:var(--ink)}
.cards a:hover{border-color:var(--stamp)}
.cards b{display:block;font-family:var(--f-disp);font-weight:900;font-size:1.3rem;line-height:1.25}
.cards small{display:block;color:var(--muted);font-size:.9rem;line-height:1.45;margin-block-start:.2rem}
.cards .card p{margin:.3rem 0 .9rem;color:var(--ink2);font-size:.97rem}
.cards .card .btn{min-height:2.75rem;padding-inline:1.2rem;font-size:.95rem}
"""),
("toc", """
.toc{list-style:none;margin:0;padding:.2rem 1.2rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);counter-reset:none}
.toc li{border-block-end:1px solid var(--line)}
.toc li:last-child{border-block-end:0}
.toc a{display:flex;gap:.8rem;align-items:baseline;padding-block:.7rem;text-decoration:none;color:var(--ink);min-height:2.75rem}
.toc i{font-style:normal;flex:none;min-width:1.6rem;color:var(--stamp);font-weight:700;font-size:.9rem}
.toc b{display:block;font-weight:700;font-size:1.08rem;line-height:1.35}
.toc small{display:block;color:var(--muted);font-family:var(--f-read);font-size:.92rem;line-height:1.5}
.toc a:hover b{color:var(--stamp)}
"""),
("sched", """
.sched{list-style:none;margin:0;padding:0;display:grid;gap:.55rem}
.sched li{padding:.8rem 1.1rem .9rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r)}
.sched li.now{border-color:var(--stamp);box-shadow:var(--sh)}
.sched b{font-weight:700;font-size:1.08rem}
.sched b a{color:var(--ink);display:inline-block;padding-block:.6rem}
.sched .rng{color:var(--muted);margin-inline-start:.5rem}
.sched .tag{display:inline-block;margin-inline-start:.5rem;padding:.05rem .6rem;border-radius:999px;background:var(--grad);color:#fff;font-size:.8rem;font-weight:700}
.sched .chs{display:flex;flex-wrap:wrap;gap:.3rem;margin-block-start:.5rem}
.sched .chs a{display:inline-grid;place-items:center;min-width:2.75rem;min-height:2.75rem;padding-inline:.5rem;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--ink);font-weight:700}
.sched .chs a:hover{border-color:var(--stamp);color:var(--stamp)}
.sched .more{display:flex;flex-wrap:wrap;gap:0 1rem}
.sched .more a{display:inline-flex;align-items:center;min-height:2.75rem;font-weight:600}
"""),
("steps", """
.steps{list-style:none;margin:1.5rem 0;padding:0;display:grid;gap:.7rem;counter-reset:st}
.steps li{counter-increment:st;display:grid;grid-template-columns:auto 1fr;gap:.2rem 1rem;align-items:start;padding:1rem 1.2rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh)}
.steps li::before{content:counter(st);grid-row:span 2;display:grid;place-items:center;inline-size:2.5rem;block-size:2.5rem;border-radius:50%;background:var(--grad);color:#fff;font-weight:700;font-size:1.15rem}
.steps b{font-family:var(--f-disp);font-weight:900;font-size:1.3rem;line-height:1.3}
.steps span{color:var(--ink2);grid-column:2}
"""),
("yhero", """
.yhero{margin:1rem 0 1.4rem;padding:1.7rem 1.4rem 1.5rem;background:var(--grad);color:#fff;border-radius:1.75rem;box-shadow:var(--sh);text-align:center}
.yhero p{margin:0 0 1.1rem;font-family:var(--f-disp);font-weight:900;font-size:clamp(1.9rem,7.5vw,2.7rem);line-height:1.15}
.yhero .btn{background:#fff;color:#0B3F6E;box-shadow:0 10px 24px -12px rgba(2,30,66,.6);min-height:56px;padding-inline:1.8rem;font-size:1.1rem}
.yhero .btn:hover{filter:none;color:#0A6CA8}
.yhero small{display:block;margin-block-start:.9rem;color:#E4F3FE;font-size:.95rem}
html[data-theme=dark] .yhero{filter:invert(1) hue-rotate(180deg)}
.ynum{display:flex;justify-content:center;gap:.6rem;margin:1.2rem 0 0;padding:0;list-style:none}
.ynum li{flex:1;max-inline-size:11rem;background:rgba(255,255,255,.16);border-radius:1rem;padding:.6rem .4rem;font-size:.88rem;color:#E4F3FE;line-height:1.3}
.ynum b{display:block;font-family:var(--f-disp);font-weight:900;font-size:1.6rem;color:#fff;font-variant-numeric:tabular-nums}
"""),
("st3", """
.st3{list-style:none;margin:.8rem 0 1.4rem;padding:.3rem 1rem;counter-reset:st;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh)}
.st3 li{counter-increment:st;display:grid;grid-template-columns:auto 1fr;gap:0 .8rem;align-items:center;padding:.75rem 0}
.st3 li+li{border-block-start:1px solid var(--line)}
.st3 li::before{content:counter(st);grid-row:span 2;display:grid;place-items:center;inline-size:2.1rem;block-size:2.1rem;border-radius:50%;background:var(--grad);color:#fff;font-weight:700;font-size:1.05rem}
.st3 b{font-family:var(--f-disp);font-weight:900;font-size:1.12rem;line-height:1.25}
.st3 span{color:var(--ink2);font-size:.93rem;line-height:1.35}
"""),
("yfig", """
.yfig{margin:.4rem auto 1.4rem;max-inline-size:360px}.yfig img{display:block;inline-size:100%;block-size:auto;border-radius:24px;box-shadow:var(--sh)}
html[data-theme=dark] .yfig img{filter:invert(1) hue-rotate(180deg)}
"""),
("qa", """
.qa{border-block-end:1px solid var(--line)}.qa:first-of-type{border-block-start:1px solid var(--line)}
.qa summary{display:flex;align-items:center;justify-content:space-between;gap:.8rem;min-block-size:52px;padding:.5rem .2rem;cursor:pointer;list-style:none;font:700 1.02rem var(--f-ui);color:var(--ink)}
.qa summary::-webkit-details-marker{display:none}.qa summary::after{content:"+";flex:none;font:400 1.5rem/1 var(--f-ui);color:var(--stamp)}.qa[open] summary::after{content:"−"}
.qa summary:focus-visible{outline:2px solid var(--stamp);outline-offset:2px;border-radius:8px}
.qa p{margin:0 .2rem 1rem;color:var(--ink2)}
"""),
("yrec", """
.yrec{list-style:none;margin:.8rem 0 .6rem;padding:0;display:grid;gap:.6rem}
@media (min-width:640px){.yrec{grid-template-columns:1fr 1fr}}
.yrec a{display:block;padding:.9rem 1.1rem 1rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh);color:var(--ink);text-decoration:none}
.yrec a:hover{border-color:var(--stamp)}
.yrec small{display:block;color:var(--muted);font-size:.85rem;font-weight:600}
.yrec b{display:block;font-family:var(--f-disp);font-weight:700;font-size:1.08rem;line-height:1.3;margin:.1rem 0 .6rem;overflow-wrap:anywhere}
.yrec i{display:block;block-size:.45rem;border-radius:99px;background:var(--sunk);overflow:hidden}
.yrec i u{display:block;block-size:100%;border-radius:99px;background:var(--grad)}
.yrec em{display:flex;justify-content:space-between;gap:.5rem;margin-block-start:.45rem;font-style:normal;font-size:.88rem;color:var(--ink2)}
.yrec em span{color:var(--stamp);font-weight:700}
.ypin{grid-template-columns:1fr!important;margin-block:.6rem 1.2rem}.ypin a{border-block-start:4px solid #FFD35A}.ypin small{color:#7A5200}
.ysrch{display:block;margin:.6rem 0 .2rem}.ysrch input{inline-size:100%;min-block-size:48px;padding:0 1.1rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:600 1rem var(--f-ui)}
.ysrch input:focus-visible{outline:2px solid var(--stamp);outline-offset:2px}
"""),
("hero", """
.hero{margin:1rem 0 1.5rem;padding:1.6rem 1.5rem 1.7rem;background:linear-gradient(160deg,#FFFFFF,#F3FAFF 55%,#E4F3FE);border:1px solid var(--line);color:var(--ink);border-radius:1.75rem;box-shadow:var(--sh)}
.hero p{margin:0 0 1.1rem;font-family:var(--f-disp);font-weight:900;font-size:clamp(1.7rem,6vw,2.4rem);line-height:1.2}
.hero .btn{color:#fff;box-shadow:none}
.hero .btn:hover{color:var(--stamp);filter:none}
.hero small{display:block;margin-block-start:.8rem;color:var(--ink2);font-size:.92rem}
"""),
("prose", """
.prose{max-width:36rem}
.prose p{margin:0 0 .9rem;color:var(--ink2)}
.prose ul{margin:0 0 .9rem;padding-inline-start:1.2rem;color:var(--ink2)}.prose li{margin:0 0 .35rem}
.text .perek{font:700 .85rem var(--f-ui);color:var(--muted);margin:1.1rem 0 .3rem}.text h2 small{font:600 .85rem var(--f-ui);color:var(--muted);margin-inline-start:.5rem}
.prose h2{font-family:var(--f-disp);font-weight:900;font-size:1.5rem;line-height:1.25;margin:1.6rem 0 .5rem;color:var(--ink)}
.prose table{border-collapse:collapse;margin:0 0 1rem;font-size:.97rem}
.prose td,.prose th{padding:.35rem .9rem .35rem 0;text-align:start;border-block-end:1px solid var(--line)}
"""),
("zt", """
.zt{inline-size:100%;border-collapse:collapse;margin:.6rem 0 1rem;font-variant-numeric:tabular-nums}
.zt th,.zt td{padding:.7rem .4rem;text-align:start;border-block-end:1px solid var(--line);white-space:nowrap}.zt th{font-size:.85rem;color:var(--muted);font-weight:600}
.zt td b{font-size:1.1rem}.zt tr.now td{background:var(--sunk);font-weight:700}.zt tr.past{display:none}
@media (max-width:380px){.zt th,.zt td{padding:.6rem .25rem}.zt td:first-child{white-space:normal}.zt td b{font-size:1rem}}
.znow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem;margin:1rem 0}.znow div{padding:1rem;border-radius:1.25rem;background:var(--sunk);display:grid;gap:.2rem}
.znow span{font-size:.85rem;color:var(--muted);font-weight:600}.znow b{font-family:var(--f-disp);font-weight:900;font-size:clamp(1.6rem,7vw,2.3rem);line-height:1;font-variant-numeric:tabular-nums}
.znow small{color:var(--muted)}
.zday td small{color:var(--muted);white-space:normal}.zday td:first-child{white-space:normal;font-weight:600}.zt.zday tr.past{display:table-row}
.zscroll{overflow-x:auto;margin-inline:-.25rem;padding-inline:.25rem}.zweek td,.zweek th{padding-inline:.35rem;font-size:.95rem}@media (max-width:520px){.zweek td,.zweek th{padding-inline:.2rem;font-size:.86rem}.zweek td:first-child{white-space:normal;min-inline-size:4.4rem;line-height:1.3}.zweek td b{font-size:.92rem}}@media (max-width:350px){.zweek td,.zweek th{padding-inline:.1rem;font-size:.78rem}.zweek td:first-child{min-inline-size:3.5rem}.zweek td b{font-size:.82rem}}
"""),
("plainx", """
.plainx{margin:.4rem 0 1rem;padding:1rem 1.15rem;border-radius:1.25rem;background:var(--sunk)}
.plainx b{display:block;font-size:.9rem;color:var(--stamp);margin-block-end:.3rem}.plainx p{margin:0;line-height:1.75}
"""),
("nform", """
.nform{display:grid;gap:.7rem;margin:1rem 0;padding:1.2rem;border:1px solid var(--line);border-radius:1.5rem;background:linear-gradient(150deg,#fff,#EEF8FF 60%,#DDF0FD)}
.nform label{font-weight:700}.nform input[name=n]{min-height:3.2rem;padding:.6rem 1rem;border-radius:999px;border:1px solid var(--line);background:#fff;font:inherit;color:var(--ink)}
.nform fieldset{border:0;margin:0;padding:0;display:grid;gap:.4rem}.nform legend{font-weight:700;padding:0;margin-block-end:.3rem}.nform fieldset label{font-weight:400;display:flex;align-items:center;gap:.5rem;min-height:2.75rem}
.nlet{display:flex;flex-wrap:wrap;gap:.35rem;margin:.6rem 0}.nlet span{display:grid;place-items:center;inline-size:2.5rem;block-size:2.75rem;border-radius:.75rem;background:var(--grad);color:#fff;font-weight:700;font-size:1.25rem}
.nact{display:flex;flex-wrap:wrap;gap:.5rem;margin:.8rem 0}.btn2{min-height:3rem;padding:.4rem 1.2rem;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:700;cursor:pointer}
@media print{.top,.crumbs,.nform,.nact,.prose,.pager,.related,.applink,footer,.note,.lead{display:none!important}}
"""),
("fbl", """
.fbl{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:4px 12px;margin:22px auto 0;padding:4px 6px 4px 14px;padding-inline:14px 6px;max-inline-size:34rem;border-radius:999px;background:#F1F8FE;border:1px solid var(--line);color:var(--ink2);font-size:.92rem;line-height:1.4;text-align:center}.fbl[hidden]{display:none}.fbl a{display:inline-flex;align-items:center;gap:6px;min-block-size:44px;color:#1257BD;font-weight:700;text-decoration:underline;text-underline-offset:3px}.fbl button{display:grid;place-items:center;inline-size:44px;block-size:44px;border:0;background:none;color:inherit;cursor:pointer;border-radius:50%;opacity:.75}@media(max-width:560px){.fbl{border-radius:20px;padding-block:10px 2px}.fbl span{flex:1 1 100%}}@media print{.fbl{display:none}}html[data-theme=dark] .fbl a{filter:invert(1) hue-rotate(180deg)}
"""),
("kala", """
.kala{position:relative;margin:0 0 1.1rem;padding:1.3rem 1.2rem 1.25rem;border-radius:22px;border:1px solid #F5C6D6;background:linear-gradient(150deg,#FFF6F9 0%,#FFE9F0 60%,#FFDDE8 100%);color:#7A1238;text-align:center;font-family:var(--f-ui);overflow:hidden}
.kala::before,.kala::after{content:"";position:absolute;inline-size:9rem;block-size:9rem;border-radius:50%;border:1px solid rgba(214,84,128,.22);pointer-events:none}
.kala::before{inset-block-start:-4.5rem;inset-inline-start:-3.5rem}.kala::after{inset-block-end:-5rem;inset-inline-end:-3rem}
.kala-ic{color:#C2255C;margin:0 auto .35rem;display:block}
.kala h2{margin:0 0 .35rem;font:900 1.3rem/1.25 var(--f-disp);color:#7A1238}
.kala p{margin:0 auto .95rem;max-inline-size:26rem;font-size:.98rem;line-height:1.6;color:#8A2B4C}
.kala-btn{position:relative;display:inline-flex;align-items:center;justify-content:center;gap:.5rem;min-height:3rem;padding:.45rem 1.5rem;border:0;border-radius:999px;background:#B81F55;color:#fff;font:700 1rem var(--f-ui);cursor:pointer;box-shadow:0 .7rem 1.4rem -.7rem rgba(184,31,85,.8)}
.kala-btn:hover{background:#A31A4B}.kala-btn svg{inline-size:1.2rem;block-size:1.2rem}
@media (prefers-reduced-motion:no-preference){.kala-btn{transition:transform .15s ease,background .15s ease}.kala-btn:active{transform:scale(.97)}}
"""),
("zshare", """
.zshare{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:0 0 1rem}
.zshare .zwa{gap:.5rem;background:#0E7A41;box-shadow:0 .5rem 1.2rem -.6rem rgba(14,122,65,.7)}
.zshare .zim{display:inline-flex;align-items:center;gap:.45rem;min-height:3rem;padding:.4rem 1.2rem;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:700 1rem var(--f-ui);cursor:pointer}
.zshare .zim:hover{border-color:var(--stamp)}.zshare .zim:disabled{opacity:.6}.zmsg{flex:1 1 100%;font-size:.9rem;color:var(--ink2);min-height:0}.zmsg:empty{display:none}
@media print{.zshare{display:none}}
html[data-theme=dark] .zshare .zwa{filter:invert(1) hue-rotate(180deg)}
"""),
("tautbox", """
.tautbox{margin:.8rem 0 0}
.cgrid{display:grid;gap:1rem;margin-block:2rem 1rem;align-items:start}@media(min-width:54rem){.cgrid{grid-template-columns:1fr 1fr;gap:1.25rem}}
.ccard{padding:clamp(1.1rem,3.5vw,1.6rem);border-radius:1.4rem;border:1px solid var(--line);background:linear-gradient(160deg,#fff,#F3FAFF);scroll-margin-top:.75rem;min-inline-size:0}
.ccard h2{font-family:var(--f-disp);font-weight:900;font-size:1.4rem;line-height:1.25;margin:0 0 .4rem;color:var(--ink)}.ccard>p{margin:0;color:var(--ink2);line-height:1.6}
.cform .nact{margin:.5rem 0 0}.cform .btn{inline-size:100%;min-block-size:3rem;border:0;justify-content:center}.cform{display:grid;gap:.5rem}.cform label{font-weight:700;margin-block-start:.3rem}
.cform textarea,.cform input[type=email]{inline-size:100%;padding:.8rem 1rem;border-radius:1rem;border:1px solid var(--line);background:#fff;font:inherit;color:var(--ink);line-height:1.6}
.cform input[type=email]{min-block-size:3rem;text-align:left}.cform .chp{position:absolute;inset-inline-start:-9999px;inline-size:1px;block-size:1px;opacity:0}
.cwhere{margin:0;padding:.7rem 1rem;border-radius:1rem;background:#EEF7FE;color:var(--ink);line-height:1.5;overflow-wrap:anywhere}.cwhere span{font-size:.85rem;color:var(--muted)}
.cmsg{margin:0;min-block-size:1.5rem;font-weight:700}.cmsg.good{color:#0A6FB3}.cmsg.bad{color:#B3261E}
.nact{display:flex;flex-wrap:wrap;gap:.5rem;margin:.4rem 0}.btn2{min-height:3rem;padding:.4rem 1.2rem;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:700;cursor:pointer}
"""),
("tklong", """
.tklong{margin:1rem 0;border-block:1px solid var(--line)}.tklong summary{cursor:pointer;min-height:3rem;display:flex;align-items:center;font-family:var(--f-ui);font-weight:700;font-size:1rem}
"""),
("svctoc", """
.svctoc{margin:.6rem 0 1rem;border:1px solid var(--line);border-radius:1.25rem;background:#fff}
.svctoc summary{cursor:pointer;list-style:none;min-height:3.2rem;display:flex;align-items:center;padding:.5rem 1.1rem;font-weight:700}
.svctoc summary::-webkit-details-marker{display:none}.svctoc summary::after{content:"";margin-inline-start:auto;inline-size:.55rem;block-size:.55rem;border-inline-end:2px solid var(--ink);border-block-end:2px solid var(--ink);transform:rotate(45deg)}
.svctoc[open] summary::after{transform:rotate(-135deg)}.svctoc .grp{margin:.4rem 1.1rem 0}.svctoc .toc{margin:0;padding:0 .6rem .8rem}
"""),
("pask", """
.pask{background:#FFF3C4;color:inherit;font-family:var(--f-ui,inherit);font-size:.8em;font-weight:700;padding:.1em .4em;border-radius:6px}
"""),
("pweek", """
.pweek{margin:.2rem 0 1rem;min-block-size:5.9rem;padding:.9rem 1.1rem;border-radius:18px;background:var(--sunk);font-size:1.08rem;box-sizing:border-box}.pweek a{font-weight:700}.pweek small{display:block;color:var(--muted);font-size:.86rem;margin-top:.15rem}.pweek:empty{background:none}
"""),
("note", """
.note{margin:1rem 0;color:var(--muted);font-size:.93rem;max-width:36rem}.tdn{margin:1rem 0 1.25rem;padding:.9rem 1rem;border:1px solid var(--line);border-inline-start:3px solid var(--accent);border-radius:12px;background:var(--accent-soft,#f3f6ff);font-family:var(--f-ui,inherit);font-size:.95rem;line-height:1.65;color:var(--ink);text-align:start}.tdn h2{margin:0 0 .4rem;font-size:1.05rem}.tdn ul{margin:0;padding-inline-start:1.1rem}.tdn li{margin:.3rem 0}.tdn p{margin:.6rem 0 0}.tdn .tds{font-size:.85rem;color:var(--muted)}.tdn a{color:inherit;text-decoration:underline;text-underline-offset:.15em}
"""),
]

def css_for(body):
    used = set()
    for m in re.finditer(r'class="([^"]*)"', body):
        used.update(m.group(1).split())
    return (CSS_BASE + "".join(css for key, css in CSS_BLOCKS if key in used)).replace("\n", "")

# Runs in <head>: applies the reader's saved text size before first paint.
# Same key and format as the app: localStorage "fs" = JSON number in rem.
JS_HEAD = ("(function(){try{var v=JSON.parse(localStorage.getItem('fs'));"
           "if(typeof v==='number'&&v>=.95&&v<=2.6)document.documentElement.style.setProperty('--reading',v+'rem')}catch(e){}})()")

# Runs right after the text: size and nikud tools. Keys shared with the app:
# "fs" = JSON number (rem, .95 to 2.6, step .12, default 1.32); "nikud" = JSON true/false.
FBL = '<p class="fbl" id="fbl" hidden><span>פסוק יומי וקריאות תהילים משותפות, גם בפייסבוק.</span><a href="https://www.facebook.com/tfilahcom" target="_blank" rel="noopener" data-fbgo><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/></svg>עקבו אחרינו</a><button type="button" data-fbx aria-label="סגירת ההזמנה לפייסבוק"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg></button></p>'
FBL_JS = "(function(){" + "var FBE=Date.UTC(2026,10,25,21,59),fbS=function(){try{return JSON.parse(localStorage.getItem('fbl')||'{}')||{}}catch(e){return{}}},fbP=function(o){try{localStorage.setItem('fbl',JSON.stringify(o))}catch(e){}},fbD=function(){return new Date().toISOString().slice(0,10)},fbOk=function(){var s=fbS();return Date.now()<FBE&&!s.off&&s.day!==fbD()&&!/^\\/(shem|leiluy-nishmat|n|y|kelim\\/shem|tehillim-yachad)\\//.test(location.pathname)};document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('[data-fbx],[data-fbgo]');if(!t)return;fbP({off:1});var b=t.closest('.fbl');if(b&&t.hasAttribute('data-fbx'))b.remove()});addEventListener('scroll',function(){var b=document.querySelector('.fbl:not([hidden])');if(!b)return;var r=b.getBoundingClientRect();if(r.top<innerHeight&&r.bottom>0){var s=fbS();if(s.day!==fbD()){s.day=fbD();fbP(s)}}},{passive:true});" + "var b=document.getElementById('fbl');if(b&&fbOk())b.hidden=false})();"
JS_TOOLS = r"""(function(){
var art=document.getElementById('text'),bar=document.getElementById('tools');if(!art||!bar)return;
var NIK=/[֑-ֽֿ-ׇ]/g,orig=null,MIN=.95,MAX=2.6,STEP=.12;
function get(k,d){try{var v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}}
function set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
var fs=get('fs',1.32),nik=get('nikud',true);
if(typeof fs!=='number'||!(fs>=MIN&&fs<=MAX))fs=1.32;
nik=nik!==false;
var fm=document.getElementById('fm'),fp=document.getElementById('fp'),nk=document.getElementById('nk');
function size(){document.documentElement.style.setProperty('--reading',fs+'rem');fm.disabled=fs<=MIN;fp.disabled=fs>=MAX}
var ish=get('isha',false)===true,ib=document.getElementById('ish'),IM={'מודה':'מודה','גויה':'גוי','שפחה':'עבד'};
function pl(h){return h.replace(/<[^>]+>/g,'').replace(NIK,'').replace(/\s+/g,' ').trim()}
function fem(html){return html.replace(/<p>([\s\S]*?)<\/p>/g,function(all,x){var s=pl(x);
if(/שלא עשני אשה\s*[:׃.]?$/.test(s))return'';
if(/^\(?\s*נשים (אומרות|מברכות)/.test(s)){var h=x.replace(/^\(\s*([\s\S]*?)\)\s*$/,'$1').replace(/<small>\s*נשים (?:אומרות|מברכות):?\s*<\/small>\s*/,'').replace(/^\s*נשים (?:אומרות|מברכות)\s*[-:]\s*/,'');return pl(h)?'<p>'+h+'</p>':''}
var m=x.match(/\s*<small>(?:האשה|האישה) אומרת:\s*(?:<b>)?([^<]+?)(?:<\/b>)?\s*<\/small>/);
if(m){var f=m[1].trim(),ml=IM[f.replace(NIK,'')];if(ml){var re=new RegExp('(^|[\\s>])'+ml.split('').map(function(c){return c+'[\\u0591-\\u05C7]*'}).join('')+'(?=[\\s:׃<.,]|$)'),h2=x.replace(m[0],'');if(re.test(h2))return'<p>'+h2.replace(re,'$1'+f)+'</p>'}}
return'<p>'+x.replace(/^<b>מוֹדֶה אֲנִי<\/b>/,'<b>מודָה אֲנִי</b>')+'</p>'})}
function hasF(h){return /האשה אומרת|האישה אומרת|נשים אומרות|נשים מברכות|שלא עשני אשה/.test(pl(h))||/<p><b>מוֹדֶה אֲנִי<\/b>/.test(h)}
function nikud(){if(orig==null)orig=art.innerHTML;var h=ish&&hasF(orig)?fem(orig):orig;art.innerHTML=nik?h:h.replace(NIK,'');nk.setAttribute('aria-pressed',nik?'true':'false');if(ib)ib.setAttribute('aria-pressed',ish?'true':'false')}
fm.onclick=function(){fs=Math.max(MIN,+(fs-STEP).toFixed(2));set('fs',fs);size()};
fp.onclick=function(){fs=Math.min(MAX,+(fs+STEP).toFixed(2));set('fs',fs);size()};
nk.onclick=function(){nik=!nik;set('nikud',nik);nikud()};
if(ib&&hasF(art.innerHTML)){ib.hidden=false;ib.onclick=function(){ish=!ish;set('isha',ish);nikud()}}
size();if(!nik||(ish&&hasF(art.innerHTML)))nikud();else nk.setAttribute('aria-pressed','true');
bar.hidden=false;
})()"""

# Progressive enhancement on /tehillim/yomi/: marks today's portions. Same calculation as the app.
JS_TODAY = ("(function(){try{var d=new Date(),h=+new Intl.DateTimeFormat('en-u-ca-hebrew',{day:'numeric'}).format(d);"
            "function m(id){var e=document.getElementById(id);if(!e)return;e.className+=' now';var s=document.createElement('span');"
            "s.className='tag';s.textContent='היום';e.querySelector('b').after(s)}"
            "if(h>=1&&h<=30)m('d'+h);m('w'+d.getDay())}catch(e){}})()")

TOOLS_HTML = ('<div class="tools" id="tools" role="group" aria-label="כלי קריאה" hidden>'
              '<button type="button" id="fm" class="az sm" aria-label="א− הקטנת הטקסט">א−</button>'
              '<button type="button" id="fp" class="az" aria-label="א+ הגדלת הטקסט">א+</button>'
              '<button type="button" id="nk" aria-pressed="true">ניקוד</button><button type="button" id="ish" aria-pressed="false" hidden>נוסח לאישה</button></div>')

NAV = ('<nav aria-label="ניווט ראשי"><a href="/siddur/">סידור</a><a href="/tehillim/">תהילים</a>'
       '<a href="/sefer/">ספרייה</a><a href="/tehillim-yachad/">תהילים יחד</a></nav>')
DONATE_ON = bool(re.search(r'donateUrl:\s*"[^"]+"', open(os.path.join(ROOT, "config.js"), encoding="utf-8").read()))
CONTACT = (re.search(r'contactEmail:\s*"([^"]*)"', open(os.path.join(ROOT, "config.js"), encoding="utf-8").read()) or [None, ""])[1]
TD_BOX = '<aside class="tdn" aria-label="מתי אומרים את תפילת הדרך בברכה"><h2>מתי אומרים אותה בברכה?</h2><ul><li><b>לפי זמן הנסיעה:</b> בסידור עדות המזרח שבאתר נכתב שמי ששוהה בנסיעה מחוץ לעיר שעה וחמישית (72 דקות) אומר אותה בשם ומלכות, ובנסיעה קצרה מזו אינו מברך בשם ומלכות.</li><li><b>לפי המרחק:</b> בשולחן ערוך נפסק שאומרים אותה כשהדרך היא פרסה לפחות, ובפחות מפרסה אין חותמים ב”ברוך”. המשנה ברורה מוסיף שפרסה היא 8,000 אמה, ושגם הנוסע ברכבת מברך כשהוא נוסע פרסה אחת.</li><li><b>מתי בדרך:</b> אחרי שיצאו מהעיר, ולכתחילה בתחילת הדרך.</li></ul><p>כשלא חותמים, אומרים את התפילה עד ”כי אל שומע תפילה ותחנון אתה” בלי הסיום ”ברוך אתה ה׳ שומע תפילה”. יש שתי דרכי מדידה, זמן ומרחק, והאתר אינו מכריע ביניהן. מי שמסופק שואל רב.</p><p class="tds">מקורות: הוראת הסידור בנוסח עדות המזרח · <a href="https://www.sefaria.org.il/Shulchan_Arukh%2C_Orach_Chayim.110.7" target="_blank" rel="noopener">שולחן ערוך אורח חיים קי, ז</a> · <a href="https://www.sefaria.org.il/Mishnah_Berurah.110.30" target="_blank" rel="noopener">משנה ברורה שם, ס״ק כט עד לא</a></p></aside>'
DCLOSE_JS = "document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-dclose]');if(!b)return;var d=b.closest('details');if(!d)return;d.open=false;var s=d.querySelector('summary');if(s){try{s.focus({preventScroll:true})}catch(x){s.focus()}}var r=d.getBoundingClientRect();if(r.top<70||r.top>innerHeight-80)window.scrollTo({top:Math.max(0,(window.scrollY||0)+r.top-90),behavior:'auto'})});"
TOP_JS = "(function(){var b=document.getElementById('totop');if(!b)return;var t=0,rm=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;function off(){b.classList.remove('on');b.tabIndex=-1}addEventListener('scroll',function(){clearTimeout(t);if((window.scrollY||0)<900){off();return}b.classList.add('on');b.tabIndex=0;t=setTimeout(off,2200)},{passive:true});b.addEventListener('click',function(){off();window.scrollTo({top:0,behavior:rm?'auto':'smooth'})})})();"
DARK_JS = "(function(){function on(){return document.documentElement.dataset.theme==='dark'}function paint(){var d=on();document.querySelectorAll('[data-dark]').forEach(function(b){if(b.getAttribute('aria-pressed')!==String(d))b.setAttribute('aria-pressed',d);var s=b.querySelector('span'),w=d?'מצב יום':'מצב לילה';if(s&&s.textContent!==w)s.textContent=w});var m=document.querySelector('meta[name=theme-color]'),k=d?'#000000':'#FFFFFF';if(m&&m.content!==k)m.content=k}document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-dark]');if(!b)return;var d=!on();if(d)document.documentElement.dataset.theme='dark';else delete document.documentElement.dataset.theme;try{localStorage.setItem('dark',JSON.stringify(d))}catch(x){}paint()});paint();new MutationObserver(paint).observe(document.body,{childList:true,subtree:true})})();"
DARK_EARLY = '<script>try{if(JSON.parse(localStorage.getItem("dark")||"false"))document.documentElement.dataset.theme="dark"}catch(e){}</script>'
FOOT_JS = "document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('[data-taut]');if(!a)return;var h=document.querySelector('h1');a.href='/odot/?u='+encodeURIComponent(location.origin+location.pathname)+'&t='+encodeURIComponent(h?h.textContent.replace(/\\\\s+/g,' ').trim():'')+'#taut'});"
FOOT_NAV = ('<details class="fmap"><summary>עוד דפים באתר</summary><nav aria-label="קישורי תחתית"><a href="/siddur/">סידור תפילה</a><a href="/tehillim/">ספר תהילים</a>'
            '<a href="/tehillim/#bakasha">תהילים לפי בקשה</a><a href="/tehillim/yomi/">תהילים יומי</a>'
            '<a href="/tehillim-yachad/">תהילים יחד</a><a href="/sefer/">ספרייה</a><a href="/kelim/">כלים אישיים</a>'
            '<a href="/zmanei-hayom/">זמני היום</a><a href="/zmanei-shabbat/">זמני שבת</a><a href="/chanukah/">חנוכה</a><a href="/tisha-beav/">תשעה באב</a><a href="/kotel/">תפילה בכותל</a><a href="/leiluy-nishmat/">תהילים לעילוי נשמה</a><a href="/segulat-rachel-imenu/">סגולת רחל אמנו</a><a href="/birkat-kala/">ברכת כלה</a><a href="/ma-mevarchim/">מה מברכים על</a><a href="/odot/">אודות ומקורות</a></nav><p class="dclose"><button type="button" data-dclose><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg>סגירה</button></p></details>')
FONT_HEAD = '<link rel="preload" as="font" type="font/woff2" href="/fonts/heebo-hebrew-900.woff2" crossorigin><link rel="preload" as="font" type="font/woff2" href="/fonts/assistant-hebrew-400.woff2" crossorigin><link rel="preload" as="font" type="font/woff2" href="/fonts/heebo-hebrew-400.woff2" crossorigin><link rel="preload" as="font" type="font/woff2" href="/fonts/assistant-hebrew-700.woff2" crossorigin><link rel="preload" as="font" type="font/woff2" href="/fonts/assistant-hebrew-600.woff2" crossorigin><link rel="preload" as="font" type="font/woff2" href="/fonts/heebo-hebrew-700.woff2" crossorigin><style>@font-face{font-family:"Heebo";font-style:normal;font-weight:400;font-display:optional;src:url(/fonts/heebo-hebrew-400.woff2) format("woff2");unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}@font-face{font-family:"Heebo";font-style:normal;font-weight:400;font-display:optional;src:url(/fonts/heebo-latin-400.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}@font-face{font-family:"Heebo";font-style:normal;font-weight:700;font-display:optional;src:url(/fonts/heebo-hebrew-700.woff2) format("woff2");unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}@font-face{font-family:"Heebo";font-style:normal;font-weight:700;font-display:optional;src:url(/fonts/heebo-latin-700.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}@font-face{font-family:"Heebo";font-style:normal;font-weight:900;font-display:optional;src:url(/fonts/heebo-hebrew-900.woff2) format("woff2");unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}@font-face{font-family:"Heebo";font-style:normal;font-weight:900;font-display:optional;src:url(/fonts/heebo-latin-900.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}@font-face{font-family:"Assistant";font-style:normal;font-weight:400;font-display:optional;src:url(/fonts/assistant-hebrew-400.woff2) format("woff2");unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}@font-face{font-family:"Assistant";font-style:normal;font-weight:400;font-display:optional;src:url(/fonts/assistant-latin-400.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}@font-face{font-family:"Assistant";font-style:normal;font-weight:600;font-display:optional;src:url(/fonts/assistant-hebrew-600.woff2) format("woff2");unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}@font-face{font-family:"Assistant";font-style:normal;font-weight:600;font-display:optional;src:url(/fonts/assistant-latin-600.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}@font-face{font-family:"Assistant";font-style:normal;font-weight:700;font-display:optional;src:url(/fonts/assistant-hebrew-700.woff2) format("woff2");unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}@font-face{font-family:"Assistant";font-style:normal;font-weight:700;font-display:optional;src:url(/fonts/assistant-latin-700.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}</style>'

WEBSITE = {"@type": "WebSite", "name": BRAND, "url": SITE + "/"}

# ---------- lastmod without churn ----------
# A page keeps its previous <lastmod> when its title, description and <main> did not change.
# The fingerprint of each page is kept in sitemap.xml itself (an XML comment after the entry),
# so a failed or partial run cannot blur the dates.
OLD = {}   # path -> (lastmod, fingerprint)
_sm = os.path.join(ROOT, "sitemap.xml")
if os.path.exists(_sm):
    for loc, lm, fp in re.findall(r"<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>.*?</url><!--([0-9a-f]+)-->", open(_sm, encoding="utf-8").read()):
        OLD[loc[len(SITE):]] = (lm, fp)

def signature(doc):
    t = re.search(r"<title>.*?</title>", doc, flags=re.S)
    d = re.search(r'<meta name="description"[^>]*>', doc)
    m = re.search(r"<main\b.*?</main>", doc, flags=re.S)
    return hashlib.sha1(((t.group(0) if t else "") + (d.group(0) if d else "") + (m.group(0) if m else "")).encode("utf-8")).hexdigest()[:12]

URLS = []          # (path, priority, lastmod, fingerprint)
TITLES = {}
DESCS = {}

# pages people pass around get a picture of their own (tools/build-og.js draws them)
OG_OWN = (("/perek-shira/", "og-perek"), ("/sefer/perek/", "og-perek"), ("/parasha/", "og-parasha"), ("/kotel/", "og-kotel"), ("/kaddish", "og-kaddish"), ("/chatzi-kaddish", "og-kaddish"),
          ("/nishmat-kol-chai/", "og-nishmat"), ("/mizmor-letoda/", "og-toda"), ("/tefilat-haderech/", "og-derech"), ("/birkat-hamazon/", "og-mazon"),
          ("/kriat-shema-al-hamita/", "og-shema"), ("/modeh-ani/", "og-modeh"), ("/asher-yatzar/", "og-asher"))
BEACON_JS = open(os.path.join(ROOT, "tools", "beacon.js"), encoding="utf-8").read().strip()  # anonymous page views for /admin/
OG_V = "5"  # raise when the pictures are redrawn, so chat apps fetch them again

def og_for(path):
    """the share picture that matches what the link opens"""
    for pre, name in OG_OWN:
        if path.startswith(pre): return name
    if path in _PRAYER_PATHS: return "og-siddur"
    for pre, name in (("/kelim/shem/", "og-shem"), ("/kelim/", "og-kelim"), ("/tehillim-yachad/", "og-yachad"), ("/tehillim/", "og-tehillim"),
                      ("/zmanei-shabbat/", "og-shabbat"), ("/zmanei-hayom/", "og-zmanim"), ("/chanukah/", "og-chanukah"), ("/siddur/", "og-siddur")):
        if path.startswith(pre): return name
    return "og"


_PRAYER_PATHS = set()


# Someone who is already using the app and reloads, or goes back to, a page address is returned to the same screen in the app.
# A visitor arriving from a search engine or a shared link has no such mark and gets the page itself.
BACK_TO_APP = '<script>try{if(sessionStorage.getItem("tfapp")&&!location.hash&&!location.search)location.replace("/#__H__")}catch(e){}</script>'
IC_COPY = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>'
IC_WA = '<svg viewBox="0 0 24 24" width="21" height="21" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.2-.4.6-1.2.1-.2 0-.3 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.3-.2.3-.9.9-.9 2.2s.9 2.5 1.1 2.7c.1.2 1.9 2.9 4.6 4 1.7.7 2.3.7 3.1.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.3-.2-.5-.3z"/></svg>'
IC_PRINT = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 9V4h10v5"/><rect x="4" y="9" width="16" height="8" rx="2"/><path d="M7 14h10v6H7z"/></svg>'
VIEWS_MIN = 100   # an opening count is shown only from this number up; "opened 4 times" helps nobody
JS_SIDE = (";(function(){var s=document.querySelector('.acts');if(!s)return;var tc=document.querySelector('.rside .svctoc');if(tc&&matchMedia('(min-width:64rem)').matches)tc.open=true;"
           "var P=location.pathname,sv=s.querySelector('[data-act=save]');function fv(){try{return JSON.parse(localStorage.getItem('favs')||'[]')||[]}catch(e){return[]}}"
           "function paint(){if(!sv)return;var on=fv().indexOf(sv.dataset.id)>=0;sv.setAttribute('aria-pressed',on);sv.querySelector('span').textContent=on?'נשמר':'שמירה'}paint();"
           "s.addEventListener('click',function(e){var b=e.target.closest('[data-act]');if(!b)return;var a=b.dataset.act;"
           "if(a==='print'){print()}else if(a==='save'){var f=fv(),k=f.indexOf(b.dataset.id);if(k>=0)f.splice(k,1);else f.push(b.dataset.id);try{localStorage.setItem('favs',JSON.stringify(f))}catch(x){}paint()}"
           "else if(a==='copy'){var u=location.origin+P,l=b.querySelector('span');(navigator.clipboard?navigator.clipboard.writeText(u):Promise.reject()).then(function(){b.classList.add('ok');l.textContent='הועתק';setTimeout(function(){b.classList.remove('ok');l.textContent='קישור'},1800)},function(){prompt('הקישור:',u)})}});"
           "try{var vc=document.querySelector('.vcount'),k='tfv'+P,seen=sessionStorage.getItem(k);if(!/bot|crawl|spider|lighthouse/i.test(navigator.userAgent))"
           "fetch('/api/views'+(seen?'?p='+encodeURIComponent(P):''),seen?{}:{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({p:P})}).then(function(r){return r.json()}).then(function(d){sessionStorage.setItem(k,'1');"
           "if(vc&&d.n>=VIEWS_MIN){vc.textContent='נפתח '+d.n.toLocaleString('he-IL')+' פעמים';vc.hidden=false}}).catch(function(){})}catch(e){}})();".replace("VIEWS_MIN", str(VIEWS_MIN)))
IC_STAR = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/></svg>'


def page(path, title, desc, h1, crumbs, text="", meta="", bar_extra="", after="", before="", lead="", app_hash="",
         app_label="לפתיחה באפליקציה", h1_ctx="", ctx_out=False, hub=False, ld=None, prio="0.6", script="", notfound=False, canon_to=""):
    """text = the sacred text as an <article> body (reading pages); before/after = page chrome around it."""
    url = SITE + path
    assert notfound or (path.startswith("/") and path.endswith("/")), path
    assert title not in TITLES, f"duplicate title: {title!r} ({path} and {TITLES[title]})"
    assert desc not in DESCS, f"duplicate description: {desc!r} ({path} and {DESCS[desc]})"
    assert notfound or 120 <= len(desc) <= 160, f"description length {len(desc)}: {path} {desc!r}"
    assert "—" not in title + desc + h1 + lead + h1_ctx, path
    TITLES[title] = path
    DESCS[desc] = path
    allc = [(BRAND, "/")] + crumbs
    lds = []
    if not notfound:
        bc = [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(allc)]
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": bc})
    for x in ld or []:
        x = dict(x)
        # the square logo card (tools/build-thumb.js) is named as the page's preferred image, which Google reads for the result thumbnail
        if x.get("@type") in ("WebPage", "CollectionPage", "CreativeWork") and not notfound and "primaryImageOfPage" not in x:
            x["primaryImageOfPage"] = {"@type": "ImageObject", "url": f"{SITE}/icons/thumb.png?v=1", "width": 1200, "height": 1200}
        lds.append({"@context": "https://schema.org", **x})
    crumb_html = "<span>›</span>".join(f'<a href="{u}">{esc(n)}</a>' for n, u in allc[:-1])
    h1_html = esc(h1) + (f' <span class="ctx">{esc(h1_ctx)}</span>' if h1_ctx and not ctx_out else "")
    ctx_under = f'<p class="hctx">{esc(h1_ctx)}</p>' if h1_ctx and ctx_out else ""
    reading = ""
    printhead = ""
    if text:
        bar = f'<div class="bar">{TOOLS_HTML}{bar_extra}</div>'
        # on a wide screen the text gets the main column and everything that serves it sits beside it
        # the actions come first, in words: share, link, save, print
        _save = f'<button type="button" data-act="save" data-id="{app_hash[2:]}" aria-pressed="false">{IC_STAR}<span>שמירה</span></button>' if app_hash.startswith("p-") else ""
        acts = (f'<div class="acts" role="group" aria-label="שיתוף ושמירה"><a class="wa" data-act="wa" target="_blank" rel="noopener" href="https://wa.me/?text={quote(h1 + " | תפילה " + url)}" aria-label="שיתוף בוואטסאפ">{IC_WA}<span>שיתוף</span></a>'
                f'<button type="button" data-act="copy" aria-label="העתקת קישור">{IC_COPY}<span>קישור</span></button>{_save}'
                f'<button type="button" data-act="print" aria-label="הדפסה או שמירה כ-PDF">{IC_PRINT}<span>הדפסה</span></button></div><p class="vcount" hidden></p>')
        side = (f'<div class="rside">{acts}{before}<div class="sidebar">{bar}</div></div>'
                # what a printed copy or a saved PDF carries: the site's mark and address at the top, and the page address at the end
                )
        printhead = f'<div class="printhead" aria-hidden="true"><div class="ph">{LOGO.replace("tfg", "tfgp")}<span>כל התפילות במקום אחד · tfilah.com</span></div></div>'
        reading = (f'<div class="rgrid">{side}<div class="rmain"><article class="text" id="text">{text}</article>{FBL}<script>{JS_TOOLS}{JS_SIDE}{FBL_JS}</script><p class="printfoot" aria-hidden="true">הודפס מתוך תפילה · {url.replace("https://", "")}</p>{after}'
                   + (f'<p class="applink"><a href="/#{app_hash}">{esc(app_label)}</a></p>' if app_hash else "") + '</div></div>')
    applink = f'<p class="applink"><a href="/#{app_hash}">{esc(app_label)}</a></p>' if app_hash else ""
    body = f"""<a class="skip" href="#{'text' if text else 'main'}">{'דילוג לטקסט' if text else 'דילוג לתוכן'}</a>
<header class="top"><div class="in"><a class="logo" href="/" aria-label="תפילה, לדף הבית">{LOGO}</a>
{NAV}<button class="dkt" type="button" data-dark aria-pressed="false" aria-label="מצב לילה"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg></button></div></header>
<main id="main">{printhead if text else ''}<div class="rhead"><nav class="crumbs" aria-label="מיקום באתר">{crumb_html}</nav><h1>{h1_html}</h1>{ctx_under}{f'<p class="meta">{meta}</p>' if meta else ''}{f'<p class="lead">{esc(lead)}</p>' if lead else ''}</div>{reading if text else before + after + applink}</main>
<footer class="sitefoot"><div class="in"><div class="fcols"><div class="fbrand"><a class="flogo" href="/" aria-label="תפילה, לדף הבית">{LOGO}</a><b>תפילה · Tfilah.com</b><p>כל התפילות. במקום אחד.</p><div class="fbtns"><a class="fshare" data-share-site href="https://wa.me/?text=%D7%AA%D7%A4%D7%99%D7%9C%D7%94%3A%20%D7%A1%D7%99%D7%93%D7%95%D7%A8%20%D7%AA%D7%A4%D7%99%D7%9C%D7%94%2C%20%D7%A1%D7%A4%D7%A8%20%D7%AA%D7%94%D7%99%D7%9C%D7%99%D7%9D%2C%20%D7%A7%D7%A8%D7%99%D7%90%D7%94%20%D7%9E%D7%A9%D7%95%D7%AA%D7%A4%D7%AA%20%D7%95%D7%96%D7%9E%D7%A0%D7%99%20%D7%A9%D7%91%D7%AA.%20%D7%9B%D7%9C%20%D7%94%D7%AA%D7%A4%D7%99%D7%9C%D7%95%D7%AA%20%D7%91%D7%9E%D7%A7%D7%95%D7%9D%20%D7%90%D7%97%D7%93%20%F0%9F%99%8F%0Ahttps%3A//tfilah.com/%3Futm_source%3Dshare" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.61-.92-2.2-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.21 3.08c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.2 1.87.12.57-.08 1.76-.72 2.01-1.42.25-.7.25-1.29.17-1.42-.07-.12-.27-.2-.57-.35M12.05 21.79h-.01a9.87 9.87 0 0 1-5.03-1.38l-.36-.21-3.74.98 1-3.65-.24-.37a9.86 9.86 0 0 1-1.51-5.26c0-5.45 4.44-9.88 9.89-9.88 2.64 0 5.12 1.03 6.99 2.9a9.82 9.82 0 0 1 2.89 6.99c0 5.45-4.44 9.88-9.88 9.88M20.46 3.49A11.82 11.82 0 0 0 12.05 0C5.5 0 .16 5.34.16 11.89c0 2.1.55 4.14 1.59 5.95L.06 24l6.3-1.65a11.88 11.88 0 0 0 5.68 1.45h.01c6.55 0 11.89-5.34 11.89-11.89 0-3.18-1.24-6.16-3.48-8.41"/></svg>שתפו את האתר לזיכוי הרבים</a><a class="ffb" href="https://www.facebook.com/tfilahcom" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/></svg>עקבו אחרינו בפייסבוק</a></div></div>
<nav aria-label="ניווט באתר"><a href="/siddur/">סידור תפילה</a><a href="/tehillim/">ספר תהילים</a><a href="/kelim/shem/">תהילים לפי שם</a><a href="/ma-mevarchim/">מה מברכים על</a><a href="/zmanei-hayom/">זמני היום</a><a href="/zmanei-shabbat/">זמני שבת</a><a href="/stickers/">סטיקרים לוואטסאפ</a></nav>
<nav aria-label="מקורות, דיווח ותמיכה"><a href="/odot/">מקורות ונוסחים</a><a href="/odot/#taut" data-taut>דיווח על טעות בנוסח</a><a href="/odot/#kesher">צור קשר</a><a href="/#tmicha">תמיכה באתר</a></nav></div>
{'<p class="fsup">תפילה עוזרת לכם? <a href="/#tmicha">אפשר לתמוך בתחזוקת האתר.</a></p>' if DONATE_ON else ''}
<p class="fmail"><span>לתרומות, צרו קשר: <!--email_off--><a href="mailto:team@tfilah.com" dir="ltr">team@tfilah.com</a><!--/email_off--></span><span>לפניות עסקיות: <!--email_off--><a href="mailto:business@tfilah.com" dir="ltr">business@tfilah.com</a><!--/email_off--></span></p><p class="fcredit">הטקסטים מתוך המהדורות הפתוחות של תורת אמת, דעת ו-Tanach.us, דרך הארכיון של ספריא. <a href="/odot/">פירוט המקורות</a></p>
<p class="flegal"><a href="/pratiyut/">פרטיות</a><a href="/tnaim/">תנאי שימוש</a><a href="/negishut/">נגישות</a><button type="button" class="dkb" data-dark aria-pressed="false"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg><span>מצב לילה</span></button></p>
{FOOT_NAV}</div></footer><button type="button" class="totop" id="totop" aria-label="חזרה לראש העמוד" tabindex="-1"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6"/></svg></button><script>{FOOT_JS}{DARK_JS}{TOP_JS}{DCLOSE_JS}</script>{f'<script>{script}</script>' if script else ''}"""
    canon = ('<meta name="robots" content="noindex">' if notfound else
             f'<link rel="canonical" href="{SITE + canon_to if canon_to else url}">\n<meta property="og:url" content="{url}">')
    doc = f"""<!doctype html>
<html lang="he" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{DARK_EARLY}{BACK_TO_APP.replace("__H__", app_hash) if app_hash and app_hash != "home" and not notfound else ""}
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{canon}
<meta property="og:type" content="{'website' if hub or notfound else 'article'}"><meta property="og:site_name" content="{BRAND}"><meta property="og:locale" content="he_IL">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/icons/{og_for(path)}.png?v={OG_V}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#FFFFFF"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" href="/icons/favicon-96.png" type="image/png" sizes="96x96"><link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/icon-192.png">

<style>{css_for(body)}</style><script>{JS_HEAD}</script>
{FONT_HEAD}
{''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False, separators=(",", ":"))}</script>' for x in lds)}
<script>if("serviceWorker" in navigator)addEventListener("load",function(){{navigator.serviceWorker.register("/sw.js").catch(function(){{}})}});</script>{'' if notfound else '<script>' + BEACON_JS + '</script>'}
</head><body{' class="hub"' if hub else ' class="rd"' if text else ''}><i class="tint" aria-hidden="true"></i>
{body}
</body></html>
"""
    out = os.path.join(ROOT, "404.html") if notfound else os.path.join(ROOT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fp = signature(doc)
    lastmod = OLD[path][0] if path in OLD and OLD[path][1] == fp else TODAY
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    if not notfound and not canon_to:
        URLS.append((path, prio, lastmod, fp))

def pager(prev, nxt):
    """prev / nxt = (href, label) or None"""
    a = f'<a href="{prev[0]}" rel="prev"><small>הקודם</small>{esc(prev[1])}</a>' if prev else "<span></span>"
    b = f'<a class="next" href="{nxt[0]}" rel="next"><small>הבא</small>{esc(nxt[1])}</a>' if nxt else "<span></span>"
    return f'<nav class="pager" aria-label="הקודם והבא">{a}{b}</nav>'

# what the site says about the custom of forty days of Perek Shira (see the sources named in the text itself)
PEREK40_NOTE = ('<p class="note">יש נוהגים לומר פרק שירה ארבעים יום ברצף. לא מצאנו מקור קדום למספר ארבעים דווקא: ההקדמה לפרק שירה מדברת על מי שעוסק בו ”בכל יום”. '
                'באתר הידברות השיבו רבנים שאמירת פרק שירה בכל יום היא ”מנהג עתיק יומין” ושאפשר להמשיך גם אחרי ארבעים יום '
                '(<a href="https://www.hidabroot.org/question/26515" rel="noopener" target="_blank">תשובה</a>), '
                'שהקבלה נעשית בלי נדר ושגם שבתות וחגים נכללים בארבעים הימים '
                '(<a href="https://www.hidabroot.org/question/44616" rel="noopener" target="_blank">תשובה</a>), '
                'ושמותר לומר אותו גם בלילה '
                '(<a href="https://www.hidabroot.org/question/260017" rel="noopener" target="_blank">תשובה</a>). '
                'המעקב כאן הוא עזר לזיכרון בלבד, ואין בו הבטחה לתוצאה.</p>')


def track40(key, idle):
    """(html, script) of a forty-day tracker; key names its saved state and its element ids"""
    g, s, r = key + "g", key + "s", key + "r"
    html_ = ('<style>.r40g{display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;max-width:26rem;margin:.8rem 0}@media(min-width:40rem){.r40g{grid-template-columns:repeat(8,1fr);max-width:32rem}}'
             '.r40g button{min-height:2.75rem;border:1px solid var(--line);border-radius:.8rem;background:var(--surface,#fff);color:inherit;font:inherit;font-weight:700;cursor:pointer}'
             '.r40g button[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}.r40x{margin-block-start:.3rem}</style>'
             f'<h2 class="sec" id="maakav">מעקב 40 יום</h2><p class="note" id="{s}" aria-live="polite">{esc(idle)}</p>'
             f'<div class="r40g" id="{g}" role="group" aria-label="ארבעים הימים">' + "".join(f'<button type="button" data-d="{i}" aria-pressed="false" aria-label="יום {i}">{i}</button>' for i in range(1, 41)) + '</div>'
             f'<p><button type="button" class="btn2 r40x" id="{r}" hidden>התחלה מחדש</button></p><p class="note">הסימון נשמר רק במכשיר הזה.</p>')
    js = ("(function(){var g=document.getElementById('" + g + "'),s=document.getElementById('" + s + "'),r=document.getElementById('" + r + "');if(!g)return;var K='" + key + "',d=[];"
          "try{d=JSON.parse(localStorage.getItem(K)||'[]')||[]}catch(e){}if(!(d instanceof Array))d=[];"
          "function save(){try{localStorage.setItem(K,JSON.stringify(d))}catch(e){}}"
          "function paint(){var b=g.querySelectorAll('button'),n=0;for(var i=0;i<b.length;i++){var on=d.indexOf(i+1)>=0;if(on)n++;b[i].setAttribute('aria-pressed',on?'true':'false')}"
          "s.textContent=n===0?" + json.dumps(idle, ensure_ascii=False) + ":n>=40?'סומנו כל 40 הימים.':'סומנו '+n+' מתוך 40 ימים. נשארו '+(40-n)+'.';r.hidden=n===0}"
          "g.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('button');if(!b)return;var k=+b.getAttribute('data-d'),i=d.indexOf(k);if(i>=0)d.splice(i,1);else d.push(k);save();paint()});"
          "r.addEventListener('click',function(){if(confirm('למחוק את כל הסימונים ולהתחיל מחדש?')){d=[];save();paint()}});paint()})();")
    return html_, js


def chips(title, links, hid=""):
    """links = [(href, label)]"""
    if not links:
        return ""
    return (f'<h2 class="sec"{f" id={hid!r}".replace(chr(39), chr(34)) if hid else ""}>{esc(title)}</h2><div class="related">'
            + "".join(f'<a href="{h}">{esc(l)}</a>' for h, l in links) + "</div>")

def item_list(paths):
    return {"@type": "ItemList", "numberOfItems": len(paths),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": SITE + u} for i, u in enumerate(paths)]}

def collection(name, path, paths, desc=""):
    d = {"@type": "CollectionPage", "name": name, "url": SITE + path, "inLanguage": "he", "isPartOf": WEBSITE}
    if desc:
        d["description"] = desc
    if paths:
        d["mainEntity"] = item_list(paths)
    return d

# =====================================================================
# Load everything first: links between pages need the whole picture.
# =====================================================================
P = json.load(open(os.path.join(DATA, "tehillim.json"), encoding="utf-8"))
TIKKUN = json.load(open(os.path.join(DATA, "tikkun.json"), encoding="utf-8"))
I = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
NUS = I["nusachim"]
TEXTS = {n: json.load(open(os.path.join(DATA, f"{n}.json"), encoding="utf-8")) for n in NUS}
by_nus = {n: [p for p in I["prayers"] if p["n"] == n and TEXTS[n].get(p["id"])] for n in NUS}

# ---------- short addresses for prayer pages: /<name in Latin letters>/ ----------
# The name alone is the address (tfilah.com/perek-shira/). When the same prayer exists in more than one nusach,
# the first in the order Edot HaMizrach, Sefard, Ashkenaz has the plain address and the others add their nusach
# after the name (tfilah.com/tefilat-haderech/ashkenaz/).
_RESERVED = {"n", "siddur", "birkat-kala", "segulat-rachel-imenu", "kaddish", "shem", "leiluy-nishmat", "kotel", "tefila", "tehillim", "sefer", "kelim", "odot", "chanukah", "tisha-beav", "zmanei-hayom", "zmanei-shabbat", "tehillim-yachad", "pratiyut", "tnaim", "negishut", "parasha", "ma-mevarchim", "y", "api", "data", "icons",
             "brand", "fonts", "src", "tools", "functions", "mizrach", "sefard", "ashkenaz", "index", "sitemap", "robots", "config", "shim", "sw", "404"}
TRANSLIT = json.load(open(os.path.join(ROOT, "tools", "translit.json"), encoding="utf-8"))
_SLUG_CTX = [("שבת", "shabbat"), ("ראש חודש", "rosh-chodesh"), ("רגלים", "regalim"), ("קבלת שבת", "kabbalat"), ("שחרית", "shacharit"), ("מנחה", "mincha"),
             ("ערבית", "arvit"), ("מעריב", "arvit"), ("מוסף", "musaf"), ("סעוד", "seuda"), ("חנוכה", "chanukah"), ("סוכות", "sukkot"), ("הגדה", "hagada"), ("קדיש", "kaddish")]


def _slug(title):
    ws = re.findall(r"[א-ת\"'׳״]+|[A-Za-z0-9]+", NIK.sub("", title))
    miss = [w for w in ws if w not in TRANSLIT]
    assert not miss, f"tools/translit.json has no entry for {miss} (title {title!r}); add it"
    return "-".join(TRANSLIT[w] for w in ws) or "tefila"


# A bare name ("שחרית", "הלל") that in the source is a part of a special occasion must not hold the plain address:
# /shacharit/ used to open the Chanukah additions. These records get an address that says what they are.
FORCE_SLUG = {"mizrach-101": "shacharit-lachanukah", "mizrach-88": "musaf-rosh-chodesh", "sefard-165": "hallel-hagada",
              "sefard-90": "tefilat-amida-erev-shabbat", "ashkenaz-299": "haftara-shabbat", "ashkenaz-141": "baruch-hashem-leolam"}
# short addresses that moved, or that people type: one 301 hop to the page they mean
MOVED = {"/shacharit/": "/siddur/mizrach/shacharit/", "/mincha/": "/siddur/mizrach/mincha/", "/arvit/": "/siddur/mizrach/arvit/", "/maariv/": "/siddur/mizrach/arvit/",
         "/hallel/": "/seder-hallel/", "/musaf/": "mizrach-88", "/tefilat-amida/": "sefard-90", "/haftara/": "ashkenaz-299",
         "/baruch-hashem-leolam-outside-of-israel/": "ashkenaz-141"}


def _build_purl():
    out, taken = {}, set(_RESERVED) | {m.strip("/") for m in MOVED}
    for n in ("mizrach", "sefard", "ashkenaz"):
        ps = [p for p in I["prayers"] if p["n"] == n and TEXTS[n].get(p["id"])]
        base = {p["id"]: _slug(p["t"]) for p in ps}
        count = {}
        for v in base.values(): count[v] = count.get(v, 0) + 1
        used = set(_RESERVED) | {m.strip("/") for m in MOVED}
        for p in ps:
            s = FORCE_SLUG.get(p["id"]) or base[p["id"]]
            if s in used:                                   # the first prayer with a name keeps it plain; later ones say where they belong
                ctx = " / ".join(p["s"])
                tags = []
                for he, la in _SLUG_CTX:
                    if he in ctx and la not in tags and la not in s.split("-"):
                        tags.append(la)
                s2 = "-".join([s] + tags[:2]) if tags else s
                k, cand = 2, s2
                while cand in used:
                    cand = f"{s2}-{k}"; k += 1
                s = cand
            assert s not in used, s
            used.add(s)
            if s in taken:
                out[p["id"]] = f"/{s}/{n}/"                   # the same name in another nusach
            else:
                taken.add(s); out[p["id"]] = f"/{s}/"
    return out


PURL = _build_purl()
# The same words printed again in another service (Aleinu of mincha is Aleinu of shacharit, letter for letter) are one
# text for a search engine. Every copy stays readable at its own address, but names the first one as canonical and stays
# out of the sitemap, so the site is not judged by 79 repeats. Only exact matches inside one nusach count.
def _dups():
    out = {}
    for n in ("mizrach", "sefard", "ashkenaz"):
        groups = {}
        for i, p in enumerate(q for q in I["prayers"] if q["n"] == n and TEXTS[n].get(q["id"])):
            key = re.sub(r"[^\u05D0-\u05EA]", "", re.sub(r"<[^>]+>", "", "".join(TEXTS[n][p["id"]])))
            groups.setdefault(key, []).append((len(PURL[p["id"]]), i, p["id"]))
        for g in groups.values():
            if len(g) > 1:
                first = min(g)[2]
                out.update({pid: first for _, _, pid in g if pid != first})
    return out


DUP_OF = _dups()
json.dump({PURL[a]: PURL[b] for a, b in DUP_OF.items()}, open(os.path.join(ROOT, "tools", "dup-canon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
_PRAYER_PATHS.update(PURL.values())
BYID = {p["id"]: p for plist in by_nus.values() for p in plist}
B = json.load(open(os.path.join(DATA, "books.json"), encoding="utf-8"))
BOOK_KEYS = list(B)

def sec_of(p):
    return [x for x in (p.get("s") or []) if x]

def norm_t(t):
    """title key for matching: spelling variants only, never meaning"""
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
            s = sec_of(p)
            ctx = " · ".join(s)
            clash = [q for q in g if sec_of(q) == s]
            if len(clash) > 1:
                ctx = (ctx + " · " if ctx else "") + f"חלק {gem(clash.index(p) + 1)}"
            if not ctx:
                continue  # the only one of its title without a section keeps the bare title
            assert ctx not in seen, (p["id"], ctx)
            seen[ctx] = 1
            CTX[p["id"]] = ctx

for pid in ("mizrach-101", "mizrach-88", "sefard-165", "sefard-90", "ashkenaz-299"):
    CTX.setdefault(pid, " · ".join(sec_of(BYID[pid])[-2:]))

# The stand-alone instance of a repeated title gets the clean <title> (its twins keep their context).
PRIMARY = {"ashkenaz-1", "ashkenaz-3", "ashkenaz-4", "ashkenaz-13", "ashkenaz-440", "ashkenaz-441", "ashkenaz-442", "ashkenaz-443"}
for pid in PRIMARY:
    assert pid in BYID and pid in CTX, pid
# ...and so does the first page of every other repeated name: it is the one that holds the plain address (/kaddish-yatom/),
# and a title that drags its whole section path behind it reads badly in search results.
for _n, _pl in by_nus.items():
    _first = {}
    for p in _pl:
        _first.setdefault(p["t"], p)
    _own = {BYID[i]["t"] for i in PRIMARY if BYID[i]["n"] == _n}   # names that already have a stand-alone page chosen by hand
    PRIMARY |= {p["id"] for p in _first.values() if p["id"] in CTX and p["t"] not in _own}

# How people type the name. The source title stays as the H1; these only lead the <title> and description.
SPELL = {"תפלת הדרך": "תפילת הדרך", "פטום הקטורת": "פיטום הקטורת", "פטום קטורת": "פיטום הקטורת",
         'ק"ש וברכותיה': "קריאת שמע וברכותיה", "קריאת שמע על המיטה": "קריאת שמע שעל המיטה",
         "תפלת הנוטל תרופה": "תפילת הנוטל תרופה"}
LEAD = {"סדר הבדלה": "הבדלה למוצאי שבת", "סדר הדלקת נרות שבת": "הדלקת נרות שבת",
        "סדר הדלקת נרות חנוכה": "הדלקת נרות חנוכה", "הבדלה": "הבדלה למוצאי שבת"}
LEAD_ID = {"mizrach-11": "פתיחה לתפילת שחרית (לשם יחוד)", "ashkenaz-211": "קידוש לליל שבת", "sefard-132": "הלל לראש חודש (סדר הלל)"}
ALSO = {"קידוש לבנה": "ברכת הלבנה", "ברכת הלבנה": "קידוש לבנה", "ברכת מעין שלוש": "על המחיה",
        "ברכה אחרונה מעין שלוש": "על המחיה", "על המחיה": "ברכה מעין שלוש"}

# the same name typed without the gershayim: shown next to the source title, never instead of it
ALT_SPELL = {'אגרת הרמב"ן': "אגרת הרמבן", 'תפילת השל"ה הקדוש': "תפילת השלה"}

# One line on when the prayer is said. Only where it is plain and undisputed; everything else gets no line.
CONTEXT = {
    "מודה אני": "נאמר בבוקר, מיד עם ההתעוררות.",
    "קריאת שמע על המיטה": "נאמרת בלילה, לפני השינה.",
    "ברכת המזון": "נאמרת אחרי סעודה שאכלו בה לחם.",
    "תפילת הדרך": "נאמרת ביציאה לדרך אל מחוץ לעיר.",
    "אשר יצר": "נאמרת אחרי היציאה מבית הכיסא.",
    "ברכת הלבנה": "נאמרת פעם בחודש, בלילה, כשהלבנה נראית.",
    "קידוש לבנה": "נאמרת פעם בחודש, בלילה, כשהלבנה נראית.",
    "ספירת העומר": "נאמרת בכל לילה, מליל שני של פסח ועד ערב חג השבועות.",
    "סדר הבדלה": "נאמרת במוצאי שבת, על כוס יין.",
    "הבדלה": "נאמרת במוצאי שבת, על כוס יין.",
    "קידוש ליל שבת": "נאמר בליל שבת, לפני הסעודה.",
    "נשמת כל חי": "נאמרת בתפילת שחרית של שבת ויום טוב.",
    "קדיש יתום": "נאמר על ידי האבלים, במניין.",
}
CONTEXT_ID = {"ashkenaz-211": "נאמר בליל שבת, לפני הסעודה."}

# People who type "ספרדי" often mean עדות המזרח; "נוסח ספרד" is the chassidic rite. One factual line, with a link.
NUS_NOTE = {"mizrach": ("נוסח עדות המזרח הוא נוסח הספרדים ובני עדות המזרח. נוסח ספרד, הנהוג בקהילות החסידים, הוא נוסח אחר", "sefard"),
            "sefard": ("נוסח ספרד הוא הנוסח הנהוג בקהילות החסידים. נוסח הספרדים ובני עדות המזרח הוא נוסח אחר", "mizrach")}
assert all(k in NUS and v[1] in NUS for k, v in NUS_NOTE.items())

def nus_note(n, href, label):
    if n not in NUS_NOTE:
        return ""
    return f'<p class="note">{esc(NUS_NOTE[n][0])}: <a href="{href}">{esc(label)}</a>.</p>'

def weekday_amida(p):
    s = sec_of(p)
    return p["t"] == "עמידה" and s and ("לימי החול" in s[0] or "לימות החול" in s[0])

def lead_of(p):
    if weekday_amida(p):
        return "תפילת שמונה עשרה"
    return LEAD_ID.get(p["id"]) or SPELL.get(p["t"]) or LEAD.get(p["t"]) or p["t"]

def also_of(p):
    if weekday_amida(p):
        return "עמידה"
    return ALSO.get(p["t"], "")

def title_name(p):
    t = lead_of(p) + (f" ({also_of(p)})" if also_of(p) else "")
    ctx = CTX.get(p["id"])
    if ctx and p["id"] not in PRIMARY:
        t += f", {ctx}" if weekday_amida(p) else f" ({ctx})"
    return t

# a common spelling may coincide with another prayer's own title: then both carry their section
TNAME = {p["id"]: title_name(p) for plist in by_nus.values() for p in plist}
_seen = {}
for pid, t in TNAME.items():
    _seen.setdefault((BYID[pid]["n"], t), []).append(pid)
for (n, t), ids in _seen.items():
    if len(ids) > 1:
        for pid in ids:
            TNAME[pid] = f"{t} ({' · '.join(sec_of(BYID[pid])[:2])})"
assert len({(BYID[i]["n"], t) for i, t in TNAME.items()}) == len(TNAME)

def pname(p):
    return p["t"] + (f" ({CTX[p['id']]})" if CTX.get(p["id"]) else "")

# Counterparts in the other nusachim. Only real ones:
#  1. same title and same section path (after spelling normalisation), or
#  2. same title where the title is unique in BOTH nusachim (no guessing between several), or
#  3. the hand-checked most-wanted prayers below (WANT).
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

def by_title(n, *titles):
    """first prayer of the nusach with one of the titles; the stand-alone instance wins over its twins"""
    for t in titles:
        c = T_COUNT[n].get(norm_t(t), [])
        if c:
            return next((p for p in c if p["id"] in PRIMARY), c[0])
    return None

# ---------- weekday services ----------
SERVICES = [
    ("shacharit", "שחרית", {"mizrach": [["סדר השכמת הבוקר"], ["שחרית לימי החול"], ["תוספות לשחרית"]],
                            "sefard": [["סדר השכמת הבוקר"], ["שחרית לימות החול"], ["תוספות אחרי שחרית"]],
                            "ashkenaz": [["ימי חול", "תפילת שחרית"]]}),
    ("mincha", "מנחה", {"mizrach": [["מנחה לימי החול"]], "sefard": [["מנחה לימות החול"]], "ashkenaz": [["ימי חול", "תפילת מנחה"]]}),
    ("arvit", "ערבית", {"mizrach": [["ערבית לימי החול"]], "sefard": [["ערבית לימות החול"]], "ashkenaz": [["ימי חול", "מעריב"]]}),
]
SVC = {}        # (nusach, key) -> [(prayer, matched prefix)]
SVC_OF = {}     # prayer id -> service key
for key, label, cfg in SERVICES:
    for n in NUS:
        items = []
        for p in by_nus[n]:
            s = sec_of(p)
            pre = next((x for x in cfg[n] if s[:len(x)] == x), None)
            if pre:
                items.append((p, pre))
                SVC_OF[p["id"]] = key
        assert items, (n, key)
        SVC[(n, key)] = items
SVC_LABEL = {k: l for k, l, _ in SERVICES}

def svc_name(n, key):
    return ("ערבית (מעריב)" if key == "arvit" and n == "ashkenaz" else SVC_LABEL[key]) + " לימי חול"

# ---------- section groups of a nusach (the app groups consecutive prayers by the first two section levels) ----------
GROUPS = {}     # nusach -> [(label, [prayers])]
GROUP_OF = {}   # prayer id -> index
for n, plist in by_nus.items():
    gs, cur = [], None
    for p in plist:
        k = tuple(sec_of(p)[:2])
        if not gs or k != cur:
            gs.append((" · ".join(k) if k else "תפילות וברכות", []))
            cur = k
        gs[-1][1].append(p)
        GROUP_OF[p["id"]] = len(gs) - 1
    GROUPS[n] = gs

def section_link(p):
    """(href, label) of the page that lists this prayer's section"""
    n = p["n"]
    if p["id"] in SVC_OF:
        k = SVC_OF[p["id"]]
        return f"/siddur/{n}/{k}/", svc_name(n, k)
    gi = GROUP_OF[p["id"]]
    return f"/siddur/{n}/#g{gi + 1}", GROUPS[n][gi][0]

# ---------- most wanted ----------
WANT = [
    ("ברכת המזון", ["ברכת המזון"]), ("תפילת הדרך", ["תפילת הדרך"]), ("קריאת שמע שעל המיטה", ["קריאת שמע על המיטה"]),
    ("מודה אני", ["מודה אני"]), ("ברכות השחר", ["ברכות השחר"]), ("אשר יצר", ["אשר יצר"]),
    ("ברכת הלבנה", ["ברכת הלבנה", "קידוש לבנה"]), ("ספירת העומר", ["ספירת העומר"]),
    ("פיטום הקטורת", ["פטום הקטורת", "פטום קטורת", "פיטום הקטורת"]), ("קדיש יתום", ["קדיש יתום"]),
    ("נשמת כל חי", ["נשמת כל חי"]), ("קידוש לליל שבת", ["קידוש ליל שבת", "קידוש"]), ("הבדלה", ["סדר הבדלה", "הבדלה"]),
    ("הלל", ["סדר הלל", "הלל לראש חודש ולמועדים"]), ("ברכה מעין שלוש (על המחיה)", ["ברכת מעין שלוש", "ברכה אחרונה מעין שלוש", "על המחיה"]),
    ("אנא בכח", ["אנא בכח"]), ('אגרת הרמב"ן', ['אגרת הרמב"ן']), ('תפילת השל"ה', ['תפילת השל"ה הקדוש']), ("פרשת המן", ["פרשת המן"]),
    ("תפילה על הפרנסה", ["תפילה על הפרנסה"]),
]
WANT_IDS = {q["id"] for _, titles in WANT for q in (by_title(n, *titles) for n in NUS) if q}
SAME = {p["id"]: counterparts(p) for plist in by_nus.values() for p in plist}
for label, titles in WANT:
    grp = [q for q in (by_title(n, *titles) for n in NUS) if q]
    for q in grp:
        for r in grp:
            if r is not q and all(x["n"] != r["n"] for x in SAME[q["id"]]):
                SAME[q["id"]].append(r)
for v in SAME.values():
    v.sort(key=lambda q: list(NUS).index(q["n"]))

# ---------- curated relations ----------
# T(...) = a prayer by title, resolved inside the reader's nusach; U(path, label) = a fixed page.
def T(*titles): return ("t", titles)
def U(path, label): return ("u", path, label)
REL = [
    [T("ברכת המזון"), T("ברכת מעין שלוש", "ברכה אחרונה מעין שלוש", "על המחיה"), T("ברכות הנהנין", "ברכות ראשונות"), T("בורא נפשות"), T("סדר שבע ברכות")],
    [T("תפילת הדרך"), T("תפילת הדרך לטסים באוירון"), T("ברכת הגומל"), U("/tehillim/derech/", "תהילים להצלחה בדרך"), U("/tehillim/121/", "תהילים פרק קכא")],
    [T("קריאת שמע על המיטה"), T("מודה אני"), T("ברכות השחר"), T("אשר יצר"), T("ברכות התורה"), U("/tehillim/91/", "תהילים פרק צא")],
    [T("ברכת הלבנה", "קידוש לבנה"), T("ספירת העומר"), T("ברכת החודש", "הכרזת ראש חדש"), T("סדר ברכת האילנות", "ברכת האילנות")],
    [T("סדר הדלקת נרות שבת"), T("קבלת שבת", "לכה דודי"), T("שלום עליכם"), T("אשת חיל"), T("קידוש ליל שבת", "קידוש"), T("סדר הבדלה", "הבדלה")],
    [T("קדיש יתום"), T("אבלות"), T("הזכרת נשמות", "סדר הזכרת נשמות"), U("/sefer/yizkor/", "יזכור"), U("/tehillim/neshama/", "תהילים לעילוי נשמה"), U("/tehillim/kever/", "תהילים לבית העלמין")],
    [T("פרשת המן"), T("תפילה על הפרנסה"), U("/sefer/haman/", "פרשת המן"), U("/tehillim/parnasa/", "תהילים לפרנסה")],
    [T("תפלת הנוטל תרופה"), T("מי שברך לחולה", "לחולים"), U("/tehillim/refuah/", "תהילים לרפואה")],
    [T("פרקי אבות"), U("/sefer/avot/", "פרקי אבות, ששת הפרקים")],
    [T("שיר השירים"), U("/sefer/shir/", "שיר השירים")],
    [T("פרק שירה"), U("/sefer/perek/", "פרק שירה")],
    [T("קריאת המגילה"), T("סדר יום פורים"), U("/sefer/esther/", "מגילת אסתר")],
    [T("סדר הלל", "הלל לראש חודש ולמועדים", "ברכת הלל"), U("/tehillim/113/", "תהילים פרק קיג"), U("/tehillim/118/", "תהילים פרק קיח"), U("/tehillim/hodaya/", "תהילים להודיה ולשמחה")],
    [U("/sefer/chana/", "תפילת חנה"), U("/tehillim/banim/", "תהילים לזרע של קיימא")],
    [U("/sefer/haazinu/", "שירת האזינו"), U("/tehillim/parnasa/", "תהילים לפרנסה"), U("/sefer/haman/", "פרשת המן")],
    [U("/sefer/selichot/", "סליחות"), U("/tehillim/tzara/", "תהילים לעת צרה"), U("/tehillim/130/", "תהילים פרק קל")],
    [U("/tehillim/tikkun/", "תיקון הכללי"), U("/tehillim/tzara/", "תהילים לעת צרה"), U("/tehillim/yomi/", "תהילים יומי")],
]
CUR = {}   # path -> [(href, label)]

def cur_add(a, href, label):
    if a != href and all(h != href for h, _ in CUR.setdefault(a, [])):
        CUR[a].append((href, label))

for grp in REL:
    fixed = [(m[1], m[2]) for m in grp if m[0] == "u"]
    per_nus = {n: [q for q in (by_title(n, *m[1]) for m in grp if m[0] == "t") if q] for n in NUS}
    for n in NUS:
        members = per_nus[n]
        for p in members:
            me = f"{PURL[p['id']]}"
            for q in members:
                if q is not p and norm_t(q["t"]) != norm_t(p["t"]):
                    cur_add(me, f"{PURL[q['id']]}", lead_of(q))
            for href, label in fixed:
                cur_add(me, href, label)
    for href, label in fixed:
        for h2, l2 in fixed:
            cur_add(href, h2, l2)
        for n in NUS:
            for q in per_nus[n]:
                cur_add(href, f"{PURL[q['id']]}", f"{lead_of(q)} · נוסח {NUS[n]}")

# Ashkenaz lists single psalms as parts of the service ("תהילים קמו"): link them to the chapter page and back.
for p in by_nus.get("ashkenaz", []):
    m = re.fullmatch(r"תהילים ([א-ת]{1,3})", p["t"])
    if m and 1 <= ungem(m.group(1)) <= 150:
        cur_add(f"{PURL[p['id']]}", f"/tehillim/{ungem(m.group(1))}/", f"תהילים פרק {m.group(1)}, הפרק המלא")

NEED_OF = {}   # chapter -> [need keys]
for k, t, chs in NEEDS:
    for c in chs:
        NEED_OF.setdefault(c, []).append(k)
NEED_T = {k: t for k, t, _ in NEEDS}

def need_h1(k):
    return "תיקון הכללי" if k == "tikkun" else "תהילים " + NEED_T[k]

def month_day(c):
    return [i + 1 for i, (a, b) in enumerate(MONTHLY) if a <= c <= b]
def week_day(c):
    return next(i for i, (a, b) in enumerate(WEEKLY) if a <= c <= b)

def fill(links, extra, lo=6, hi=8):
    """curated links first, then extras until there are at least lo; never more than hi"""
    out = []
    for h, l in links:
        if all(h != x for x, _ in out):
            out.append((h, l))
    for h, l in extra:
        if len(out) >= lo:
            break
        if all(h != x for x, _ in out):
            out.append((h, l))
    return out[:hi]

WD_SLUG = ["yom-rishon", "yom-sheni", "yom-shlishi", "yom-revii", "yom-chamishi", "yom-shishi", "yom-shabbat"]

def rng(a, b):
    return f"פרק {gem(a)}" if a == b else f"פרקים {gem(a)} עד {gem(b)}"

# The shared reading itself lives in the app: this block is the way in from pages that are said for someone.
TOGETHER_APP = ('<aside class="together" aria-labelledby="tg"><h2 id="tg">קריאת תהילים משותפת</h2>'
                '<p>כל אחד פרק. ביחד ספר שלם. הקריאה המשותפת נפתחת באפליקציה.</p>'
                '<a class="btn" href="/#zikaron">לתהילים יחד באפליקציה</a><a href="/tehillim-yachad/">איך זה עובד</a></aside>')
TOGETHER = ('<aside class="together" aria-labelledby="tg"><h2 id="tg">תהילים יחד</h2>'
            '<p>כל אחד פרק. ביחד ספר שלם.</p><a class="btn" href="/tehillim-yachad/">איך קוראים תהילים יחד</a></aside>')

# =====================================================================
# Tehillim
# =====================================================================
def verses(c):
    return "".join(f'<p><sup>{gem(i+1)}</sup>{clean(v)}</p>' for i, v in enumerate(P[c - 1]))

BOOK_T = {"@type": "Book", "name": "ספר תהילים", "inLanguage": "he", "url": SITE + "/tehillim/"}

for c in range(1, 151):
    vs = P[c - 1]
    after = pager((f"/tehillim/{c-1}/", f"תהילים פרק {gem(c-1)}") if c > 1 else None,
                  (f"/tehillim/{c+1}/", f"תהילים פרק {gem(c+1)}") if c < 150 else None)
    rel = [(f"/tehillim/{k}/", need_h1(k)) for k in NEED_OF.get(c, [])]
    if c == 100:
        rel.insert(0, ("/mizmor-letoda/", "מזמור לתודה בסידור"))
    md, wd = month_day(c), week_day(c)
    rel += [(f"/tehillim/chodesh-{d}/", f"תהילים ליום {gem(d)} בחודש") for d in md]
    rel.append((f"/tehillim/{WD_SLUG[wd]}/", f"תהילים ליום {DAYS[wd]}"))
    if c == 119:
        rel.append(("/kelim/shem/", "תהילים קיט לפי אותיות השם"))
    rel += [(h, l) for h, l in CUR.get(f"/tehillim/{c}/", []) if not re.fullmatch(r"/tehillim/\d+/", h)][:3]
    near = [x for x in (c - 2, c + 2, c - 3, c + 3, c - 4, c + 4) if 1 <= x <= 150]
    rel = fill(rel, [(f"/tehillim/{x}/", f"תהילים פרק {gem(x)}") for x in near], lo=6)
    rel.append(("/tehillim/", "כל 150 פרקי התהילים"))
    after += TOGETHER + chips("עוד בתהילים", rel)
    nv = "פסוק אחד" if len(vs) == 1 else f"{len(vs)} פסוקים"
    name = f"תהילים פרק {gem(c)}"
    first = snippet(vs[0], max(16, 62 - len(f"{name} ({c}) |  | {BRAND}")))
    page(f"/tehillim/{c}/",
         f"{name} ({c}) | {first} | {BRAND}",
         fit_desc(f"{name} ({c}), מזמור {gem(c)}, בניקוד מלא, {nv}", " ".join(vs[:3])),
         name, [("תהילים", "/tehillim/"), (f"פרק {gem(c)}", f"/tehillim/{c}/")],
         text=verses(c), meta=f"{esc(first)} · {nv}", after=after, app_hash=f"t-{c}",
         before=(f'<aside class="plainx" aria-label="הסבר קצר"><b>על מה המזמור הזה?</b><p>{esc(PLAIN_T_EARLY[str(c)])}</p></aside>' if str(c) in PLAIN_T_EARLY else ""),
         ld=[{"@type": "Chapter", "name": name, "position": c, "inLanguage": "he", "isAccessibleForFree": True,
              "url": f"{SITE}/tehillim/{c}/", "isPartOf": BOOK_T}])

# ---------- Tehillim by need ----------
NEED_ALT = {"refuah": "לרפואת חולה", "shidduch": "לשידוך", "banim": "לפרי בטן", "kever": "לאזכרה וליום השנה",
            "tzara": "ליום צרה", "shmira": "להצלה", "hodaya": "לתודה"}
NEED_NOTE = {
    "refuah": "נוהגים להזכיר בתפילה את שם החולה ואת שם אמו.",
    "tikkun": "עשרת הפרקים נאמרים ברצף, לפי הסדר הזה. את הסדר תיקן רבי נחמן מברסלב.",
    "neshama": "יש נוהגים להוסיף מפרק קיט את הפסוקים שלפי אותיות שם הנפטר ואותיות המילה נשמה.",
    "kever": "אלה הפרקים שנוהגים לומר ליד הקבר, לפי הסדר הזה. יש נוהגים להוסיף מפרק קיט את הפסוקים שלפי אותיות שם הנפטר.",
}
for i, (k, t, chs) in enumerate(NEEDS):
    h1 = need_h1(k)
    names = ", ".join(gem(c) for c in chs)
    cnt = f"{len(chs)} פרקי תהילים" if len(chs) > 2 else "שני פרקי תהילים"
    if k == "tikkun":
        title = f"תיקון הכללי: עשרת פרקי התהילים בניקוד מלא | {BRAND}"
        lead = f"עשרת פרקי התהילים של תיקון הכללי: {names}. כל הפרקים כאן ברצף, בניקוד מלא."
        desc = fit_desc(f"תיקון הכללי, עשרת פרקי התהילים לפי הסדר: {names}. הנוסח המלא בניקוד בעמוד אחד, עם קישור לכל פרק", tails=("קריאה נוחה בנייד.",))
    else:
        alt = f" ({NEED_ALT[k]})" if k in NEED_ALT else ""
        title = f"{h1}: פרקים {names} | {BRAND}"
        lead = f"{cnt} שנוהגים לומר {t}{alt}: {names}. כל הפרקים כאן ברצף, בניקוד מלא."
        desc = fit_desc(f"{h1}{alt}: {cnt} שנוהגים לומר, פרקים {names}. כל הפרקים ברצף בעמוד אחד, בניקוד מלא",
                        tails=("עם קישור לכל פרק בנפרד.", "קריאה נוחה בנייד.", "באתר תפילה."))
    text = "".join(f'<h2 id="p{c}"><a href="/tehillim/{c}/">תהילים פרק {gem(c)}</a></h2>{verses(c)}' for c in chs)
    if k == "tikkun":
        # what is said before and after the ten psalms, from the edition named in data/tikkun.json
        text = ('<h2 id="lifnei">לפני אמירת המזמורים</h2>' + "".join(f"<p>{clean(x)}</p>" for x in TIKKUN["open"]) + text
                + '<h2 id="acharei">תפילה אחרי תיקון הכללי</h2>' + "".join(f"<p>{clean(x)}</p>" for x in TIKKUN["short"])
                + '<details class="tklong"><summary>התפילה הארוכה של רבי נתן</summary>' + "".join(f"<p>{clean(x)}</p>" for x in TIKKUN["natan"]) + "</details>")
        title = f"תיקון הכללי המלא: עשרת המזמורים והתפילה שאחריהם | {BRAND}"
        lead = f"תיקון הכללי כפי שאומרים אותו: הפתיחה, עשרת פרקי התהילים ({names}) והתפילה שאחריהם. הכול ברצף, בניקוד מלא."
    before = (f'<p class="note">{esc(NEED_NOTE[k])}</p>' if k in NEED_NOTE else "")
    before += ('<div class="related jr" style="margin-block-end:1rem">' + ('<a href="#lifnei">הפתיחה</a>' if k == "tikkun" else "")
               + "".join(f'<a href="#p{c}">פרק {gem(c)}</a>' for c in chs) + ('<a href="#acharei">התפילה שאחרי</a>' if k == "tikkun" else "") + "</div>")
    prev, nxt = (NEEDS[i - 1] if i else None), (NEEDS[i + 1] if i + 1 < len(NEEDS) else None)
    after = pager((f"/tehillim/{prev[0]}/", need_h1(prev[0])) if prev else None, (f"/tehillim/{nxt[0]}/", need_h1(nxt[0])) if nxt else None)
    after += chips("כל פרק בעמוד משלו", [(f"/tehillim/{c}/", f"תהילים פרק {gem(c)}") for c in chs])
    rel = [(h, l) for h, l in CUR.get(f"/tehillim/{k}/", []) if not re.fullmatch(r"/tehillim/\d+/", h)][:5]
    others = sorted((x for x in NEEDS if x[0] != k), key=lambda x: -len(set(x[2]) & set(chs)))
    rel = fill(rel, [(f"/tehillim/{x[0]}/", need_h1(x[0])) for x in others], lo=6)
    rel.append(("/tehillim/#bakasha", "כל פרקי התהילים לפי בקשה"))
    after += chips("קשור לעמוד הזה", rel)
    if k in ("neshama", "kever", "refuah"):
        after += '<p class="applink"><a href="/kelim/shem/">תהילים קיט לפי אותיות השם</a></p>'
    after += TOGETHER_APP
    page(f"/tehillim/{k}/", title, desc, h1, [("תהילים", "/tehillim/"), (h1, f"/tehillim/{k}/")],
         text=text, lead=lead, before=before, after=after, app_hash=f"k-{k}", prio="0.8",
         ld=[{"@type": "CreativeWork", "name": h1, "inLanguage": "he", "isAccessibleForFree": True, "url": f"{SITE}/tehillim/{k}/",
              "isPartOf": BOOK_T, "hasPart": [{"@type": "Chapter", "name": f"תהילים פרק {gem(c)}", "url": f"{SITE}/tehillim/{c}/"} for c in chs]}])

# ---------- a page per weekday and per day of the month, chapters in full ----------
def verses_part(c, lo, hi):
    return "".join(f'<p><sup>{gem(i+1)}</sup>{clean(v)}</p>' for i, v in list(enumerate(P[c - 1]))[lo:hi])

def day_page(path, h1, title, head, a, b, part, prev, nxt, rel, lead):
    """part = None, or (lo, hi, label) for the half of chapter 119 that belongs to the day"""
    text, jump = "", ""
    for c in range(a, b + 1):
        lab = f"תהילים פרק {gem(c)}" + (f", {part[2]}" if part else "")
        text += f'<h2 id="p{c}"><a href="/tehillim/{c}/">{lab}</a></h2>' + (verses_part(c, part[0], part[1]) if part else verses(c))
        jump += f'<a href="#p{c}">פרק {gem(c)}</a>'
    before = f'<div class="related jr" style="margin-block-end:1rem">{jump}</div>' if b > a else ""
    after = pager(prev, nxt) + chips("קשור לעמוד הזה", rel) + TOGETHER_APP
    first = P[a - 1][part[0] if part else 0]
    page(path, title, fit_desc(head, first), h1, [("תהילים", "/tehillim/"), ("תהילים יומי", "/tehillim/yomi/"), (h1, path)],
         text=text, lead=lead, before=before, after=after, app_hash=f"t-{a}-{b}" if b > a else f"t-{a}", app_label="לקריאה רצופה באפליקציה", prio="0.7",
         ld=[{"@type": "CreativeWork", "name": h1, "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + path, "isPartOf": BOOK_T,
              "hasPart": [{"@type": "Chapter", "name": f"תהילים פרק {gem(c)}", "url": f"{SITE}/tehillim/{c}/"} for c in range(a, b + 1)]}])

def wd_h1(d): return f"תהילים ליום {DAYS[d]}"
def md_h1(d): return f"תהילים ליום {gem(d)} בחודש"

for d, (a, b) in enumerate(WEEKLY):
    overlap = [m + 1 for m, (x, y) in enumerate(MONTHLY) if x <= b and y >= a]
    rel = [("/tehillim/yomi/", "תהילים יומי: החלוקה לימי השבוע ולימי החודש")] + [(f"/tehillim/chodesh-{m}/", md_h1(m)) for m in overlap][:6] + [("/tehillim/", "כל 150 פרקי התהילים")]
    n = b - a + 1
    day_page(f"/tehillim/{WD_SLUG[d]}/", wd_h1(d), f"{wd_h1(d)}: {rng(a, b)} בניקוד מלא | {BRAND}",
             f"{wd_h1(d)} לפי החלוקה השבועית של הספר: {rng(a, b)}, {n} פרקים ברצף בעמוד אחד, בניקוד מלא", a, b, None,
             (f"/tehillim/{WD_SLUG[d-1]}/", wd_h1(d - 1)) if d else None, (f"/tehillim/{WD_SLUG[d+1]}/", wd_h1(d + 1)) if d < 6 else None, rel,
             f"החלק של יום {DAYS[d]} בחלוקת ספר תהילים לשבעת ימי השבוע: {rng(a, b)}, {n} פרקים ברצף.")

_half = 0
for d, (a, b) in enumerate(MONTHLY, 1):
    part, extra = None, ""
    if a == b == 119:
        _half += 1
        part = (0, 96, "אותיות א עד ל") if _half == 1 else (96, 176, "אותיות מ עד ת")
        extra = ", " + part[2]
    wds = sorted({week_day(c) for c in range(a, b + 1)})
    rel = [("/tehillim/yomi/", "תהילים יומי: החלוקה לימי החודש ולימי השבוע")] + [(f"/tehillim/{WD_SLUG[w]}/", wd_h1(w)) for w in wds] \
        + [(f"/tehillim/{k}/", need_h1(k)) for k in dict.fromkeys(k for c in range(a, b + 1) for k in NEED_OF.get(c, []))][:4] + [("/tehillim/", "כל 150 פרקי התהילים")]
    n = b - a + 1
    cnt = "פרק אחד" if n == 1 else f"{n} פרקים ברצף"
    day_page(f"/tehillim/chodesh-{d}/", md_h1(d), f"{md_h1(d)} ({d}): {rng(a, b)}{extra} | {BRAND}",
             f"{md_h1(d)} ({d} בחודש העברי) לפי החלוקה החודשית של הספר: {rng(a, b)}{extra}, בניקוד מלא", a, b, part,
             (f"/tehillim/chodesh-{d-1}/", md_h1(d - 1)) if d > 1 else None, (f"/tehillim/chodesh-{d+1}/", md_h1(d + 1)) if d < 30 else None, rel,
             f"החלק של יום {gem(d)} בחודש העברי בחלוקת ספר תהילים לשלושים יום: {rng(a, b)}{extra}, {cnt}.")

# ---------- daily and weekly division ----------
yomi = ('<p class="note">הסימון ״היום״ מחושב לפי התאריך האזרחי במכשיר שלכם. היום העברי מתחיל בערב שלפניו.</p>'
        '<div class="related"><a href="#chodesh">לפי ימי החודש</a><a href="#shavua">לפי ימי השבוע</a></div>')
yomi += '<h2 class="sec" id="chodesh">תהילים לפי ימי החודש</h2><ul class="sched">'
seen119 = 0
for d, (a, b) in enumerate(MONTHLY, 1):
    extra = ""
    if a == b == 119:
        seen119 += 1
        extra = "אותיות א עד ל" if seen119 == 1 else "אותיות מ עד ת"
    yomi += (f'<li id="d{d}"><b><a href="/tehillim/chodesh-{d}/">תהילים ליום {gem(d)} בחודש</a></b><span class="rng">{rng(a, b)}{", " + extra if extra else ""}</span><div class="chs">'
             + "".join(f'<a href="/tehillim/{c}/" title="תהילים פרק {gem(c)}">{gem(c)}</a>' for c in range(a, b + 1)) + "</div></li>")
yomi += '</ul><p class="note">בחודש שיש בו כ״ט ימים נוהגים לומר ביום כ״ט גם את הפרקים של יום ל.</p>'
yomi += '<h2 class="sec" id="shavua">תהילים לפי ימי השבוע</h2><ul class="sched">'
for d, (a, b) in enumerate(WEEKLY):
    yomi += (f'<li id="w{d}"><b><a href="/tehillim/{WD_SLUG[d]}/">תהילים ליום {DAYS[d]}</a></b><span class="rng">{rng(a, b)}</span><div class="more">'
             f'<a href="/tehillim/{WD_SLUG[d]}/">כל פרקי יום {DAYS[d]} ברצף</a><a href="/tehillim/{a}/">תהילים פרק {gem(a)}</a></div></li>')
yomi += "</ul>" + chips("עוד בתהילים", [("/tehillim/", "כל 150 פרקי התהילים"), ("/tehillim/#bakasha", "תהילים לפי בקשה"),
                                        ("/tehillim/tikkun/", "תיקון הכללי"), ("/tehillim/119/", "תהילים פרק קיט"),
                                        ("/tehillim/refuah/", "תהילים לרפואה שלמה"), ("/tehillim/neshama/", "תהילים לעילוי נשמה")]) + TOGETHER
page("/tehillim/yomi/", f"תהילים יומי: חלוקת התהילים לימי החודש ולימי השבוע | {BRAND}",
     "תהילים יומי: חלוקת ספר תהילים לפי יום בחודש ולפי ימי השבוע, מיום ראשון עד שבת. עמוד לכל יום עם הפרקים המלאים, וקישור לכל פרק בנפרד.",
     "תהילים יומי", [("תהילים", "/tehillim/"), ("תהילים יומי", "/tehillim/yomi/")], after=yomi, hub=True, prio="0.8",
     lead="חלוקת ספר תהילים לימי החודש העברי ולימי השבוע. מי שקורא כל יום את החלק של אותו יום מסיים את הספר פעם בחודש או פעם בשבוע.",
     script=JS_TODAY, app_hash="tehillim", app_label="לתהילים באפליקציה, עם החלק של היום",
     ld=[{"@type": "WebPage", "name": "תהילים יומי", "url": SITE + "/tehillim/yomi/", "inLanguage": "he", "isPartOf": WEBSITE, "about": BOOK_T}])

# ---------- Tehillim hub ----------
SEFARIM = [("ספר ראשון", 1, 41), ("ספר שני", 42, 72), ("ספר שלישי", 73, 89), ("ספר רביעי", 90, 106), ("ספר חמישי", 107, 150)]
POPULAR = [86, 84, 1, 20, 23, 130, 90, 100, 27, 30, 91, 121, 119, 13, 145, 142, 24, 16, 67, 51]
hub = '<h2 class="sec" style="margin-block-start:.5rem">הפרקים המבוקשים</h2><div class="related">' + "".join(
    f'<a href="/tehillim/{c}/">תהילים פרק {gem(c)}</a>' for c in POPULAR) + '</div><h2 class="sec">תהילים לפי פרקים: כל 150 הפרקים</h2>'
for name, a, b in SEFARIM:
    hub += (f'<h3 class="grp">{name}: {rng(a, b)}</h3><div class="grid">'
            + "".join(f'<a href="/tehillim/{c}/" title="תהילים פרק {gem(c)} ({c})">{gem(c)}</a>' for c in range(a, b + 1)) + "</div>")
hub += '<h2 class="sec" id="bakasha">תהילים לפי בקשה</h2><ul class="cards">'
for k, t, chs in NEEDS:
    hub += f'<li><a href="/tehillim/{k}/"><b>{esc(need_h1(k))}</b><small>פרקים {", ".join(gem(c) for c in chs)}</small></a></li>'
hub += "</ul>"
hub += ('<h2 class="sec" id="yomi">תהילים לפי יום</h2><div class="related">' + "".join(
    f'<a href="/tehillim/{WD_SLUG[d]}/">{wd_h1(d)}</a>' for d in range(7)) + '</div><div class="related" style="margin-block-start:.6rem">' + "".join(
    f'<a href="/tehillim/chodesh-{d}/" title="{md_h1(d)}">יום {gem(d)} בחודש</a>' for d in range(1, 31)) + "</div>")
hub += ('<h2 class="sec">סדר קריאה</h2><ul class="cards">'
        '<li><a href="/tehillim/yomi/"><b>תהילים יומי</b><small>החלוקה לימי החודש ולימי השבוע</small></a></li>'
        '<li><a href="/tehillim-yachad/"><b>תהילים יחד</b><small>כל אחד פרק. ביחד ספר שלם.</small></a></li>'
        '<li><a href="/kelim/"><b>כלים אישיים</b><small>תהילים לפי השם, פרק לפי גיל ועוד</small></a></li></ul>')
page("/tehillim/", f"ספר תהילים אונליין לפי פרקים: כל 150 הפרקים בניקוד מלא | {BRAND}",
     "ספר תהילים המלא אונליין בניקוד: כל 150 הפרקים, פרק בכל עמוד, תהילים לפי בקשה (לרפואה, לפרנסה, לעילוי נשמה), תיקון הכללי וחלוקה יומית.",
     "ספר תהילים", [("תהילים", "/tehillim/")], after=hub, app_hash="tehillim", hub=True, prio="0.9",
     lead="ספר תהילים המלא (תהלים): כל 150 הפרקים בניקוד מלא. בחרו פרק והתחילו לקרוא.",
     ld=[collection("ספר תהילים", "/tehillim/", [f"/tehillim/{c}/" for c in range(1, 151)])])

# =====================================================================
# Prayers
# =====================================================================
def siddur_of(n):
    return {"@type": "CreativeWork", "name": f"סידור תפילה, נוסח {NUS[n]}", "inLanguage": "he", "url": f"{SITE}/siddur/{n}/"}

PLAIN = json.loads(re.search(r"^const PLAIN=(\[.*\]);$", APP_SRC, re.M).group(1))
PLAIN_T = json.loads(re.search(r"^const PLAIN_T=(\{.*\});$", APP_SRC, re.M).group(1))
for n, plist in by_nus.items():
    for i, p in enumerate(plist):
        paras = TEXTS[n][p["id"]]
        # the source repeats the title as its first line; the page already has it as the h1
        _pl = lambda x: re.sub(r"[\s:.]+", "", re.sub(r"[\u0591-\u05BD\u05BF-\u05C7]", "", re.sub(r"<[^>]+>", "", x)))
        shown = paras[1:] if len(paras) > 1 and _pl(paras[0]) == _pl(p["t"]) else paras
        text = "".join(f"<p>{clean(x)}</p>" for x in shown)
        _px = next((x for r, x in PLAIN if re.search(r, p["t"])), "")
        plain_html = f'<aside class="plainx" aria-label="הסבר קצר"><b>על מה התפילה הזאת?</b><p>{esc(_px)}</p></aside>' if _px else ""
        assert plain(text), p["id"]
        me = f"{PURL[p['id']]}"
        prev = plist[i - 1] if i > 0 else None
        nxt = plist[i + 1] if i + 1 < len(plist) else None
        after = pager((f'{PURL[prev["id"]]}', prev["t"]) if prev else None, (f'{PURL[nxt["id"]]}', nxt["t"]) if nxt else None)
        same = SAME[p["id"]]
        switch = ""
        if same:
            after += chips("אותה תפילה בנוסח אחר", [(f'{PURL[q["id"]]}', f'{q["t"]} · נוסח {NUS[q["n"]]}') for q in same])
            switch = ('<nav class="nus" aria-label="אותה תפילה בנוסח אחר"><span>גם בנוסח</span>'
                      + "".join(f'<a href="{PURL[q["id"]]}">{esc(NUS[q["n"]])}</a>' for q in same) + "</nav>")
        s = sec_of(p)
        ctx = CTX.get(p["id"], "")
        lead_name, also = lead_of(p), also_of(p)
        sec_href, sec_label = section_link(p)

        # related: curated first, then the nearest prayers of the same section
        skip = {me} | {f'{PURL[q["id"]]}' for q in (prev, nxt) if q}
        full = [q for q in plist if sec_of(q) == s]
        grp = GROUPS[n][GROUP_OF[p["id"]]][1]
        cands = sorted(full, key=lambda q: abs(plist.index(q) - i)) + sorted(grp, key=lambda q: abs(plist.index(q) - i)) \
            + sorted(plist, key=lambda q: abs(plist.index(q) - i))[:12]
        extra = []
        for q in cands:
            h = f'{PURL[q["id"]]}'
            if h not in skip and norm_t(q["t"]) != norm_t(p["t"]):
                same_sec = sec_of(q) == s
                extra.append((h, q["t"] if same_sec or not sec_of(q) else f'{q["t"]} ({sec_of(q)[-1]})'))
        rel = fill([x for x in CUR.get(me, []) if x[0] not in skip][:6], extra, lo=5)
        if p["id"] in WANT_IDS and n in NUS_NOTE:
            other = next((q for q in same if q["n"] == NUS_NOTE[n][1]), None)
            after += nus_note(n, f'{PURL[other["id"]]}' if other else f"/siddur/{NUS_NOTE[n][1]}/",
                              f'{lead_of(other)} בנוסח {NUS[other["n"]]}' if other else f"סידור נוסח {NUS[NUS_NOTE[n][1]]}")
        after += chips("תפילות קשורות", rel)
        after += chips("בסידור", [(sec_href, f"{sec_label}: כל הסדר"), (f"/siddur/{n}/", f"סידור נוסח {NUS[n]}"), ("/siddur/", "כל הנוסחים")])

        tname = TNAME[p["id"]]
        where = ctx or " · ".join(s)
        if len(where) > 58:
            where = " · ".join(s[-2:]) + (" · " + ctx.rsplit(" · ", 1)[-1] if "חלק " in ctx.rsplit(" · ", 1)[-1] else "")
        alt = ALT_SPELL.get(p["t"], "")
        head = f"{lead_name} בנוסח {NUS[n]}" + (f" ({also or alt})" if also or alt else "") + (f", {where}" if where and p["id"] not in PRIMARY else "")
        when = CONTEXT_ID.get(p["id"]) or CONTEXT.get(p["t"]) or CONTEXT.get(norm_t(p["t"]))
        if when and len(head) + len(when) <= 96:
            head += ". " + when.rstrip(". ")
        meta = f'<b>נוסח {esc(NUS[n])}</b>' + (f' · <a href="{sec_href}">{esc(" · ".join(s))}</a>' if s and not ctx else "")
        # the heading uses the spelling people write; the spelling of the source is noted beside it
        h1_name = p["t"]
        if lead_name != p["t"] and p["t"] in SPELL:
            h1_name = lead_name
            meta += f" · בסידור נכתב: {esc(p['t'])}"
        if weekday_amida(p):
            h1_name = lead_name
        if p["id"] == "mizrach-11":
            h1_name = lead_name
            meta += f" · כותרת הקטע בסידור: {esc(p['t'])}"
        if also:
            meta += f" · נקראת גם {esc(also)}"
        if alt:
            meta += f" · נכתב גם: {esc(alt)}"
        before = f'<p class="note">{esc(when)}</p>' if when else ""
        if p["id"] == "mizrach-11":
            before += '<p class="note">זהו קטע הפתיחה בלבד. <a href="/siddur/mizrach/shacharit/">לסדר תפילת שחרית המלא, נוסח עדות המזרח</a></p>'
        if norm_t(p["t"]) == "תפילת הדרך":
            after = TD_BOX + after
        crumbs = [("סידור", "/siddur/"), (f"נוסח {NUS[n]}", f"/siddur/{n}/")]
        if p["id"] in SVC_OF:
            crumbs.append((sec_label, sec_href))
        crumbs.append((pname(p), me))
        _tt = f"{tname}: הנוסח המלא בניקוד | נוסח {NUS[n]} | {BRAND}"
        # where the same name opens two different editions, the title says which one this is
        if p["id"] == "sefard-32": _tt = f"פרק שירה המלא בניקוד: שירת הבריאה, עם מעקב 40 יום | {BRAND}"
        if len(_tt) > 62 and f"{tname} | נוסח {NUS[n]} | {BRAND}" not in TITLES: _tt = f"{tname} | נוסח {NUS[n]} | {BRAND}"
        if len(_tt) > 62 and CTX.get(p["id"]) and p["id"] not in PRIMARY:
            _parts = CTX[p["id"]].split(" · ")
            for _k in (2, 1, 3):
                _cand = f"{lead_of(p)} ({' · '.join(_parts[-_k:])}) | נוסח {NUS[n]} | {BRAND}"
                if len(_cand) <= 62 and _cand not in TITLES and len(_parts) >= _k:
                    _tt = _cand
                    break
        _open = []
        for x in shown[:8]:
            if re.fullmatch(r"\s*<big>.*?</big>\s*", x, re.S):
                continue                                   # a printed heading
            _m = re.fullmatch(r"\s*<small>(.*)</small>\s*", x, re.S)
            if _m and "<small>" not in _m.group(1) and (len(plain(x)) < 70 or (len(plain(x)) < 260 and re.search(r"יאמר|יקרא|אומרים|יטול|נוהגים|צריך ל|יש להפסיק|אומר ", plain(x)))):
                continue                                   # a printed instruction
            x = re.sub(r"<small>(.*?)</small>", lambda m: " " if len(plain(m.group(1))) < 60 else m.group(0), x, flags=re.S)
            if len(plain(x)) > 3:
                _open.append(x)
        _desc = fit_desc(head, " ".join(_open[:3]) if _open else " ".join(paras[:3]))
        if p["id"] == "sefard-32":
            _desc = "פרק שירה המלא בניקוד, עם ההקדמה ”תניא רבי אליעזר הגדול”: שירת השמים והארץ, הצמחים, העופות ובעלי החיים. עם מעקב 40 יום למי שנוהג לומר אותו ברצף."
            meta += ' · <a href="#maakav">מעקב 40 יום</a>'
            # the six chapter lines of the source become headings one can jump to; their words are the source's own
            _pk = []
            def _pkh(m):
                _pk.append(m.group(1).strip())
                return f'<h2 id="perek-{len(_pk)}">{_pk[-1]}</h2>'
            text = re.sub(r"<p>(?:<small>\s*)?<b>(פרק [^<]+?)\s*</b>(?:</small>)?</p>", _pkh, text)
            assert len(_pk) == 6, _pk
            before += ('<div class="related jr" style="margin-block-end:1rem">' + "".join(f'<a href="#perek-{i + 1}">{esc(h)}</a>' for i, h in enumerate(_pk))
                       + '<a href="#bakasha">בקשה לאחר פרק שירה</a><a href="#maakav">מעקב 40 יום</a></div>')
            _t40, _t40js = track40("perek40", "מסמנים כל יום שבו קראתם את פרק שירה.")
            after = _t40 + PEREK40_NOTE + after
            after = chips("מהדורה נוספת", [("/sefer/perek/", "פרק שירה לפי פרקים, עם מקורות הפסוקים והבקשה שאחריו")]) + after
            # the request said after Perek Shira, from the book edition (data/books.json), with the place for a personal request marked
            _ask = next(s for s in B["perek"]["secs"] if "בקשה" in s["h"])
            assert len(_ask["v"]) == 3 and "כאן יוסיף" in plain(_ask["v"][2]), "the request changed: look at the page again"
            text += f'<h2 id="bakasha">{esc(_ask["h"])}</h2>' + "".join(
                "<p>" + re.sub(r"<small>\(([^<]*)\)</small>", r'<mark class="pask">(\1)</mark>', clean(x), count=1 if i else 0) + "</p>" for i, x in enumerate(_ask["v"][1:]))
        if p["t"].startswith(("קדיש", "חצי קדיש")):
            after = chips("קדיש", [("/kaddish/", "כל סוגי הקדיש בעמוד אחד")]) + after
        if p["id"] == "ashkenaz-264":
            _nl = [("/nishmat-kol-chai/mizrach/", "mizrach"), ("/nishmat-kol-chai/sefard/", "sefard")]
            switch = '<nav class="nus" aria-label="אותה תפילה בנוסח אחר"><span>גם בנוסח</span>' + "".join(f'<a href="{h}">{esc(NUS[m])}</a>' for h, m in _nl) + "</nav>"
            after = chips("אותה תפילה בנוסח אחר", [(h, f"נשמת כל חי · נוסח {NUS[m]}") for h, m in _nl]) + after
        if p["id"] == "ashkenaz-28":
            assert len(shown) == 2 and shown[0].startswith("<small>") and "מִזְמוֹר לְתוֹדָה" in shown[1], "the entry changed: look at the page again"
            text = f"<p>{clean(shown[1])}</p>"
            _tt = f"מזמור לתודה (תהילים ק): המזמור המלא בניקוד | {BRAND}"
            _desc = "מזמור לתודה, תהילים פרק ק, בניקוד מלא: ”הריעו לה׳ כל הארץ, עבדו את ה׳ בשמחה”. נאמר בפסוקי דזמרה של ימי חול. לקריאה בנייד, להדפסה ולשיתוף."
            meta = '<a href="/tehillim/100/">תהילים פרק ק</a> · נאמר בפסוקי דזמרה של ימי חול'
            crumbs = [("ספר תהילים", "/tehillim/"), (p["t"], me)]
            ctx, switch = "", ""
            after = ('<div class="prose"><h2 class="sec">מתי אומרים את המזמור</h2><p>' + plain(clean(shown[0])) + '</p><p><small>מתוך הוראות הסידור (נוסח אשכנז).</small></p></div>'
                     + chips("עוד מזמורים", [("/tehillim/100/", "תהילים פרק ק, עם הפרקים שלפניו ואחריו"), ("/tehillim/hodaya/", "תהילים להודיה"), ("/tehillim/", "ספר תהילים")]) + after)
        if norm_t(p["t"]) == "תפילת הדרך":
            _desc = f"תפילת הדרך המלאה בניקוד, בנוסח {NUS[n]}, לקריאה נוחה בנייד. נאמרת ביציאה לדרך אל מחוץ לעיר. בעמוד: הנוסח המלא, הסבר קצר, ומתי אומרים אותה בברכה."
        page(me, _tt, _desc,
             h1_name, crumbs, text=text, meta=meta, before=plain_html + before, h1_ctx=ctx, ctx_out=True, bar_extra=switch, after=after, app_hash=f"p-{p['id']}",
             canon_to=PURL[DUP_OF[p["id"]]] if p["id"] in DUP_OF else "", script=_t40js if p["id"] == "sefard-32" else "",
             ld=[{"@type": "CreativeWork", "name": pname(p), "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me, "isPartOf": siddur_of(n)}])

# ---------- service pages ----------
def opening(p):
    return snippet(" ".join(TEXTS[p["n"]][p["id"]][:2]), 64)

for n in NUS:
    for si, (key, label, cfg) in enumerate(SERVICES):
        items = SVC[(n, key)]
        name = svc_name(n, key)
        path = f"/siddur/{n}/{key}/"
        first = items[0][0]
        body = ""
        full = ""
        cur, opened, num = None, False, 0
        for p, pre in items:
            s = sec_of(p)
            lab = " · ".join(s[len(pre):]) or s[-1]
            if lab == "עמידה" and s[0] == "ימי חול":
                lab = "תפילת שמונה עשרה"
            _nm = lead_of(p) if weekday_amida(p) else p["t"]
            if lab != cur:
                if opened: body += "</ol>"
                body += f'<h3 class="grp">{esc(lab)}</h3><ol class="toc">'
                cur, opened = lab, True
            num += 1
            body += f'<li><a href="#k{num}"><i>{num}</i><span><b>{esc(_nm)}</b><small>{esc(opening(p))}</small></span></a></li>'
            _ps = TEXTS[n][p["id"]]
            _sh = _ps[1:] if len(_ps) > 1 and _pl(_ps[0]) == _pl(p["t"]) else _ps
            full += f'<h2 id="k{num}">{esc(_nm)}</h2>' + "".join(f"<p>{clean(x)}</p>" for x in _sh)
        body += "</ol>"
        toc_html = '<details class="svctoc"><summary>תוכן התפילה</summary>' + body + "</details>"
        body = ""
        pv = SERVICES[si - 1] if si else None
        nx = SERVICES[si + 1] if si + 1 < len(SERVICES) else None
        body += pager((f"/siddur/{n}/{pv[0]}/", svc_name(n, pv[0])) if pv else None, (f"/siddur/{n}/{nx[0]}/", svc_name(n, nx[0])) if nx else None)
        body += nus_note(n, f"/siddur/{NUS_NOTE[n][1]}/{key}/", f"{svc_name(NUS_NOTE[n][1], key)} בנוסח {NUS[NUS_NOTE[n][1]]}") if n in NUS_NOTE else ""
        body += chips(f"{label} בנוסח אחר", [(f"/siddur/{m}/{key}/", f"{svc_name(m, key)} · נוסח {NUS[m]}") for m in NUS if m != n])
        relp = [by_title(n, t) for t in ("ברכת המזון", "תפילת הדרך", "קריאת שמע על המיטה", "ספירת העומר")]
        body += chips("עוד בסידור", [(f"/siddur/{n}/", f"סידור נוסח {NUS[n]}, כל התפילות")]
                      + [(f'{PURL[q["id"]]}', lead_of(q)) for q in relp if q and q["id"] not in {x[0]["id"] for x in items}]
                      + [("/tehillim/", "ספר תהילים")])
        parts = "חלק אחד" if num == 1 else f"{num} חלקים"
        desc = fit_desc(f"תפילת {name} בנוסח {NUS[n]}: סדר התפילה המלא לפי הסדר, {parts}, מ{plain(items[0][0]['t'])} ועד {plain(items[-1][0]['t'])}. כל התפילה בעמוד אחד משלו, בניקוד מלא",
                        tails=("קריאה נוחה בנייד.",))
        page(path, f"תפילת {name} נוסח {NUS[n]}: הסדר המלא | {BRAND}", desc, f"תפילת {name}",
             [("סידור", "/siddur/"), (f"נוסח {NUS[n]}", f"/siddur/{n}/"), (name, path)],
             h1_ctx=f"נוסח {NUS[n]}", text=full, before=toc_html, after=body, hub=False, prio="0.9", app_hash=f"p-{first['id']}", app_label="לתפילה באפליקציה, עם התאמות לפי היום",
             lead=f"תפילת {label} של ימי החול בנוסח {NUS[n]}, כולה בעמוד אחד ובניקוד מלא. {parts}, לפי הסדר.",
             ld=[collection(f"{name}, נוסח {NUS[n]}", path, [f'{PURL[p["id"]]}' for p, _ in items])])

# ---------- most wanted (shared by the hubs) ----------
WANT_REPORT = []
def want_block(only=None):
    out = '<ul class="want">'
    for key, label, _ in SERVICES:
        links = "".join(f'<a href="/siddur/{n}/{key}/" title="{esc(svc_name(n, key))} בנוסח {esc(NUS[n])}">נוסח {esc(NUS[n])}</a>' for n in NUS if only in (None, n))
        out += f'<li><b>{esc(label)} לימי חול</b><span>{links}</span></li>'
    for label, titles in WANT:
        links = ""
        for n in NUS:
            q = by_title(n, *titles)
            if only is None:
                WANT_REPORT.append((label, n, q["id"] if q else None, q["t"] if q else None))
            if q and only in (None, n):
                links += f'<a href="{PURL[q["id"]]}" title="{esc(label)} בנוסח {esc(NUS[n])}: {esc(pname(q))}">{"נוסח " + esc(NUS[n]) if only is None else "לתפילה"}</a>'
        if links:
            out += f'<li><b>{esc(label)}</b><span>{links}</span></li>'
    for n in NUS:   # whole sections that people look for by name
        for gi, (lab, ps) in enumerate(GROUPS[n]):
            if lab == "הגדה של פסח" and only in (None, n):
                out += f'<li><b>הגדה של פסח</b><span><a href="/siddur/{n}/#g{gi + 1}" title="הגדה של פסח בנוסח {esc(NUS[n])}, {len(ps)} חלקים">{"נוסח " + esc(NUS[n]) if only is None else "לסדר ההגדה"}</a></span></li>'
    return out + "</ul>"

def nusach_lists(n, hlevel, prefix):
    out = ""
    for gi, (lab, ps) in enumerate(GROUPS[n]):
        out += f'<{hlevel} class="grp" id="{prefix}{gi + 1}">{esc(lab)}</{hlevel}><ul class="list">'
        out += "".join(f'<li><a href="{PURL[p["id"]]}">{esc(lead_of(p) if weekday_amida(p) else p["t"])}</a></li>' for p in ps) + "</ul>"
    return out

# ---------- nusach hubs ----------
for n in NUS:
    path = f"/siddur/{n}/"
    body = (nus_note(n, f"/siddur/{NUS_NOTE[n][1]}/", f"סידור נוסח {NUS[NUS_NOTE[n][1]]}") if n in NUS_NOTE else "")
    body += '<h2 class="sec">תפילות ימי החול</h2><ul class="cards">'
    for key, label, _ in SERVICES:
        items = SVC[(n, key)]
        body += f'<li><a href="/siddur/{n}/{key}/"><b>{esc(svc_name(n, key))}</b><small>{len(items)} חלקים, מ{esc(items[0][0]["t"])} ועד {esc(items[-1][0]["t"])}</small></a></li>'
    body += '</ul><h2 class="sec" id="mevukashot">התפילות המבוקשות</h2>' + want_block(n)
    body += chips("הסידור בנוסח אחר", [(f"/siddur/{m}/", f"סידור נוסח {NUS[m]}") for m in NUS if m != n])
    body += f'<h2 class="sec big" id="kol">כל התפילות בנוסח {esc(NUS[n])}</h2>' + nusach_lists(n, "h3", "g")
    cnt = len(by_nus[n])
    page(path, f"סידור נוסח {NUS[n]} אונליין: כל התפילות בניקוד מלא | {BRAND}",
         fit_desc(f"סידור תפילה בנוסח {NUS[n]}, {cnt} תפילות וברכות בניקוד מלא: שחרית, מנחה וערבית לימי חול, שבת, ראש חודש וחגים, ברכת המזון, תפילת הדרך וקריאת שמע שעל המיטה", tails=()),
         f"סידור נוסח {NUS[n]}", [("סידור", "/siddur/"), (f"נוסח {NUS[n]}", path)], after=body, hub=True, prio="0.9",
         app_hash="siddur", app_label="לסידור באפליקציה",
         lead=f"{cnt} תפילות וברכות בנוסח {NUS[n]}, בניקוד מלא. כל תפילה בעמוד קריאה משלה.",
         ld=[collection(f"סידור נוסח {NUS[n]}", path, [f"/siddur/{n}/{k}/" for k, _, _ in SERVICES] + [f'{PURL[p["id"]]}' for p in by_nus[n]])])

# ---------- siddur hub ----------
hub = '<ul class="cards">' + "".join(
    f'<li><a href="/siddur/{n}/"><b>נוסח {esc(NUS[n])}</b><small>{len(by_nus[n])} תפילות וברכות, שחרית, מנחה וערבית</small></a></li>' for n in NUS) + "</ul>"
hub += '<h2 class="sec" id="mevukashot">התפילות המבוקשות</h2>' + want_block()
hub += '<h2 class="sec">כל התפילות לפי נוסח</h2><div class="related">' + "".join(f'<a href="#{n}">נוסח {esc(NUS[n])}</a>' for n in NUS) + "</div>"
for n in NUS:
    hub += f'<h2 class="sec big" id="{n}"><a href="/siddur/{n}/">נוסח {esc(NUS[n])}</a></h2>' + nusach_lists(n, "h3", n + "-g")
page("/siddur/", f"סידור תפילה אונליין | עדות המזרח, ספרד ואשכנז | {BRAND}",
     "סידור תפילה מלא אונליין בניקוד, בלי פרסומות: שחרית, מנחה, ערבית, ברכת המזון, תפילת הדרך, שבת וחגים, בנוסח עדות המזרח, ספרד ואשכנז.",
     "סידור תפילה", [("סידור", "/siddur/")], after=hub, app_hash="siddur", hub=True, prio="0.9",
     lead="כל התפילות בשלושה נוסחים, בניקוד מלא. כל תפילה בעמוד קריאה משלה.",
     ld=[collection("סידור תפילה", "/siddur/", [f"/siddur/{n}/" for n in NUS])])

# =====================================================================
# Library
# =====================================================================
PLAIN_B = json.loads(re.search(r"^const PLAIN_B=(\{.*\});$", APP_SRC, re.M).group(1))
BOOK_ART = {"perek": ["שמים וארץ", "יום ולילה", "עצים וצמחים", "עופות", "בהמות וחיות", "שרצים ורמשים"]}
for bi, (k, b) in enumerate(B.items()):
    text = ""
    b = dict(b, secs=[s for s in b["secs"] if s.get("v")])  # a heading with no text under it is not shown
    for j, s in enumerate(b["secs"]):
        _art = BOOK_ART.get(k, [])
        if s.get("h"): text += f'<h2 id="s{j+1}">{esc(s["h"])}{(": " + esc(_art[j])) if j < len(_art) else ""}</h2>'
        text += "".join(f'<p>{f"<sup>{gem(i+1)}</sup>" if b.get("num") else ""}{clean(v)}</p>' for i, v in enumerate(s["v"]))
    me = f"/sefer/{k}/"
    pk = BOOK_KEYS[bi - 1] if bi else None
    nk = BOOK_KEYS[bi + 1] if bi + 1 < len(BOOK_KEYS) else None
    after = pager((f"/sefer/{pk}/", B[pk]["t"]) if pk else None, (f"/sefer/{nk}/", B[nk]["t"]) if nk else None)
    near = [BOOK_KEYS[x] for x in (bi - 2, bi + 2, bi - 3, bi + 3, bi - 4, bi + 4) if 0 <= x < len(BOOK_KEYS)]
    rel = fill(CUR.get(me, [])[:6], [(f"/sefer/{x}/", B[x]["t"]) for x in near], lo=5)
    after += chips("קשור לעמוד הזה", rel)
    after += chips("עוד בספרייה", [("/sefer/", "כל ספרי הספרייה"), ("/tehillim/", "ספר תהילים"), ("/siddur/", "סידור תפילה")])
    sub = b.get("sub", "")
    nsec = len([s for s in b["secs"] if s.get("h")])
    jump = ('<div class="related jr" style="margin-block-end:1rem">' + "".join(
        f'<a href="#s{j+1}">{esc(s["h"])}</a>' for j, s in enumerate(b["secs"]) if s.get("h")) + "</div>") if nsec > 1 else ""
    first_v = " ".join(b["secs"][0]["v"][:3])
    _bx = PLAIN_B.get(k, "")
    jump = (f'<aside class="plainx" aria-label="הסבר קצר"><b>על מה {esc(b["t"])}?</b><p>{esc(_bx)}</p></aside>' if _bx else "") + jump
    if k == "perek":
        after = chips("מהדורה נוספת", [(PURL["sefard-32"], "פרק שירה עם ההקדמה ”תניא רבי אליעזר”, כפי שנדפס בסידור")]) + after
    page(me, (f"פרק שירה לפי פרקים, עם מקורות הפסוקים | {BRAND}" if k == "perek" else f"{b['t']} | הנוסח המלא בניקוד | {BRAND}"),
         ("פרק שירה מחולק לשישה פרקים, עם מקור כל פסוק ועם הבקשה שאומרים אחרי הקריאה. מהדורת תורת אמת בניקוד מלא, בעמוד אחד. ההקדמה ”תניא רבי אליעזר” בפרק שירה שבסידור." if k == "perek" else "") or
         fit_desc(f"{b['t']} בניקוד מלא אונליין" + (f". {plain(sub)}" if sub else "") + (f". {nsec} פרקים בעמוד אחד" if nsec > 1 else ""), first_v),
         b["t"], [("ספרייה", "/sefer/"), (b["t"], me)],
         text=text, meta=esc(sub), before=jump, after=after, app_hash=f"b-{k}",
         ld=[{"@type": "Book" if nsec > 1 else "CreativeWork", "name": b["t"], "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me}])
# ---------- the weekly Torah portion: one page per portion, the full text divided into its seven aliyot ----------
# Text: "Tanach with Nikkud" (public domain, tanach.us), stored untouched in data/torah.json by tools/get-torah.py.
TORAH = json.load(open(os.path.join(DATA, "torah.json"), encoding="utf-8"))["books"]
PARASHOT = json.load(open(os.path.join(ROOT, "tools", "parashot.json"), encoding="utf-8"))
CHUMASH = {"Genesis": "בראשית", "Exodus": "שמות", "Leviticus": "ויקרא", "Numbers": "במדבר", "Deuteronomy": "דברים"}
NAVI = {"Isaiah": "ישעיהו", "Jeremiah": "ירמיהו", "Ezekiel": "יחזקאל", "Hosea": "הושע", "Joel": "יואל", "Amos": "עמוס", "Obadiah": "עובדיה", "Jonah": "יונה", "Micah": "מיכה",
        "Zechariah": "זכריה", "Malachi": "מלאכי", "Joshua": "יהושע", "Judges": "שופטים", "I Samuel": "שמואל א", "II Samuel": "שמואל ב", "I Kings": "מלכים א", "II Kings": "מלכים ב"}
ALIYA = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שביעי"]
# the source spells some names the way the verse does; the page titles use the spelling people type
_PNAME = {"תצוה": "תצווה", "מצרע": "מצורע", "קדשים": "קדושים", "בחקתי": "בחוקותי", "בהעלתך": "בהעלותך", "חקת": "חוקת", "פינחס": "פנחס", "נצבים": "ניצבים"}
for _p in PARASHOT:
    _p["he"] = _PNAME.get(_p["he"], _p["he"])
par_slug = lambda p: re.sub(r"[^a-z]+", "-", p["key"].lower().replace("'", "")).strip("-")
PAR_PATH = {p["num"]: f"/parasha/{par_slug(p)}/" for p in PARASHOT}
assert len(set(PAR_PATH.values())) == 54


def _ref(c, v):
    return f"{gem(c)}, {gem(v)}"


def _haft(h):
    """one reading, or several ranges: the reference only (the text of the haftarot is not on the site yet)"""
    if not h:
        return ""
    hs = h if isinstance(h, list) else [h]
    out = []
    for x in hs:
        (c1, v1), (c2, v2) = (map(int, x["b"].split(":")), map(int, x["e"].split(":")))
        out.append(f'{NAVI[x["k"]]} {_ref(c1, v1)} עד {_ref(c2, v2) if c1 != c2 else gem(v2)}')
    return "; ".join(out)


def _verses(book, c1, v1, c2, v2):
    out, n = "", 0
    for c in range(c1, c2 + 1):
        ch = TORAH[book][c - 1]
        lo = v1 if c == c1 else 1
        hi = v2 if c == c2 else len(ch)
        if lo == 1 or c == c1:
            out += f'<p class="perek">פרק {gem(c)}</p>'
        for v in range(lo, hi + 1):
            out += f"<p><sup>{gem(v)}</sup>{esc(ch[v - 1])}</p>"
            n += 1
    return out, n


for bi, p in enumerate(PARASHOT):
    me, book, he = PAR_PATH[p["num"]], p["book"], p["he"]
    text, total, jump = "", 0, ""
    for ai, (c1, v1, c2, v2) in enumerate(p["aliyot"]):
        body, n = _verses(book, c1, v1, c2, v2)
        total += n
        text += f'<h2 id="a{ai + 1}">{ALIYA[ai]} <small>{CHUMASH[book]} {_ref(c1, v1)}</small></h2>' + body
        jump += f'<a href="#a{ai + 1}">{ALIYA[ai]}</a>'
    c1, v1 = p["aliyot"][0][:2]
    c2, v2 = p["aliyot"][-1][2:]
    rng = f"{CHUMASH[book]} {_ref(c1, v1)} עד {_ref(c2, v2)}"
    ha, hs = _haft(p.get("haft")), _haft(p.get("seph"))
    haft = ("הפטרה: " + (f"{ha} (אשכנזים), {hs} (ספרדים)" if hs and hs != ha else ha)) if ha else ""
    prev = PARASHOT[bi - 1] if bi else None
    nxt = PARASHOT[bi + 1] if bi + 1 < len(PARASHOT) else None
    after = pager((PAR_PATH[prev["num"]], "פרשת " + prev["he"]) if prev else None, (PAR_PATH[nxt["num"]], "פרשת " + nxt["he"]) if nxt else None)
    same = [q for q in PARASHOT if q["book"] == book and q["num"] != p["num"]]
    near = sorted(same, key=lambda q: abs(q["num"] - p["num"]))[:6]
    after += chips(f"עוד בחומש {CHUMASH[book]}", [(PAR_PATH[q["num"]], "פרשת " + q["he"]) for q in sorted(near, key=lambda q: q["num"])])
    after += chips("עוד באתר", [("/parasha/", "כל פרשות השבוע"), ("/zmanei-shabbat/", "זמני כניסת ויציאת שבת"), ("/tehillim/", "ספר תהילים"), ("/siddur/", "סידור תפילה")])
    first = TORAH[book][c1 - 1][v1 - 1]
    before = (f'<p class="note">{esc(rng)}. {total} פסוקים, בשבע עליות.' + (f" {esc(haft)}." if haft else "") + "</p>"
              f'<div class="related jr" style="margin-block-end:1rem">{jump}</div>')
    page(me, f"פרשת {he}: הטקסט המלא בניקוד, לפי עליות | {BRAND}",
         fit_desc(f"פרשת {he} בניקוד מלא, מחולקת לשבע העליות. {rng}, {total} פסוקים", first, tails=("לקריאה נוחה בנייד ולהדפסה.",)),
         f"פרשת {he}", [("פרשת השבוע", "/parasha/"), (f"פרשת {he}", me)], text=text, meta=f"חומש {CHUMASH[book]} · {esc(rng)}", before=before, after=after, prio="0.8",
         ld=[{"@type": "Chapter", "name": f"פרשת {he}", "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me,
              "isPartOf": {"@type": "Book", "name": "חמישה חומשי תורה", "inLanguage": "he"}}])

_plist = ""
for en, he in CHUMASH.items():
    _plist += f'<h2 class="sec">חומש {he}</h2><ul class="list">' + "".join(
        f'<li><a href="{PAR_PATH[p["num"]]}">פרשת {esc(p["he"])}<small>{he} {_ref(*p["aliyot"][0][:2])}</small></a></li>' for p in PARASHOT if p["book"] == en) + "</ul>"
PWEEK_JS = ("(function(){var M=" + json.dumps({p["key"]: [p["he"], PAR_PATH[p["num"]]] for p in PARASHOT}, ensure_ascii=False, separators=(",", ":")) + ";"
            "var s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/@hebcal/core@6.14.5/dist/bundle.min.js';"
            "s.onload=function(){try{var H=window.hebcal,box=document.getElementById('pweek'),d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+((6-d.getDay()+7)%7));"
            "var p=H.HebrewCalendar.calendar({start:d,end:d,sedrot:true,il:true}).filter(function(e){return e.getFlags()&H.flags.PARSHA_HASHAVUA})[0],"
            "date=d.toLocaleDateString('he-IL',{day:'numeric',month:'long'});"
            "if(!p){box.textContent='בשבת הקרובה, '+date+', אין פרשת שבוע רגילה לפי הלוח.';return}"
            "var L=(p.parsha||[]).filter(function(k){return M[k]});if(!L.length||L.length!==p.parsha.length)return;"
            "box.innerHTML='<b>פרשת השבוע:</b> '+L.map(function(k){return '<a href=\"'+M[k][1]+'\">פרשת '+M[k][0]+'</a>'}).join(' ו')"
            "+'<small>שבת, '+date+' · לפי לוח ארץ ישראל</small>'}catch(e){}};document.head.appendChild(s)})()")
page("/parasha/", f"פרשת השבוע: כל 54 הפרשות בניקוד מלא, לפי עליות | {BRAND}",
     "פרשת השבוע אונליין: כל 54 פרשות התורה, מבראשית ועד וזאת הברכה, בניקוד מלא ומחולקות לשבע העליות. לכל פרשה עמוד קריאה משלו, עם מראה המקום של ההפטרה.",
     "פרשת השבוע", [("פרשת השבוע", "/parasha/")],
     after=_plist + chips("עוד באתר", [("/zmanei-shabbat/", "זמני כניסת ויציאת שבת"), ("/tehillim/", "ספר תהילים"), ("/siddur/", "סידור תפילה"), ("/sefer/", "ספרייה")]),
     hub=True, prio="0.9", lead="חמישה חומשי תורה לפי סדר הפרשות. כל פרשה בניקוד מלא, מחולקת לשבע העליות.", script=PWEEK_JS,
     before='<p class="pweek" id="pweek" aria-live="polite"></p>',
     ld=[collection("פרשת השבוע", "/parasha/", list(PAR_PATH.values()))])

# ---------- נשמת כל חי in the other two nusachim ----------
# Only the Ashkenaz siddur holds it as an entry of its own. In the other two it sits inside the Shabbat morning service,
# so its page is cut from there: from "נשמת כל חי" up to, and not including, the passage that quotes "רננו צדיקים".
# Nothing is rewritten; the asserts stop the build if the siddur entry ever changes under the cut.
NISHMAT = {"mizrach": ("mizrach-57", 19, 22), "sefard": ("sefard-102", 89, 90)}
_n_px = next(x for r, x in PLAIN if re.search(r, "נשמת כל חי"))
_n_all = [("ashkenaz", "/nishmat-kol-chai/")] + [(n, f"/nishmat-kol-chai/{n}/") for n in NISHMAT]
for n, (pid, lo, hi) in NISHMAT.items():
    _src = TEXTS[n][pid]
    assert plain(_src[lo]).startswith("נשמת כל חי") and "רננו צדיקים" not in plain(" ".join(_src[lo:hi])) and "רננו צדיקים" in plain(" ".join(_src[hi:hi + 8])), n
    me = f"/nishmat-kol-chai/{n}/"
    _svc = PURL[pid]
    page(me, f"נשמת כל חי: הנוסח המלא בניקוד | נוסח {NUS[n]} | {BRAND}",
         fit_desc(f"נשמת כל חי בנוסח {NUS[n]}, בניקוד מלא. נאמרת בתפילת שחרית של שבת ויום טוב", " ".join(_src[lo:lo + 1])),
         "נשמת כל חי", [("סידור", "/siddur/"), (f"נוסח {NUS[n]}", f"/siddur/{n}/"), ("נשמת כל חי", me)],
         text="".join(f"<p>{clean(x)}</p>" for x in _src[lo:hi]),
         meta=f'<b>נוסח {esc(NUS[n])}</b> · מתוך <a href="{_svc}">פסוקי דזמרה של שבת</a>',
         before=f'<aside class="plainx" aria-label="הסבר קצר"><b>על מה התפילה הזאת?</b><p>{esc(_n_px)}</p></aside><p class="note">נאמרת בתפילת שחרית של שבת ויום טוב.</p>',
         bar_extra='<nav class="nus" aria-label="אותה תפילה בנוסח אחר"><span>גם בנוסח</span>' + "".join(f'<a href="{h}">{esc(NUS[m])}</a>' for m, h in _n_all if m != n) + "</nav>",
         after='<div class="prose"><p><small>בסידור התפילה ממשיכה מכאן עד ברכת ”ישתבח”. הנוסח המלא נמצא בתוך סדר התפילה.</small></p></div>'
               + chips("להמשך התפילה", [(_svc, f"פסוקי דזמרה של שבת · נוסח {NUS[n]}")])
               + chips("אותה תפילה בנוסח אחר", [(h, f"נשמת כל חי · נוסח {NUS[m]}") for m, h in _n_all if m != n]),
         app_hash=f"p-{pid}", app_label="לתפילה המלאה באפליקציה",
         ld=[{"@type": "CreativeWork", "name": "נשמת כל חי", "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me, "isPartOf": siddur_of(n)}])

# ---------- Kaddish in the other two nusachim ----------
# Only the Ashkenaz siddur holds the Kaddish as entries of their own. In the other two it is printed inside the services,
# so each page here is cut from one place where the siddur prints it in full: from "יתגדל ויתקדש" through the last
# paragraph that still belongs to the Kaddish. Nothing is rewritten; the asserts stop the build if the entry changes.
_KD_PARTS = ("יהא שמה", "יהא שמיה", "יתברך", "לעלא", "על ישראל", "תתקבל", "יהא שלמא", "עושה שלום")
KD_CUT = {   # slug: (name in the title, {nusach: (entry, index of "יתגדל", the paragraph the Kaddish must reach)})
    "chatzi-kaddish": ("חצי קדיש", {"mizrach": ("mizrach-14", 22, ""), "sefard": ("sefard-12", 5, "")}),
    "kaddish-yatom": ("קדיש יתום", {"mizrach": ("mizrach-22", 28, "יהא שלמא"), "sefard": ("sefard-39", 106, "עושה שלום")}),
    "kaddish-shalem": ("קדיש שלם (תתקבל)", {"mizrach": ("mizrach-20", 4, "עושה שלום"), "sefard": ("sefard-36", 18, "עושה שלום")}),
    "kaddish-derabanan": ("קדיש דרבנן (על ישראל)", {"mizrach": ("mizrach-36", 20, "יהא שלמא"), "sefard": ("sefard-24", 12, "עושה שלום")}),
}
KD_NOTE = {("kaddish-yatom", "mizrach"): "בסידור עדות המזרח הקדיש הזה נקרא קדיש ”יהא שלמא”."}
KD_PAGES = {}
for _slug, (_name, _by) in KD_CUT.items():
    for n, (pid, lo, must) in _by.items():
        _src = TEXTS[n][pid]
        assert plain(_src[lo]).startswith("יתגדל ויתקדש"), (pid, lo)
        hi = lo + 1
        while hi < len(_src) and plain(_src[hi]).startswith(_KD_PARTS) and hi - lo < 8:
            hi += 1
        _body = plain(" ".join(_src[lo:hi]))
        assert "ואמרו אמן" in _body and (not must or must in _body), (pid, lo, hi)
        if _slug == "chatzi-kaddish":
            assert "יהא שלמא" not in _body and "תתקבל" not in _body, pid
        KD_PAGES[(_slug, n)] = (f"/{_slug}/{n}/", _name, pid, lo, hi)
for (_slug, n), (me, _name, pid, lo, hi) in KD_PAGES.items():
    _src = TEXTS[n][pid]
    _others = [(KD_PAGES[(_slug, m)][0], m) for m in NISHMAT if m != n and (_slug, m) in KD_PAGES]
    _nt = KD_NOTE.get((_slug, n), "")
    page(me, f"{_name}: הנוסח המלא בניקוד | נוסח {NUS[n]} | {BRAND}",
         fit_desc(f"{_name} בנוסח {NUS[n]}, בניקוד מלא", " ".join(_src[lo:lo + 1])),
         _name.split(" (")[0], [("סידור", "/siddur/"), ("קדיש", "/kaddish/"), (f"נוסח {NUS[n]}", me)],
         text="".join(f"<p>{clean(x)}</p>" for x in _src[lo:hi]),
         meta=f'<b>נוסח {esc(NUS[n])}</b> · מתוך <a href="{PURL[pid]}">{esc(BYID[pid]["t"])}</a>',
         before=(f'<p class="note">{esc(_nt)}</p>' if _nt else "") + ('<p class="note">נאמר על ידי האבלים, במניין.</p>' if _slug == "kaddish-yatom" else ""),
         bar_extra='<nav class="nus" aria-label="אותו קדיש בנוסח אחר"><span>גם בנוסח</span>' + "".join(f'<a href="{h}">{esc(NUS[m])}</a>' for h, m in _others) + "</nav>" if _others else "",
         after=chips("קדיש", [("/kaddish/", "כל סוגי הקדיש בעמוד אחד")]) + chips("בתוך סדר התפילה", [(PURL[pid], f'{BYID[pid]["t"]} · נוסח {NUS[n]}')]),
         app_hash=f"p-{pid}", app_label="לתפילה המלאה באפליקציה",
         ld=[{"@type": "CreativeWork", "name": _name, "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me, "isPartOf": siddur_of(n)}])

# ---------- kaddish: one page that names every kind and points to its text ----------
_kd = [("קדיש יתום", "נאמר על ידי האבלים, במניין."), ("חצי קדיש", ""), ("קדיש שלם", ""), ("קדיש דרבנן", ""), ("קדיש דאתחדתא", ""), ("קדיש אחר השלמת מסכת", "")]
_kd_items = [(t, note, next((p for p in by_nus["ashkenaz"] if p["t"] == t and p["id"] in PRIMARY), None) or next(p for p in by_nus["ashkenaz"] if p["t"] == t and p["id"] not in DUP_OF)) for t, note in _kd]
_kd_html = '<ul class="list">' + "".join(f'<li><a href="{PURL[p["id"]]}">{esc(t)}<small>{esc(note or "הנוסח המלא בניקוד")}</small></a></li>' for t, note, p in _kd_items) + "</ul>"
page("/kaddish/", f"קדיש: קדיש יתום, חצי קדיש, קדיש שלם וקדיש דרבנן בניקוד | {BRAND}",
     "נוסח הקדיש המלא בניקוד, בנוסח אשכנז, עדות המזרח וספרד: קדיש יתום, חצי קדיש, קדיש שלם (תתקבל) וקדיש דרבנן. לכל קדיש עמוד קריאה משלו.",
     "קדיש", [("סידור", "/siddur/"), ("קדיש", "/kaddish/")],
     after='<h2 class="sec">נוסח אשכנז</h2>' + _kd_html
           + "".join(f'<h2 class="sec">נוסח {esc(NUS[m])}</h2><ul class="list">' + "".join(f'<li><a href="{v[0]}">{esc(v[1])}<small>הנוסח המלא בניקוד</small></a></li>' for (s, mm), v in KD_PAGES.items() if mm == m) + "</ul>" for m in NISHMAT)
           + chips("בתוך סדר התפילה", [("/siddur/mizrach/shacharit/", "שחרית · נוסח עדות המזרח"), ("/siddur/sefard/shacharit/", "שחרית · נוסח ספרד"), ("/siddur/ashkenaz/shacharit/", "שחרית · נוסח אשכנז")])
           + chips("עוד באתר", [("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/kelim/yahr/", "חישוב יום השנה לפטירה"), ("/kelim/shem/", "תהילים לפי אותיות השם")]),
     hub=True, prio="0.8", lead="כל סוגי הקדיש, לכל אחד עמוד קריאה משלו בניקוד מלא.",
     ld=[collection("קדיש", "/kaddish/", [PURL[p["id"]] for _, _, p in _kd_items] + [v[0] for v in KD_PAGES.values()])])

# ---------- at the Western Wall ----------
# No composed "Kotel prayer" is printed here: none was found whose text can be read at its source and copied freely.
# The page holds only verses and Psalms (data/tehillim.json; Isaiah 64:10 from data/kotel.json), in the order the old
# accounts give, and names the source of every custom. Whether one tears a garment today is left to a rabbi.
KOTEL = json.load(open(os.path.join(DATA, "kotel.json"), encoding="utf-8"))
_KSRC = "https://timeline.thekotel.org/wp-content/uploads/2024/06/u2_t1583397251.pdf"
_kv = lambda c, i: f'<p>{clean(P[c - 1][i - 1])} <small>(תהילים {gem(c)}, {gem(i)})</small></p>'
_kp = lambda c: f'<h3 id="p{c}"><a href="/tehillim/{c}/">תהילים פרק {gem(c)}</a></h3>{verses(c)}'
k_text = ('<h2 id="bo">כשמגיעים אל הכותל</h2>'
          '<p><small>בספר התפילות ”שערי דמעה” (ירושלים, תר״ט, 1849) נכתב שהבא אל הכותל אומר את שני הפסוקים האלה:</small></p>'
          + _kv(26, 8) + _kv(5, 8)
          + '<h2 id="mizmorim">מזמורים שנהגו לומר ליד הכותל</h2>'
          '<p><small>לפי תיאורים של אנשי ירושלים מהמאות ה-17 וה-18: פרק פד ופרק קכב, ואחריהם פרק קלב ופרק קלג.</small></p>'
          + _kp(84) + _kp(122) + _kp(132) + _kp(133)
          + '<h2 id="churban">על חורבן בית המקדש</h2>'
          '<p><small>בשולחן ערוך (אורח חיים תקסא, ב) נכתב שהרואה את מקום המקדש בחורבנו אומר את הפסוק הזה:</small></p>'
          f'<p>{clean(KOTEL["verses"]["Isaiah.64.10"])} <small>(ישעיהו סד, י)</small></p>'
          '<p><small>הב״ח והמשנה ברורה (שם, ס״ק ו) מוסיפים את המזמור ”מזמור לאסף”, פרק עט:</small></p>'
          + _kp(79))
k_before = ('<div class="prose"><p>אין נוסח אחד מחייב לתפילה בכותל המערבי. לאורך הדורות נהגו לומר שם פסוקים ומזמורי תהילים על ירושלים ועל בית המקדש, ולהוסיף אחריהם בקשה אישית, כל אחד במילים שלו.</p>'
            '<p>בעמוד הזה מופיעים רק פסוקים ומזמורים, בסדר שמתואר במקורות, ולצד כל קטע כתוב מאיפה המנהג. '
            'השולחן ערוך מזכיר שם גם קריעה על חורבן המקדש. אם ואיך נוהגים בזה היום, שואלים רב.</p></div>'
            '<div class="related jr" style="margin-block-end:1rem"><a href="#bo">כשמגיעים</a><a href="#mizmorim">מזמורים</a><a href="#churban">על החורבן</a></div>')
k_after = ('<div class="prose"><h2 class="sec">מקורות</h2><ul>'
           '<li>הפסוקים בבואו אל הכותל והמזמורים: ”מנהג אמירת תהלים ליד הכותל המערבי, לקט תיעוד היסטורי”, הקרן למורשת הכותל המערבי '
           f'(<a href="{_KSRC}" target="_blank" rel="noopener">לקריאת הלקט</a>), שמביא את ”שערי דמעה”, מכתב מירושלים משנת שע״ו, את רבי משה פוריית מפראג ואת רבי משה חאגיז.</li>'
           '<li><a href="https://www.sefaria.org.il/Shulchan_Arukh%2C_Orach_Chayim.561.2" target="_blank" rel="noopener">שולחן ערוך אורח חיים תקסא, ב</a> · '
           '<a href="https://www.sefaria.org.il/Bach%2C_Orach_Chayim.561" target="_blank" rel="noopener">ב״ח שם</a> · '
           '<a href="https://www.sefaria.org.il/Mishnah_Berurah.561.6" target="_blank" rel="noopener">משנה ברורה שם, ס״ק ו</a>.</li>'
           '<li>נוסח הפסוקים: תהילים מתוך ספר התהילים שבאתר, והפסוק מישעיהו מתוך ”תנ״ך עם ניקוד” (נחלת הכלל).</li></ul></div>'
           + chips("עוד באתר", [("/tehillim/", "ספר תהילים"), ("/kelim/kivun/", "כיוון תפילה לירושלים"), ("/tefilat-haderech/", "תפילת הדרך"), ("/siddur/", "סידור תפילה")]))
page("/kotel/", f"תפילה בכותל המערבי: פסוקים ומזמורים שנהגו לומר | {BRAND}",
     "מה אומרים בכותל המערבי: הפסוקים שנאמרים כשמגיעים אל הכותל ומזמורי התהילים שנהגו לומר שם, בניקוד מלא ועם המקור של כל מנהג.",
     "תפילה בכותל המערבי", [("תפילה בכותל המערבי", "/kotel/")], text=k_text, before=k_before, after=k_after, prio="0.8",
     lead="הפסוקים והמזמורים שנהגו לומר ליד הכותל, עם המקור של כל מנהג.",
     ld=[{"@type": "CreativeWork", "name": "תפילה בכותל המערבי", "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + "/kotel/"}])

# ---------- the forty-day custom of Rachel Imenu ----------
# A custom that passes by word of mouth. The page describes it as the two pages that were read describe it, says plainly
# that it is a custom and not a ruling, and prints no composed prayer: the request is made in one's own words.
# The only sacred text is the three verses about Rachel (Jeremiah 31:15-17, data/kotel.json), shown as verses, not as part of the custom.
_R_SRC = [("https://www.tehillim-center.co.il/article/4954", "מוקד תהילים ארצי"), ("https://breslev.co.il/4873956/", "ברסלב ישראל")]
R40_JS = ("(function(){var g=document.getElementById('r40g'),s=document.getElementById('r40s'),r=document.getElementById('r40r');if(!g)return;var K='rachel40',d=[];"
          "try{d=JSON.parse(localStorage.getItem(K)||'[]')||[]}catch(e){}if(!(d instanceof Array))d=[];"
          "function save(){try{localStorage.setItem(K,JSON.stringify(d))}catch(e){}}"
          "function paint(){var b=g.querySelectorAll('button'),n=0;for(var i=0;i<b.length;i++){var on=d.indexOf(i+1)>=0;if(on)n++;b[i].setAttribute('aria-pressed',on?'true':'false')}"
          "s.textContent=n===0?'עוד לא סומן יום. מסמנים כל יום אחרי שהדליקו.':n>=40?'סומנו כל 40 הימים.':'סומנו '+n+' מתוך 40 ימים. נשארו '+(40-n)+'.';r.hidden=n===0}"
          "g.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('button');if(!b)return;var k=+b.getAttribute('data-d'),i=d.indexOf(k);if(i>=0)d.splice(i,1);else d.push(k);save();paint()});"
          "r.addEventListener('click',function(){if(confirm('למחוק את כל הסימונים ולהתחיל מחדש?')){d=[];save();paint()}});paint()})();")
_r40 = ('<style>.r40g{display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;max-width:26rem;margin:.8rem 0}@media(min-width:40rem){.r40g{grid-template-columns:repeat(8,1fr);max-width:32rem}}'
        '.r40g button{min-height:2.75rem;border:1px solid var(--line);border-radius:.8rem;background:var(--surface,#fff);color:inherit;font:inherit;font-weight:700;cursor:pointer}'
        '.r40g button[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}#r40r{margin-block-start:.3rem}</style>'
        '<h2 class="sec" id="maakav">מעקב 40 יום</h2><p class="note" id="r40s" aria-live="polite">מסמנים כל יום אחרי שהדליקו.</p>'
        '<div class="r40g" id="r40g" role="group" aria-label="ארבעים הימים">' + "".join(f'<button type="button" data-d="{i}" aria-pressed="false" aria-label="יום {i}">{i}</button>' for i in range(1, 41)) + '</div>'
        '<p><button type="button" class="btn2" id="r40r" hidden>התחלה מחדש</button></p><p class="note">הסימון נשמר רק במכשיר הזה.</p>')
r_before = ('<div class="prose"><p>סגולת רחל אמנו היא מנהג שעובר מפה לאוזן: מדליקים נר לעילוי נשמתה של רחל אמנו 40 יום ברצף, נותנים צדקה ומתפללים על ישועה. '
            'זה מנהג ולא הלכה. יש תפילה קצרה שנוהגות לומר, והיא מופיעה כאן למטה, ואפשר גם לבקש במילים שלכם.</p>'
            '<h2 class="sec">איך נוהגים</h2><ol>'
            '<li>מדליקים נר לעילוי נשמת רחל אמנו בכל יום, 40 יום ברצף, ושמים כמה מטבעות לצדקה.</li>'
            '<li>אחרי ההדלקה מתפללים לקדוש ברוך הוא שבזכותה של רחל אמנו ירחם וישלח את הישועה שמבקשים, למשל זיווג הגון או זרע של קיימא.</li>'
            '<li>מקבלים על עצמכם לפרסם את הסגולה ברבים אם התפילה נענתה.</li></ol>'
            '<p>בשבת לא מדליקים נר. את הנר של שבת מדליקים ביום שישי, לפני כניסת השבת.</p></div>' + _r40)
RACHEL = json.load(open(os.path.join(DATA, "rachel.json"), encoding="utf-8"))
r_text = ('<h2 id="tefila">התפילה שנוהגות לומר</h2><p><small>אחרי הדלקת הנר. הנוסח כתוב בלשון אישה שמבקשת זיווג ופרי בטן.</small></p>'
          f'<p>{clean(RACHEL["prayer"])}</p>'
          '<h2 id="psukim">הפסוקים על רחל אמנו</h2><p><small>מתוך ספר ירמיהו, פרק לא. הפסוקים אינם חלק מהסגולה. הם המקור לדמותה של רחל כמי שמתפללת על בניה.</small></p>'
          + "".join(f'<p>{clean(KOTEL["verses"][k])} <small>(ירמיהו לא, {v})</small></p>' for k, v in (("Jeremiah.31.15", "טו"), ("Jeremiah.31.16", "טז"), ("Jeremiah.31.17", "יז"))))
r_after = ('<div class="prose"><h2 class="sec">מקורות</h2><ul>'
           + "".join(f'<li>תיאור המנהג: <a href="{u}" target="_blank" rel="noopener">{esc(t)}</a>.</li>' for u, t in _R_SRC)
           + '<li>נוסח התפילה: כפי שהוא נפוץ בין הנוהגות בסגולה. המחבר והמקור הראשון אינם ידועים לנו.</li><li>נוסח הפסוקים: ”תנ״ך עם ניקוד” (נחלת הכלל).</li></ul>'
           '<p><small>האתר מתאר את המנהג כפי שהוא מתואר במקורות האלה ואינו פוסק בו. מי שרוצה הדרכה שואל רב.</small></p></div>'
           + chips("עוד באתר", [("/tikun-rachel/", "תיקון רחל"), ("/birkat-kala/", "ברכת כלה"), ("/mizmor-letoda/", "מזמור לתודה"), ("/nishmat-kol-chai/", "נשמת כל חי"), ("/sefer/haman/", "פרשת המן"), ("/tehillim/", "ספר תהילים"), ("/kelim/shem/", "תהילים לפי שם")]))
page("/segulat-rachel-imenu/", f"סגולת רחל אמנו 40 יום: התפילה ואיך נוהגים | {BRAND}",
     "סגולת רחל אמנו ל-40 יום: איך נוהגים שלב אחרי שלב, התפילה ”קומי רחל אמנו” בניקוד מלא, מעקב ימים שנשמר בטלפון והפסוקים על רחל אמנו.",
     "סגולת רחל אמנו", [("סגולת רחל אמנו", "/segulat-rachel-imenu/")], text=r_text, before=r_before, after=r_after, prio="0.8", script=R40_JS,
     lead="40 יום של נר, צדקה ותפילה. איך נוהגים, ומעקב ימים.",
     ld=[{"@type": "Article", "headline": "סגולת רחל אמנו: 40 יום", "inLanguage": "he", "url": SITE + "/segulat-rachel-imenu/"}])

page("/sefer/", f"ספרייה: פרקי אבות, מגילות, פרק שירה ועוד | {BRAND}",
     "ספרייה בניקוד מלא: פרקי אבות, שיר השירים, מגילת רות, מגילת אסתר, איכה, קהלת, משלי, פרק שירה, פרשת המן, סליחות, יזכור ועוד. כל ספר בעמוד קריאה משלו.",
     "ספרייה", [("ספרייה", "/sefer/")],
     after='<ul class="list">' + "".join(f'<li><a href="/sefer/{k}/">{esc(b["t"])}<small>{esc(b.get("sub",""))}</small></a></li>' for k, b in B.items()) + "</ul>"
           + chips("עוד באתר", [("/siddur/", "סידור תפילה"), ("/tehillim/", "ספר תהילים"), ("/tehillim/yomi/", "תהילים יומי"), ("/kelim/", "כלים אישיים")]),
     app_hash="sifriya", hub=True, prio="0.9", lead="ספרים ופרקים שקוראים לאורך השנה.",
     ld=[collection("ספרייה", "/sefer/", [f"/sefer/{k}/" for k in B])])

# =====================================================================
# Explainers that lead into the app
# =====================================================================
SB_ON = bool(re.search(r'supabaseUrl:\s*"[^"]+"|^\s*yachad:\s*true', open(os.path.join(ROOT, "config.js"), encoding="utf-8").read(), re.M))
Y_QA = [('איך מצטרפים לקריאה קיימת?', 'נכנסים לקישור שקיבלתם, או בוחרים קריאה מהרשימה. לוקחים פרק, קוראים ולוחצים ”סיימתי”.'), ('על מה אפשר לפתוח קריאה?', 'לרפואה שלמה, לעילוי נשמה, לזיווג הגון, להצלחה ולישועה, או לבקשה כללית.'), ('מי רואה את הקריאה שפתחתי?', 'מי שקיבל מכם את הקישור. ברשימה כאן היא מופיעה רק אם בחרתם בכך.'), ('לקחתי פרק ולא הספקתי לקרוא', 'אחרי 24 שעות הפרק חוזר להיות פנוי, ומישהו אחר יכול לקחת אותו.'), ('מה קורה כשכל הספר נקרא?', 'הספר נשלם, ומתחיל סבב חדש.')]
Y_PIN = "93fe6ej9xd"  # the standing reading for the soldiers; shown first only while it is on the public list
Y_JS = ("(function(){var PIN='" + Y_PIN + "',K={neshama:['לעילוי נשמה','לעילוי נשמת ',' ז״ל'],refuah:['לרפואה שלמה','',''],zivug:['לזיווג הגון','',''],hatzlacha:['להצלחה ולישועה','','']};"
        "function get(u,f){fetch(u).then(function(r){return r.ok?r.json():null}).then(function(j){if(j&&j.data)f(j.data)}).catch(function(){})}"
        "function el(t,x){var e=document.createElement(t);if(x!=null)e.textContent=x;return e}"
        "function nm(m){var k=K[m.kind];return String(m.name||'').trim()+(k&&m.parent?' '+(m.rel||'בן')+' '+String(m.parent).trim():'')}"
        "function card(m,tag){var k=K[m.kind],done=+m.done||0,inr=done%150,rnd=Math.floor(done/150),n=nm(m);"
        "var li=el('li'),a2=el('a');a2.href='/y/'+m.id;a2.appendChild(el('small',tag||(k?k[0]:'קריאה משותפת')));a2.appendChild(el('b',k?k[1]+n+k[2]:n));"
        "var bar=el('i'),u=el('u');u.style.inlineSize=Math.max(2,Math.round(inr/150*100))+'%';bar.appendChild(u);a2.appendChild(bar);"
        "var em=el('em');em.appendChild(document.createTextNode((rnd?'סבב '+(rnd+1)+' · ':'')+inr+' מתוך 150 פרקים'));em.appendChild(el('span','להצטרפות ‹'));a2.appendChild(em);"
        "li.appendChild(a2);return li}"
        "function norm(x){return String(x||'').replace(/[\\u0591-\\u05C7\"'׳״.,\\-–]/g,'').replace(/\\s+/g,' ').trim()}"
        "get('/api/yachad?stats=1',function(d){var b=document.getElementById('ynum');if(!b||!(d.chapters>0))return;"
        "b.querySelectorAll('[data-k]').forEach(function(x){x.textContent=Number(d[x.getAttribute('data-k')]||0).toLocaleString('he-IL')});b.hidden=false});"
        "get('/api/yachad?list=1',function(a){a=(a||[]).filter(function(m){return m&&/^[a-z0-9]+$/.test(m.id||'')&&nm(m)});if(!a.length)return;"
        "var s=document.getElementById('yrec'),ul=s.querySelector('ul'),q=document.getElementById('yq'),none=document.getElementById('ynone'),"
        "pin=a.filter(function(m){return m.id===PIN})[0],rest=a.filter(function(m){return m.id!==PIN});"
        "if(pin){var ps=document.getElementById('ypin');ps.querySelector('ul').appendChild(card(pin,'קריאה קבועה · פתוחה לכולם'));ps.hidden=false}"
        "function draw(){var v=norm(q.value),L=v?a.filter(function(m){return norm(nm(m)).indexOf(v)>=0}).slice(0,20):rest.slice(0,6);"
        "ul.textContent='';L.forEach(function(m){ul.appendChild(card(m))});none.hidden=!v||L.length>0}"
        "q.addEventListener('input',draw);draw();if(rest.length||pin)s.hidden=false})})();")
yachad = ('<div class="yhero"><p>כל אחד פרק.<br>ביחד ספר שלם.</p>'
          + ('<a class="btn" href="/#znew">פתחו קריאה משותפת</a>'
             '<ul class="ynum" id="ynum" hidden><li><b data-k="chapters">0</b>פרקים נקראו</li><li><b data-k="readings">0</b>קריאות נפתחו</li></ul></div>' if SB_ON else
             '<a class="btn" href="/tehillim/">לקריאת תהילים עכשיו</a><small>הקריאה המשותפת תיפתח בקרוב. בינתיים כל ספר התהילים פתוח לקריאה באתר.</small></div>')
          + ('<section id="ypin" hidden><h2 class="sec">קריאה פתוחה עכשיו</h2><ul class="yrec ypin"></ul></section>' if SB_ON else '')
          + '<h2 class="sec">איך פותחים קריאת תהילים משותפת</h2><ol class="st3">'
          '<li><b>פותחים קריאה</b><span>לרפואה, לעילוי נשמה או לכל בקשה.</span></li>'
          '<li><b>שולחים קישור</b><span>בוואטסאפ, למשפחה ולחברים.</span></li>'
          '<li><b>כל אחד קורא פרק</b><span>ומסמן שקרא, עד שהספר נשלם.</span></li></ol>'
          + ('<section id="yrec" hidden><h2 class="sec">נפתחו לאחרונה</h2>'
             '<div class="ysrch"><input type="search" id="yq" aria-label="חיפוש קריאה לפי שם" placeholder="חיפוש קריאה לפי שם" autocomplete="off" enterkeyhint="search"></div>'
             '<ul class="yrec"></ul><p class="note" id="ynone" hidden>לא נמצאה קריאה פתוחה בשם הזה. אפשר לפתוח קריאה חדשה בכפתור שלמעלה.</p>'
             '</section>' if SB_ON else '') +
          '<div class="prose"><h2>חלוקת תהילים בין המשתתפים</h2>'
          '<p>150 פרקי הספר מתחלקים בין כל מי שמצטרף. כל אחד לוקח פרק, קורא ומסמן שקרא.</p></div>'
          '<figure class="yfig"><img src="/icons/tehillim-yachad.png?v=2" width="1200" height="1200" loading="lazy" decoding="async" '
          'alt="תהילים יחד: קריאת תהילים משותפת באתר תפילה, כפי שהיא נראית בטלפון, עם מספר הפרקים שנקראו וכפתור לקבלת פרק"></figure>'
          + "".join(f'<details class="qa"><summary>{q}</summary><p>{a_}</p></details>' for q, a_ in Y_QA)
          + ('' if SB_ON else '<p class="note">העמוד הזה מסביר איך הקריאה המשותפת תעבוד. היא עדיין לא פתוחה לשימוש.</p>'))
yachad += chips("לקריאה עצמית", [("/tehillim/", "ספר תהילים, כל 150 הפרקים"), ("/kelim/shem/", "תהילים לפי שם"), ("/tehillim/refuah/", "תהילים לרפואה שלמה"),
                                 ("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/tehillim/kever/", "תהילים לבית העלמין"),
                                 ("/tehillim/tikkun/", "תיקון הכללי"), ("/tehillim/yomi/", "תהילים יומי"), ("/kelim/shem/", "תהילים קיט לפי שם")])
page("/tehillim-yachad/", f"תהילים יחד: חלוקת תהילים וקריאה משותפת | {BRAND}",
     "תהילים יחד: קוראים תהילים ביחד, משפחה וחברים, בלי הרשמה. פותחים קריאה לרפואה או לעילוי נשמה, שולחים קישור בוואטסאפ, וכל אחד קורא פרק עד שהספר נשלם.",
     "תהילים יחד", [("תהילים יחד", "/tehillim-yachad/")], after=yachad, hub=True, prio="0.8", h1_ctx="קריאת תהילים משותפת", script=Y_JS if SB_ON else "",
     lead="קוראים תהילים ביחד: מחלקים את 150 הפרקים בין כל מי שמצטרף, עד שהספר כולו נקרא.",
     ld=[{"@type": "WebPage", "name": "תהילים יחד", "url": SITE + "/tehillim-yachad/", "inLanguage": "he", "isPartOf": WEBSITE, "about": BOOK_T,
          "primaryImageOfPage": {"@type": "ImageObject", "url": SITE + "/icons/tehillim-yachad.png?v=2", "width": 1200, "height": 1200,
                                 "caption": "תהילים יחד: קריאת תהילים משותפת באתר תפילה"}}])

# ---------- personal tools: what each one does and how it calculates (read from the app's own code), then into the app ----------
ABC = "אבגדהוזחטיכלמנסעפצקרשת"
_letters = ('<table><tr><th>אות</th><th>פסוקים בפרק קיט</th></tr>' + "".join(
    f"<tr><td>{c}</td><td>{gem(i * 8 + 1)} עד {gem(i * 8 + 8)}</td></tr>" for i, c in enumerate(ABC)) + "</table>")
TOOL = {
    "shem": ("תהילים לפי שם: פסוקי פרק קי״ט לפי אותיות השם",
             "תהילים קיט לפי שם: מקלידים שם בעברית ומקבלים את פסוקי פרק קיט לפי אותיות השם, עם אפשרות להוסיף את אותיות נשמה לעילוי נשמת",
             ["בתהילים פרק קיט יש 176 פסוקים, שמונה פסוקים לכל אות, לפי סדר האלף-בית. הכלי עובר על אותיות השם לפי הסדר ומציג לכל אות את שמונת הפסוקים שלה.",
              "אפשר להוסיף בסוף את אותיות המילה נשמה (נ, ש, מ, ה), כפי שנוהגים לעילוי נשמת. אות סופית נחשבת כאות הרגילה, והמילים בן ובת שבין השם לשם האם אינן נספרות.",
              "יש נוהגים לומר את אותיות השם הפרטי בלבד, ויש שמוסיפים גם את שם האם, לפי המנהג."],
             '<h2>האותיות והפסוקים</h2>' + _letters + '<p><a href="/tehillim/119/">תהילים פרק קיט, הפרק המלא</a></p>',
             [("/tehillim/119/", "תהילים פרק קיט"), ("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/tehillim/kever/", "תהילים לבית העלמין"), ("/tehillim/refuah/", "תהילים לרפואה שלמה")]),
    "pasuk": ("פסוק לשם: פסוק שמתחיל ומסתיים באותיות השם",
              "פסוק לשמך: מקלידים שם פרטי ומקבלים פסוקים מספר תהילים שמתחילים באות הראשונה של השם ומסתיימים באות האחרונה שלו",
              ["הכלי מחפש בכל ספר תהילים פסוקים שהאות הראשונה שלהם היא האות הראשונה של השם, והאות האחרונה שלהם היא האות האחרונה של השם. מוצגים עד שישה פסוקים, הקצרים קודם, עם מראה המקום של כל אחד.",
               "לפי המנהג אומרים את הפסוק לפני ״יהיו לרצון״ שבסוף העמידה. בסידורים רבים יש רשימה מסורתית של פסוקים מכל התנ״ך; כאן החיפוש הוא בספר תהילים בלבד."],
              "", [("/tehillim/", "ספר תהילים"), ("/kelim/shem/", "תהילים קיט לפי שם")]),
    "gil": ("פרק תהילים לפי גיל: איזה פרק אומרים השנה",
            "פרק תהילים לפי גיל: מקלידים גיל ומקבלים את הפרק שנוהגים לומר כל יום בשנה הנוכחית לחיים, עם קישור לקריאת הפרק",
            ["החישוב פשוט: מספר הפרק הוא הגיל ועוד אחד. מי שמלאו לו 30 נמצא בשנה ה-31 לחייו, ולכן בשנה שבין יום ההולדת ה-30 ל-31 הפרק שלו הוא פרק לא.",
             "הכלי מציג את הפרק של השנה הנוכחית ואת הפרק של השנה שעברה, ומוביל ישר לקריאה."],
            "", [("/tehillim/", "כל 150 פרקי התהילים"), ("/kelim/bday/", "יום הולדת עברי לפי תאריך לועזי"), ("/tehillim/yomi/", "תהילים יומי")]),
    "yahr": ("חישוב יום השנה לפטירה (יארצייט) לפי התאריך העברי",
             "חישוב יום השנה לפטירה (יארצייט): מזינים את תאריך הפטירה הלועזי ומקבלים את התאריך העברי ואת יום השנה בחמש השנים הקרובות, עם הוספה ליומן",
             ["מזינים את תאריך הפטירה הלועזי, ומסמנים אם הפטירה הייתה אחרי השקיעה: היום העברי מתחיל בערב, ולכן פטירה אחרי השקיעה שייכת לתאריך העברי של היום הבא.",
              "הכלי ממיר את התאריך לתאריך העברי, ומציג את יום השנה בחמש השנים הקרובות עם התאריך הלועזי של כל אחד. אפשר להוסיף את התאריכים ליומן.",
              "יום השנה מתחיל בערב שלפניו. מי שנפטר בחודש אדר בשנה רגילה: לגבי שנה מעוברת יש מנהגים שונים, וכדאי לשאול רב."],
             "", [("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/tehillim/kever/", "תהילים לבית העלמין"), ("/sefer/yizkor/", "יזכור"), ("/kelim/shem/", "תהילים קיט לפי שם")]),
    "bday": ("יום הולדת עברי לפי תאריך לועזי: חישוב התאריך העברי",
             "יום הולדת עברי לפי תאריך לועזי: מזינים תאריך לידה ומקבלים את התאריך העברי, מתי יוצא יום ההולדת העברי השנה ומועד בר או בת המצווה",
             ["מזינים את תאריך הלידה הלועזי, ומסמנים אם הלידה הייתה אחרי השקיעה: היום העברי מתחיל בערב, ולכן לידה אחרי השקיעה שייכת לתאריך העברי של היום הבא.",
              "הכלי מציג את התאריך העברי של הלידה, את התאריך הלועזי שבו יוצא יום ההולדת העברי הקרוב, ואת מועד בר המצווה (בגיל 13) או בת המצווה (בגיל 12). אפשר להוסיף את יום ההולדת העברי ליומן לעשר השנים הבאות."],
             "", [("/kelim/gil/", "פרק תהילים לפי גיל"), ("/kelim/yahr/", "חישוב יום השנה לפטירה"), ("/tehillim/", "ספר תהילים")]),
    "kivun": ("כיוון תפילה לירושלים: מצפן לפי המיקום שלכם",
              "כיוון תפילה לירושלים: מצפן שמחשב לפי המיקום שלכם את הכיוון לירושלים ולמקום המקדש במעלות מהצפון, ואת המרחק בקילומטרים",
              ["הכלי מחשב את הכיוון מהמקום שבו אתם נמצאים אל ירושלים, במעלות מהצפון (0 צפון, 90 מזרח), ואת המרחק בקילומטרים.",
               "בטלפון שיש בו מצפן החץ מצביע לירושלים כשמחזיקים את הטלפון שטוח. במכשיר בלי מצפן החץ מראה את הכיוון ביחס לצפון. בלי הרשאת מיקום החישוב נעשה לפי העיר שנבחרה באתר.",
               "מתפללים לכיוון ירושלים ומקום המקדש, ובירושלים עצמה לכיוון הר הבית."],
              "", [("/siddur/", "סידור תפילה"), ("/siddur/mizrach/shacharit/", "שחרית לימי חול"), ("/tehillim/", "ספר תהילים")]),
}
assert set(TOOL) == {k for k, _, _ in KELIM}, "a tool was added to the app: describe it in TOOL"
SHEM_FORM = ('<form id="nf" class="nform"><label for="nn">שם בעברית</label>'
             '<input id="nn" name="n" maxlength="40" placeholder="למשל: אברהם בן שרה" autocomplete="off" required>'
             '<fieldset><legend>למה קוראים?</legend><label><input type="radio" name="m" value="r" checked> לרפואה ולכל בקשה</label>'
             '<label><input type="radio" name="m" value="n"> לעילוי נשמה, עם אותיות ”נשמה”</label></fieldset>'
             '<button class="btn" type="submit">הצגת הפסוקים</button></form><div id="nout" aria-live="polite"></div>')
SHEM_JS = ("(function(){var f=document.getElementById('nf'),out=document.getElementById('nout');if(!f||!out)return;"
           "var ABC='אבגדהוזחטיכלמנסעפצקרשת',FIN={'ך':'כ','ם':'מ','ן':'נ','ף':'פ','ץ':'צ'},P=null,NIK=/[֑-ֽֿ-ׇ]/g;"
           "function gem(n){var H=['','ק'],T=['','י','כ','ל','מ','נ','ס','ע','פ','צ'],O=['','א','ב','ג','ד','ה','ו','ז','ח','ט'],r=n%100;return H[Math.floor(n/100)]+(r===15?'טו':r===16?'טז':T[Math.floor(r/10)]+O[r%10])}"
           "function esc(s){return s.replace(/[&<>\"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]})}"
           "function letters(s){return s.replace(NIK,'').split('').map(function(c){return FIN[c]||c}).filter(function(c){return ABC.indexOf(c)>=0})}"
           "function run(push){var name=f.n.value.trim().slice(0,40),ns=f.m.value==='n',ls=letters(name.replace(/\\s+(בן|בת)\\s+/,' '));"
           "if(!ls.length){out.innerHTML='<p class=\"note\">כתבו את השם באותיות עבריות.</p>';return}if(ns)ls=ls.concat(['נ','ש','מ','ה']);out.innerHTML='<p class=\"note\">טוען את הפסוקים…</p>';"
           "(P?Promise.resolve(P):fetch('/data/tehillim.json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){P=j;return j})).then(function(T){"
           "function shemSlug(s){var A='אבגדהוזחטיכלמנסעפצקרשת',L='abgdhvzxjyklmnsepcqrwt',F={'ך':'k','ם':'m','ן':'n','ף':'p','ץ':'c'};return s.replace(/[^\\u05D0-\\u05EA ]/g,'').trim().split(/\\s+/).map(function(w){var o='';for(var i=0;i<w.length;i++){var c=w.charAt(i),last=i===w.length-1;if(F[c])o+=F[c];else{var l=L.charAt(A.indexOf(c));o+=l+(last&&'kmnpc'.indexOf(l)>=0?'0':'')}}return o}).join('-')}var path=(ns?'/leiluy-nishmat/':'/kelim/shem/')+'?n='+name.replace(/[^\\u05D0-\\u05EA ]/g,'').trim().replace(/\\s+/g,'+'),link=location.origin+path,h='<h2 class=\"sec\">הפסוקים לשם '+esc(name)+'</h2><div class=\"nlet\">'+ls.map(function(c){return '<span>'+c+'</span>'}).join('')+'</div>'"
           "+'<p class=\"nact\"><a class=\"btn\" target=\"_blank\" rel=\"noopener\" href=\"https://wa.me/?text='+encodeURIComponent((ns?'תהילים לעילוי נשמת '+name:'תהילים לפי שם: '+name)+'\\nפסוקי פרק קי״ט לפי אותיות השם:\\n'+link)+'\">שליחה בוואטסאפ</a><button type=\"button\" class=\"btn2\" id=\"ncp\">העתקת קישור</button><button type=\"button\" class=\"btn2\" id=\"npr\">הדפסה</button></p><article class=\"text\">';"
           "ls.forEach(function(c,j){var i=ABC.indexOf(c);h+='<h2>אות '+c+(ns&&j>=ls.length-4?' · נשמה':'')+'</h2>';T[118].slice(i*8,i*8+8).forEach(function(v,k){h+='<p><sup>'+gem(i*8+k+1)+'</sup>'+v+'</p>'})});"
           "out.innerHTML=h+'</article>';document.getElementById('npr').onclick=function(){print()};"
           "document.getElementById('ncp').onclick=function(){var b=this;(navigator.clipboard?navigator.clipboard.writeText(link):Promise.reject()).then(function(){b.textContent='הקישור הועתק'},function(){prompt('הקישור:',link)})};"
           "try{history.replaceState(null,'',path)}catch(e){}"
           "if(push)out.scrollIntoView({behavior:'smooth',block:'start'})"
           "}).catch(function(){out.innerHTML='<p class=\"note\">הטעינה נכשלה. בדקו את החיבור ונסו שוב.</p>'})}"
           "f.addEventListener('submit',function(e){e.preventDefault();run(true)});"
           "function boot(){var h=new URLSearchParams(location.hash.slice(1)),q=new URLSearchParams(location.search),w=window.__shem,n0=h.get('name')||q.get('n')||(w&&w.name),ns0=h.has('neshama')?h.get('neshama')==='1':q.has('m')?q.get('m')==='n':w?!!w.neshama:(location.pathname.indexOf('/leiluy-nishmat')===0||f.m.value==='n');"
           "if(n0){f.n.value=n0.replace(/[^\\u05D0-\\u05EA \\-]/g,'').slice(0,40);f.m.value=ns0?'n':'r';run(false)}}boot();addEventListener('hashchange',boot)})();")
for i, (k, t, d) in enumerate(KELIM):
    ttl, head, paras, extra, rel = TOOL[k]
    pv, nx = (KELIM[i - 1] if i else None), (KELIM[i + 1] if i + 1 < len(KELIM) else None)
    opener = SHEM_FORM if k == "shem" else f'<p><a class="btn" href="/#kli-{k}">לפתיחת הכלי באפליקציה</a></p>'
    if k == "shem":
        # the four sections people look for by name: printed here, pointed, straight from the Psalms data
        _ns = "".join(f'<h3 id="ot-{c}">אות {c}</h3>' + "".join(f"<p><sup>{gem(ABC.index(c) * 8 + j + 1)}</sup>{clean(v)}</p>" for j, v in enumerate(P[118][ABC.index(c) * 8:ABC.index(c) * 8 + 8])) for c in "נשמה")
        opener += ('<h2 class="sec" id="neshama">אותיות נשמה: הפסוקים מפרק קי״ט</h2><p class="note">לעילוי נשמה נוהגים לומר, אחרי אותיות השם, את פסוקי האותיות נ, ש, מ, ה. אלה 32 הפסוקים:</p>'
                   f'<article class="text nesh">{_ns}</article>')
    body = (opener + '<div class="prose"><h2>איך זה עובד</h2>'
            + "".join(f"<p>{esc(x)}</p>" for x in paras) + extra + "</div>"
            + ('<p class="note">הכלי מחשב בדפדפן שלכם. השם שמקלידים לא נשלח לשום מקום.</p>' if k == "shem" else '<p class="note">הכלי מחשב לפי מה שמקלידים בו, ונפתח באפליקציה של תפילה.</p>')
            + (chips("רוצים שעוד אנשים יקראו?", [("/tehillim-yachad/", "פתיחת קריאת תהילים משותפת"), ("/kaddish/", "קדיש"), ("/tehillim/yomi/", "תהילים יומי")]) if k == "shem" else "")
            + pager((f"/kelim/{pv[0]}/", pv[1]) if pv else None, (f"/kelim/{nx[0]}/", nx[1]) if nx else None)
            + chips("קשור לכלי הזה", rel + [("/kelim/", "כל הכלים האישיים")]))
    page(f"/kelim/{k}/", f"{ttl} | {BRAND}", fit_desc(head, tails=("הכלי נפתח באפליקציה של תפילה.", "באתר תפילה.")),
         t, [("כלים אישיים", "/kelim/"), (t, f"/kelim/{k}/")], after=body, lead=d, hub=False, prio="0.9" if k == "shem" else "0.7", script=SHEM_JS if k == "shem" else "",
         ld=[{"@type": "WebPage", "name": t, "description": d, "url": f"{SITE}/kelim/{k}/", "inLanguage": "he", "isPartOf": WEBSITE}])
    if k == "shem":
        # the same tool under the name people search for, with "for the elevation of a soul" chosen from the start
        _lb = body.replace('value="r" checked', 'value="r"').replace('value="n">', 'value="n" checked>')
        assert _lb != body and _lb.count("checked") == body.count("checked"), "the form changed: look at the landing page again"
        page("/leiluy-nishmat/", f"תהילים אותיות נשמה: לפי שם הנפטר, מפרק קי״ט | {BRAND}",
             "תהילים אותיות נשמה לעילוי נשמת הנפטר: מקלידים את השם ומקבלים את פסוקי פרק קי״ט לפי אותיות השם ואותיות נ, ש, מ, ה, בניקוד מלא, עם קישור לשליחה למשפחה.",
             "תהילים אותיות נשמה", [("ספר תהילים", "/tehillim/"), ("תהילים אותיות נשמה", "/leiluy-nishmat/")], after=_lb, hub=False, prio="0.9", script=SHEM_JS,
             lead="מקלידים את שם הנפטר ומקבלים את הפסוקים לפי אותיות השם ואותיות ”נשמה”.",
             ld=[{"@type": "WebPage", "name": "תהילים אותיות נשמה", "url": f"{SITE}/leiluy-nishmat/", "inLanguage": "he", "isPartOf": WEBSITE}])

kelim = ('<ul class="cards"><li><a href="/ma-mevarchim/"><b>מה מברכים על?</b><small>כותבים שם של מאכל ומקבלים את הברכה הראשונה והאחרונה.</small>'
         '<small>ברכה ראשונה ואחרונה לכל מאכל, עם מקור לכל הוראה</small></a></li>')
for k, t, d in KELIM:
    kelim += f'<li><a href="/kelim/{k}/"><b>{esc(t)}</b><small>{esc(d)}</small><small>{esc(TOOL[k][0])}</small></a></li>'
kelim += '</ul><p class="note">הכלים מחשבים לפי מה שמקלידים בהם, ונפתחים באפליקציה של תפילה.</p>'
kelim += chips("קשור לכלים", [("/tehillim/119/", "תהילים פרק קיט"), ("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/tehillim/kever/", "תהילים לבית העלמין"),
                              ("/sefer/yizkor/", "יזכור"), ("/tehillim/yomi/", "תהילים יומי"), ("/tehillim-yachad/", "תהילים יחד")])
page("/kelim/", f"כלים אישיים: תהילים לפי שם, יארצייט ויום הולדת עברי | {BRAND}",
     fit_desc("כלי תפילה ולוח עברי: תהילים לפי שם, פסוק אישי לסוף העמידה, תהילים לפי גיל, יארצייט, יום הולדת עברי וכיוון התפילה. הסבר קצר על כל כלי ואיך הוא מחשב", tails=()),
     "כלים אישיים", [("כלים אישיים", "/kelim/")], after=kelim, hub=True, prio="0.8", app_hash="kelim", app_label="לכל הכלים באפליקציה",
     lead=f"{len(KELIM)} כלים שמחשבים בשבילכם: לפי השם, לפי הגיל, לפי התאריך העברי ולפי המקום.",
     ld=[{"@type": "CollectionPage", "name": "כלים אישיים", "url": SITE + "/kelim/", "inLanguage": "he", "isPartOf": WEBSITE,
          "mainEntity": item_list([f"/kelim/{k}/" for k, _, _ in KELIM])}])

# ---------- Shabbat times by city ----------
# Same sun formula as the app (src/app.html sunUTC). Candle lighting = sunset minus the local custom,
# end of Shabbat = sun 8.5 degrees below the horizon, Rabbenu Tam = sunset plus 72 minutes.
import math
from zoneinfo import ZoneInfo
IL = "Asia/Jerusalem"
SH_CITIES = [("jerusalem", "ירושלים", 31.778, 35.235, IL, 40), ("tel-aviv", "תל אביב", 32.085, 34.781, IL, 18), ("haifa", "חיפה", 32.794, 34.989, IL, 30),
    ("bnei-brak", "בני ברק", 32.084, 34.834, IL, 22), ("beer-sheva", "באר שבע", 31.252, 34.791, IL, 18), ("ashdod", "אשדוד", 31.804, 34.655, IL, 18),
    ("petah-tikva", "פתח תקווה", 32.087, 34.887, IL, 40), ("netanya", "נתניה", 32.332, 34.860, IL, 18), ("rishon-lezion", "ראשון לציון", 31.973, 34.789, IL, 18),
    ("holon", "חולון", 32.011, 34.775, IL, 18), ("bat-yam", "בת ים", 32.017, 34.745, IL, 18), ("ramat-gan", "רמת גן", 32.068, 34.824, IL, 18),
    ("ashkelon", "אשקלון", 31.669, 34.574, IL, 18), ("rehovot", "רחובות", 31.894, 34.811, IL, 18), ("beit-shemesh", "בית שמש", 31.747, 34.988, IL, 18),
    ("modiin", "מודיעין", 31.898, 35.010, IL, 18), ("modiin-illit", "מודיעין עילית", 31.933, 35.041, IL, 18), ("elad", "אלעד", 32.052, 34.951, IL, 18),
    ("herzliya", "הרצליה", 32.166, 34.843, IL, 18), ("kfar-saba", "כפר סבא", 32.175, 34.907, IL, 18), ("raanana", "רעננה", 32.184, 34.871, IL, 18),
    ("hadera", "חדרה", 32.434, 34.919, IL, 18), ("lod", "לוד", 31.951, 34.888, IL, 18), ("ramla", "רמלה", 31.929, 34.866, IL, 18),
    ("tzfat", "צפת", 32.965, 35.496, IL, 20), ("tiberias", "טבריה", 32.796, 35.530, IL, 18), ("afula", "עפולה", 32.608, 35.289, IL, 18),
    ("nahariya", "נהריה", 33.006, 35.095, IL, 18), ("kiryat-shmona", "קריית שמונה", 33.207, 35.570, IL, 18), ("eilat", "אילת", 29.558, 34.952, IL, 18),
    ("netivot", "נתיבות", 31.421, 34.588, IL, 18), ("kiryat-gat", "קריית גת", 31.610, 34.764, IL, 18), ("beitar-illit", "ביתר עילית", 31.698, 35.118, IL, 18),
    ("new-york", "ניו יורק", 40.713, -74.006, "America/New_York", 18), ("los-angeles", "לוס אנג׳לס", 34.052, -118.244, "America/Los_Angeles", 18),
    ("miami", "מיאמי", 25.762, -80.192, "America/New_York", 18), ("london", "לונדון", 51.507, -0.128, "Europe/London", 18), ("paris", "פריז", 48.857, 2.352, "Europe/Paris", 18)]
def sun_utc(dt, lat, lon, zen):
    y0 = datetime.datetime(dt.year, 1, 1); N = (datetime.datetime(dt.year, dt.month, dt.day) - y0).days + 1
    lh = lon / 15; t = N + (18 - lh) / 24; M = .9856 * t - 3.289; r = math.radians
    L = (M + 1.916 * math.sin(r(M)) + .02 * math.sin(r(2 * M)) + 282.634) % 360
    RA = math.degrees(math.atan(.91764 * math.tan(r(L)))) % 360
    RA = (RA + math.floor(L / 90) * 90 - math.floor(RA / 90) * 90) / 15
    sD = .39782 * math.sin(r(L)); cD = math.cos(math.asin(sD))
    cH = (math.cos(r(zen)) - sD * math.sin(r(lat))) / (cD * math.cos(r(lat)))
    if not -1 <= cH <= 1: return None
    H = math.degrees(math.acos(cH)) / 15; ut = (H + RA - .06571 * t - 6.622 - lh) % 24
    base = datetime.datetime(dt.year, dt.month, dt.day, tzinfo=datetime.timezone.utc)
    ms = base + datetime.timedelta(hours=ut); noon = base + datetime.timedelta(hours=12 - lh)
    while (ms - noon).total_seconds() > 43200: ms -= datetime.timedelta(days=1)
    while (noon - ms).total_seconds() > 43200: ms += datetime.timedelta(days=1)
    return ms
HEMON = ["בינואר", "בפברואר", "במרץ", "באפריל", "במאי", "ביוני", "ביולי", "באוגוסט", "בספטמבר", "באוקטובר", "בנובמבר", "בדצמבר"]
def shabbat_rows(c, weeks=30):
    _, _, lat, lon, tz, mins = c; z = ZoneInfo(tz); today = datetime.date.today()
    fri = today + datetime.timedelta(days=(4 - today.weekday()) % 7)
    if today.weekday() == 5: fri = today - datetime.timedelta(days=1)
    out = []
    for i in range(weeks):
        f = fri + datetime.timedelta(days=7 * i); s = f + datetime.timedelta(days=1)
        sf, hv, ss = sun_utc(f, lat, lon, 90.833), sun_utc(s, lat, lon, 98.5), sun_utc(s, lat, lon, 90.833)
        if not (sf and hv and ss): continue
        hm = lambda d: d.astimezone(z).strftime("%H:%M")
        out.append((s, f, hm(sf - datetime.timedelta(minutes=mins)), hm(hv), hm(max(ss + datetime.timedelta(minutes=72), hv))))
    return out
# The page recomputes itself in the reader's browser with the same sun formula, so it never goes stale:
# the coming Shabbat is always on top and the table always runs 30 weeks ahead. The HTML written at build time is the fallback.
SH_CALC = ("function R(d){return d*Math.PI/180}function G(r){return r*180/Math.PI}"
           "function sun(P,y,m,d,zen){var N=Math.floor((Date.UTC(y,m-1,d)-Date.UTC(y,0,0))/864e5),lh=P.lon/15,t=N+(18-lh)/24,M=.9856*t-3.289;"
           "var L=(M+1.916*Math.sin(R(M))+.02*Math.sin(R(2*M))+282.634)%360;if(L<0)L+=360;var RA=G(Math.atan(.91764*Math.tan(R(L))))%360;if(RA<0)RA+=360;"
           "RA=(RA+Math.floor(L/90)*90-Math.floor(RA/90)*90)/15;var sD=.39782*Math.sin(R(L)),cD=Math.cos(Math.asin(sD)),cH=(Math.cos(R(zen))-sD*Math.sin(R(P.lat)))/(cD*Math.cos(R(P.lat)));"
           "if(cH>1||cH<-1)return null;var H=G(Math.acos(cH))/15,ut=(H+RA-.06571*t-6.622-lh)%24;if(ut<0)ut+=24;var ms=Date.UTC(y,m-1,d)+ut*36e5,noon=Date.UTC(y,m-1,d)+(12-lh)*36e5;"
           "while(ms-noon>432e5)ms-=864e5;while(noon-ms>432e5)ms+=864e5;return new Date(ms)}"
           "function hm(P,d){return new Intl.DateTimeFormat('he-IL',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:P.tz}).format(d)}"
           "function friday(P){var f=new Intl.DateTimeFormat('en-CA',{timeZone:P.tz,year:'numeric',month:'2-digit',day:'2-digit',weekday:'short'}).formatToParts(new Date()),o={};"
           "f.forEach(function(x){o[x.type]=x.value});var wd=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].indexOf(o.weekday),add=wd===6?-1:(5-wd+7)%7;return Date.UTC(+o.year,+o.month-1,+o.day)+add*864e5}"
           "function week(P,ms){var f=new Date(ms),s=new Date(ms+864e5),a=sun(P,f.getUTCFullYear(),f.getUTCMonth()+1,f.getUTCDate(),90.833),"
           "b=sun(P,s.getUTCFullYear(),s.getUTCMonth()+1,s.getUTCDate(),98.5),c=sun(P,s.getUTCFullYear(),s.getUTCMonth()+1,s.getUTCDate(),90.833);if(!a||!b||!c)return null;"
           "return{f:f,c:hm(P,new Date(+a-P.m*6e4)),h:hm(P,b),r:hm(P,new Date(Math.max(+c+72*6e4,+b)))}}")
SHARE_HTML = '<div class="zshare"><a class="btn zwa" id="zwa" target="_blank" rel="noopener" href="https://wa.me/"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.2-.4.6-1.2.1-.2 0-.3 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.3-.2.3-.9.9-.9 2.2s.9 2.5 1.1 2.7c.1.2 1.9 2.9 4.6 4 1.7.7 2.3.7 3.1.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.3-.2-.5-.3z"/></svg>שליחה לקבוצה</a><button class="zim" id="zim" type="button"><svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="4.5" width="17" height="15" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="m5 17 4.5-4 3.5 3 2.5-2 3.5 3"/></svg>תמונה לשיתוף</button><span class="zmsg" id="zmsg" role="status" aria-live="polite"></span></div>'
SHARE_JS = "var U=location.origin+location.pathname+'?utm_source=shabbat',wa=document.getElementById('zwa'),im=document.getElementById('zim'),ms=document.getElementById('zmsg');var TX='שבת שלום 🕯️\\nזמני השבת ב'+P.n+' ('+first.dt+'):\\nכניסת שבת '+first.c+'\\nצאת השבת '+first.h+'\\n';if(wa)wa.href='https://wa.me/?text='+encodeURIComponent(TX+U);function rr(x,a,b,w,h,r){x.beginPath();x.moveTo(a+r,b);x.arcTo(a+w,b,a+w,b+h,r);x.arcTo(a+w,b+h,a,b+h,r);x.arcTo(a,b+h,a,b,r);x.arcTo(a,b,a+w,b,r);x.closePath()}function draw(){var c=document.createElement('canvas');c.width=1080;c.height=1350;var x=c.getContext('2d'),g=x.createLinearGradient(0,0,0,1350);g.addColorStop(0,'#2FA9EA');g.addColorStop(.5,'#1583D2');g.addColorStop(1,'#0A4F92');x.fillStyle=g;x.fillRect(0,0,1080,1350);x.direction='rtl';x.textAlign='center';x.textBaseline='alphabetic';x.save();x.setLineDash([2,22]);x.lineCap='round';x.lineWidth=5;x.strokeStyle='rgba(255,255,255,.45)';x.beginPath();x.arc(540,1010,820,Math.PI*1.18,Math.PI*1.82);x.stroke();x.restore();x.fillStyle='rgba(255,228,138,.28)';x.beginPath();x.arc(540,190,54,0,7);x.fill();x.fillStyle='#FFE48A';x.beginPath();x.arc(540,190,26,0,7);x.fill();x.fillStyle='#FFE48A';x.font='900 150px Heebo,Assistant,sans-serif';x.shadowColor='rgba(4,36,74,.35)';x.shadowBlur=26;x.shadowOffsetY=8;x.fillText('שבת שלום',540,420);x.fillStyle='#fff';x.font='700 58px Heebo,Assistant,sans-serif';x.shadowBlur=14;x.fillText('זמני השבת ב'+P.n,540,520);x.shadowColor='transparent';x.shadowBlur=0;x.shadowOffsetY=0;x.font='600 40px Assistant,Heebo,sans-serif';x.fillStyle='#EAF6FF';x.fillText('ערב שבת '+first.dt,540,584);[[570,'כניסת שבת',first.c],[80,'צאת השבת',first.h]].forEach(function(b){x.fillStyle='#fff';rr(x,b[0],660,430,300,44);x.fill();x.fillStyle='#3A5D7C';x.font='700 46px Heebo,Assistant,sans-serif';x.fillText(b[1],b[0]+215,752);x.fillStyle='#0B2E4F';x.font='900 132px Heebo,Assistant,sans-serif';x.fillText(b[2],b[0]+215,900)});x.fillStyle='#fff';rr(x,372,1080,92,92,24);x.fill();x.save();x.translate(372+14,1080+12);x.scale(2,2);x.strokeStyle='#1E9BE4';x.lineWidth=5.6;x.lineCap='round';x.lineJoin='round';x.stroke(new Path2D('M23 26.5V13.5A7 7 0 0 0 9 13.5V22.5Q9 26.5 5 26.5'));x.fillStyle='#1E9BE4';x.beginPath();x.arc(16,19.4,2.6,0,7);x.fill();x.restore();x.textAlign='right';x.fillStyle='#fff';x.font='900 76px Heebo,Assistant,sans-serif';x.fillText('תפילה',708,1152);x.textAlign='center';x.fillStyle='#fff';rr(x,390,1212,300,76,38);x.fill();x.direction='ltr';x.fillStyle='#0A5CA8';x.font='700 42px Assistant,Heebo,sans-serif';x.fillText('tfilah.com',540,1264);return c}if(im)im.onclick=function(){im.disabled=true;var ft=document.fonts&&document.fonts.load?Promise.all([document.fonts.load('900 100px Heebo'),document.fonts.load('700 50px Heebo'),document.fonts.load('700 40px Assistant')]):Promise.resolve();ft.catch(function(){}).then(function(){draw().toBlob(function(bl){im.disabled=false;if(!bl)return;var f=new File([bl],'shabbat-'+(P.s||'times')+'.png',{type:'image/png'});if(navigator.canShare&&navigator.canShare({files:[f]})){navigator.share({files:[f],text:TX+U}).catch(function(){});return}var a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download=f.name;document.body.appendChild(a);a.click();a.remove();if(ms)ms.textContent='התמונה נשמרה. אפשר לשלוח אותה בוואטסאפ.'},'image/png')})};"
SH_JS = ("(function(){try{var P=__P__,MON=['בינואר','בפברואר','במרץ','באפריל','במאי','ביוני','ביולי','באוגוסט','בספטמבר','באוקטובר','בנובמבר','בדצמבר'];" + SH_CALC +
         "var f0=friday(P),rows=[],first=null;for(var i=0;i<30;i++){var w=week(P,f0+i*7*864e5);if(!w)continue;if(!first)first=w;"
         "var dt=w.f.getUTCDate()+' '+MON[w.f.getUTCMonth()]+' '+w.f.getUTCFullYear();w.dt=dt;"
         "rows.push('<tr'+(rows.length?'':' class=\"now\"')+'><td>'+dt+'</td><td><b>'+w.c+'</b></td><td><b>'+w.h+'</b></td><td>'+w.r+'</td></tr>')}"
         "if(!first)return;var tb=document.querySelector('.zt tbody');if(tb)tb.innerHTML=rows.join('');var n=document.querySelectorAll('.znow b');"
         "if(n.length>2){n[0].textContent=first.c;n[1].textContent=first.h;n[2].textContent=first.r}"
         "var set=function(id,v){var e=document.getElementById(id);if(e)e.textContent=v};set('zwhen','ערב שבת '+first.dt);set('zq1',first.c);set('zq2',first.h);set('zq3',first.dt);"
         + SHARE_JS + "}catch(e){}})();")
SH_HUB_JS = ("(function(){try{" + SH_CALC + "document.querySelectorAll('.cards li[data-p]').forEach(function(li){var a=li.getAttribute('data-p').split(','),P={lat:+a[0],lon:+a[1],tz:a[2],m:+a[3]},"
             "w=week(P,friday(P)),s=li.querySelector('small');if(w&&s)s.textContent='כניסה '+w.c+' · יציאה '+w.h})}catch(e){}})();")
sh_links = [(f"/zmanei-shabbat/{c[0]}/", "זמני שבת ב" + c[1]) for c in SH_CITIES]
for c in SH_CITIES:
    slug, name, lat, lon, tz, mins = c; rows = shabbat_rows(c)
    if not rows: continue
    s0, f0, cand, hav, rt = rows[0]
    dtxt = lambda d: f"{d.day} {HEMON[d.month - 1]} {d.year}"
    body = (f'<p class="note">שבת הקרובה: <b id="zwhen">ערב שבת {dtxt(f0)}</b></p>'
            f'<div class="znow"><div><span>כניסת שבת</span><b>{cand}</b></div>'
            f'<div><span>יציאת שבת</span><b>{hav}</b></div><div><span>רבנו תם</span><b>{rt}</b></div></div>'
            + SHARE_HTML +
            f'<p class="note" style="margin-block-start:0">הדלקת נרות {mins} דקות לפני השקיעה. יציאת שבת בצאת הכוכבים. רבנו תם 72 דקות אחרי השקיעה.</p>'
            f'<h2 class="sec">זמני כניסת ויציאת שבת ב{esc(name)} לשבתות הקרובות</h2>'
            '<table class="zt"><thead><tr><th scope="col">ערב שבת</th><th scope="col">כניסה</th><th scope="col">יציאה</th><th scope="col">ר״ת</th></tr></thead><tbody>'
            + "".join(f'<tr data-s="{s.isoformat()}"{chr(32)+"class="+chr(34)+"now"+chr(34) if i == 0 else ""}><td>{dtxt(f)}</td><td><b>{a}</b></td><td><b>{b}</b></td><td>{r_}</td></tr>' for i, (s, f, a, b, r_) in enumerate(rows))
            + '</tbody></table>'
            f'<h2 class="sec">מתי נכנסת ומתי יוצאת שבת ב{esc(name)}?</h2>'
            f'<div class="prose"><p>השבת הקרובה ב{esc(name)}, ערב שבת <span id="zq3">{dtxt(f0)}</span>, נכנסת בשעה <b id="zq1">{cand}</b> (הדלקת נרות) ויוצאת במוצאי שבת בשעה <b id="zq2">{hav}</b>. '
            f'הדף מחשב את הזמנים מחדש בכל כניסה, כך שתמיד מוצגת השבת הקרובה.</p></div>'
            f'<p class="note">הזמנים מחושבים לפי מיקום {esc(name)} ושעון המקום, ועשויים לסטות בדקה או שתיים מלוחות אחרים. הדלקת נרות לפי המנהג המקובל במקום ({mins} דקות לפני השקיעה). למעשה יש להחמיר ולהקדים.</p>'
            + chips("לקראת שבת", [("/siddur/", "סידור תפילה"), ("/tehillim/", "ספר תהילים"), ("/tehillim/yomi/", "תהילים יומי"), ("/tehillim-yachad/", "תהילים יחד"), (f"/zmanei-hayom/{slug}/", "זמני היום ב" + name), ("/zmanei-shabbat/", "זמני שבת בכל הערים")])
            + chips("ערים נוספות", (lambda i: [sh_links[(i + k) % len(sh_links)] for k in range(1, 13)])(next(n for n, l in enumerate(sh_links) if l[0] == f"/zmanei-shabbat/{slug}/"))))
    page(f"/zmanei-shabbat/{slug}/", f"זמני שבת ב{name}: כניסת שבת ויציאת שבת השבוע | {BRAND}",
         f"מתי נכנסת ומתי יוצאת שבת ב{name}: שעת הדלקת נרות, שעת צאת השבת וזמן רבנו תם לשבת הקרובה, ולוח זמנים לשבתות הבאות, מחושב לפי מיקום העיר.",
         f"זמני שבת ב{name}", [("זמני שבת", "/zmanei-shabbat/"), (name, f"/zmanei-shabbat/{slug}/")], after=body, hub=True, prio="0.8", script=SH_JS.replace("__P__", json.dumps({"lat": lat, "lon": lon, "tz": tz, "m": mins, "n": name, "s": slug}, ensure_ascii=False)),
         app_hash="home", app_label="לכל זמני היום באפליקציה", lead=f"כניסת שבת ויציאת שבת ב{name}, מתעדכן לכל שבת.",
         ld=[{"@type": "WebPage", "name": f"זמני שבת ב{name}", "url": SITE + f"/zmanei-shabbat/{slug}/", "inLanguage": "he", "isPartOf": WEBSITE,
              "about": {"@type": "Place", "name": name, "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon}}}])

# ---------- the day's times, a page per city: /zmanei-hayom/<city>/ ----------
# Same rules as the app's zmanim(): proportional hours from sunrise to sunset; dawn and Rabbenu Tam 72 proportional
# minutes; nightfall 13.5 proportional minutes after sunset. One more row gives nightfall at 8.5 degrees.
def sun_rise_set(d, lat, lon, zen, rising):
    y0 = datetime.datetime(d.year, 1, 1); N = (datetime.datetime(d.year, d.month, d.day) - y0).days + 1
    lh = lon / 15; t = N + ((6 if rising else 18) - lh) / 24; M = .9856 * t - 3.289; r = math.radians
    L = (M + 1.916 * math.sin(r(M)) + .02 * math.sin(r(2 * M)) + 282.634) % 360
    RA = math.degrees(math.atan(.91764 * math.tan(r(L)))) % 360
    RA = (RA + math.floor(L / 90) * 90 - math.floor(RA / 90) * 90) / 15
    sD = .39782 * math.sin(r(L)); cD = math.cos(math.asin(sD))
    cH = (math.cos(r(zen)) - sD * math.sin(r(lat))) / (cD * math.cos(r(lat)))
    if not -1 <= cH <= 1: return None
    H = (360 - math.degrees(math.acos(cH)) if rising else math.degrees(math.acos(cH))) / 15
    ut = (H + RA - .06571 * t - 6.622 - lh) % 24
    base = datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc)
    ms = base + datetime.timedelta(hours=ut); noon = base + datetime.timedelta(hours=12 - lh)
    while (ms - noon).total_seconds() > 43200: ms -= datetime.timedelta(days=1)
    while (noon - ms).total_seconds() > 43200: ms += datetime.timedelta(days=1)
    return ms


DAY_ROWS = [("alot", "עלות השחר", "72 דקות זמניות לפני הנץ"), ("talit", "זמן טלית ותפילין", "60 דקות זמניות לפני הנץ"),
            ("netz", "הנץ החמה", "זריחה, בגובה פני הים"), ("shmaM", "סוף זמן קריאת שמע (מג״א)", "3 שעות זמניות מעלות השחר"),
            ("shmaG", "סוף זמן קריאת שמע (גר״א)", "3 שעות זמניות מהנץ"), ("tfila", "סוף זמן תפילה (גר״א)", "4 שעות זמניות מהנץ"),
            ("chatzot", "חצות היום", "אמצע היום"), ("mg", "מנחה גדולה", "חצי שעה זמנית אחרי חצות"), ("mk", "מנחה קטנה", "9.5 שעות זמניות מהנץ"),
            ("plag", "פלג המנחה", "10.75 שעות זמניות מהנץ"), ("shkia", "שקיעה", "בגובה פני הים"),
            ("tzet", "צאת הכוכבים", "13.5 דקות זמניות אחרי השקיעה"), ("tzet85", "צאת הכוכבים לחומרה", "השמש 8.5° מתחת לאופק"),
            ("rt", "צאת הכוכבים לרבנו תם", "72 דקות זמניות אחרי השקיעה")]


def day_times(c, d):
    _, _, lat, lon, tz, _m = c
    rise, sset = sun_rise_set(d, lat, lon, 90.833, True), sun_rise_set(d, lat, lon, 90.833, False)
    if not rise or not sset: return None
    hr = (sset - rise) / 12; alot = rise - hr * 1.2; rt = sset + hr * 1.2; mga = (rt - alot) / 12
    t85 = sun_rise_set(d, lat, lon, 98.5, False)
    v = {"alot": alot, "talit": rise - hr, "netz": rise, "shmaM": alot + 3 * mga, "shmaG": rise + 3 * hr, "tfila": rise + 4 * hr, "chatzot": rise + 6 * hr,
         "mg": rise + 6.5 * hr, "mk": rise + 9.5 * hr, "plag": rise + 10.75 * hr, "shkia": sset, "tzet": sset + hr * (13.5 / 60), "tzet85": t85, "rt": rt}
    z = ZoneInfo(tz)
    return {k: (x.astimezone(z).strftime("%H:%M") if x else "") for k, x in v.items()}


HEDAY = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "שבת", "יום ראשון"]
DAY_CALC = ("function R(d){return d*Math.PI/180}function G(r){return r*180/Math.PI}"
            "function sun(P,y,m,d,zen,up){var N=Math.floor((Date.UTC(y,m-1,d)-Date.UTC(y,0,0))/864e5),lh=P.lon/15,t=N+((up?6:18)-lh)/24,M=.9856*t-3.289;"
            "var L=(M+1.916*Math.sin(R(M))+.02*Math.sin(R(2*M))+282.634)%360;if(L<0)L+=360;var RA=G(Math.atan(.91764*Math.tan(R(L))))%360;if(RA<0)RA+=360;"
            "RA=(RA+Math.floor(L/90)*90-Math.floor(RA/90)*90)/15;var sD=.39782*Math.sin(R(L)),cD=Math.cos(Math.asin(sD)),cH=(Math.cos(R(zen))-sD*Math.sin(R(P.lat)))/(cD*Math.cos(R(P.lat)));"
            "if(cH>1||cH<-1)return null;var H=(up?360-G(Math.acos(cH)):G(Math.acos(cH)))/15,ut=(H+RA-.06571*t-6.622-lh)%24;if(ut<0)ut+=24;var ms=Date.UTC(y,m-1,d)+ut*36e5,noon=Date.UTC(y,m-1,d)+(12-lh)*36e5;"
            "while(ms-noon>432e5)ms-=864e5;while(noon-ms>432e5)ms+=864e5;return ms}"
            "function hm(P,ms){return ms==null?'':new Intl.DateTimeFormat('he-IL',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:P.tz}).format(new Date(ms))}"
            "function today(P){var o={};new Intl.DateTimeFormat('en-CA',{timeZone:P.tz,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).forEach(function(x){o[x.type]=x.value});return Date.UTC(+o.year,+o.month-1,+o.day)}"
            "function day(P,ms){var D=new Date(ms),y=D.getUTCFullYear(),m=D.getUTCMonth()+1,d=D.getUTCDate(),r=sun(P,y,m,d,90.833,1),s=sun(P,y,m,d,90.833,0);if(r==null||s==null)return null;"
            "var h=(s-r)/12,a=r-h*1.2,rt=s+h*1.2,g=(rt-a)/12;return{alot:a,talit:r-h,netz:r,shmaM:a+3*g,shmaG:r+3*h,tfila:r+4*h,chatzot:r+6*h,mg:r+6.5*h,mk:r+9.5*h,plag:r+10.75*h,shkia:s,tzet:s+h*.225,tzet85:sun(P,y,m,d,98.5,0),rt:rt}}")
DAY_JS = ("(function(){try{var P=__P__,MON=['בינואר','בפברואר','במרץ','באפריל','במאי','ביוני','ביולי','באוגוסט','בספטמבר','באוקטובר','בנובמבר','בדצמבר'],WD=['יום ראשון','יום שני','יום שלישי','יום רביעי','יום חמישי','יום שישי','שבת'];" + DAY_CALC +
          "var t0=today(P),v=day(P,t0);if(!v)return;var dt=function(ms){var D=new Date(ms);return WD[D.getUTCDay()]+', '+D.getUTCDate()+' '+MON[D.getUTCMonth()]+' '+D.getUTCFullYear()};"
          "document.querySelectorAll('[data-z]').forEach(function(e){var k=e.getAttribute('data-z');if(k==='date')e.textContent=dt(t0);else if(v[k]!=null)e.textContent=hm(P,v[k])});"
          "var now=Date.now(),nx=null;document.querySelectorAll('.zday tr[data-k]').forEach(function(tr){var k=tr.getAttribute('data-k');tr.className='';if(!nx&&v[k]!=null&&v[k]>=now){nx=tr;tr.className='now'}});"
          "var tb=document.querySelector('.zweek tbody');if(tb){var rows=[];for(var i=0;i<7;i++){var w=day(P,t0+i*864e5);if(!w)continue;"
          "rows.push('<tr'+(i?'':' class=\"now\"')+'><td>'+dt(t0+i*864e5).replace(/ \\d{4}$/,'')+'</td><td>'+hm(P,w.netz)+'</td><td>'+hm(P,w.shmaG)+'</td><td>'+hm(P,w.chatzot)+'</td><td><b>'+hm(P,w.shkia)+'</b></td><td>'+hm(P,w.tzet)+'</td></tr>')}tb.innerHTML=rows.join('')}"
          "}catch(e){}})();")
DAY_HUB_JS = ("(function(){try{" + DAY_CALC + "document.querySelectorAll('.cards li[data-p]').forEach(function(li){var a=li.getAttribute('data-p').split(','),P={lat:+a[0],lon:+a[1],tz:a[2]},"
              "v=day(P,today(P)),s=li.querySelector('small');if(v&&s)s.textContent='הנץ '+hm(P,v.netz)+' · שקיעה '+hm(P,v.shkia)})}catch(e){}})();")
_today = datetime.date.today()
_dtxt = lambda d: f"{HEDAY[d.weekday()]}, {d.day} {HEMON[d.month - 1]} {d.year}"
day_links = [(f"/zmanei-hayom/{c[0]}/", "זמני היום ב" + c[1]) for c in SH_CITIES]
for c in SH_CITIES:
    slug, name, lat, lon, tz, _mins = c; v = day_times(c, _today)
    if not v: continue
    week = [(d, day_times(c, d)) for d in (_today + datetime.timedelta(days=i) for i in range(7))]
    body = (f'<p class="note">היום: <b data-z="date">{_dtxt(_today)}</b></p>'
            f'<div class="znow"><div><span>הנץ החמה</span><b data-z="netz">{v["netz"]}</b></div><div><span>שקיעה</span><b data-z="shkia">{v["shkia"]}</b></div>'
            f'<div><span>צאת הכוכבים</span><b data-z="tzet">{v["tzet"]}</b></div></div>'
            f'<h2 class="sec">כל זמני היום ב{esc(name)}</h2>'
            '<table class="zt zday"><thead><tr><th scope="col">הזמן</th><th scope="col">שעה</th><th scope="col">לפי</th></tr></thead><tbody>'
            + "".join(f'<tr data-k="{k}"><td>{esc(lbl)}</td><td><b data-z="{k}">{v[k]}</b></td><td><small>{esc(how)}</small></td></tr>' for k, lbl, how in DAY_ROWS if v[k])
            + '</tbody></table>'
            f'<h2 class="sec">זמני היום ב{esc(name)} לשבוע הקרוב</h2>'
            '<div class="zscroll" tabindex="0" role="region" aria-label="לוח זמני היום לשבוע הקרוב"><table class="zt zweek"><thead><tr><th scope="col">יום</th><th scope="col">הנץ</th><th scope="col">סוף ק״ש</th><th scope="col">חצות</th><th scope="col">שקיעה</th><th scope="col">צאת</th></tr></thead><tbody>'
            + "".join(f'<tr{chr(32) + "class=" + chr(34) + "now" + chr(34) if i == 0 else ""}><td>{_dtxt(d).rsplit(" ", 1)[0]}</td><td>{w["netz"]}</td><td>{w["shmaG"]}</td><td>{w["chatzot"]}</td><td><b>{w["shkia"]}</b></td><td>{w["tzet"]}</td></tr>' for i, (d, w) in enumerate(week) if w)
            + '</tbody></table></div>'
            f'<h2 class="sec">שאלות נפוצות על זמני היום ב{esc(name)}</h2><div class="prose">'
            f'<h3>מתי השקיעה היום ב{esc(name)}?</h3><p>השקיעה ב{esc(name)} היום בשעה <b data-z="shkia">{v["shkia"]}</b>, וצאת הכוכבים בשעה <b data-z="tzet">{v["tzet"]}</b>.</p>'
            f'<h3>עד מתי אפשר לקרוא קריאת שמע של שחרית?</h3><p>סוף זמן קריאת שמע ב{esc(name)} היום: <b data-z="shmaM">{v["shmaM"]}</b> לפי המגן אברהם, ו-<b data-z="shmaG">{v["shmaG"]}</b> לפי הגר״א. סוף זמן תפילה לפי הגר״א: <b data-z="tfila">{v["tfila"]}</b>.</p>'
            f'<h3>ממתי אפשר להתפלל מנחה?</h3><p>ממנחה גדולה, היום בשעה <b data-z="mg">{v["mg"]}</b>, ועד השקיעה.</p>'
            '<h3>איך מחושבים הזמנים?</h3><p>היום מתחלק ל-12 שעות זמניות, מהנץ החמה ועד השקיעה. עלות השחר וצאת הכוכבים לרבנו תם הם 72 דקות זמניות לפני הנץ ואחרי השקיעה. '
            'צאת הכוכבים מחושב 13.5 דקות זמניות אחרי השקיעה, כמקובל בלוחות של עדות המזרח, ולצידו מוצג גם הזמן המחמיר, כשהשמש 8.5 מעלות מתחת לאופק. '
            'הנץ והשקיעה מחושבים בגובה פני הים, בלי התחשבות בהרים שמסתירים את האופק. הדף מחשב את הזמנים מחדש בכל כניסה, כך שתמיד מוצג היום הנוכחי.</p></div>'
            f'<p class="note">הזמנים מחושבים לפי מיקום {esc(name)} ושעון המקום, ועשויים לסטות בדקה או שתיים מלוחות אחרים. בכל דבר שתלוי בזמן יש להחמיר, ובשאלה למעשה לשאול רב.</p>'
            + chips("עוד ל" + name, [(f"/zmanei-shabbat/{slug}/", "זמני שבת ב" + name), ("/siddur/mizrach/shacharit/", "תפילת שחרית"), ("/siddur/mizrach/mincha/", "תפילת מנחה"), ("/siddur/mizrach/arvit/", "תפילת ערבית"), ("/zmanei-hayom/", "זמני היום בכל הערים")])
            + chips("ערים נוספות", (lambda k: [day_links[(k + j) % len(day_links)] for j in range(1, 13)])([l[0] for l in day_links].index(f"/zmanei-hayom/{slug}/"))))
    page(f"/zmanei-hayom/{slug}/", f"זמני היום ב{name}: הנץ החמה, שקיעה וצאת הכוכבים | {BRAND}",
         fit_desc(f"זמני היום ב{name} להיום: עלות השחר, הנץ החמה, סוף זמן קריאת שמע ותפילה, חצות, מנחה גדולה, פלג המנחה, שקיעה וצאת הכוכבים", tails=("מתעדכן בכל יום, עם לוח לשבוע הקרוב.", "מתעדכן בכל יום.")),
         f"זמני היום ב{name}", [("זמני היום", "/zmanei-hayom/"), (name, f"/zmanei-hayom/{slug}/")], after=body, hub=True, prio="0.8",
         script=DAY_JS.replace("__P__", json.dumps({"lat": lat, "lon": lon, "tz": tz})), app_hash="home", app_label="לזמני היום באפליקציה, עם תזכורות",
         lead=f"כל זמני היום ב{name}, מתעדכן בכל יום.",
         ld=[{"@type": "WebPage", "name": f"זמני היום ב{name}", "url": SITE + f"/zmanei-hayom/{slug}/", "inLanguage": "he", "isPartOf": WEBSITE,
              "about": {"@type": "Place", "name": name, "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon}}}])

_jr = day_times(SH_CITIES[0], _today)
dayhub = ('<ul class="cards">' + "".join(f'<li data-p="{c[2]},{c[3]},{c[4]}"><a href="/zmanei-hayom/{c[0]}/"><b>{esc(c[1])}</b><small>הנץ {day_times(c, _today)["netz"]} · שקיעה {day_times(c, _today)["shkia"]}</small></a></li>' for c in SH_CITIES if day_times(c, _today)) + "</ul>"
          '<div class="prose"><h2>מה כולל לוח זמני היום</h2><p>לכל עיר: עלות השחר, זמן טלית ותפילין, הנץ החמה, סוף זמן קריאת שמע לפי המגן אברהם ולפי הגר״א, סוף זמן תפילה, חצות, מנחה גדולה, מנחה קטנה, פלג המנחה, שקיעה וצאת הכוכבים, וגם לוח לשבוע הקרוב. הזמנים מחושבים מחדש בכל כניסה לדף.</p></div>'
          + chips("קשור", [("/zmanei-shabbat/", "זמני כניסת ויציאת שבת"), ("/siddur/", "סידור תפילה"), ("/tehillim/", "ספר תהילים")]))
page("/zmanei-hayom/", f"זמני היום לפי עיר: הנץ החמה, שקיעה וצאת הכוכבים | {BRAND}",
     fit_desc(f"זמני היום ב-{len(SH_CITIES)} ערים: הנץ החמה, סוף זמן קריאת שמע ותפילה, חצות, מנחה גדולה, שקיעה וצאת הכוכבים. בירושלים היום: הנץ {_jr['netz']}, שקיעה {_jr['shkia']}", tails=("מתעדכן בכל יום.",)),
     "זמני היום", [("זמני היום", "/zmanei-hayom/")], after=dayhub, hub=True, prio="0.9", app_hash="home", app_label="לזמני היום באפליקציה", script=DAY_HUB_JS,
     lead=f"{len(SH_CITIES)} ערים. בוחרים עיר ורואים את כל זמני היום, מעלות השחר ועד צאת הכוכבים.",
     ld=[{"@type": "CollectionPage", "name": "זמני היום", "url": SITE + "/zmanei-hayom/", "inLanguage": "he", "isPartOf": WEBSITE,
          "mainEntity": item_list([f"/zmanei-hayom/{c[0]}/" for c in SH_CITIES])}])

jr = shabbat_rows(SH_CITIES[0])[0]
shhub = ('<ul class="cards">' + "".join(f'<li data-p="{c[2]},{c[3]},{c[4]},{c[5]}"><a href="/zmanei-shabbat/{c[0]}/"><b>{esc(c[1])}</b><small>כניסה {shabbat_rows(c, 1)[0][2]} · יציאה {shabbat_rows(c, 1)[0][3]}</small></a></li>' for c in SH_CITIES) + '</ul>'
         '<p class="note">הזמנים בכרטיסים הם לשבת הקרובה, ומתעדכנים מעצמם בכל שבוע. בדף של כל עיר יש גם לוח לשבתות הבאות.</p>'
         '<div class="prose"><h2>מתי יוצאת שבת השבוע?</h2><p>צאת השבת משתנה מעיר לעיר ומשבוע לשבוע, כי היא תלויה בשעת השקיעה במקום. '
         'בחרו עיר מהרשימה כדי לראות את שעת כניסת השבת (הדלקת נרות), את שעת צאת השבת במוצאי שבת ואת זמן רבנו תם.</p></div>')
page("/zmanei-shabbat/", f"זמני כניסת שבת ויציאת שבת השבוע, לפי עיר | {BRAND}",
     "מתי נכנסת שבת ומתי יוצאת שבת השבוע: זמני הדלקת נרות, צאת שבת ומוצאי שבת בירושלים, תל אביב, חיפה, באר שבע ובעוד עשרות ערים. מתעדכן מעצמו בכל שבוע.",
     "זמני כניסת ויציאת שבת", [("זמני שבת", "/zmanei-shabbat/")], after=shhub, hub=True, prio="0.9", app_hash="home", app_label="לזמני היום באפליקציה", script=SH_HUB_JS,
     lead=f"{len(SH_CITIES)} ערים. בוחרים עיר ורואים מתי נכנסת ומתי יוצאת השבת.",
     ld=[{"@type": "CollectionPage", "name": "זמני כניסת ויציאת שבת", "url": SITE + "/zmanei-shabbat/", "inLanguage": "he", "isPartOf": WEBSITE,
          "mainEntity": item_list([f"/zmanei-shabbat/{c[0]}/" for c in SH_CITIES])}])

# ---------- Chanukah: one entry page for the candle-lighting blessings, in all three nusachim ----------
PID = {q["id"]: q for n in NUS for q in by_nus[n]}
CH_SETS = [("mizrach", ["mizrach-100"]), ("sefard", ["sefard-183"]), ("ashkenaz", ["ashkenaz-422", "ashkenaz-423", "ashkenaz-424"])]
ch_text, ch_links = "", []
for n, ids in CH_SETS:
    ch_text += f'<h2 id="{n}">נוסח {esc(NUS[n])}</h2>'
    for pid in ids:
        q = PID[pid]; _ps = TEXTS[n][pid]
        _sh = _ps[1:] if len(_ps) > 1 and _pl(_ps[0]) == _pl(q["t"]) else _ps
        if len(ids) > 1: ch_text += f'<h3>{esc(q["t"])}</h3>'
        ch_text += "".join(f"<p>{clean(x)}</p>" for x in _sh)
        ch_links.append((f"{PURL[pid]}", f'{q["t"]} · נוסח {NUS[n]}'))
CH_NIGHTS = [(o, ("מוצאי שבת" if w == "שבת" else f"יום {w}") + f", {4 + i} בדצמבר", "שלוש" if i == 0 else "שתיים") for i, (o, w) in enumerate(
    [("ראשון", "שישי"), ("שני", "שבת"), ("שלישי", "ראשון"), ("רביעי", "שני"), ("חמישי", "שלישי"), ("שישי", "רביעי"), ("שביעי", "חמישי"), ("שמיני", "שישי")])]
ch_before = ('<div class="prose"><p>מדליקים נר אחד בלילה הראשון ומוסיפים נר בכל לילה, עד שמונה נרות. מברכים, מדליקים, ומניחים את החנוכייה במקום שרואים אותה מבחוץ. '
             'בלילה הראשון מברכים שלוש ברכות, ובשאר הלילות שתיים.</p>'
             '<p>בשנת תשפ״ז הנר הראשון מודלק ביום שישי, 4 בדצמבר 2026, והנר השמיני ביום שישי, 11 בדצמבר 2026. בערב שבת מדליקים את נרות החנוכה לפני נרות השבת.</p>'
             '<h2 id="matai">מתי מדליקים נרות חנוכה תשפ״ז (2026)</h2>'
             '<table class="zt zday"><thead><tr><th scope="col">נר</th><th scope="col">הערב של</th><th scope="col">ברכות</th></tr></thead><tbody>'
             + "".join(f'<tr><td>נר {o}</td><td>{d}</td><td>{b}</td></tr>' for o, d, b in CH_NIGHTS)
             + '</tbody></table></div>'
             '<div class="related jr" style="margin-block-end:1rem">' + "".join(f'<a href="#{n}">נוסח {esc(NUS[n])}</a>' for n, _ in CH_SETS) + "</div>")
CH_JS = "(function(){try{var U=location.origin+'/chanukah/?utm_source=chanukah',wa=document.getElementById('zwa'),im=document.getElementById('zim'),ms=document.getElementById('zmsg');var ORD=['ראשון','שני','שלישי','רביעי','חמישי','שישי','שביעי','שמיני'];function hd(d){var o={};new Intl.DateTimeFormat('en-u-ca-hebrew',{month:'long',day:'numeric',timeZone:'Asia/Jerusalem'}).formatToParts(d).forEach(function(x){o[x.type]=x.value});return o}function night(now){for(var k=0;k<8;k++){var h=hd(new Date(+now+864e5-k*864e5));if(h.month==='Kislev'&&+h.day===25)return k+1}return 0}var N=0;try{N=night(new Date())}catch(e){}var TX=N?'חנוכה שמח 🕎\\nהערב מדליקים נר '+ORD[N-1]+' של חנוכה.\\nברכות ההדלקה, הנרות הללו ומעוז צור:\\n':'חנוכה שמח 🕎\\nברכות הדלקת נרות חנוכה, הנרות הללו ומעוז צור, בשלושה נוסחים:\\n';if(wa)wa.href='https://wa.me/?text='+encodeURIComponent(TX+U);function rr(x,a,b,w,h,r){x.beginPath();x.moveTo(a+r,b);x.arcTo(a+w,b,a+w,b+h,r);x.arcTo(a+w,b+h,a,b+h,r);x.arcTo(a,b+h,a,b,r);x.arcTo(a,b,a+w,b,r);x.closePath()}function flame(x,cx,cy,s){x.fillStyle='rgba(255,228,138,.3)';x.beginPath();x.arc(cx,cy-6*s,30*s,0,7);x.fill();x.fillStyle='#FFE48A';x.beginPath();x.moveTo(cx,cy-40*s);x.bezierCurveTo(cx+22*s,cy-12*s,cx+16*s,cy+12*s,cx,cy+12*s);x.bezierCurveTo(cx-16*s,cy+12*s,cx-22*s,cy-12*s,cx,cy-40*s);x.fill()}function draw(){var c=document.createElement('canvas');c.width=1080;c.height=1350;var x=c.getContext('2d'),g=x.createLinearGradient(0,0,0,1350);g.addColorStop(0,'#1F8FD9');g.addColorStop(.55,'#0F62B0');g.addColorStop(1,'#072F66');x.fillStyle=g;x.fillRect(0,0,1080,1350);x.direction='rtl';x.textAlign='center';x.fillStyle='#FFE48A';x.font='900 150px Heebo,Assistant,sans-serif';x.shadowColor='rgba(4,36,74,.4)';x.shadowBlur=26;x.shadowOffsetY=8;x.fillText('חנוכה שמח',540,250);x.fillStyle='#fff';x.font='700 60px Heebo,Assistant,sans-serif';x.shadowBlur=14;x.fillText(N?'נר '+ORD[N-1]+' של חנוכה':'ברכות הדלקת נרות חנוכה',540,352);x.shadowColor='transparent';x.shadowBlur=0;x.shadowOffsetY=0;var base=900,xs=[];for(var i=0;i<9;i++)xs.push(940-i*100);x.fillStyle='#fff';rr(x,110,base,860,26,13);x.fill();rr(x,440,base+26,200,60,16);x.fill();rr(x,330,base+86,420,26,13);x.fill();for(var j=0;j<9;j++){var sh=j===4,pos=j<4?j:j-1,lit=sh||(N?pos<N:true),h=sh?330:250,cx=xs[j];x.globalAlpha=lit?1:.38;x.fillStyle='#fff';rr(x,cx-19,base-h,38,h,12);x.fill();x.globalAlpha=1;if(lit)flame(x,cx,base-h-22,sh?1.15:1)}x.fillStyle='#EAF6FF';x.font='600 44px Assistant,Heebo,sans-serif';x.fillText('ברכות ההדלקה בניקוד מלא, בשלושה נוסחים',540,1072);x.fillStyle='#fff';rr(x,372,1112,92,92,24);x.fill();x.save();x.translate(386,1124);x.scale(2,2);x.strokeStyle='#1E9BE4';x.lineWidth=5.6;x.lineCap='round';x.lineJoin='round';x.stroke(new Path2D('M23 26.5V13.5A7 7 0 0 0 9 13.5V22.5Q9 26.5 5 26.5'));x.fillStyle='#1E9BE4';x.beginPath();x.arc(16,19.4,2.6,0,7);x.fill();x.restore();x.textAlign='right';x.fillStyle='#fff';x.font='900 76px Heebo,Assistant,sans-serif';x.fillText('תפילה',708,1184);x.textAlign='center';x.fillStyle='#fff';rr(x,300,1232,480,70,35);x.fill();x.direction='ltr';x.fillStyle='#0A5CA8';x.font='700 40px Assistant,Heebo,sans-serif';x.fillText('tfilah.com/chanukah',540,1281);return c}if(im)im.onclick=function(){im.disabled=true;var ft=document.fonts&&document.fonts.load?Promise.all([document.fonts.load('900 100px Heebo'),document.fonts.load('700 50px Heebo'),document.fonts.load('600 40px Assistant')]):Promise.resolve();ft.catch(function(){}).then(function(){draw().toBlob(function(bl){im.disabled=false;if(!bl)return;var f=new File([bl],'chanukah'+(N?'-'+N:'')+'.png',{type:'image/png'});if(navigator.canShare&&navigator.canShare({files:[f]})){navigator.share({files:[f],text:TX+U}).catch(function(){});return}var a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download=f.name;document.body.appendChild(a);a.click();a.remove();if(ms)ms.textContent='התמונה נשמרה. אפשר לשלוח אותה בוואטסאפ.'},'image/png')})};window.__chNight=night}catch(e){}})();"
ch_before = SHARE_HTML + ch_before
ch_after = chips("כל קטע בעמוד משלו", ch_links) + chips("עוד לחנוכה ולשבת", [("/zmanei-shabbat/", "זמני כניסת ויציאת שבת"), ("/siddur/", "סידור תפילה"), ("/tehillim/", "ספר תהילים")])
page("/chanukah/", f"ברכות הדלקת נרות חנוכה: הנוסח המלא בניקוד, בשלושה נוסחים | {BRAND}",
     "ברכות הדלקת נרות חנוכה תשפ״ז בניקוד מלא: להדליק נר חנוכה, שעשה נסים, שהחיינו, הנרות הללו ומעוז צור, בשלושה נוסחים. נר ראשון: יום שישי, 4 בדצמבר 2026.",
     "ברכות הדלקת נרות חנוכה", [("חנוכה", "/chanukah/")], text=ch_text, before=ch_before, after=ch_after, prio="0.9", app_hash=f"p-{CH_SETS[0][1][0]}",
     app_label="לסדר ההדלקה באפליקציה", lead="סדר הדלקת נרות חנוכה והברכות, בשלושת הנוסחים.", script=CH_JS,
     ld=[{"@type": "CreativeWork", "name": "ברכות הדלקת נרות חנוכה", "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + "/chanukah/", "isPartOf": WEBSITE}])


# ---------- Tisha B'Av: what the site has for the day, gathered on one page. Statements about the day are the siddurim's own printed instructions. ----------
tb = ('<div class="prose"><p>תשעה באב הוא יום הצום על חורבן בית המקדש. ריכזנו כאן את מה שיש באתר ליום הזה.</p>'
      '<h2>מגילת איכה</h2><p>המגילה שקוראים בתשעה באב, בניקוד מלא.</p></div>'
      + '<div class="related"><a href="/sefer/eicha/">מגילת איכה</a></div>'
      + '<div class="prose"><h2>תפילת ”נחם”</h2><p>בסידורים שבאתר ”נחם” מודפס בתוך תפילת העמידה, בברכת בונה ירושלים, עם ההוראה שלצידו: '
      'בנוסח עדות המזרח ”בתשעה באב מוסיפים”, ובנוסח ספרד ובנוסח אשכנז ”במנחת תשעה באב”.</p></div>'
      + '<div class="related">' + "".join(f'<a href="{PURL[i]}">{esc(l)}</a>' for i, l in [
          ("mizrach-16", "שחרית · נוסח עדות המזרח"), ("mizrach-28", "מנחה · נוסח עדות המזרח"), ("sefard-35", "מנחה · נוסח ספרד"), ("ashkenaz-120", "מנחה · נוסח אשכנז")]) + "</div>"
      + chips("קריאת התורה לתענית ציבור", [(PURL["mizrach-125"], "נוסח עדות המזרח"), (PURL["sefard-203"], "נוסח ספרד")])
      + '<div class="prose"><h2>קינות</h2><p>הקינות עדיין אינן באתר. נוסיף אותן כשתהיה בידינו מהדורה שמותר לפרסם.</p></div>'
      + chips("צומות נוספים", [(PURL[i], l) for i, l in [("mizrach-123", "סליחות לי״ז בתמוז"), ("mizrach-121", "סליחות לעשרה בטבת"), ("mizrach-120", "סליחות לצום גדליה"), ("mizrach-122", "סליחות לתענית אסתר")]]))
page("/tisha-beav/", f"תשעה באב: מגילת איכה, נחם וקריאת התורה | {BRAND}",
     "תשעה באב באתר תפילה: מגילת איכה בניקוד מלא, תפילת נחם בתוך העמידה בשלושת הנוסחים וקריאת התורה לתענית ציבור, לפי סדר היום ובאותיות נוחות לקריאה.",
     "תשעה באב", [("תשעה באב", "/tisha-beav/")], after=tb, hub=True, prio="0.7", lead="מגילת איכה, תפילת נחם וקריאת התורה ליום הצום.",
     ld=[{"@type": "CollectionPage", "name": "תשעה באב", "url": SITE + "/tisha-beav/", "inLanguage": "he", "isPartOf": WEBSITE}])


# ---------- The bride's prayer for her wedding day. The wording is the Wikisource page (data/kala.json, CC BY-SA 4.0), laid out, never edited. ----------
KALA = json.load(open(os.path.join(DATA, "kala.json"), encoding="utf-8"))


def _kala_ref(m):
    a, b = m.group(1), m.group(2)
    lab = b if b and (not b.startswith("שם") or "#" in a) else a
    assert "#" not in lab, lab
    book, verse = lab.rsplit(" ", 1)
    return f' <small>({book}, {verse})</small>'


def kala_blocks(raw):
    """the page's own markup turned into paragraphs: verse references in brackets, line breaks kept, footnotes and instructions taken aside"""
    body = re.sub(r"\[\[קטגוריה:[^\]]*\]\]", "", raw.split("\n", 1)[1])
    intro = re.search(r"\{\{הור2\|(.*?)\}\}\n", body, flags=re.S)
    body = body.replace(intro.group(0), "", 1)
    notes = []

    def note(m):
        notes.append(m.group(1))
        return ""
    body = re.sub(r"\{\{הערה\|([^{}]*)\}\}", note, body)
    out = []
    for p in re.split(r"\n\s*\n", body.strip()):
        ins = re.match(r"\{\{הור\|([^{}]*)\}\}\{\{ש\}\}\n", p)
        if ins:
            p = p[ins.end():]
        t = html.escape(p.strip(), quote=False)
        t = re.sub(r"\{\{ממס\|([^{}|]*)(?:\|([^{}]*))?\}\}", _kala_ref, t)
        t = re.sub(r"\{\{סי\|([^{}]*)\}\}", r"<b>\1</b>", t)
        t = re.sub(r"\s*\{\{ש\}\}\s*", "<br>", t)
        assert "{{" not in t and "}}" not in t and "\n" not in t, t[:80]
        out.append((html.escape(ins.group(1), quote=False) if ins else "", t))
    assert len(out) == 6 and len(notes) == 2 and out[5][0] and not any(x[0] for x in out[:5]), "the source page changed shape: read it again before publishing"
    return out, notes


_kb, _kn = kala_blocks(KALA["wikitext"])
_k_note1 = html.escape(_kn[0].split(" (ויקיעורך")[0], quote=False)
k_text = ('<h2 id="chupa">תפילת הכלה ביום חופתה</h2>' + "".join(f"<p>{t}</p>" for _, t in _kb[:2])
          + f'<p><small>{_k_note1}</small></p>' + "".join(f"<p>{t}</p>" for _, t in _kb[2:5])
          + f'<h2 id="tamid">תפילה נוספת</h2><p><small>{_kb[5][0]}</small></p><p>{_kb[5][1]}</p>')
K_JS = "(function(){var b=document.getElementById('kpr');if(b)b.onclick=function(){print()}})();"
k_before = ('<aside class="kala" aria-label="הדפסה"><svg class="kala-ic" viewBox="0 0 48 48" width="44" height="44" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<circle cx="18" cy="29" r="11"/><circle cx="30" cy="29" r="11"/><path d="m21 9 3-4 3 4-3 3z"/></svg>'
            '<h2>מדפיסים ולוקחים לחופה</h2><p>הנוסח המלא בניקוד, בעמוד נקי בלי תפריטים. אפשר להדפיס אותו או לשמור כקובץ PDF ולשלוח לכלה.</p>'
            f'<button type="button" class="kala-btn" id="kpr">{IC_PRINT}<span>הדפסה או שמירה כ-PDF</span></button></aside>'
            '<div class="prose"><p>תפילה שהכלה אומרת ביום שבו היא נכנסת לחופה. היא מבקשת בה על הבית שהיא עומדת להקים: אהבה ושלום, ילדים בריאים וברכה.</p>'
            '<p>הנוסח לקוח מהספר ”חופת חתנים” של ר׳ רפאל מילדולה. שם התפילה מיוחסת לר׳ יוסף בן סאמון, מחבר הספר ”עדות ביהוסף”.</p></div>')
k_after = ('<div class="prose"><h2 class="sec">מקורות</h2><ul>'
           f'<li>נוסח התפילה: <a href="{KALA["url"]}" target="_blank" rel="noopener">ויקיטקסט, ”תפילה לכלה ביום חופתה”</a>, מתוך הספר ”חופת חתנים”. '
           f'הטקסט מובא לפי רישיון <a href="{KALA["license_url"]}" target="_blank" rel="noopener">CC BY-SA 4.0</a>, והנוסח לא שונה. מראי המקום של הפסוקים מוצגים בסוגריים.</li>'
           '<li>במהדורת ויקיטקסט מצוין שבספר נוסף לפני ”ובכן יהי רצון” משפט ”לשם יחוד” שנאמר לקראת טבילה. הוא אינו מובא שם בגוף התפילה, וכך גם כאן.</li></ul>'
           '<p><small>האתר מביא את התפילה כפי שהיא במקור ואינו פוסק מתי ואיך לומר אותה. מי שרוצה הדרכה שואלת רב.</small></p></div>'
           + chips("עוד באתר", [("/segulat-rachel-imenu/", "סגולת רחל אמנו"), ("/nishmat-kol-chai/", "נשמת כל חי"), ("/mizmor-letoda/", "מזמור לתודה"), ("/sefer/shir/", "שיר השירים"), ("/tehillim/", "ספר תהילים"), ("/kelim/shem/", "תהילים לפי שם")]))
page("/birkat-kala/", f"ברכת כלה: תפילת הכלה ביום חופתה, מנוקד להדפסה | {BRAND}",
     "ברכת כלה בניקוד מלא: התפילה שהכלה אומרת ביום חופתה, מתוך הספר ”חופת חתנים”. עמוד נקי להדפסה או לשמירה כקובץ PDF, עם מקור הנוסח.",
     "ברכת כלה", [("ברכת כלה", "/birkat-kala/")], text=k_text, before=k_before, after=k_after, prio="0.8", script=K_JS,
     lead="תפילת הכלה ביום חופתה, בניקוד מלא. מוכנה להדפסה.",
     ld=[{"@type": "Article", "headline": "ברכת כלה: תפילת הכלה ביום חופתה", "inLanguage": "he", "url": SITE + "/birkat-kala/", "license": KALA["license_url"]}])

# ---------- About and sources ----------
TAUT_JS = open(os.path.join(ROOT, "tools", "odot.js"), encoding="utf-8").read().replace("__MAIL__", CONTACT)
TAUT_JS = re.sub(r"/\*.*?\*/", "", TAUT_JS, flags=re.S)
TAUT_JS = "".join(l.strip() + ("\n" if l.rstrip().endswith(("{", "}", ";", ",")) is False else "") for l in TAUT_JS.split("\n") if l.strip())
odot = ('<div class="prose"><h2>מה יש באתר</h2><p>תפילה הוא סידור אונליין בשלושה נוסחים, עדות המזרח, ספרד ואשכנז, עם ספר תהילים מלא, ספרייה של מגילות ופרקים, זמני היום וכלים אישיים. '
        'הקריאה חופשית, בלי הרשמה ובלי פרסומות.</p>'
        '<h2>מי מפעיל את האתר</h2><p>תפילה מופעל בידי צוות מתנדבים, לזיכוי הרבים. המטרה פשוטה: שלכל אחד יהיו סידור נוח, ספר תהילים וזמני היום בהישג יד, בחינם, בלי הרשמה ובלי פרסומות. '
        'האתר אינו פוסק הלכה ואינו בא במקום רב. לפניות ולהערות אפשר לכתוב לנו בטופס שבתחתית העמוד.</p>'
        '<h2>מקורות הטקסטים</h2><p>נוסח עדות המזרח ונוסח ספרד: מהדורות פתוחות ממאגר תורת אמת, שבנחלת הכלל. נוסח אשכנז: מאגר דעת, שבנחלת הכלל, עם השלמות מסידור מצודה ברישיון CC-BY. '
        'ספר תהילים והמגילות: Tanach.us, בנחלת הכלל. הטקסטים נאספו דרך המהדורות הפתוחות בארכיון של ספריא. '
        'בנוסח אשכנז, ”ויתן לך” מתוך סידור ושננתם, ו”במה מדליקין” מתוך תורת אמת. הפתיחה והתפילות של תיקון הכללי: מהדורת rabenubook.com. ברכת כלה: ויקיטקסט, מתוך הספר ”חופת חתנים”, ברישיון CC BY-SA 4.0.</p>'
        '<h2>איך שומרים על דיוק הטקסט</h2><p>הטקסטים אינם מוקלדים ביד. הם מועתקים מהמהדורות הפתוחות כמות שהן, ובכל עדכון של האתר נבדק אוטומטית שכל עמוד מציג בדיוק את המילים שבמהדורה, שאין קטע ריק ושאין קישור שבור. '
        'ההסברים שליד התפילות נכתבו עבור האתר ואינם חלק מהנוסח. מי שמוצא טעות יכול לדווח עליה למטה, והיא נבדקת מול המהדורה לפני שמתקנים.</p>'
        '<h2>זמני היום והלוח</h2><p>הלוח העברי, פרשת השבוע והמועדים מחושבים בספריית Hebcal. זמני היום מחושבים לפי מיקום העיר: הנץ ושקיעה אסטרונומיים, סוף זמן קריאת שמע לפי המגן אברהם ולפי הגר״א, '
        'וצאת השבת כשהשמש 8.5 מעלות מתחת לאופק. הזמנים עשויים לסטות בדקה או שתיים מלוחות אחרים, ולמעשה יש להחמיר.</p>'
        '<h2>ההסברים במילים פשוטות</h2><p>ההסברים הקצרים שליד התפילות, המזמורים והספרים נכתבו עבור האתר, כדי לתת הקשר למי שקורא. הם אינם פסק הלכה ואינם באים במקום רב.</p></div>'
        '<div class="cgrid"><section class="ccard" id="taut" aria-labelledby="tauth"><h2 id="tauth">דיווח על טעות בנוסח</h2><p>מצאתם מילה חסרה, ניקוד שגוי או קטע שלא במקומו? כתבו לנו. כל דיווח נבדק מול המהדורה שהטקסט נלקח ממנה, ורק אחר כך מתוקן.</p>'
        '<div id="tautbox" class="tautbox"></div></section>'
        '<section class="ccard" id="kesher" aria-labelledby="kesherh"><h2 id="kesherh">צור קשר</h2><p id="kesherp">' + (f'אפשר לכתוב כאן, או ישירות למייל <!--email_off--><a href="mailto:{CONTACT}">{CONTACT}</a><!--/email_off-->.' if CONTACT else 'אפשר לכתוב לנו כאן.') + '</p><p class="fmail" style="margin-block-end:.8rem"><span>לתרומות, צרו קשר: <!--email_off--><a href="mailto:team@tfilah.com" dir="ltr">team@tfilah.com</a><!--/email_off--></span><span>לפניות עסקיות: <!--email_off--><a href="mailto:business@tfilah.com" dir="ltr">business@tfilah.com</a><!--/email_off--></span></p><div id="kesherbox" class="tautbox"></div></section></div>'
        + chips("להתחיל לקרוא", [("/siddur/", "סידור תפילה"), ("/tehillim/", "ספר תהילים"), ("/sefer/", "ספרייה"), ("/kelim/", "כלים אישיים"), ("/zmanei-shabbat/", "זמני שבת")]))
# old numbered addresses redirect to the readable ones (kept in _redirects, between the two marker lines)
_rd = os.path.join(ROOT, "_redirects")
_cur = open(_rd, encoding="utf-8").read() if os.path.exists(_rd) else ""
_cur = re.sub(r"# prayers: begin.*?# prayers: end\n?", "", _cur, flags=re.S).rstrip("\n")
# two generations of old addresses: /tefila/<nusach>-<number>/ and /tefila/<nusach>/<name>/ (tools/old-urls.json)
_old = json.load(open(os.path.join(ROOT, "tools", "old-urls.json"), encoding="utf-8"))
MOVED["/tefila/"] = "/siddur/"
for _n in NUS:
    MOVED[f"/tefila/{_n}/"] = f"/siddur/{_n}/"
    for _k in ("shacharit", "mincha", "arvit"):
        MOVED[f"/tefila/{_n}/{_k}/"] = f"/siddur/{_n}/{_k}/"
_moved = "".join(f"{a} {PURL.get(b, b)} 301\n" for a, b in MOVED.items())
for a, b in MOVED.items():
    assert a not in _PRAYER_PATHS and PURL.get(b, b) != a, a
_lines = _moved + "".join(f"/tefila/{pid}/ {path} 301\n" + (f"{_old[pid]} {path} 301\n" if _old.get(pid) and _old[pid] != path else "") for pid, path in PURL.items())
assert _lines.count("\n") < 1900, "Cloudflare Pages allows 2,000 static redirects"
open(_rd, "w", encoding="utf-8").write((_cur + "\n" if _cur else "") + "# prayers: begin (written by tools/prerender.py)\n" + _lines + "# prayers: end\n")
json.dump(PURL, open(os.path.join(DATA, "urls.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---------- WhatsApp stickers: built by tools/build-stickers.js and .py, every one carries the site's mark ----------
STK_ITEMS = '<li><img src="/stickers/shabbat-shalom.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר שבת שלום"><div class="sb"><button type="button" data-stk="shabbat-shalom" data-name="שבת שלום">שליחה</button><a href="/stickers/shabbat-shalom.png?v=1" download="tfilah-shabbat-shalom.png">הורדה</a></div></li><li><img src="/stickers/shavua-tov.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר שבוע טוב"><div class="sb"><button type="button" data-stk="shavua-tov" data-name="שבוע טוב">שליחה</button><a href="/stickers/shavua-tov.png?v=1" download="tfilah-shavua-tov.png">הורדה</a></div></li><li><img src="/stickers/amen.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר אמן"><div class="sb"><button type="button" data-stk="amen" data-name="אמן">שליחה</button><a href="/stickers/amen.png?v=1" download="tfilah-amen.png">הורדה</a></div></li><li><img src="/stickers/mazal-tov.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר מזל טוב"><div class="sb"><button type="button" data-stk="mazal-tov" data-name="מזל טוב">שליחה</button><a href="/stickers/mazal-tov.png?v=1" download="tfilah-mazal-tov.png">הורדה</a></div></li><li><img src="/stickers/besha-tova.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר בשעה טובה"><div class="sb"><button type="button" data-stk="besha-tova" data-name="בשעה טובה">שליחה</button><a href="/stickers/besha-tova.png?v=1" download="tfilah-besha-tova.png">הורדה</a></div></li><li><img src="/stickers/refua-shlema.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר רפואה שלמה"><div class="sb"><button type="button" data-stk="refua-shlema" data-name="רפואה שלמה">שליחה</button><a href="/stickers/refua-shlema.png?v=1" download="tfilah-refua-shlema.png">הורדה</a></div></li><li><img src="/stickers/chodesh-tov.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר חודש טוב"><div class="sb"><button type="button" data-stk="chodesh-tov" data-name="חודש טוב">שליחה</button><a href="/stickers/chodesh-tov.png?v=1" download="tfilah-chodesh-tov.png">הורדה</a></div></li><li><img src="/stickers/chanukah-sameach.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר חנוכה שמח"><div class="sb"><button type="button" data-stk="chanukah-sameach" data-name="חנוכה שמח">שליחה</button><a href="/stickers/chanukah-sameach.png?v=1" download="tfilah-chanukah-sameach.png">הורדה</a></div></li><li><img src="/stickers/chag-sameach.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר חג שמח"><div class="sb"><button type="button" data-stk="chag-sameach" data-name="חג שמח">שליחה</button><a href="/stickers/chag-sameach.png?v=1" download="tfilah-chag-sameach.png">הורדה</a></div></li><li><img src="/stickers/toda-raba.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר תודה רבה"><div class="sb"><button type="button" data-stk="toda-raba" data-name="תודה רבה">שליחה</button><a href="/stickers/toda-raba.png?v=1" download="tfilah-toda-raba.png">הורדה</a></div></li><li><img src="/stickers/lechaim.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר לחיים"><div class="sb"><button type="button" data-stk="lechaim" data-name="לחיים">שליחה</button><a href="/stickers/lechaim.png?v=1" download="tfilah-lechaim.png">הורדה</a></div></li><li><img src="/stickers/behatzlacha.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר בהצלחה"><div class="sb"><button type="button" data-stk="behatzlacha" data-name="בהצלחה">שליחה</button><a href="/stickers/behatzlacha.png?v=1" download="tfilah-behatzlacha.png">הורדה</a></div></li><li><img src="/stickers/tizku-lemitzvot.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר תזכו למצוות"><div class="sb"><button type="button" data-stk="tizku-lemitzvot" data-name="תזכו למצוות">שליחה</button><a href="/stickers/tizku-lemitzvot.png?v=1" download="tfilah-tizku-lemitzvot.png">הורדה</a></div></li><li><img src="/stickers/karati-perek.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר קראתי פרק, תהילים יחד"><div class="sb"><button type="button" data-stk="karati-perek" data-name="קראתי פרק, תהילים יחד">שליחה</button><a href="/stickers/karati-perek.png?v=1" download="tfilah-karati-perek.png">הורדה</a></div></li><li><img src="/stickers/chaser-asiri.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר חסר עשירי למניין"><div class="sb"><button type="button" data-stk="chaser-asiri" data-name="חסר עשירי למניין">שליחה</button><a href="/stickers/chaser-asiri.png?v=1" download="tfilah-chaser-asiri.png">הורדה</a></div></li><li><img src="/stickers/matai-shabbat.webp?v=1" width="512" height="512" loading="lazy" alt="סטיקר מתי נכנסת שבת"><div class="sb"><button type="button" data-stk="matai-shabbat" data-name="מתי נכנסת שבת">שליחה</button><a href="/stickers/matai-shabbat.png?v=1" download="tfilah-matai-shabbat.png">הורדה</a></div></li>'
STK_JS = ("document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('[data-stk]');if(!b)return;var n=b.dataset.stk,u='/stickers/'+n+'.png?v=1';"
          "var dl=function(){var a=document.createElement('a');a.href=u;a.download='tfilah-'+n+'.png';document.body.appendChild(a);a.click();a.remove()};"
          "fetch(u).then(function(r){return r.blob()}).then(function(bl){var f=new File([bl],'tfilah-'+n+'.png',{type:'image/png'});"
          "if(navigator.canShare&&navigator.canShare({files:[f]}))return navigator.share({files:[f]}).catch(function(){});dl()}).catch(dl)})")
stickers = ('<p class="stkcredit">כל סטיקר נושא את הסימן tfilah.com, כך שכל מי שמקבל אותו יודע מאיפה הוא. מותר לשתף ולהשתמש בחופשיות, רק בלי להסיר את הסימן.</p>'
            '<div class="stkall"><a href="/stickers/tfilah-stickers.zip?v=1" download>הורדת כל הסטיקרים (ZIP)</a><a class="alt" href="#eich">איך מוסיפים לוואטסאפ</a></div>'
            f'<ul class="stkgrid">{STK_ITEMS}</ul>'
            '<div class="prose"><h2 id="eich">איך מוסיפים לוואטסאפ</h2>'
            '<p><b>שליחה מהירה:</b> לוחצים על ”שליחה” מתחת לסטיקר ובוחרים בוואטסאפ. הוא נשלח כתמונה.</p>'
            '<p><b>כסטיקר של ממש, באייפון ובוואטסאפ במחשב:</b> מורידים את הסטיקר, ובוואטסאפ פותחים את מגירת הסטיקרים, לוחצים על יצירת סטיקר ובוחרים את התמונה ששמרתם. מאותו רגע הוא מחכה לכם במגירה.</p>'
            '<p><b>באנדרואיד:</b> מורידים את כל הסטיקרים (ZIP) ומוסיפים אותם דרך אפליקציה ליצירת סטיקרים לוואטסאפ, מתוך התיקייה webp שבקובץ.</p>'
            '<p>יש לכם רעיון לסטיקר שחסר? <a href="/odot/#kesher">כתבו לנו</a>.</p></div>'
            + chips("עוד באתר", [("/zmanei-shabbat/", "זמני שבת"), ("/tehillim-yachad/", "תהילים יחד"), ("/siddur/", "סידור תפילה"), ("/ma-mevarchim/", "מה מברכים על")]))
page("/stickers/", f"סטיקרים לוואטסאפ: שבת שלום, אמן ומזל טוב | {BRAND}",
     "סטיקרים לוואטסאפ מבית תפילה: שבת שלום, שבוע טוב, אמן, מזל טוב, רפואה שלמה, חנוכה שמח ועוד. שולחים בלחיצה או מורידים את כולם בקובץ אחד.",
     "סטיקרים לוואטסאפ", [("סטיקרים לוואטסאפ", "/stickers/")], after=stickers, hub=True, prio="0.5", script=STK_JS,
     lead="שבת שלום, אמן, מזל טוב ועוד. שולחים בלחיצה, או מורידים ומוסיפים לוואטסאפ.",
     ld=[{"@type": "CollectionPage", "name": "סטיקרים לוואטסאפ", "url": SITE + "/stickers/", "inLanguage": "he", "isPartOf": WEBSITE}])

page("/odot/", f"אודות האתר תפילה ומקורות הטקסטים | {BRAND}",
     "מי אנחנו ומאין הטקסטים: סידור תפילה בשלושה נוסחים, ספר תהילים וספרייה ממהדורות פתוחות, שיטת חישוב זמני היום והלוח העברי, ומה מעמדם של ההסברים באתר.",
     "אודות ומקורות", [("אודות ומקורות", "/odot/")], after=odot, hub=True, prio="0.4", script=TAUT_JS, lead="תפילה · Tfilah.com. מה יש באתר, מאין הטקסטים ואיך מחושבים הזמנים.",
     ld=[{"@type": "AboutPage", "name": "אודות ומקורות", "url": SITE + "/odot/", "inLanguage": "he", "isPartOf": WEBSITE}])

# ---------- Privacy, terms, accessibility: short and in plain words ----------
LEGAL_DATE = "י״ב בכסלו תשפ״ז (22.11.2026)"
PRIV_DATE = "ז׳ בכסלו תשפ״ז (27.11.2026)"
_mail = f'<!--email_off--><a href="mailto:{CONTACT}">{CONTACT}</a><!--/email_off-->' if CONTACT else '<a href="/odot/#kesher">טופס צור קשר</a>'
_legal_chips = chips("עוד על האתר", [("/odot/", "אודות ומקורות"), ("/pratiyut/", "פרטיות"), ("/tnaim/", "תנאי שימוש"), ("/negishut/", "נגישות"), ("/odot/#kesher", "צור קשר")])
pratiyut = ('<div class="prose"><h2>בקצרה</h2><p>אין הרשמה, אין פרסומות, אין עוגיות מעקב, ואיננו מוכרים או מעבירים מידע לאף אחד. רוב מה שהאתר זוכר נשמר רק במכשיר שלכם.</p>'
            '<h2>מה נשמר במכשיר שלכם</h2><p>הנוסח שבחרתם, גודל האותיות, העיר לזמני היום, המועדפים והשמות שהקלדתם בכלים האישיים נשמרים בדפדפן שלכם בלבד, כדי שלא תצטרכו לבחור מחדש בכל כניסה. '
            'המידע הזה לא נשלח אלינו. מחיקת נתוני האתר בדפדפן מוחקת אותו.</p>'
            '<h2>מה נשמר אצלנו: תהילים יחד</h2><p>כשפותחים קריאה משותפת, נשמרים בשרת השם שכתבתם ושם ההורה, סוג הבקשה, והמילים שהוספתם אם הוספתם. '
            'לכל פרק שנקרא נשמרים מספר הפרק, שעת הקריאה, ושם הקורא רק אם בחר לכתוב אותו. כדי לספור קוראים בלי הרשמה, הדפדפן שולח מזהה אקראי שאינו מזהה אתכם אישית.</p>'
            '<p>כל מי שקיבל את הקישור לקריאה רואה את הפרטים האלה. קריאה חדשה מופיעה ברשימת הקריאות הפתוחות באתר, אלא אם סימנתם בזמן הפתיחה ”קריאה פרטית”. '
            'לפני שכותבים שם של חולה, כדאי לוודא שהדבר מקובל עליו ועל משפחתו.</p>'
            f'<h2>מחיקה ותיקון</h2><p>רוצים למחוק קריאה שפתחתם, או לתקן שם? כתבו אל {_mail} עם הקישור לקריאה, ונמחק או נתקן בהקדם.</p>'
            '<h2>פנייה אלינו</h2><p>כשאתם כותבים אלינו, אנחנו מקבלים את ההודעה ואת כתובת המייל שמסרתם, ומשתמשים בהן רק כדי לענות לכם.</p>'
            '<h2>מיקום</h2><p>כלי כיוון התפילה מבקש את מיקום המכשיר רק אחרי שאישרתם. החישוב נעשה במכשיר עצמו, והמיקום לא נשלח אלינו ולא נשמר.</p>'
            '<h2>שירותים חיצוניים</h2><p>האתר מתארח ב-Cloudflare, ששומרת רישום טכני רגיל של גלישה, כמו כתובת IP, לצורכי אבטחה ותפעול. '
            'כדי לדעת כמה נכנסים לאתר ואילו עמודים נפתחים, האתר סופר כניסות בעצמו, בלי עוגיות ובלי לזהות את המבקר. לכל פתיחת עמוד נשמרים כתובת העמוד, השעה, סוג המכשיר (טלפון, טאבלט או מחשב) ומאיפה הגעתם בקטגוריה כללית בלבד (למשל גוגל, פייסבוק או כניסה ישירה). לא נשמרים כתובת IP, שם, מה שהקלדתם או הכתובת המלאה שממנה הגעתם. מספר אקראי שנוצר בכל פתיחת עמוד, ולא נשמר בדפדפן, מאפשר לדעת שהעמוד עדיין פתוח. הרישומים נמחקים אחרי 30 יום, ונשארים רק סיכומים יומיים. אם הדפדפן מבקש לא לעקוב (Do Not Track או Global Privacy Control), לא נשלח דבר. '
            'כדי להציג כמה פעמים עמוד נפתח, נשמר אצלנו מספר אחד לכל עמוד, בלי שום פרט על מי שפתח אותו. ספריית הלוח העברי נטענת מ-jsDelivr, וגופני קריאה נוספים נטענים מ-Google Fonts רק אם בחרתם בהם. שיתוף בוואטסאפ, בטלגרם או במייל פותח את השירות שבחרתם, לפי התנאים שלו.</p>'
            f'<h2>שינויים</h2><p>אם נשנה משהו מהותי, נעדכן את הדף הזה. עדכון אחרון: {PRIV_DATE}.</p></div>' + _legal_chips)
page("/pratiyut/", f"מדיניות פרטיות | {BRAND}",
     "מה האתר תפילה שומר ומה לא: בלי הרשמה ובלי עוגיות מעקב, ההעדפות נשמרות במכשיר שלכם, ומה נשמר בקריאת תהילים משותפת ואיך מבקשים למחוק.",
     "פרטיות", [("פרטיות", "/pratiyut/")], after=pratiyut, hub=True, prio="0.2", lead="מה אנחנו שומרים, מה נשאר רק אצלכם, ואיך מבקשים למחוק.",
     ld=[{"@type": "WebPage", "name": "מדיניות פרטיות", "url": SITE + "/pratiyut/", "inLanguage": "he", "isPartOf": WEBSITE}])

tnaim = ('<div class="prose"><h2>השימוש באתר</h2><p>האתר פתוח לכולם, בחינם ובלי הרשמה. האתר מופעל בידי מפעילי האתר תפילה, Tfilah.com. השימוש בו מהווה הסכמה לתנאים הקצרים שכאן.</p>'
         '<h2>הטקסטים</h2><p>נוסחי התפילה והתהילים לקוחים ממהדורות פתוחות, כמפורט בדף <a href="/odot/">אודות ומקורות</a>. אנחנו בודקים אותם מול המקור ומתקנים כל טעות שמדווחת, '
         'ועדיין ייתכנו טעויות הקלדה או ניקוד. מצאתם טעות? <a href="/odot/#taut" data-taut>דווחו לנו</a>.</p>'
         '<h2>זמנים, לוח והסברים</h2><p>זמני היום, זמני השבת והלוח העברי מחושבים אוטומטית ועשויים לסטות בדקה או שתיים מלוחות אחרים. למעשה יש להחמיר, ולא לסמוך על האתר לרגע האחרון. '
         'ההסברים שליד התפילות נכתבו כדי לתת הקשר לקורא. הם אינם פסק הלכה ואינם באים במקום רב.</p>'
         '<h2>תהילים יחד</h2><p>כל אחד יכול לפתוח קריאה משותפת. מי שפותח אחראי לשם ולמילים שכתב, ועליו לוודא שהפרסום מקובל על מי שהקריאה לזכותו או על משפחתו. '
         'נסיר קריאה שיש בה תוכן פוגעני, מטעה או מסחרי, וכן כל קריאה שנתבקשנו להסיר בידי מי שהיא נוגעת לו.</p>'
         '<h2>שימוש הוגן</h2><p>מותר ורצוי לקרוא, להדפיס ולשתף קישורים. אין להעמיס על האתר באמצעים אוטומטיים, לנסות לשבש את פעולתו, או להציג אותו כאילו הוא שלכם. '
         'השם תפילה, הסמל והעיצוב שייכים למפעילי האתר. ההסברים שנכתבו עבור האתר מותרים לציטוט עם קישור למקור.</p>'
         '<h2>אחריות</h2><p>האתר ניתן כמות שהוא. אנחנו משתדלים מאוד שיהיה מדויק וזמין, אך איננו יכולים להתחייב שלא תהיה בו טעות או תקלה, והשימוש בו באחריות המשתמש.</p>'
         f'<h2>יצירת קשר ושינויים</h2><p>לכל שאלה: {_mail}. אם התנאים ישתנו, הדף הזה יתעדכן. עדכון אחרון: {LEGAL_DATE}.</p></div>' + _legal_chips)
page("/tnaim/", f"תנאי שימוש | {BRAND}",
     "תנאי השימוש באתר תפילה בקיצור ובמילים פשוטות: שימוש חופשי בלי הרשמה, מעמד הטקסטים, הזמנים וההסברים, כללי הקריאה המשותפת בתהילים וגבולות האחריות.",
     "תנאי שימוש", [("תנאי שימוש", "/tnaim/")], after=tnaim, hub=True, prio="0.2", lead="הכללים של האתר, בקיצור ובמילים פשוטות.",
     ld=[{"@type": "WebPage", "name": "תנאי שימוש", "url": SITE + "/tnaim/", "inLanguage": "he", "isPartOf": WEBSITE}])

negishut = ('<div class="prose"><h2>המטרה שלנו</h2><p>תפילה צריכה להיות נוחה לכל אדם, גם למי שמתקשה בראייה, במוטוריקה או בשימוש במסך. האתר נבנה לפי הנחיות הנגישות WCAG 2.1 ברמה AA, '
            'שעליהן מבוסס התקן הישראלי ת״י 5568.</p>'
            '<h2>מה עשינו</h2><ul><li>אפשר להגדיל ולהקטין את אותיות הקריאה, ולקרוא עם ניקוד או בלעדיו.</li><li>כל האתר פועל במקלדת בלבד, עם סימון ברור של המקום שבו נמצאים וקישור דילוג לתוכן.</li>'
            '<li>הדפים בנויים עם כותרות, תוויות ותיאורים לקוראי מסך.</li><li>צבעי הטקסט והכפתורים נבדקים לניגודיות מספקת.</li><li>האתר מכבד את הגדרת ”הפחתת תנועה” במכשיר.</li>'
            '<li>האתר מותאם לטלפון, לטאבלט ולמחשב, וכפתוריו גדולים מספיק ללחיצה נוחה.</li></ul>'
            '<h2>איך בדקנו</h2><p>האתר נבדק בכלי בדיקה אוטומטיים ובמעבר ידני במקלדת, בטלפון ובמחשב. בדיקה מלאה עם קוראי מסך על מכשירים אמיתיים עדיין לא הושלמה.</p>'
            '<h2>מה עוד לא מושלם</h2><p>ייתכן שתיתקלו בחלק שאינו נגיש כראוי, בעיקר בכלים חדשים. שיתוף פותח אפליקציות חיצוניות כמו וואטסאפ, שנגישותן אינה בשליטתנו.</p>'
            f'<h2>נתקלתם בקושי?</h2><p>כתבו אל {_mail} וספרו באיזה דף ובאיזה מכשיר. נשתדל לתקן מהר, ובינתיים נעזור לכם להגיע לתפילה שחיפשתם.</p>'
            f'<p>עדכון אחרון: {LEGAL_DATE}.</p></div>' + _legal_chips)
page("/negishut/", f"הצהרת נגישות | {BRAND}",
     "הצהרת הנגישות של האתר תפילה: התאמה להנחיות WCAG 2.1 ברמה AA, הגדלת אותיות, שימוש במקלדת ובקוראי מסך, מה עדיין לא מושלם ואיך פונים אלינו בנושא נגישות.",
     "הצהרת נגישות", [("נגישות", "/negishut/")], after=negishut, hub=True, prio="0.2", lead="מה עשינו כדי שהאתר יהיה נוח לכולם, ולמי פונים כשמשהו לא עובד.",
     ld=[{"@type": "WebPage", "name": "הצהרת נגישות", "url": SITE + "/negishut/", "inLanguage": "he", "isPartOf": WEBSITE}])

# ---------- 404 ----------
nf = ('<p><a class="btn" href="/">לדף הבית</a></p><ul class="cards" style="margin-block-start:1.5rem">'
      '<li><a href="/siddur/"><b>סידור תפילה</b><small>עדות המזרח, ספרד ואשכנז</small></a></li>'
      '<li><a href="/tehillim/"><b>ספר תהילים</b><small>כל 150 הפרקים ותהילים לפי בקשה</small></a></li>'
      '<li><a href="/sefer/"><b>ספרייה</b><small>פרקי אבות, מגילות, פרק שירה ועוד</small></a></li>'
      '<li><a href="/tehillim-yachad/"><b>תהילים יחד</b><small>כל אחד פרק. ביחד ספר שלם.</small></a></li>'
      '<li><a href="/tehillim/yomi/"><b>תהילים יומי</b><small>החלוקה לימי החודש ולימי השבוע</small></a></li>'
      '<li><a href="/kelim/"><b>כלים אישיים</b><small>תהילים לפי השם, יארצייט ועוד</small></a></li></ul>')
page("/404.html", f"העמוד לא נמצא | {BRAND}", "העמוד שחיפשתם לא נמצא באתר תפילה.", "העמוד לא נמצא", [],
     after=nf, hub=True, notfound=True, lead="ייתכן שהקישור שגוי או שהעמוד הועבר. מכאן אפשר להגיע לכל חלקי האתר.")

# =====================================================================
# sitemap
# =====================================================================
paths = [u for u, _, _, _ in URLS]
assert len(set(paths)) == len(paths)
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f"  <url><loc>{SITE}/</loc><lastmod>{max(l for _, _, l, _ in URLS)}</lastmod><priority>1.0</priority></url>"]
sm += [f"  <url><loc>{SITE}{u}</loc><lastmod>{l}</lastmod><priority>{pr}</priority></url><!--{fp}-->" for u, pr, l, fp in URLS]
sm.append("</urlset>")
with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write("\n".join(sm) + "\n")
print("pages:", len(URLS), "+ 404.html")
print("  changed since the previous run (lastmod = today):", sum(1 for _, _, l, _ in URLS if l == TODAY))
print("prayer pages with a counterpart in another nusach:", sum(1 for v in SAME.values() if v), "of", len(SAME))
print("most-wanted:")
for label, n, pid, t in WANT_REPORT:
    print(f"  {label} | {n} | {pid or '-'} | {t or ''}")
