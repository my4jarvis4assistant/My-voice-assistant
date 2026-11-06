package org.myassistant.myvoiceassistant;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Voice-Access jaisa control: bole hue tukde ko kaam me badalta hai (click, scroll, type, send, back...).
 * Sirf samajhna (parse) aur naam milana yahan hai; screen par asli kaam JarvisAccessService karti hai.
 * Is class me Android ka kuch nahi hai, isliye alag se test ho sakti hai.
 */
public final class JarvisControl {
    private JarvisControl() {
    }

    public static final int CLICK = 1, LONG = 2, SCROLL = 3, SWIPE = 4, BACK = 5, HOME = 6, RECENTS = 7,
            NOTIFS = 8, QUICK = 9, TYPE = 10, SEND = 11, ENTER = 12, CLEAR = 13, OPEN = 14;

    public static final class Cmd {
        public int kind = 0;
        public String target = "";      // jis par click / jis chat me type
        public String text = "";        // type karne ka text
        public String dir = "";         // up / down / left / right
        public int count = 1;           // kitni baar scroll
        public boolean qual = false;    // "wale option me jao": app nahi, screen ka hissa
    }

    private static Set<String> set(String... a) {
        return new HashSet<String>(Arrays.asList(a));
    }

    private static final Set<String> TYPE_V = set("type", "tipe", "taip", "typing", "tyep");
    private static final Set<String> WRITE_V = set("likho", "likh", "likhna", "likhiye");
    private static final Set<String> CLICK_V = set("click", "clik", "tap", "tep", "press", "dabao", "daba", "dabana",
            "dabaiye", "dabado", "touch", "select", "chuno", "chune", "chunna", "klik");
    private static final Set<String> GO_V = set("kholo", "khol", "open", "jao", "jaao", "jaiye", "go", "kholiye",
            "khulao");
    private static final Set<String> DO_W = set("karo", "kro", "kar", "do", "dena", "kijiye", "kariye", "kardo",
            "krdo", "karna", "de", "dijiye", "dedo", "please", "plz", "abhi", "jarvis", "hey", "ab", "zara", "jara");
    private static final Set<String> TARGET_NOISE = set("par", "pe", "pr", "per", "ko", "on", "the", "a", "an", "me",
            "mein", "in", "to", "wale", "wala", "wali", "waale", "option", "button", "icon", "tab", "link", "field",
            "box", "bar", "ek", "wo", "vo", "ye", "us", "uspe", "uspar", "isko", "ise", "ki", "ka", "ke", "se", "section",
            "page", "screen", "of", "and", "aur");
    private static final Set<String> QUAL_W = set("wale", "wala", "wali", "waale", "option", "tab", "button", "icon",
            "section", "link", "page");
    private static final Set<String> DEVICE = set("alarm", "timer", "wifi", "bluetooth", "torch", "flashlight",
            "volume", "brightness", "hotspot", "weather", "mausam", "gaana", "music", "reminder");
    private static final Set<String> LABELS = set("like", "unlike", "follow", "unfollow", "subscribe", "share",
            "comment", "save", "play", "pause", "mute", "unmute", "next", "skip", "reply", "forward", "download",
            "search", "cancel", "ok", "okay", "accept", "allow", "confirm", "done", "submit", "post", "add", "edit",
            "settings", "menu", "profile", "reels", "stories", "story", "explore", "messages", "message", "inbox",
            "camera", "gallery", "photos", "close", "retry", "continue", "next", "back");

    private static boolean subset(List<String> w, Set<String> allowed) {
        for (String t : w) {
            if (!allowed.contains(t)) {
                return false;
            }
        }
        return true;
    }

    private static boolean has(List<String> w, Set<String> s) {
        for (String t : w) {
            if (s.contains(t)) {
                return true;
            }
        }
        return false;
    }

    private static Set<String> union(Set<String> a, Set<String> b) {
        Set<String> r = new HashSet<String>(a);
        r.addAll(b);
        return r;
    }

    private static List<String> cleanTarget(List<String> w, Set<String> verbs) {
        List<String> out = new ArrayList<String>();
        for (String t : w) {
            if (verbs.contains(t) || DO_W.contains(t) || TARGET_NOISE.contains(t)) {
                continue;
            }
            out.add(t);
        }
        return out;
    }

    private static String join(List<String> l) {
        StringBuilder sb = new StringBuilder();
        for (String s : l) {
            if (sb.length() > 0) {
                sb.append(' ');
            }
            sb.append(s);
        }
        return sb.toString();
    }

    private static final Pattern TYPE_RE = Pattern.compile(
            "^(?:(.*?)\\s+(ko|me|mein|par|pe|pr|per|in|on)\\s+)?(?:(?:message|msg|text)\\s+)?(?:type|tipe|taip|tyep)\\s*(?:karo|kro|kar\\s*do|kardo|"
                    + "krdo|kijiye|kariye|karna|kar)?\\s*[:,]?\\s*(.*)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern WRITE_RE = Pattern.compile(
            "^(?:ye\\s+|ab\\s+|aur\\s+)?(?:likho|likh\\s+do|likhiye|likh)\\s*[:,]?\\s*(.+)$", Pattern.CASE_INSENSITIVE);

    /** null = ye control ka kaam nahi. */
    public static Cmd parse(String utterance) {
        String u = utterance == null ? "" : utterance.trim();
        if (u.length() == 0) {
            return null;
        }
        List<String> w = JarvisContactMatch.words(u);
        if (w.isEmpty() || w.size() > 40 || has(w, DEVICE)) {
            return null;
        }
        List<String> core = new ArrayList<String>();       // "jarvis", "please" jaise shabd hatakar
        for (String t : w) {
            if (!t.equals("jarvis") && !t.equals("hey") && !t.equals("please") && !t.equals("plz")) {
                core.add(t);
            }
        }
        if (core.isEmpty()) {
            return null;
        }
        Cmd c = new Cmd();
        String low = u.toLowerCase(Locale.ENGLISH).replaceAll("^(?:hey\\s+|hello\\s+)?jarvis[,\\s]+", "");

        // ---- type ----
        if (has(core, TYPE_V)) {
            Matcher m = TYPE_RE.matcher(low);
            if (m.find()) {
                c.kind = TYPE;
                String tg = m.group(1) == null ? "" : m.group(1);
                String joiner = m.group(2) == null ? "" : m.group(2).toLowerCase(Locale.ENGLISH);
                c.qual = joiner.length() > 0 && !joiner.equals("ko");       // "search box me type karo": text-box ka naam
                List<String> tw = new ArrayList<String>();
                for (String t : JarvisContactMatch.words(tg)) {
                    if (!SocialWords.isApp(t) && !t.equals("message") && !t.equals("msg") && !t.equals("text")
                            && !DO_W.contains(t) && !TARGET_NOISE.contains(t)) {
                        tw.add(t);
                    }
                }
                c.target = join(tw);
                c.text = m.group(3) == null ? "" : m.group(3).trim();
                return c;
            }
        }
        if (has(core, WRITE_V) && !core.contains("ko") && !has(core, SocialWords.APPS)) {
            Matcher m = WRITE_RE.matcher(low);
            if (m.find()) {
                c.kind = TYPE;
                c.text = m.group(1).trim();
                return c;
            }
        }
        // ---- send (bina naam ke) ----
        Set<String> sendOk = set("send", "bhej", "bhejo", "bhejdo", "bhejiye", "it", "ise", "isko", "message", "msg",
                "button", "dabao", "click", "tap", "press", "dabana", "daba", "ab", "ko", "ye", "wo", "abhi");
        if ((core.contains("send") || core.contains("bhej") || core.contains("bhejo") || core.contains("bhejdo")
                || core.contains("bhejiye")) && subset(core, union(sendOk, DO_W))) {
            c.kind = SEND;
            return c;
        }
        // ---- enter ----
        if (core.contains("enter") && subset(core, union(set("enter", "dabao", "press", "tap", "click", "key", "button",
                "daba", "dabana"), DO_W))) {
            c.kind = ENTER;
            return c;
        }
        // ---- clear / delete ----
        Set<String> clearV = set("clear", "delete", "mita", "mitao", "hata", "hatao", "saaf", "saf");
        if (has(core, clearV) && subset(core, union(union(clearV, set("text", "sab", "saara", "pura", "sara", "all",
                "likha", "hua", "message", "box", "field", "ye", "wo", "ko", "ise", "isko", "sabkuch", "everything",
                "kuch", "poora")), DO_W))) {
            c.kind = CLEAR;
            return c;
        }
        // ---- back / home / recents / notifications ----
        Set<String> backV = set("back", "peeche", "pichhe", "piche", "wapas", "vapas", "pichla", "previous");
        if (has(core, backV) && subset(core, union(union(backV, set("go", "jao", "jaao", "ja", "jaiye", "ek", "one",
                "step", "screen", "par", "pe", "to", "page", "pehle", "wale", "wali")), DO_W))) {
            c.kind = BACK;
            return c;
        }
        if (core.contains("home") && subset(core, union(set("home", "screen", "jao", "jaao", "go", "to", "par", "pe",
                "ja", "pr", "page", "pe", "chalo", "wapas"), DO_W))) {
            c.kind = HOME;
            return c;
        }
        if ((core.contains("recent") || core.contains("recents")) && subset(core, union(set("recent", "recents",
                "apps", "app", "kholo", "open", "dikhao", "show", "screen"), DO_W))) {
            c.kind = RECENTS;
            return c;
        }
        if ((core.contains("notification") || core.contains("notifications")) && has(core, set("kholo", "open",
                "dikhao", "show", "panel", "bar", "shade", "neeche", "khinchho", "drawer")) && !has(core, set("aaye",
                "aaya", "aayi", "kitne", "kiske", "koi", "padho", "padh", "sunao", "mile", "naye"))) {
            c.kind = NOTIFS;
            return c;
        }
        if ((core.contains("quick") && core.contains("settings")) || core.contains("control") && core.contains("center")) {
            c.kind = QUICK;
            return c;
        }
        // ---- scroll / swipe ----
        Set<String> down = set("down", "neeche", "niche", "nichey", "nichhe", "neechey");
        Set<String> up = set("up", "upar", "ooper", "oopar", "uppar");
        Set<String> left = set("left", "bayen", "baayen", "baen");
        Set<String> right = set("right", "dayen", "daayen", "daen");
        boolean scrollWord = core.contains("scroll") || core.contains("swipe") || core.contains("skrol")
                || core.contains("scrol");
        boolean top = has(core, set("top", "start", "shuru")) || (core.contains("sabse") && has(core, up));
        boolean bottom = has(core, set("bottom", "end", "last")) || (core.contains("sabse") && has(core, down));
        String dir = has(core, down) ? "down" : has(core, up) ? "up" : has(core, left) ? "left"
                : has(core, right) ? "right" : "";
        if (dir.length() == 0 && top) {
            dir = "up";
        }
        if (dir.length() == 0 && bottom) {
            dir = "down";
        }
        Set<String> scrollOk = union(set("scroll", "swipe", "skrol", "scrol", "thoda", "aur", "more", "page", "ko", "ki",
                "taraf", "side", "screen", "tak", "bottom", "top", "last", "start", "ek", "ke", "se", "pura", "fast",
                "slowly", "jao", "jaao", "ja", "sabse", "end", "shuru", "list", "bahut", "zyada", "thodi", "or", "again",
                "phir", "dobara"), union(union(down, up), union(left, right)));
        if (dir.length() > 0 && subset(core, union(scrollOk, DO_W))
                && (scrollWord || (core.size() <= 3 && has(core, set("jao", "jaao", "ja", "karo", "kro", "do"))))) {
            c.kind = (core.contains("swipe") || dir.equals("left") || dir.equals("right")) ? SWIPE : SCROLL;
            c.dir = dir;
            c.count = (top || bottom) && (dir.equals("up") || dir.equals("down")) ? 8 : 1;
            return c;
        }
        // ---- long press ----
        if ((core.contains("long") && has(core, union(CLICK_V, set("hold")))) || core.contains("hold")
                || (core.contains("lamba") && has(core, CLICK_V))) {
            List<String> tg = cleanTarget(core, union(union(CLICK_V, set("long", "hold", "lamba")), GO_V));
            if (!tg.isEmpty()) {
                c.kind = LONG;
                c.target = join(tg);
                return c;
            }
        }
        // ---- click / tap ----
        if (has(core, CLICK_V)) {
            List<String> tg = cleanTarget(core, CLICK_V);
            if (!tg.isEmpty()) {
                c.kind = CLICK;
                c.target = join(tg);
                return c;
            }
            return null;
        }
        // ---- kholo / jao ----
        if (has(core, GO_V)) {
            List<String> tg = cleanTarget(core, GO_V);
            if (!tg.isEmpty() && tg.size() <= 5) {
                c.kind = OPEN;
                c.target = join(tg);
                c.qual = has(core, QUAL_W);
                return c;
            }
            return null;
        }
        // ---- "like karo", "follow karo" ----
        if (core.size() <= 3 && has(core, LABELS) && subset(core, union(union(LABELS, DO_W), set("button", "ko", "par",
                "pe")))) {
            List<String> tg = cleanTarget(core, set());
            if (tg.size() == 1) {
                c.kind = CLICK;
                c.target = tg.get(0);
                return c;
            }
        }
        return null;
    }

    /** Python/anya jagah se: kya ye control ka kaam hai? */
    public static boolean isControl(String utterance) {
        try {
            return parse(utterance) != null || JarvisScreen.isAsk(utterance) || JarvisMemory.isMemory(utterance)
                    || JarvisStyle.isStyle(utterance) || JarvisRoutine.isCmd(utterance)
                    || JarvisSpend.isCmd(utterance) || JarvisCallWords.parseToggle(utterance) >= 0
                    || JarvisCallWords.parseAssist(utterance).kind != 0;
        } catch (Throwable t) {
            return false;
        }
    }

    // ------------------------------------------------------------------- naam milana --
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

    /** 0..1: bole hue naam (target) aur screen ke label ka milaan. */
    public static double match(String target, String label) {
        String t = norm(target);
        String l = norm(label);
        if (t.length() == 0 || l.length() == 0) {
            return 0;
        }
        if (t.equals(l)) {
            return 1.0;
        }
        String tp = " " + t + " ";
        String lp = " " + l + " ";
        if (lp.contains(tp)) {
            return 0.93 - Math.min(0.1, (l.length() - t.length()) * 0.002);
        }
        if (l.length() >= 3 && tp.contains(lp)) {
            return 0.88;
        }
        String[] tt = t.split(" ");
        String[] lt = l.split(" ");
        int found = 0;
        for (String a : tt) {
            for (String b : lt) {
                if (a.equals(b) || (a.length() >= 4 && b.length() >= 4 && JarvisContactMatch.tokenScore(a, b) >= 0.78)) {
                    found++;
                    break;
                }
            }
        }
        if (found == tt.length) {
            return 0.86 - Math.min(0.06, Math.max(0, lt.length - tt.length) * 0.01);
        }
        double s = JarvisContactMatch.score(t, l);
        return s >= 0.8 ? s * 0.92 : 0;
    }

    /** Pichle kuch labels me se sabse achha. -1 = koi nahi (0.8 se kam). */
    public static int best(String target, List<String> labels) {
        int bi = -1;
        double bs = 0;
        for (int i = 0; i < labels.size(); i++) {
            double s = match(target, labels.get(i));
            if (s > bs + 0.0001) {
                bs = s;
                bi = i;
            }
        }
        return bs >= 0.8 ? bi : -1;
    }

    /** Chhota sa hissa jo social parser ke shabd bhi jaanta hai (app ke naam). */
    static final class SocialWords {
        static final Set<String> APPS = set("whatsapp", "watsapp", "whatsap", "vatsapp", "instagram", "insta", "facebook",
                "fb", "messenger", "telegram");

        static boolean isApp(String t) {
            return APPS.contains(t);
        }
    }
}
