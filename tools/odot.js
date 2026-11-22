/* The two forms on the about page: report an error in the text, and contact.
   Sent through /api/contact; when that is not available the same details open in the visitor's mail app. */
(function () {
  var M = "__MAIL__", q = new URLSearchParams(location.search);
  function cl(s, n) { return (s || "").replace(/[<>"]/g, "").slice(0, n); }
  var u = cl(q.get("u"), 200), t = cl(q.get("t"), 80), n = cl(q.get("n"), 30);
  if (u && u.indexOf(location.origin) !== 0) u = "";
  function build(box, kind) {
    if (!box) return;
    var id = kind === "error" ? "taut" : "ksr", err = kind === "error";
    var start = err ? ["מה הטעות (המילים כפי שהן באתר):", "", "מה צריך להיות, ולפי איזה סידור:", ""].join("\n") : "";
    box.innerHTML = '<form class="cform" id="' + id + 'f" novalidate>'
      + (err && (u || t) ? '<p class="cwhere">' + (t ? "<b>" + t + "</b>" + (n ? " · נוסח " + n : "") + "<br>" : "") + (u ? '<span dir="ltr">' + decodeURI(u).replace(/^https?:\/\//, "") + "</span>" : "") + "</p>" : "")
      + '<label for="' + id + 't">' + (err ? "מה מצאתם?" : "ההודעה") + '</label><textarea id="' + id + 't" rows="' + (err ? 6 : 5) + '" maxlength="3000" required></textarea>'
      + '<label for="' + id + 'e">מייל לתשובה (לא חובה)</label><input id="' + id + 'e" type="email" inputmode="email" autocomplete="email" dir="ltr" placeholder="name@example.com">'
      + '<input class="chp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">'
      + '<p class="nact"><button class="btn" type="submit">' + (err ? "שליחת הדיווח" : "שליחה") + '</button></p><p class="cmsg" role="status" aria-live="polite"></p></form>';
    var f = document.getElementById(id + "f"), ta = document.getElementById(id + "t"), em = document.getElementById(id + "e"), msg = f.querySelector(".cmsg"), btn = f.querySelector("button");
    ta.value = start;
    function say(s, bad) { msg.textContent = s; msg.className = "cmsg" + (bad ? " bad" : " good"); }
    function mailto() {
      if (!M) return false;
      var body = (err ? ["העמוד: " + u, "התפילה: " + t, n ? "הנוסח: " + n : ""].filter(function (x) { return x.length > 9; }).join("\n") + "\n\n" : "") + ta.value;
      location.href = "mailto:" + M + "?subject=" + encodeURIComponent((err ? "דיווח על טעות בנוסח" : "פנייה מהאתר") + (t && err ? ": " + t : "")) + "&body=" + encodeURIComponent(body);
      return true;
    }
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = ta.value.trim();
      if (text.replace(start.trim(), "").trim().length < 5 && text.length < start.trim().length + 5) { say("כתבו כמה מילים, כדי שנדע במה מדובר.", true); ta.focus(); return; }
      if (em.value && !em.checkValidity()) { say("כתובת המייל לא נראית תקינה.", true); em.focus(); return; }
      btn.disabled = true; say("שולחים…");
      fetch("/api/contact", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ kind: kind, message: text, email: em.value.trim(), page: err ? u.replace(location.origin, "https://tfilah.com") : "", title: err ? t : "", nusach: err ? n : "", website: f.website.value }) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { s: r.status, j: j }; }); })
        .then(function (x) {
          btn.disabled = false;
          if (x.s === 200 && x.j.ok) { f.reset(); ta.value = ""; say(x.j.confirmed ? "נשלח, תודה. שלחנו לכם אישור במייל." : "נשלח, תודה."); return; }
          if (x.s === 429) { say("נשלחו כמה הודעות ברצף. נסו שוב בעוד כמה דקות.", true); return; }
          if (x.s === 400 || x.s === 413) { say(x.j.error === "bad email" ? "כתובת המייל לא נראית תקינה." : "ההודעה קצרה מדי או ארוכה מדי.", true); return; }
          if (!mailto()) say("השליחה לא הצליחה. נסו שוב מאוחר יותר.", true); else say("פתחנו את תוכנת המייל שלכם עם הפרטים.");
        })
        .catch(function () { btn.disabled = false; if (!mailto()) say("אין חיבור כרגע. נסו שוב.", true); else say("פתחנו את תוכנת המייל שלכם עם הפרטים."); });
    });
  }
  build(document.getElementById("tautbox"), "error");
  build(document.getElementById("kesherbox"), "contact");
  if (location.hash === "#taut" || location.hash === "#kesher") { var el = document.getElementById(location.hash.slice(1)); if (el) el.scrollIntoView(); }
})();
