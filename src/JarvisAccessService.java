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

    static volatile JarvisAccessService instance = null;

    /** Control ka kaam der se (baad me) fail ho to bolne ke liye (JarvisOverlayService lagati hai). */
    public interface Say {
        void say(String msg);
    }

    static volatile Say sayHook = null;

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        prefs = getSharedPreferences("jarvis_prefs", 0);
        prefs.registerOnSharedPreferenceChangeListener(listener);
        log("service chalu");
        beat.run();
        if (armed()) {
            startPolling();
        }
    }

    /** Har 4 second "main zinda hoon" likhti hai, taaki Jarvis jaan sake ki service sach me chal rahi hai. */
    private final Runnable beat = new Runnable() {
        @Override
        public void run() {
            try {
                getSharedPreferences("jarvis_prefs", 0).edit()
                        .putLong("access_alive", System.currentTimeMillis()).apply();
            } catch (Exception ignored) {
            }
            handler.postDelayed(this, 4000);
        }
    };

    @Override
    public boolean onUnbind(android.content.Intent intent) {
        instance = null;
        return super.onUnbind(intent);
    }

    @Override
    public void onDestroy() {
        instance = null;
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


    // ======================================================================= Voice-Access jaisa control ==
    private static final class Entry {
        AccessibilityNodeInfo node;
        String label;
        double w;           // label ka bharosa (viewId ka kam)
    }

    private static final int MAX_NODES = 2500;

    private AccessibilityNodeInfo activeRoot() {
        AccessibilityNodeInfo r = getRootInActiveWindow();
        if (r != null && !getPackageName().contentEquals(r.getPackageName() == null ? "" : r.getPackageName())) {
            return r;
        }
        try {
            List<android.view.accessibility.AccessibilityWindowInfo> ws = getWindows();
            AccessibilityNodeInfo best = null;
            int layer = -1;
            for (android.view.accessibility.AccessibilityWindowInfo w : ws) {
                AccessibilityNodeInfo wr = w.getRoot();
                if (wr == null || getPackageName().contentEquals(wr.getPackageName() == null ? "" : wr.getPackageName())) {
                    continue;
                }
                if (w.getType() == android.view.accessibility.AccessibilityWindowInfo.TYPE_APPLICATION
                        && w.getLayer() > layer) {
                    layer = w.getLayer();
                    best = wr;
                }
            }
            if (best != null) {
                return best;
            }
        } catch (Throwable ignored) {
        }
        return r;
    }

    private void gather(AccessibilityNodeInfo n, List<Entry> out, int[] count, int depth) {
        if (n == null || depth > 45 || count[0] > MAX_NODES) {
            return;
        }
        count[0]++;
        if (n.isVisibleToUser()) {
            CharSequence t = n.getText();
            CharSequence d = n.getContentDescription();
            CharSequence h = Build.VERSION.SDK_INT >= 26 ? n.getHintText() : null;
            if (t != null && t.length() > 0 && !n.isPassword()) {
                add(out, n, t.toString(), 1.0);
            }
            if (d != null && d.length() > 0) {
                add(out, n, d.toString(), 1.0);
            }
            if (h != null && h.length() > 0) {
                add(out, n, h.toString(), 0.97);
            }
            String vid = n.getViewIdResourceName();
            if (vid != null && vid.contains("/")) {
                add(out, n, vid.substring(vid.indexOf('/') + 1).replace('_', ' '), 0.85);
            }
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            gather(n.getChild(i), out, count, depth + 1);
        }
    }

    private void add(List<Entry> out, AccessibilityNodeInfo n, String label, double w) {
        Entry e = new Entry();
        e.node = n;
        e.label = label;
        e.w = w;
        out.add(e);
    }

    private List<Entry> screen() {
        List<Entry> out = new ArrayList<Entry>();
        AccessibilityNodeInfo r = activeRoot();
        if (r != null) {
            gather(r, out, new int[]{0}, 0);
        }
        return out;
    }

    private boolean clickable(AccessibilityNodeInfo n) {
        AccessibilityNodeInfo c = n;
        for (int i = 0; i < 6 && c != null; i++) {
            if (c.isClickable()) {
                return true;
            }
            c = c.getParent();
        }
        return false;
    }

    /** Bole hue naam se sabse milta screen ka hissa (None = nahi mila). */
    private AccessibilityNodeInfo findTarget(String target, double min) {
        AccessibilityNodeInfo best = null;
        double bs = 0;
        int bt = Integer.MAX_VALUE, bl = Integer.MAX_VALUE;
        for (Entry e : screen()) {
            double sc = JarvisControl.match(target, e.label) * e.w;
            if (sc < min) {
                continue;
            }
            if (clickable(e.node)) {
                sc += 0.015;
            }
            Rect r = new Rect();
            e.node.getBoundsInScreen(r);
            if (sc > bs + 0.0001 || (Math.abs(sc - bs) <= 0.0001 && (r.top < bt || (r.top == bt && r.left < bl)))) {
                bs = sc;
                best = e.node;
                bt = r.top;
                bl = r.left;
            }
        }
        return best;
    }

    private boolean doClick(AccessibilityNodeInfo n, boolean longPress) {
        AccessibilityNodeInfo c = n;
        for (int i = 0; i < 6 && c != null; i++) {
            if (longPress ? c.isLongClickable() : c.isClickable()) {
                if (c.performAction(longPress ? AccessibilityNodeInfo.ACTION_LONG_CLICK
                        : AccessibilityNodeInfo.ACTION_CLICK)) {
                    return true;
                }
            }
            c = c.getParent();
        }
        return gestureAt(n, longPress ? 700 : 60);
    }

    private boolean gestureAt(AccessibilityNodeInfo n, int ms) {
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
            b.addStroke(new GestureDescription.StrokeDescription(p, 0, ms));
            return dispatchGesture(b.build(), null, null);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean swipe(float x1, float y1, float x2, float y2) {
        if (Build.VERSION.SDK_INT < 24) {
            return false;
        }
        try {
            Path p = new Path();
            p.moveTo(x1, y1);
            p.lineTo(x2, y2);
            GestureDescription.Builder b = new GestureDescription.Builder();
            b.addStroke(new GestureDescription.StrokeDescription(p, 0, 320));
            return dispatchGesture(b.build(), null, null);
        } catch (Exception e) {
            return false;
        }
    }

    private AccessibilityNodeInfo scrollable(AccessibilityNodeInfo n, int depth, AccessibilityNodeInfo[] best, long[] area) {
        if (n == null || depth > 40) {
            return null;
        }
        if (n.isScrollable() && n.isVisibleToUser()) {
            Rect r = new Rect();
            n.getBoundsInScreen(r);
            long a = (long) r.width() * r.height();
            if (a > area[0]) {
                area[0] = a;
                best[0] = n;
            }
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            scrollable(n.getChild(i), depth + 1, best, area);
        }
        return best[0];
    }

    private void scrollOnce(String dir) {
        int w = getResources().getDisplayMetrics().widthPixels;
        int h = getResources().getDisplayMetrics().heightPixels;
        boolean vertical = dir.equals("up") || dir.equals("down");
        if (vertical) {
            AccessibilityNodeInfo r = activeRoot();
            AccessibilityNodeInfo sc = r == null ? null : scrollable(r, 0, new AccessibilityNodeInfo[1], new long[1]);
            if (sc != null && sc.performAction(dir.equals("down") ? AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
                    : AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)) {
                return;
            }
            if (dir.equals("down")) {
                swipe(w / 2f, h * 0.72f, w / 2f, h * 0.28f);
            } else {
                swipe(w / 2f, h * 0.28f, w / 2f, h * 0.72f);
            }
        } else if (dir.equals("left")) {
            swipe(w * 0.8f, h / 2f, w * 0.2f, h / 2f);
        } else {
            swipe(w * 0.2f, h / 2f, w * 0.8f, h / 2f);
        }
    }

    private void editables(AccessibilityNodeInfo n, List<AccessibilityNodeInfo> out, int depth) {
        if (n == null || depth > 45 || out.size() > 30) {
            return;
        }
        if (n.isEditable() && n.isVisibleToUser()) {
            out.add(n);
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            editables(n.getChild(i), out, depth + 1);
        }
    }

    private String hintOf(AccessibilityNodeInfo n) {
        StringBuilder sb = new StringBuilder();
        if (Build.VERSION.SDK_INT >= 26 && n.getHintText() != null) {
            sb.append(n.getHintText()).append(' ');
        }
        if (n.getContentDescription() != null) {
            sb.append(n.getContentDescription()).append(' ');
        }
        if (n.getText() != null && (Build.VERSION.SDK_INT < 26 || n.isShowingHintText())) {
            sb.append(n.getText());
        }
        String vid = n.getViewIdResourceName();
        if (vid != null && vid.contains("/")) {
            sb.append(' ').append(vid.substring(vid.indexOf('/') + 1).replace('_', ' '));
        }
        return sb.toString();
    }

    /** Text likhne ki jagah chuno: naam se, ya jis par cursor hai, ya "message" likha ho, warna pehli. */
    private AccessibilityNodeInfo pickEditable(String hintTarget) {
        AccessibilityNodeInfo r = activeRoot();
        if (r == null) {
            return null;
        }
        List<AccessibilityNodeInfo> list = new ArrayList<AccessibilityNodeInfo>();
        editables(r, list, 0);
        if (list.isEmpty()) {
            return null;
        }
        if (hintTarget != null && hintTarget.length() > 0) {
            AccessibilityNodeInfo b = null;
            double bs = 0;
            for (AccessibilityNodeInfo e : list) {
                double sc = JarvisControl.match(hintTarget, hintOf(e));
                if (sc > bs) {
                    bs = sc;
                    b = e;
                }
            }
            if (b != null && bs >= 0.8) {
                return b;
            }
        }
        AccessibilityNodeInfo f = r.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
        if (f != null && f.isEditable()) {
            return f;
        }
        for (AccessibilityNodeInfo e : list) {
            String h = hintOf(e).toLowerCase(java.util.Locale.ENGLISH);
            if (h.contains("message") || h.contains("type") || h.contains("write") || h.contains("reply")
                    || h.contains("comment")) {
                return e;
            }
        }
        return list.get(0);
    }

    private boolean typeInto(AccessibilityNodeInfo e, String text) {
        String base = "";
        CharSequence cur = e.getText();
        boolean hint = Build.VERSION.SDK_INT >= 26 && e.isShowingHintText();
        if (cur != null && !hint) {
            base = cur.toString();
        }
        String nw = base.length() == 0 ? text : (base.endsWith(" ") ? base + text : base + " " + text);
        Bundle b = new Bundle();
        b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, nw);
        e.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
        return e.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, b);
    }

    private boolean imeEnter(AccessibilityNodeInfo e) {
        if (Build.VERSION.SDK_INT < 30 || e == null) {
            return false;
        }
        try {
            return e.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_IME_ENTER.getId());
        } catch (Throwable t) {
            return false;
        }
    }

    private void tellLater(final String msg) {
        Say s = sayHook;
        if (s != null) {
            s.say(msg);
        }
    }

    /** Type karna (kabhi pehle ek chat/naam dabakar). Dobara-dobara koshish karke, phir bolkar batata hai. */
    private void typeFlow(final String target, final String text, boolean fieldName) {
        if (text.length() == 0) {
            tellLater("Kya likhna hai? Jaise: type karo, aur phir jo likhna ho.");
            return;
        }
        if (fieldName || target.length() == 0) {
            AccessibilityNodeInfo e = pickEditable(target);
            if (e == null) {
                tellLater("Likhne ki jagah nahi dikhi. Pehle text box par click boliye.");
            } else if (!typeInto(e, text)) {
                tellLater("Yahan likh nahi paya.");
            }
            return;
        }
        // "PRIME AKJ ko message type karo ...": pehle us chat par jao
        AccessibilityNodeInfo t = findTarget(target, 0.85);
        AccessibilityNodeInfo e0 = pickEditable("");
        int h = getResources().getDisplayMetrics().heightPixels;
        boolean titleOnly = false;
        if (t != null) {
            Rect r = new Rect();
            t.getBoundsInScreen(r);
            titleOnly = r.top < h * 0.2;
        }
        if (t == null || (titleOnly && e0 != null)) {
            if (e0 != null) {
                if (!typeInto(e0, text)) {
                    tellLater("Yahan likh nahi paya.");
                }
            } else {
                tellLater(target + " screen par nahi dikha.");
            }
            return;
        }
        doClick(t, false);
        waitAndType(text, 0);
    }

    private void waitAndType(final String text, final int attempt) {
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                AccessibilityNodeInfo e = pickEditable("message");
                if (e != null) {
                    if (!typeInto(e, text)) {
                        tellLater("Yahan likh nahi paya.");
                    }
                } else if (attempt < 8) {
                    waitAndType(text, attempt + 1);
                } else {
                    tellLater("Chat khul nahi payi, isliye likh nahi paya.");
                }
            }
        }, attempt == 0 ? 1200 : 450);
    }

    private boolean sendNow() {
        AccessibilityNodeInfo s = null;
        double bs = 0;
        for (Entry e : screen()) {
            double sc = Math.max(JarvisControl.match("send", e.label), JarvisControl.match("भेजें", e.label)) * e.w;
            if (sc >= 0.9 && sc > bs) {
                bs = sc;
                s = e.node;
            }
        }
        if (s != null && doClick(s, false)) {
            return true;
        }
        AccessibilityNodeInfo f = pickEditable("");
        return imeEnter(f);
    }

    /** Ek control-kaam chalao. "" = ho gaya (chup-chap), warna bolne layak sandesh. */
    public String exec(JarvisControl.Cmd c) {
        try {
            switch (c.kind) {
                case JarvisControl.BACK:
                    performGlobalAction(GLOBAL_ACTION_BACK);
                    return "";
                case JarvisControl.HOME:
                    performGlobalAction(GLOBAL_ACTION_HOME);
                    return "";
                case JarvisControl.RECENTS:
                    performGlobalAction(GLOBAL_ACTION_RECENTS);
                    return "";
                case JarvisControl.NOTIFS:
                    performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS);
                    return "";
                case JarvisControl.QUICK:
                    performGlobalAction(GLOBAL_ACTION_QUICK_SETTINGS);
                    return "";
                case JarvisControl.SCROLL:
                case JarvisControl.SWIPE: {
                    final String d = c.dir;
                    int n = Math.max(1, c.count);
                    for (int i = 0; i < n; i++) {
                        handler.postDelayed(new Runnable() {
                            @Override
                            public void run() {
                                scrollOnce(d);
                            }
                        }, i * 450L);
                    }
                    return "";
                }
                case JarvisControl.CLICK:
                case JarvisControl.LONG: {
                    AccessibilityNodeInfo t = findTarget(c.target, 0.8);
                    if (t == null) {
                        return c.target + " screen par nahi dikha.";
                    }
                    return doClick(t, c.kind == JarvisControl.LONG) ? "" : c.target + " dab nahi paya.";
                }
                case JarvisControl.TYPE:
                    typeFlow(c.target, c.text, c.qual);
                    return "";
                case JarvisControl.SEND:
                    return sendNow() ? "" : "Send ka button nahi mila.";
                case JarvisControl.ENTER:
                    return imeEnter(pickEditable("")) ? "" : "Enter nahi dab paya.";
                case JarvisControl.CLEAR: {
                    AccessibilityNodeInfo e = pickEditable("");
                    if (e == null) {
                        return "Saaf karne ke liye text box nahi dikha.";
                    }
                    Bundle b = new Bundle();
                    b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, "");
                    return e.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, b) ? "" : "Saaf nahi kar paya.";
                }
                default:
                    return "Ye kaam abhi nahi aata.";
            }
        } catch (Throwable t) {
            log("control error: " + t.getClass().getSimpleName());
            return "Ye kaam nahi ho paya.";
        }
    }

    /** Screen par is naam ka kuch hai? (OPEN: app kholna hai ya screen ka hissa dabana hai, tay karne ke liye) */
    public boolean screenHas(String target) {
        try {
            return findTarget(target, 0.85) != null;
        } catch (Throwable t) {
            return false;
        }
    }

    // ---- Screen samajhna: dikh rahe text ko padh kar do (password wale box chhod kar) ----
    private void collectText(AccessibilityNodeInfo n, StringBuilder sb, int cap, int[] count, String[] last, int depth) {
        if (n == null || depth > 45 || count[0] > MAX_NODES || sb.length() >= cap) {
            return;
        }
        count[0]++;
        if (n.isVisibleToUser() && !n.isPassword()) {
            CharSequence t = n.getText();
            CharSequence d = n.getContentDescription();
            String s = "";
            if (t != null && t.toString().trim().length() > 0) {
                s = t.toString().trim();
            } else if (d != null && d.toString().trim().length() > 0) {
                s = d.toString().trim();
            }
            if (s.length() > 0 && !s.equals(last[0])) {
                sb.append(s).append('\n');
                last[0] = s;
            }
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            collectText(n.getChild(i), sb, cap, count, last, depth + 1);
        }
    }

    /** Abhi jo app khula hai uski screen ka text (cap akshar tak). "" = kuch nahi mila. */
    public String screenText(int cap) {
        try {
            AccessibilityNodeInfo r = activeRoot();
            if (r == null) {
                return "";
            }
            StringBuilder sb = new StringBuilder();
            collectText(r, sb, cap, new int[]{0}, new String[]{""}, 0);
            String out = sb.toString().trim();
            return out.length() > cap ? out.substring(0, cap) : out;
        } catch (Throwable t) {
            return "";
        }
    }

    public String screenApp() {
        try {
            AccessibilityNodeInfo r = activeRoot();
            return r == null || r.getPackageName() == null ? "" : r.getPackageName().toString();
        } catch (Throwable t) {
            return "";
        }
    }

    @Override
    public void onInterrupt() {
    }
}
