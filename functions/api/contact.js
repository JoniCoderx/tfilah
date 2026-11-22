// Cloudflare Pages Function: POST /api/contact
// The contact form and the "report an error in the text" form. It sends two emails through Resend:
//   1. the message itself, to the site's inbox (support@tfilah.com), with the visitor's address as Reply-To;
//   2. a fixed, designed confirmation to the visitor, if they left an address.
// Needs the secret RESEND_API_KEY (Cloudflare Pages -> Settings -> Variables and Secrets) and a domain
// verified in Resend. Without the secret the function answers 503 and the page falls back to a mail link.
// Tests: node tools/test-contact.mjs
//
// What keeps this from being abused:
//   * Origin / Referer must be this site, the same rule as /api/ask. It stops other websites, not scripts.
//   * A hidden field that people never fill; a request that fills it is accepted and dropped.
//   * The confirmation carries NOTHING the visitor typed: no message, no name, no page. So the form
//     cannot be used to deliver someone's text to a third party's inbox.
//   * A small per-address limiter inside one isolate (a damper, not a guarantee). The real limit is a
//     WAF rate limiting rule on "URI Path equals /api/contact" in the Cloudflare dashboard.

const INBOX = "support@tfilah.com";
const FROM = "תפילה <support@tfilah.com>";
const SITE_ORIGINS = ["https://tfilah.com", "https://www.tfilah.com"];
const MAX_BODY_BYTES = 16 * 1024;
const MAX_MESSAGE = 3000;
const RATE_WINDOW_MS = 10 * 60000;
const RATE_PER_IP = 4;
const RATE_GLOBAL = 60;
const UPSTREAM_TIMEOUT_MS = 12000;
const hits = new Map();
let globalHits = [];

export async function onRequest(context) {
  try {
    return await handle(context);
  } catch (e) {
    console.error("contact: unexpected error", e && e.name);
    return json({ error: "internal error" }, 500);
  }
}

async function handle({ request, env }) {
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405, { allow: "POST" });
  if (!sameSite(request, env)) return json({ error: "forbidden" }, 403);
  if (!env || !env.RESEND_API_KEY) return json({ error: "not configured" }, 503);
  const type = (request.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
  if (type !== "application/json") return json({ error: "content-type must be application/json" }, 415);
  if (Number(request.headers.get("content-length")) > MAX_BODY_BYTES) return json({ error: "too long" }, 413);
  const raw = await request.text();
  if (raw.length > MAX_BODY_BYTES) return json({ error: "too long" }, 413);
  let b;
  try { b = JSON.parse(raw); } catch { return json({ error: "bad json" }, 400); }
  if (!b || typeof b !== "object") return json({ error: "bad request" }, 400);

  const str = (v, max) => (typeof v === "string" ? v.replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "").trim().slice(0, max) : "");
  const line = (v, max) => str(v, max).replace(/[\r\n]+/g, " ");
  if (str(b.website, 200)) return json({ ok: true });            // the hidden field: pretend it worked
  const kind = b.kind === "error" ? "error" : "contact";
  const message = str(b.message, MAX_MESSAGE + 1);
  if (message.length < 5) return json({ error: "message too short" }, 400);
  if (message.length > MAX_MESSAGE) return json({ error: "too long" }, 413);
  const email = line(b.email, 254).toLowerCase();
  if (email && !/^[^\s@<>"',;:]+@[^\s@<>"',;:]+\.[a-z]{2,}$/.test(email)) return json({ error: "bad email" }, 400);
  const name = line(b.name, 80), title = line(b.title, 120), nusach = line(b.nusach, 40);
  let page = line(b.page, 300);
  if (page && !/^https:\/\/(www\.)?tfilah\.com\//.test(page)) page = "";

  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const wait = rateLimited(ip, Date.now());
  if (wait) return json({ error: "rate limited" }, 429, { "retry-after": String(wait) });

  const subject = (kind === "error" ? "דיווח על טעות בנוסח" : "פנייה מהאתר") + (title ? ": " + title : "");
  const rows = [["סוג", kind === "error" ? "דיווח על טעות בנוסח" : "פנייה"], ["שם", name], ["מייל לתשובה", email], ["העמוד", page], ["התפילה", title], ["הנוסח", nusach]].filter(r => r[1]);
  const text = rows.map(r => r[0] + ": " + r[1]).join("\n") + "\n\n" + message;
  const html = `<div dir="rtl" style="font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#0B2E4F">`
    + `<table style="border-collapse:collapse">${rows.map(r => `<tr><td style="padding:2px 0 2px 14px;color:#5b7186">${esc(r[0])}</td><td>${esc(r[1])}</td></tr>`).join("")}</table>`
    + `<p style="white-space:pre-wrap;border-top:1px solid #d7e6f2;padding-top:12px;margin-top:12px">${esc(message)}</p></div>`;

  const first = await send(env, { from: FROM, to: [INBOX], subject, text, html, ...(email ? { reply_to: email } : {}) });
  if (!first.ok) return json({ error: first.error }, first.status);
  let confirmed = false;
  if (email) {
    const c = confirmation(kind);
    const second = await send(env, { from: FROM, to: [email], reply_to: INBOX, subject: c.subject, text: c.text, html: c.html });
    confirmed = second.ok;                                       // the message itself already arrived
  }
  return json({ ok: true, confirmed });
}

// The confirmation is fixed text. Nothing from the request goes into it.
export function confirmation(kind) {
  const err = kind === "error";
  const subject = err ? "קיבלנו את הדיווח שלך | תפילה" : "קיבלנו את הפנייה שלך | תפילה";
  const head = err ? "תודה על הדיווח" : "תודה שכתבת לנו";
  const body = err
    ? "קיבלנו את הדיווח על טעות בנוסח. כל דיווח נבדק מול המהדורה שהטקסט נלקח ממנה, ואם אכן נפלה טעות היא מתוקנת באתר."
    : "קיבלנו את הפנייה שלך ונחזור אליך בהקדם האפשרי.";
  const more = "אם רצית להוסיף משהו, אפשר פשוט להשיב למייל הזה.";
  const text = `${head}\n\n${body}\n${more}\n\nתפילה · tfilah.com\nסידור תפילה, תהילים וזמני היום`;
  const html = `<!doctype html><html lang="he" dir="rtl"><body style="margin:0;background:#F3F9FE;padding:24px 12px;font-family:Arial,'Segoe UI',sans-serif">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:20px;border:1px solid #D7E6F2">`
    + `<tr><td dir="rtl" style="padding:28px 28px 8px;text-align:right"><img src="https://tfilah.com/icons/icon-192.png" width="44" height="44" alt="" style="border-radius:12px;vertical-align:middle">`
    + `<span style="font-size:24px;font-weight:bold;color:#0B2E4F;vertical-align:middle;margin-right:10px">תפילה</span></td></tr>`
    + `<tr><td dir="rtl" style="padding:8px 28px 4px;text-align:right"><h1 style="margin:0;font-size:22px;line-height:1.3;color:#0B2E4F">${head}</h1></td></tr>`
    + `<tr><td dir="rtl" style="padding:8px 28px;text-align:right;font-size:16px;line-height:1.7;color:#24435F"><p style="margin:0 0 10px">${body}</p><p style="margin:0">${more}</p></td></tr>`
    + `<tr><td dir="rtl" style="padding:18px 28px 26px;text-align:right"><a href="https://tfilah.com/" style="display:inline-block;background:#0B79C0;color:#ffffff;text-decoration:none;font-weight:bold;font-size:16px;padding:12px 26px;border-radius:999px">חזרה לסידור</a></td></tr>`
    + `<tr><td dir="rtl" style="padding:16px 28px 22px;text-align:right;border-top:1px solid #E4EEF6;font-size:13px;line-height:1.6;color:#5B7186">תפילה · tfilah.com<br>סידור תפילה, תהילים וזמני היום</td></tr>`
    + `</table></td></tr></table></body></html>`;
  return { subject, text, html };
}

async function send(env, mail) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer " + env.RESEND_API_KEY },
      body: JSON.stringify(mail),
      signal: ctl.signal
    });
    try { await r.body?.cancel(); } catch {}
    if (r.ok) return { ok: true };
    console.error("contact: upstream status", r.status);      // status only, never the body
    return { ok: false, status: r.status === 429 ? 429 : 502, error: r.status === 429 ? "rate limited" : "upstream error" };
  } catch (e) {
    console.error("contact: upstream fetch failed", ctl.signal.aborted ? "timeout" : (e && e.name));
    return { ok: false, status: ctl.signal.aborted ? 504 : 502, error: ctl.signal.aborted ? "upstream timeout" : "upstream unreachable" };
  } finally {
    clearTimeout(timer);
  }
}

function sameSite(request, env) {
  const allowed = new Set(SITE_ORIGINS);
  try { allowed.add(new URL(request.url).origin); } catch {}
  for (const o of String((env && env.ALLOWED_ORIGINS) || "").split(",")) if (o.trim()) allowed.add(o.trim().replace(/\/+$/, ""));
  const origin = request.headers.get("origin");
  if (origin) return allowed.has(origin);
  const ref = request.headers.get("referer");
  if (!ref) return false;
  try { return allowed.has(new URL(ref).origin); } catch { return false; }
}

function rateLimited(ip, now) {
  const fresh = t => now - t < RATE_WINDOW_MS;
  globalHits = globalHits.filter(fresh);
  const mine = (hits.get(ip) || []).filter(fresh);
  const over = mine.length >= RATE_PER_IP ? mine : globalHits.length >= RATE_GLOBAL ? globalHits : null;
  if (over) { hits.set(ip, mine); return Math.max(1, Math.ceil((over[0] + RATE_WINDOW_MS - now) / 1000)); }
  mine.push(now); globalHits.push(now); hits.set(ip, mine);
  if (hits.size > 5000) hits.clear();
  return 0;
}

export function _resetRateLimit() { hits.clear(); globalHits = []; }

const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function json(obj, status, extra) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "cache-control": "no-store", "x-content-type-options": "nosniff", vary: "Origin", "content-type": "application/json; charset=utf-8", ...(extra || {}) }
  });
}
