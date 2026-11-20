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
PAPER, INK, STAMP = "#FBF8F1", "#241B0E", "#8A6410"

# 32-unit grid. The gate: one rounded stroke that is both the letter tav and a doorway, and a point of light inside it.
GATE = "M23 26.5V13.5A7 7 0 0 0 9 13.5V22.5Q9 26.5 5 26.5"
G1, G2, G3 = "#C9A24A", "#8A6410", "#5E4306"
GRAD = f'<defs><linearGradient id="tfg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{G1}"/><stop offset=".52" stop-color="{G2}"/><stop offset="1" stop-color="{G3}"/></linearGradient></defs>'

def mark(roof=None, right=None, left=None, colour="url(#tfg)"):
    g = GRAD if "url(" in colour else ""
    return (f'{g}<path d="{GATE}" fill="none" stroke="{colour}" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="16" cy="19.4" r="2.6" fill="{colour}"/>')

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
    write("mark-mono.svg", 32, 32, mark(colour="currentColor"), "תפילה")
    # favicon / app icon: paper mark on an ink tile
    tile = f'{GRAD}<rect width="32" height="32" rx="9" fill="url(#tfg)"/>{mark(colour="#FFFFFF")}'
    write("favicon.svg", 32, 32, tile, "תפילה")
    write("icon-maskable.svg", 32, 32, f'{GRAD}<rect width="32" height="32" fill="url(#tfg)"/><g transform="translate(5.6 5.6) scale(.65)">{mark(colour="#FFFFFF")}</g>', "תפילה")
    # horizontal lockup, right to left: mark, then the wordmark, domain under it
    word = "הליפת"  # visual order of תפילה
    wd, ww = text_path(frank, word, 30, x_left=0, baseline=0)
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
