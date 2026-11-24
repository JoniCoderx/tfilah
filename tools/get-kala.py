#!/usr/bin/env python3
"""Fetches the bride's prayer for her wedding day and stores the source page untouched.

  python3 tools/get-kala.py            # fetch from Wikisource
  python3 tools/get-kala.py FILE       # store a copy of the page source that was already downloaded

Source: Hebrew Wikisource, "תפילה לכלה ביום חופתה", from the book "חופת חתנים" (R. Raphael Meldola).
Licence: CC BY-SA 4.0. The wording is never edited here; tools/prerender.py only lays the page markup out."""
import datetime, json, os, subprocess, sys, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE = "תפילה לכלה ביום חופתה"
PAGE = "https://he.wikisource.org/wiki/" + urllib.parse.quote(TITLE.replace(" ", "_"))
RAW = "https://he.wikisource.org/w/index.php?title=" + urllib.parse.quote(TITLE.replace(" ", "_")) + "&action=raw"
if len(sys.argv) > 1:
    raw = open(sys.argv[1], encoding="utf-8").read()
else:
    raw = subprocess.run(["curl", "-s", "-f", "--max-time", "40", RAW], capture_output=True, check=True).stdout.decode("utf-8")
assert raw.startswith("{{טקסט מנוקד") and "מוֹשִׁיב יְחִידִים בַּיְתָה" in raw and "חופת חתנים" in raw, "the page is not what was expected"
out = {"title": TITLE, "book": "חופת חתנים (ר׳ רפאל מילדולה)", "source": "ויקיטקסט", "url": PAGE, "license": "CC BY-SA 4.0",
       "license_url": "https://creativecommons.org/licenses/by-sa/4.0/deed.he", "retrieved": datetime.date.today().isoformat(), "wikitext": raw}
json.dump(out, open(os.path.join(ROOT, "data", "kala.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(raw), "characters stored")
