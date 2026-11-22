// Tests for functions/api/contact.js with a mocked fetch (no network, no key needed).
//   node tools/test-contact.mjs
import { onRequest, confirmation, _resetRateLimit } from "../functions/api/contact.js";

const SITE = "https://tfilah.com";
let sent = [], upstream = () => new Response("{}", { status: 200 });
globalThis.fetch = async (url, init) => { sent.push({ url: String(url), init, body: JSON.parse(init.body) }); return upstream(sent.length); };
let pass = 0, fail = 0;
const ok = (name, cond, extra) => { cond ? pass++ : fail++; if (!cond) console.log("FAIL ", name, extra === undefined ? "" : JSON.stringify(extra)); };
const req = (body, { method = "POST", headers = {}, raw } = {}) => new Request(SITE + "/api/contact", {
  method, headers: { "content-type": "application/json", origin: SITE, "cf-connecting-ip": "1.2.3.4", ...headers }, body: method === "POST" ? (raw !== undefined ? raw : JSON.stringify(body)) : undefined });
const call = async (body, opt = {}, env = { RESEND_API_KEY: "re_test" }) => { sent = []; const r = await onRequest({ request: req(body, opt), env }); let j = null; try { j = await r.json(); } catch {} return { r, j }; };
const good = { kind: "error", message: "במילה השלישית חסרה אות", email: "Reader@Example.com", name: "ישראל", page: "https://tfilah.com/tefila/mizrach-119/", title: "תפלת הדרך", nusach: "עדות המזרח" };

_resetRateLimit();
let x = await call(good);
ok("valid report is accepted", x.r.status === 200 && x.j.ok === true && x.j.confirmed === true, x.j);
ok("two emails are sent", sent.length === 2, sent.length);
ok("both go to Resend with the key", sent.every(s => s.url === "https://api.resend.com/emails" && s.init.headers.authorization === "Bearer re_test"));
ok("first goes to the inbox with reply-to", sent[0].body.to[0] === "support@tfilah.com" && sent[0].body.reply_to === "reader@example.com");
ok("first carries the message and the page", sent[0].body.text.includes("במילה השלישית") && sent[0].body.text.includes("/tefila/mizrach-119/") && sent[0].body.subject.includes("תפלת הדרך"));
ok("second goes to the visitor", sent[1].body.to[0] === "reader@example.com" && sent[1].body.reply_to === "support@tfilah.com");
const c = JSON.stringify(sent[1].body);
ok("confirmation holds nothing the visitor typed", !c.includes("במילה") && !c.includes("ישראל") && !c.includes("mizrach-119") && !c.includes("תפלת הדרך"));
ok("confirmation is right-to-left and has plain text", sent[1].body.html.includes('dir="rtl"') && sent[1].body.text.length > 40);
ok("from address is the site", sent.every(s => s.body.from.includes("support@tfilah.com")));

_resetRateLimit();
x = await call({ ...good, email: "" });
ok("no address: one email, not confirmed", x.r.status === 200 && sent.length === 1 && x.j.confirmed === false && !("reply_to" in sent[0].body));
_resetRateLimit();
x = await call({ ...good, message: "<script>alert(1)</script> בדיקה" });
ok("message is escaped in the html", sent[0].body.html.includes("&lt;script&gt;") && !sent[0].body.html.includes("<script>"));
_resetRateLimit();
x = await call({ ...good, title: "כותרת\r\nBcc: x@y.z" });
ok("no line breaks reach the subject", !/[\r\n]/.test(sent[0].body.subject));
_resetRateLimit();
x = await call({ ...good, page: "https://evil.example/x" });
ok("a page outside the site is dropped", !sent[0].body.text.includes("evil.example"));
_resetRateLimit();
x = await call({ ...good, website: "http://spam" });
ok("hidden field: accepted and nothing sent", x.r.status === 200 && sent.length === 0);

for (const [name, body, status] of [["short message", { ...good, message: "אב" }, 400], ["bad email", { ...good, email: "not an email" }, 400], ["two addresses", { ...good, email: "a@b.co,c@d.co" }, 400],
  ["too long", { ...good, message: "א".repeat(3001) }, 413], ["missing message", { kind: "contact" }, 400]]) {
  _resetRateLimit(); x = await call(body); ok(name + " is refused", x.r.status === status && sent.length === 0, x.r.status);
}
_resetRateLimit(); x = await call(null, { raw: "{not json" }); ok("bad json", x.r.status === 400);
_resetRateLimit(); x = await call(good, { method: "GET" }); ok("GET is refused", x.r.status === 405);
_resetRateLimit(); x = await call(good, { headers: { origin: "https://other.example" } }); ok("another site is refused", x.r.status === 403 && sent.length === 0);
_resetRateLimit(); x = await call(good, { headers: { "content-type": "text/plain" } }); ok("wrong content type", x.r.status === 415);
_resetRateLimit(); x = await call(good, {}, {}); ok("no key: 503, nothing sent", x.r.status === 503 && sent.length === 0);

_resetRateLimit(); upstream = () => new Response("{}", { status: 500 });
x = await call(good); ok("upstream failure is reported, body not echoed", x.r.status === 502 && x.j.error === "upstream error" && sent.length === 1);
_resetRateLimit(); upstream = n => new Response("{}", { status: n === 1 ? 200 : 500 });
x = await call(good); ok("message arrived, confirmation failed: still ok", x.r.status === 200 && x.j.ok && x.j.confirmed === false);
upstream = () => new Response("{}", { status: 200 });

_resetRateLimit(); let last;
for (let i = 0; i < 5; i++) last = await call(good);
ok("fifth request in ten minutes is limited", last.r.status === 429 && last.r.headers.get("retry-after") && sent.length === 0, last.r.status);
ok("responses are not cached", last.r.headers.get("cache-control") === "no-store");
const k = confirmation("contact");
ok("contact confirmation differs from the report one", k.subject !== confirmation("error").subject && k.html.includes("תודה שכתבת לנו"));

console.log(`${pass + fail} checks, ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
