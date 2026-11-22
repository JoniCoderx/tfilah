// Acceptance and consistency checks for "מה מברכים על". Reads tools/brachot/out.json (written by tools/brachot/build.py).
//   node tools/test-brachot.mjs
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { mmNorm, mmParse, mmIndex, mmSearch } = require("./brachot/search.js");
const D = JSON.parse(fs.readFileSync(new URL("./brachot/out.json", import.meta.url), "utf8"));
const IX = mmIndex(D);
let pass = 0, fail = 0;
const ok = (name, cond, detail = "") => { if (cond) pass++; else { fail++; console.log("FAIL", name, detail); } };
const S = q => mmSearch(D, IX, q);
const food = q => { const r = S(q); return r.kind === "food" ? r.food : null; };
const choice = q => { const r = S(q); return r.kind === "choice" ? r.list.map(f => f.id) : null; };

// ---- consistency ----
// 1. a name or alias leads to one record, unless a chooser was written for it on purpose
for (const [k, ids] of IX.keys) ok(`"${k}" names one record`, ids.length === 1 || IX.choices.has(k), ids.join(", "));
// 2. every record is reachable by its own name, and by each of its aliases (directly or through a chooser that contains it)
for (const f of D.foods) for (const k of [f.name, ...(f.alias || [])]) {
  const r = S(k);
  ok(`"${k}" reaches ${f.id}`, (r.kind === "food" && r.food.id === f.id) || (r.kind === "choice" && r.list.some(x => x.id === f.id)), r.kind + " " + (r.food ? r.food.id : ""));
}
// 3. choosers point at records, and never at a single one
for (const c of D.choices) ok(`chooser "${c.term}"`, c.ids.length >= 2 && c.ids.every(id => IX.byId.has(id)));
// 4. no answer without a source unless it is marked for review; "review" with no source shows no ruling borrowed from a category
for (const f of D.foods) {
  const ruled = !!f.before || (f.ops || []).length > 0;
  ok(`${f.id}: ruling has a source or is marked review`, !ruled || (f.src || []).length > 0 || f.status === "review");
  ok(`${f.id}: after-blessing is stated`, !f.before || !!f.after, "before without after");
  for (const k of f.src || []) ok(`${f.id}: source ${k} exists`, !!D.sources[k]);
  for (const o of f.ops || []) ok(`${f.id}: opinion names who says it`, !!o.who && (!!o.before || !!o.after || !!o.text));
}
// 5. normalisation
ok("nikud, geresh, maqaf and punctuation are ignored", mmNorm("גָּ׳חְנוּן") === mmNorm("גחנון") && mmNorm("פיש־אנד-צ'יפס!") === mmNorm("פיש אנד ציפס"));
ok("question forms are understood", mmParse("מה מברכים על שווארמה?").term === mmNorm("שווארמה") && mmParse("ברכה אחרונה על קפה").after === true && mmParse("ברכה אחרונה על קפה").term === mmNorm("קפה"));

// ---- acceptance (the numbered cases of the brief) ----
const gum = food("מסטיק"), candy = food("סוכריות");
ok("1. מסטיק has its own record", !!gum && (!candy || gum.id !== candy.id));
ok("1. מסטיק does not get בורא נפשות", !!gum && gum.after !== "nefashot" && !(gum.ops || []).some(o => o.after === "nefashot"), gum && JSON.stringify([gum.after, gum.ops]));
const bamba = food("במבה"), nougat = food("במבה נוגט");
ok("2. במבה shows two named opinions with sources", !!bamba && (bamba.ops || []).length >= 2 && bamba.ops.every(o => o.who) && (bamba.src || []).length >= 2);
ok("2. במבה נוגט is a separate record that does not inherit", !!nougat && nougat.id !== bamba.id);
ok("3. שוארמה opens a chooser", (choice("שוארמה") || []).length >= 2 && (choice("שווארמה") || []).length >= 2);
const ids3 = ["שווארמה בלאפה", "שווארמה בצלחת", "סביח בפיתה", "סביח בצלחת"].map(q => (food(q) || {}).id);
ok("3. the four explicit dishes open four different records", ids3.every(Boolean) && new Set(ids3).size === 3 + 1, ids3.join(", "));
ok("3. שווארמה בלאפה and שווארמה בפיתה are the same record", (food("שווארמה בלאפה") || {}).id === (food("שווארמה בפיתה") || {id: 0}).id);
ok("3. pita versions are המוציא, plate versions are not", ["שווארמה בלאפה", "סביח בפיתה"].every(q => (food(q) || {}).before === "motzi") && (food("שווארמה בצלחת") || {}).before !== "motzi");
ok("4. מג׳דרה and מגדרה are the same record", !!food("מג׳דרה") && food("מג׳דרה").id === (food("מגדרה") || {}).id);
ok("4. sushi finds סושי", !!food("sushi") && food("sushi").id === (food("סושי") || {}).id);
ok("4. מיץ ענבים is not swallowed by מיץ", (food("מיץ ענבים") || {}).before === "gefen" && (food("מיץ תפוזים") || {}).before !== "gefen");
for (const q of ["גרנולה", "כיף כף", "קפה", "קולה"]) {
  const r = S(q), fs_ = r.kind === "food" ? [r.food] : r.kind === "choice" ? r.list : [];
  ok(`5. ${q}: the after-blessing condition is on the card`, fs_.length > 0 && fs_.every(f => f.after_cond || (f.ops || []).some(o => o.after || o.text) || (!f.before && f.status === "review")), JSON.stringify(fs_.map(f => f.id)));
}
ok("5. a record with no source shows no ruling", D.foods.filter(f => !(f.src || []).length).every(f => f.status === "review"));
ok("6. latin spellings", ["shakshuka", "sabich", "bamba"].every(q => S(q).kind !== "none"));
ok("6. spellings from the brief", ["שורמה", "סביח בלאפה", "פלאפל לבד", "קבוק", "פתיבר", "קולה זירו", "גחנון", "דוריטוס"].every(q => S(q).kind !== "none"), ["שורמה", "סביח בלאפה", "פלאפל לבד", "קבוק", "פתיבר", "קולה זירו", "גחנון", "דוריטוס"].filter(q => S(q).kind === "none").join(", "));
ok("3. תות offers strawberry and mulberry", (choice("תות") || []).length >= 2);
ok("7. nothing found is reported as nothing", S("קרוקודיל מטוגן").kind === "none" && S("").kind === "empty");

const rv = D.foods.filter(f => f.status === "review");
console.log(`${D.foods.length} records | ${rv.length} wait for review (${rv.filter(f => !f.before && !(f.ops || []).length).length} with no ruling shown) | ${D.choices.length} choosers`);
console.log(`${pass + fail} checks, ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
