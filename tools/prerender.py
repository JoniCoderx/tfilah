"""Static reading pages for תפילה (tfilah.com).

Generates real, crawlable HTML for:
  /tehillim/<1-150>/            every Tehillim chapter
  /tehillim/<need>/             Tehillim by need (the app's NEEDS list), chapters in full
  /tehillim/yomi/               the monthly and weekly division of the book
  /tefila/<nusach>-<n>/         every prayer, per nusach
  /tefila/<nusach>/             nusach hub
  /tefila/<nusach>/<service>/   weekday shacharit / mincha / arvit: ordered contents
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
    return re.sub(r"\s+", " ", NIK.sub("", TAG.sub(" ", s).replace("־", " ")).replace("—", " ")).replace("יהוה", "ה'").strip()

def snippet(s, n=150):
    s = plain(s)
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(" ,;:.(־-") + "…"

def esc(s):
    return html.escape(s, quote=True)

TAILS = ("טקסט מלא בניקוד.", "קריאה נוחה בנייד, עם שליטה בגודל הכתב ובהצגת הניקוד.", "חינם וללא הרשמה, באתר תפילה.")

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
:root{--paper:#FFFFFF;--surface:#FFFFFF;--ink:#0B2E4F;--ink2:#27506F;--muted:#46677F;--line:#DDEEF9;--sunk:#F3F9FE;--stamp:#0A6CA8;--tint:#B3E0FA;--grad:linear-gradient(135deg,#6CC6F7,#45B0EE 52%,#2FA0E4);
--sh:0 1px 2px rgba(11,46,79,.05),0 10px 28px -16px rgba(11,46,79,.22);--r:1.375rem;
--reading:1.32rem;--f-disp:"Heebo","Assistant",system-ui,Arial,sans-serif;--f-ui:"Assistant",system-ui,"Segoe UI",Arial,sans-serif;--f-read:"Heebo","Assistant",system-ui,Arial,sans-serif;--top:3.5rem}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:calc(var(--top) + .75rem)}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f-ui);font-size:1rem;line-height:1.6;overflow-wrap:break-word}
a{color:var(--stamp);text-underline-offset:.2em;text-decoration-thickness:1px}
a:hover{color:var(--ink)}
:focus-visible{outline:2px solid var(--stamp);outline-offset:2px;border-radius:.5rem}
[hidden]{display:none!important}
.skip{position:absolute;inset-block-start:-5rem;inset-inline-start:.5rem;z-index:10;background:var(--ink);color:#fff;padding:.7rem 1.1rem;font-weight:700;text-decoration:none;border-radius:999px}
.skip:focus{inset-block-start:.5rem;color:#fff}
.top{position:sticky;inset-block-start:0;z-index:5;background:rgba(255,255,255,.94);border-block-end:1px solid var(--line)}
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
h1 .ctx{display:block;font-family:var(--f-ui);font-weight:600;font-size:.95rem;line-height:1.4;color:var(--ink2);letter-spacing:0;margin-block-start:.3rem}
.meta{margin:0 0 .5rem;color:var(--muted);font-size:.93rem}
.meta b{color:var(--ink);font-weight:700}
.meta a{color:var(--ink2);display:inline-block;padding-block:.8rem;margin-block:-.8rem}
.lead{margin:0 0 1.25rem;color:var(--ink2);max-width:36rem;font-size:1.05rem}
h1,h2,h3,[id]{scroll-margin-top:calc(var(--top) + .75rem)}
h2.sec{font-family:var(--f-disp);font-weight:900;font-size:1.7rem;line-height:1.25;margin:2.25rem 0 .7rem}
.related{display:flex;flex-wrap:wrap;gap:.45rem}
.related a{display:inline-flex;align-items:center;min-height:2.75rem;padding:.3rem 1rem;border:1px solid var(--line);background:var(--surface);text-decoration:none;color:var(--ink);font-size:.95rem;font-weight:600;line-height:1.3;border-radius:999px}
.related a:hover{border-color:var(--stamp);color:var(--stamp)}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:3rem;padding:.4rem 1.5rem;background:linear-gradient(135deg,#6CC6F7,#45B0EE 52%,#2FA0E4);color:var(--ink);text-decoration:none;font-weight:700;border-radius:999px;box-shadow:var(--sh)}
.btn:hover{color:var(--ink);filter:brightness(1.08)}
.applink{margin:1.5rem 0 0}
.applink a{display:inline-flex;align-items:center;min-height:2.75rem;font-weight:600}
footer{border-block-start:1px solid var(--line);color:var(--muted);font-size:.88rem}
footer .in{max-width:40rem;margin-inline:auto;padding:1.25rem 1rem 2.5rem}
footer p{margin:0 0 .4rem}
footer .sig{font-family:var(--f-disp);font-weight:900;font-size:1.15rem;color:var(--ink)}
footer .sig span{font-family:var(--f-ui);font-weight:400;font-size:.88rem;color:var(--muted)}
footer nav{display:flex;flex-wrap:wrap;margin-inline:-.5rem}
footer nav a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.5rem;color:var(--ink2)}
@media (max-width:26rem){.top .in{padding-inline:.75rem;gap:.25rem}.logo svg{height:1.625rem}.top nav a{padding-inline:.4rem;font-size:.9rem}main{padding-inline:.75rem}}
@media (max-width:21.5rem){.logo svg{height:1.4rem}.top nav a{padding-inline:.3rem;font-size:.84rem}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
@media print{.top,.bar,.pager,.together,.applink,.related,footer nav,.skip{display:none}.text{border:0;padding:0;box-shadow:none}}
"""

# class token that triggers the block -> css
CSS_BLOCKS = [
("text", """
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:.25rem .5rem;margin:0 0 .6rem;min-height:2.75rem}
.tools{display:flex;gap:.375rem}
.tools button{min-width:2.75rem;min-height:2.75rem;padding-inline:.85rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);font:600 .95rem var(--f-ui);cursor:pointer;border-radius:999px}
.tools button:hover{border-color:var(--stamp)}
.tools button[aria-pressed="true"]{background:var(--grad);border-color:transparent;color:var(--ink)}
.tools button:disabled{color:var(--muted);cursor:default;border-color:var(--line)}
.tools .az{font-weight:700;font-size:1.1rem}
.tools .az.sm{font-size:.9rem}
.nus{display:flex;align-items:center;flex-wrap:wrap;margin-inline-start:auto;font-size:.93rem;color:var(--muted)}
.nus a{display:inline-flex;align-items:center;min-height:2.75rem;padding-inline:.45rem;font-weight:600}
.bar{flex-wrap:nowrap}.nus{flex-wrap:nowrap;white-space:nowrap}
@media (max-width:30rem){.nus span{display:none}}
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
("pager", """
.pager{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:1.5rem 0 0}
.pager a{display:block;padding:.75rem 1.2rem;border:1px solid var(--line);background:var(--surface);border-radius:var(--r);text-decoration:none;color:var(--ink);font-weight:700;font-size:1.05rem;line-height:1.35;min-height:2.75rem}
.pager a:hover{border-color:var(--stamp);color:var(--ink)}
.pager small{display:block;color:var(--muted);font-weight:400;font-size:.8rem}
.pager .next{text-align:end;background:var(--grad);border-color:transparent;color:var(--ink);box-shadow:var(--sh)}
.pager .next:hover{color:var(--ink);filter:brightness(1.08)}
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
.sched .tag{display:inline-block;margin-inline-start:.5rem;padding:.05rem .6rem;border-radius:999px;background:var(--grad);color:var(--ink);font-size:.8rem;font-weight:700}
.sched .chs{display:flex;flex-wrap:wrap;gap:.3rem;margin-block-start:.5rem}
.sched .chs a{display:inline-grid;place-items:center;min-width:2.75rem;min-height:2.75rem;padding-inline:.5rem;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--ink);font-weight:700}
.sched .chs a:hover{border-color:var(--stamp);color:var(--stamp)}
.sched .more{display:flex;flex-wrap:wrap;gap:0 1rem}
.sched .more a{display:inline-flex;align-items:center;min-height:2.75rem;font-weight:600}
"""),
("steps", """
.steps{list-style:none;margin:1.5rem 0;padding:0;display:grid;gap:.7rem;counter-reset:st}
.steps li{counter-increment:st;display:grid;grid-template-columns:auto 1fr;gap:.2rem 1rem;align-items:start;padding:1rem 1.2rem;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh)}
.steps li::before{content:counter(st);grid-row:span 2;display:grid;place-items:center;inline-size:2.5rem;block-size:2.5rem;border-radius:50%;background:var(--grad);color:var(--ink);font-weight:700;font-size:1.15rem}
.steps b{font-family:var(--f-disp);font-weight:900;font-size:1.3rem;line-height:1.3}
.steps span{color:var(--ink2);grid-column:2}
"""),
("hero", """
.hero{margin:1rem 0 1.5rem;padding:1.6rem 1.5rem 1.7rem;background:linear-gradient(160deg,#FFFFFF,#F3FAFF 55%,#E4F3FE);border:1px solid var(--line);color:var(--ink);border-radius:1.75rem;box-shadow:var(--sh)}
.hero p{margin:0 0 1.1rem;font-family:var(--f-disp);font-weight:900;font-size:clamp(1.7rem,6vw,2.4rem);line-height:1.2}
.hero .btn{color:var(--ink);box-shadow:none}
.hero .btn:hover{color:var(--stamp);filter:none}
.hero small{display:block;margin-block-start:.8rem;color:var(--ink2);font-size:.92rem}
"""),
("prose", """
.prose{max-width:36rem}
.prose p{margin:0 0 .9rem;color:var(--ink2)}
.prose h2{font-family:var(--f-disp);font-weight:900;font-size:1.5rem;line-height:1.25;margin:1.6rem 0 .5rem;color:var(--ink)}
.prose table{border-collapse:collapse;margin:0 0 1rem;font-size:.97rem}
.prose td,.prose th{padding:.35rem .9rem .35rem 0;text-align:start;border-block-end:1px solid var(--line)}
"""),
("zt", """
.zt{inline-size:100%;border-collapse:collapse;margin:.6rem 0 1rem;font-variant-numeric:tabular-nums}
.zt th,.zt td{padding:.7rem .5rem;text-align:start;border-block-end:1px solid var(--line)}.zt th{font-size:.85rem;color:var(--muted);font-weight:600}
.zt td b{font-size:1.1rem}.zt tr.now td{background:var(--sunk);font-weight:700}.zt tr.past{display:none}
.znow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.6rem;margin:1rem 0}.znow div{padding:1rem;border-radius:1.25rem;background:var(--sunk);display:grid;gap:.2rem}
.znow span{font-size:.85rem;color:var(--muted);font-weight:600}.znow b{font-family:var(--f-disp);font-weight:900;font-size:clamp(1.6rem,7vw,2.3rem);line-height:1;font-variant-numeric:tabular-nums}
.znow small{color:var(--muted)}
"""),
("plainx", """
.plainx{margin:.4rem 0 1rem;padding:1rem 1.15rem;border-radius:1.25rem;background:var(--sunk)}
.plainx b{display:block;font-size:.9rem;color:var(--stamp);margin-block-end:.3rem}.plainx p{margin:0;line-height:1.75}
"""),
("note", """
.note{margin:1rem 0;color:var(--muted);font-size:.93rem;max-width:36rem}
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
function nikud(){if(orig==null)orig=art.innerHTML;art.innerHTML=nik?orig:orig.replace(NIK,'');nk.setAttribute('aria-pressed',nik?'true':'false')}
fm.onclick=function(){fs=Math.max(MIN,+(fs-STEP).toFixed(2));set('fs',fs);size()};
fp.onclick=function(){fs=Math.min(MAX,+(fs+STEP).toFixed(2));set('fs',fs);size()};
nk.onclick=function(){nik=!nik;set('nikud',nik);nikud()};
size();if(!nik)nikud();else nk.setAttribute('aria-pressed','true');
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
              '<button type="button" id="nk" aria-pressed="true">ניקוד</button></div>')

NAV = ('<nav aria-label="ניווט ראשי"><a href="/tefila/">סידור</a><a href="/tehillim/">תהילים</a>'
       '<a href="/sefer/">ספרייה</a><a href="/tehillim-yachad/">תהילים יחד</a></nav>')
FOOT_NAV = ('<nav aria-label="קישורי תחתית"><a href="/tefila/">סידור תפילה</a><a href="/tehillim/">ספר תהילים</a>'
            '<a href="/tehillim/#bakasha">תהילים לפי בקשה</a><a href="/tehillim/yomi/">תהילים יומי</a>'
            '<a href="/tehillim-yachad/">תהילים יחד</a><a href="/sefer/">ספרייה</a><a href="/kelim/">כלים אישיים</a>'
            '<a href="/zmanei-shabbat/">זמני שבת</a></nav>')
FONTS = "https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700&family=Heebo:wght@400;700;900&display=swap"

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

def page(path, title, desc, h1, crumbs, text="", meta="", bar_extra="", after="", before="", lead="", app_hash="",
         app_label="לפתיחה באפליקציה", h1_ctx="", hub=False, ld=None, prio="0.6", script="", notfound=False):
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
        lds.append({"@context": "https://schema.org", **x})
    crumb_html = "<span>›</span>".join(f'<a href="{u}">{esc(n)}</a>' for n, u in allc[:-1])
    h1_html = esc(h1) + (f' <span class="ctx">{esc(h1_ctx)}</span>' if h1_ctx else "")
    reading = ""
    if text:
        bar = f'<div class="bar">{TOOLS_HTML}{bar_extra}</div>'
        reading = f'{bar}<article class="text" id="text">{text}</article><script>{JS_TOOLS}</script>'
    applink = f'<p class="applink"><a href="/#{app_hash}">{esc(app_label)}</a></p>' if app_hash else ""
    body = f"""<a class="skip" href="#{'text' if text else 'main'}">{'דילוג לטקסט' if text else 'דילוג לתוכן'}</a>
<header class="top"><div class="in"><a class="logo" href="/" aria-label="תפילה, לדף הבית">{LOGO}</a>
{NAV}</div></header>
<main id="main"><nav class="crumbs" aria-label="מיקום באתר">{crumb_html}</nav><h1>{h1_html}</h1>{f'<p class="meta">{meta}</p>' if meta else ''}{f'<p class="lead">{esc(lead)}</p>' if lead else ''}{before}{reading}{after}{applink}</main>
<footer><div class="in"><p class="sig">תפילה <span>· tfilah.com</span></p><p>סידור תפילה, תהילים וזמני היום. הטקסטים מתוך מאגרי Sefaria ותורת אמת, ברשיונות חופשיים.</p>
{FOOT_NAV}</div></footer>{f'<script>{script}</script>' if script else ''}"""
    canon = ('<meta name="robots" content="noindex">' if notfound else
             f'<link rel="canonical" href="{url}">\n<meta property="og:url" content="{url}">')
    doc = f"""<!doctype html>
<html lang="he" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{canon}
<meta property="og:type" content="{'website' if hub or notfound else 'article'}"><meta property="og:site_name" content="{BRAND}"><meta property="og:locale" content="he_IL">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/icons/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#FFFFFF"><link rel="icon" href="/brand/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<style>{css_for(body)}</style><script>{JS_HEAD}</script>
<link rel="stylesheet" href="{FONTS}">
{''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False, separators=(",", ":"))}</script>' for x in lds)}
<script>if("serviceWorker" in navigator)addEventListener("load",function(){{navigator.serviceWorker.register("/sw.js").catch(function(){{}})}});</script>
</head><body{' class="hub"' if hub else ''}>
{body}
</body></html>
"""
    out = os.path.join(ROOT, "404.html") if notfound else os.path.join(ROOT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fp = signature(doc)
    lastmod = OLD[path][0] if path in OLD and OLD[path][1] == fp else TODAY
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    if not notfound:
        URLS.append((path, prio, lastmod, fp))

def pager(prev, nxt):
    """prev / nxt = (href, label) or None"""
    a = f'<a href="{prev[0]}" rel="prev"><small>הקודם</small>{esc(prev[1])}</a>' if prev else "<span></span>"
    b = f'<a class="next" href="{nxt[0]}" rel="next"><small>הבא</small>{esc(nxt[1])}</a>' if nxt else "<span></span>"
    return f'<nav class="pager" aria-label="הקודם והבא">{a}{b}</nav>'

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
I = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
NUS = I["nusachim"]
TEXTS = {n: json.load(open(os.path.join(DATA, f"{n}.json"), encoding="utf-8")) for n in NUS}
by_nus = {n: [p for p in I["prayers"] if p["n"] == n and TEXTS[n].get(p["id"])] for n in NUS}
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

# The stand-alone instance of a repeated title gets the clean <title> (its twins keep their context).
PRIMARY = {"ashkenaz-1", "ashkenaz-3", "ashkenaz-4", "ashkenaz-13", "ashkenaz-440", "ashkenaz-441", "ashkenaz-442", "ashkenaz-443"}
for pid in PRIMARY:
    assert pid in BYID and pid in CTX, pid

# How people type the name. The source title stays as the H1; these only lead the <title> and description.
SPELL = {"תפלת הדרך": "תפילת הדרך", "פטום הקטורת": "פיטום הקטורת", "פטום קטורת": "פיטום הקטורת",
         'ק"ש וברכותיה': "קריאת שמע וברכותיה", "קריאת שמע על המיטה": "קריאת שמע שעל המיטה",
         "תפלת הנוטל תרופה": "תפילת הנוטל תרופה"}
LEAD = {"סדר הבדלה": "הבדלה למוצאי שבת", "סדר הדלקת נרות שבת": "הדלקת נרות שבת",
        "סדר הדלקת נרות חנוכה": "הדלקת נרות חנוכה", "הבדלה": "הבדלה למוצאי שבת"}
LEAD_ID = {"ashkenaz-211": "קידוש לליל שבת", "sefard-132": "הלל לראש חודש (סדר הלל)"}
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
    return LEAD_ID.get(p["id"]) or SPELL.get(p["t"]) or LEAD.get(p["t"]) or p["t"]

def also_of(p):
    if weekday_amida(p):
        return "שמונה עשרה"
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
        return f"/tefila/{n}/{k}/", svc_name(n, k)
    gi = GROUP_OF[p["id"]]
    return f"/tefila/{n}/#g{gi + 1}", GROUPS[n][gi][0]

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
            me = f"/tefila/{p['id']}/"
            for q in members:
                if q is not p and norm_t(q["t"]) != norm_t(p["t"]):
                    cur_add(me, f"/tefila/{q['id']}/", lead_of(q))
            for href, label in fixed:
                cur_add(me, href, label)
    for href, label in fixed:
        for h2, l2 in fixed:
            cur_add(href, h2, l2)
        for n in NUS:
            for q in per_nus[n]:
                cur_add(href, f"/tefila/{q['id']}/", f"{lead_of(q)} · נוסח {NUS[n]}")

# Ashkenaz lists single psalms as parts of the service ("תהילים קמו"): link them to the chapter page and back.
for p in by_nus.get("ashkenaz", []):
    m = re.fullmatch(r"תהילים ([א-ת]{1,3})", p["t"])
    if m and 1 <= ungem(m.group(1)) <= 150:
        cur_add(f"/tefila/{p['id']}/", f"/tehillim/{ungem(m.group(1))}/", f"תהילים פרק {m.group(1)}, הפרק המלא")

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
    first = snippet(vs[0], 40)
    nv = "פסוק אחד" if len(vs) == 1 else f"{len(vs)} פסוקים"
    name = f"תהילים פרק {gem(c)}"
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
                        tails=("עם קישור לכל פרק בנפרד.", "קריאה נוחה בנייד.", "חינם וללא הרשמה."))
    text = "".join(f'<h2 id="p{c}"><a href="/tehillim/{c}/">תהילים פרק {gem(c)}</a></h2>{verses(c)}' for c in chs)
    before = (f'<p class="note">{esc(NEED_NOTE[k])}</p>' if k in NEED_NOTE else "")
    before += '<div class="related" style="margin-block-end:1rem">' + "".join(f'<a href="#p{c}">פרק {gem(c)}</a>' for c in chs) + "</div>"
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
    before = f'<div class="related" style="margin-block-end:1rem">{jump}</div>' if b > a else ""
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
    f'<a href="/tehillim/{c}/">תהילים פרק {gem(c)}</a>' for c in POPULAR) + '</div><h2 class="sec">כל 150 הפרקים</h2>'
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
page("/tehillim/", f"ספר תהילים אונליין | כל 150 הפרקים בניקוד מלא | {BRAND}",
     "ספר תהילים המלא אונליין בניקוד: כל 150 הפרקים, פרק בכל עמוד, תהילים לפי בקשה (לרפואה, לפרנסה, לעילוי נשמה), תיקון הכללי וחלוקה יומית.",
     "ספר תהילים", [("תהילים", "/tehillim/")], after=hub, app_hash="tehillim", hub=True, prio="0.9",
     lead="כל 150 הפרקים בניקוד מלא. בחרו פרק והתחילו לקרוא.",
     ld=[collection("ספר תהילים", "/tehillim/", [f"/tehillim/{c}/" for c in range(1, 151)])])

# =====================================================================
# Prayers
# =====================================================================
def siddur_of(n):
    return {"@type": "CreativeWork", "name": f"סידור תפילה, נוסח {NUS[n]}", "inLanguage": "he", "url": f"{SITE}/tefila/{n}/"}

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
        me = f"/tefila/{p['id']}/"
        prev = plist[i - 1] if i > 0 else None
        nxt = plist[i + 1] if i + 1 < len(plist) else None
        after = pager((f'/tefila/{prev["id"]}/', prev["t"]) if prev else None, (f'/tefila/{nxt["id"]}/', nxt["t"]) if nxt else None)
        same = SAME[p["id"]]
        switch = ""
        if same:
            after += chips("אותה תפילה בנוסח אחר", [(f'/tefila/{q["id"]}/', f'{q["t"]} · נוסח {NUS[q["n"]]}') for q in same])
            switch = ('<nav class="nus" aria-label="אותה תפילה בנוסח אחר"><span>גם בנוסח</span>'
                      + "".join(f'<a href="/tefila/{q["id"]}/">{esc(NUS[q["n"]])}</a>' for q in same) + "</nav>")
        s = sec_of(p)
        ctx = CTX.get(p["id"], "")
        lead_name, also = lead_of(p), also_of(p)
        sec_href, sec_label = section_link(p)

        # related: curated first, then the nearest prayers of the same section
        skip = {me} | {f'/tefila/{q["id"]}/' for q in (prev, nxt) if q}
        full = [q for q in plist if sec_of(q) == s]
        grp = GROUPS[n][GROUP_OF[p["id"]]][1]
        cands = sorted(full, key=lambda q: abs(plist.index(q) - i)) + sorted(grp, key=lambda q: abs(plist.index(q) - i)) \
            + sorted(plist, key=lambda q: abs(plist.index(q) - i))[:12]
        extra = []
        for q in cands:
            h = f'/tefila/{q["id"]}/'
            if h not in skip and norm_t(q["t"]) != norm_t(p["t"]):
                same_sec = sec_of(q) == s
                extra.append((h, q["t"] if same_sec or not sec_of(q) else f'{q["t"]} ({sec_of(q)[-1]})'))
        rel = fill([x for x in CUR.get(me, []) if x[0] not in skip][:6], extra, lo=5)
        if p["id"] in WANT_IDS and n in NUS_NOTE:
            other = next((q for q in same if q["n"] == NUS_NOTE[n][1]), None)
            after += nus_note(n, f'/tefila/{other["id"]}/' if other else f"/tefila/{NUS_NOTE[n][1]}/",
                              f'{lead_of(other)} בנוסח {NUS[other["n"]]}' if other else f"סידור נוסח {NUS[NUS_NOTE[n][1]]}")
        after += chips("תפילות קשורות", rel)
        after += chips("בסידור", [(sec_href, f"{sec_label}: כל הסדר"), (f"/tefila/{n}/", f"סידור נוסח {NUS[n]}"), ("/tefila/", "כל הנוסחים")])

        tname = TNAME[p["id"]]
        where = ctx or " · ".join(s)
        if len(where) > 58:
            where = " · ".join(s[-2:]) + (" · " + ctx.rsplit(" · ", 1)[-1] if "חלק " in ctx.rsplit(" · ", 1)[-1] else "")
        alt = ALT_SPELL.get(p["t"], "")
        head = f"{lead_name} בנוסח {NUS[n]}" + (f" ({also or alt})" if also or alt else "") + (f", {where}" if where and p["id"] not in PRIMARY else "")
        meta = f'<b>נוסח {esc(NUS[n])}</b>' + (f' · <a href="{sec_href}">{esc(" · ".join(s))}</a>' if s and not ctx else "")
        if lead_name != p["t"] and p["t"] in SPELL:
            meta += f" · כתיב נפוץ: {esc(lead_name)}"
        if also:
            meta += f" · נקראת גם {esc(also)}"
        if alt:
            meta += f" · נכתב גם: {esc(alt)}"
        when = CONTEXT_ID.get(p["id"]) or CONTEXT.get(p["t"]) or CONTEXT.get(norm_t(p["t"]))
        before = f'<p class="note">{esc(when)}</p>' if when else ""
        crumbs = [("סידור", "/tefila/"), (f"נוסח {NUS[n]}", f"/tefila/{n}/")]
        if p["id"] in SVC_OF:
            crumbs.append((sec_label, sec_href))
        crumbs.append((pname(p), me))
        page(me, f"{tname} נוסח {NUS[n]}: טקסט מנוקד לקריאה | {BRAND}", fit_desc(head, " ".join(paras[:3])),
             p["t"], crumbs, text=text, meta=meta, before=plain_html + before, h1_ctx=ctx, bar_extra=switch, after=after, app_hash=f"p-{p['id']}",
             ld=[{"@type": "CreativeWork", "name": pname(p), "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me, "isPartOf": siddur_of(n)}])

# ---------- service pages ----------
def opening(p):
    return snippet(" ".join(TEXTS[p["n"]][p["id"]][:2]), 64)

for n in NUS:
    for si, (key, label, cfg) in enumerate(SERVICES):
        items = SVC[(n, key)]
        name = svc_name(n, key)
        path = f"/tefila/{n}/{key}/"
        first = items[0][0]
        body = f'<p><a class="btn" href="/tefila/{first["id"]}/">מתחילים: {esc(first["t"])}</a></p>'
        cur, opened, num = None, False, 0
        for p, pre in items:
            s = sec_of(p)
            lab = " · ".join(s[len(pre):]) or s[-1]
            if lab != cur:
                if opened: body += "</ol>"
                body += f'<h3 class="grp">{esc(lab)}</h3><ol class="toc">'
                cur, opened = lab, True
            num += 1
            body += f'<li><a href="/tefila/{p["id"]}/"><i>{num}</i><span><b>{esc(p["t"])}</b><small>{esc(opening(p))}</small></span></a></li>'
        body += "</ol>"
        pv = SERVICES[si - 1] if si else None
        nx = SERVICES[si + 1] if si + 1 < len(SERVICES) else None
        body += pager((f"/tefila/{n}/{pv[0]}/", svc_name(n, pv[0])) if pv else None, (f"/tefila/{n}/{nx[0]}/", svc_name(n, nx[0])) if nx else None)
        body += nus_note(n, f"/tefila/{NUS_NOTE[n][1]}/{key}/", f"{svc_name(NUS_NOTE[n][1], key)} בנוסח {NUS[NUS_NOTE[n][1]]}") if n in NUS_NOTE else ""
        body += chips(f"{label} בנוסח אחר", [(f"/tefila/{m}/{key}/", f"{svc_name(m, key)} · נוסח {NUS[m]}") for m in NUS if m != n])
        relp = [by_title(n, t) for t in ("ברכת המזון", "תפילת הדרך", "קריאת שמע על המיטה", "ספירת העומר")]
        body += chips("עוד בסידור", [(f"/tefila/{n}/", f"סידור נוסח {NUS[n]}, כל התפילות")]
                      + [(f'/tefila/{q["id"]}/', lead_of(q)) for q in relp if q and q["id"] not in {x[0]["id"] for x in items}]
                      + [("/tehillim/", "ספר תהילים")])
        parts = "חלק אחד" if num == 1 else f"{num} חלקים"
        desc = fit_desc(f"{name} בנוסח {NUS[n]}: סדר התפילה המלא לפי הסדר, {parts}, מ{plain(items[0][0]['t'])} ועד {plain(items[-1][0]['t'])}. כל חלק בעמוד קריאה משלו, בניקוד מלא",
                        tails=("קריאה נוחה בנייד.",))
        page(path, f"{name} | נוסח {NUS[n]}: סדר התפילה המלא | {BRAND}", desc, name,
             [("סידור", "/tefila/"), (f"נוסח {NUS[n]}", f"/tefila/{n}/"), (name, path)],
             h1_ctx=f"נוסח {NUS[n]}", after=body, hub=True, prio="0.8", app_hash=f"p-{first['id']}", app_label="לתפילה באפליקציה",
             lead=f"סדר תפילת {label} של ימי החול בנוסח {NUS[n]}, לפי הסדר: {parts}, כל חלק בעמוד קריאה משלו.",
             ld=[collection(f"{name}, נוסח {NUS[n]}", path, [f'/tefila/{p["id"]}/' for p, _ in items])])

# ---------- most wanted (shared by the hubs) ----------
WANT_REPORT = []
def want_block(only=None):
    out = '<ul class="want">'
    for key, label, _ in SERVICES:
        links = "".join(f'<a href="/tefila/{n}/{key}/" title="{esc(svc_name(n, key))} בנוסח {esc(NUS[n])}">נוסח {esc(NUS[n])}</a>' for n in NUS if only in (None, n))
        out += f'<li><b>{esc(label)} לימי חול</b><span>{links}</span></li>'
    for label, titles in WANT:
        links = ""
        for n in NUS:
            q = by_title(n, *titles)
            if only is None:
                WANT_REPORT.append((label, n, q["id"] if q else None, q["t"] if q else None))
            if q and only in (None, n):
                links += f'<a href="/tefila/{q["id"]}/" title="{esc(label)} בנוסח {esc(NUS[n])}: {esc(pname(q))}">{"נוסח " + esc(NUS[n]) if only is None else "לתפילה"}</a>'
        if links:
            out += f'<li><b>{esc(label)}</b><span>{links}</span></li>'
    for n in NUS:   # whole sections that people look for by name
        for gi, (lab, ps) in enumerate(GROUPS[n]):
            if lab == "הגדה של פסח" and only in (None, n):
                out += f'<li><b>הגדה של פסח</b><span><a href="/tefila/{n}/#g{gi + 1}" title="הגדה של פסח בנוסח {esc(NUS[n])}, {len(ps)} חלקים">{"נוסח " + esc(NUS[n]) if only is None else "לסדר ההגדה"}</a></span></li>'
    return out + "</ul>"

def nusach_lists(n, hlevel, prefix):
    out = ""
    for gi, (lab, ps) in enumerate(GROUPS[n]):
        out += f'<{hlevel} class="grp" id="{prefix}{gi + 1}">{esc(lab)}</{hlevel}><ul class="list">'
        out += "".join(f'<li><a href="/tefila/{p["id"]}/">{esc(p["t"])}</a></li>' for p in ps) + "</ul>"
    return out

# ---------- nusach hubs ----------
for n in NUS:
    path = f"/tefila/{n}/"
    body = (nus_note(n, f"/tefila/{NUS_NOTE[n][1]}/", f"סידור נוסח {NUS[NUS_NOTE[n][1]]}") if n in NUS_NOTE else "")
    body += '<h2 class="sec">תפילות ימי החול</h2><ul class="cards">'
    for key, label, _ in SERVICES:
        items = SVC[(n, key)]
        body += f'<li><a href="/tefila/{n}/{key}/"><b>{esc(svc_name(n, key))}</b><small>{len(items)} חלקים, מ{esc(items[0][0]["t"])} ועד {esc(items[-1][0]["t"])}</small></a></li>'
    body += '</ul><h2 class="sec" id="mevukashot">התפילות המבוקשות</h2>' + want_block(n)
    body += chips("הסידור בנוסח אחר", [(f"/tefila/{m}/", f"סידור נוסח {NUS[m]}") for m in NUS if m != n])
    body += f'<h2 class="sec big" id="kol">כל התפילות בנוסח {esc(NUS[n])}</h2>' + nusach_lists(n, "h3", "g")
    cnt = len(by_nus[n])
    page(path, f"סידור נוסח {NUS[n]} אונליין: כל התפילות בניקוד מלא | {BRAND}",
         fit_desc(f"סידור תפילה בנוסח {NUS[n]}, {cnt} תפילות וברכות בניקוד מלא: שחרית, מנחה וערבית לימי חול, שבת, ראש חודש וחגים, ברכת המזון, תפילת הדרך וקריאת שמע שעל המיטה", tails=()),
         f"סידור נוסח {NUS[n]}", [("סידור", "/tefila/"), (f"נוסח {NUS[n]}", path)], after=body, hub=True, prio="0.9",
         app_hash="siddur", app_label="לסידור באפליקציה",
         lead=f"{cnt} תפילות וברכות בנוסח {NUS[n]}, בניקוד מלא. כל תפילה בעמוד קריאה משלה.",
         ld=[collection(f"סידור נוסח {NUS[n]}", path, [f"/tefila/{n}/{k}/" for k, _, _ in SERVICES] + [f'/tefila/{p["id"]}/' for p in by_nus[n]])])

# ---------- siddur hub ----------
hub = '<ul class="cards">' + "".join(
    f'<li><a href="/tefila/{n}/"><b>נוסח {esc(NUS[n])}</b><small>{len(by_nus[n])} תפילות וברכות, שחרית, מנחה וערבית</small></a></li>' for n in NUS) + "</ul>"
hub += '<h2 class="sec" id="mevukashot">התפילות המבוקשות</h2>' + want_block()
hub += '<h2 class="sec">כל התפילות לפי נוסח</h2><div class="related">' + "".join(f'<a href="#{n}">נוסח {esc(NUS[n])}</a>' for n in NUS) + "</div>"
for n in NUS:
    hub += f'<h2 class="sec big" id="{n}"><a href="/tefila/{n}/">נוסח {esc(NUS[n])}</a></h2>' + nusach_lists(n, "h3", n + "-g")
page("/tefila/", f"סידור תפילה אונליין | עדות המזרח, ספרד ואשכנז | {BRAND}",
     "סידור תפילה מלא אונליין בניקוד: שחרית, מנחה, ערבית, ברכת המזון, תפילת הדרך, קריאת שמע שעל המיטה, שבת וחגים, בנוסח עדות המזרח, ספרד ואשכנז.",
     "סידור תפילה", [("סידור", "/tefila/")], after=hub, app_hash="siddur", hub=True, prio="0.9",
     lead="כל התפילות בשלושה נוסחים, בניקוד מלא. כל תפילה בעמוד קריאה משלה.",
     ld=[collection("סידור תפילה", "/tefila/", [f"/tefila/{n}/" for n in NUS])])

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
    after += chips("עוד בספרייה", [("/sefer/", "כל ספרי הספרייה"), ("/tehillim/", "ספר תהילים"), ("/tefila/", "סידור תפילה")])
    sub = b.get("sub", "")
    nsec = len([s for s in b["secs"] if s.get("h")])
    jump = ('<div class="related" style="margin-block-end:1rem">' + "".join(
        f'<a href="#s{j+1}">{esc(s["h"])}</a>' for j, s in enumerate(b["secs"]) if s.get("h")) + "</div>") if nsec > 1 else ""
    first_v = " ".join(b["secs"][0]["v"][:3])
    _bx = PLAIN_B.get(k, "")
    jump = (f'<aside class="plainx" aria-label="הסבר קצר"><b>על מה {esc(b["t"])}?</b><p>{esc(_bx)}</p></aside>' if _bx else "") + jump
    page(me, f"{b['t']} | הנוסח המלא בניקוד | {BRAND}",
         fit_desc(f"{b['t']} בניקוד מלא אונליין" + (f". {plain(sub)}" if sub else "") + (f". {nsec} פרקים בעמוד אחד" if nsec > 1 else ""), first_v),
         b["t"], [("ספרייה", "/sefer/"), (b["t"], me)],
         text=text, meta=esc(sub), before=jump, after=after, app_hash=f"b-{k}",
         ld=[{"@type": "Book" if nsec > 1 else "CreativeWork", "name": b["t"], "inLanguage": "he", "isAccessibleForFree": True, "url": SITE + me}])
page("/sefer/", f"ספרייה: פרקי אבות, מגילות, פרק שירה ועוד | {BRAND}",
     "ספרייה בניקוד מלא: פרקי אבות, שיר השירים, מגילת רות, מגילת אסתר, איכה, קהלת, משלי, פרק שירה, פרשת המן, סליחות, יזכור ועוד. כל ספר בעמוד קריאה משלו.",
     "ספרייה", [("ספרייה", "/sefer/")],
     after='<ul class="list">' + "".join(f'<li><a href="/sefer/{k}/">{esc(b["t"])}<small>{esc(b.get("sub",""))}</small></a></li>' for k, b in B.items()) + "</ul>"
           + chips("עוד באתר", [("/tefila/", "סידור תפילה"), ("/tehillim/", "ספר תהילים"), ("/tehillim/yomi/", "תהילים יומי"), ("/kelim/", "כלים אישיים")]),
     app_hash="sifriya", hub=True, prio="0.9", lead="ספרים ופרקים שקוראים לאורך השנה.",
     ld=[collection("ספרייה", "/sefer/", [f"/sefer/{k}/" for k in B])])

# =====================================================================
# Explainers that lead into the app
# =====================================================================
yachad = ('<div class="hero"><p>כל אחד פרק.<br>ביחד ספר שלם.</p><a class="btn" href="/#zikaron">לתהילים יחד באפליקציה</a>'
          '<small>הקריאה המשותפת נפתחת באפליקציה של תפילה.</small></div>'
          '<h2 class="sec">איך פותחים קריאת תהילים משותפת</h2><ol class="steps">'
          '<li><b>פותחים קריאה</b><span>לרפואה, לעילוי נשמה או לכל בקשה אחרת, על שם האדם שקוראים בשבילו.</span></li>'
          '<li><b>שולחים קישור</b><span>משתפים את הקישור לקריאה בוואטסאפ, עם המשפחה, החברים או הקהילה.</span></li>'
          '<li><b>כל אחד קורא פרק</b><span>כל מי שנכנס מקבל פרק תהילים, קורא ומסמן שקרא.</span></li></ol>'
          '<div class="prose"><h2>חלוקת תהילים בין המשתתפים</h2>'
          '<p>בתהילים משותף 150 פרקי הספר מתחלקים בין כל מי שמצטרף לקריאה: כל אחד מקבל פרק, קורא אותו ומסמן שקרא. '
          'כשכל 150 הפרקים נקראו הספר נשלם, ומתחיל סבב חדש.</p></div>'
          '<p class="note">העמוד הזה מסביר איך קריאת התהילים המשותפת בנויה. פתיחת תהילים משותף והצטרפות לקריאה נעשות באפליקציה.</p>')
yachad += chips("לקריאה עצמית", [("/tehillim/", "ספר תהילים, כל 150 הפרקים"), ("/tehillim/refuah/", "תהילים לרפואה שלמה"),
                                 ("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/tehillim/kever/", "תהילים לבית העלמין"),
                                 ("/tehillim/tikkun/", "תיקון הכללי"), ("/tehillim/yomi/", "תהילים יומי"), ("/kelim/shem/", "תהילים קיט לפי שם")])
page("/tehillim-yachad/", f"תהילים יחד: קריאת תהילים משותפת, כל אחד פרק | {BRAND}",
     "תהילים יחד: קריאת תהילים משותפת לרפואה או לעילוי נשמה. פותחים תהילים משותף, שולחים קישור בוואטסאפ, וכל אחד קורא פרק. כל אחד פרק. ביחד ספר שלם.",
     "תהילים יחד", [("תהילים יחד", "/tehillim-yachad/")], after=yachad, hub=True, prio="0.8", h1_ctx="קריאת תהילים משותפת",
     lead="קריאת תהילים משותפת: מחלקים את 150 הפרקים בין כל מי שמצטרף, עד שהספר כולו נקרא.",
     ld=[{"@type": "WebPage", "name": "תהילים יחד", "url": SITE + "/tehillim-yachad/", "inLanguage": "he", "isPartOf": WEBSITE, "about": BOOK_T}])

# ---------- personal tools: what each one does and how it calculates (read from the app's own code), then into the app ----------
ABC = "אבגדהוזחטיכלמנסעפצקרשת"
_letters = ('<table><tr><th>אות</th><th>פסוקים בפרק קיט</th></tr>' + "".join(
    f"<tr><td>{c}</td><td>{gem(i * 8 + 1)} עד {gem(i * 8 + 8)}</td></tr>" for i, c in enumerate(ABC)) + "</table>")
TOOL = {
    "shem": ("תהילים קיט לפי שם: אותיות השם ואותיות נשמה",
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
              "", [("/tefila/", "סידור תפילה"), ("/tefila/mizrach/shacharit/", "שחרית לימי חול"), ("/tehillim/", "ספר תהילים")]),
}
assert set(TOOL) == {k for k, _, _ in KELIM}, "a tool was added to the app: describe it in TOOL"
for i, (k, t, d) in enumerate(KELIM):
    ttl, head, paras, extra, rel = TOOL[k]
    pv, nx = (KELIM[i - 1] if i else None), (KELIM[i + 1] if i + 1 < len(KELIM) else None)
    body = (f'<p><a class="btn" href="/#kli-{k}">לפתיחת הכלי באפליקציה</a></p><div class="prose"><h2>איך זה עובד</h2>'
            + "".join(f"<p>{esc(x)}</p>" for x in paras) + extra + "</div>"
            + '<p class="note">הכלי מחשב לפי מה שמקלידים בו, ונפתח באפליקציה של תפילה.</p>'
            + pager((f"/kelim/{pv[0]}/", pv[1]) if pv else None, (f"/kelim/{nx[0]}/", nx[1]) if nx else None)
            + chips("קשור לכלי הזה", rel + [("/kelim/", "כל הכלים האישיים")]))
    page(f"/kelim/{k}/", f"{ttl} | {BRAND}", fit_desc(head, tails=("הכלי נפתח באפליקציה של תפילה.", "חינם וללא הרשמה.")),
         t, [("כלים אישיים", "/kelim/"), (t, f"/kelim/{k}/")], after=body, lead=d, hub=False, prio="0.7",
         ld=[{"@type": "WebPage", "name": t, "description": d, "url": f"{SITE}/kelim/{k}/", "inLanguage": "he", "isPartOf": WEBSITE}])

kelim = '<ul class="cards">'
for k, t, d in KELIM:
    kelim += f'<li><a href="/kelim/{k}/"><b>{esc(t)}</b><small>{esc(d)}</small><small>{esc(TOOL[k][0])}</small></a></li>'
kelim += '</ul><p class="note">הכלים מחשבים לפי מה שמקלידים בהם, ונפתחים באפליקציה של תפילה.</p>'
kelim += chips("קשור לכלים", [("/tehillim/119/", "תהילים פרק קיט"), ("/tehillim/neshama/", "תהילים לעילוי נשמה"), ("/tehillim/kever/", "תהילים לבית העלמין"),
                              ("/sefer/yizkor/", "יזכור"), ("/tehillim/yomi/", "תהילים יומי"), ("/tehillim-yachad/", "תהילים יחד")])
page("/kelim/", f"כלים אישיים: תהילים לפי השם, יארצייט, יום הולדת עברי וכיוון התפילה | {BRAND}",
     fit_desc("כלים אישיים באתר תפילה: " + ", ".join(t for _, t, _ in KELIM) + ". הסבר קצר על כל כלי וקישור לפתיחתו באפליקציה", tails=()),
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
        out.append((s, f, hm(sf - datetime.timedelta(minutes=mins)), hm(hv), hm(ss + datetime.timedelta(minutes=72))))
    return out
SH_JS = ("(function(){var t=new Date();t.setHours(0,0,0,0);var r=document.querySelectorAll('.zt tbody tr'),f=null;"
         "for(var i=0;i<r.length;i++){var d=new Date(r[i].getAttribute('data-s')+'T00:00:00');r[i].classList.remove('now');if(d<t)r[i].classList.add('past');else if(!f){f=r[i];f.classList.add('now')}}"
         "if(f){var c=f.querySelectorAll('td'),n=document.querySelectorAll('.znow b'),w=document.getElementById('zwhen');if(n.length>2){n[0].textContent=c[1].textContent;n[1].textContent=c[2].textContent;n[2].textContent=c[3].textContent}if(w)w.textContent=c[0].textContent}})();")
sh_links = [(f"/zmanei-shabbat/{c[0]}/", "זמני שבת ב" + c[1]) for c in SH_CITIES]
for c in SH_CITIES:
    slug, name, lat, lon, tz, mins = c; rows = shabbat_rows(c)
    if not rows: continue
    s0, f0, cand, hav, rt = rows[0]
    dtxt = lambda d: f"{d.day} {HEMON[d.month - 1]} {d.year}"
    body = (f'<p class="note">שבת הקרובה: <b id="zwhen">ערב שבת {dtxt(f0)}</b></p>'
            f'<div class="znow"><div><span>כניסת שבת (הדלקת נרות)</span><b>{cand}</b><small>{mins} דקות לפני השקיעה</small></div>'
            f'<div><span>יציאת שבת</span><b>{hav}</b><small>צאת הכוכבים</small></div><div><span>רבנו תם</span><b>{rt}</b><small>72 דקות אחרי השקיעה</small></div></div>'
            f'<h2 class="sec">זמני כניסת ויציאת שבת ב{esc(name)} לשבתות הקרובות</h2>'
            '<table class="zt"><thead><tr><th scope="col">ערב שבת</th><th scope="col">כניסת שבת</th><th scope="col">יציאת שבת</th><th scope="col">רבנו תם</th></tr></thead><tbody>'
            + "".join(f'<tr data-s="{s.isoformat()}"{chr(32)+"class="+chr(34)+"now"+chr(34) if i == 0 else ""}><td>ערב שבת {dtxt(f)}</td><td><b>{a}</b></td><td><b>{b}</b></td><td>{r_}</td></tr>' for i, (s, f, a, b, r_) in enumerate(rows))
            + '</tbody></table>'
            f'<p class="note">הזמנים מחושבים לפי מיקום {esc(name)} ושעון המקום, ועשויים לסטות בדקה או שתיים מלוחות אחרים. הדלקת נרות לפי המנהג המקובל במקום ({mins} דקות לפני השקיעה). למעשה יש להחמיר ולהקדים.</p>'
            + chips("לקראת שבת", [("/tefila/", "סידור תפילה"), ("/tehillim/", "ספר תהילים"), ("/tehillim/yomi/", "תהילים יומי"), ("/tehillim-yachad/", "תהילים יחד"), ("/zmanei-shabbat/", "זמני שבת בכל הערים")])
            + chips("ערים נוספות", [l for l in sh_links if l[0] != f"/zmanei-shabbat/{slug}/"][:12]))
    page(f"/zmanei-shabbat/{slug}/", f"זמני שבת ב{name}: כניסת שבת ויציאת שבת השבוע | {BRAND}",
         f"מתי נכנסת ומתי יוצאת שבת ב{name}: שעת הדלקת נרות, שעת צאת השבת וזמן רבנו תם לשבת הקרובה, ולוח זמנים לשבתות הבאות, מחושב לפי מיקום העיר.",
         f"זמני שבת ב{name}", [("זמני שבת", "/zmanei-shabbat/"), (name, f"/zmanei-shabbat/{slug}/")], after=body, hub=True, prio="0.8", script=SH_JS,
         app_hash="home", app_label="לכל זמני היום באפליקציה", lead=f"כניסת שבת ויציאת שבת ב{name}, מתעדכן לכל שבת.",
         ld=[{"@type": "WebPage", "name": f"זמני שבת ב{name}", "url": SITE + f"/zmanei-shabbat/{slug}/", "inLanguage": "he", "isPartOf": WEBSITE,
              "about": {"@type": "Place", "name": name, "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon}}}])
jr = shabbat_rows(SH_CITIES[0])[0]
shhub = ('<ul class="cards">' + "".join(f'<li><a href="/zmanei-shabbat/{c[0]}/"><b>{esc(c[1])}</b><small>כניסה {shabbat_rows(c, 1)[0][2]} · יציאה {shabbat_rows(c, 1)[0][3]}</small></a></li>' for c in SH_CITIES) + '</ul>'
         '<p class="note">הזמנים בכרטיסים הם לשבת הקרובה ביום בניית הדף. בדף של כל עיר מופיעה תמיד השבת הקרובה ולוח לשבתות הבאות.</p>')
page("/zmanei-shabbat/", f"זמני כניסת שבת ויציאת שבת לפי עיר: מתי נכנסת ומתי יוצאת שבת | {BRAND}",
     "מתי נכנסת שבת ומתי יוצאת שבת השבוע: זמני הדלקת נרות וצאת השבת בירושלים, תל אביב, חיפה, באר שבע ובעשרות ערים נוספות בארץ ובעולם.",
     "זמני כניסת ויציאת שבת", [("זמני שבת", "/zmanei-shabbat/")], after=shhub, hub=True, prio="0.9", app_hash="home", app_label="לזמני היום באפליקציה",
     lead=f"{len(SH_CITIES)} ערים. בוחרים עיר ורואים מתי נכנסת ומתי יוצאת השבת.",
     ld=[{"@type": "CollectionPage", "name": "זמני כניסת ויציאת שבת", "url": SITE + "/zmanei-shabbat/", "inLanguage": "he", "isPartOf": WEBSITE,
          "mainEntity": item_list([f"/zmanei-shabbat/{c[0]}/" for c in SH_CITIES])}])

# ---------- 404 ----------
nf = ('<p><a class="btn" href="/">לדף הבית</a></p><ul class="cards" style="margin-block-start:1.5rem">'
      '<li><a href="/tefila/"><b>סידור תפילה</b><small>עדות המזרח, ספרד ואשכנז</small></a></li>'
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
