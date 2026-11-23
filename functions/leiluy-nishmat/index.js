// Cloudflare Pages Function: /leiluy-nishmat/  and  /leiluy-nishmat/?n=<name in Hebrew>
// Without a name this is the ordinary landing page. With a name, the same page is answered with a title and a
// preview that carry the name, so a shared link shows who the reading is for.
import { cleanName, rewrite } from "../shem/[name].js";

export async function withName({ env, request }, neshama, base) {
  const url = new URL(request.url), name = cleanName(url.searchParams.get("n") || "");
  const page = await env.ASSETS.fetch(new Request(new URL(base, url).href, { headers: { accept: "text/html" } }));
  if (!name || !page.ok) return page;
  const self = "https://tfilah.com" + base + "?n=" + encodeURIComponent(name).replace(/%20/g, "+");
  return new Response(rewrite(await page.text(), name, neshama, self),
    { status: 200, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300", "x-content-type-options": "nosniff" } });
}

export const onRequestGet = ctx => withName(ctx, true, "/leiluy-nishmat/");
