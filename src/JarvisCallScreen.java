package org.myassistant.myvoiceassistant;

import android.app.Notification;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.telephony.SmsManager;

/**
 * Call screening: anjaan number se call ring hone par Jarvis bolkar batata hai, aur aap bolte ho
 * "kaat do" / "busy hu" (call kaatkar SMS) / "utha lo". Call notification ke Answer/Decline buttons dabakar kaam hota hai,
 * isliye koi khaas permission nahi chahiye; sirf busy SMS ke liye SEND_SMS chahiye.
 */
public final class JarvisCallScreen {
    private JarvisCallScreen() {
    }

    private static final String PREF = "jarvis_callscreen";
    static volatile Notification.Action answerAct, declineAct;
    static volatile String curKey = "", curNumber = "";
    private static volatile String lastKey = "";
    private static volatile long lastAt = 0;

    public static boolean enabled(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE).getString("on", "").length() > 0;
    }

    public static void setEnabled(Context c, boolean on) {
        SharedPreferences.Editor e = c.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit();
        if (on) {
            e.putString("on", "1");
        } else {
            e.remove("on");
        }
        e.apply();
    }

    /** Dialer ka incoming-call notification aaya (Answer + Decline dono buttons ke saath). */
    public static void onIncoming(Context c, String key, String title, String text,
                                  Notification.Action answer, Notification.Action decline) {
        try {
            if (!enabled(c)) {
                return;
            }
            if (!JarvisCallWords.isNumberLike(title)) {
                return;                                    // saved contact ka call: chup raho
            }
            long now = System.currentTimeMillis();
            if (key.equals(lastKey) && now - lastAt < 60000L) {
                return;                                    // ring ke dauraan notification baar baar update hota hai
            }
            lastKey = key;
            lastAt = now;
            answerAct = answer;
            declineAct = decline;
            curKey = key;
            curNumber = JarvisCallWords.extractNumber(title) == null ? "" : JarvisCallWords.extractNumber(title);
            String say = "Anjaan number se call aa raha hai: " + JarvisCallWords.speakNumber(title) + ". "
                    + (JarvisCallWords.spamHint(text) ? "Ye spam ho sakta hai. " : "")
                    + "Kaat doon, busy bolkar message bhej doon, ya utha lo?";
            JarvisInbox.log(c, "anjaan call: screening bola");
            JarvisOverlayService.callAsk(c, key, say);
        } catch (Throwable ignored) {
        }
    }

    public static void ended(String key) {
        try {
            if (key != null && key.equals(curKey)) {
                JarvisOverlayService.callEnded(key);
                curKey = "";
            }
        } catch (Throwable ignored) {
        }
    }

    private static boolean fire(Notification.Action a) {
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

    public static boolean decline() {
        return fire(declineAct);
    }

    public static boolean answer() {
        return fire(answerAct);
    }

    /** 0 = bhej diya, 1 = SMS permission nahi, 2 = number nahi mila, 3 = bhej nahi paya. */
    public static int sendBusySms(Context c, String text) {
        if (curNumber.length() < 7) {
            return 2;
        }
        try {
            if (Build.VERSION.SDK_INT >= 23
                    && c.checkSelfPermission(android.Manifest.permission.SEND_SMS)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                return 1;
            }
            SmsManager sm = SmsManager.getDefault();
            sm.sendMultipartTextMessage(curNumber, null, sm.divideMessage(text), null, null);
            return 0;
        } catch (Throwable t) {
            return 3;
        }
    }
}
