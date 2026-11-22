#!/usr/bin/env python3
"""Fetches the verses outside the Torah and Psalms that the site shows (the Kotel page, the Rachel page) and stores them untouched.

  python3 tools/get-kotel.py

Source: "Tanach with Nikkud" (public domain), through the Sefaria API. The Psalms on the page come from data/tehillim.json."""
import json, os, subprocess, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "Tanach with Nikkud"
out = {"source": VERSION, "license": "Public Domain", "via": "https://www.sefaria.org/api/v3/texts/", "verses": {}}
for ref in ("Isaiah.64.10", "Jeremiah.31.15", "Jeremiah.31.16", "Jeremiah.31.17"):
    url = "https://www.sefaria.org/api/v3/texts/" + ref + "?version=" + urllib.parse.quote("hebrew|" + VERSION)
    d = json.loads(subprocess.run(["curl", "-s", "-f", "--max-time", "40", url], capture_output=True, check=True).stdout)
    v = [x for x in d["versions"] if x["versionTitle"] == VERSION]
    assert len(v) == 1 and v[0]["license"] == "Public Domain", ref
    assert isinstance(v[0]["text"], str) and v[0]["text"].strip(), ref
    out["verses"][ref] = v[0]["text"].strip()
json.dump(out, open(os.path.join(ROOT, "data", "kotel.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(out["verses"])
