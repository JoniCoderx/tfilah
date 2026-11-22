// Cloudflare Pages Function: /leiluy-nishmat/<name>
// The same page as /shem/<name>, with the letters of "נשמה" added after the name.
import { serve } from "../shem/[name].js";

export const onRequestGet = ctx => serve(ctx, true);
