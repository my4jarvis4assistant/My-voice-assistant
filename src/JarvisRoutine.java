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
 * Subah ka briefing, mausam, routines ("good night") aur driving mode: bole hue vaakya ka matlab nikalna
 * aur routines / driving ki yaaddasht. Is class me Android ka kaam sirf SharedPreferences hai.
 */
public final class JarvisRoutine {
    private JarvisRoutine() {
    }

    private static final String PREF = "jarvis_routine";

    public static final int NONE = 0, BRIEF = 1, WEATHER = 2, SET_CITY = 3, SCHED_ON = 4, SCHED_OFF = 5, CREATE = 6,
            LIST = 7, DELETE = 8, DRIVE_ON = 9, DRIVE_OFF = 10;

    public static final class Cmd {
        public int kind = NONE;
        public String text = "";     // shehar / routine ka naam
        public int minutes = 0;      // briefing ka samay (din ke minute) ya driving kitni der
    }

    public static final class Action {
        public String type = "";     // vol dnd torch open alarm brief busy drive
        public String arg = "";
        public int n = 0;
    }

    static String norm(String s) {
        if (s == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (char ch : s.toLowerCase(Locale.ENGLISH).toCharArray()) {
            sb.append(Character.isLetterOrDigit(ch) ? ch : ' ');
        }
        return sb.toString().trim().replaceAll("\\s+", " ");
    }

    // ----------------------------------------------------------------- samay --
    private static final Pattern TIME = Pattern.compile("\\b(\\d{1,2})(?:\\s+(\\d{2}))?\\s*(baje|bje|am|pm)\\b");

    /** "subah 7 baje", "shaam 6 30 baje", "raat 11 baje" -> din ke minute. -1 = samay nahi mila. */
    public static int parseTime(String utterance) {
        String w = norm(utterance);
        Matcher m = TIME.matcher(w);
        while (m.find()) {
            int h, mi = 0;
            try {
                h = Integer.parseInt(m.group(1));
                if (m.group(2) != null) {
                    mi = Integer.parseInt(m.group(2));
                }
            } catch (NumberFormatException e) {
                continue;
            }
            if (h > 23 || mi > 59) {
                continue;
            }
            boolean pm = "pm".equals(m.group(3)) || w.matches(".*\\b(?:shaam|sham|evening|dopahar|afternoon)\\b.*");
            boolean night = w.matches(".*\\b(?:raat|night)\\b.*");
            boolean am = "am".equals(m.group(3)) || w.matches(".*\\b(?:subah|savere|morning)\\b.*");
            if (pm && !am && h < 12 && !(h == 12)) {
                h += 12;
            } else if (night && !am) {
                if (h == 12) {
                    h = 0;
                } else if (h >= 6 && h < 12) {
                    h += 12;
                }
            } else if (am && h == 12) {
                h = 0;
            }
            return h * 60 + mi;
        }
        return -1;
    }

    private static int durationMinutes(String w, int def) {
        Matcher d = Pattern.compile("(\\d+)\\s*(ghante|ghanta|ghantey|ghanto|hour|hours|hr|hrs|minute|minutes|min|mins)\\b")
                .matcher(w);
        if (d.find()) {
            try {
                int n = Integer.parseInt(d.group(1));
                boolean hours = d.group(2).startsWith("g") || d.group(2).startsWith("h");
                if (n > 0) {
                    return Math.min(24 * 60, hours ? n * 60 : n);
                }
            } catch (NumberFormatException ignored) {
            }
        }
        return def;
    }

    // ------------------------------------------------------------------ parse --
    private static final Pattern CREATE_A = Pattern.compile(
            "^(?:jarvis\\s+)?(?:ek\\s+)?(?:nayi\\s+|new\\s+)?routine\\s+(?:banao|bana\\s+do|banana|banani|create|add\\s+karo|add)"
                    + "(?:\\s+(.+))?$");
    private static final Pattern CREATE_B = Pattern.compile("^(?:jarvis\\s+)?(.+?)\\s+routine\\s+(?:banao|bana\\s+do)$");
    private static final Pattern DELETE_A = Pattern.compile(
            "^(?:jarvis\\s+)?routine\\s+(.+?)\\s+(?:hata|delete|mita|remove|khatam)\\w*(?:\\s+(?:do|karo|dena))?$");
    private static final Pattern DELETE_B = Pattern.compile(
            "^(?:jarvis\\s+)?(.+?)\\s+routine\\s+(?:hata|delete|mita|remove|khatam)\\w*(?:\\s+(?:do|karo|dena))?$");
    private static final Pattern CITY_A = Pattern.compile(
            "^(?:jarvis\\s+)?(?:mera|meri|apna)\\s+(?:shehar|sheher|city|shahar)\\s+(.+?)(?:\\s+(?:hai|he|h|rakho|set\\s+karo))?$");
    private static final Pattern CITY_B = Pattern.compile(
            "^(?:jarvis\\s+)?(?:main|mai|mein)\\s+(.+?)\\s+(?:me|mein)\\s+rehta\\s+(?:hu|hun|hoon)$");
    private static final Pattern CITY_C = Pattern.compile(
            "^(?:jarvis\\s+)?(?:mausam|weather)\\s+ke\\s+liye\\s+(?:shehar\\s+|city\\s+)?(.+?)\\s+(?:rakho|set\\s+karo|chuno)$");
    private static final Pattern WEATHER_CITY = Pattern.compile(
            "(?:^|\\s)([a-z]{3,20})\\s+(?:ka|ki|me|mein)\\s+(?:aaj\\s+ka\\s+)?(?:mausam|weather)");

    public static Cmd parse(String utterance) {
        Cmd c = new Cmd();
        String w = norm(utterance);
        if (w.length() < 4) {
            return c;
        }
        // ---- driving mode
        boolean driveOff = w.matches(".*\\bdriving\\s+mode\\s+(?:off|band|khatam|bund).*")
                || w.matches(".*\\bdriving\\s+(?:off|band|khatam|bund).*")
                || w.matches(".*\\b(?:off|band|khatam)\\s+driving\\s+mode.*")
                || w.matches(".*\\b(?:gaadi|gadi|gaadee|car)\\s+se\\s+utar.*")
                || w.matches(".*\\b(?:gaadi|gadi|car)\\s+(?:nahi|nhi)\\s+chala.*")
                || w.matches(".*\\bdrive\\s+(?:khatam|band).*");
        if (driveOff) {
            c.kind = DRIVE_OFF;
            return c;
        }
        boolean driveOn = w.matches(".*\\bdriving\\s+mode\\b.*") || w.matches(".*\\b(?:gaadi|gadi|car)\\s+chala\\s+(?:raha|rahi|rha|rhi)\\b.*")
                || w.matches(".*\\bdrive\\s+kar\\s+(?:raha|rahi|rha|rhi)\\b.*");
        if (driveOn) {
            c.kind = DRIVE_ON;
            c.minutes = durationMinutes(w, 240);
            return c;
        }
        // ---- routine banana / dikhana / hatana
        Matcher m = CREATE_A.matcher(w);
        if (m.matches()) {
            c.kind = CREATE;
            c.text = m.group(1) == null ? "" : m.group(1).trim();
            return c;
        }
        m = CREATE_B.matcher(w);
        if (m.matches()) {
            c.kind = CREATE;
            c.text = m.group(1).trim();
            return c;
        }
        if (w.contains("routine") && w.matches(".*\\b(?:batao|dikhao|sunao|list|kaun\\s+kaun|kitni)\\b.*")) {
            c.kind = LIST;
            return c;
        }
        m = DELETE_A.matcher(w);
        if (!m.matches()) {
            m = DELETE_B.matcher(w);
        }
        if (m.matches()) {
            c.kind = DELETE;
            c.text = m.group(1).trim();
            return c;
        }
        // ---- shehar
        m = CITY_A.matcher(w);
        if (!m.matches()) {
            m = CITY_B.matcher(w);
        }
        if (!m.matches()) {
            m = CITY_C.matcher(w);
        }
        if (m.matches() && m.group(1).trim().length() >= 3 && m.group(1).trim().split(" ").length <= 3) {
            c.kind = SET_CITY;
            c.text = m.group(1).trim();
            return c;
        }
        // ---- briefing
        if (w.contains("briefing") || w.matches(".*\\bbrief\\b.*")) {
            boolean daily = w.matches(".*\\b(?:roz|rozana|har\\s+din|daily|every\\s+day|hamesha)\\b.*");
            boolean off = w.matches(".*\\b(?:band|hata|cancel|off|mat|nahi|nhi|delete|mita)\\w*.*");
            if (daily && off) {
                c.kind = SCHED_OFF;
                return c;
            }
            if (daily) {
                int t = parseTime(w);
                if (t >= 0) {
                    c.kind = SCHED_ON;
                    c.minutes = t;
                }
                return c;                      // samay bina "roz ..." = samajh nahi aaya, Gemini ko mat do
            }
            if (off) {
                c.kind = SCHED_OFF;                // "briefing band karo" = roz wali briefing band
                return c;
            }
            if (w.matches(".*\\b(?:do|dena|sunao|batao|chalao|karo|suna|de|chaliye|start|shuru|sunna)\\b.*")) {
                c.kind = BRIEF;
            }
            return c;
        }
        if (w.equals("good morning") || w.equals("good morning jarvis") || w.equals("gm jarvis")
                || w.equals("suprabhat") || w.equals("suprabhat jarvis")) {
            c.kind = BRIEF;
            return c;
        }
        // ---- mausam
        if (w.matches(".*\\b(?:mausam|weather|tapman|temperature)\\b.*")
                && !w.matches(".*\\b(?:gana|song|play|video|youtube|search|dhundo|dhoondo|kholo|app|widget)\\b.*")
                && w.matches(".*\\b(?:kaisa|kaisi|kya|batao|bata|hai|hain|aaj|abhi|sunao|bolo)\\b.*")) {
            c.kind = WEATHER;
            Matcher wc = WEATHER_CITY.matcher(w);
            if (wc.find()) {
                String city = wc.group(1);
                if (!city.matches("aaj|abhi|ye|yeh|is|yahan|mera|meri|apna|bahar|ka|ki")) {
                    c.text = city;
                }
            }
            return c;
        }
        return c;
    }

    public static boolean isCmd(String utterance) {
        try {
            return parse(utterance).kind != NONE;
        } catch (Throwable t) {
            return false;
        }
    }

    // ---------------------------------------------------------------- actions --
    /** Routine ka ek kaam samjho: "volume 20 percent", "dnd on", "spotify kholo", "subah 6 baje alarm"... null = samajh nahi aaya. */
    public static Action parseAction(String phrase) {
        String w = norm(phrase);
        if (w.length() < 2) {
            return null;
        }
        Action a = new Action();
        boolean off = w.matches(".*\\b(?:off|band|hata|khatam|nahi|disable|bund)\\b.*");
        if (w.contains("volume") || w.contains("awaaz") || w.contains("awaz")) {
            a.type = "vol";
            Matcher m = Pattern.compile("\\b(\\d{1,3})\\b").matcher(w);
            if (m.find()) {
                a.n = Math.min(100, Integer.parseInt(m.group(1)));
            } else if (w.matches(".*\\b(?:full|max|maximum|poora|pura|tez|zyada)\\b.*")) {
                a.n = 100;
            } else if (w.matches(".*\\b(?:mute|zero|silent|band)\\b.*")) {
                a.n = 0;
            } else if (w.matches(".*\\b(?:kam|low|dheema|dhima|halka|dheemi)\\b.*")) {
                a.n = 20;
            } else if (w.matches(".*\\b(?:medium|beech|aadha|normal)\\b.*")) {
                a.n = 50;
            } else {
                return null;
            }
            return a;
        }
        if (w.contains("dnd") || w.contains("do not disturb") || w.matches(".*\\bsilent\\s+mode\\b.*")
                || w.matches(".*\\bdisturb\\b.*")) {
            a.type = "dnd";
            a.n = off ? 0 : 1;
            return a;
        }
        if (w.matches(".*\\b(?:torch|flashlight|flash)\\b.*")) {
            a.type = "torch";
            a.n = off ? 0 : 1;
            return a;
        }
        if (w.contains("briefing")) {
            a.type = "brief";
            return a;
        }
        if (w.contains("busy")) {
            JarvisStyle.Cmd b = JarvisStyle.parse(phrase);
            if (b.kind == JarvisStyle.BUSY_ON) {
                a.type = "busy";
                a.n = b.minutes;
                a.arg = b.text;
                return a;
            }
            if (b.kind == JarvisStyle.BUSY_OFF) {
                a.type = "busy";
                a.n = 0;
                return a;
            }
            return null;
        }
        if (w.matches(".*\\b(?:driving|drive|gaadi)\\b.*")) {
            a.type = "drive";
            a.n = off ? 0 : 1;
            return a;
        }
        if (w.contains("alarm")) {
            int t = parseTime(w);
            if (t < 0) {
                return null;
            }
            a.type = "alarm";
            a.n = t;
            return a;
        }
        Matcher o = Pattern.compile("^(?:app\\s+)?(.+?)\\s+(?:app\\s+)?(?:kholo|khol|open|chalu\\s+karo|chalao|start\\s+karo|lagao)$")
                .matcher(w);
        if (!o.matches()) {
            o = Pattern.compile("^(?:open|kholo)\\s+(.+)$").matcher(w);
        }
        if (o.matches() && o.group(1).trim().length() >= 2) {
            a.type = "open";
            a.arg = o.group(1).trim();
            return a;
        }
        return null;
    }

    public static boolean isEnd(String utterance) {
        String w = norm(utterance);
        return w.matches("^(?:bas|bas\\s+itna|itna\\s+hi|ho\\s+gaya|ho\\s+gya|khatam|done|save|save\\s+karo|bas\\s+ho\\s+gaya|"
                + "bas\\s+itna\\s+hi|aur\\s+kuch\\s+nahi|aur\\s+nahi|nahi\\s+bas)$");
    }

    // ------------------------------------------------------------------ store --
    private static SharedPreferences sp(Context ctx) {
        return ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    private static List<String> readList(Context ctx) {
        List<String> out = new ArrayList<String>();
        try {
            JSONArray a = new JSONArray(sp(ctx).getString("list", "[]"));
            for (int i = 0; i < a.length(); i++) {
                String s = a.optString(i, "");
                if (s.indexOf('|') > 0) {
                    out.add(s);
                }
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private static void writeList(Context ctx, List<String> l) {
        JSONArray a = new JSONArray();
        for (String s : l) {
            a.put(s);
        }
        sp(ctx).edit().putString("list", a.toString()).apply();
    }

    private static String[] builtin(String name) {
        if (name.equals("good night")) {
            return new String[]{"dnd on", "volume 15 percent"};
        }
        return null;
    }

    public static synchronized void save(Context ctx, String name, List<String> actions) {
        String n = norm(name);
        List<String> all = readList(ctx);
        for (int i = all.size() - 1; i >= 0; i--) {
            if (all.get(i).startsWith(n + "|")) {
                all.remove(i);
            }
        }
        StringBuilder sb = new StringBuilder(n).append('|');
        for (int i = 0; i < actions.size(); i++) {
            sb.append(i > 0 ? ";;" : "").append(actions.get(i).replace("|", " ").replace(";;", " "));
        }
        all.add(sb.toString());
        while (all.size() > 30) {
            all.remove(0);
        }
        writeList(ctx, all);
    }

    public static synchronized boolean delete(Context ctx, String name) {
        String n = norm(name);
        List<String> all = readList(ctx);
        boolean hit = false;
        for (int i = all.size() - 1; i >= 0; i--) {
            if (all.get(i).startsWith(n + "|")) {
                all.remove(i);
                hit = true;
            }
        }
        if (hit) {
            writeList(ctx, all);
        }
        return hit;
    }

    public static synchronized List<String> names(Context ctx) {
        List<String> out = new ArrayList<String>();
        for (String e : readList(ctx)) {
            out.add(e.substring(0, e.indexOf('|')));
        }
        if (!out.contains("good night")) {
            out.add("good night");
        }
        return out;
    }

    /** Routine ke kaam (phrases). null = aisi routine nahi. */
    public static synchronized List<String> get(Context ctx, String name) {
        String n = norm(name);
        for (String e : readList(ctx)) {
            if (e.startsWith(n + "|")) {
                List<String> out = new ArrayList<String>();
                for (String p : e.substring(e.indexOf('|') + 1).split(";;")) {
                    if (p.trim().length() > 0) {
                        out.add(p.trim());
                    }
                }
                return out;
            }
        }
        String[] b = builtin(n);
        if (b != null) {
            List<String> out = new ArrayList<String>();
            for (String p : b) {
                out.add(p);
            }
            return out;
        }
        return null;
    }

    /** Bole hue vaakya se chalane wali routine ka naam (ya null). */
    public static String findRun(Context ctx, String utterance) {
        String w = norm(utterance);
        if (w.length() < 2) {
            return null;
        }
        for (String n : names(ctx)) {
            String q = Pattern.quote(n);
            if (w.equals(n) || w.equals("jarvis " + n) || w.replace(" ", "").equals(n.replace(" ", ""))
                    || w.matches("^(?:jarvis\\s+)?" + q + "\\s+routine(?:\\s+(?:chalao|chalu|start|lagao|run|karo|shuru).*)?$")
                    || w.matches("^(?:jarvis\\s+)?routine\\s+" + q + "(?:\\s+(?:chalao|chalu|start|lagao|run|karo|shuru).*)?$")
                    || w.matches("^(?:jarvis\\s+)?" + q + "\\s+(?:chalao|chalu\\s+karo|start\\s+karo|lagao)$")) {
                return n;
            }
        }
        return null;
    }

    // ---------------------------------------------------------------- driving --
    public static void setDriving(Context ctx, int minutes) {
        sp(ctx).edit().putLong("drive_until", System.currentTimeMillis() + Math.max(1, minutes) * 60000L).apply();
    }

    public static void clearDriving(Context ctx) {
        sp(ctx).edit().remove("drive_until").apply();
    }

    public static boolean driving(Context ctx) {
        try {
            long u = sp(ctx).getLong("drive_until", 0);
            if (u <= 0) {
                return false;
            }
            if (System.currentTimeMillis() > u) {
                sp(ctx).edit().remove("drive_until").apply();
                return false;
            }
            return true;
        } catch (Throwable t) {
            return false;
        }
    }
}
