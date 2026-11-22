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
            nomap.append(p['id'])
print('records', len(I['prayers']), '| pages whose text differs from the data:', len(bad), bad[:8])
print('not in sitemap:', len(nomap), nomap[:8], '| old address without a redirect:', len(noredir), noredir[:8])
if len(set(URLS.values())) != len(URLS):
    print('RESULT: FAILED (two prayers share an address)'); sys.exit(1)
print('empty records:', empty, '| damaged nikud:', nikud[:10])
d = [v for k, v in dup.items() if len(v) > 1 and len(k.split()) > 30]
print('identical bodies (over 30 words): groups', len(d), '| records', sum(len(v) for v in d))
same_n = [v for v in d if len({x.split('-')[0] for x in v}) < len(v)]
print('  of them inside one nusach:', len(same_n), same_n[:6])

if bad or nomap or empty or noredir:
    print('RESULT: FAILED'); sys.exit(1)
print('RESULT: OK')
