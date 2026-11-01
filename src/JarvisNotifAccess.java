package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.provider.Settings;

/** Notification access On hai ya nahi. */
public final class JarvisNotifAccess {
    private JarvisNotifAccess() {
    }

    public static boolean enabled(Context c) {
        try {
            String v = Settings.Secure.getString(c.getContentResolver(), "enabled_notification_listeners");
            return v != null && v.contains("JarvisNotifService");
        } catch (Exception e) {
            return false;
        }
    }
}
