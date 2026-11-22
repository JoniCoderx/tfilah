// Cloudflare Pages Function: /shem/<name> and (through functions/leiluy-nishmat/[name].js) /leiluy-nishmat/<name>
// The address people send for "Psalm 119 by the letters of a name". The name is part of the address itself, written
// with hyphens between the words (tfilah.com/shem/אברהם-בן-שרה), so the link reads well in a message. The answer is the
// ordinary tool page with a title and a preview that carry the name, and the verses open by themselves.
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// One Latin letter for each Hebrew letter. k, m, n, p, c at the end of a word are the final forms (ך ם ן ף ץ),
// unless a 0 follows them. Addresses written in Hebrew letters (the first form of these links) keep working.
const HEB = "אבגדהוזחטיכלמנסעפצקרשת", LAT = "abgdhvzxjyklmnsepcqrwt", FINAL = { k: "ך", m: "ם", n: "ן", p: "ף", c: "ץ" };
export function fromLatin(slug) {
  return slug.split("-").map(w => {
    let o = "";
    for (let i = 0; i < w.length; i++) {
      const l = w[i], at = LAT.indexOf(l);
      if (at < 0) continue;
      const plain = w[i + 1] === "0", last = i === w.length - 1;
      o += FINAL[l] && last && !plain ? FINAL[l] : HEB[at];
      if (plain) i++;
    }
    return o;
  }).join(" ");
}

export function cleanName(raw) {
  let s = String(raw || "");
  try { s = decodeURIComponent(s); } catch (e) { /* keep as it came */ }
  if (/^[a-z0-9-]+$/.test(s)) s = fromLatin(s);
  return s.replace(/[-_+]+/g, " ").replace(/[^א-ת ]/g, "").replace(/\s+/g, " ").trim().slice(0, 40);
}

export function rewrite(html, name, neshama, self) {
  const title = neshama ? `תהילים לעילוי נשמת ${name}` : `תהילים לפי שם: ${name}`;
  const desc = `פסוקי תהילים פרק קי״ט לפי אותיות השם ${name}${neshama ? ", עם אותיות ”נשמה”" : ""}. הפסוקים מוכנים לקריאה, בניקוד מלא.`;
  const set = (re, v) => { html = html.replace(re, (m, a, b) => a + esc(v) + b); };
  set(/(<title>)[^<]*(<\/title>)/, title + " | תפילה");
  set(/(<meta name="description" content=")[^"]*(")/, desc);
  set(/(<meta property="og:title" content=")[^"]*(")/, title);
  set(/(<meta property="og:description" content=")[^"]*(")/, desc);
  set(/(<meta property="og:url" content=")[^"]*(")/, self);
  set(/(<meta name="twitter:title" content=")[^"]*(")/, title);
  set(/(<meta name="twitter:description" content=")[^"]*(")/, desc);
  // a page per name is not for search engines: the tool page itself stays the one that is indexed
  html = html.replace(/<meta name="robots" content="[^"]*">/, "");
  const boot = `<meta name="robots" content="noindex"><script>window.__shem=${JSON.stringify({ name, neshama })}</script>`;
  return html.replace("</head>", boot + "</head>");
}

export async function serve({ params, env, request }, neshama) {
  const name = cleanName(params.name), url = new URL(request.url);
  if (!name) return Response.redirect(new URL("/kelim/shem/", url).href, 302);
  const page = await env.ASSETS.fetch(new Request(new URL("/kelim/shem/", url).href, { headers: { accept: "text/html" } }));
  if (!page.ok) return Response.redirect(new URL("/kelim/shem/", url).href, 302);
  const self = "https://tfilah.com/" + (neshama ? "leiluy-nishmat" : "shem") + "/" + url.pathname.split("/").filter(Boolean).pop();
  return new Response(rewrite(await page.text(), name, neshama, self),
    { status: 200, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300", "x-content-type-options": "nosniff" } });
}

export const onRequestGet = ctx => serve(ctx, false);
