package com.tfilah.app;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import java.util.Calendar;

/** The two reminders: the daily Psalms, and Friday before Shabbat. Never on Shabbat or Yom Tov. */
public class Remind extends BroadcastReceiver {
    static final String DAILY = "com.tfilah.app.DAILY", FRIDAY = "com.tfilah.app.FRIDAY", CHANNEL = "remind";

    @Override public void onReceive(Context ctx, Intent i) {
        String a = i == null ? null : i.getAction();
        SharedPreferences p = ctx.getSharedPreferences("tf", Context.MODE_PRIVATE);
        long now = System.currentTimeMillis();
        if (DAILY.equals(a) && p.getBoolean("rDaily", false) && !rest(now)) show(ctx, 1, "תהילים יומי", "הפרקים של היום מחכים לכם.", "yomi");
        if (FRIDAY.equals(a) && p.getBoolean("rFri", false) && !rest(now)) show(ctx, 2, "שבת שלום", "זמני כניסת השבת ויציאתה, לפי העיר שלכם.", "shabbat");
        schedule(ctx);   // also after a restart of the phone
    }

    static void schedule(Context ctx) {
        SharedPreferences p = ctx.getSharedPreferences("tf", Context.MODE_PRIVATE);
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        long now = System.currentTimeMillis();
        set(ctx, am, DAILY, 1, p.getBoolean("rDaily", false), next(p.getInt("rDailyAt", 8 * 60), false, now));
        set(ctx, am, FRIDAY, 2, p.getBoolean("rFri", false), next(p.getInt("rFriAt", 13 * 60), true, now));
    }

    static void set(Context ctx, AlarmManager am, String action, int code, boolean on, long at) {
        PendingIntent pi = PendingIntent.getBroadcast(ctx, code, new Intent(ctx, Remind.class).setAction(action), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        am.cancel(pi);
        if (on) am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi);
    }

    /** the next time the clock shows this hour and minute (on a Friday, for the Friday reminder) */
    static long next(int minutes, boolean friday, long now) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(now);
        c.set(Calendar.HOUR_OF_DAY, minutes / 60); c.set(Calendar.MINUTE, minutes % 60); c.set(Calendar.SECOND, 0); c.set(Calendar.MILLISECOND, 0);
        if (c.getTimeInMillis() <= now) c.add(Calendar.DAY_OF_MONTH, 1);
        while (friday && c.get(Calendar.DAY_OF_WEEK) != Calendar.FRIDAY) c.add(Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }

    /** Shabbat or Yom Tov now, with a wide margin: from 15:00 on the day before until 21:00 on the day itself */
    static boolean rest(long t) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(t);
        int h = c.get(Calendar.HOUR_OF_DAY);
        if (holy(c) && h < 21) return true;
        if (h >= 15) { c.add(Calendar.DAY_OF_MONTH, 1); return holy(c); }
        return false;
    }

    /** Shabbat, or a Yom Tov by its Hebrew date (the days kept in the Land of Israel, and both days of Rosh Hashana) */
    static boolean holy(Calendar c) {
        if (c.get(Calendar.DAY_OF_WEEK) == Calendar.SATURDAY) return true;
        if (Build.VERSION.SDK_INT < 24) return false;
        android.icu.util.HebrewCalendar hc = new android.icu.util.HebrewCalendar();
        hc.setTimeInMillis(noon(c));
        int m = hc.get(android.icu.util.Calendar.MONTH), d = hc.get(android.icu.util.Calendar.DAY_OF_MONTH);
        return (m == android.icu.util.HebrewCalendar.TISHRI && (d == 1 || d == 2 || d == 10 || d == 15 || d == 22))
                || (m == android.icu.util.HebrewCalendar.NISAN && (d == 15 || d == 21)) || (m == android.icu.util.HebrewCalendar.SIVAN && d == 6);
    }

    static long noon(Calendar c) { Calendar x = (Calendar) c.clone(); x.set(Calendar.HOUR_OF_DAY, 12); x.set(Calendar.MINUTE, 0); return x.getTimeInMillis(); }

    static void show(Context ctx, int id, String title, String text, String go) {
        if (Build.VERSION.SDK_INT >= 33 && ctx.checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL, "תזכורות", NotificationManager.IMPORTANCE_DEFAULT));
            b = new Notification.Builder(ctx, CHANNEL);
        } else b = new Notification.Builder(ctx);
        PendingIntent open = PendingIntent.getActivity(ctx, id, new Intent(ctx, MainActivity.class).putExtra("go", go).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        nm.notify(id, b.setSmallIcon(R.drawable.ic_note).setColor(0xFF1389D6).setContentTitle(title).setContentText(text).setContentIntent(open).setAutoCancel(true).build());
    }
}
