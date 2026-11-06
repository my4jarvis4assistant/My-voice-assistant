package org.myassistant.myvoiceassistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;

/**
 * Call assistant (experimental): aap busy ho aur WhatsApp voice call aaye to kuch der ringing ke baad Jarvis call utha kar
 * speakerphone par baat karta hai, aapka haal batata hai aur sandesh leta hai. Video call nahi uthata.
 * Baat ka hisaab yahan jama hota hai.
 */
public final class JarvisCallAssist {
    private JarvisCallAssist() {
    }

    private static final String PREF = "jarvis_assist";
    static volatile Notification.Action answerAct, declineAct, hangupAct;
    static volatile String pendingKey = "";
    private static volatile String lastKey = "";
    private static volatile long lastAt = 0;

    private static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public static boolean enabled(Context c) {
        return sp(c).getString("on", "").length() > 0;
    }

    public static void setEnabled(Context c, boolean on, String status) {
        SharedPreferences.Editor e = sp(c).edit();
        if (on) {
            e.putString("on", "1");
            if (status != null && status.trim().length() > 0) {
                e.putString("status", status.trim());
            }
        } else {
            e.remove("on");
        }
        e.apply();
    }

    /** Caller ko batane layak haal (teesre insaan me). */
    public static String statusText(Context c) {
        String s = sp(c).getString("status", "");
        if (s.length() == 0) {
            String busy = null;
            try {
                busy = JarvisStyle.busyReason(c);
            } catch (Throwable ignored) {
            }
            s = busy == null ? "" : busy;
        }
        String t = JarvisCallWords.thirdPerson(s);
        return t.length() == 0 ? "abhi call nahi utha sakte" : t;
    }

    /** WhatsApp ka incoming call notification (Answer + Decline buttons ke saath). */
    public static void onIncoming(Context c, String key, String title, String text,
                                  Notification.Action answer, Notification.Action decline) {
        try {
            if (!enabled(c)) {
                return;
            }
            long now = System.currentTimeMillis();
            if (key.equals(lastKey) && now - lastAt < 60000L) {
                return;                                    // ring ke dauraan notification baar baar update hota hai
            }
            lastKey = key;
            lastAt = now;
            if (!JarvisOverlayService.running()) {
                JarvisInbox.log(c, "call assistant: Jarvis service chal nahi rahi, call nahi uthaya");
                return;
            }
            String low = (title + " " + text).toLowerCase(Locale.ENGLISH);
            answerAct = answer;
            declineAct = decline;
            if (low.contains("video") || low.contains("वीडियो")) {
                JarvisInbox.log(c, "call assistant: video call, kaat diya");
                fire(decline);
                JarvisOverlayService.assistVideoMessage(c, title);
                return;
            }
            pendingKey = key;
            JarvisInbox.log(c, "call assistant: " + title + " ka call, kuch der baad uthaunga");
            JarvisOverlayService.assistRing(c, key, title);
        } catch (Throwable ignored) {
        }
    }

    public static void ended(String key) {
        try {
            if (key != null && key.equals(pendingKey)) {
                pendingKey = "";              // aapne khud utha liya ya caller ne kaat diya
            }
        } catch (Throwable ignored) {
        }
    }

    static boolean fire(Notification.Action a) {
        try {
            if (a == null || a.actionIntent == null) {
                return false;
            }
            a.actionIntent.send();
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    public static boolean answer() {
        return fire(answerAct);
    }

    /** Call kaato: notification ka Hang up button, ya screen ka End call button. */
    public static boolean hangup() {
        if (fire(hangupAct)) {
            return true;
        }
        JarvisAccessService svc = JarvisAccessService.instance;
        if (svc == null) {
            return false;
        }
        return svc.clickLabel("end call", 0.8) || svc.clickLabel("hang up", 0.8) || svc.clickLabel("leave call", 0.8);
    }

    public static boolean speakerOn() {
        JarvisAccessService svc = JarvisAccessService.instance;
        if (svc == null) {
            return false;
        }
        return svc.clickLabel("speaker", 0.8) || svc.clickLabel("speakerphone", 0.8);
    }

    // ------------------------------------------------------------------ hisaab --
    public static synchronized void addLog(Context c, String name, String said) {
        try {
            String t = said == null ? "" : said.trim();
            if (t.length() > 280) {
                t = t.substring(0, 280);
            }
            String when = new SimpleDateFormat("d MMM, h:mm a", Locale.ENGLISH).format(new Date());
            String line = when + "|" + name.replace("|", " ") + "|" + (t.length() == 0 ? "kuch nahi bola" : t.replace("|", " "));
            List<String> all = readLog(c);
            all.add(line);
            while (all.size() > 20) {
                all.remove(0);
            }
            JSONArray a = new JSONArray();
            for (String s : all) {
                a.put(s);
            }
            sp(c).edit().putString("log", a.toString()).apply();
            notifySummary(c, name, t.length() == 0 ? "kuch nahi bola" : t);
        } catch (Throwable ignored) {
        }
    }

    public static synchronized List<String> readLog(Context c) {
        List<String> out = new ArrayList<String>();
        try {
            JSONArray a = new JSONArray(sp(c).getString("log", "[]"));
            for (int i = 0; i < a.length(); i++) {
                out.add(a.optString(i, ""));
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    /** Sunane layak: pichli teen baat-cheet. */
    public static String speakLog(Context c) {
        List<String> all = readLog(c);
        if (all.isEmpty()) {
            return "Abhi tak maine koi call nahi uthaya.";
        }
        StringBuilder sb = new StringBuilder();
        int from = Math.max(0, all.size() - 3);
        for (int i = all.size() - 1; i >= from; i--) {
            String[] p = all.get(i).split("\\|", 3);
            if (p.length < 3) {
                continue;
            }
            sb.append(p[0]).append(" ko ").append(p[1]).append(" ka call aaya tha, unhone kaha: ").append(p[2]).append(". ");
        }
        return sb.toString().trim();
    }

    private static void notifySummary(Context c, String name, String said) {
        try {
            NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
            Notification.Builder nb;
            if (Build.VERSION.SDK_INT >= 26) {
                nm.createNotificationChannel(new NotificationChannel("jarvis_ask", "Jarvis sawaal",
                        NotificationManager.IMPORTANCE_HIGH));
                nb = new Notification.Builder(c, "jarvis_ask");
            } else {
                nb = new Notification.Builder(c);
            }
            nb.setSmallIcon(android.R.drawable.ic_menu_call)
                    .setContentTitle(name + " ka call (Jarvis ne uthaya)")
                    .setContentText(said)
                    .setStyle(new Notification.BigTextStyle().bigText(said))
                    .setAutoCancel(true);
            nm.notify(4713, nb.build());
        } catch (Throwable ignored) {
        }
    }
}
