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
    const big = name === 'og' ? 116 : a.length > 14 ? 104 : a.length > 11 ? 124 : 150;
    await p.setContent(`<!doctype html><html lang="he" dir="rtl"><style>
@font-face{font-family:H;font-weight:900;src:url(${font(pick('heebo', 'hebrew', 900))})}
@font-face{font-family:A;font-weight:700;src:url(${font(pick('assistant', 'latin', 700))})}
*{margin:0;box-sizing:border-box}
/* a straight top-to-bottom gradient: every row is one colour, so the picture stays smooth and light without reducing its colours */
body{width:1200px;height:630px;font-family:H;color:#fff;overflow:hidden;background:linear-gradient(180deg,#2FA9EA 0%,#1583D2 48%,#0A4F92 100%)}
.f{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;position:relative;padding-bottom:34px}
.arc{position:absolute;left:50%;top:26px;width:1060px;transform:translateX(-50%)}
.b{display:flex;align-items:center;gap:18px;font-size:54px;font-weight:900;line-height:1;margin-bottom:26px}
.m{flex:none;width:84px;height:84px;border-radius:22px;background:#fff;display:grid;place-items:center;box-shadow:0 10px 26px rgba(4,30,60,.35)}.m svg{width:58px;height:58px}
h1{font-size:${big}px;line-height:1.06;font-weight:900;white-space:nowrap;letter-spacing:-.02em;text-shadow:0 6px 22px rgba(4,36,74,.35)}
h1 span{display:block;color:#FFE48A;font-size:${name === 'og' ? '1em' : '.56em'};margin-top:${name === 'og' ? '.02em' : '.2em'};letter-spacing:0}
.u{position:absolute;left:50%;bottom:40px;transform:translateX(-50%);font:700 34px A;direction:ltr;color:#0A5CA8;background:#fff;border-radius:99px;padding:9px 34px;box-shadow:0 8px 20px rgba(4,30,60,.3)}
</style><div class="f"><svg class="arc" viewBox="0 0 200 60"><path d="M4 58A120 120 0 0 1 196 58" fill="none" stroke="rgba(255,255,255,.45)" stroke-width=".6" stroke-dasharray=".1 2.6" stroke-linecap="round"/></svg>
<p class="b"><span class="m">${mark}</span>תפילה</p><h1>${a}<span>${c}</span></h1><p class="u">tfilah.com</p></div></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate(() => { const h = document.querySelector('h1'); let s = parseFloat(getComputedStyle(h).fontSize); while (h.getBoundingClientRect().width > 1040 && s > 60) h.style.fontSize = (s -= 2) + 'px'; });
    await p.screenshot({path: path.join(root, 'icons', name + '.png')});
    const ov = await p.evaluate(() => { const h = document.querySelector('h1').getBoundingClientRect(), u = document.querySelector('.u').getBoundingClientRect(); return h.bottom > u.top - 14 || h.left < 40 || h.right > 1160; });
    console.log(name, big, ov ? 'OVERLAP' : 'ok');
  }
  await b.close();
})();
