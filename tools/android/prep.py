import json, os, re, sys, collections
R = '/home/user/tfilah/'; A = sys.argv[1]
T = lambda s: re.sub(r'[\t\r\n]+', ' ', str(s or '')).strip()
ix = json.load(open(R + 'data/index.json', encoding='utf-8'))
urls = json.load(open(R + 'data/urls.json', encoding='utf-8'))
umap = urls if isinstance(urls, dict) else {}
rows = []
for n in ('mizrach', 'sefard', 'ashkenaz'):
    d = json.load(open(R + f'data/{n}.json', encoding='utf-8'))
    for p in ix['prayers']:
        if p['n'] != n or p['id'] not in d: continue
        paras = [T(x) for x in d[p['id']] if T(x)]
        open(f"{A}/p/{p['id']}.txt", 'w', encoding='utf-8').write('\n'.join(paras))
        s = p.get('s') or []
        u = umap.get(p['id'], '')
        u = u if isinstance(u, str) else ''
        rows.append('\t'.join([p['id'], n, T(s[0]) if s else 'תפילות נוספות', T(' · '.join(s[1:])), T(p['t']), u]))
open(A + '/index.tsv', 'w', encoding='utf-8').write('\n'.join(rows))
def heb(n):
    out = ''
    for v, c in ((100, 'ק'), (90, 'צ'), (80, 'פ'), (70, 'ע'), (60, 'ס'), (50, 'נ'), (40, 'מ'), (30, 'ל'), (20, 'כ'), (10, 'י'), (9, 'ט'), (8, 'ח'), (7, 'ז'), (6, 'ו'), (5, 'ה'), (4, 'ד'), (3, 'ג'), (2, 'ב'), (1, 'א')):
        while n >= v: out += c; n -= v
    return out.replace('יה', 'טו').replace('יו', 'טז')
teh = json.load(open(R + 'data/tehillim.json', encoding='utf-8'))
NIK = re.compile('[֑-ׇ​-‍]')
trows = []
for i, ch in enumerate(teh, 1):
    open(f'{A}/t/{i}.txt', 'w', encoding='utf-8').write('\n'.join(f'<small>{heb(k)}</small> {T(v)}' for k, v in enumerate(ch, 1)))
    first = ' '.join(NIK.sub('', re.sub('<[^>]+>', '', ch[0])).replace('־', ' ').split()[:5]).replace('יהוה', "ה'")
    trows.append(f'{i}\t{heb(i)}\t{first}')
open(A + '/tehillim.tsv', 'w', encoding='utf-8').write('\n'.join(trows))
b = json.load(open(R + 'tools/brachot/out.json', encoding='utf-8'))
BT = {"etz": "בורא פרי העץ", "adama": "בורא פרי האדמה", "mezonot": "בורא מיני מזונות", "gefen": "בורא פרי הגפן", "shehakol": "שהכל נהיה בדברו", "motzi": "המוציא לחם מן הארץ"}
AT = {"nefashot": "בורא נפשות", "michya": "על המחיה", "haetz": "על העץ", "hagefen": "על הגפן", "mazon": "ברכת המזון", "none": "אין ברכה אחרונה"}
frows = []
for f in b['foods']:
    if f.get('status') != 'ok': continue
    ops = '¶'.join('§'.join([T(o['who']), BT.get(o.get('before'), ''), AT.get(o.get('after'), ''), T(o.get('text'))]) for o in f.get('ops') or [])
    src = ' · '.join(b['sources'][k][0] for k in f.get('src', []) if k in b['sources'])
    if not ops and (f.get('before') not in BT or f.get('after') not in AT): continue
    frows.append('\t'.join([f['id'], T(f['name']), '|'.join(T(x) for x in f.get('alias', [])), f.get('kind') or '', BT.get(f.get('before'), ''), AT.get(f.get('after'), ''),
                            T(f.get('cond')), T(f.get('after_cond')), T(f.get('note')), ops, T(src)]))
open(A + '/brachot.tsv', 'w', encoding='utf-8').write('\n'.join(frows))
g = collections.Counter(r.split('\t')[1] for r in rows)
print('prayers', len(rows), dict(g), 'with url', sum(1 for r in rows if r.split('\t')[5]), 'psalms', len(trows), 'foods', len(frows))
print(rows[0]); print(trows[22]); print(frows[0][:200])
from fontTools.ttLib import TTFont
for n in ('heebo-hebrew-900', 'heebo-hebrew-700', 'assistant-hebrew-400', 'assistant-hebrew-600', 'assistant-hebrew-700'):
    f = TTFont(R + f'fonts/{n}.woff2'); f.flavor = None; f.save(f'{A}/fonts/{n}.ttf')
print(os.listdir(A + '/fonts'))
