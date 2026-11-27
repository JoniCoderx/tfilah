// Builds the WhatsApp sticker pack from tools/stickers/stickers.html.
// Run: node tools/build-stickers.js   (then python3 tools/build-stickers.py packs the WebP files and the ZIP)
// Output: stickers/<id>.png (512x512, transparent) and stickers/tray.png (96x96).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..'), OUT = path.join(ROOT, 'stickers');
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 2048, height: 2048 } });
  await p.goto('file://' + path.join(__dirname, 'stickers', 'stickers.html'));
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(600);
  const ids = await p.$$eval('.cell', els => els.map(e => e.id));
  for (const id of ids) await (await p.$('#' + id)).screenshot({ path: path.join(OUT, id + '.png'), omitBackground: true });
  fs.writeFileSync(path.join(OUT, 'list.json'), JSON.stringify(ids));
  console.log(ids.length, 'stickers'); await b.close();
})();
