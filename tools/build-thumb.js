// Builds icons/thumb.png: the square picture that every page names as its preferred image (schema.org primaryImageOfPage),
// which Google may show beside a search result. A quiet logo card: the app icon, the name, and the slogan.
// Run: node tools/build-thumb.js   (needs Playwright; uses the site's own fonts)
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const font = f => 'data:font/woff2;base64,' + fs.readFileSync(path.join(root, 'fonts', f)).toString('base64');
const MARK = '<svg viewBox="0 0 32 32"><path d="M23 26.5V13.5A7 7 0 0 0 9 13.5V22.5Q9 26.5 5 26.5" fill="none" stroke="#fff" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="16" cy="19.4" r="2.6" fill="#fff"/></svg>';
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 1200, height: 1200}});
  await p.setContent(`<!doctype html><html lang="he" dir="rtl"><style>
@font-face{font-family:H;font-weight:900;src:url(${font('heebo-hebrew-900.woff2')})}
@font-face{font-family:A;font-weight:600;src:url(${font('assistant-hebrew-600.woff2')})}
*{margin:0;box-sizing:border-box}
body{width:1200px;height:1200px;background:#F3F8FC;display:grid;place-items:center;font-family:H}
.c{display:flex;flex-direction:column;align-items:center;transform:translateY(-10px)}
.i{width:440px;height:440px;border-radius:104px;display:grid;place-items:center;background:linear-gradient(135deg,#6CC6F7 0%,#35A9EC 52%,#1493DB 100%);box-shadow:0 26px 60px -22px rgba(10,80,150,.45)}
.i svg{width:290px;height:290px;transform:translateY(-6px)}
h1{margin-top:58px;font-size:200px;line-height:1;font-weight:900;color:#0B2E4F;letter-spacing:-.01em}
p{margin-top:30px;font:600 64px A;color:#46677F}
</style><div class="c"><span class="i">${MARK}</span><h1>תפילה</h1><p>כל התפילות. במקום אחד.</p></div></html>`);
  await p.evaluate(() => document.fonts.ready);
  const out = path.join(root, 'icons', 'thumb.png');
  await p.screenshot({path: out});
  await b.close();
  console.log('icons/thumb.png', Math.round(fs.statSync(out).size / 1024), 'KB');
})();
