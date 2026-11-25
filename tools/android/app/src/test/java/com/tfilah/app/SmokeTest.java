package com.tfilah.app;

import static org.junit.Assert.*;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadows.ShadowLooper;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34, qualifiers = "w411dp-h891dp-xxhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class SmokeTest {
    MainActivity a;

    void shot(String name) throws Exception {
        ShadowLooper.idleMainLooper();
        View v = a.root;
        int w = 1080, h = 2340;
        v.measure(View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY), View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY));
        v.layout(0, 0, w, h);
        Bitmap b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        v.draw(new Canvas(b));
        String dir = System.getProperty("shots");
        if (dir != null && !dir.isEmpty()) try (FileOutputStream o = new FileOutputStream(new File(dir, name + ".png"))) { b.compress(Bitmap.CompressFormat.PNG, 100, o); }
    }

    void texts(View v, ArrayList<TextView> out) {
        if (v instanceof TextView) out.add((TextView) v);
        if (v instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) v).getChildCount(); i++) texts(((ViewGroup) v).getChildAt(i), out);
    }

    TextView find(String s) {
        ArrayList<TextView> l = new ArrayList<>(); texts(a.root, l);
        for (TextView t : l) if (!(t instanceof EditText) && t.getText().toString().equals(s)) return t;
        fail("no view with text: " + s); return null;
    }

    void click(String s) { View v = find(s); while (v != null && !v.hasOnClickListeners()) v = v.getParent() instanceof View ? (View) v.getParent() : null; assertNotNull(s, v); v.performClick(); ShadowLooper.idleMainLooper(); }

    /** read-only calls to the real site, with the app's own request code: the server must accept them */
    @Test public void realServerAnswersTheApp() throws Exception {
        a = Robolectric.buildActivity(MainActivity.class).setup().get();
        org.json.JSONObject list = new org.json.JSONObject(a.net.call("?list=1", null));
        org.json.JSONArray rows = list.getJSONArray("data");
        assertTrue(rows.length() > 0);
        String id = rows.getJSONObject(0).getString("id");
        org.json.JSONObject one = new org.json.JSONObject(a.net.call("", new org.json.JSONObject().put("fn", "get_memorial").put("args", new org.json.JSONObject().put("p_id", id)).toString()));
        assertFalse(one.toString(), one.has("error"));
        assertEquals(id, one.getJSONObject("data").getJSONObject("memorial").getString("id"));
        assertFalse(MainActivity.lineOf(one.getJSONObject("data").getJSONObject("memorial")).isEmpty());
        System.out.println("live: " + rows.length() + " public readings; first has " + one.getJSONObject("data").getJSONArray("chapters").length() + " chapter rows");
    }

    @Test public void everyScreenOpens() throws Exception {
        a = Robolectric.buildActivity(MainActivity.class).setup().get();
        assertEquals(794, a.prayers.size()); assertEquals(150, a.psalms.size()); assertTrue(a.foods.size() > 200);
        shot("1-home");
        click("סידור"); shot("2-siddur");
        click("ספרד"); click("אשכנז"); click("עדות המזרח");
        click("סדר השכמת הבוקר"); shot("3-group");
        click("מודה אני"); shot("4-reader");
        click("ניקוד"); click("ניקוד"); click("א+"); click("א−"); click("☆ שמירה"); find("★ נשמר");
        a.onBackPressed(); a.onBackPressed(); a.onBackPressed();
        find("שמורים"); find("להמשיך מאיפה שעצרתם");
        click("תהילים"); shot("5-tehillim");
        click("כג"); shot("6-psalm"); click("הפרק הבא ‹"); find("› הפרק הקודם"); a.onBackPressed(); a.onBackPressed();
        click("מה מברכים על"); 
        ArrayList<TextView> l = new ArrayList<>(); texts(a.root, l);
        for (TextView t : l) if (t instanceof EditText) t.setText("בננה");
        ShadowLooper.idleMainLooper(); shot("7-brachot");
        click("בננה"); find("בורא פרי האדמה"); find("בורא נפשות"); shot("8-food");
        a.onBackPressed(); a.onBackPressed();
        a.dark = true; a.views.clear(); a.render(); shot("9-dark");
        // every prayer and every chapter has its text file
        for (String[] r : a.prayers) assertFalse(r[0], a.asset("p/" + r[0] + ".txt").isEmpty());
        for (String[] r : a.psalms) assertFalse(r[0], a.asset("t/" + r[0] + ".txt").isEmpty());
        // every food opens
        for (String[] f : a.foods) { a.open(a.new Food(f)); a.onBackPressed(); }
        // every group and sub-section opens, and every prayer builds its screen
        long t0 = System.currentTimeMillis();
        for (String[] r : a.prayers) { a.open(a.new Reader("p", r[0], r[4])); a.onBackPressed(); }
        System.out.println("all prayers built in ms: " + (System.currentTimeMillis() - t0));
        a.dark = false; a.views.clear(); a.render();
        a.prefs.edit().putString("nus", "ashkenaz").commit();
        click("סידור"); click("שבת"); shot("10-subs"); click("שחרית"); shot("11-list"); a.onBackPressed(); a.onBackPressed(); a.onBackPressed();
        click("🔍  חיפוש תפילה או פרק תהילים");
        l = new ArrayList<>(); texts(a.root, l);
        for (TextView t : l) if (t instanceof EditText) t.setText("עלינו");
        ShadowLooper.idleMainLooper(); shot("12-search"); a.onBackPressed();
        click("אודות ומקורות"); shot("13-about"); a.onBackPressed();
        a.open(a.new Reader("p", "mizrach-2", "ברכות השחר")); shot("14-next"); 
        assertEquals(1, a.stack.size() - 1);
        a.onBackPressed();
        sharedReading();
    }

    static long at(int y, int mo, int d, int h) { java.util.Calendar c = java.util.Calendar.getInstance(); c.set(y, mo - 1, d, h, 0, 0); return c.getTimeInMillis(); }

    @Test public void remindersKeepShabbatAndWork() throws Exception {
        a = Robolectric.buildActivity(MainActivity.class).setup().get();
        // 27 November 2026 is a Friday
        java.util.Calendar fri = java.util.Calendar.getInstance(); fri.setTimeInMillis(at(2026, 11, 27, 10));
        assertEquals(java.util.Calendar.FRIDAY, fri.get(java.util.Calendar.DAY_OF_WEEK));
        assertFalse("Friday morning", Remind.rest(at(2026, 11, 27, 10)));
        assertTrue("Friday afternoon", Remind.rest(at(2026, 11, 27, 16)));
        assertTrue("Shabbat morning", Remind.rest(at(2026, 11, 28, 9)));
        assertTrue("Shabbat 20:00", Remind.rest(at(2026, 11, 28, 20)));
        assertFalse("after Shabbat", Remind.rest(at(2026, 11, 28, 22)));
        assertFalse("a weekday", Remind.rest(at(2026, 11, 25, 8)));
        // Yom Kippur and the first day of Pesach, found by their Hebrew dates
        android.icu.util.HebrewCalendar hc = new android.icu.util.HebrewCalendar();
        for (int[] md : new int[][]{{android.icu.util.HebrewCalendar.TISHRI, 10}, {android.icu.util.HebrewCalendar.NISAN, 15}, {android.icu.util.HebrewCalendar.SIVAN, 6}, {android.icu.util.HebrewCalendar.TISHRI, 1}}) {
            hc.set(5787, md[0], md[1], 10, 0, 0);
            assertTrue("yom tov " + md[0] + "/" + md[1], Remind.rest(hc.getTimeInMillis()));
            assertTrue("its eve", Remind.rest(hc.getTimeInMillis() - 18 * 3600 * 1000L));
        }
        hc.set(5787, android.icu.util.HebrewCalendar.KISLEV, 25, 10, 0, 0);   // Chanukah is a weekday
        java.util.Calendar ch = java.util.Calendar.getInstance(); ch.setTimeInMillis(hc.getTimeInMillis());
        if (ch.get(java.util.Calendar.DAY_OF_WEEK) != java.util.Calendar.SATURDAY) assertFalse(Remind.rest(hc.getTimeInMillis()));
        // the next Friday reminder falls on a Friday, in the future
        long nf = Remind.next(13 * 60, true, at(2026, 11, 25, 8));
        java.util.Calendar c = java.util.Calendar.getInstance(); c.setTimeInMillis(nf);
        assertEquals(java.util.Calendar.FRIDAY, c.get(java.util.Calendar.DAY_OF_WEEK)); assertEquals(13, c.get(java.util.Calendar.HOUR_OF_DAY));
        assertTrue(Remind.next(8 * 60, false, at(2026, 11, 25, 9)) > at(2026, 11, 25, 9));
        // turning a reminder on sets an alarm; turning it off removes it
        click("תזכורות"); shot("20-reminders");
        org.robolectric.shadows.ShadowAlarmManager am = org.robolectric.Shadows.shadowOf((android.app.AlarmManager) a.getSystemService(android.content.Context.ALARM_SERVICE));
        assertEquals(0, am.getScheduledAlarms().size());
        ArrayList<TextView> l = new ArrayList<>(); texts(a.root, l);
        TextView off = null; for (TextView t : l) if (t.getText().toString().equals("כבויה")) { off = t; break; }
        off.performClick(); ShadowLooper.idleMainLooper();
        assertEquals(1, am.getScheduledAlarms().size());
        assertTrue(a.prefs.getBoolean("rDaily", false));
        find("✓ פועלת"); shot("21-reminder-on");
        // the alarm fires: a notification, and the next alarm is set
        org.robolectric.Shadows.shadowOf(a.getApplication()).grantPermissions("android.permission.POST_NOTIFICATIONS");
        Remind.show(a, 1, "תהילים יומי", "הפרקים של היום מחכים לכם.", "yomi");
        org.robolectric.shadows.ShadowNotificationManager nm = org.robolectric.Shadows.shadowOf((android.app.NotificationManager) a.getSystemService(android.content.Context.NOTIFICATION_SERVICE));
        assertEquals(1, nm.getAllNotifications().size());
        new Remind().onReceive(a, new android.content.Intent(a, Remind.class).setAction(Remind.DAILY));
        assertEquals(1, am.getScheduledAlarms().size());
        click("✓ פועלת");
        assertEquals(0, am.getScheduledAlarms().size());
        a.onBackPressed();
        // daily Psalms: the weekday portion always opens, and its chapters are the site's
        click("תהילים");
        find("תהילים יומי"); shot("22-yomi");
        int wd = java.util.Calendar.getInstance().get(java.util.Calendar.DAY_OF_WEEK) - 1;
        a.open(a.new Portion("x", MainActivity.WEEKLY[wd][0], MainActivity.WEEKLY[wd][1], "")); shot("23-portion");
        int sum = 0; for (int[] r : MainActivity.WEEKLY) sum += r[1] - r[0] + 1; assertEquals(150, sum);
        assertEquals(30, MainActivity.MONTHLY.length); assertEquals(150, MainActivity.MONTHLY[29][1]); assertEquals(1, MainActivity.MONTHLY[0][0]);
        for (int i = 1; i < 30; i++) assertTrue(MainActivity.MONTHLY[i][0] == MainActivity.MONTHLY[i - 1][1] + 1 || MainActivity.MONTHLY[i][0] == 119);
        // the Hebrew day: 25 November 2026 is 15 Kislev (checked against another calendar), a month of 30 days
        assertEquals(15, MainActivity.hebDayAt(at(2026, 11, 25, 10))[0]);
        assertEquals(30, MainActivity.hebDayAt(at(2026, 11, 25, 10))[1]);
        assertEquals(MainActivity.hebDayAt(java.util.Calendar.getInstance().getTimeInMillis())[0], MainActivity.hebDay()[0]);
        // a tapped reminder opens the right screen
        a.go(new android.content.Intent().putExtra("go", "yomi"), true);
        assertTrue(a.stack.get(a.stack.size() - 1) instanceof MainActivity.Tehillim);
    }

    /** a stand-in for the site's shared-reading server, keeping the same rules for the calls the app makes */
    static class FakeServer implements MainActivity.Net {
        final org.json.JSONArray memorials = new org.json.JSONArray();
        final java.util.HashMap<String, java.util.TreeMap<Integer, String>> chapters = new java.util.HashMap<>();
        boolean down; int calls;
        public String call(String query, String body) throws Exception {
            calls++;
            if (down) throw new java.io.IOException("no network");
            if (body == null) return new org.json.JSONObject().put("data", memorials).toString();
            org.json.JSONObject b = new org.json.JSONObject(body), a = b.getJSONObject("args");
            String fn = b.getString("fn");
            Object out = org.json.JSONObject.NULL;
            if (fn.equals("create_memorial")) {
                String id = "id" + memorials.length();
                memorials.put(new org.json.JSONObject().put("id", id).put("name", a.getString("p_name")).put("parent", a.getString("p_parent")).put("rel", a.getString("p_rel")).put("kind", a.getString("p_kind")).put("msg", "").put("done", 0).put("listed", a.getBoolean("p_listed")));
                chapters.put(id, new java.util.TreeMap<Integer, String>());
                out = id;
            } else {
                String id = a.has("p_id") ? a.getString("p_id") : a.getString("p_mid");
                java.util.TreeMap<Integer, String> ch = chapters.get(id);
                if (ch == null) return new org.json.JSONObject().put("data", org.json.JSONObject.NULL).toString();
                org.json.JSONObject m = null;
                for (int i = 0; i < memorials.length(); i++) if (memorials.getJSONObject(i).getString("id").equals(id)) m = memorials.getJSONObject(i);
                if (fn.equals("get_memorial")) {
                    org.json.JSONArray list = new org.json.JSONArray();
                    for (java.util.Map.Entry<Integer, String> e : ch.entrySet()) list.put(new org.json.JSONObject().put("n", e.getKey()).put("s", e.getValue()).put("by_name", "").put("at", MainActivity.stamp(System.currentTimeMillis()) + ".000Z"));
                    out = new org.json.JSONObject().put("memorial", new org.json.JSONObject(m.toString()).put("readers", ch.isEmpty() ? 0 : 1)).put("chapters", list);
                } else if (fn.equals("take_chapter")) {
                    for (int n = 1; n <= 150; n++) if (!ch.containsKey(n)) { ch.put(n, "claimed"); out = n; break; }
                } else if (fn.equals("claim_chapter")) {
                    int n = a.getInt("p_n");
                    if (ch.containsKey(n)) out = false; else { ch.put(n, "claimed"); out = true; }
                } else if (fn.equals("finish_chapter")) {
                    ch.put(a.getInt("p_n"), "done");
                    int d = 0; for (String v : ch.values()) if (v.equals("done")) d++;
                    m.put("done", d); out = d;
                } else return new org.json.JSONObject().put("error", "unknown function").toString();
            }
            return new org.json.JSONObject().put("data", out).toString();
        }
    }

    void type(String hint, String text) {
        ArrayList<TextView> l = new ArrayList<>(); texts(a.root, l);
        for (TextView t : l) if (t instanceof EditText && hint.contentEquals(t.getHint())) { t.setText(text); ShadowLooper.idleMainLooper(); return; }
        fail("no field: " + hint);
    }

    void sharedReading() throws Exception {
        FakeServer srv = new FakeServer();
        a.net = srv; a.io = Runnable::run;
        // no network: a clear message and a retry, no crash
        srv.down = true;
        click("קריאה משותפת"); ShadowLooper.idleMainLooper();
        find("לא הצלחנו לטעון את הרשימה. בדקו את החיבור לאינטרנט.");
        srv.down = false;
        click("לנסות שוב"); ShadowLooper.idleMainLooper();
        find("אין כרגע קריאות פתוחות.");
        // open a new reading
        click("פתיחת קריאה חדשה");
        click("פתיחת הקריאה");                       // empty form: nothing is sent
        assertEquals(0, srv.memorials.length());
        type("שם החולה", "דוד"); type("שם האם", "שרה");
        click("להציג גם ברשימה הפתוחה לכולם");
        shot("15-new");
        click("פתיחת הקריאה"); ShadowLooper.idleMainLooper();
        assertEquals(1, srv.memorials.length());
        assertEquals("refuah", srv.memorials.getJSONObject(0).getString("kind"));
        find("לרפואה שלמה של דוד בן שרה"); find("נקראו 0 מתוך 150 פרקים");
        shot("16-reading");
        // take a chapter, read it, finish it
        click("קחו פרק לקריאה"); ShadowLooper.idleMainLooper();
        find("✓ סיימתי לקרוא את הפרק"); shot("17-read");
        click("✓ סיימתי לקרוא את הפרק"); ShadowLooper.idleMainLooper();
        find("נקראו 1 מתוך 150 פרקים"); find("קורא אחד השתתף עד עכשיו");
        assertEquals("done", srv.chapters.get("id0").get(1));
        // choose a chapter from the grid; one that someone else just took is refused politely
        srv.chapters.get("id0").put(3, "claimed");
        click("ג"); ShadowLooper.idleMainLooper();
        find("נקראו 1 מתוך 150 פרקים");
        click("ה"); ShadowLooper.idleMainLooper();
        click("✓ סיימתי לקרוא את הפרק"); ShadowLooper.idleMainLooper();
        find("נקראו 2 מתוך 150 פרקים"); shot("18-progress");
        // finishing while the network is down keeps the reader open
        click("ו"); ShadowLooper.idleMainLooper();
        srv.down = true;
        click("✓ סיימתי לקרוא את הפרק"); ShadowLooper.idleMainLooper();
        find("✓ סיימתי לקרוא את הפרק");
        srv.down = false;
        click("✓ סיימתי לקרוא את הפרק"); ShadowLooper.idleMainLooper();
        find("נקראו 3 מתוך 150 פרקים");
        // back at the list: the reading is under "mine" and in the public list
        a.onBackPressed(); ShadowLooper.idleMainLooper();
        find("הקריאות שלי"); find("נקראו 3 פרקים"); shot("19-list");
        // a reading that does not exist
        a.open(a.new Reading("nosuch", "")); ShadowLooper.idleMainLooper();
        find("הקריאה הזו לא נמצאה. ייתכן שהקישור שגוי.");
        a.onBackPressed(); a.onBackPressed();
        // a full round moves on to the next one
        for (int n = 1; n <= 150; n++) srv.chapters.get("id0").put(n, "done");
        a.open(a.new Reading("id0", "")); ShadowLooper.idleMainLooper();
        find("סבב 2 · נקראו 0 מתוך 150 פרקים");
        // a link that opens the app
        assertEquals("abc123", MainActivity.sharedId(new android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://tfilah.com/y/abc123"))));
        assertNull(MainActivity.sharedId(new android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://tfilah.com/siddur/"))));
        assertNull(MainActivity.sharedId(new android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://evil.example/y/abc123"))));
    }
}
