package org.myassistant.myvoiceassistant;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.List;

/**
 * Sirf ek kaam: Jarvis ne WhatsApp me message likh kar chat kholi ho (pichle 25 second me),
 * to us chat ka 'Send' button dabana. Aur kuch nahi padhta ya karta. Settings > Accessibility me
 * 'JARVIS auto-send' On karne par hi chalti hai.
 */
public class JarvisAccessService extends AccessibilityService {
    private long lastTry = 0;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        try {
            long now = System.currentTimeMillis();
            long until = getSharedPreferences("jarvis_prefs", 0).getLong("access_send_until", 0);
            if (now > until || now - lastTry < 400) {
                return;
            }
            lastTry = now;
            AccessibilityNodeInfo root = getRootInActiveWindow();
            if (root == null) {
                return;
            }
            AccessibilityNodeInfo send = find(root);
            if (send != null && click(send)) {
                getSharedPreferences("jarvis_prefs", 0).edit().putLong("access_send_until", 0).apply();
            }
        } catch (Exception ignored) {
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
        String[] labels = {"Send", "भेजें"};
        for (String label : labels) {
            List<AccessibilityNodeInfo> l = root.findAccessibilityNodeInfosByText(label);
            if (l != null) {
                for (AccessibilityNodeInfo n : l) {
                    CharSequence d = n.getContentDescription();
                    if (d != null && d.toString().equalsIgnoreCase(label)) {
                        return n;
                    }
                }
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

    @Override
    public void onInterrupt() {
    }
}
