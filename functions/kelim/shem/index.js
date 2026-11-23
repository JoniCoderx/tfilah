// Cloudflare Pages Function: /kelim/shem/  and  /kelim/shem/?n=<name in Hebrew>
// The tool page itself; with a name in the address, its title and preview carry the name.
import { withName } from "../../leiluy-nishmat/index.js";

export const onRequestGet = ctx => {
  const m = new URL(ctx.request.url).searchParams.get("m");
  return withName(ctx, m === "n", "/kelim/shem/");
};
