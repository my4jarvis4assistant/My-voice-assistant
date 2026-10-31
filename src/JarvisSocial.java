package org.myassistant.myvoiceassistant;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * WhatsApp message / voice call / video call ki baat samajhna (sirf Java, Android par nirbhar nahi).
 * jarvis_social.py ka Java version.
 */
public final class JarvisSocial {
    private JarvisSocial() {
    }

    public static final class Job {
        public String kind = "";        // "message" ya "call"
        public String app = "whatsapp";
        public boolean video = false;
        public String name = "";
        public String body = null;      // null = abhi pata nahi
        public boolean ambiguous = false;
        // chalte kaam ke liye
        public JarvisWhatsApp.Person person = null;
    }

    private static Set<String> set(String... a) {
        return new HashSet<String>(Arrays.asList(a));
    }

    static final String[][] APPS = {
            {"whatsapp", "whatsapp", "watsapp", "whatsap", "vatsapp", "whats", "wa", "whatsup", "whatsapps", "whatapp"},
            {"instagram", "instagram", "insta", "instagrm", "instagraam"},
            {"facebook", "facebook", "fb", "fecbook", "facebok"},
            {"messenger", "messenger", "masenger"},
            {"telegram", "telegram", "telegrm"}};

    static final Set<String> VIDEO = set("video", "vdo", "vedio", "videocall", "vidio");
    static final Set<String> MSG = set("message", "msg", "messege", "massage", "messeg", "text", "sms", "bhejo",
            "bhej", "bhejna", "send", "likho", "likh", "bhejdo", "bhejiye", "bhejein", "bhejde");
    static final Set<String> MSG_NOUN = set("message", "msg", "messege", "massage", "text", "sms");
    static final Set<String> NOISE = set("ek", "ko", "ka", "ki", "ke", "se", "par", "pe", "me", "mein", "to", "karo",
            "kro", "kar", "kare", "karna", "kariye", "kijiye", "kardo", "krdo", "do", "de", "dena", "dijiye", "mujhe",
            "mera", "meri", "jarvis", "hey", "hello", "hi", "please", "plz", "a", "the", "on", "via", "through", "for",
            "abhi", "zara", "jara", "wala", "wali", "contact", "naam", "number", "phone", "call", "calls", "lagao",
            "laga", "lagana", "dial", "kall", "caal", "cal", "milao", "can", "you", "will", "make", "now", "voice",
            "audio", "normal", "krna", "kre", "kardena", "bol", "bolo", "keh", "kaho", "bhi");
    static final Set<String> SKIP = new HashSet<String>();

    static {
        for (String[] row : APPS) {
            for (int i = 1; i < row.length; i++) {
                SKIP.add(row[i]);
            }
        }
        SKIP.addAll(VIDEO);
        SKIP.addAll(MSG);
        SKIP.addAll(NOISE);
    }

    static final Set<String> APP_WORDS = new HashSet<String>();

    static {
        for (String[] row : APPS) {
            for (int i = 1; i < row.length; i++) {
                APP_WORDS.add(row[i]);
            }
        }
    }

    private static final Pattern MARKER = Pattern.compile(
            "\\b(?:ki|kee|ye|yeh|that|saying|likho|likh\\s+do|likh\\s+kar|bolo|bol\\s+do|keh\\s+do|kehdo|kaho|"
                    + "message\\s+hai)\\b[\\s,:]*(.+)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern VERB = Pattern.compile(
            "\\b(?:bhejo|bhej\\s*do|bhejdo|bhejna|bhejiye|bhejein|bhejde|send(?:\\s+karo|\\s+kro)?)\\b[\\s,:]*(.+)$",
            Pattern.CASE_INSENSITIVE);
    private static final Pattern LEAD = Pattern.compile(
            "^(?:(?:ki|kee|ye|yeh|that|saying|ke|ko|to|message|msg|text|karo|kro|do|de|bolo|likho|bhejo|whatsapp|"
                    + "par|pe|me|mein|ek)\\b[\\s,:]*)+", Pattern.CASE_INSENSITIVE);

    static String detectApp(List<String> w) {
        for (String t : w) {
            for (String[] row : APPS) {
                for (int i = 1; i < row.length; i++) {
                    if (row[i].equals(t)) {
                        return row[0];
                    }
                }
            }
        }
        return "";
    }

    static String squash(String s) {
        return s == null ? "" : s.trim().replaceAll("\\s+", " ");
    }

    /** null = ye WhatsApp/social wali baat nahi. */
    public static Job parse(String utterance) {
        String u = squash(utterance);
        List<String> w = JarvisContactMatch.words(u);
        if (w.isEmpty()) {
            return null;
        }
        for (String t : w) {
            if (JarvisContactMatch.NOT_A_CALL.contains(t) && !MSG.contains(t) && !APP_WORDS.contains(t)) {
                return null;
            }
        }
        String app = detectApp(w);
        boolean video = false;
        boolean hasMsg = false;
        boolean hasCall = false;
        boolean hasNoun = false;
        for (String t : w) {
            if (VIDEO.contains(t)) {
                video = true;
            }
            if (MSG.contains(t)) {
                hasMsg = true;
            }
            if (MSG_NOUN.contains(t)) {
                hasNoun = true;
            }
            if (JarvisContactMatch.CALL_WORDS.contains(t) || t.equals("videocall")) {
                hasCall = true;
            }
        }
        String kind;
        if (hasMsg && !(hasCall && !hasNoun)) {
            kind = "message";
        } else if (hasCall || video) {
            kind = "call";
        } else if (app.length() > 0 && MARKER.matcher(u).find()) {
            kind = "message";
        } else {
            return null;
        }
        if (kind.equals("call") && app.length() == 0 && !video) {
            return null;            // seedha phone call: purana call flow sambhalega
        }
        if (kind.equals("message") && w.size() > 40) {
            return null;
        }
        String body = null;
        String head = u;
        boolean ambiguous = false;
        if (kind.equals("message")) {
            Matcher m = MARKER.matcher(u);
            if (m.find() && m.start() > 0) {
                head = u.substring(0, m.start());
                body = m.group(1);
            } else {
                Matcher v = VERB.matcher(u);
                if (v.find()) {
                    boolean nameBefore = false;
                    if (v.start() > 0) {
                        for (String t : JarvisContactMatch.words(u.substring(0, v.start()))) {
                            if (!SKIP.contains(t)) {
                                nameBefore = true;
                            }
                        }
                    }
                    if (nameBefore) {
                        head = u.substring(0, v.start());
                        body = v.group(1);
                    } else {
                        ambiguous = true;
                    }
                }
            }
            if (body != null) {
                body = squash(LEAD.matcher(body).replaceFirst(""));
                if (body.length() == 0) {
                    body = null;
                }
            }
        }
        List<String> nameTokens = new ArrayList<String>();
        if (kind.equals("message") && ambiguous) {
            List<String> tail = JarvisContactMatch.words(u);
            int idx = -1;
            for (int i = 0; i < tail.size(); i++) {
                if (tail.get(i).equals("to") || tail.get(i).equals("ko")) {
                    idx = i;
                }
            }
            nameTokens.addAll(idx >= 0 ? tail.subList(idx + 1, tail.size()) : tail);
        } else {
            for (String t : JarvisContactMatch.words(head)) {
                if (!SKIP.contains(t)) {
                    nameTokens.add(t);
                }
            }
        }
        Job j = new Job();
        j.kind = kind;
        j.app = app.length() == 0 ? "whatsapp" : app;
        j.video = video;
        j.name = join(nameTokens);
        j.body = body;
        j.ambiguous = ambiguous;
        return j;
    }

    static String join(List<String> t) {
        StringBuilder sb = new StringBuilder();
        for (String s : t) {
            if (sb.length() > 0) {
                sb.append(' ');
            }
            sb.append(s);
        }
        return sb.toString();
    }

    static final Set<String> YES = set("haan", "han", "ha", "haa", "yes", "yeah", "yep", "bhej", "bhejo", "send",
            "ok", "okay", "kar", "karo", "theek", "thik", "sahi", "correct", "sure", "bilkul", "hanji", "haanji",
            "ji");
    static final Set<String> NO = set("nahi", "nhi", "no", "cancel", "mat", "ruko", "stop", "galat", "nope", "rehne",
            "rahne", "chhodo", "chodo");

    /** "yes", "no" ya "" (samajh nahi aaya). */
    public static String yesNo(String text) {
        List<String> w = JarvisContactMatch.words(text);
        for (String t : w) {
            if (NO.contains(t)) {
                return "no";
            }
        }
        for (String t : w) {
            if (YES.contains(t)) {
                return "yes";
            }
        }
        return "";
    }

    /** "saket hello how are you" -> contact milne tak pehle 1-3 shabd naam, baaki message. [naam, message ya null] */
    public static String[] splitNameBody(List<String> tokens, List<JarvisContactMatch.Contact> contacts) {
        for (int k = 3; k >= 1; k--) {
            if (tokens.size() < k) {
                continue;
            }
            String cand = join(tokens.subList(0, k));
            if (!JarvisContactMatch.find(cand, contacts, 4).isEmpty()) {
                String rest = join(tokens.subList(k, tokens.size()));
                return new String[]{cand, rest.length() == 0 ? null : rest};
            }
        }
        return new String[]{join(tokens), null};
    }
}
