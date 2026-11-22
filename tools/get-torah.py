#!/usr/bin/env python3
"""One-time download of the Torah text and the division into weekly portions. Run by hand; the result is committed.

Text: the edition "Tanach with Nikkud" (public domain, from tanach.us), read through Sefaria's API, chapter by chapter.
Nothing is edited: each verse is stored as received, minus HTML tags and the open/closed paragraph marks.
Division: portions and aliyot from the data file of @hebcal/leyning (the customary full reading).

  python3 tools/get-torah.py      ->  data/torah.json , tools/parashot.json
"""
import json, os, re, subprocess, sys, time, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS = [("Genesis", "בראשית", 50), ("Exodus", "שמות", 40), ("Leviticus", "ויקרא", 27), ("Numbers", "במדבר", 36), ("Deuteronomy", "דברים", 34)]
VERSION = "hebrew|Tanach with Nikkud"


def get(url):
    for k in range(4):
        r = subprocess.run(["curl", "-s", "-f", "--max-time", "40", url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf-8")
        time.sleep(2 + 2 * k)
    sys.exit("failed: " + url)


def clean(v):
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"\{[פס]\}", "", v).replace("&nbsp;", " ").replace("&thinsp;", "")
    return re.sub(r"\s+", " ", v).strip()


torah = {}
for en, he, n in BOOKS:
    chapters = []
    for c in range(1, n + 1):
        d = json.loads(get(f"https://www.sefaria.org/api/v3/texts/{en}.{c}?version=" + urllib.parse.quote(VERSION)))
        v = d["versions"][0]
        assert v["versionTitle"] == "Tanach with Nikkud" and v["license"] == "Public Domain", (en, c, v["versionTitle"], v["license"])
        verses = [clean(x) for x in v["text"]]
        assert verses and all(verses), (en, c)
        chapters.append(verses)
        time.sleep(0.15)
    torah[en] = chapters
    print(en, len(chapters), "chapters", sum(len(c) for c in chapters), "verses")
json.dump({"source": "Tanach with Nikkud, tanach.us (public domain), through Sefaria", "books": torah}, open(os.path.join(ROOT, "data", "torah.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---- portions and aliyot: a plain data file from the project's repository, read as data ----
src = json.loads(get("https://cdn.jsdelivr.net/gh/hebcal/hebcal-leyning@v9.2.3/src/aliyot.json"))
got = {"names": list(src), "out": list(src.values())}
EN = {1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy"}
NIK = re.compile(r"[\u0591-\u05C7]")
ORD = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שביעי"]
par = []
for var, p in zip(got["names"], got["out"]):
    if not isinstance(p.get("num"), int) or not (1 <= p["num"] <= 54):
        continue
    aliyot = []
    for i in range(1, 8):
        a = p["fullkriyah"][str(i)]
        (c1, v1), (c2, v2) = (map(int, a[0].split(":")), map(int, a[1].split(":")))
        aliyot.append([c1, v1, c2, v2])
    par.append({"num": p["num"], "key": var, "he": NIK.sub("", p["hebrew"].replace("\u05be", " ")), "book": EN[p["book"]], "aliyot": aliyot,
                "haft": p.get("haft"), "seph": p.get("seph")})
par.sort(key=lambda x: x["num"])
assert [x["num"] for x in par] == list(range(1, 55)), [x["num"] for x in par]
# a portion's aliyot must tile its text without gaps, and consecutive portions must tile the book
for a, b in zip(par, par[1:]):
    if a["book"] == b["book"]:
        c2, v2 = a["aliyot"][-1][2:]
        c1, v1 = b["aliyot"][0][:2]
        last = len(torah[a["book"]][c2 - 1])
        assert (c1, v1) == ((c2, v2 + 1) if v2 < last else (c2 + 1, 1)), (a["key"], b["key"])
json.dump(par, open(os.path.join(ROOT, "tools", "parashot.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("portions", len(par))
