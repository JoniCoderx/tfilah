// Builds the 1200x630 share images in icons/. Run: node tools/build-og.js
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const font = f => 'data:font/woff2;base64,' + fs.readFileSync(path.join(root, 'fonts', f)).toString('base64');
const mark = fs.readFileSync(path.join(root, 'brand', 'mark.svg'), 'utf8');
const CARDS = {
  'og': ['כל התפילות.', 'במקום אחד.'],
  'og-yachad': ['כל אחד פרק.', 'ביחד ספר שלם.'],
  'og-siddur': ['סידור תפילה', 'בשלושה נוסחים'],
  'og-tehillim': ['ספר תהילים', 'מנוקד, לפי פרקים'],
  'og-shabbat': ['זמני שבת', 'כניסה ויציאה לפי עיר'],
  'og-zmanim': ['זמני היום', 'מהנץ ועד צאת הכוכבים'],
  'og-shem': ['תהילים לפי שם', 'פסוקים מפרק קי״ט'],
  'og-chanukah': ['הדלקת נרות חנוכה', 'ברכות לפי הנוסח'],
  'og-kelim': ['כלי תפילה', 'ולוח עברי'],
  'og-perek': ['פרק שירה', 'שירת הבריאה, בניקוד מלא'],
  'og-brachot': ['מה מברכים על?', 'ברכה לכל מאכל, בשנייה'],
  'og-parasha': ['פרשת השבוע', 'בניקוד, לפי עליות'],
  'og-kotel': ['תפילה בכותל', 'פסוקים ומזמורים'],
  'og-kaddish': ['קדיש', 'הנוסח המלא בניקוד'],
  'og-nishmat': ['נשמת כל חי', 'בניקוד מלא'],
  'og-toda': ['מזמור לתודה', 'תהילים פרק ק'],
  'og-derech': ['תפילת הדרך', 'לפני שיוצאים'],
  'og-mazon': ['ברכת המזון', 'בשלושה נוסחים'],
  'og-shema': ['שמע על המיטה', 'קריאת שמע לפני השינה'],
  'og-modeh': ['מודה אני', 'פותחים את הבוקר'],
  'og-asher': ['אשר יצר', 'הברכה בניקוד מלא'],
};
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 1200, height: 630}});
  const hf = fs.readdirSync(path.join(root, 'fonts'));
  const pick = (fam, sub, w) => hf.find(f => f.startsWith(fam) && f.includes(sub) && f.includes(String(w)));
  for (const [name, [a, c]] of Object.entries(CARDS)) {
    const big = a.length > 14 ? 104 : a.length > 11 ? 124 : 150;
    await p.setContent(`<!doctype html><html lang="he" dir="rtl"><style>
@font-face{font-family:H;font-weight:900;src:url(${font(pick('heebo', 'hebrew', 900))})}
@font-face{font-family:A;font-weight:700;src:url(${font(pick('assistant', 'latin', 700))})}
*{margin:0;box-sizing:border-box}body{width:1200px;height:630px;font-family:H;color:#fff;overflow:hidden;
  background:radial-gradient(380px 380px at 18% 22%,rgba(255,255,255,.2),rgba(255,255,255,0)),radial-gradient(120% 120% at 78% 0%,#46B6F3 0%,#1489D4 38%,#0B62AA 70%,#0A3C6E 100%)}
.f{height:100%;display:flex;align-items:center;justify-content:space-between;padding:0 84px 0 76px;position:relative}
.t{max-width:800px}.b{font-size:50px;font-weight:900;margin-bottom:14px;opacity:.95}
h1{display:inline-block;font-size:${big}px;line-height:1.1;font-weight:900;white-space:nowrap;text-shadow:0 6px 26px rgba(4,36,74,.38)}
h1 span{display:block;color:#FFE9A8;font-size:.62em;margin-top:.16em}
.u{position:absolute;left:76px;bottom:44px;font:700 34px A;direction:ltr;background:rgba(255,255,255,.16);border:2px solid rgba(255,255,255,.6);border-radius:99px;padding:8px 26px}
.m{flex:none;width:270px;height:270px;border-radius:64px;background:#fff;display:grid;place-items:center;box-shadow:0 22px 60px rgba(4,30,60,.4)}
.m svg{width:190px;height:190px}
</style><div class="f"><div class="t"><p class="b">תפילה</p><h1>${a}<span>${c}</span></h1></div><div class="m">${mark}</div><p class="u">tfilah.com</p></div></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate(() => { const h = document.querySelector('h1'); let s = parseFloat(getComputedStyle(h).fontSize); while (h.getBoundingClientRect().width > 700 && s > 60) h.style.fontSize = (s -= 2) + 'px'; });
    await p.screenshot({path: path.join(root, 'icons', name + '.png')});
    const ov = await p.evaluate(() => { const h = document.querySelector('h1').getBoundingClientRect(), s = document.querySelector('.m').getBoundingClientRect(); return h.left < s.right + 20; });
    console.log(name, big, ov ? 'OVERLAP' : 'ok');
  }
  await b.close();
})();
