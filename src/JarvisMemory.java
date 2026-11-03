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
 * Yaaddasht: "yaad rakho ki mere papa ka birthday 5 March ko hai".
 * Baatein phone me hi rehti hain (SharedPreferences) aur Gemini ko har baat-cheet me di jaati hain.
 * Samajhne wala hissa (parse) me Android nahi hai.
 */
public final class JarvisMemory {
    private JarvisMemory() {
    }

    private static final String PREF = "jarvis_mem";
    private static final String KEY = "facts";
    private static final int MAX_FACTS = 60;
    private static final int MAX_LEN = 300;

    public static final int NONE = 0, REMEMBER = 1, RECALL = 2, FORGET_ALL = 3, FORGET_ONE = 4;

    public static final class Cmd {
        public int kind = NONE;
        public String fact = "";
    }

    private static final Pattern REMEMBER_RE = Pattern.compile(
            "^(?:jarvis\\s+)?(?:ye\\s+|isko\\s+|is\\s+baat\\s+ko\\s+)?(?:yaad|yad)\\s+"
                    + "(?:rakh\\w*|kar\\s*l\\w*|karlo|rakhna)\\s*(?:ki\\s+|k\\s+)?(.*)$");
    private static final Pattern REMEMBER_EN = Pattern.compile("^(?:jarvis\\s+)?remember\\s+(?:that\\s+)?(.*)$");
    private static final Pattern FORGET_RE = Pattern.compile(
            "^(?:jarvis\\s+)?(.*?)\\s*(?:bhool|bhul)\\s*(?:jao|jaao|jaiye|jaye)\\s*(?:ki\\s+)?(.*)$");

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

    /** Bole hue vaakya se yaaddasht ka kaam nikalo (kind == NONE: ye iska kaam nahi). */
    public static Cmd parse(String utterance) {
        Cmd c = new Cmd();
        String w = norm(utterance);
        if (w.length() == 0) {
            return c;
        }
        Matcher m = REMEMBER_RE.matcher(w);
        if (!m.matches()) {
            m = REMEMBER_EN.matcher(w);
        }
        if (m.matches()) {
            c.kind = REMEMBER;
            c.fact = m.group(1).trim();
            return c;
        }
        // kya yaad hai / meri yaaddasht
        if ((w.contains("kya") && (w.contains("yaad hai") || w.contains("yad hai") || w.contains("yaad rakha")))
                || w.matches(".*\\b(?:meri|apni|teri|tumhari)\\s+yaaddasht\\b.*")
                || w.matches(".*\\byaaddasht\\s+(?:sunao|batao|bolo|dikhao)\\b.*")) {
            c.kind = RECALL;
            return c;
        }
        // bhool jao
        if (w.contains("yaaddasht") && w.matches(".*\\b(?:saaf|mita|delete|clear|khali|hata)\\w*.*")) {
            c.kind = FORGET_ALL;
            return c;
        }
        Matcher f = FORGET_RE.matcher(w);
        if (f.matches()) {
            String before = f.group(1).trim();
            String after = f.group(2).trim();
            boolean all = before.matches(".*\\bsab\\b.*") || after.matches("^(?:sab|sab kuch|sabkuch|saari baatein|sari baatein)$")
                    || after.length() == 0 && before.matches(".*\\bsab(?: kuch)?\\b.*");
            if (all) {
                c.kind = FORGET_ALL;
            } else if (after.length() >= 3) {
                c.kind = FORGET_ONE;
                c.fact = after;
            }
        }
        return c;
    }

    public static boolean isMemory(String utterance) {
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

    public static synchronized List<String> list(Context ctx) {
        List<String> out = new ArrayList<String>();
        try {
            JSONArray a = new JSONArray(sp(ctx).getString(KEY, "[]"));
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

    private static void save(Context ctx, List<String> facts) {
        JSONArray a = new JSONArray();
        for (String s : facts) {
            a.put(s);
        }
        sp(ctx).edit().putString(KEY, a.toString()).apply();
    }

    /** true = nayi baat judi (pehle se wahi ho to false). */
    public static synchronized boolean add(Context ctx, String fact) {
        String f = fact == null ? "" : fact.trim();
        if (f.length() == 0) {
            return false;
        }
        if (f.length() > MAX_LEN) {
            f = f.substring(0, MAX_LEN);
        }
        List<String> all = list(ctx);
        for (String s : all) {
            if (norm(s).equals(norm(f))) {
                return false;
            }
        }
        all.add(f);
        while (all.size() > MAX_FACTS) {
            all.remove(0);
        }
        save(ctx, all);
        return true;
    }

    public static synchronized void clear(Context ctx) {
        sp(ctx).edit().remove(KEY).apply();
    }

    /** Bole hue shabdon se sabse milti baat hatao. Hatayi gayi baat (ya "" agar koi nahi mili). */
    public static synchronized String forget(Context ctx, String about) {
        List<String> all = list(ctx);
        String[] want = norm(about).split(" ");
        int bestIdx = -1, best = 0;
        for (int i = 0; i < all.size(); i++) {
            String n = " " + norm(all.get(i)) + " ";
            int hit = 0;
            for (String t : want) {
                if (t.length() >= 3 && n.contains(" " + t)) {
                    hit++;
                }
            }
            if (hit > best) {
                best = hit;
                bestIdx = i;
            }
        }
        if (bestIdx < 0) {
            return "";
        }
        String gone = all.remove(bestIdx);
        save(ctx, all);
        return gone;
    }

    /** Gemini ke system prompt me jodne ke liye. Khaali ho to "". */
    public static String block(Context ctx) {
        List<String> all = list(ctx);
        if (all.isEmpty()) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(" User ne tumhe ye baatein yaad rakhne ko kahi hain (zaroorat ho tabhi inka istemaal karo, "
                + "bina poochhe dohrao mat): ");
        for (int i = 0; i < all.size(); i++) {
            sb.append(i + 1).append(") ").append(all.get(i)).append(". ");
        }
        return sb.toString();
    }

    /** Sunane layak yaaddasht ki list. */
    public static String speak(Context ctx) {
        List<String> all = list(ctx);
        if (all.isEmpty()) {
            return "Abhi mujhe aapki koi khaas baat yaad nahi hai. Bolo, yaad rakho ki...";
        }
        StringBuilder sb = new StringBuilder("Mujhe ye yaad hai. ");
        int from = Math.max(0, all.size() - 8);
        for (int i = from; i < all.size(); i++) {
            sb.append(all.get(i)).append(". ");
        }
        if (from > 0) {
            sb.append("Aur ").append(from).append(" baatein aur hain.");
        }
        return sb.toString().trim();
    }
}
