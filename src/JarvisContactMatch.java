package org.myassistant.myvoiceassistant;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Naam se contact dhoondhne ka dimaag. Android par nirbhar nahi (sirf Java), isliye alag se test ho sakta hai.
 * - "jarvis saket ko call kro" se sirf "saket" nikalta hai
 * - "saket jha(gau)" jaise saved naam se Hinglish spelling ka fark (saket/sakit/sakeet) maaf karke match karta hai
 * - "2 ko call karo", "dusra", "second" jaise chunav samajhta hai
 */
public final class JarvisContactMatch {
    private JarvisContactMatch() {
    }

    public static final class Contact {
        public final String name;
        public final String number;

        public Contact(String name, String number) {
            this.name = name;
            this.number = number;
        }
    }

    public static final class Scored {
        public final Contact contact;
        public final double score;

        Scored(Contact c, double s) {
            contact = c;
            score = s;
        }
    }

    private static final Set<String> CALL_WORDS = new HashSet<String>(Arrays.asList(
            "call", "calls", "kall", "caal", "kaal", "cal", "dial", "phone", "fone", "milao", "milana",
            "lagao", "laga", "lagana", "lagado", "lagade", "lagadena"));

    private static final Set<String> FILLER = new HashSet<String>(Arrays.asList(
            "jarvis", "hey", "hello", "hi", "ok", "okay", "please", "plz", "ko", "ka", "ki", "ke", "se",
            "kro", "karo", "kar", "karna", "kariye", "kijiye", "karein", "krna", "kre", "kare", "kardo", "kardena",
            "do", "de", "dena", "dijiye", "diye", "dial", "phone", "fone", "mobile", "number", "mujhe",
            "mera", "meri", "mere", "hume", "humko", "contact", "naam", "wale", "wali", "wala", "ek", "zara",
            "jara", "abhi", "now", "to", "tu", "pe", "par", "on", "me", "mein", "karke", "phir", "can", "you",
            "could", "will", "make", "a", "the", "call", "calls", "kall", "caal", "kaal", "cal", "milao",
            "milana", "lagao", "laga", "lagana", "lagado", "lagade", "lagadena", "baat", "karni", "karwa",
            "karwao", "krdo", "krde", "kr", "bol", "bolo", "bulao", "bula"));

    /** In shabdon ke saath vaakya call ka nahi, kisi aur kaam ka hai. */
    private static final Set<String> NOT_A_CALL = new HashSet<String>(Arrays.asList(
            "open", "kholo", "khol", "launch", "alarm", "timer", "remind", "reminder", "note", "settings",
            "setting", "search", "youtube", "play", "message", "sms", "whatsapp", "send", "install", "volume",
            "wifi", "bluetooth", "torch", "flashlight", "brightness", "history", "log", "logs", "recent"));

    // --------------------------------------------------------------- tokens --
    static List<String> words(String s) {
        List<String> out = new ArrayList<String>();
        if (s == null) {
            return out;
        }
        String low = s.toLowerCase(Locale.ENGLISH);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < low.length(); i++) {
            char ch = low.charAt(i);
            if (Character.isLetterOrDigit(ch)) {
                sb.append(ch);
            } else if (sb.length() > 0) {
                out.add(sb.toString());
                sb.setLength(0);
            }
        }
        if (sb.length() > 0) {
            out.add(sb.toString());
        }
        return out;
    }

    /**
     * Bole hue vaakya me call ka irada ho to naam lautata hai ("" = irada hai par naam nahi bola),
     * call ka irada na ho to null.
     */
    public static String parseCallRequest(String utterance) {
        List<String> w = words(utterance);
        boolean hasCall = false;
        for (String t : w) {
            if (NOT_A_CALL.contains(t)) {
                return null;
            }
            if (CALL_WORDS.contains(t)) {
                hasCall = true;
            }
        }
        if (!hasCall) {
            return null;
        }
        List<String> name = new ArrayList<String>();
        for (String t : w) {
            if (!FILLER.contains(t)) {
                name.add(t);
            }
        }
        if (name.size() > 4) {
            return null;          // lamba vaakya: shayad call ki baat hi nahi, AI ko do
        }
        StringBuilder sb = new StringBuilder();
        for (String t : name) {
            if (sb.length() > 0) {
                sb.append(' ');
            }
            sb.append(t);
        }
        return sb.toString();
    }

    // ------------------------------------------------------------- phonetic --
    /** Hinglish spelling ka fark mitane wali chhoti chabi: saket/sakit/sakeet -> "sakat". */
    static String phon(String s) {
        String x = s.toLowerCase(Locale.ENGLISH);
        x = x.replace("ph", "f").replace("ck", "k").replace("kh", "k").replace("gh", "g")
                .replace("bh", "b").replace("dh", "d").replace("th", "t").replace("sh", "s")
                .replace("ch", "c").replace("w", "v").replace("z", "j").replace("q", "k")
                .replace("x", "ks").replace("y", "i");
        StringBuilder sb = new StringBuilder();
        char prev = 0;
        for (int i = 0; i < x.length(); i++) {
            char ch = x.charAt(i);
            if (!Character.isLetterOrDigit(ch) || ch == 'h') {
                continue;
            }
            if ("aeiou".indexOf(ch) >= 0) {
                ch = 'a';
            }
            if (ch == prev) {
                continue;
            }
            sb.append(ch);
            prev = ch;
        }
        return sb.toString();
    }

    static int lev(String a, String b) {
        int[] prev = new int[b.length() + 1];
        int[] cur = new int[b.length() + 1];
        for (int j = 0; j <= b.length(); j++) {
            prev[j] = j;
        }
        for (int i = 1; i <= a.length(); i++) {
            cur[0] = i;
            for (int j = 1; j <= b.length(); j++) {
                int c = a.charAt(i - 1) == b.charAt(j - 1) ? 0 : 1;
                cur[j] = Math.min(Math.min(cur[j - 1] + 1, prev[j] + 1), prev[j - 1] + c);
            }
            int[] t = prev;
            prev = cur;
            cur = t;
        }
        return prev[b.length()];
    }

    static double tokenScore(String q, String c) {
        if (q.equals(c)) {
            return 1.0;
        }
        if (q.length() >= 3 && c.startsWith(q)) {
            return 0.92;
        }
        String pq = phon(q);
        String pc = phon(c);
        if (pq.length() == 0 || pc.length() == 0) {
            return 0;
        }
        if (pq.equals(pc)) {
            return 0.9;
        }
        if (pq.length() >= 3 && pc.startsWith(pq)) {
            return 0.82;
        }
        if (pq.length() >= 4 && lev(pq, pc) <= 1) {
            return 0.78;
        }
        int d = lev(q, c);
        double ratio = 1.0 - (double) d / Math.max(q.length(), c.length());
        if (q.length() >= 4 && ratio >= 0.75) {
            return ratio * 0.85;
        }
        return 0;
    }

    /** Ek contact ka score (0..1). Naam ke sab bole shabd mile to hi 0.7 se upar. */
    public static double score(String spoken, String contactName) {
        List<String> q = words(spoken);
        if (q.isEmpty()) {
            return 0;
        }
        // brackets ke andar ke shabd (jaise "(gau)") ginte hain par extra naam nahi maane jaate
        List<String> main = new ArrayList<String>();
        List<String> all = new ArrayList<String>();
        boolean inParen = false;
        StringBuilder sb = new StringBuilder();
        String cn = contactName == null ? "" : contactName.toLowerCase(Locale.ENGLISH);
        for (int i = 0; i <= cn.length(); i++) {
            char ch = i < cn.length() ? cn.charAt(i) : ' ';
            if (Character.isLetterOrDigit(ch)) {
                sb.append(ch);
                continue;
            }
            if (sb.length() > 0) {
                all.add(sb.toString());
                if (!inParen) {
                    main.add(sb.toString());
                }
                sb.setLength(0);
            }
            if (ch == '(' || ch == '[' || ch == '{') {
                inParen = true;
            } else if (ch == ')' || ch == ']' || ch == '}') {
                inParen = false;
            }
        }
        if (all.isEmpty()) {
            return 0;
        }
        // poora naam jod kar bhi dekho: "sakatjha" == "saket jha"
        StringBuilder qj = new StringBuilder();
        for (String t : q) {
            qj.append(t);
        }
        StringBuilder cj = new StringBuilder();
        for (String t : main) {
            cj.append(t);
        }
        if (qj.length() > 0 && qj.toString().equals(cj.toString())) {
            return 1.0;
        }
        double sum = 0;
        boolean allMatched = true;
        for (String t : q) {
            double best = 0;
            for (String c : all) {
                best = Math.max(best, tokenScore(t, c));
            }
            if (best <= 0) {
                allMatched = false;
            }
            sum += best;
        }
        double avg = sum / q.size();
        if (!allMatched) {
            avg *= 0.5;
        }
        int extra = Math.max(0, main.size() - q.size());
        return Math.max(0, avg - 0.02 * extra);
    }

    static String digits(String number) {
        String d = number == null ? "" : number.replaceAll("[^0-9]", "");
        return d.length() > 10 ? d.substring(d.length() - 10) : d;
    }

    /** Sabse achhe match (zyada se zyada max). Ek jaisa naam+number ek hi baar. */
    public static List<Scored> find(String spoken, List<Contact> contacts, int max) {
        List<Scored> all = new ArrayList<Scored>();
        double best = 0;
        for (Contact c : contacts) {
            if (c.name == null || c.number == null) {
                continue;
            }
            double s = score(spoken, c.name);
            if (s >= 0.7) {
                all.add(new Scored(c, s));
                best = Math.max(best, s);
            }
        }
        List<Scored> out = new ArrayList<Scored>();
        Set<String> seen = new HashSet<String>();
        // score ke hisaab se chhaanto (sort)
        List<Scored> sorted = new ArrayList<Scored>(all);
        java.util.Collections.sort(sorted, new java.util.Comparator<Scored>() {
            @Override
            public int compare(Scored a, Scored b) {
                return Double.compare(b.score, a.score);
            }
        });
        for (Scored s : sorted) {
            if (s.score < best - 0.08) {
                continue;
            }
            String key = digits(s.contact.number);
            if (key.length() == 0 || seen.contains(key)) {
                continue;
            }
            seen.add(key);
            out.add(s);
            if (out.size() >= max) {
                break;
            }
        }
        return out;
    }

    // --------------------------------------------------------------- choice --
    /** 1..n = chunav, -1 = rehne do, 0 = samajh nahi aaya. */
    public static int parseChoice(String utterance, int n) {
        List<String> w = words(utterance);
        for (String t : w) {
            if (t.equals("cancel") || t.equals("nahi") || t.equals("nhi") || t.equals("mat")
                    || t.equals("rehne") || t.equals("rahne") || t.equals("chhodo") || t.equals("chodo")
                    || t.equals("stop") || t.equals("no") || t.equals("band")) {
                return -1;
            }
        }
        for (int i = 0; i < w.size(); i++) {
            String t = w.get(i);
            String prev = i > 0 ? w.get(i - 1) : "";
            int v = numberOf(t);
            if (v == 2 && (t.equals("do") || t.equals("dow"))
                    && (prev.equals("kar") || prev.equals("karo") || prev.equals("laga") || prev.equals("lagao")
                    || prev.equals("kr") || prev.equals("kro"))) {
                continue;     // "call kar do" ka "do" number nahi hai
            }
            if (v > 0 && v <= n) {
                return v;
            }
            if (t.equals("last") || t.equals("aakhri") || t.equals("akhri") || t.equals("antim")) {
                return n;
            }
        }
        return 0;
    }

    static int numberOf(String t) {
        switch (t) {
            case "1": case "one": case "ek": case "won": case "pehla": case "pehle": case "pahla": case "pahle":
            case "first": case "1st": case "pehli": case "pahli":
                return 1;
            case "2": case "two": case "do": case "dow": case "to": case "too": case "tu": case "dusra":
            case "dusre": case "doosra": case "doosre": case "second": case "2nd": case "dusri": case "doosri":
                return 2;
            case "3": case "three": case "teen": case "tin": case "tree": case "teesra": case "teesre":
            case "tisra": case "third": case "3rd": case "teesri":
                return 3;
            case "4": case "four": case "for": case "char": case "chaar": case "chautha": case "chauthe":
            case "fourth": case "4th":
                return 4;
            case "5": case "five": case "panch": case "paanch": case "paanchva": case "panchva": case "fifth":
            case "5th":
                return 5;
            default:
                return 0;
        }
    }

    /** Bolne layak naam: "Saket Jha(gau)" -> "Saket Jha gau". */
    public static String speakable(String name) {
        return name == null ? "" : name.replaceAll("[()\\[\\]{}]", " ").replaceAll("\\s+", " ").trim();
    }
}
