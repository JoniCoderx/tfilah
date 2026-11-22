# מה מברכים על

A draft tool: type a food or drink, get the blessing before, the blessing after, and the condition that changes the answer.
The page is `/ma-mevarchim/`. It is published: it has a canonical, adds itself to the sitemap, and is linked from the footer and the home page.
The data was assembled from written sources and has not been approved as a whole by a rabbi; the page says so.

- `data.py`: the records. Every ruling was read on the page named as its source. `F` = one answer, `O` = several named opinions or cases, `Q` = no source yet, so no ruling is shown.
- `search.js`: the search (normalisation, question forms, choosers for ambiguous words). Shared by the page and the tests.
- `page.html`: the page body. `build.py` puts it inside the site's shell.
- `icons/`: Twemoji 15.1.0 illustrations (CC-BY 4.0). `custom.py`: drawings made for foods that have no emoji.
- `REVIEW.md`: generated. The table and the open questions that go to the rabbi.

Build and test:

    python3 tools/prerender.py
    python3 tools/brachot/build.py
    node tools/test-brachot.mjs

To take the page down again: put its path in `tools/drafts.json`, restore the `noindex` line and drop the canonical in `build.py`.
