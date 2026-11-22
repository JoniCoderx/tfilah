#!/usr/bin/env python3
"""Shrinks the share pictures in icons/ after tools/build-og.js has drawn them.

  node tools/build-og.js
  python3 tools/shrink-og.py

A gradient saved as a full-colour PNG weighs about 650 KB, and chat apps may refuse a preview picture that heavy.
Reduced to a 160-colour palette each picture is under 100 KB. After redrawing, raise OG_V in tools/prerender.py
(and the ?v= in tools/build.py and functions/y/[id].js) so the apps fetch the pictures again."""
import glob, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in sorted(glob.glob(os.path.join(ROOT, "icons", "og*.png"))):
    im = Image.open(f)
    if im.mode != "P":
        im.convert("RGB").quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(f, optimize=True)
    kb = os.path.getsize(f) / 1024
    assert kb < 300, f"{f}: {kb:.0f} KB is too heavy for a link preview"
    print(f"{os.path.basename(f)} {kb:.0f} KB")
