"""Packs the sticker pack built by tools/build-stickers.js: a WebP for each sticker (WhatsApp's format, under 100 KB),
the 96x96 tray icon, and one ZIP with everything. Run after the .js: python3 tools/build-stickers.py"""
import io, json, os, zipfile
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "stickers")
ids = json.load(open(os.path.join(D, "list.json")))
for n in ids:
    im = Image.open(os.path.join(D, n + ".png")).convert("RGBA")
    assert im.size == (512, 512), (n, im.size)
    for q in (82, 72, 60):
        buf = io.BytesIO(); im.save(buf, "WEBP", quality=q, method=6)
        if buf.tell() < 100_000: break
    assert buf.tell() < 100_000, n
    open(os.path.join(D, n + ".webp"), "wb").write(buf.getvalue())
Image.open(os.path.join(D, ids[0] + ".png")).convert("RGBA").resize((96, 96), Image.LANCZOS).save(os.path.join(D, "tray.png"), optimize=True)
note = ("סטיקרים לוואטסאפ מאת תפילה · tfilah.com\n"
        "מותר לשתף ולהשתמש בחופשיות, בלי לשנות ובלי להסיר את סימן האתר.\n"
        "סטיקרים חדשים והוראות הוספה: https://tfilah.com/stickers/\n")
with zipfile.ZipFile(os.path.join(D, "tfilah-stickers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("קרא אותי.txt", note)
    z.write(os.path.join(D, "tray.png"), "tray.png")
    for n in ids:
        z.write(os.path.join(D, n + ".webp"), f"webp/{n}.webp")
        z.write(os.path.join(D, n + ".png"), f"png/{n}.png")
print(len(ids), "stickers packed")
