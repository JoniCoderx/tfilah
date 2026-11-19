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
PAPER, INK, STAMP = "#F6F0E4", "#351A29", "#A6781F"

# 32-unit grid. Three pieces of similar weight with a 4-unit gap, so they stay apart at 16px.
ROOF = "M2 2H24Q30 2 30 8V9H2Z"   # the top edge curls down like the corner of a page
RIGHT = "M21 13H30V30H21Z"
LEFT = "M8 13H17V30H2L8 23Z"      # the left leg ends in a pointed foot

def mark(roof=INK, right=INK, left=INK):
    return f'<path d="{ROOF}" fill="{roof}"/><path d="{RIGHT}" fill="{right}"/><path d="{LEFT}" fill="{left}"/>'

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
    write("mark-mono.svg", 32, 32, f'<path d="{ROOF}{RIGHT}{LEFT}" fill="currentColor"/>', "תפילה")
    # favicon / app icon: paper mark on an ink tile
    tile = f'<rect width="32" height="32" rx="7" fill="{INK}"/><g transform="translate(3.2 3.2) scale(.8)">{mark(PAPER, PAPER, PAPER)}</g>'
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
