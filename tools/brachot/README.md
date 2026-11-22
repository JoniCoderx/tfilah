# מה מברכים על

A draft tool: type a food or drink, get the blessing before, the blessing after, and the condition that changes the answer.
The page is `/ma-mevarchim/`. It is a draft: it says `noindex`, carries no canonical, and is kept out of the sitemap (`tools/drafts.json`) until a rabbi has reviewed the data.

- `data.py`: the records. Every ruling was read on the page named as its source. `F` = one answer, `O` = several named opinions or cases, `Q` = no source yet, so no ruling is shown.
- `search.js`: the search (normalisation, question forms, choosers for ambiguous words). Shared by the page and the tests.
- `page.html`: the page body. `build.py` puts it inside the site's shell.
- `icons/`: Twemoji 15.1.0 illustrations (CC-BY 4.0). `custom.py`: drawings made for foods that have no emoji.
- `REVIEW.md`: generated. The table and the open questions that go to the rabbi.

Build and test:

    python3 tools/prerender.py
    python3 tools/brachot/build.py
    node tools/test-brachot.mjs

To publish after the review: remove the path from `tools/drafts.json`, drop the `noindex` line and add a canonical in `build.py`, and add the page to the sitemap.
