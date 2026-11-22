// Search for "מה מברכים על". Pure functions over the data, shared by the page and by tools/test-brachot.mjs.
// D = {foods:[{id,name,alias[],...}], choices:[{term, alias[], ids[]}]}
function mmNorm(s) {
  return String(s || '').toLowerCase()
    .replace(/[־\-–—_/]+/g, ' ')                // maqaf and hyphens are spaces (first: the maqaf sits inside the nikud range)
    .replace(/[֑-ׇ]/g, '')            // nikud and cantillation
    .replace(/[׳'`’"״“”]/g, '')                 // geresh, gershayim, quotes: ג׳חנון = גחנון
    .replace(/[?!.,:;()\[\]]/g, ' ')
    .replace(/ך/g, 'כ').replace(/ם/g, 'מ').replace(/ן/g, 'נ').replace(/ף/g, 'פ').replace(/ץ/g, 'צ')
    .replace(/\s+/g, ' ').trim();
}
// "מה מברכים על שווארמה", "ברכה אחרונה על קפה" -> the food, and whether the question is about the after-blessing
function mmParse(q) {
  let t = mmNorm(q), after = false;
  const pre = [/^(מה|איזו|איזה) (ברכה )?(אחרונה )?(מברכימ|מברכ|לברכ) (אחרי|לאחר) /, /^(מה )?(ה)?ברכה (ה)?אחרונה (של|על|ל) ?/, /^ברכה אחרונה /,
    /^(מה|איזו|איזה) (ברכה )?(מברכימ|מברכ|לברכ) על /, /^(מה )?(ה)?ברכה (ה)?ראשונה (של|על) /, /^(מה )?(ה)?ברכה (של|על) /, /^מברכימ על /, /^על מה מברכימ /];
  for (let i = 0; i < pre.length; i++) if (pre[i].test(t)) { if (i < 3) after = true; t = t.replace(pre[i], ''); break; }
  return { term: t.trim(), after };
}
function mmIndex(D) {
  const keys = new Map();   // normalised name or alias -> [food ids]
  const add = (k, id) => { k = mmNorm(k); if (!k) return; if (!keys.has(k)) keys.set(k, []); if (!keys.get(k).includes(id)) keys.get(k).push(id); };
  for (const f of D.foods) { add(f.name, f.id); (f.alias || []).forEach(a => add(a, f.id)); }
  const choices = new Map();
  for (const c of D.choices) [c.term].concat(c.alias || []).forEach(t => choices.set(mmNorm(t), c));
  const byId = new Map(D.foods.map(f => [f.id, f]));
  return { keys, choices, byId };
}
// -> {kind:'empty'} | {kind:'choice', choice, list} | {kind:'food', food, list, after} | {kind:'none', term}
function mmSearch(D, IX, q) {
  const { term, after } = mmParse(q);
  if (!term) return { kind: 'empty' };
  const ch = IX.choices.get(term);
  const scored = [];
  for (const f of D.foods) {
    let best = -1;
    for (const k of [f.name].concat(f.alias || [])) {
      const n = mmNorm(k);
      const s = n === term ? 0 : n.startsWith(term + ' ') ? 1 : n.startsWith(term) ? 2 : (' ' + n + ' ').includes(' ' + term + ' ') ? 3 : n.includes(term) && term.length >= 3 ? 4 : -1;
      if (s >= 0 && (best < 0 || s < best)) best = s + (k === f.name ? 0 : .5);
    }
    if (best >= 0) scored.push([best, f]);
  }
  scored.sort((a, b) => a[0] - b[0] || a[1].name.length - b[1].name.length);
  const list = scored.map(x => x[1]);
  if (ch) return { kind: 'choice', choice: ch, list: ch.ids.map(id => IX.byId.get(id)), after };
  const exact = IX.keys.get(term);
  if (exact && exact.length === 1) return { kind: 'food', food: IX.byId.get(exact[0]), list, after };
  if (exact && exact.length > 1) return { kind: 'choice', choice: { term, q: 'למה התכוונתם?', ids: exact }, list: exact.map(id => IX.byId.get(id)), after };
  if (!list.length) return { kind: 'none', term };
  // nothing exact: one candidate opens, several are offered, the best one first
  if (list.length === 1 || scored[0][0] < 3 && (scored.length < 2 || scored[1][0] - scored[0][0] >= 1)) return { kind: 'food', food: list[0], list, after };
  return { kind: 'choice', choice: { term, q: 'למה התכוונתם?', ids: list.slice(0, 6).map(f => f.id) }, list: list.slice(0, 6), after };
}
if (typeof module !== 'undefined') module.exports = { mmNorm, mmParse, mmIndex, mmSearch };
