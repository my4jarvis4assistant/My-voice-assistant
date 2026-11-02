package org.myassistant.myvoiceassistant;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.SharedPreferences;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONObject;

import java.util.ArrayList;
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
                    if ("ui_task".equals(key) && sp.getString(key, "").length() > 0) {
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
        return System.currentTimeMillis() <= getSharedPreferences("jarvis_prefs", 0).getLong("access_send_until", 0)
                || uiActive();
    }

    // ---------------------------------------------------------------- WhatsApp ke andar naam se dhundhna --
    private String uiKind = "", uiName = "", uiBody = "";
    private long uiUntil = 0, uiStageAt = 0, uiId = 0;
    private int uiStage = 0, uiBacks = 0;
    private boolean uiTriedFirst = false;

    private boolean uiActive() {
        loadUi();
        return uiKind.length() > 0 && System.currentTimeMillis() <= uiUntil;
    }

    private void loadUi() {
        try {
            String raw = getSharedPreferences("jarvis_prefs", 0).getString("ui_task", "");
            if (raw.length() == 0) {
                uiKind = "";
                return;
            }
            JSONObject o = new JSONObject(raw);
            long id = o.optLong("id", 0);
            if (id != uiId) {                       // naya kaam: shuru se
                uiId = id;
                uiStage = 0;
                uiBacks = 0;
                uiTriedFirst = false;
                uiStageAt = System.currentTimeMillis();
            }
            uiKind = o.optString("kind", "");
            uiName = o.optString("name", "");
            uiBody = o.optString("body", "");
            uiUntil = o.optLong("until", 0);
        } catch (Exception e) {
            uiKind = "";
        }
    }

    private void uiEnd(String why) {
        log(why);
        getSharedPreferences("jarvis_prefs", 0).edit().putString("ui_task", "")
                .putString("ui_result", why).apply();
        uiKind = "";
        final String msg = why;
        handler.post(new Runnable() {
            @Override
            public void run() {
                try {
                    android.widget.Toast.makeText(JarvisAccessService.this, msg, android.widget.Toast.LENGTH_LONG).show();
                } catch (Exception ignored) {
                }
            }
        });
    }

    private long uiBackAt = 0, uiTypedAt = 0;

    /** Chat ke upar ka naam (jis se baat ho rahi hai) uiName se milta hai ya nahi. */
    private boolean chatTitleMatches(AccessibilityNodeInfo root) {
        AccessibilityNodeInfo t = byId(root, "conversation_contact_name");
        if (t != null && t.getText() != null) {
            return JarvisContactMatch.score(uiName, t.getText().toString()) >= 0.7;
        }
        int h = getResources().getDisplayMetrics().heightPixels;
        List<AccessibilityNodeInfo> texts = new ArrayList<AccessibilityNodeInfo>();
        collectTexts(root, texts, 0);
        for (AccessibilityNodeInfo n : texts) {
            Rect r = new Rect();
            n.getBoundsInScreen(r);
            if (r.top < h * 0.22 && !n.isEditable() && n.getText() != null
                    && JarvisContactMatch.score(uiName, n.getText().toString()) >= 0.7) {
                return true;
            }
        }
        return false;
    }

    private void uiBack(long now, String why) {
        if (now - uiBackAt > 900) {
            uiBackAt = now;
            performGlobalAction(GLOBAL_ACTION_BACK);
            log("peeche ja raha hoon (" + why + ")");
        }
    }

    /** Screen dekhkar faisla: jahan bhi WhatsApp khula ho (list, purani chat, search) wahin se aage badho. */
    private void uiStep(AccessibilityNodeInfo root) {
        long now = System.currentTimeMillis();
        long inStage = now - uiStageAt;
        if (uiStage == 4) {                                   // message likha hai, Send dabao
            if (inStage < 400) {
                return;
            }
            AccessibilityNodeInfo send = find(root);
            if (send != null && (click(send) || tap(send))) {
                uiEnd("Message bhej diya");
            } else if (inStage > 2500 && tapBesideEntry(root)) {
                uiEnd("Message bhej diya");
            } else if (inStage > 7000) {
                uiEnd("Send nahi dab paya");
            }
            return;
        }
        if (uiStage == 5) {                                   // call ki pushti wala dabba aaye to 'Call' dabao
            AccessibilityNodeInfo ok = byText(root, "call");
            if (ok == null) {
                ok = byText(root, "voice call");
            }
            if (ok != null && ok.isClickable()) {
                click(ok);
            }
            if (inStage > 2500) {
                uiEnd("Call laga raha hoon");
            }
            return;
        }
        if (now - uiStageAt > 40000) {
            uiEnd("WhatsApp me " + uiName + " tak nahi pahunch paya");
            return;
        }
        AccessibilityNodeInfo entry = byId(root, "entry");
        if (entry != null) {                                  // koi chat khuli hai
            if (!chatTitleMatches(root)) {
                uiBack(now, "galat chat");
                return;
            }
            if (uiKind.equals("message")) {
                Bundle b = new Bundle();
                b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, uiBody);
                entry.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
                if (entry.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, b)) {
                    uiStage = 4;
                    uiStageAt = now;
                    log("message likha");
                }
                return;
            }
            String want = uiKind.equals("video") ? "video call" : "voice call";
            AccessibilityNodeInfo callBtn = byDesc(root, want);
            if (callBtn == null && uiKind.equals("call")) {
                callBtn = byDesc(root, "audio call");
            }
            if (callBtn != null && click(callBtn)) {
                uiStage = 5;
                uiStageAt = now;
                log("call dabaya");
            }
            return;
        }
        AccessibilityNodeInfo field = byId(root, "search_src_text");
        if (field == null) {
            field = firstEdit(root);                          // nayi WhatsApp me search ka dabba alag naam ka ho sakta hai
        }
        if (field != null) {                                  // search khula hai
            String q = uiName;
            if (uiTriedFirst) {
                String[] t = uiName.trim().split("\\s+");
                q = t.length > 0 ? t[0] : uiName;
            }
            String cur = field.getText() == null ? "" : field.getText().toString();
            if (!cur.equalsIgnoreCase(q)) {
                Bundle b = new Bundle();
                b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, q);
                field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
                if (field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, b)) {
                    uiTypedAt = now;
                    log("naam likha: " + q);
                }
                return;
            }
            if (now - uiTypedAt < 1300) {
                return;
            }
            int h = getResources().getDisplayMetrics().heightPixels;
            List<AccessibilityNodeInfo> texts = new ArrayList<AccessibilityNodeInfo>();
            collectTexts(root, texts, 0);
            AccessibilityNodeInfo best = null;
            double bestScore = 0;
            for (AccessibilityNodeInfo n : texts) {
                CharSequence t = n.getText();
                if (t == null || n.isEditable()) {
                    continue;
                }
                Rect r = new Rect();
                n.getBoundsInScreen(r);
                if (r.top < h * 0.12) {
                    continue;                                 // upar ka search-bar / title chhodo
                }
                String tx = t.toString().trim();
                if (tx.length() == 0 || tx.length() > 60) {
                    continue;
                }
                double sc = JarvisContactMatch.score(uiName, tx);
                if (sc > bestScore) {
                    bestScore = sc;
                    best = n;
                }
            }
            if (best != null && bestScore >= 0.7) {
                if (click(best)) {
                    log("chuna: " + best.getText());
                    uiTypedAt = now + 3000;                   // chat khulne ka intezaar
                }
            } else if (now - uiTypedAt > 4500) {
                String[] t = uiName.trim().split("\\s+");
                if (!uiTriedFirst && t.length > 1) {
                    uiTriedFirst = true;
                } else {
                    uiEnd(uiName + " naam WhatsApp me nahi mila");
                }
            }
            return;
        }
        AccessibilityNodeInfo search = byId(root, "menuitem_search");
        if (search == null) {
            search = byDesc(root, "search");
        }
        if (search != null && click(search)) {
            log("search khola");
            return;
        }
        uiBack(now, "list dhundh raha hoon");
    }

    private AccessibilityNodeInfo byId(AccessibilityNodeInfo root, String shortId) {
        String[] pk = {"com.whatsapp:id/", "com.whatsapp.w4b:id/"};
        for (String p : pk) {
            List<AccessibilityNodeInfo> l = root.findAccessibilityNodeInfosByViewId(p + shortId);
            if (l != null && !l.isEmpty()) {
                return l.get(0);
            }
        }
        return null;
    }

    private AccessibilityNodeInfo byDesc(AccessibilityNodeInfo n, String contains) {
        if (n == null) {
            return null;
        }
        CharSequence d = n.getContentDescription();
        if (d != null && d.toString().toLowerCase().contains(contains)) {
            return n;
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = byDesc(n.getChild(i), contains);
            if (r != null) {
                return r;
            }
        }
        return null;
    }

    private AccessibilityNodeInfo byText(AccessibilityNodeInfo root, String exact) {
        List<AccessibilityNodeInfo> l = root.findAccessibilityNodeInfosByText(exact);
        if (l != null) {
            for (AccessibilityNodeInfo n : l) {
                CharSequence t = n.getText();
                if (t != null && t.toString().trim().equalsIgnoreCase(exact)) {
                    return n;
                }
            }
        }
        return null;
    }

    private AccessibilityNodeInfo firstEdit(AccessibilityNodeInfo n) {
        if (n == null) {
            return null;
        }
        if (n.isEditable() || "android.widget.EditText".contentEquals(n.getClassName() == null ? "" : n.getClassName())) {
            return n;
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = firstEdit(n.getChild(i));
            if (r != null) {
                return r;
            }
        }
        return null;
    }

    private void collectTexts(AccessibilityNodeInfo n, List<AccessibilityNodeInfo> out, int depth) {
        if (n == null || depth > 25) {
            return;
        }
        if (n.getText() != null && n.getText().length() > 0) {
            out.add(n);
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            collectTexts(n.getChild(i), out, depth + 1);
        }
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
        if (uiActive()) {
            try {
                AccessibilityNodeInfo r = getRootInActiveWindow();
                CharSequence pk = r == null ? null : r.getPackageName();
                if (r != null && pk != null && pk.toString().startsWith("com.whatsapp")) {
                    uiStep(r);
                } else if (System.currentTimeMillis() - uiStageAt > 15000) {
                    uiEnd("WhatsApp samne nahi aaya");
                }
            } catch (Exception e) {
                log("ui error: " + e.getClass().getSimpleName());
            }
            if (uiActive()) {
                polling = true;
                handler.postDelayed(tick, 450);
            }
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
                        if (tries >= 5 && tapBesideEntry(root)) {
                            done = true;
                            log("Send tap kiya (text-box ke bagal)");
                        } else {
                            log("Send button nahi mila (try " + tries + ")");
                        }
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

    /** Send ka button dhundh na paye to: message likha ho to text-box ke theek dayein bagal (Send ki jagah) tap. */
    private boolean tapBesideEntry(AccessibilityNodeInfo root) {
        if (Build.VERSION.SDK_INT < 24) {
            return false;
        }
        try {
            AccessibilityNodeInfo entry = byId(root, "entry");
            if (entry == null || entry.getText() == null || entry.getText().toString().trim().length() == 0) {
                return false;
            }
            Rect r = new Rect();
            entry.getBoundsInScreen(r);
            int w = getResources().getDisplayMetrics().widthPixels;
            Path p = new Path();
            p.moveTo(w - w * 0.075f, r.centerY());
            GestureDescription.Builder b = new GestureDescription.Builder();
            b.addStroke(new GestureDescription.StrokeDescription(p, 0, 60));
            return dispatchGesture(b.build(), null, null);
        } catch (Exception e) {
            return false;
        }
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
