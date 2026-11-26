# Required credentials and setup (no secret values here)

Set secrets in Cloudflare: Workers & Pages → tfilah → Settings → Variables and Secrets → Add → type **Secret**, for Production. Redeploy (or wait for the next deploy) after adding.

| Name | Needed for | Status on 2026-11-27 | Notes |
|---|---|---|---|
| `ADMIN_EMAIL` | /admin/ login | not set | the super admin address, e.g. `admin@tfilah.com` |
| `ADMIN_PASSWORD` | /admin/ login | not set | at least 12 characters; a new, strong password that was never sent in chat or email. Changing it signs every session out. |
| `ADMIN_SESSION_SECRET` | optional | not set | any long random string; adds a second key to the session signature |
| D1 binding `DB` | analytics, admin, shared reading | connected | already used by /api/yachad |
| `RESEND_API_KEY` | contact form | existing | unchanged |
| Google Search Console API | organic data inside /admin/ | **not connected** | needs a Google Cloud project, OAuth client and the owner's consent (read-only scope `webmasters.readonly`). Until then use search.google.com/search-console. |
| Bing Webmaster API key | Bing data inside /admin/ | **not connected** | bing.com/webmasters → Settings → API access. |
| IndexNow key | IndexNow submissions | published | public by design: `/<key>.txt` at the site root; submit with `python3 tools/indexnow.py`. |
| Mail provider for team@ and business@ | public addresses, Tfilah Mail | **owner action needed** | See "Mail" below. |
| AI search APIs (benchmarks) | AI visibility benchmark | **not approved** | paid API use needs the owner's approval and a budget cap. |

## Mail (team@tfilah.com, business@tfilah.com)

The domain's MX records point to Cloudflare Email Routing. Receiving at the two new addresses works only after the owner adds a routing rule for each:
Cloudflare → tfilah.com → Email → Email Routing → Routing rules → Create address: `team` → forward to the owner's inbox; same for `business`.

Replying *from* those addresses needs an outbound provider. The site already sends through Resend for support@tfilah.com; Gmail "Send mail as" can use Resend's SMTP (smtp.resend.com, user `resend`, password = an API key) once the domain is verified in Resend.

A built-in Gmail-style mailbox inside /admin/ (section 23A of the directive) is **not built**: Cloudflare Pages Functions cannot receive email, so it needs an inbound provider (an Email Worker or a provider with inbound webhooks) and stored mail with its own access controls. That is a separate project to approve.
