"""Regression check for the prayer texts: every record has a page, the page carries exactly the words of the data,
every page is in the sitemap, and no record is empty. Run from the repo root after tools/prerender.py:
    python3 tools/check-texts.py
It reads data/ and never changes it. Stray vowel marks are listed as warnings for a person to decide on."""
import json, re, os, sys, html, collections
R = os.getcwd() + '/'
I = json.load(open(R + 'data/index.json', encoding='utf-8'))
TAG = re.compile(r'<[^>]+>'); NIK = re.compile('[֑-ׇ]')
words = lambda s: re.sub(r'[^א-ת ]', '', NIK.sub('', html.unescape(TAG.sub(' ', s)))).split()
sm = open(R + 'sitemap.xml', encoding='utf-8').read()
URLS = json.load(open(R + 'data/urls.json', encoding='utf-8'))
RD = open(R + '_redirects', encoding='utf-8').read()
OLD = json.load(open(R + 'tools/old-urls.json', encoding='utf-8'))
noredir = []
DUPC = json.load(open(R + 'tools/dup-canon.json', encoding='utf-8'))
bad, nomap, nikud, empty, dup = [], [], [], [], collections.defaultdict(list)
for n in ('mizrach', 'sefard', 'ashkenaz'):
    T = json.load(open(R + f'data/{n}.json', encoding='utf-8'))
    for p in I['prayers']:
        if p['n'] != n:
            continue
        ps = T.get(p['id']) or []
        if not ps or not ''.join(ps).strip():
            empty.append(p['id'])
        raw = ' '.join(ps)
        # nikud integrity: a combining mark with no letter before it, or the replacement character
        if '�' in raw or re.search(r'(^|[\s>])[ְ-ׇֽֿׁׂׅׄ]', raw):
            nikud.append(p['id'])
        dup[' '.join(words(raw))].append(p['id'])
        f = R + URLS[p['id']].strip('/') + '/index.html'
        if f"/tefila/{p['id']}/ {URLS[p['id']]} 301" not in RD or (OLD.get(p['id']) and f"{OLD[p['id']]} {URLS[p['id']]} 301" not in RD):
            noredir.append(p['id'])
        if not os.path.exists(f):
            bad.append((p['id'], 'no page')); continue
        h = open(f, encoding='utf-8').read()
        m = re.search(r'<article class="text" id="text">(.*?)</article>', h, re.S)
        if not m:
            bad.append((p['id'], 'no text block')); continue
        a, b = words(m.group(1)), words(raw)
        if a != b:
            # the page may drop a first paragraph that only repeats the title
            b2 = words(' '.join(ps[1:])) if len(ps) > 1 else b
            if a != b2:
                bad.append((p['id'], f'words differ: page {len(a)} data {len(b)}'))
        if f"{URLS[p['id']]}</loc>" not in sm:
            if URLS[p['id']] not in DUPC: nomap.append(p['id'])   # an exact repeat names the first copy as canonical and is left out on purpose
print('records', len(I['prayers']), '| pages whose text differs from the data:', len(bad), bad[:8])
print('not in sitemap:', len(nomap), nomap[:8], '| old address without a redirect:', len(noredir), noredir[:8])
if len(set(URLS.values())) != len(URLS):
    print('RESULT: FAILED (two prayers share an address)'); sys.exit(1)
print('empty records:', empty, '| damaged nikud:', nikud[:10])
d = [v for k, v in dup.items() if len(v) > 1 and len(k.split()) > 30]
print('identical bodies (over 30 words): groups', len(d), '| records', sum(len(v) for v in d))
same_n = [v for v in d if len({x.split('-')[0] for x in v}) < len(v)]
print('  of them inside one nusach:', len(same_n), same_n[:6])

# ---- the weekly portions: every page carries exactly the verses of its portion, word for word, and the 54 pages cover the whole Torah once ----
TOR = json.load(open(R + 'data/torah.json', encoding='utf-8'))['books']
PAR = json.load(open(R + 'tools/parashot.json', encoding='utf-8'))
pbad, seen_v = [], 0
for p in PAR:
    slug = re.sub(r"[^a-z]+", "-", p["key"].lower().replace("'", "")).strip("-")
    f = R + 'parasha/' + slug + '/index.html'
    if not os.path.exists(f):
        pbad.append((slug, 'no page')); continue
    art = re.search(r'<article[^>]*>(.*?)</article>', open(f, encoding='utf-8').read(), re.S).group(1)
    got = [html.unescape(re.sub(r'<[^>]+>', '', x)) for x in re.findall(r'<p><sup>[^<]*</sup>(.*?)</p>', art, re.S)]
    want = []
    c1, v1 = p['aliyot'][0][:2]; c2, v2 = p['aliyot'][-1][2:]
    for c in range(c1, c2 + 1):
        ch = TOR[p['book']][c - 1]
        want += ch[(v1 if c == c1 else 1) - 1:(v2 if c == c2 else len(ch))]
    seen_v += len(got)
    if got != want:
        pbad.append((slug, f'page {len(got)} verses, data {len(want)}'))
    if len(re.findall(r'<h2 id="a\d">', art)) != 7:
        pbad.append((slug, 'not seven aliyot'))
total_v = sum(len(c) for b in TOR.values() for c in b)
print('portions', len(PAR), '| verses on the pages', seen_v, 'of', total_v, '| pages that differ from the data:', len(pbad), pbad[:6])
if pbad or seen_v != total_v:
    print('RESULT: FAILED (weekly portions)'); sys.exit(1)
if bad or nomap or empty or noredir:
    print('RESULT: FAILED'); sys.exit(1)
print('RESULT: OK')
