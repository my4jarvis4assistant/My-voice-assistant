package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.json.JSONArray;

/**
 * Auto-reply ko "aapki tarah" banane wala hissa:
 *  - Style: aapke apne bheje hue messages (Jarvis se bheje ya "meri style ..." bolkar sikhaye) yaad rakhta hai.
 *  - Tone: har insaan ke liye alag ("Prime ko dost ki tarah reply karo", "papa ko respect se reply dena").
 *  - Busy mode: "busy mode on, main gym me hu" -> reply me bata do ki aap busy ho, kuch ghante baad apne aap band.
 * Samajhne wala hissa (parse) me Android nahi hai.
 */
public final class JarvisStyle {
    private JarvisStyle() {
    }

    private static final String PREF = "jarvis_style";
    private static final int MAX_SAMPLES = 30;
    private static final int USE_SAMPLES = 12;

    public static final int NONE = 0, BUSY_ON = 1, BUSY_OFF = 2, STYLE_ADD = 3, STYLE_CLEAR = 4, TONE_SET = 5,
            TONE_CLEAR = 6, STATUS = 7;

    public static final class Cmd {
        public int kind = NONE;
        public String text = "";      // busy ka karan / style ka namuna / tone
        public String name = "";      // tone kis ke liye
        public int minutes = 180;     // busy kitni der
    }

    private static String norm(String s) {
        if (s == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (char ch : s.toLowerCase(Locale.ENGLISH).toCharArray()) {
            sb.append(Character.isLetterOrDigit(ch) ? ch : ' ');
        }
        return sb.toString().trim().replaceAll("\\s+", " ");
    }

    private static final Pattern DURATION = Pattern.compile(
            "(\\d+)\\s*(ghante|ghanta|ghantey|ghanto|hour|hours|hr|hrs|minute|minutes|min|mins|minat)\\b");
    private static final Pattern STYLE_RE = Pattern.compile(
            "^(?:jarvis\\s+)?(?:meri\\s+style\\s+(?:yaad\\s+rakho|seekho|sikho|ye\\s+hai|aisi\\s+hai|aise\\s+hai)|"
                    + "main\\s+aise\\s+(?:likhta|bolta)\\s+hu+n?|mai\\s+aise\\s+(?:likhta|bolta)\\s+hu+n?|"
                    + "aise\\s+reply\\s+(?:karna|dena|kiya\\s+karo))\\s*(.*)$");
    private static final Pattern TONE_RE = Pattern.compile(
            "^(?:jarvis\\s+)?(.+?)\\s+(?:ko|se)\\s+(.{3,60}?)\\s+(?:reply|jawab|jawaab)\\s+"
                    + "(?:karna|dena|karo|do|kiya\\s+karo)$");
    private static final Pattern BUSY_STOP = Pattern.compile(
            "\\b(?:main|mai|mein|mera|meri|jarvis|busy|mode|on|chalu|shuru|start|karo|kar|do|dena|abhi|hu|hun|hoon|"
                    + "ho|gaya|hoon|ki|kyunki|kyuki|isliye|bol|bolo|bata|batao|dena|sabko|se)\\b");

    public static boolean isDefaultName(String n) {
        String w = norm(n);
        return w.equals("sab") || w.equals("sabko") || w.equals("baaki") || w.equals("baki") || w.equals("everyone")
                || w.equals("default") || w.contains("anjaan") || w.contains("unknown") || w.contains("sab log")
                || w.contains("baaki sab") || w.equals("sabhi");
    }

    public static Cmd parse(String utterance) {
        Cmd c = new Cmd();
        String w = norm(utterance);
        if (w.length() < 4) {
            return c;
        }
        // ---- busy
        if (w.matches(".*\\bbusy\\b.*") || w.matches(".*\\bab\\s+free\\s+(?:hu|hun|hoon)\\b.*")) {
            boolean off = w.matches(".*\\bbusy\\b.*\\b(?:off|band|khatam|nahi|nhi|nahin)\\b.*")
                    || w.matches(".*\\bab\\s+free\\s+(?:hu|hun|hoon)\\b.*")
                    || w.matches(".*\\b(?:off|band|khatam)\\b.*\\bbusy\\b.*");
            if (off) {
                c.kind = BUSY_OFF;
                return c;
            }
            if (w.contains("busy mode") && w.matches(".*\\b(?:kya|kaise|hai|status)\\b.*")
                    && !w.matches(".*\\b(?:hu|hun|hoon)\\b.*")) {
                c.kind = STATUS;
                return c;
            }
            if (w.matches(".*\\b(?:mode|hu|hun|hoon|ho gaya|ho gya)\\b.*")) {
                c.kind = BUSY_ON;
                String rest = w;
                Matcher d = DURATION.matcher(rest);
                if (d.find()) {
                    int n = 0;
                    try {
                        n = Integer.parseInt(d.group(1));
                    } catch (NumberFormatException ignored) {
                    }
                    boolean hours = d.group(2).startsWith("g") || d.group(2).startsWith("h");
                    if (n > 0) {
                        c.minutes = Math.min(24 * 60, hours ? n * 60 : n);
                    }
                    rest = rest.replace(d.group(0), " ");
                }
                rest = BUSY_STOP.matcher(rest).replaceAll(" ").replaceAll("\\s+", " ").trim();
                c.text = rest;
                return c;
            }
            return c;
        }
        // ---- style sikhana
        Matcher s = STYLE_RE.matcher(w);
        if (s.matches()) {
            c.kind = STYLE_ADD;
            c.text = s.group(1).trim();
            return c;
        }
        if (w.matches(".*\\bmeri\\s+style\\b.*\\b(?:bhool|saaf|hata|delete|reset|mita)\\w*.*")
                || w.matches(".*\\bstyle\\b.*\\b(?:reset|saaf)\\b.*")) {
            c.kind = STYLE_CLEAR;
            return c;
        }
        // ---- tone
        if (w.matches(".*\\b(?:sab|saare|sabhi)\\s+tone\\s+(?:hata|bhool|reset|saaf|mita)\\w*.*")
                || w.matches("^tone\\s+reset.*")) {
            c.kind = TONE_CLEAR;
            return c;
        }
        Matcher t = TONE_RE.matcher(w);
        if (t.matches()) {
            String name = t.group(1).trim();
            String tone = t.group(2).trim();
            String first = tone.split(" ")[0];
            if (first.equals("message") || first.equals("whatsapp") || first.equals("call") || first.equals("msg")
                    || name.length() < 2 || name.matches("^(?:is|iss|isko|ise|iska|ye|yeh|us|usko)$")) {
                return c;
            }
            c.kind = TONE_SET;
            c.name = isDefaultName(name) ? "*" : name;
            c.text = tone;
        }
        return c;
    }

    public static boolean isStyle(String utterance) {
        try {
            return parse(utterance).kind != NONE;
        } catch (Throwable t) {
            return false;
        }
    }

    // ------------------------------------------------------------------ store --
    private static SharedPreferences sp(Context ctx) {
        return ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    private static List<String> readList(Context ctx, String key) {
        List<String> out = new ArrayList<String>();
        try {
            JSONArray a = new JSONArray(sp(ctx).getString(key, "[]"));
            for (int i = 0; i < a.length(); i++) {
                String s = a.optString(i, "");
                if (s.length() > 0) {
                    out.add(s);
                }
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private static void writeList(Context ctx, String key, List<String> l) {
        JSONArray a = new JSONArray();
        for (String s : l) {
            a.put(s);
        }
        sp(ctx).edit().putString(key, a.toString()).apply();
    }

    /** Aapka apna bheja hua message (ya sikhaya hua namuna) yaad rakho. */
    public static synchronized boolean learn(Context ctx, String msg) {
        try {
            String m = msg == null ? "" : msg.trim();
            if (m.length() < 3 || m.matches("^[0-9 +\\-]+$")) {
                return false;
            }
            if (m.length() > 160) {
                m = m.substring(0, 160);
            }
            List<String> all = readList(ctx, "samples");
            for (String s : all) {
                if (norm(s).equals(norm(m))) {
                    return false;
                }
            }
            all.add(m);
            while (all.size() > MAX_SAMPLES) {
                all.remove(0);
            }
            writeList(ctx, "samples", all);
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    public static synchronized int sampleCount(Context ctx) {
        return readList(ctx, "samples").size();
    }

    public static synchronized void clearStyle(Context ctx) {
        sp(ctx).edit().remove("samples").apply();
    }

    public static synchronized void setTone(Context ctx, String name, String tone) {
        String key = norm(name);
        List<String> all = readList(ctx, "tones");
        for (int i = all.size() - 1; i >= 0; i--) {
            if (all.get(i).startsWith(key + "|")) {
                all.remove(i);
            }
        }
        all.add(key + "|" + tone.trim());
        while (all.size() > 80) {
            all.remove(0);
        }
        writeList(ctx, "tones", all);
    }

    public static synchronized void clearTones(Context ctx) {
        sp(ctx).edit().remove("tones").apply();
    }

    /** Is sender ke liye tone ("" = koi nahi). Naam ke koi bhi shabd (3+ akshar) milne par. */
    public static synchronized String toneFor(Context ctx, String sender) {
        String s = " " + norm(sender) + " ";
        String def = "";
        for (String e : readList(ctx, "tones")) {
            int bar = e.indexOf('|');
            if (bar < 0) {
                continue;
            }
            String name = e.substring(0, bar);
            String tone = e.substring(bar + 1);
            if (name.equals("*")) {
                def = tone;
                continue;
            }
            if (s.contains(" " + name + " ")) {
                return tone;
            }
            for (String tok : name.split(" ")) {
                if (tok.length() >= 3 && s.contains(" " + tok + " ")) {
                    return tone;
                }
            }
        }
        return def;
    }

    // ------------------------------------------------------------------- busy --
    public static synchronized void busyOn(Context ctx, String reason, int minutes) {
        long until = System.currentTimeMillis() + Math.max(1, minutes) * 60000L;
        sp(ctx).edit().putString("busy", until + "|" + (reason == null ? "" : reason.trim())).apply();
    }

    public static synchronized void busyOff(Context ctx) {
        sp(ctx).edit().remove("busy").apply();
    }

    /** Busy chalu ho to karan (khaali ho sakta hai), warna null. Samay beet gaya to apne aap band. */
    public static synchronized String busyReason(Context ctx) {
        String v = sp(ctx).getString("busy", "");
        int bar = v.indexOf('|');
        if (bar < 0) {
            return null;
        }
        try {
            long until = Long.parseLong(v.substring(0, bar));
            if (System.currentTimeMillis() > until) {
                sp(ctx).edit().remove("busy").apply();
                return null;
            }
        } catch (NumberFormatException e) {
            return null;
        }
        return v.substring(bar + 1);
    }

    public static synchronized long busyLeftMinutes(Context ctx) {
        String v = sp(ctx).getString("busy", "");
        int bar = v.indexOf('|');
        if (bar < 0) {
            return 0;
        }
        try {
            return Math.max(0, (Long.parseLong(v.substring(0, bar)) - System.currentTimeMillis()) / 60000L);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    // ------------------------------------------------------------ compose helper --
    /** Auto-reply ke system prompt ke aage jodne wala text. Kuch na ho to "". */
    public static String block(Context ctx, String sender) {
        StringBuilder sb = new StringBuilder();
        try {
            List<String> samples = readList(ctx, "samples");
            if (!samples.isEmpty()) {
                sb.append(" SHAKSHM KI APNI STYLE: neeche Shakshm ke khud bheje hue asli messages hain. Reply ke shabd, "
                        + "lambai, Hinglish ka dhang aur emoji bilkul inhi jaise rakho (ye niyam upar ke 'samne wale ki "
                        + "style' wale niyam se zyada zaroori hai): ");
                int from = Math.max(0, samples.size() - USE_SAMPLES);
                for (int i = from; i < samples.size(); i++) {
                    sb.append("[").append(samples.get(i)).append("] ");
                }
            }
            String tone = toneFor(ctx, sender);
            if (tone.length() > 0) {
                sb.append(" Is insaan se baat ka tareeka: ").append(tone).append(" (isi tone me jawab do).");
            }
            String busy = busyReason(ctx);
            if (busy != null) {
                sb.append(" ABHI SHAKSHM BUSY HAI");
                if (busy.length() > 0) {
                    sb.append(" (").append(busy).append(")");
                }
                sb.append(". Reply me chhota sa bata do ki wo abhi busy hain aur free hote hi baat karenge. Iske liye ASK "
                        + "mat likho, par koi wada, samay ya paisa mat batao. Sirf emergency, gambhir ya paise maangne wale "
                        + "message par ASK likho.");
            }
        } catch (Throwable ignored) {
        }
        return sb.toString();
    }
}
