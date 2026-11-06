package org.myassistant.myvoiceassistant;

import android.app.Notification;
import android.os.Bundle;
import android.os.Parcelable;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

/**
 * Aaye hue notifications padhta hai (sirf message / missed call wale) aur JarvisInbox ko deta hai.
 * Settings > Notification access me 'JARVIS' On karne par hi chalta hai.
 */
public class JarvisNotifService extends NotificationListenerService {

    @Override
    public void onListenerConnected() {
        JarvisInbox.log(this, "notification access chalu");
        try {
            StatusBarNotification[] cur = getActiveNotifications();
            if (cur != null) {
                for (StatusBarNotification s : cur) {
                    handle(s, true);
                }
            }
        } catch (Throwable ignored) {
        }
    }

    @Override
    public void onListenerDisconnected() {
        JarvisInbox.log(this, "notification access toot gaya, dobara jod raha hoon");
        try {
            if (android.os.Build.VERSION.SDK_INT >= 24) {
                requestRebind(new android.content.ComponentName(this, JarvisNotifService.class));
            }
        } catch (Throwable ignored) {
        }
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try {
            handle(sbn, false);
        } catch (Throwable t) {
            JarvisInbox.log(this, "error: " + t.getClass().getSimpleName());
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        try {
            if (sbn != null && (JarvisInbox.appLabel(sbn.getPackageName()) != null
                    || JarvisInbox.isDialer(sbn.getPackageName()))) {
                JarvisInbox.markReadByKey(this, sbn.getKey());
            }
            if (sbn != null && JarvisInbox.isDialer(sbn.getPackageName())) {
                JarvisCallScreen.ended(sbn.getKey());
            }
            if (sbn != null && sbn.getPackageName() != null && sbn.getPackageName().startsWith("com.whatsapp")) {
                JarvisCallAssist.ended(sbn.getKey());
            }
        } catch (Throwable ignored) {
        }
    }

    private static String str(CharSequence c) {
        return c == null ? "" : c.toString().trim();
    }

    private void handle(StatusBarNotification sbn, boolean seed) {
        if (sbn == null) {
            return;
        }
        String pkg = sbn.getPackageName();
        if (getPackageName().equals(pkg)) {
            return;
        }
        if (!seed) {
            try {
                monitor(sbn);
            } catch (Throwable ignored) {
            }
        }
        String label = JarvisInbox.appLabel(pkg);
        boolean dialer = JarvisInbox.isDialer(pkg);
        if (label == null && !dialer) {
            return;
        }
        Notification n = sbn.getNotification();
        if (n == null) {
            return;
        }
        if ((n.flags & Notification.FLAG_GROUP_SUMMARY) != 0 || (n.flags & Notification.FLAG_ONGOING_EVENT) != 0) {
            return;
        }
        String key = sbn.getKey();
        Bundle ex = n.extras;
        if (ex == null) {
            return;
        }
        String title = str(ex.getCharSequence(Notification.EXTRA_TITLE));
        String text = str(ex.getCharSequence(Notification.EXTRA_TEXT));
        String big = str(ex.getCharSequence(Notification.EXTRA_BIG_TEXT));
        if (big.length() > text.length()) {
            text = big;
        }
        String low = (title + " " + text).toLowerCase();
        boolean missed = low.contains("missed") || low.contains("मिस") || low.contains("miss call")
                || (n.category != null && n.category.equals("missed_call"))
                || (android.os.Build.VERSION.SDK_INT >= 26 && n.getChannelId() != null
                        && n.getChannelId().toLowerCase().contains("missed"));
        if (dialer) {
            if (!missed) {
                return;
            }
            addCall(key, pkg, "Phone", title, text, sbn.getPostTime(), seed);
            return;
        }
        if (missed && (low.contains("call") || low.contains("कॉल"))) {
            addCall(key, pkg, label, title, text, sbn.getPostTime(), seed);
            return;
        }
        // "3 new messages" jaisi summary lines chhodo
        if (text.matches("(?i)^\\d+\\s+(new\\s+)?messages?.*") || text.matches("(?i)^checking for new messages.*")
                || text.length() == 0) {
            if (text.length() == 0) {
                return;
            }
        }
        title = title.replaceAll("\\s*\\(\\d+\\s+messages?\\)\\s*$", "");
        boolean group = ex.getBoolean("android.isGroupConversation", false);
        String convTitle = str(ex.getCharSequence("android.conversationTitle"));
        if (convTitle.length() > 0) {
            group = true;                         // group chat (1:1 me conversationTitle nahi hota)
        }
        String chat = convTitle.length() > 0 ? convTitle : title;

        // Reply ka rasta (RemoteInput wala action) yaad rakho
        Notification.Action reply = null;
        if (n.actions != null) {
            for (Notification.Action a : n.actions) {
                if (a != null && a.getRemoteInputs() != null && a.getRemoteInputs().length > 0) {
                    reply = a;
                    break;
                }
            }
        }
        if (reply == null) {
            try {
                for (Notification.Action a : new Notification.WearableExtender(n).getActions()) {
                    if (a != null && a.getRemoteInputs() != null && a.getRemoteInputs().length > 0) {
                        reply = a;
                        break;
                    }
                }
            } catch (Throwable ignored) {
            }
        }
        JarvisInbox.setAction(key, reply);

        boolean fresh = !seed && !JarvisInbox.recentlyReplied(key);
        Parcelable[] msgs = ex.getParcelableArray(Notification.EXTRA_MESSAGES);
        if (msgs != null && msgs.length > 0) {
            long last = JarvisInbox.lastTime(key);
            long maxT = last;
            for (Parcelable pc : msgs) {
                if (!(pc instanceof Bundle)) {
                    continue;
                }
                Bundle b = (Bundle) pc;
                long t = b.getLong("time", 0);
                String mt = str(b.getCharSequence("text"));
                String sender = str(b.getCharSequence("sender"));
                if (mt.length() == 0 || t <= last) {
                    if (mt.length() > 0 && !seed) {
                        JarvisInbox.log(this, "purana samajh kar chhoda: " + cutTxt(mt));
                    }
                    continue;
                }
                maxT = Math.max(maxT, t);
                if (isMe(sender)) {
                    continue;                              // mera apna bheja hua message
                }
                String who = sender.length() > 0 ? sender : title;
                record(key, pkg, label, who, chat, mt, t, group, seed, fresh);
            }
            JarvisInbox.setLastTime(key, maxT);
        } else {
            String prev = JarvisInbox.lastText(key);
            String sig = title + "|" + text;
            if (sig.equals(prev)) {
                return;
            }
            JarvisInbox.setLastText(key, sig);
            if (title.length() == 0 && text.length() == 0) {
                return;
            }
            record(key, pkg, label, title, chat, text, sbn.getPostTime(), group, seed, fresh);
        }
    }

    /** Paise ki khabar (bank SMS / UPI) aur incoming call (call screening) pakdo. */
    private void monitor(StatusBarNotification sbn) {
        Notification n = sbn.getNotification();
        if (n == null || n.extras == null) {
            return;
        }
        Bundle ex = n.extras;
        String pkg = sbn.getPackageName();
        String title = str(ex.getCharSequence(Notification.EXTRA_TITLE));
        String text = str(ex.getCharSequence(Notification.EXTRA_TEXT));
        String big = str(ex.getCharSequence(Notification.EXTRA_BIG_TEXT));
        if (big.length() > text.length()) {
            text = big;
        }
        boolean isCall = "call".equals(n.category);
        if (!isCall && (n.flags & Notification.FLAG_GROUP_SUMMARY) == 0) {
            JarvisSpend.onNotification(this, pkg, title, text, sbn.getPostTime());
        }
        if (isCall && ("com.whatsapp".equals(pkg) || "com.whatsapp.w4b".equals(pkg)) && n.actions != null) {
            Notification.Action ans = null, dec = null, hang = null;
            for (Notification.Action a : n.actions) {
                if (a == null || a.title == null) {
                    continue;
                }
                String t = a.title.toString().toLowerCase();
                if (t.matches(".*(hang\\s*up|end\\s*call|end).*")) {
                    hang = a;
                } else if (t.matches(".*(decline|reject|dismiss|cut|कट|अस्वीकार).*")) {
                    dec = a;
                } else if (t.matches(".*(answer|accept|receive|pick|उत्तर|उठा|स्वीकार).*")) {
                    ans = a;
                }
            }
            if (hang != null) {
                JarvisCallAssist.hangupAct = hang;
            }
            if (ans != null && dec != null) {
                JarvisCallAssist.onIncoming(this, sbn.getKey(), title, text, ans, dec);
            }
        }
        if (isCall && JarvisInbox.isDialer(pkg) && n.actions != null) {
            Notification.Action ans = null, dec = null;
            for (Notification.Action a : n.actions) {
                if (a == null || a.title == null) {
                    continue;
                }
                String t = a.title.toString().toLowerCase();
                if (t.matches(".*(decline|reject|dismiss|cut|कट|अस्वीकार).*")) {
                    dec = a;
                } else if (t.matches(".*(answer|accept|receive|pick|उत्तर|उठा|स्वीकार).*")) {
                    ans = a;
                }
            }
            if (ans != null && dec != null) {
                JarvisCallScreen.onIncoming(this, sbn.getKey(), title, text, ans, dec);
            }
        }
    }

    private static String cutTxt(String t) {
        return t.length() > 18 ? t.substring(0, 18) : t;
    }

    private static boolean isMe(String s) {
        String l = s.toLowerCase();
        return l.equals("you") || l.equals("me") || l.equals("आप") || l.equals("मैं") || l.equals("aap");
    }

    private void addCall(String key, String pkg, String app, String title, String text, long time, boolean seed) {
        String sig = title + "|" + text;
        if (sig.equals(JarvisInbox.lastText(key))) {
            return;
        }
        JarvisInbox.setLastText(key, sig);
        JarvisInbox.Item it = new JarvisInbox.Item();
        it.key = key;
        it.pkg = pkg;
        it.app = app;
        it.kind = "call";
        it.sender = title;
        it.chat = title;
        it.text = text;
        it.time = time;
        JarvisInbox.add(this, it);
    }

    private void record(String key, String pkg, String label, String sender, String chat, String text, long t,
                        boolean group, boolean seed, boolean fresh) {
        JarvisInbox.Item it = new JarvisInbox.Item();
        it.key = key;
        it.pkg = pkg;
        it.app = label;
        it.sender = sender;
        it.chat = chat;
        it.text = text;
        it.time = t > 0 ? t : System.currentTimeMillis();
        it.group = group;
        JarvisInbox.add(this, it);
        JarvisInbox.log(this, "message mila: " + sender);
        if (fresh) {
            JarvisInbox.onNew(this, it);
        }
    }
}
