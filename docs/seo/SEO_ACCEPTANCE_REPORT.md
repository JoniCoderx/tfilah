# Acceptance report: master SEO/GEO/admin directive, first slice

Date: 2026-11-27 · Branch merged to main as PR #132 (commit 8d2d451) · Live: https://tfilah.com, service worker tfilah-v164.
SEO baseline before this work: commit 2d4fe6b. Rollback: see SEO_MONITORING_RUNBOOK.md.

## Status

| Requirement | Status | Evidence | Next action |
|---|---|---|---|
| Public SEO unchanged by this work | PASS | `tools/seo-snapshot.py check`: 1,405 pages, 0 changed/added/removed | run after every build |
| Revert to original SEO | PASS (procedure) | Cloudflare deployment rollback to 2d4fe6b; steps in runbook and in /admin/ | — |
| Crawler access (Googlebot, Bingbot, OAI-SearchBot, ChatGPT-User, GPTBot, ClaudeBot, Claude-SearchBot, PerplexityBot, DuckDuckBot) | PASS | live fetch with each user agent: HTTP 200 | training opt-out policy unchanged (none set) |
| robots.txt | PASS | live: Allow /, Disallow /admin/, sitemap listed | — |
| Sitemap, titles, descriptions, canonicals, JSON-LD | PASS | `tools/seo-audit.py`: OK; 2,810 JSON-LD blocks parse | — |
| llms.txt | PASS | live 200, text/plain UTF-8 (PR #117) | experimental by nature |
| IndexNow | PASS | 2026-11-26 22:00 UTC: 1,326 sitemap URLs submitted, HTTP 200 (received, not proof of indexing) | after page changes: `python3 tools/indexnow.py <date>` |
| First-party analytics ingest | PASS (tests) / NOT RUN (production write) | 38/38 in tools/test-analytics.mjs; live endpoint rejects extra fields (400) and ignores crawlers (204) | a production write was not forced, to keep synthetic traffic out of the numbers; confirm in /admin/ after login |
| Privacy: no IP/UA/referrer/typed text stored; DNT/GPC respected; private paths refused | PASS (tests, code review) | tests "rejected: …", privacy page updated | — |
| Admin login | PASS (configured) | owner set ADMIN_EMAIL and ADMIN_PASSWORD secrets; live endpoint now answers 401 without a session (was 503) | owner confirms a login |
| Admin access control | PASS (tests) | 401 without session, forged/expired sessions refused, password change revokes, lock after 8 failures | — |
| Admin noindex / no-store | PASS | live header X-Robots-Tag: noindex, nofollow | — |
| Live dashboard, trends, CSV, SEO check, integrations panel | PASS (mocked UI render) / NOT RUN (live data) | rendered at 1240 and 390 px | verify after login |
| Footer and contact links team@ / business@ | PASS (links) / BLOCKED (delivery) | live footer contains both addresses | owner adds Email Routing rules; see REQUIRED_CREDENTIALS.md |
| Search Console / Bing data in admin | NOT BUILT (needs credentials) | integrations panel shows "not connected" | owner approves OAuth / API key |
| Tfilah Mail inbox (23A) | NOT BUILT | needs inbound mail provider | owner decision |
| Keyword center, CMS, roles beyond super admin, AI benchmark runs, scheduler, alerts, reports | NOT BUILT | — | next slices; AI benchmarks need a paid-API budget approval |
| Hreflang / translations | NOT APPLICABLE yet | no translated pages exist | — |
