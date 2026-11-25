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
    List<String[]> prayers, psalms, foods;
    GeolocationPermissions.Callback geoCb;
    String geoOrigin;

    // ---------- lifecycle ----------
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("tf", MODE_PRIVATE);
        dark = prefs.getBoolean("dark", false);
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
        render();
    }

    @Override public void onBackPressed() {
        if (stack.size() > 1) { stack.remove(stack.size() - 1); render(); } else super.onBackPressed();
    }

    @Override public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        boolean ok = false;
        for (int r : res) ok |= r == PackageManager.PERMISSION_GRANTED;
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
        tap(dk, 999, v -> { dark = !dark; prefs.edit().putBoolean("dark", dark).apply(); render(); });
        bar.addView(dk, new LinearLayout.LayoutParams(dp(44), dp(44)));
        content.removeAllViews();
        content.addView(s.build(), new FrameLayout.LayoutParams(-1, -1));
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

    static String norm(String s) { return bare(s).replaceAll("[\"'׳״`.,?!]", "").replaceAll("\\s+", " ").trim().toLowerCase(); }

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
            final String last = prefs.getString("last", "");
            if (!last.isEmpty()) {
                final String[] p = last.split("\t", -1);
                if (p.length == 3) col.addView(row("להמשיך מאיפה שעצרתם", p[2], v -> open(new Reader(p[0], p[1], p[2]))), gap(14));
            }
            String[][] tiles = {{"📖", "סידור", "שחרית, מנחה, ערבית ועוד"}, {"🎵", "תהילים", "כל 150 הפרקים"}, {"🍎", "מה מברכים על", "כותבים מאכל, מקבלים ברכה"},
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
                    else if (k == 3) open(new Web("קריאה משותפת", SITE + "/tehillim-yachad/?utm_source=app"));
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
                seg.addView(pill(NUS_HE[i], n.equals(nus), v -> { prefs.edit().putString("nus", n).apply(); render(); }), lp);
            }
            col.addView(seg);
            LinkedHashMap<String, Integer> groups = new LinkedHashMap<>();
            for (String[] r : prayers) if (r[1].equals(nus)) { Integer c = groups.get(r[2]); groups.put(r[2], c == null ? 1 : c + 1); }
            for (final Map.Entry<String, Integer> e : groups.entrySet())
                col.addView(row(e.getKey(), e.getValue() == 1 ? "תפילה אחת" : e.getValue() + " תפילות", v -> open(new Group(nus, e.getKey()))), gap(10));
            return scroll(col);
        }
    }

    class Group implements Screen {
        final String nus, name;
        Group(String n, String g) { nus = n; name = g; }
        public String title() { return name; }
        public View build() {
            LinearLayout col = column();
            TextView n = label("נוסח " + NUS_HE[nusIndex(nus)], 14, fUiB, cMuted);
            col.addView(n);
            for (final String[] r : prayers) if (r[1].equals(nus) && r[2].equals(name)) col.addView(row(r[4], r[3], v -> open(new Reader("p", r[0], r[4]))), gap(10));
            return scroll(col);
        }
    }

    // ---------- psalms ----------
    class Tehillim implements Screen {
        public String title() { return "תהילים"; }
        public View build() {
            LinearLayout col = column();
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

    // ---------- reading ----------
    class Reader implements Screen {
        final String kind, id, name;
        Reader(String k, String i, String n) { kind = k; id = i; name = n; }
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
            tools.addView(pill("א−", false, v -> { prefs.edit().putFloat("size", Math.max(16f, size - 2f)).apply(); render(); }), new LinearLayout.LayoutParams(dp(52), dp(44)));
            LinearLayout.LayoutParams m = new LinearLayout.LayoutParams(dp(52), dp(44)); m.setMarginStart(dp(6));
            tools.addView(pill("א+", false, v -> { prefs.edit().putFloat("size", Math.min(40f, size + 2f)).apply(); render(); }), m);
            LinearLayout.LayoutParams m2 = new LinearLayout.LayoutParams(-2, dp(44)); m2.setMarginStart(dp(6));
            tools.addView(pill("ניקוד", nikud, v -> { prefs.edit().putBoolean("nikud", !nikud).apply(); render(); }), m2);
            tools.addView(new View(MainActivity.this), new LinearLayout.LayoutParams(0, 1, 1));
            LinearLayout.LayoutParams m3 = new LinearLayout.LayoutParams(-2, dp(44));
            tools.addView(pill(favs.contains(key) ? "★ נשמר" : "☆ שמירה", favs.contains(key), v -> {
                if (!favs.remove(key)) favs.add(key);
                prefs.edit().putStringSet("favs", favs).apply(); render(); }), m3);
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
            if ("t".equals(kind)) {
                final int n = Integer.parseInt(id);
                LinearLayout nav = new LinearLayout(MainActivity.this);
                if (n > 1) nav.addView(pill("› הפרק הקודם", false, v -> swap(n - 1)), new LinearLayout.LayoutParams(0, dp(48), 1));
                if (n < psalms.size()) { LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(48), 1); if (n > 1) lp.setMarginStart(dp(8)); nav.addView(pill("הפרק הבא ‹", true, v -> swap(n + 1)), lp); }
                col.addView(nav, gap(14));
            }
            return scroll(col);
        }
        void swap(int n) { stack.remove(stack.size() - 1); open(new Reader("t", String.valueOf(n), "תהילים פרק " + psalms.get(n - 1)[1])); }
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
            final EditText in = new EditText(MainActivity.this);
            in.setHint("כתבו מאכל או משקה");
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
            w.getSettings().setUserAgentString(w.getSettings().getUserAgentString() + " TfilahApp/0.3");
            w.setWebViewClient(new WebViewClient() {
                @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                    Uri u = r.getUrl();
                    if ("https".equals(u.getScheme()) && "tfilah.com".equals(u.getHost())) return false;
                    try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { /* no app for this link */ }
                    return true;
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
