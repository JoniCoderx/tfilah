# Admin and analytics architecture

## Data flow
1. Every public page (static pages via `tools/prerender.py`, the app via `tools/build.py`, food pages via the shared shell) inlines `tools/beacon.js`.
2. The beacon sends at most these fields to `POST /api/ev` (`functions/api/ev.js`): `k` (pv, hb, print, share), `p` (public path; `/y/<id>` becomes `/y/`; app hashes become `/#section`), `c` (source category), `d` (m, t, d), `v` (random id made per page opening, never stored in the browser).
3. It sends nothing when Do Not Track or Global Privacy Control is on, for `navigator.webdriver`, or in a browser where an admin logged in (`localStorage tf-admin`).
4. The server rejects any other field, any query string, private paths (`/y/<id>`, `/admin/`, `/api/`), unknown categories and bodies over 400 bytes; it ignores crawler user agents and other origins. It stores no IP, user agent, full referrer or typed text.

## Tables (D1, created on first use)
| Table | Contents | Retention |
|---|---|---|
| `ev` | t, k, p, c, d | 30 days (pruned on about 2% of writes) |
| `live` | v, p, c, d, start, last seen | 1 hour |
| `day` | day, k, p, c, d, count | kept (aggregates only; capped at 3,000 paths per day) |
| `admin_fail` | keyed hash of IP+day, time | 1 day |
| `admin_audit` | time, action, ok | kept |

## Metric definitions
- **Pages open now**: page views whose last heartbeat (every 60 s while visible) is within 5 minutes. An estimate of open pages, not of people.
- **Views**: `pv` events. A reload is a new view. Crawlers, DNT/GPC browsers and admins are excluded, so totals are lower than server logs.
- **Source**: category from the referrer host only (`search:google`, `ai:chatgpt`, `social:facebook`, `direct`, `internal`, `referral`, `utm:<source>`). AI products often send no referrer; those visits appear as `direct`.

## Admin
- Page: `/admin/` (noindex, no-store, disallowed in robots.txt). Server: `functions/api/admin/[[path]].js`.
- Login: email + password from Cloudflare secrets; signed session cookie (HMAC-SHA256, HttpOnly, Secure, SameSite=Strict, path /api/admin, 12 h). 8 failures per address per 15 minutes lock that address. No registration, no default password.
- One role (super admin). Further roles are not built.
- Views: live (10 s polling, pause, stale indicator), trends 7/30/90 days with CSV, technical SEO audit of key pages plus 32 random sitemap pages (via the static assets binding only, so it cannot fetch other hosts), integrations and the SEO baseline.
