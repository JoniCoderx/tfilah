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
    }
}
