package org.myassistant.myvoiceassistant;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.SharedPreferences;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.List;

/**
 * Sirf ek kaam: Jarvis ne WhatsApp me message likh kar chat kholi ho (pichle 25 second me),
 * to us chat ka 'Send' button dabana. Event ka intezaar nahi karta - har 400 ms khud dekhta hai.
 * Kya hua, wo prefs 'access_log' me likhta hai (Jarvis Settings me dikhta hai).
 */
public class JarvisAccessService extends AccessibilityService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean polling = false;
    private int tries = 0;
    private SharedPreferences prefs;
    private final SharedPreferences.OnSharedPreferenceChangeListener listener =
            new SharedPreferences.OnSharedPreferenceChangeListener() {
                @Override
                public void onSharedPreferenceChanged(SharedPreferences sp, String key) {
                    if ("access_send_until".equals(key) && sp.getLong(key, 0) > System.currentTimeMillis()) {
                        startPolling();
                    }
                }
            };
    private final Runnable tick = new Runnable() {
        @Override
        public void run() {
            polling = false;
            attempt();
        }
    };

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        prefs = getSharedPreferences("jarvis_prefs", 0);
        prefs.registerOnSharedPreferenceChangeListener(listener);
        log("service chalu");
        if (armed()) {
            startPolling();
        }
    }

    @Override
    public void onDestroy() {
        try {
            if (prefs != null) {
                prefs.unregisterOnSharedPreferenceChangeListener(listener);
            }
        } catch (Exception ignored) {
        }
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }

    private boolean armed() {
        return System.currentTimeMillis() <= getSharedPreferences("jarvis_prefs", 0).getLong("access_send_until", 0);
    }

    private void log(String s) {
        try {
            getSharedPreferences("jarvis_prefs", 0).edit()
                    .putString("access_log", s + " @" + System.currentTimeMillis() / 1000).apply();
        } catch (Exception ignored) {
        }
    }

    private void startPolling() {
        if (!polling) {
            polling = true;
            tries = 0;
            handler.postDelayed(tick, 700);
        }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (armed() && !polling) {
            startPolling();
        }
    }

    private void attempt() {
        if (!armed()) {
            return;
        }
        tries++;
        boolean done = false;
        try {
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root == null) {
                log("window nahi mili (try " + tries + ")");
            } else {
                CharSequence pkg = root.getPackageName();
                if (pkg == null || !pkg.toString().startsWith("com.whatsapp")) {
                    log("WhatsApp samne nahi hai (" + pkg + ")");
                } else {
                    AccessibilityNodeInfo send = find(root);
                    if (send == null) {
                        log("Send button nahi mila (try " + tries + ")");
                    } else if (click(send)) {
                        done = true;
                        log("Send dab gaya");
                    } else if (tap(send)) {
                        done = true;
                        log("Send tap kiya (gesture)");
                    } else {
                        log("Send mila par dab nahi paya");
                    }
                }
            }
        } catch (Exception e) {
            log("error: " + e.getClass().getSimpleName());
        }
        if (done) {
            getSharedPreferences("jarvis_prefs", 0).edit().putLong("access_send_until", 0).apply();
        } else if (armed()) {
            polling = true;
            handler.postDelayed(tick, 400);
        }
    }

    private AccessibilityNodeInfo find(AccessibilityNodeInfo root) {
        String[] ids = {"com.whatsapp:id/send", "com.whatsapp.w4b:id/send"};
        for (String id : ids) {
            List<AccessibilityNodeInfo> l = root.findAccessibilityNodeInfosByViewId(id);
            if (l != null && !l.isEmpty()) {
                return l.get(0);
            }
        }
        return walk(root, 0);
    }

    private AccessibilityNodeInfo walk(AccessibilityNodeInfo n, int depth) {
        if (n == null || depth > 25) {
            return null;
        }
        CharSequence d = n.getContentDescription();
        if (d != null) {
            String t = d.toString().trim();
            if (t.equalsIgnoreCase("send") || t.equals("भेजें") || t.equalsIgnoreCase("send message")) {
                return n;
            }
        }
        String vid = n.getViewIdResourceName();
        if (vid != null && vid.endsWith(":id/send")) {
            return n;
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = walk(n.getChild(i), depth + 1);
            if (r != null) {
                return r;
            }
        }
        return null;
    }

    private boolean click(AccessibilityNodeInfo n) {
        AccessibilityNodeInfo cur = n;
        for (int i = 0; i < 4 && cur != null; i++) {
            if (cur.isClickable() && cur.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                return true;
            }
            cur = cur.getParent();
        }
        return false;
    }

    /** ACTION_CLICK na chale to button ke beech me ungli se tap. */
    private boolean tap(AccessibilityNodeInfo n) {
        if (Build.VERSION.SDK_INT < 24) {
            return false;
        }
        try {
            Rect r = new Rect();
            n.getBoundsInScreen(r);
            if (r.width() <= 0 || r.height() <= 0) {
                return false;
            }
            Path p = new Path();
            p.moveTo(r.centerX(), r.centerY());
            GestureDescription.Builder b = new GestureDescription.Builder();
            b.addStroke(new GestureDescription.StrokeDescription(p, 0, 60));
            return dispatchGesture(b.build(), null, null);
        } catch (Exception e) {
            return false;
        }
    }

    @Override
    public void onInterrupt() {
    }
}
