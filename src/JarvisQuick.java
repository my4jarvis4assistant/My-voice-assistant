package org.myassistant.myvoiceassistant;

import java.util.Calendar;
import java.util.List;
import java.util.Locale;

/**
 * Chhote lekin kaam ke commands (bina internet, turant jawab):
 *  - Notes / to-do list: "note karo kal dudh lana hai", "meri notes sunao", "list se dudh hata do", "saare notes delete karo"
 *  - Samay aur tareekh: "kitne baje hain", "aaj kaun sa din hai"
 *  - Battery: "battery kitni hai" (jawab service banati hai, yahan "@battery" lautta hai)
 * Pure Java hai (Android nahi chahiye) taaki aasani se test ho sake.
 */
public final class JarvisQuick {
    private JarvisQuick() {
    }

    private static String norm(String s) {
        StringBuilder sb = new StringBuilder();
        for (char ch : (s == null ? "" : s).toLowerCase(Locale.ENGLISH).toCharArray()) {
            sb.append(Character.isLetterOrDigit(ch) ? ch : ' ');
        }
        return sb.toString().trim().replaceAll("\\s+", " ");
    }

    private static boolean has(String w, String... words) {
        for (String x : words) {
            if (w.contains(" " + x + " ")) {
                return true;
            }
        }
        return false;
    }

    /**
     * @param items  saved notes (is list ko badalta hai)
     * @param changed [0]=true agar items badle (tab service ise save kare)
     * @return jawab ka text, ya null agar ye in commands me se nahi hai. "@battery" = battery batao.
     */
    public static String handle(String text, List<String> items, Calendar now, boolean[] changed) {
        String n = norm(text);
        if (n.length() < 3) {
            return null;
        }
        String w = " " + n + " ";

        // ---- battery
        if (has(w, "battery", "bettery", "batri") && has(w, "kitni", "kitna", "level", "percent", "kya", "hai", "status",
                "charge", "charging", "bachi", "bacha")) {
            return "@battery";
        }
        // ---- samay / tareekh
        if (has(w, "kitne") && has(w, "baje") && !has(w, "alarm", "timer", "reminder")) {
            return "Abhi " + clock(now) + " baj rahe hain.";
        }
        if ((has(w, "time", "samay", "waqt") && has(w, "kya", "kitna", "bata", "batao", "hua", "hai"))
                && !has(w, "alarm", "timer", "reminder", "set", "laga", "lagao", "next", "kitni", "bar", "baar")) {
            return "Abhi " + clock(now) + " baj rahe hain.";
        }
        if (has(w, "aaj") && has(w, "date", "tareekh", "tarikh", "din", "taarikh") && !has(w, "alarm", "reminder", "set")
                && has(w, "kya", "kaun", "kon", "kaunsa", "batao", "bata", "hai")) {
            return "Aaj " + dateText(now) + " hai.";
        }

        // ---- notes / to-do
        boolean kw = has(w, "note", "notes", "nots", "todo", "to do", "list");
        if (!kw) {
            return null;
        }
        boolean listWord = has(w, "list") && !has(w, "note", "notes", "nots", "todo", "to do");
        // list akela tabhi jab to-do/kaam/shopping jaisa sandarbh ho (warna "playlist"/"contact list" se takkar na ho)
        if (listWord && !has(w, "kaam", "kaamon", "shopping", "grocery", "task", "tasks", "bazaar", "saman")) {
            return null;
        }
        boolean remove = has(w, "hata", "hatao", "hata do", "delete", "mita", "mitao", "clear", "remove", "nikal", "nikalo");
        boolean read = has(w, "sunao", "batao", "bata", "padho", "padh", "dikhao", "dikha", "kya", "kitne", "read", "show");
        boolean add = has(w, "karo", "kar", "kr", "likho", "likh", "add", "jodo", "jod", "daalo", "dalo", "dal", "save",
                "banao", "bana", "rakho", "rakh");
        boolean all = has(w, "saare", "sare", "sab", "saari", "poori", "puri", "all", "sabhi");

        if (remove) {
            if (all) {
                int c = items.size();
                if (c == 0) {
                    return "Aapki notes pehle se khaali hain.";
                }
                items.clear();
                changed[0] = true;
                return c == 1 ? "Note hata diya." : "Saari " + c + " notes hata di.";
            }
            String key = stripFillers(n);
            int idx = ordinal(n);
            if (idx >= 1 && idx <= items.size()) {
                String gone = items.remove(idx - 1);
                changed[0] = true;
                return "Note " + idx + " hata diya: " + gone + ".";
            }
            if (key.length() >= 2) {
                for (int i = 0; i < items.size(); i++) {
                    if (items.get(i).toLowerCase(Locale.ENGLISH).contains(key)) {
                        String gone = items.remove(i);
                        changed[0] = true;
                        return "Hata diya: " + gone + ".";
                    }
                }
                return "Notes me '" + key + "' wala kuch nahi mila.";
            }
            return "Kaun sa note hata'u? Jaise bolo: dudh wala note hata do, ya saare notes hata do.";
        }
        if (read && !add) {
            if (items.isEmpty()) {
                return "Abhi koi note nahi hai.";
            }
            StringBuilder sb = new StringBuilder("Aapke " + items.size() + " notes hain. ");
            for (int i = 0; i < items.size() && i < 8; i++) {
                sb.append(i + 1).append(". ").append(items.get(i)).append(". ");
            }
            if (items.size() > 8) {
                sb.append("Baaki bhi hain.");
            }
            return sb.toString().trim();
        }
        if (add) {
            String body = stripFillers(n);
            if (body.length() < 3) {
                return "Kya likhna hai? Jaise bolo: note karo kal dudh lana hai.";
            }
            String shown = body.substring(0, 1).toUpperCase(Locale.ENGLISH) + body.substring(1);
            items.add(shown);
            changed[0] = true;
            return "Note kar liya: " + shown + ". Ab aapke " + items.size() + " notes hain.";
        }
        return null;
    }

    private static final java.util.Set<String> STRONG = new java.util.HashSet<String>(java.util.Arrays.asList(
            "note", "notes", "nots", "todo", "list", "karo", "kar", "kr", "likho", "likh", "add", "jodo", "jod",
            "daalo", "dalo", "dal", "save", "banao", "bana", "rakho", "rakh", "hata", "hatao", "delete", "mita", "mitao",
            "clear", "remove", "nikal", "nikalo", "dena", "dijiye", "kijiye", "naya", "nayi", "nai", "new", "yaad",
            "kaam", "kaamon", "task", "tasks", "pehla", "doosra", "dusra", "teesra", "tisra", "pehle", "last", "aakhri",
            "number", "no", "wa", "va"));
    private static final java.util.Set<String> WEAK = new java.util.HashSet<String>(java.util.Arrays.asList(
            "ki", "ka", "ke", "ko", "se", "me", "mein", "mei", "men", "mai", "par", "pe", "per", "ye", "yeh", "wo", "vo",
            "isko", "ise", "mere", "meri", "mera", "mujhe", "ek", "bhi", "zara", "please", "plz", "jarvis", "wala", "wali",
            "to", "do", "lo", "de", "that"));
    private static final java.util.Set<String> VERBS = new java.util.HashSet<String>(java.util.Arrays.asList(
            "karo", "kar", "kr", "likho", "likh", "add", "jodo", "jod", "daalo", "dalo", "dal", "hata", "hatao", "delete",
            "mita", "mitao", "clear", "remove", "nikal", "nikalo", "rakho", "rakh", "banao", "bana", "save"));

    private static String stripFillers(String n) {
        String[] tok = n.split(" ");
        java.util.List<String> out = new java.util.ArrayList<String>();
        for (int i = 0; i < tok.length; i++) {
            String t = tok[i];
            if (t.length() == 0 || STRONG.contains(t) || t.matches("\\d+(st|nd|rd|th)?")) {
                continue;
            }
            // "kar do / hata do / likh lo": verb ke baad ka do/lo/de bhi hatao, baaki jagah rehne do ("do kilo aata")
            if ((t.equals("do") || t.equals("lo") || t.equals("de")) && i > 0 && VERBS.contains(tok[i - 1])) {
                continue;
            }
            out.add(t);
        }
        while (!out.isEmpty() && WEAK.contains(out.get(0))) {
            out.remove(0);
        }
        while (!out.isEmpty() && WEAK.contains(out.get(out.size() - 1))) {
            out.remove(out.size() - 1);
        }
        StringBuilder sb = new StringBuilder();
        for (String t : out) {
            sb.append(sb.length() > 0 ? " " : "").append(t);
        }
        return sb.toString().trim();
    }

    /** "pehla note hata do", "2 number wala note hata do" -> 1 / 2. Nahi mila to 0. */
    private static int ordinal(String n) {
        if (n.contains("pehla") || n.contains("pehle")) {
            return 1;
        }
        if (n.contains("doosra") || n.contains("dusra")) {
            return 2;
        }
        if (n.contains("teesra") || n.contains("tisra")) {
            return 3;
        }
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("(?:^| )(\\d{1,2})(?: number| no| wa| va)").matcher(n);
        if (m.find()) {
            return Integer.parseInt(m.group(1));
        }
        return 0;
    }

    private static String clock(Calendar c) {
        int h = c.get(Calendar.HOUR);
        if (h == 0) {
            h = 12;
        }
        int m = c.get(Calendar.MINUTE);
        String ap = c.get(Calendar.AM_PM) == Calendar.AM ? "subah" : (c.get(Calendar.HOUR_OF_DAY) < 16 ? "dopahar"
                : (c.get(Calendar.HOUR_OF_DAY) < 20 ? "shaam" : "raat"));
        if (c.get(Calendar.HOUR_OF_DAY) < 4) {
            ap = "raat";
        }
        return ap + " ke " + h + ":" + (m < 10 ? "0" + m : String.valueOf(m));
    }

    private static String dateText(Calendar c) {
        String[] days = {"Ravivar", "Somvar", "Mangalvar", "Budhvar", "Guruvar", "Shukravar", "Shanivar"};
        String[] mons = {"January", "February", "March", "April", "May", "June", "July", "August", "September",
                "October", "November", "December"};
        return days[c.get(Calendar.DAY_OF_WEEK) - 1] + ", " + c.get(Calendar.DAY_OF_MONTH) + " "
                + mons[c.get(Calendar.MONTH)] + " " + c.get(Calendar.YEAR);
    }
}
