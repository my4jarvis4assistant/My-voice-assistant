package org.myassistant.myvoiceassistant;

import android.app.Notification;
import android.app.PendingIntent;
import android.app.RemoteInput;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Phone ke aaye hue messages / missed calls ka khaata (notifications se) + unka jawab.
 * - Jarvis bata sakta hai: kitne aaye, kiske aaye, kya likha hai, kaun si call miss hui.
 * - Gemini message padhkar reply likhta hai aur notification ke 'Reply' se bhej deta hai.
 *   Jo jawab wo nahi de sakta (aapke baare me sawal), uske liye aapse bolkar poochta hai.
 */
public final class JarvisInbox {
    private JarvisInbox() {
    }

    public static final class Item {
        public String key = "";
        public String pkg = "";
        public String app = "";
        public String sender = "";
        public String chat = "";
        public String text = "";
        public String kind = "msg";          // msg | call
        public String reply = "";
        public long time = 0;
        public boolean group = false;
        public boolean read = false;
        public boolean replied = false;
        public boolean asked = false;
        public boolean canReply = false;
        public boolean voiced = false;       // user se is ke baare me bolkar poochh liya
    }

    /** Ek command ka matlab. kind: summary | from | calls | read | sent | reply */
    public static final class Cmd {
        public String kind = "summary";
        public String app = "";
        public String name = "";
        public boolean msgs = true;
        public boolean calls = true;
    }

    private static final List<Item> ITEMS = new ArrayList<Item>();
    private static final List<Item> ASKS = new ArrayList<Item>();
    private static final Map<String, Notification.Action> ACTIONS = new HashMap<String, Notification.Action>();
    private static final Map<String, Long> LAST_TIME = new HashMap<String, Long>();
    private static final Map<String, String> LAST_TEXT = new HashMap<String, String>();
    private static final Map<String, Long> REPLY_AT = new HashMap<String, Long>();
    private static final Set<String> BUSY = new HashSet<String>();
    private static boolean loaded = false;

    // ------------------------------------------------------------ app info --
    static String appLabel(String pkg) {
        if ("com.whatsapp".equals(pkg)) {
            return "WhatsApp";
        }
        if ("com.whatsapp.w4b".equals(pkg)) {
            return "WhatsApp Business";
        }
        if ("com.instagram.android".equals(pkg)) {
            return "Instagram";
        }
        if ("com.facebook.orca".equals(pkg)) {
            return "Messenger";
        }
        if ("org.telegram.messenger".equals(pkg) || "org.telegram.messenger.web".equals(pkg)) {
            return "Telegram";
        }
        if (isSms(pkg)) {
            return "SMS";
        }
        return null;
    }

    static boolean isSms(String pkg) {
        return pkg != null && (pkg.equals("com.google.android.apps.messaging") || pkg.equals("com.android.mms")
                || pkg.equals("com.samsung.android.messaging") || pkg.equals("com.miui.mms")
                || pkg.equals("com.android.messaging") || pkg.endsWith(".mms"));
    }

    static boolean isDialer(String pkg) {
        return pkg != null && (pkg.equals("com.google.android.dialer") || pkg.equals("com.android.dialer")
                || pkg.equals("com.samsung.android.dialer") || pkg.equals("com.android.server.telecom")
                || pkg.equals("com.android.phone") || pkg.equals("com.miui.voip")
                || pkg.equals("com.google.android.apps.dialer"));
    }

    /** Auto-reply sirf in chat apps me (SMS me nahi: wahan OTP/bank wale hote hain). */
    static boolean autoApp(String pkg) {
        return "com.whatsapp".equals(pkg) || "com.whatsapp.w4b".equals(pkg)
                || "com.instagram.android".equals(pkg) || "com.facebook.orca".equals(pkg)
                || (pkg != null && pkg.startsWith("org.telegram.messenger"));
    }

    // ------------------------------------------------------------- storage --
    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("jarvis_prefs", 0);
    }

    private static synchronized void load(Context c) {
        if (loaded) {
            return;
        }
        loaded = true;
        try {
            String js = prefs(c).getString("inbox_json", "");
            if (js.length() == 0) {
                return;
            }
            JSONArray a = new JSONArray(js);
            long cutoff = System.currentTimeMillis() - 36L * 3600 * 1000;
            for (int i = 0; i < a.length(); i++) {
                JSONObject o = a.getJSONObject(i);
                Item it = new Item();
                it.key = o.optString("key");
                it.pkg = o.optString("pkg");
                it.app = o.optString("app");
                it.sender = o.optString("sender");
                it.chat = o.optString("chat");
                it.text = o.optString("text");
                it.kind = o.optString("kind", "msg");
                it.reply = o.optString("reply");
                it.time = o.optLong("time");
                it.group = o.optBoolean("group");
                it.read = o.optBoolean("read");
                it.replied = o.optBoolean("replied");
                it.asked = o.optBoolean("asked");
                if (it.time >= cutoff) {
                    ITEMS.add(it);
                }
            }
        } catch (Exception ignored) {
        }
    }

    private static synchronized void save(Context c) {
        try {
            JSONArray a = new JSONArray();
            int from = Math.max(0, ITEMS.size() - 80);
            for (int i = from; i < ITEMS.size(); i++) {
                Item it = ITEMS.get(i);
                JSONObject o = new JSONObject();
                o.put("key", it.key).put("pkg", it.pkg).put("app", it.app).put("sender", it.sender)
                        .put("chat", it.chat).put("text", it.text).put("kind", it.kind).put("reply", it.reply)
                        .put("time", it.time).put("group", it.group).put("read", it.read)
                        .put("replied", it.replied).put("asked", it.asked);
                a.put(o);
            }
            prefs(c).edit().putString("inbox_json", a.toString()).apply();
        } catch (Exception ignored) {
        }
    }

    // ---------------------------------------------------- notification side --
    static synchronized long lastTime(String key) {
        Long v = LAST_TIME.get(key);
        return v == null ? 0 : v;
    }

    static synchronized void setLastTime(String key, long t) {
        LAST_TIME.put(key, t);
    }

    static synchronized String lastText(String key) {
        return LAST_TEXT.get(key);
    }

    static synchronized void setLastText(String key, String t) {
        LAST_TEXT.put(key, t);
    }

    static synchronized void setAction(String key, Notification.Action a) {
        if (a != null) {
            ACTIONS.put(key, a);
        }
    }

    static synchronized boolean recentlyReplied(String key) {
        Long t = REPLY_AT.get(key);
        return t != null && System.currentTimeMillis() - t < 10000;
    }

    static synchronized Item add(Context c, Item it) {
        load(c);
        it.canReply = ACTIONS.containsKey(it.key);
        ITEMS.add(it);
        while (ITEMS.size() > 1000) {
            ITEMS.remove(0);
        }
        save(c);
        return it;
    }

    static synchronized void markReadByKey(Context c, String key) {
        load(c);
        boolean ch = false;
        for (Item it : ITEMS) {
            if (it.key.equals(key) && !it.read) {
                it.read = true;
                ch = true;
            }
        }
        ACTIONS.remove(key);
        LAST_TIME.remove(key);
        LAST_TEXT.remove(key);
        if (ch) {
            save(c);
        }
    }

    static synchronized List<Item> unread(Context c, String kind) {
        load(c);
        List<Item> out = new ArrayList<Item>();
        for (Item it : ITEMS) {
            if (!it.read && it.kind.equals(kind)) {
                out.add(it);
            }
        }
        return out;
    }

    // --------------------------------------------------------- understanding --
    private static final Set<String> QUERY = set("aaye", "aaya", "aayi", "aayee", "aaya?", "aya", "aye", "aai",
            "aayein", "mile", "mila", "mili", "kitne", "kitni", "kitna", "kiske", "kiska", "kiski", "kisne",
            "naye", "naya", "nayi", "unread", "pending", "new", "received", "came", "missed", "miss", "padho",
            "padh", "sunao", "suna", "dikhao", "batao", "bataiye", "bata", "read", "check", "kisi", "koi", "kuch");
    private static final Set<String> MSG = set("message", "messages", "msg", "msgs", "sandesh", "massage",
            "messeg", "messege", "text", "texts", "sms", "notification", "notifications", "dm", "dms",
            "whatsapp", "watsapp", "whatsap", "vatsapp", "insta", "instagram", "messenger", "telegram", "chat",
            "chats");
    private static final Set<String> CALL = set("call", "calls", "caal", "kall", "missed", "miss");
    private static final Set<String> SEND = set("bhejo", "bhej", "bhejna", "send", "likho", "likh", "bhejdo",
            "bhejiye", "karo", "kro", "lagao", "laga", "dial", "set", "alarm", "timer", "open", "kholo");
    private static final Set<String> REPLY = set("reply", "riply", "jawab", "javab", "jawaab", "jawap", "uttar",
            "respond", "answer");
    private static final Set<String> SENT = set("diya", "diye", "bheja", "bhejaa", "kiya", "gaya", "gayi");
    private static final Set<String> STOP = set("kya", "hai", "hain", "he", "mere", "mera", "meri", "me", "mein",
            "par", "pe", "per", "pr", "ne", "ka", "ke", "ki", "ko", "se", "to", "ye", "yeh", "wo", "woh", "abhi",
            "tak", "jarvis", "hey", "hello", "hi", "please", "plz", "phone", "aur", "bhi", "sab", "saare",
            "sare", "sabke", "ab", "tak", "wale", "wala", "wali", "the", "a", "my", "any", "is", "are", "have",
            "did", "do", "i", "me", "from", "on", "of", "in", "and", "all", "has", "ho", "hua", "hui", "huye",
            "jo", "jis", "dena", "de", "do", "kar", "karna", "karke", "ek", "unhone", "unka", "unki", "unko",
            "usne", "usko", "uska", "uski", "kab", "kaun", "kon", "kis", "koi", "kuch", "kisi", "naye", "naya",
            "nayi", "new", "latest", "last");

    private static Set<String> set(String... a) {
        Set<String> s = new HashSet<String>();
        for (String x : a) {
            s.add(x);
        }
        return s;
    }

    private static boolean any(List<String> w, Set<String> s) {
        for (String t : w) {
            if (s.contains(t)) {
                return true;
            }
        }
        return false;
    }

    static String appOf(List<String> w) {
        for (String t : w) {
            if (t.equals("whatsapp") || t.equals("watsapp") || t.equals("whatsap") || t.equals("vatsapp")) {
                return "whatsapp";
            }
            if (t.equals("instagram") || t.equals("insta")) {
                return "instagram";
            }
            if (t.equals("messenger")) {
                return "messenger";
            }
            if (t.equals("telegram")) {
                return "telegram";
            }
            if (t.equals("sms")) {
                return "sms";
            }
        }
        return "";
    }

    /** null = ye inbox ki baat nahi. */
    public static Cmd parse(String utterance) {
        List<String> w = JarvisContactMatch.words(utterance);
        if (w.isEmpty() || w.size() > 24) {
            return null;
        }
        boolean q = any(w, QUERY);
        boolean msg = any(w, MSG);
        boolean call = any(w, CALL);
        boolean send = any(w, SEND);
        boolean rep = any(w, REPLY);
        Cmd c = new Cmd();
        c.app = appOf(w);
        if (rep) {
            if (w.size() > 7 || any(w, set("ki", "kee", "bolo", "likho", "saying", "that"))) {
                return null;                      // "saket ko reply bhejo ki ..." = khud ka message, social flow sambhalega
            }
            if (any(w, SENT) && !any(w, set("de", "do", "dena", "kar", "karo", "kro", "bhejo", "bhej"))) {
                c.kind = "sent";
            } else if (any(w, SENT) && any(w, set("kya", "kisko", "kisne", "kiska", "kitne"))) {
                c.kind = "sent";
            } else if (any(w, set("de", "do", "dena", "dijiye", "kar", "karo", "kro", "kardo", "krdo", "kardena",
                    "bhejo", "bhej", "bhejna", "kijiye", "kariye", "send", "dedo", "dedena", "karde"))) {
                c.kind = "reply";
            } else {
                return null;
            }
            c.name = nameOf(w);
            c.msgs = true;
            c.calls = false;
            return c;
        }
        if (send && !any(w, set("kitne", "kiske", "kisne", "kiska", "aaya", "aaye", "aayi"))) {
            return null;
        }
        boolean generic = q && any(w, set("aaya", "aaye", "aayi", "aya", "aye", "aai", "mile", "mila"))
                && any(w, set("kuch", "koi", "kisi", "kitne", "kiske", "kisne", "kiska", "kiski"));
        if (!((msg || call) && q) && !generic) {
            return null;
        }
        c.msgs = msg || !call;
        c.calls = call || !msg;
        if (any(w, set("padho", "padh", "sunao", "suna", "read", "dikhao", "likha"))) {
            c.kind = "read";
            c.calls = false;
        } else if (any(w, set("kiske", "kisne", "kiska", "kiski", "kaun", "kon", "kisi"))
                && !any(w, set("kitne", "kitni", "kitna"))) {
            c.kind = "from";
        } else if (call && !msg) {
            c.kind = "calls";
            c.msgs = false;
        }
        c.name = nameOf(w);
        return c;
    }

    private static String nameOf(List<String> w) {
        StringBuilder sb = new StringBuilder();
        int n = 0;
        for (String t : w) {
            if (STOP.contains(t) || QUERY.contains(t) || MSG.contains(t) || CALL.contains(t) || SEND.contains(t)
                    || REPLY.contains(t) || SENT.contains(t) || t.length() < 3) {
                continue;
            }
            sb.append(n > 0 ? " " : "").append(t);
            n++;
        }
        return n <= 3 ? sb.toString() : "";
    }

    // --------------------------------------------------------------- answers --
    private static boolean appMatches(Item it, String app) {
        if (app.length() == 0) {
            return true;
        }
        if (app.equals("whatsapp")) {
            return it.pkg.startsWith("com.whatsapp");
        }
        if (app.equals("instagram")) {
            return it.pkg.equals("com.instagram.android");
        }
        if (app.equals("messenger")) {
            return it.pkg.equals("com.facebook.orca");
        }
        if (app.equals("telegram")) {
            return it.pkg.startsWith("org.telegram");
        }
        if (app.equals("sms")) {
            return isSms(it.pkg);
        }
        return true;
    }

    private static boolean nameMatches(Item it, String name) {
        if (name.length() == 0) {
            return true;
        }
        return JarvisContactMatch.score(name, it.sender) >= 0.7 || JarvisContactMatch.score(name, it.chat) >= 0.7;
    }

    public static synchronized List<Item> select(Context c, String kind, String app, String name) {
        List<Item> all = unread(c, kind);
        List<Item> out = new ArrayList<Item>();
        for (Item it : all) {
            if (appMatches(it, app) && nameMatches(it, name)) {
                out.add(it);
            }
        }
        return out;
    }

    private static String who(Item it) {
        String s = JarvisContactMatch.speakable(it.sender.length() > 0 ? it.sender : it.chat);
        if (it.group && it.chat.length() > 0 && !it.chat.equals(it.sender)) {
            s = s + " (" + JarvisContactMatch.speakable(it.chat) + " group me)";
        }
        return s;
    }

    private static String cut(String t, int n) {
        t = t == null ? "" : t.replace("\n", " ").trim();
        return t.length() <= n ? t : t.substring(0, n) + "...";
    }

    /** Bolne layak jawab. Doosra element: kya iske baad "jawab de doon?" poochna chahiye. */
    public static String[] answer(Context c, Cmd cmd) {
        String note = "";
        List<Item> msgs = new ArrayList<Item>();
        List<Item> calls = new ArrayList<Item>();
        if (cmd.msgs) {
            msgs = select(c, "msg", cmd.app, cmd.name);
        }
        if (cmd.calls) {
            calls = select(c, "call", cmd.app, cmd.name);
        }
        if (cmd.name.length() > 0 && msgs.isEmpty() && calls.isEmpty()) {
            List<Item> m2 = cmd.msgs ? select(c, "msg", cmd.app, "") : new ArrayList<Item>();
            List<Item> c2 = cmd.calls ? select(c, "call", cmd.app, "") : new ArrayList<Item>();
            if (!m2.isEmpty() || !c2.isEmpty()) {
                note = cmd.name + " naam se kuch nahi mila. ";
                msgs = m2;
                calls = c2;
            }
        }
        if (msgs.isEmpty() && calls.isEmpty()) {
            String what = cmd.kind.equals("calls") ? "missed call" : (cmd.calls && cmd.msgs ? "message ya call" : "message");
            return new String[]{note + "Abhi koi naya " + what + " nahi hai.", ""};
        }
        StringBuilder sb = new StringBuilder(note);
        boolean offer = false;
        if (!msgs.isEmpty()) {
            if (cmd.kind.equals("read")) {
                int from = Math.max(0, msgs.size() - 5);
                for (int i = from; i < msgs.size(); i++) {
                    Item it = msgs.get(i);
                    sb.append(who(it)).append(" ne ").append(it.app).append(" par likha: ")
                            .append(cut(it.text, 160)).append(". ");
                    offer = offer || (it.canReply && !it.group);
                }
                if (from > 0) {
                    sb.append("Isse pehle ke ").append(from).append(" message aur hain. ");
                }
            } else {
                Map<String, List<Item>> g = new LinkedHashMap<String, List<Item>>();
                for (Item it : msgs) {
                    String k = who(it) + "|" + it.app;
                    if (!g.containsKey(k)) {
                        g.put(k, new ArrayList<Item>());
                    }
                    g.get(k).add(it);
                    offer = offer || (it.canReply && !it.group);
                }
                if (cmd.kind.equals("from")) {
                    sb.append("Message aaye hain: ");
                } else {
                    sb.append("Aapke ").append(msgs.size()).append(" naye message hain. ");
                }
                int shown = 0;
                for (Map.Entry<String, List<Item>> e : g.entrySet()) {
                    if (shown >= 6) {
                        sb.append("aur kuch logon ke bhi. ");
                        break;
                    }
                    Item f = e.getValue().get(0);
                    int n = e.getValue().size();
                    if (cmd.kind.equals("from")) {
                        sb.append(who(f)).append(" (").append(f.app).append(")");
                        sb.append(shown < g.size() - 1 && shown < 5 ? ", " : ". ");
                    } else {
                        sb.append(who(f)).append(n > 1 ? " ke " + n + " message" : " ka ek message")
                                .append(" (").append(f.app).append(")");
                        sb.append(shown < g.size() - 1 && shown < 5 ? ", " : ". ");
                    }
                    shown++;
                }
                if (msgs.size() == 1) {
                    sb.append("Unhone likha: ").append(cut(msgs.get(0).text, 140)).append(". ");
                }
            }
        }
        if (!calls.isEmpty()) {
            sb.append(calls.size()).append(" missed call: ");
            Set<String> seen = new HashSet<String>();
            int n = 0;
            for (Item it : calls) {
                String w = who(it);
                if (seen.add(w) && n < 5) {
                    sb.append(n > 0 ? ", " : "").append(w);
                    n++;
                }
            }
            sb.append(". ");
        } else if (cmd.calls && !cmd.msgs) {
            sb.append("Koi missed call nahi hai. ");
        }
        if (offer) {
            sb.append("Jawab de doon?");
        }
        return new String[]{sb.toString().trim(), offer ? "1" : ""};
    }

    /** "Maine kya reply bheje" */
    public static synchronized String sentText(Context c, String name) {
        load(c);
        StringBuilder sb = new StringBuilder();
        int n = 0;
        for (int i = ITEMS.size() - 1; i >= 0 && n < 4; i--) {
            Item it = ITEMS.get(i);
            if (it.replied && it.reply.length() > 0 && nameMatches(it, name)) {
                sb.append(JarvisContactMatch.speakable(it.sender.length() > 0 ? it.sender : it.chat))
                        .append(" ko ").append(it.app).append(" par bheja: ").append(cut(it.reply, 120)).append(". ");
                n++;
            }
        }
        return n == 0 ? "Abhi tak maine koi reply nahi bheja." : sb.toString().trim();
    }

    // ----------------------------------------------------------------- reply --
    private static final String SYSTEM = "Tum Shakshm Jha ki taraf se unke dost/parichit ko chat reply likh rahe ho. "
            + "Reply ek aam insaan jaisa chhota (ek ya do line) likho, usi bhasha aur style me jisme samne wale ne "
            + "likha hai (Hinglish Roman, Hindi Roman ya English). Emoji tabhi jab samne wale ne use kiya ho. "
            + "Khud ko AI ya assistant mat batao. Sirf wahi kaho jo message se saaf pata ho. "
            + "Agar jawab dene ke liye Shakshm ki nijee jaankari, kahan hain/kya kar rahe hain, kab aayenge, free hain ya nahi, "
            + "koi faisla, plan, wada, paisa, address ya samay dena pade, ya message gambhir/emotional/emergency/paise "
            + "maangne ya legal type ka ho, ya tumhe samajh na aaye ki kya kehna hai, to sirf ek shabd likho: ASK. "
            + "Hello, hal-chaal, shukriya, good morning jaise saadharan messages ka chhota jawab do. "
            + "Sirf reply ka text likho, koi quote, naam ya samjhaish nahi.";

    /** Reply ka text ya null (null = jawab nahi de sakta, user se poochna hai). */
    public static String compose(Context c, Item it) {
        SharedPreferences p = prefs(c);
        String key = p.getString("gemini_key", "");
        if (key.trim().length() == 0) {
            return null;
        }
        StringBuilder user = new StringBuilder();
        long since = System.currentTimeMillis() - 6L * 3600 * 1000;
        synchronized (JarvisInbox.class) {
            int n = 0;
            List<Item> hist = new ArrayList<Item>();
            for (int i = ITEMS.size() - 1; i >= 0 && n < 8; i--) {
                Item o = ITEMS.get(i);
                if (o != it && o.kind.equals("msg") && o.time >= since && o.chat.equals(it.chat)
                        && o.pkg.equals(it.pkg) && !o.group) {
                    hist.add(0, o);
                    n++;
                }
            }
            if (!hist.isEmpty()) {
                user.append("Pehle ki baat-cheet:\n");
                for (Item o : hist) {
                    user.append("Unhone: ").append(cut(o.text, 200)).append("\n");
                    if (o.reply.length() > 0) {
                        user.append("Maine: ").append(cut(o.reply, 200)).append("\n");
                    }
                }
            }
        }
        user.append("Sender: ").append(it.sender).append(" (").append(it.app).append(")\n");
        user.append("Naya message: ").append(it.text);
        String out = JarvisBrain.generate(key, p.getString("ai_model", ""), SYSTEM, user.toString());
        if (out == null) {
            return null;
        }
        out = out.trim();
        if (out.startsWith("\"") && out.endsWith("\"") && out.length() > 2) {
            out = out.substring(1, out.length() - 1).trim();
        }
        if (out.length() == 0 || out.toUpperCase(Locale.ENGLISH).startsWith("ASK") || out.length() > 400) {
            return null;
        }
        return out;
    }

    /** Notification ke Reply se bhejo. */
    public static boolean send(Context c, Item it, String text) {
        Notification.Action a;
        synchronized (JarvisInbox.class) {
            a = ACTIONS.get(it.key);
        }
        if (a == null || a.actionIntent == null || text == null || text.trim().length() == 0) {
            return false;
        }
        try {
            RemoteInput[] ris = a.getRemoteInputs();
            if (ris == null || ris.length == 0) {
                return false;
            }
            RemoteInput ri = ris[0];
            for (RemoteInput r : ris) {
                if (r.getAllowFreeFormInput()) {
                    ri = r;
                    break;
                }
            }
            Intent intent = new Intent();
            Bundle b = new Bundle();
            b.putCharSequence(ri.getResultKey(), text.trim());
            RemoteInput.addResultsToIntent(new RemoteInput[]{ri}, intent, b);
            a.actionIntent.send(c, 0, intent);
            synchronized (JarvisInbox.class) {
                REPLY_AT.put(it.key, System.currentTimeMillis());
                for (Item o : ITEMS) {
                    if (o.key.equals(it.key) && !o.read && o.kind.equals("msg")) {
                        o.read = true;
                        o.replied = true;
                        o.reply = text.trim();
                    }
                }
                it.replied = true;
                it.read = true;
                it.reply = text.trim();
                ASKS.remove(it);
            }
            save(c);
            return true;
        } catch (PendingIntent.CanceledException e) {
            return false;
        } catch (Exception e) {
            return false;
        }
    }

    /** Ek chat ke saare naye message ek saath padhkar ek reply (auto-mode ke liye, thoda ruk kar). */
    private static void autoKey(final Context c, final String key) {
        synchronized (JarvisInbox.class) {
            if (!BUSY.add(key)) {
                return;
            }
        }
        final Context app = c.getApplicationContext();
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Thread.sleep(4000);                  // agar 2-3 message peeche peeche aayein to ek hi reply
                    Item last = null;
                    StringBuilder all = new StringBuilder();
                    synchronized (JarvisInbox.class) {
                        for (Item it : ITEMS) {
                            if (it.key.equals(key) && it.kind.equals("msg") && !it.read && !it.replied) {
                                if (all.length() > 0) {
                                    all.append("\n");
                                }
                                all.append(it.text);
                                last = it;
                            }
                        }
                    }
                    if (last == null) {
                        return;
                    }
                    Item probe = new Item();
                    probe.key = last.key;
                    probe.pkg = last.pkg;
                    probe.app = last.app;
                    probe.sender = last.sender;
                    probe.chat = last.chat;
                    probe.group = last.group;
                    probe.time = last.time;
                    probe.text = all.toString();
                    String r = compose(app, probe);
                    if (r == null) {
                        synchronized (JarvisInbox.class) {
                            for (Item it : ITEMS) {
                                if (it.key.equals(key) && it.kind.equals("msg") && !it.read && !it.replied) {
                                    it.asked = true;
                                }
                            }
                            ASKS.add(last);
                        }
                        save(app);
                        JarvisOverlayService.askAbout(app, last);
                        return;
                    }
                    Thread.sleep(1200 + (long) (Math.random() * 1800));
                    if (!send(app, last, r)) {
                        synchronized (JarvisInbox.class) {
                            for (Item it : ITEMS) {
                                if (it.key.equals(key) && it.kind.equals("msg") && !it.read && !it.replied) {
                                    it.asked = true;             // dobara-dobara koshish ka loop na bane
                                }
                            }
                        }
                        log(app, "reply bhej nahi paya (" + last.app + ")");
                    } else {
                        log(app, "auto-reply bheja: " + last.sender);
                    }
                } catch (Exception ignored) {
                } finally {
                    boolean more = false;
                    synchronized (JarvisInbox.class) {
                        BUSY.remove(key);
                        for (Item it : ITEMS) {
                            if (it.key.equals(key) && it.kind.equals("msg") && !it.read && !it.replied
                                    && !it.asked && !it.group) {
                                more = true;
                                break;
                            }
                        }
                    }
                    if (more) {
                        autoKey(app, key);           // jawab dete waqt aur message aa gaye: unka bhi jawab
                    }
                }
            }
        }).start();
    }

    /** Naya message aaya: auto mode ho to jawab ki taiyari. */
    static void onNew(Context c, Item it) {
        try {
            if (!"auto".equals(prefs(c).getString("reply_mode", "off"))) {
                return;
            }
            if (!it.kind.equals("msg") || !it.canReply || it.group || !autoApp(it.pkg)) {
                return;
            }
            // ek sender ko ghante me 500 se zyada nahi (sirf bot-loop se bachne ki bahut badi hadd)
            int recent = 0;
            long hour = System.currentTimeMillis() - 3600L * 1000;
            synchronized (JarvisInbox.class) {
                for (Item o : ITEMS) {
                    if (o.replied && o.time >= hour && o.key.equals(it.key)) {
                        recent++;
                    }
                }
            }
            if (recent >= 500) {
                return;
            }
            autoKey(c, it.key);
        } catch (Exception ignored) {
        }
    }

    public static final class Outcome {
        public final List<Item> sent = new ArrayList<Item>();
        public final List<Item> asks = new ArrayList<Item>();
        public int skippedGroups = 0;
    }

    /** Voice command se: sab (ya chune hue) naye messages ka jawab. Network hai: thread se bulao. */
    public static Outcome replyNow(Context c, String app, String name) {
        Outcome o = new Outcome();
        List<Item> msgs = select(c, "msg", app, name);
        if (msgs.isEmpty() && name.length() > 0) {
            msgs = select(c, "msg", app, "");
        }
        Set<String> done = new HashSet<String>();
        for (int i = msgs.size() - 1; i >= 0; i--) {
            Item it = msgs.get(i);
            if (!done.add(it.key)) {
                continue;                               // ek chat ka ek hi reply
            }
            if (it.group) {
                o.skippedGroups++;
                continue;
            }
            if (!it.canReply) {
                continue;
            }
            StringBuilder all = new StringBuilder();
            for (Item x : msgs) {
                if (x.key.equals(it.key)) {
                    all.append(all.length() > 0 ? "\n" : "").append(x.text);
                }
            }
            Item probe = new Item();
            probe.key = it.key;
            probe.pkg = it.pkg;
            probe.app = it.app;
            probe.sender = it.sender;
            probe.chat = it.chat;
            probe.time = it.time;
            probe.text = all.toString();
            String r = compose(c, probe);
            if (r != null && send(c, it, r)) {
                o.sent.add(it);
            } else {
                synchronized (JarvisInbox.class) {
                    it.asked = true;
                    probe.text = all.toString();
                    it.text = all.toString();
                }
                o.asks.add(it);
            }
        }
        synchronized (JarvisInbox.class) {
            for (Item a : o.asks) {
                if (!ASKS.contains(a)) {
                    ASKS.add(a);
                }
            }
        }
        return o;
    }

    public static synchronized Item nextAsk() {
        return nextAsk(false);
    }

    public static synchronized Item nextAsk(boolean onlyNew) {
        while (!ASKS.isEmpty()) {
            Item it = ASKS.get(0);
            if (it.replied || it.read) {
                ASKS.remove(0);
                continue;
            }
            if (onlyNew && it.voiced) {
                boolean found = false;
                for (Item o : ASKS) {
                    if (!o.voiced && !o.replied && !o.read) {
                        return o;
                    }
                }
                return null;
            }
            return it;
        }
        return null;
    }

    public static synchronized void dropAsk(Item it) {
        ASKS.remove(it);
    }

    public static synchronized void addAsk(Item it) {
        if (!ASKS.contains(it)) {
            ASKS.add(it);
        }
    }

    /** "bolo ki main aa raha hoon" -> "main aa raha hoon" */
    public static String stripLead(String t) {
        String s = t == null ? "" : t.trim();
        String prev;
        do {
            prev = s;
            s = s.replaceFirst("(?i)^(bolo|bol do|bol dena|keh do|kehdo|kehna|likho|likh do|bhejo|bhej do|reply|jawab|"
                    + "unhe|unko|usko|use|ye|yeh|ki|ke|ye bhejo|send|tell him|tell her|say)\\b[\\s,:]*", "");
        } while (!s.equals(prev));
        return s.length() == 0 ? t.trim() : s;
    }

    static void log(Context c, String s) {
        try {
            prefs(c).edit().putString("notif_log", s + " @" + System.currentTimeMillis() / 1000).apply();
        } catch (Exception ignored) {
        }
    }
}
