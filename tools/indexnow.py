#!/usr/bin/env python3
"""Tells IndexNow search engines (Bing, Yandex, Seznam, Naver and others; not Google) which public pages changed.

  python3 tools/indexnow.py                 # every URL in sitemap.xml
  python3 tools/indexnow.py 2026-11-26      # only URLs whose lastmod is on or after this date

Run it after a deploy has finished, from a machine with internet access. The key file /<key>.txt is published at the
site root; the key itself is public by design (https://www.indexnow.org/documentation). A 200 or 202 answer means the
list was received, not that anything was indexed."""
import json, re, sys, urllib.request, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = next(f[:-4] for f in os.listdir(ROOT) if re.fullmatch(r"[0-9a-f]{32}\.txt", f))
since = sys.argv[1] if len(sys.argv) > 1 else ""
sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
urls = [u for u, m in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", sm) if m >= since]
for i in range(0, len(urls), 10000):
    body = json.dumps({"host": "tfilah.com", "key": KEY, "keyLocation": f"https://tfilah.com/{KEY}.txt", "urlList": urls[i:i + 10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"content-type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"submitted {len(urls[i:i + 10000])} URLs: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"IndexNow answered HTTP {e.code}: {e.read()[:200]!r}")
        sys.exit(1)
