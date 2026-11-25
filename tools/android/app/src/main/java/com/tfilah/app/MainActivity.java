package com.tfilah.app;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.text.Editable;
import android.text.Html;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.webkit.GeolocationPermissions;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** תפילה: the siddur, the Psalms and the blessings tool as a native app. All texts are bundled; nothing is typed here. */
public class MainActivity extends Activity {
    static final String SITE = "https://tfilah.com";
    static final String[] NUS = {"mizrach", "sefard", "ashkenaz"};
    static final String[] NUS_HE = {"עדות המזרח", "ספרד", "אשכנז"};

    interface Screen { String title(); View build(); }

    SharedPreferences prefs;
    Typeface fDisp, fBold, fText, fUi, fUiB;
    boolean dark;
    int cBg, cSurface, cInk, cInk2, cMuted, cLine, cPrimary, cPrimaryDk, cSoft, cGold;
    LinearLayout root, bar;
    FrameLayout content;
    final ArrayList<Screen> stack = new ArrayList<>();
    final java.util.HashMap<Screen, View> views = new java.util.HashMap<>();
    List<String[]> prayers, psalms, foods;
    /** the one place the app talks to the site: the shared reading. Replaced by a stand-in in the tests. */
    interface Net { String call(String query, String body) throws Exception; }
    interface Got { void got(Object data); }
    Net net = (query, body) -> {
        java.net.HttpURLConnection c = (java.net.HttpURLConnection) new java.net.URL(SITE + "/api/yachad" + query).openConnection();
        c.setConnectTimeout(10000); c.setReadTimeout(15000);
        c.setRequestProperty("User-Agent", "TfilahApp/1.1 (Android)");
        if (body != null) {
            c.setRequestMethod("POST"); c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json");
            // the server takes writes only from the site itself; the app is the site's own, and says so in both headers it reads
            c.setRequestProperty("Origin", SITE);
            c.setRequestProperty("Referer", SITE + "/");
            try (java.io.OutputStream o = c.getOutputStream()) { o.write(body.getBytes("UTF-8")); }
        }
        try (InputStream in = c.getResponseCode() >= 400 ? c.getErrorStream() : c.getInputStream()) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] b = new byte[8192];
            for (int n; in != null && (n = in.read(b)) > 0; ) out.write(b, 0, n);
            return out.toString("UTF-8");
        } finally { c.disconnect(); }
    };
    java.util.concurrent.Executor io = java.util.concurrent.Executors.newSingleThreadExecutor();
    static final Object FAILED = new Object();

    /** asks the server; the answer (its "data", or FAILED) comes back on the main thread */
    void ask(final String fn, final org.json.JSONObject args, final Got then) {
        io.execute(() -> {
            Object out = FAILED;
            try {
                String raw = fn == null ? net.call("?list=1", null) : net.call("", new org.json.JSONObject().put("fn", fn).put("args", args).toString());
                org.json.JSONObject j = new org.json.JSONObject(raw);
                if (!j.has("error")) out = j.opt("data");
            } catch (Exception e) { out = FAILED; }
            final Object res = out;
            runOnUiThread(() -> { if (!isFinishing()) then.got(res); });
        });
    }

    String rid() {
        String r = prefs.getString("rid", "");
        if (r.isEmpty()) {
            StringBuilder b = new StringBuilder();
            java.util.Random x = new java.security.SecureRandom();
            for (int i = 0; i < 16; i++) b.append("abcdefghijklmnopqrstuvwxyz0123456789".charAt(x.nextInt(36)));
            r = b.toString();
            prefs.edit().putString("rid", r).apply();
        }
        return r;
    }

    void say(String s) { android.widget.Toast.makeText(this, s, android.widget.Toast.LENGTH_LONG).show(); }

    GeolocationPermissions.Callback geoCb;
    String geoOrigin;

    // ---------- lifecycle ----------
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("tf", MODE_PRIVATE);
        dark = prefs.contains("dark") ? prefs.getBoolean("dark", false)
                : (getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK) == android.content.res.Configuration.UI_MODE_NIGHT_YES;
        fDisp = font("heebo-hebrew-900"); fBold = font("heebo-hebrew-700"); fText = font("assistant-hebrew-400"); fUi = font("assistant-hebrew-600"); fUiB = font("assistant-hebrew-700");
        prayers = table("index.tsv"); psalms = table("tehillim.tsv"); foods = table("brachot.tsv");
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
        bar = new LinearLayout(this);
        content = new FrameLayout(this);
        root.addView(bar, new LinearLayout.LayoutParams(-1, dp(56)));
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);
        stack.add(new Home());
        String id = sharedId(getIntent());
        if (id != null) { stack.add(new Yachad()); stack.add(new Reading(id, "")); }
        go(getIntent(), false);
        render();
        Remind.schedule(this);
    }

    /** a reminder that was tapped */
    void go(Intent i, boolean draw) {
        String g = i == null ? null : i.getStringExtra("go");
        if (g == null) return;
        Screen s = "shabbat".equals(g) ? new Web("זמני שבת", SITE + "/zmanei-shabbat/?utm_source=app") : "yomi".equals(g) ? new Tehillim() : null;
        if (s == null) return;
        if (draw) open(s); else stack.add(s);
    }

    void buzz(View v) { v.performHapticFeedback(android.os.Build.VERSION.SDK_INT >= 30 ? android.view.HapticFeedbackConstants.CONFIRM : android.view.HapticFeedbackConstants.VIRTUAL_KEY); }

    /** a shared-reading link (tfilah.com/y/...) that opened the app */
    static String sharedId(Intent i) {
        Uri u = i == null ? null : i.getData();
        if (u == null || !"tfilah.com".equals(u.getHost()) || u.getPathSegments().size() != 2 || !"y".equals(u.getPathSegments().get(0))) return null;
        String id = u.getPathSegments().get(1);
        return id.matches("[A-Za-z0-9_-]{1,40}") ? id : null;
    }

    @Override protected void onNewIntent(Intent i) {
        super.onNewIntent(i);
        String id = sharedId(i);
        if (id != null) open(new Reading(id, ""));
        go(i, true);
    }

    @Override public void onBackPressed() {
        Screen top = stack.get(stack.size() - 1);
        View v = views.get(top);
        if (top instanceof Web && v instanceof WebView && ((WebView) v).canGoBack()) { ((WebView) v).goBack(); return; }
        if (stack.size() <= 1) { super.onBackPressed(); return; }
        keepPlace();
        stack.remove(stack.size() - 1);
        views.remove(top);
        if (v instanceof WebView) ((WebView) v).destroy();
        Screen now = stack.get(stack.size() - 1);
        if (now instanceof Home) views.remove(now);
        if (now instanceof Reading) { ((Reading) now).data = null; views.remove(now); }
        if (now instanceof Yachad) { ((Yachad) now).list = null; views.remove(now); }
        render();
    }

    @Override protected void onPause() { super.onPause(); keepPlace(); }

    /** remembers how far down the open text was read */
    void keepPlace() {
        Screen top = stack.get(stack.size() - 1);
        View v = views.get(top);
        if (top instanceof Reader && v instanceof ScrollView) prefs.edit().putInt("pos\t" + ((Reader) top).kind + "\t" + ((Reader) top).id, v.getScrollY()).apply();
    }

    /** builds the open screen again after a setting changed, staying at the same place in the text */
    void refresh() {
        Screen top = stack.get(stack.size() - 1);
        View old = views.remove(top);
        float at = -1;
        if (old instanceof ScrollView && ((ScrollView) old).getChildCount() > 0) { int h = ((ScrollView) old).getChildAt(0).getHeight(); if (h > 0) at = old.getScrollY() / (float) h; }
        render();
        final View now = views.get(top);
        final float f = at;
        if (f > 0 && now instanceof ScrollView) now.post(() -> { if (((ScrollView) now).getChildCount() > 0) now.scrollTo(0, Math.round(f * ((ScrollView) now).getChildAt(0).getHeight())); });
    }

    @Override public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        boolean ok = false;
        for (int r : res) ok |= r == PackageManager.PERMISSION_GRANTED;
        if (code == 2) { if (stack.get(stack.size() - 1) instanceof Reminders) refresh(); return; }
        if (geoCb != null) geoCb.invoke(geoOrigin, ok, false);
        geoCb = null;
    }

    void open(Screen s) { stack.add(s); render(); }

    void render() {
        palette();
        Screen s = stack.get(stack.size() - 1);
        root.setBackgroundColor(cBg);
        getWindow().setStatusBarColor(cSurface);
        getWindow().setNavigationBarColor(cBg);
        getWindow().getDecorView().setSystemUiVisibility(dark ? 0 : View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        if (s instanceof Reader) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        bar.removeAllViews();
        bar.setBackgroundColor(cSurface);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(8), 0, dp(8), 0);
        bar.setElevation(dp(2));
        if (stack.size() > 1) {
            TextView back = label("›", 30, fUiB, cInk);
            back.setGravity(Gravity.CENTER);
            back.setContentDescription("חזרה");
            tap(back, 999, v -> onBackPressed());
            bar.addView(back, new LinearLayout.LayoutParams(dp(44), dp(44)));
        } else {
            View mark = new View(this);
            mark.setBackground(new Mark(cPrimary));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(dp(30), dp(30));
            lp.setMarginStart(dp(8)); lp.setMarginEnd(dp(6));
            bar.addView(mark, lp);
        }
        TextView t = label(s.title(), 20, fDisp, cInk);
        t.setMaxLines(1);
        t.setEllipsize(TextUtils.TruncateAt.END);
        t.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        bar.addView(t, new LinearLayout.LayoutParams(0, -2, 1));
        TextView dk = label(dark ? "☀" : "☾", 22, fUiB, cInk2);
        dk.setGravity(Gravity.CENTER);
        dk.setContentDescription("מצב לילה");
        tap(dk, 999, v -> { dark = !dark; prefs.edit().putBoolean("dark", dark).apply();
            for (View w : views.values()) if (w instanceof WebView) ((WebView) w).destroy();
            Screen top = stack.get(stack.size() - 1); View keep = views.get(top); views.clear(); if (keep != null) views.put(top, keep); refresh(); });
        bar.addView(dk, new LinearLayout.LayoutParams(dp(44), dp(44)));
        View v = views.get(s);
        if (v == null) {
            v = s.build();
            // an answer that arrived while the screen was being built has already drawn the newer view: keep that one
            if (stack.get(stack.size() - 1) != s) return;
            if (views.get(s) != null) v = views.get(s); else views.put(s, v);
        }
        content.removeAllViews();
        content.addView(v, new FrameLayout.LayoutParams(-1, -1));
    }

    void palette() {
        cPrimary = 0xFF1389D6; cPrimaryDk = 0xFF0A5CA8; cGold = 0xFFFFE48A;
        if (dark) { cBg = 0xFF0A1826; cSurface = 0xFF11263A; cInk = 0xFFEAF4FC; cInk2 = 0xFFBCD4E8; cMuted = 0xFF8FB0C9; cLine = 0xFF1F3B55; cSoft = 0xFF16324B; }
        else { cBg = 0xFFF3F9FE; cSurface = 0xFFFFFFFF; cInk = 0xFF0B2E4F; cInk2 = 0xFF27506F; cMuted = 0xFF46677F; cLine = 0xFFDDEEF9; cSoft = 0xFFE8F4FD; }
    }

    // ---------- data ----------
    Typeface font(String n) { try { return Typeface.createFromAsset(getAssets(), "fonts/" + n + ".ttf"); } catch (Exception e) { return Typeface.DEFAULT; } }

    String asset(String path) {
        try (InputStream in = getAssets().open(path)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] b = new byte[16384];
            for (int n; (n = in.read(b)) > 0; ) out.write(b, 0, n);
            return out.toString("UTF-8");
        } catch (Exception e) { return ""; }
    }

    List<String[]> table(String path) {
        ArrayList<String[]> rows = new ArrayList<>();
        for (String line : asset(path).split("\n")) if (!line.isEmpty()) rows.add(line.split("\t", -1));
        return rows;
    }

    static String bare(String s) { return s.replaceAll("[֑-ׇ​-‍]", ""); }

    static String norm(String s) { return bare(s).replaceAll("[\"'׳״`.,?!]", "").replaceAll("\\s+", " ").trim().toLowerCase(java.util.Locale.ROOT); }

    // ---------- small view helpers ----------
    int dp(float v) { return Math.round(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics())); }

    TextView label(String s, float sp, Typeface f, int color) {
        TextView t = new TextView(this);
        t.setText(s); t.setTextSize(sp); t.setTypeface(f); t.setTextColor(color);
        t.setTextDirection(View.TEXT_DIRECTION_RTL);
        t.setTextAlignment(View.TEXT_ALIGNMENT_VIEW_START);
        t.setIncludeFontPadding(false);
        t.setLineSpacing(0, 1.25f);
        return t;
    }

    GradientDrawable shape(int fill, int stroke, float radiusDp) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fill); g.setCornerRadius(dp(radiusDp));
        if (stroke != 0) g.setStroke(dp(1), stroke);
        return g;
    }

    void tap(View v, float radiusDp, View.OnClickListener l) {
        Drawable bg = v.getBackground();
        GradientDrawable mask = shape(0xFFFFFFFF, 0, radiusDp);
        v.setBackground(new RippleDrawable(ColorStateList.valueOf(dark ? 0x33FFFFFF : 0x221389D6), bg, mask));
        v.setClickable(true); v.setFocusable(true);
        v.setOnClickListener(l);
    }

    LinearLayout column() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
        l.setPadding(dp(16), dp(16), dp(16), dp(28));
        return l;
    }

    ScrollView scroll(View child) {
        ScrollView s = new ScrollView(this);
        s.setFillViewport(true);
        s.addView(child, new ScrollView.LayoutParams(-1, -2));
        return s;
    }

    LinearLayout.LayoutParams gap(int topDp) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.topMargin = dp(topDp);
        return lp;
    }

    /** a list row: a title, an optional second line, and a chevron */
    View row(String title, String sub, View.OnClickListener l) {
        LinearLayout r = new LinearLayout(this);
        r.setGravity(Gravity.CENTER_VERTICAL);
        r.setPadding(dp(16), dp(14), dp(12), dp(14));
        r.setMinimumHeight(dp(58));
        r.setBackground(shape(cSurface, cLine, 16));
        LinearLayout txt = new LinearLayout(this);
        txt.setOrientation(LinearLayout.VERTICAL);
        txt.addView(label(title, 18, fBold, cInk));
        if (sub != null && !sub.isEmpty()) { TextView s = label(sub, 14, fUi, cMuted); s.setPadding(0, dp(3), 0, 0); txt.addView(s); }
        r.addView(txt, new LinearLayout.LayoutParams(0, -2, 1));
        r.addView(label("‹", 24, fUiB, cMuted));
        tap(r, 16, l);
        return r;
    }

    TextView pill(String s, boolean on, View.OnClickListener l) {
        TextView t = label(s, 15, fUiB, on ? 0xFFFFFFFF : cInk);
        t.setGravity(Gravity.CENTER);
        t.setMaxLines(1);
        t.setEllipsize(TextUtils.TruncateAt.END);
        t.setPadding(dp(14), 0, dp(14), 0);
        t.setMinHeight(dp(44));
        t.setBackground(shape(on ? cPrimary : cSurface, on ? 0 : cLine, 999));
        tap(t, 999, l);
        return t;
    }

    TextView heading(String s) { TextView t = label(s, 22, fDisp, cInk); t.setPadding(dp(2), 0, dp(2), dp(4)); return t; }

    // ---------- the brand mark ----------
    class Mark extends Drawable {
        final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        final int color;
        Mark(int c) { color = c; }
        @Override public void draw(Canvas c) {
            float k = getBounds().width() / 32f;
            c.save(); c.translate(getBounds().left, getBounds().top); c.scale(k, k);
            p.setColor(color); p.setStyle(Paint.Style.STROKE); p.setStrokeWidth(5.6f); p.setStrokeCap(Paint.Cap.ROUND); p.setStrokeJoin(Paint.Join.ROUND);
            Path path = new Path();
            path.moveTo(23, 26.5f); path.lineTo(23, 13.5f);
            path.arcTo(new RectF(9, 6.5f, 23, 20.5f), 0, -180);
            path.lineTo(9, 22.5f); path.quadTo(9, 26.5f, 5, 26.5f);
            c.drawPath(path, p);
            p.setStyle(Paint.Style.FILL);
            c.drawCircle(16, 19.4f, 2.6f, p);
            c.restore();
        }
        @Override public void setAlpha(int a) { }
        @Override public void setColorFilter(ColorFilter f) { }
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
    }

    // ---------- home ----------
    class Home implements Screen {
        public String title() { return "תפילה"; }
        public View build() {
            LinearLayout col = column();
            LinearLayout hero = new LinearLayout(MainActivity.this);
            hero.setOrientation(LinearLayout.VERTICAL);
            hero.setPadding(dp(22), dp(24), dp(22), dp(24));
            GradientDrawable g = new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM, new int[]{0xFF2FA9EA, 0xFF1583D2, 0xFF0A4F92});
            g.setCornerRadius(dp(26));
            hero.setBackground(g);
            hero.addView(label("כל התפילות.", 32, fDisp, 0xFFFFFFFF));
            hero.addView(label("במקום אחד.", 32, fDisp, cGold));
            TextView sub = label("סידור בשלושה נוסחים, ספר תהילים ומה מברכים. הכול שמור במכשיר ועובד גם בלי אינטרנט.", 16, fUi, 0xFFEAF6FF);
            sub.setPadding(0, dp(10), 0, 0);
            sub.setLineSpacing(0, 1.35f);
            hero.addView(sub);
            col.addView(hero);
            TextView find = label("🔍  חיפוש תפילה או פרק תהילים", 17, fUi, cMuted);
            find.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
            find.setPadding(dp(20), 0, dp(20), 0);
            find.setBackground(shape(cSurface, cLine, 999));
            tap(find, 999, v -> open(new Search()));
            LinearLayout.LayoutParams fl = new LinearLayout.LayoutParams(-1, dp(54)); fl.topMargin = dp(14);
            col.addView(find, fl);
            final String last = prefs.getString("last", "");
            if (!last.isEmpty()) {
                final String[] p = last.split("\t", -1);
                if (p.length == 3) col.addView(row("להמשיך מאיפה שעצרתם", p[2], v -> open(new Reader(p[0], p[1], p[2]))), gap(14));
            }
            String[][] tiles = {{"📖", "סידור", "שחרית, מנחה, ערבית ועוד"}, {"📜", "תהילים", "כל 150 הפרקים"}, {"🍎", "מה מברכים על", "כותבים מאכל, מקבלים ברכה"},
                    {"🤝", "קריאה משותפת", "קוראים תהילים ביחד"}, {"🌅", "זמני היום", "לפי העיר שלכם"}, {"🕯️", "זמני שבת", "כניסה ויציאה"}};
            LinearLayout line = null;
            for (int i = 0; i < tiles.length; i++) {
                if (i % 2 == 0) { line = new LinearLayout(MainActivity.this); col.addView(line, gap(12)); }
                final int k = i;
                LinearLayout t = new LinearLayout(MainActivity.this);
                t.setOrientation(LinearLayout.VERTICAL);
                t.setPadding(dp(16), dp(16), dp(16), dp(16));
                t.setMinimumHeight(dp(124));
                t.setBackground(shape(cSurface, cLine, 20));
                TextView ic = label(tiles[i][0], 26, Typeface.DEFAULT, cInk);
                ic.setGravity(Gravity.CENTER);
                ic.setBackground(shape(cSoft, 0, 14));
                t.addView(ic, new LinearLayout.LayoutParams(dp(48), dp(48)));
                TextView n = label(tiles[i][1], 19, fDisp, cInk); n.setPadding(0, dp(10), 0, 0); t.addView(n);
                TextView d = label(tiles[i][2], 14, fUi, cMuted); d.setPadding(0, dp(3), 0, 0); t.addView(d);
                tap(t, 20, v -> {
                    if (k == 0) open(new Siddur()); else if (k == 1) open(new Tehillim()); else if (k == 2) open(new Brachot());
                    else if (k == 3) open(new Yachad());
                    else if (k == 4) open(new Web("זמני היום", SITE + "/zmanei-hayom/?utm_source=app"));
                    else open(new Web("זמני שבת", SITE + "/zmanei-shabbat/?utm_source=app"));
                });
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, -1, 1);
                if (i % 2 == 1) lp.setMarginStart(dp(12));
                line.addView(t, lp);
            }
            Set<String> favs = prefs.getStringSet("favs", new HashSet<String>());
            if (!favs.isEmpty()) {
                col.addView(heading("שמורים"), gap(24));
                for (final String[] r : prayers) if (favs.contains("p\t" + r[0])) col.addView(row(r[4], NUS_HE[nusIndex(r[1])], v -> open(new Reader("p", r[0], r[4]))), gap(8));
                for (final String[] r : psalms) if (favs.contains("t\t" + r[0])) col.addView(row("תהילים פרק " + r[1], r[2], v -> open(new Reader("t", r[0], "תהילים פרק " + r[1]))), gap(8));
            }
            col.addView(row("תזכורות", "תהילים יומי, ויום שישי לפני שבת", v -> open(new Reminders())), gap(24));
            col.addView(row("אודות ומקורות", "מאיפה הטקסטים, פרטיות ויצירת קשר", v -> open(new About())), gap(8));
            TextView foot = label("tfilah.com · חינם, בלי הרשמה ובלי פרסומות", 14, fUi, cMuted);
            foot.setGravity(Gravity.CENTER);
            foot.setTextAlignment(View.TEXT_ALIGNMENT_CENTER);
            col.addView(foot, gap(26));
            return scroll(col);
        }
    }

    static int nusIndex(String n) { for (int i = 0; i < NUS.length; i++) if (NUS[i].equals(n)) return i; return 0; }

    // ---------- siddur ----------
    class Siddur implements Screen {
        public String title() { return "סידור"; }
        public View build() {
            final String nus = prefs.getString("nus", "mizrach");
            LinearLayout col = column();
            LinearLayout seg = new LinearLayout(MainActivity.this);
            for (int i = 0; i < NUS.length; i++) {
                final String n = NUS[i];
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(46), 1);
                if (i > 0) lp.setMarginStart(dp(8));
                seg.addView(pill(NUS_HE[i], n.equals(nus), v -> { prefs.edit().putString("nus", n).apply(); refresh(); }), lp);
            }
            col.addView(seg);
            LinkedHashMap<String, Integer> groups = new LinkedHashMap<>();
            for (String[] r : prayers) if (r[1].equals(nus)) { Integer c = groups.get(r[2]); groups.put(r[2], c == null ? 1 : c + 1); }
            for (final Map.Entry<String, Integer> e : groups.entrySet())
                col.addView(row(e.getKey(), e.getValue() == 1 ? "תפילה אחת" : e.getValue() + " תפילות", v -> open(new Group(nus, e.getKey(), null))), gap(10));
            return scroll(col);
        }
    }

    static String head(String path) { int i = path.indexOf(" · "); return i < 0 ? path : path.substring(0, i); }
    static String rest(String path) { int i = path.indexOf(" · "); return i < 0 ? "" : path.substring(i + 3); }

    class Group implements Screen {
        final String nus, name, sub;
        Group(String n, String g, String s) { nus = n; name = g; sub = s; }
        public String title() { return sub == null || sub.isEmpty() ? name : sub; }
        public View build() {
            LinearLayout col = column();
            col.addView(label("נוסח " + NUS_HE[nusIndex(nus)] + (sub == null || sub.isEmpty() ? "" : " · " + name), 14, fUiB, cMuted));
            LinkedHashMap<String, Integer> subs = new LinkedHashMap<>();
            int all = 0;
            for (String[] r : prayers) if (r[1].equals(nus) && r[2].equals(name)) { all++; String h = head(r[3]); Integer c = subs.get(h); subs.put(h, c == null ? 1 : c + 1); }
            if (sub == null && all > 24 && subs.size() > 1) {
                for (final Map.Entry<String, Integer> e : subs.entrySet())
                    col.addView(row(e.getKey().isEmpty() ? "כללי" : e.getKey(), e.getValue() == 1 ? "תפילה אחת" : e.getValue() + " תפילות", v -> open(new Group(nus, name, e.getKey()))), gap(10));
                return scroll(col);
            }
            String lastHead = "";
            for (final String[] r : prayers) {
                if (!r[1].equals(nus) || !r[2].equals(name) || (sub != null && !head(r[3]).equals(sub))) continue;
                String h = sub == null ? r[3] : rest(r[3]);
                if (!h.equals(lastHead)) { lastHead = h; if (!h.isEmpty()) { TextView t = label(h, 15, fUiB, cPrimary); t.setPadding(dp(4), dp(8), dp(4), 0); col.addView(t, gap(10)); } }
                col.addView(row(r[4], "", v -> open(new Reader("p", r[0], r[4]))), gap(8));
            }
            return scroll(col);
        }
    }

    // ---------- search ----------
    class Search implements Screen {
        String q = "";
        public String title() { return "חיפוש"; }
        public View build() {
            LinearLayout col = column();
            final EditText in = field("שם של תפילה, או מספר פרק");
            in.setText(q);
            col.addView(in, new LinearLayout.LayoutParams(-1, dp(56)));
            final LinearLayout list = new LinearLayout(MainActivity.this);
            list.setOrientation(LinearLayout.VERTICAL);
            col.addView(list);
            fill(list);
            in.addTextChangedListener(new TextWatcher() {
                public void beforeTextChanged(CharSequence s, int a, int b, int c) { }
                public void onTextChanged(CharSequence s, int a, int b, int c) { }
                public void afterTextChanged(Editable e) { q = e.toString(); fill(list); }
            });
            in.requestFocus();
            return scroll(col);
        }
        void fill(LinearLayout list) {
            list.removeAllViews();
            String n = norm(q);
            if (n.isEmpty()) { TextView t = label("כותבים כמה אותיות, למשל ”עלינו” או ”קכא”.", 16, fUi, cInk2); t.setPadding(dp(4), dp(18), dp(4), 0); list.addView(t); return; }
            int shown = 0;
            String digits = n.replaceAll("[^0-9]", ""), word = n.replace("תהילים", "").replace("תהלים", "").replace("פרק", "").trim();
            for (final String[] r : psalms) if (r[0].equals(digits) || r[1].equals(word)) { shown++; list.addView(row("תהילים פרק " + r[1], r[2], v -> open(new Reader("t", r[0], "תהילים פרק " + r[1]))), gap(10)); }
            String mine = prefs.getString("nus", "mizrach");
            for (int pass = 0; pass < 2 && shown < 40; pass++)
                for (final String[] r : prayers) {
                    if (r[1].equals(mine) != (pass == 0) || !norm(r[4]).contains(n)) continue;
                    if (shown++ >= 40) break;
                    list.addView(row(r[4], "נוסח " + NUS_HE[nusIndex(r[1])] + " · " + r[2] + (head(r[3]).isEmpty() ? "" : " · " + head(r[3])), v -> open(new Reader("p", r[0], r[4]))), gap(10));
                }
            if (shown == 0) { TextView t = label("לא מצאנו. נסו מילה אחרת.", 16, fUi, cInk2); t.setPadding(dp(4), dp(18), dp(4), 0); list.addView(t); }
        }
    }

    EditText field(String hint) {
        EditText in = new EditText(this);
        in.setHint(hint);
        in.setHintTextColor(cMuted);
        in.setTextColor(cInk);
        in.setTypeface(fBold);
        in.setTextSize(20);
        in.setMaxLines(1);
        in.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        in.setHorizontallyScrolling(false);
        in.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        in.setTextDirection(View.TEXT_DIRECTION_RTL);
        in.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        in.setPadding(dp(20), 0, dp(20), 0);
        in.setBackground(shape(cSurface, cPrimary, 999));
        return in;
    }

    // ---------- about ----------
    class About implements Screen {
        public String title() { return "אודות ומקורות"; }
        View para(String head, String body) {
            LinearLayout b = new LinearLayout(MainActivity.this);
            b.setOrientation(LinearLayout.VERTICAL);
            b.setPadding(dp(18), dp(16), dp(18), dp(16));
            b.setBackground(shape(cSurface, cLine, 20));
            b.addView(label(head, 19, fDisp, cInk));
            TextView t = label(body, 16, fUi, cInk2); t.setPadding(0, dp(6), 0, 0); t.setLineSpacing(0, 1.45f); b.addView(t);
            return b;
        }
        public View build() {
            LinearLayout col = column();
            col.addView(para("מה זה תפילה", "סידור בשלושה נוסחים, ספר תהילים מלא והכלי ”מה מברכים על”. חינם, בלי הרשמה ובלי פרסומות. האפליקציה מופעלת בידי צוות מתנדבים, לזיכוי הרבים. היא אינה פוסקת הלכה ואינה באה במקום רב."));
            col.addView(para("מקורות הטקסטים", "נוסח עדות המזרח ונוסח ספרד: מהדורות פתוחות ממאגר תורת אמת, שבנחלת הכלל. נוסח אשכנז: מאגר דעת, שבנחלת הכלל, עם השלמות מסידור מצודה ברישיון CC-BY. ספר תהילים: Tanach.us, בנחלת הכלל. הטקסטים נאספו דרך המהדורות הפתוחות בארכיון של ספריא. הם אינם מוקלדים ביד, והם מובאים כמות שהם.\n\nמה מברכים על: כל תשובה מובאת עם המקור שלה."), gap(10));
            col.addView(para("פרטיות", "הסידור, התהילים והברכות שמורים במכשיר. מה שסימנתם ושמרתם, וגם התזכורות, נשארים רק אצלכם. קריאה משותפת צריכה חיבור לאינטרנט: השם שכותבים לקריאה והפרקים שנקראו נשמרים בשרת של האתר, כדי שכל המשתתפים יראו אותם. זמני היום וזמני שבת נפתחים מהאתר."), gap(10));
            col.addView(row("מדיניות הפרטיות המלאה", "", v -> link(SITE + "/pratiyut/")), gap(10));
            col.addView(row("דיווח על טעות בנוסח", "כל דיווח נבדק מול המהדורה", v -> link(SITE + "/odot/#taut")), gap(8));
            col.addView(row("יצירת קשר", "", v -> link(SITE + "/odot/#kesher")), gap(8));
            col.addView(row("האתר המלא", "tfilah.com", v -> link(SITE + "/?utm_source=app")), gap(8));
            return scroll(col);
        }
    }

    void link(String url) { try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception e) { /* no browser */ } }

    // ---------- psalms ----------
    class Tehillim implements Screen {
        public String title() { return "תהילים"; }
        public View build() {
            LinearLayout col = column();
            col.addView(heading("תהילים יומי"));
            java.util.Calendar now = java.util.Calendar.getInstance();
            final int wd = now.get(java.util.Calendar.DAY_OF_WEEK) - 1;
            final String wn = wd == 6 ? "שבת" : "יום " + WEEKDAYS[wd];
            col.addView(row("לפי ימי השבוע: " + wn, range(WEEKLY[wd][0], WEEKLY[wd][1]), v -> open(new Portion("תהילים ל" + wn, WEEKLY[wd][0], WEEKLY[wd][1], ""))), gap(4));
            final int[] hd = hebDay();
            if (hd != null) {
                final int d = hd[0];
                final boolean both = d == 29 && hd[1] == 29;   // in a month of 29 days the last day carries the portion of day 30 too
                final int a = MONTHLY[d - 1][0], b = both ? 150 : MONTHLY[d - 1][1];
                final String extra = d == 25 ? "פרק קיט, אותיות א עד ל" : d == 26 ? "פרק קיט, אותיות מ עד ת" : "";
                final String dn = "יום " + psalms.get(d - 1)[1] + " בחודש";
                col.addView(row("לפי ימי החודש: " + dn, extra.isEmpty() ? range(a, b) : extra, v -> open(new Portion("תהילים ל" + dn, a, b, extra))), gap(8));
                TextView n = label("היום העברי מתחיל בערב שלפניו.", 13, fUi, cMuted); n.setPadding(dp(4), dp(6), dp(4), 0); col.addView(n);
            }
            col.addView(heading("כל הפרקים"), gap(22));
            col.addView(label("בוחרים פרק", 15, fUiB, cMuted));
            LinearLayout line = null;
            for (int i = 0; i < psalms.size(); i++) {
                if (i % 5 == 0) { line = new LinearLayout(MainActivity.this); col.addView(line, gap(8)); }
                final String[] r = psalms.get(i);
                TextView b = label(r[1], 19, fBold, cInk);
                b.setGravity(Gravity.CENTER);
                b.setTextAlignment(View.TEXT_ALIGNMENT_CENTER);
                b.setBackground(shape(cSurface, cLine, 14));
                b.setContentDescription("פרק " + r[1]);
                tap(b, 14, v -> open(new Reader("t", r[0], "תהילים פרק " + r[1])));
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(54), 1);
                if (i % 5 > 0) lp.setMarginStart(dp(8));
                line.addView(b, lp);
            }
            return scroll(col);
        }
    }

    // the two divisions of the book, as the site has them
    static final int[][] MONTHLY = {{1, 9}, {10, 17}, {18, 22}, {23, 28}, {29, 34}, {35, 38}, {39, 43}, {44, 48}, {49, 54}, {55, 59}, {60, 65}, {66, 68}, {69, 71}, {72, 76}, {77, 78}, {79, 82}, {83, 87}, {88, 89},
            {90, 96}, {97, 103}, {104, 105}, {106, 107}, {108, 112}, {113, 118}, {119, 119}, {119, 119}, {120, 134}, {135, 139}, {140, 144}, {145, 150}};
    static final int[][] WEEKLY = {{1, 29}, {30, 50}, {51, 72}, {73, 89}, {90, 106}, {107, 119}, {120, 150}};
    static final String[] WEEKDAYS = {"ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"};

    String range(int a, int b) { return a == b ? "פרק " + psalms.get(a - 1)[1] : "פרקים " + psalms.get(a - 1)[1] + " עד " + psalms.get(b - 1)[1]; }

    /** today's day in the Hebrew month and the length of that month; null where the phone cannot tell */
    static int[] hebDay() { return hebDayAt(java.util.Calendar.getInstance().getTimeInMillis()); }

    static int[] hebDayAt(long ms) {
        if (android.os.Build.VERSION.SDK_INT < 24) return null;
        try {
            android.icu.util.HebrewCalendar hc = new android.icu.util.HebrewCalendar();
            hc.setTimeInMillis(ms);
            int d = hc.get(android.icu.util.Calendar.DAY_OF_MONTH);
            return d >= 1 && d <= 30 ? new int[]{d, hc.getActualMaximum(android.icu.util.Calendar.DAY_OF_MONTH)} : null;
        } catch (Exception e) { return null; }
    }

    class Portion implements Screen {
        final String name, extra; final int from, to;
        Portion(String n, int a, int b, String x) { name = n; from = a; to = b; extra = x; }
        public String title() { return name; }
        public View build() {
            LinearLayout col = column();
            col.addView(label(extra.isEmpty() ? range(from, to) : extra, 15, fUiB, cMuted));
            for (int n = from; n <= to; n++) { final String[] r = psalms.get(n - 1); col.addView(row("פרק " + r[1], r[2], v -> open(new Reader("t", r[0], "תהילים פרק " + r[1]))), gap(8)); }
            return scroll(col);
        }
    }

    // ---------- reminders ----------
    class Reminders implements Screen {
        public String title() { return "תזכורות"; }
        String clock(int m) { return String.format(java.util.Locale.US, "%02d:%02d", m / 60, m % 60); }
        void block(LinearLayout col, String head, String body, final String key, final String keyAt, final int def, final boolean friday) {
            final boolean on = prefs.getBoolean(key, false);
            final int at = prefs.getInt(keyAt, def);
            LinearLayout b = new LinearLayout(MainActivity.this);
            b.setOrientation(LinearLayout.VERTICAL);
            b.setPadding(dp(18), dp(16), dp(18), dp(16));
            b.setBackground(shape(cSurface, cLine, 20));
            b.addView(label(head, 19, fDisp, cInk));
            TextView t = label(body, 15, fUi, cInk2); t.setPadding(0, dp(4), 0, dp(12)); t.setLineSpacing(0, 1.4f); b.addView(t);
            LinearLayout line = new LinearLayout(MainActivity.this);
            line.addView(pill(on ? "✓ פועלת" : "כבויה", on, v -> {
                prefs.edit().putBoolean(key, !on).apply();
                if (!on && android.os.Build.VERSION.SDK_INT >= 33 && checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 2);
                Remind.schedule(MainActivity.this); buzz(v); refresh(); }), new LinearLayout.LayoutParams(0, dp(48), 1));
            line.addView(pill("שעה: " + clock(at), false, v -> new android.app.TimePickerDialog(MainActivity.this, (picker, h, m) -> {
                int chosen = h * 60 + m;
                if (friday && chosen >= 15 * 60) { chosen = 14 * 60; say("ביום שישי התזכורת נשלחת עד 14:59, כדי שלא תגיע בשבת."); }
                prefs.edit().putInt(keyAt, chosen).apply();
                Remind.schedule(MainActivity.this); refresh(); }, at / 60, at % 60, true).show()), new LinearLayout.LayoutParams(0, dp(48), 1) {{ setMarginStart(dp(8)); }});
            b.addView(line);
            col.addView(b, gap(10));
        }
        public View build() {
            LinearLayout col = column();
            col.addView(note("התזכורות נשמרות במכשיר בלבד. הן לא נשלחות בשבת וביום טוב."));
            block(col, "תהילים יומי", "פעם ביום, בשעה שתבחרו. לחיצה על התזכורת פותחת את הפרקים של היום.", "rDaily", "rDailyAt", 8 * 60, false);
            block(col, "יום שישי, לפני שבת", "תזכורת לבדוק את זמני כניסת השבת ויציאתה.", "rFri", "rFriAt", 13 * 60, true);
            if (android.os.Build.VERSION.SDK_INT >= 33 && (prefs.getBoolean("rDaily", false) || prefs.getBoolean("rFri", false)) && checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED)
                col.addView(note("כדי שהתזכורות יופיעו צריך לאשר לאפליקציה לשלוח התראות, בהגדרות הטלפון."), gap(12));
            return scroll(col);
        }
    }

    // ---------- reading ----------
    class Reader implements Screen {
        final String kind, id, name;
        String mid; int globalN; boolean sending;
        Reader(String k, String i, String n) { kind = k; id = i; name = n; }
        Reader shared(String m, int n) { mid = m; globalN = n; return this; }
        public String title() { return name; }
        public View build() {
            prefs.edit().putString("last", kind + "\t" + id + "\t" + name).apply();
            final float size = prefs.getFloat("size", 23f);
            final boolean nikud = prefs.getBoolean("nikud", true);
            final String key = kind + "\t" + id;
            final Set<String> favs = new HashSet<>(prefs.getStringSet("favs", new HashSet<String>()));
            LinearLayout col = column();
            LinearLayout tools = new LinearLayout(MainActivity.this);
            tools.setGravity(Gravity.CENTER_VERTICAL);
            tools.addView(pill("א−", false, v -> { prefs.edit().putFloat("size", Math.max(16f, size - 2f)).apply(); refresh(); }), new LinearLayout.LayoutParams(dp(52), dp(44)));
            LinearLayout.LayoutParams m = new LinearLayout.LayoutParams(dp(52), dp(44)); m.setMarginStart(dp(6));
            tools.addView(pill("א+", false, v -> { prefs.edit().putFloat("size", Math.min(40f, size + 2f)).apply(); refresh(); }), m);
            LinearLayout.LayoutParams m2 = new LinearLayout.LayoutParams(-2, dp(44)); m2.setMarginStart(dp(6));
            tools.addView(pill("ניקוד", nikud, v -> { prefs.edit().putBoolean("nikud", !nikud).apply(); refresh(); }), m2);
            tools.addView(new View(MainActivity.this), new LinearLayout.LayoutParams(0, 1, 1));
            LinearLayout.LayoutParams m3 = new LinearLayout.LayoutParams(-2, dp(44));
            tools.addView(pill(favs.contains(key) ? "★ נשמר" : "☆ שמירה", favs.contains(key), v -> {
                if (!favs.remove(key)) favs.add(key);
                buzz(v);
                prefs.edit().putStringSet("favs", favs).apply(); refresh(); }), m3);
            LinearLayout.LayoutParams m4 = new LinearLayout.LayoutParams(-2, dp(44)); m4.setMarginStart(dp(6));
            tools.addView(pill("שיתוף", false, v -> share()), m4);
            col.addView(tools);
            LinearLayout card = new LinearLayout(MainActivity.this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(18), dp(10), dp(18), dp(20));
            card.setBackground(shape(cSurface, cLine, 22));
            String raw = asset(("p".equals(kind) ? "p/" : "t/") + id + ".txt");
            if (raw.isEmpty()) raw = "הטקסט לא נמצא.";
            for (String line : raw.split("\n")) {
                if (line.isEmpty()) continue;
                boolean head = line.startsWith("<big><b>");
                String h = nikud ? line : bare(line);
                TextView t = label("", head ? size * 0.92f : size, head ? fBold : fText, head ? cInk : cInk);
                t.setText(Html.fromHtml(h));
                t.setLineSpacing(0, 1.5f);
                t.setLinkTextColor(cPrimary);
                t.setTextIsSelectable(false);
                card.addView(t, gap(head ? 14 : 10));
            }
            col.addView(card, gap(12));
            if ("p".equals(kind)) {
                String[] prev = null, next = null, me = null;
                for (String[] r : prayers) {
                    if (r[0].equals(id)) { me = r; continue; }
                    if (me == null) prev = r; else { next = r; break; }
                }
                if (me != null) {
                    final String[] a = prev != null && prev[1].equals(me[1]) && prev[2].equals(me[2]) ? prev : null, b = next != null && next[1].equals(me[1]) && next[2].equals(me[2]) ? next : null;
                    LinearLayout nav = new LinearLayout(MainActivity.this);
                    nav.setOrientation(LinearLayout.VERTICAL);
                    if (b != null) nav.addView(pill("הבא: " + b[4] + " ‹", true, v -> swapTo(b)), new LinearLayout.LayoutParams(-1, dp(50)));
                    if (a != null) { LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, dp(46)); lp.topMargin = dp(8); nav.addView(pill("› הקודם: " + a[4], false, v -> swapTo(a)), lp); }
                    col.addView(nav, gap(14));
                }
            }
            final int place = prefs.getInt("pos\t" + key, 0);
            if (mid != null) {
                TextView done = pill(sending ? "שולח…" : "✓ סיימתי לקרוא את הפרק", true, v -> {
                    if (sending) return;
                    sending = true; refresh();
                    try {
                        ask("finish_chapter", new org.json.JSONObject().put("p_mid", mid).put("p_n", globalN).put("p_by", "").put("p_rid", rid()), d -> {
                            sending = false;
                            if (d == FAILED || d == null || d == org.json.JSONObject.NULL) { say("לא הצלחנו לעדכן. בדקו את החיבור ונסו שוב."); refresh(); return; }
                            buzz(root);
                            say("תודה. הפרק נרשם.");
                            if (stack.get(stack.size() - 1) == Reader.this) onBackPressed();
                        });
                    } catch (Exception e) { sending = false; }
                });
                col.addView(done, new LinearLayout.LayoutParams(-1, dp(54)) {{ topMargin = dp(16); }});
            } else if ("t".equals(kind)) {
                final int n = Integer.parseInt(id);
                LinearLayout nav = new LinearLayout(MainActivity.this);
                if (n > 1) nav.addView(pill("› הפרק הקודם", false, v -> swap(n - 1)), new LinearLayout.LayoutParams(0, dp(48), 1));
                if (n < psalms.size()) { LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(48), 1); if (n > 1) lp.setMarginStart(dp(8)); nav.addView(pill("הפרק הבא ‹", true, v -> swap(n + 1)), lp); }
                col.addView(nav, gap(14));
            }
            final ScrollView sv = scroll(col);
            if (place > 0) sv.post(() -> sv.scrollTo(0, place));
            return sv;
        }
        void leave() { prefs.edit().remove("pos\t" + kind + "\t" + id).apply(); views.remove(stack.remove(stack.size() - 1)); }
        void swap(int n) { leave(); open(new Reader("t", String.valueOf(n), "תהילים פרק " + psalms.get(n - 1)[1])); }
        void swapTo(String[] r) { leave(); open(new Reader("p", r[0], r[4])); }
        void share() {
            String url = SITE + "/";
            if ("t".equals(kind)) url = SITE + "/tehillim/" + id + "/";
            else for (String[] r : prayers) if (r[0].equals(id) && !r[5].isEmpty()) url = SITE + r[5];
            Intent i = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, name + " | תפילה\n" + url + "?utm_source=app");
            try { startActivity(Intent.createChooser(i, "שיתוף")); } catch (Exception e) { /* nothing to share with */ }
        }
    }

    // ---------- what blessing ----------
    class Brachot implements Screen {
        String q = "";
        public String title() { return "מה מברכים על"; }
        public View build() {
            LinearLayout col = column();
            final EditText in = field("כתבו מאכל או משקה");
            in.setText(q);
            col.addView(in, new LinearLayout.LayoutParams(-1, dp(56)));
            final LinearLayout list = new LinearLayout(MainActivity.this);
            list.setOrientation(LinearLayout.VERTICAL);
            col.addView(list);
            fill(list);
            in.addTextChangedListener(new TextWatcher() {
                public void beforeTextChanged(CharSequence s, int a, int b, int c) { }
                public void onTextChanged(CharSequence s, int a, int b, int c) { }
                public void afterTextChanged(Editable e) { q = e.toString(); fill(list); }
            });
            return scroll(col);
        }
        void fill(LinearLayout list) {
            list.removeAllViews();
            String n = norm(q);
            int shown = 0;
            for (final String[] f : foods) {
                if (!n.isEmpty() && !norm(f[1] + " " + f[2].replace('|', ' ')).contains(n)) continue;
                if (shown++ >= 40) break;
                String sub = f[9].isEmpty() ? f[4] : ("cases".equals(f[3]) ? "תלוי במקרה" : "יש יותר מדעה אחת");
                list.addView(row(f[1], sub, v -> open(new Food(f))), gap(10));
            }
            if (shown == 0) {
                TextView t = label("לא מצאנו את המאכל הזה. נסו שם אחר, או בדקו באתר.", 16, fUi, cInk2);
                t.setPadding(dp(4), dp(18), dp(4), 0);
                list.addView(t);
            }
        }
    }

    class Food implements Screen {
        final String[] f;
        Food(String[] r) { f = r; }
        public String title() { return f[1]; }
        View box(String small, String big, String note, int color) {
            LinearLayout b = new LinearLayout(MainActivity.this);
            b.setOrientation(LinearLayout.VERTICAL);
            b.setPadding(dp(18), dp(16), dp(18), dp(16));
            b.setBackground(shape(cSurface, cLine, 20));
            b.addView(label(small, 14, fUiB, cMuted));
            TextView t = label(big, 26, fDisp, color); t.setPadding(0, dp(4), 0, 0); b.addView(t);
            if (note != null && !note.isEmpty()) { TextView n = label(note, 15, fUi, cInk2); n.setPadding(0, dp(8), 0, 0); n.setLineSpacing(0, 1.4f); b.addView(n); }
            return b;
        }
        public View build() {
            LinearLayout col = column();
            col.addView(heading("מה מברכים על " + f[1] + "?"));
            if (f[9].isEmpty()) {
                col.addView(box("לפני האכילה", f[4], f[6], dark ? 0xFF6FD39A : 0xFF0E7A41), gap(10));
                col.addView(box("אחרי האכילה", f[5], f[7], cInk), gap(10));
            } else {
                TextView tag = label("cases".equals(f[3]) ? "התשובה תלויה במקרה" : "יש יותר מדעה אחת. הדעות מובאות זו לצד זו, בלי להכריע.", 15, fUiB, cInk2);
                tag.setPadding(dp(2), dp(4), dp(2), 0);
                col.addView(tag);
                if (!f[6].isEmpty()) { TextView c = label(f[6], 15, fUi, cInk2); c.setPadding(dp(2), dp(6), dp(2), 0); col.addView(c); }
                for (String op : f[9].split("¶")) {
                    String[] o = op.split("§", -1);
                    if (o.length < 4) continue;
                    String rul = (o[1].isEmpty() ? "" : "לפני: " + o[1]) + (!o[1].isEmpty() && !o[2].isEmpty() ? "\n" : "") + (o[2].isEmpty() ? "" : "אחרי: " + o[2]);
                    LinearLayout b = new LinearLayout(MainActivity.this);
                    b.setOrientation(LinearLayout.VERTICAL);
                    b.setPadding(dp(18), dp(14), dp(18), dp(14));
                    b.setBackground(shape(cSurface, cLine, 20));
                    b.addView(label(o[0], 14, fUiB, cMuted));
                    if (!rul.isEmpty()) { TextView t = label(rul, 20, fBold, cInk); t.setPadding(0, dp(4), 0, 0); b.addView(t); }
                    if (!o[3].isEmpty()) { TextView n = label(o[3], 15, fUi, cInk2); n.setPadding(0, dp(6), 0, 0); n.setLineSpacing(0, 1.4f); b.addView(n); }
                    col.addView(b, gap(10));
                }
            }
            if (!f[8].isEmpty()) { TextView n = label(f[8], 15, fUi, cInk2); n.setPadding(dp(4), 0, dp(4), 0); n.setLineSpacing(0, 1.4f); col.addView(n, gap(12)); }
            if (!f[10].isEmpty()) { TextView s = label("מקור: " + f[10], 13, fUi, cMuted); s.setPadding(dp(4), 0, dp(4), 0); s.setLineSpacing(0, 1.4f); col.addView(s, gap(14)); }
            TextView d = label("האתר מביא את ההוראות כפי שהן במקורות ואינו פוסק. במקרה של ספק שואלים רב.", 13, fUi, cMuted);
            d.setPadding(dp(4), 0, dp(4), 0);
            col.addView(d, gap(8));
            return scroll(col);
        }
    }

    // ---------- shared reading ----------
    static final String[] KIND = {"refuah", "neshama", "zivug", "hatzlacha", "general"};
    static final String[][] KIND_HE = {{"לרפואה שלמה של", "לרפואה", "שם החולה", "שם האם", ""}, {"לעילוי נשמת", "לעילוי נשמה", "שם הנפטר/ת", "שם האב או האם", " ז״ל"},
            {"לזיווג הגון עבור", "לזיווג", "שם המבקש/ת", "שם האם", ""}, {"להצלחה ולישועה של", "להצלחה", "שם", "שם האם", ""}, {"תפילת רבים", "בקשה כללית", "על מה מתפללים", "", ""}};

    static int kindIndex(String k) { for (int i = 0; i < KIND.length; i++) if (KIND[i].equals(k)) return i; return 1; }

    /** the line a reading is known by, in the site's own wording */
    static String lineOf(org.json.JSONObject m) {
        int k = kindIndex(m.optString("kind"));
        if (k == 4) return m.optString("name");
        return KIND_HE[k][0] + " " + m.optString("name") + " " + ("בת".equals(m.optString("rel")) ? "בת" : "בן") + " " + m.optString("parent") + KIND_HE[k][4];
    }

    void remember(String id, String line) {
        StringBuilder b = new StringBuilder(id + "\t" + line.replace('\t', ' ').replace('\n', ' '));
        int kept = 1;
        for (String row : prefs.getString("mine", "").split("\n")) if (!row.isEmpty() && !row.startsWith(id + "\t") && kept++ < 30) b.append("\n").append(row);
        prefs.edit().putString("mine", b.toString()).apply();
    }

    TextView note(String s) { TextView t = label(s, 16, fUi, cInk2); t.setLineSpacing(0, 1.45f); t.setPadding(dp(4), 0, dp(4), 0); return t; }

    class Yachad implements Screen {
        org.json.JSONArray list; boolean failed, asking;
        public String title() { return "קריאה משותפת"; }
        public View build() {
            LinearLayout col = column();
            col.addView(heading("מישהו צריך תפילה?"));
            col.addView(note("פותחים קריאת תהילים על שמו, שולחים קישור למשפחה ולחברים, וכל אחד לוקח פרק. ביחד מסיימים את הספר."));
            col.addView(pill("פתיחת קריאה חדשה", true, v -> open(new NewReading())), new LinearLayout.LayoutParams(-1, dp(54)) {{ topMargin = dp(14); }});
            String mine = prefs.getString("mine", "");
            if (!mine.isEmpty()) {
                col.addView(heading("הקריאות שלי"), gap(24));
                for (String row : mine.split("\n")) { final String[] r = row.split("\t", -1); if (r.length == 2) col.addView(row(r[1], "", v -> open(new Reading(r[0], r[1]))), gap(8)); }
            }
            col.addView(heading("קריאות פתוחות לכולם"), gap(24));
            if (list == null && !failed) {
                col.addView(note("טוען…"));
                if (!asking) { asking = true; ask(null, null, d -> { asking = false; if (d instanceof org.json.JSONArray) list = (org.json.JSONArray) d; else failed = true; if (stack.get(stack.size() - 1) == Yachad.this) refresh(); else views.remove(Yachad.this); }); }
            } else if (failed) {
                col.addView(note("לא הצלחנו לטעון את הרשימה. בדקו את החיבור לאינטרנט."));
                col.addView(pill("לנסות שוב", false, v -> { failed = false; refresh(); }), new LinearLayout.LayoutParams(-2, dp(46)) {{ topMargin = dp(10); }});
            } else if (list.length() == 0) col.addView(note("אין כרגע קריאות פתוחות."));
            else for (int i = 0; i < list.length() && i < 60; i++) {
                final org.json.JSONObject m = list.optJSONObject(i);
                if (m == null) continue;
                final String line = lineOf(m);
                int done = m.optInt("done");
                col.addView(row(line, done == 0 ? "עוד לא נקרא פרק. תהיו הראשונים." : done == 1 ? "נקרא פרק אחד" : "נקראו " + done + " פרקים", v -> open(new Reading(m.optString("id"), line))), gap(8));
            }
            return scroll(col);
        }
    }

    class Reading implements Screen {
        final String id; String line;
        org.json.JSONObject data; boolean failed, missing, asking, taking;
        Reading(String i, String l) { id = i; line = l; }
        public String title() { return "קריאה משותפת"; }
        void load() { if (asking) return; asking = true;
            try { ask("get_memorial", new org.json.JSONObject().put("p_id", id), d -> { asking = false;
                if (d instanceof org.json.JSONObject) { data = (org.json.JSONObject) d; org.json.JSONObject m = data.optJSONObject("memorial"); if (m != null) line = lineOf(m); }
                else if (d == FAILED) failed = true; else missing = true;
                if (stack.get(stack.size() - 1) == Reading.this) refresh(); else views.remove(Reading.this); }); } catch (Exception e) { asking = false; failed = true; } }
        void go(int n) {
            remember(id, line);
            int ch = (n - 1) % 150 + 1;
            open(new Reader("t", String.valueOf(ch), "תהילים פרק " + psalms.get(ch - 1)[1]).shared(id, n));
        }
        public View build() {
            LinearLayout col = column();
            if (!line.isEmpty()) col.addView(heading(line));
            if (missing) { col.addView(note("הקריאה הזו לא נמצאה. ייתכן שהקישור שגוי.")); return scroll(col); }
            if (failed) {
                col.addView(note("לא הצלחנו לטעון את הקריאה. בדקו את החיבור לאינטרנט."));
                col.addView(pill("לנסות שוב", false, v -> { failed = false; refresh(); }), new LinearLayout.LayoutParams(-2, dp(46)) {{ topMargin = dp(10); }});
                return scroll(col);
            }
            if (data == null) { col.addView(note("טוען…")); load(); return scroll(col); }
            org.json.JSONObject m = data.optJSONObject("memorial");
            org.json.JSONArray ch = data.optJSONArray("chapters");
            if (m == null) m = new org.json.JSONObject();
            if (ch == null) ch = new org.json.JSONArray();
            // the round being read now: the first one that does not yet have all 150 chapters done (the server's own rule)
            java.util.HashMap<Integer, Integer> perRound = new java.util.HashMap<>();
            for (int i = 0; i < ch.length(); i++) { org.json.JSONObject c = ch.optJSONObject(i); if (c != null && "done".equals(c.optString("s"))) { int r = (c.optInt("n") - 1) / 150 + 1; Integer k = perRound.get(r); perRound.put(r, k == null ? 1 : k + 1); } }
            int round = 1;
            while (round <= 100 && perRound.get(round) != null && perRound.get(round) >= 150) round++;
            final int base = (round - 1) * 150;
            final int[] state = new int[151];   // 0 free, 1 taken by someone in the last day, 2 done
            String dayAgo = stamp(System.currentTimeMillis() - 24 * 3600 * 1000L);
            int done = 0;
            for (int i = 0; i < ch.length(); i++) {
                org.json.JSONObject c = ch.optJSONObject(i);
                if (c == null) continue;
                int n = c.optInt("n") - base;
                if (n < 1 || n > 150) continue;
                if ("done".equals(c.optString("s"))) { state[n] = 2; done++; }
                else if (c.optString("at").compareTo(dayAgo) >= 0) state[n] = 1;
            }
            String msg = m.optString("msg");
            if (!msg.isEmpty()) col.addView(note(msg));
            LinearLayout card = new LinearLayout(MainActivity.this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setPadding(dp(18), dp(16), dp(18), dp(18));
            card.setBackground(shape(cSurface, cLine, 20));
            card.addView(label((round > 1 ? "סבב " + round + " · " : "") + "נקראו " + done + " מתוך 150 פרקים", 19, fDisp, cInk));
            LinearLayout track = new LinearLayout(MainActivity.this);
            track.setBackground(shape(cSoft, 0, 999));
            track.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
            View fill = new View(MainActivity.this);
            fill.setBackground(shape(cPrimary, 0, 999));
            if (done > 0) track.addView(fill, new LinearLayout.LayoutParams(0, -1, done));
            if (done < 150) track.addView(new View(MainActivity.this), new LinearLayout.LayoutParams(0, -1, 150 - done));
            card.addView(track, new LinearLayout.LayoutParams(-1, dp(12)) {{ topMargin = dp(10); }});
            int readers = m.optInt("readers");
            if (readers > 0) { TextView r = label(readers == 1 ? "קורא אחד השתתף עד עכשיו" : readers + " קוראים השתתפו עד עכשיו", 15, fUi, cMuted); r.setPadding(0, dp(8), 0, 0); card.addView(r); }
            col.addView(card, gap(12));
            col.addView(pill(taking ? "בוחר פרק…" : "קחו פרק לקריאה", true, v -> {
                if (taking) return;
                taking = true; refresh();
                try { ask("take_chapter", new org.json.JSONObject().put("p_mid", id).put("p_by", "").put("p_rid", rid()), d -> { taking = false;
                    if (d instanceof Number) go(((Number) d).intValue());
                    else { say(d == FAILED ? "לא הצלחנו. בדקו את החיבור ונסו שוב." : "כל הפרקים כבר נלקחו. נסו שוב מאוחר יותר."); refresh(); } }); } catch (Exception e) { taking = false; }
            }), new LinearLayout.LayoutParams(-1, dp(56)) {{ topMargin = dp(14); }});
            final String shareLine = line;
            col.addView(pill("שליחת הקישור למשפחה ולחברים", false, v -> {
                Intent i = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, shareLine + "\nקוראים יחד תהילים. כל אחד לוקח פרק:\n" + SITE + "/y/" + id);
                try { startActivity(Intent.createChooser(i, "שיתוף")); } catch (Exception e) { /* nothing to share with */ }
            }), new LinearLayout.LayoutParams(-1, dp(50)) {{ topMargin = dp(8); }});
            col.addView(heading("או בוחרים פרק"), gap(24));
            col.addView(note("מלא: נקרא. מסומן: מישהו קורא עכשיו. ריק: פנוי."));
            LinearLayout rowL = null;
            for (int n = 1; n <= 150; n++) {
                if ((n - 1) % 6 == 0) { rowL = new LinearLayout(MainActivity.this); col.addView(rowL, gap(6)); }
                final int g = base + n, st = state[n];
                TextView b = label(psalms.get(n - 1)[1], 16, fBold, st == 2 ? 0xFFFFFFFF : cInk);
                b.setGravity(Gravity.CENTER);
                b.setTextAlignment(View.TEXT_ALIGNMENT_CENTER);
                b.setBackground(shape(st == 2 ? cPrimary : st == 1 ? cSoft : cSurface, st == 2 ? 0 : st == 1 ? cPrimary : cLine, 12));
                b.setContentDescription("פרק " + psalms.get(n - 1)[1] + (st == 2 ? ", נקרא" : st == 1 ? ", מישהו קורא" : ", פנוי"));
                if (st == 0) tap(b, 12, v -> {
                    try { ask("claim_chapter", new org.json.JSONObject().put("p_mid", id).put("p_n", g).put("p_by", "").put("p_rid", rid()), d -> {
                        if (Boolean.TRUE.equals(d)) go(g); else { say(d == FAILED ? "לא הצלחנו. בדקו את החיבור ונסו שוב." : "מישהו כבר לקח את הפרק הזה. בחרו אחר."); data = null; refresh(); } }); } catch (Exception e) { /* nothing */ }
                });
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(46), 1);
                if ((n - 1) % 6 > 0) lp.setMarginStart(dp(6));
                rowL.addView(b, lp);
            }
            return scroll(col);
        }
    }

    static String stamp(long ms) {
        java.text.SimpleDateFormat f = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.US);
        f.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
        return f.format(new java.util.Date(ms));
    }

    class NewReading implements Screen {
        int kind = 0; boolean bat, listed, sending;
        String name = "", parent = "";
        public String title() { return "קריאה חדשה"; }
        public View build() {
            LinearLayout col = column();
            col.addView(heading("על מה קוראים?"));
            LinearLayout kinds = null;
            for (int i = 0; i < KIND.length; i++) {
                if (i % 3 == 0) { kinds = new LinearLayout(MainActivity.this); col.addView(kinds, gap(8)); }
                final int k = i;
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(46), 1);
                if (i % 3 > 0) lp.setMarginStart(dp(8));
                kinds.addView(pill(KIND_HE[i][1], i == kind, v -> { kind = k; refresh(); }), lp);
            }
            final EditText n = field(KIND_HE[kind][2]);
            n.setText(name);
            n.addTextChangedListener(watch(s -> name = s));
            col.addView(n, new LinearLayout.LayoutParams(-1, dp(56)) {{ topMargin = dp(18); }});
            if (kind != 4) {
                LinearLayout rel = new LinearLayout(MainActivity.this);
                rel.addView(pill("בן", !bat, v -> { bat = false; refresh(); }), new LinearLayout.LayoutParams(0, dp(46), 1));
                rel.addView(pill("בת", bat, v -> { bat = true; refresh(); }), new LinearLayout.LayoutParams(0, dp(46), 1) {{ setMarginStart(dp(8)); }});
                col.addView(rel, gap(10));
                final EditText pr = field(KIND_HE[kind][3]);
                pr.setText(parent);
                pr.addTextChangedListener(watch(s -> parent = s));
                col.addView(pr, new LinearLayout.LayoutParams(-1, dp(56)) {{ topMargin = dp(10); }});
            }
            col.addView(pill(listed ? "✓ מוצגת ברשימה הפתוחה לכולם" : "להציג גם ברשימה הפתוחה לכולם", listed, v -> { listed = !listed; refresh(); }), new LinearLayout.LayoutParams(-1, dp(48)) {{ topMargin = dp(16); }});
            col.addView(note(listed ? "כל מי שנכנס יראה את הקריאה ויוכל להצטרף." : "כרגע רק מי שיקבל מכם את הקישור יראה את הקריאה."), gap(8));
            col.addView(pill(sending ? "פותח…" : "פתיחת הקריאה", true, v -> {
                if (sending) return;
                final String nm = name.trim(), pa = parent.trim();
                if (nm.isEmpty() || nm.length() > 60 || (kind != 4 && (pa.isEmpty() || pa.length() > 40))) { say(kind == 4 ? "כתבו על מה מתפללים." : "כתבו את השם ואת שם ההורה."); return; }
                sending = true; refresh();
                try {
                    final org.json.JSONObject a = new org.json.JSONObject().put("p_name", nm).put("p_parent", kind == 4 ? "" : pa).put("p_rel", bat ? "בת" : "בן").put("p_kind", KIND[kind]).put("p_by", "").put("p_msg", "").put("p_listed", listed);
                    ask("create_memorial", a, d -> {
                        sending = false;
                        if (!(d instanceof String)) { say("לא הצלחנו לפתוח את הקריאה. בדקו את החיבור ונסו שוב."); refresh(); return; }
                        String line = "";
                        try { line = lineOf(new org.json.JSONObject().put("name", nm).put("parent", pa).put("rel", bat ? "בת" : "בן").put("kind", KIND[kind])); } catch (Exception e) { /* keeps the empty line */ }
                        remember((String) d, line);
                        views.remove(stack.remove(stack.size() - 1));
                        open(new Reading((String) d, line));
                    });
                } catch (Exception e) { sending = false; }
            }), new LinearLayout.LayoutParams(-1, dp(56)) {{ topMargin = dp(18); }});
            return scroll(col);
        }
    }

    interface Typed { void typed(String s); }
    TextWatcher watch(final Typed t) {
        return new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int a, int b, int c) { }
            public void onTextChanged(CharSequence s, int a, int b, int c) { }
            public void afterTextChanged(Editable e) { t.typed(e.toString()); }
        };
    }

    // ---------- the two tools that need the network ----------
    class Web implements Screen {
        final String name, url;
        Web(String n, String u) { name = n; url = u; }
        public String title() { return name; }
        public View build() {
            WebView w = new WebView(MainActivity.this);
            w.setBackgroundColor(cBg);
            w.getSettings().setJavaScriptEnabled(true);
            w.getSettings().setDomStorageEnabled(true);
            w.getSettings().setGeolocationEnabled(true);
            w.getSettings().setUserAgentString(w.getSettings().getUserAgentString() + " TfilahApp/1.2");
            w.setWebViewClient(new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                    Uri u = r.getUrl();
                    if ("https".equals(u.getScheme()) && "tfilah.com".equals(u.getHost())) return false;
                    try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { /* no app for this link */ }
                    return true;
                }
                @Override public void onReceivedError(WebView v, WebResourceRequest r, android.webkit.WebResourceError e) {
                    if (r.isForMainFrame()) v.loadDataWithBaseURL(null, "<!doctype html><html lang=he dir=rtl><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                            + "<body style='font-family:sans-serif;text-align:center;padding:22vh 24px 0;color:#27506F'><h1 style='font-size:24px;color:#0B2E4F'>אין חיבור לאינטרנט</h1>"
                            + "<p style='font-size:17px'>החלק הזה צריך חיבור. הסידור, התהילים והברכות עובדים גם בלי.</p></body></html>", "text/html", "utf-8", null);
                }
            });
            w.setWebChromeClient(new WebChromeClient() {
                @Override public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback cb) {
                    if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
                            || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) { cb.invoke(origin, true, false); return; }
                    geoCb = cb; geoOrigin = origin;
                    requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, 1);
                }
            });
            w.loadUrl(url);
            return w;
        }
    }
}
