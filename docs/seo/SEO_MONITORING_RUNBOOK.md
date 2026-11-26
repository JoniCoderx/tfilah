# SEO monitoring and revert runbook

## Revert to the original SEO (the "button")
The SEO baseline is commit `2d4fe6bd8787d11f9d7975a4bf689b1473c8992c` (2026-11-27), deployed before the admin and analytics work.

**One click:** Cloudflare → Workers & Pages → tfilah → Deployments → the deployment of that commit → ⋯ → **Rollback to this deployment**. The whole site returns to that state within about a minute (the admin panel and analytics go with it). Roll forward the same way.

**From the repository:** `git revert <merge commits>` on main, or restore files from the baseline commit, then build and deploy as usual.

## Proving SEO did not change
`python3 tools/seo-snapshot.py check tools/seo-baseline.json` compares title, description, canonical, robots, H1 and structured-data types of all 1,405 built pages with the baseline and exits 1 on any difference. Run it after every build that is not meant to change SEO.

## Routine
- After a deploy that changes pages: `python3 tools/indexnow.py <date>` (Bing and other IndexNow engines; not Google).
- Weekly: /admin/ → SEO טכני → הרצת בדיקה; Search Console → Pages and Performance (7 days).
- Tests before every merge: `python3 tools/seo-audit.py`, `python3 tools/check-texts.py`, `node tools/test-brachot.mjs`, `node --no-warnings tools/test-yachad.mjs`, `node --no-warnings tools/test-analytics.mjs`.
