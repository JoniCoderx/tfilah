// Cloudflare Pages Function: /n/<id>
// The short address for "Psalm 119 by the letters of a name". It answers with the ordinary tool page, with a title
// and a preview that carry the name, and the verses open by themselves.
import { lookup } from "../api/shem.js";
import { rewrite } from "../shem/[name].js";

export async function onRequestGet({ params, env, request }) {
  const url = new URL(request.url), tool = new URL("/kelim/shem/", url).href;
  const rec = await lookup(env, String(params.id || ""));
  if (!rec) return Response.redirect(tool, 302);          // unknown id, or the lookup failed: the tool itself
  const page = await env.ASSETS.fetch(new Request(tool, { headers: { accept: "text/html" } }));
  if (!page.ok) return Response.redirect(tool, 302);
  return new Response(rewrite(await page.text(), rec.name, rec.neshama, "https://tfilah.com/n/" + params.id),
    { status: 200, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300", "x-content-type-options": "nosniff" } });
}
