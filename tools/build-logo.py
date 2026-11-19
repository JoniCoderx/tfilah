"""Builds the brand SVGs in /brand from pure geometry plus glyph outlines.

The mark is three paper pieces that join into the letter tav. Every file is
plain vector shapes: no embedded bitmap and no font needed at display time.

Needs fonttools, a Bellefair (Hebrew) font file for the wordmark and a Latin UI font for the domain:
  python3 tools/build-logo.py <bellefair-hebrew.woff> <assistant-latin-600.woff>
"""
import sys, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "brand")
PAPER, INK, STAMP = "#EEF0F3", "#15181E", "#5F6B7C"

# 32-unit grid. roof, right leg, left leg with its foot
ROOF = "M3.8 4.8H26.2L28.2 6.8V9.4H3.8Z"
RIGHT = "M22 12.8H28.2V27.2H22Z"
LEFT = "M10.2 12.8H16.4V27.2H3.8V24.6L5.8 22.6H10.2Z"

GRAD = '<defs><linearGradient id="tfs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#A3ACB9"/><stop offset=".5" stop-color="#6F7A89"/><stop offset="1" stop-color="#98A2B0"/></linearGradient></defs>'
def mark(roof=INK, right=INK, left="url(#tfs)"):
    j = 'stroke-width="1.6" stroke-linejoin="round"'  # soft corners
    g = GRAD if "url(" in left else ""
    return f'{g}<path d="{ROOF}" fill="{roof}" stroke="{roof}" {j}/><path d="{RIGHT}" fill="{right}" stroke="{right}" {j}/><path d="{LEFT}" fill="{left}" stroke="{left}" {j}/>'

def text_path(font_file, text, size, x_right=None, x_left=None, baseline=0):
    """outline `text` (already in visual order, left to right) as one path"""
    f = TTFont(font_file); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f["head"].unitsPerEm
    k = size / upm; adv = [gs[cmap[ord(c)]].width * k for c in text]; total = sum(adv)
    x = x_left if x_left is not None else x_right - total
    d = []
    for c, a in zip(text, adv):
        pen = SVGPathPen(gs, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip("."))
        gs[cmap[ord(c)]].draw(TransformPen(pen, (k, 0, 0, -k, x, baseline)))
        d.append(pen.getCommands()); x += a
    return "".join(d), total

def write(name, w, h, inner, title):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{title}"><title>{title}</title>{inner}</svg>\n'
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(svg)

def main():
    frank, heebo = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    write("mark.svg", 32, 32, mark(), "תפילה")
    write("mark-mono.svg", 32, 32, f'<path d="{ROOF}{RIGHT}{LEFT}" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>', "תפילה")
    # favicon / app icon: paper mark on an ink tile
    tile = f'<rect width="32" height="32" rx="7" fill="{INK}"/><g transform="translate(2.9 2.9) scale(.82)">{mark(PAPER, PAPER, PAPER)}</g>'
    write("favicon.svg", 32, 32, tile, "תפילה")
    write("icon-maskable.svg", 32, 32, f'<rect width="32" height="32" fill="{INK}"/><g transform="translate(7 7) scale(.5625)">{mark(PAPER, PAPER, PAPER)}</g>', "תפילה")
    # horizontal lockup, right to left: mark, then the wordmark, domain under it
    word = "הליפת"  # visual order of תפילה
    wd, ww = text_path(frank, word, 33, x_left=0, baseline=0)
    dd, dw = text_path(heebo, "tfilah.com", 8.4, x_left=0, baseline=0)
    W = round(ww + 12 + 32 + 2, 1)
    lock = (f'<g transform="translate({W-32} 4)">{mark()}</g>'
            f'<path transform="translate({W-32-10-ww:.2f} 25)" d="{wd}" fill="{INK}"/>'
            f'<path transform="translate({W-32-10-dw:.2f} 37.4)" d="{dd}" fill="{INK}" fill-opacity=".62"/>')
    write("logo.svg", W, 40, lock, "תפילה · tfilah.com")
    head = (f'<g transform="translate({W-32} 0)">{mark()}</g><path transform="translate({W-32-10-ww:.2f} 25.6)" d="{wd}" fill="{INK}"/>')
    write("logo-header.svg", W, 32, head, "תפילה")
    print("wordmark width", round(ww, 1), "lockup", W)

if __name__ == "__main__":
    main()
