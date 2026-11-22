// Builds the 1200x630 share images in icons/. Run: node tools/build-og.js
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const font = f => 'data:font/woff2;base64,' + fs.readFileSync(path.join(root, 'fonts', f)).toString('base64');
const mark = fs.readFileSync(path.join(root, 'brand', 'mark.svg'), 'utf8');
const CARDS = {
  'og': ['סידור תפילה', 'ותהילים'],
  'og-yachad': ['כל אחד פרק.', 'ביחד ספר שלם.'],
  'og-siddur': ['סידור תפילה', 'בשלושה נוסחים'],
  'og-tehillim': ['ספר תהילים', 'מנוקד, לפי פרקים'],
  'og-shabbat': ['זמני שבת', 'כניסה ויציאה לפי עיר'],
  'og-shem': ['תהילים לפי שם', 'פסוקים מפרק קי״ט'],
  'og-chanukah': ['הדלקת נרות חנוכה', 'ברכות לפי הנוסח'],
  'og-kelim': ['כלי תפילה', 'ולוח עברי'],
};
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 1200, height: 630}});
  const hf = fs.readdirSync(path.join(root, 'fonts'));
  const pick = (fam, sub, w) => hf.find(f => f.startsWith(fam) && f.includes(sub) && f.includes(String(w)));
  for (const [name, [a, c]] of Object.entries(CARDS)) {
    const big = Math.max(a.length, c.length) > 14 ? 96 : Math.max(a.length, c.length) > 11 ? 112 : 132;
    await p.setContent(`<!doctype html><html lang="he" dir="rtl"><style>
@font-face{font-family:H;font-weight:900;src:url(${font(pick('heebo', 'hebrew', 900))})}
@font-face{font-family:A;font-weight:600;src:url(${font(pick('assistant', 'latin', 600))})}
*{margin:0;box-sizing:border-box}body{width:1200px;height:630px;background:#fff;padding:26px;font-family:H}
.f{height:100%;display:flex;align-items:center;justify-content:space-between;padding:0 64px 0 80px;position:relative}
.t{max-width:800px}.b{font-size:54px;font-weight:900;color:#0B2E4F;margin-bottom:18px}
h1{display:inline-block;font-size:${big}px;line-height:1.12;font-weight:900;color:#0B2E4F;white-space:nowrap}h1 span{display:block;color:#0A6FB3}
.u{position:absolute;left:64px;bottom:40px;font:600 30px A;color:#3B5670;direction:ltr}
svg{width:250px;height:250px;flex:none}
</style><div class="f"><div class="t"><p class="b">תפילה</p><h1>${a}<span>${c}</span></h1></div>${mark}<p class="u">tfilah.com</p></div></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate(() => { const h = document.querySelector('h1'); let s = parseFloat(getComputedStyle(h).fontSize); while (h.getBoundingClientRect().width > 690 && s > 60) h.style.fontSize = (s -= 2) + 'px'; });
    await p.screenshot({path: path.join(root, 'icons', name + '.png')});
    const ov = await p.evaluate(() => { const h = document.querySelector('h1').getBoundingClientRect(), s = document.querySelector('svg').getBoundingClientRect(); return h.left < s.right + 20; });
    console.log(name, big, ov ? 'OVERLAP' : 'ok');
  }
  await b.close();
})();
