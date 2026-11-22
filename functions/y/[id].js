// Cloudflare Pages Function: /y/<id>
// The address people send for a shared Psalms reading. It answers with a small page whose title and
// preview say who the reading is for (so the link looks right in WhatsApp), and opens the reading in the app.
import { readPublic } from "../api/yachad.js";

const PRE = { neshama: "לעילוי נשמת", refuah: "לרפואה שלמה של", zivug: "לזיווג הגון עבור", hatzlacha: "להצלחה ולישועה של" };
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export async function onRequest({ params, env, request }) {
  const id = String(params.id || "");
  if (!/^[A-Za-z0-9_-]{1,40}$/.test(id)) return Response.redirect(new URL("/tehillim-yachad/", request.url).href, 302);
  const m = await readPublic(env, id);
  let who = "";
  if (m) who = m.kind === "general" || !PRE[m.kind] ? m.name : `${PRE[m.kind]} ${m.name} ${m.rel === "בת" ? "בת" : "בן"} ${m.parent}${m.kind === "neshama" ? " ז״ל" : ""}`;
  const title = m ? `תהילים יחד ${who}` : "תהילים יחד: קריאת תהילים משותפת";
  const desc = m ? `קוראים יחד את ספר התהילים ${who}. כל אחד פרק, ביחד ספר שלם.${m.done === 1 ? " כבר נקרא פרק אחד." : m.done ? ` כבר נקראו ${m.done} פרקים.` : ""} היכנסו וקבלו פרק.`
                 : "קריאת תהילים משותפת: כל אחד פרק, ביחד ספר שלם. היכנסו וקבלו פרק.";
  const app = "/#m-" + id, self = "https://tfilah.com/y/" + id;
  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)} | תפילה</title><meta name="description" content="${esc(desc)}"><meta name="robots" content="noindex">
<meta property="og:type" content="website"><meta property="og:site_name" content="תפילה"><meta property="og:locale" content="he_IL">
<meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${self}">
<meta property="og:image" content="https://tfilah.com/icons/og-yachad.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/brand/favicon.svg" type="image/svg+xml">
<style>body{margin:0;font-family:Arial,sans-serif;background:#fff;color:#0B2E4F;display:grid;place-items:center;min-height:100vh;text-align:center;padding:24px}a{display:inline-block;margin-top:16px;background:#0B79C0;color:#fff;text-decoration:none;font-weight:bold;padding:14px 28px;border-radius:999px}h1{font-size:1.5rem;margin:0 0 8px}p{margin:0;line-height:1.6}</style>
<script>location.replace(${JSON.stringify(app)})</script></head>
<body><main><h1>${esc(title)}</h1><p>${esc(desc)}</p><a href="${app}">לפתיחת הקריאה</a></main></body></html>`;
  return new Response(html, { status: m ? 200 : 404, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=60", "x-content-type-options": "nosniff" } });
}
