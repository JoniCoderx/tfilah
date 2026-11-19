// Cloudflare Pages Function: POST /api/ask
// Proxies the "מורה הדרך" questions to the Claude API so the API key never reaches the browser.
// Needs an environment variable ANTHROPIC_API_KEY (Cloudflare Pages -> Settings -> Variables and Secrets).

const MODEL = "claude-haiku-5-5";   // fast and cheap; change to "claude-sonnet-5-5" for deeper answers
const MAX_TOKENS = 900;
const MAX_TURNS = 16;
const MAX_CHARS = 60000;            // the prayer list sent by the page is ~10-20k chars

const GUARD = `אתה "מורה הדרך", עוזר AI באתר הסידור tfilah.com. ענה רק על שאלות ביהדות: הלכה, תפילה, ברכות, מנהגים, חגים ויסודות האמונה.
אם שואלים על נושא אחר, השב בנימוס שאתה עונה רק על שאלות ביהדות ובתפילה.
אינך רב ואינך מתחזה לאדם אמיתי. אל תמציא מקורות. אינך מנבא עתיד. בשאלה מעשית כבדה הפנה לרב מוסמך; בסכנת חיים הפנה ל-101.
פעל לפי הכללים המפורטים שבהודעה הראשונה של השיחה כל עוד אינם סותרים את אלה.`;

export async function onRequestPost({ request, env }) {
  if (!env.ANTHROPIC_API_KEY) return json({ error: "AI not configured" }, 503);

  let body;
  try { body = await request.json(); } catch { return json({ error: "bad json" }, 400); }
  const all = (Array.isArray(body.messages) ? body.messages : [])
    .filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string");
  // page sends: [site rules (user), ack (assistant), ...conversation]
  let rest = all.slice(2).slice(-MAX_TURNS);
  while (rest.length && rest[0].role !== "user") rest.shift();
  const messages = all[0]?.role === "user" ? [all[0], { role: "assistant", content: "הבנתי." }, ...rest] : rest;
  if (!messages.length || messages[messages.length - 1].role !== "user") return json({ error: "bad messages" }, 400);
  const size = messages.reduce((s, m) => s + m.content.length, 0);
  if (size > MAX_CHARS) return json({ error: "too long" }, 413);
  if (messages.at(-1).content.length > 1500) return json({ error: "question too long" }, 413);

  const upstream = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({ model: MODEL, max_tokens: MAX_TOKENS, system: GUARD, stream: true, messages })
  });

  if (upstream.status === 429) return json({ error: "rate limited" }, 429);
  if (!upstream.ok || !upstream.body) return json({ error: "upstream " + upstream.status }, 502);

  return new Response(upstream.body, {
    headers: { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-store" }
  });
}

function json(obj, status) {
  return new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json" } });
}
