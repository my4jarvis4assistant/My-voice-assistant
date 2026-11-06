package org.myassistant.myvoiceassistant;

import java.util.Locale;

/**
 * Call screening ke bol-chaal ke shabd: on/off karna aur ring ke dauraan aapka jawab
 * ("kaat do", "busy hu", "utha lo"). Is class me Android ka kuch nahi.
 */
public final class JarvisCallWords {
    private JarvisCallWords() {
    }

    public static final String REJECT = "reject", BUSY = "busy", ANSWER = "answer", IGNORE = "ignore";

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

    /** 1 = call screening chalu karo, 0 = band karo, -1 = ye iska kaam nahi. */
    public static int parseToggle(String utterance) {
        String w = norm(utterance);
        boolean about = w.matches(".*\\bcall\\s+screening\\b.*") || w.matches(".*\\bcalls?\\s+screen\\b.*")
                || w.matches(".*\\b(?:anjaan|ajnabi|unknown)\\b.*\\b(?:call|calls|number|numbers)\\b.*")
                || w.matches(".*\\b(?:call|calls|number|numbers)\\b.*\\b(?:anjaan|ajnabi|unknown)\\b.*");
        if (!about) {
            return -1;
        }
        if (w.matches(".*\\b(?:off|band|mat|stop|nahi|nhi|hata|disable)\\b.*")) {
            return 0;
        }
        if (w.matches(".*\\b(?:on|chalu|shuru|lagao|start|batao|batana|bata|bol|bolna|sunao|karo|kar)\\b.*")) {
            return 1;
        }
        return -1;
    }

    /** Ring ke dauraan jawab: reject / busy / answer / ignore, ya null. */
    public static String replyKind(String utterance) {
        String w = norm(utterance);
        if (w.length() == 0) {
            return null;
        }
        if (w.matches(".*\\b(?:busy|baad\\s+me|baad\\s+mein|abhi\\s+nahi|abhi\\s+nhi|message\\s+bhej|msg\\s+bhej|sms)\\b.*")) {
            return BUSY;
        }
        if (w.matches(".*\\b(?:kaat|kat|cut|reject|decline|disconnect|mat\\s+utha\\w*|nahi\\s+utha\\w*|nhi\\s+utha\\w*)\\b.*")
                || w.matches("^(?:nahi|nhi|no|na)$")) {
            return REJECT;
        }
        if (w.matches(".*\\b(?:utha|uthao|uthalo|uthale|utha\\s+lo|utha\\s+do|receive|answer|pick|accept)\\b.*")
                || w.matches("^(?:haan|han|ha|yes|ji|ji\\s+haan)$")) {
            return ANSWER;
        }
        if (w.matches(".*\\b(?:chhodo|chodo|rehne\\s+do|rahne\\s+do|ignore|koi\\s+baat\\s+nahi|jaane\\s+do)\\b.*")) {
            return IGNORE;
        }
        return null;
    }

    public static boolean isNumberLike(String title) {
        String t = title == null ? "" : title.trim();
        return t.matches("^[+0-9][0-9\\s\\-()]{5,}$");
    }

    /** "+91 62019 76xxx" -> "plus 9 1 6 2 0 ..." (TTS ek-ek ank bole). */
    public static String speakNumber(String title) {
        String t = title == null ? "" : title.trim();
        StringBuilder sb = new StringBuilder();
        for (char ch : t.toCharArray()) {
            if (ch == '+') {
                sb.append("plus ");
            } else if (Character.isDigit(ch)) {
                sb.append(ch).append(' ');
            }
        }
        return sb.toString().trim();
    }

    public static boolean spamHint(String text) {
        String l = text == null ? "" : text.toLowerCase(Locale.ENGLISH);
        return l.contains("spam") || l.contains("scam") || l.contains("fraud") || l.contains("suspected")
                || l.contains("telemarket");
    }

    /** SMS bhejne layak number (sirf ank aur +) ya null. */
    public static String extractNumber(String title) {
        String t = title == null ? "" : title.trim();
        if (!isNumberLike(t)) {
            return null;
        }
        String d = t.replaceAll("[^0-9+]", "");
        return d.replaceAll("[^0-9]", "").length() >= 7 ? d : null;
    }

    // ------------------------------------------------ call assistant (WhatsApp call Jarvis uthaye) --
    public static final class Assist {
        public int kind = 0;          // 1 = chalu, 2 = band, 3 = pichli baat-cheet ka hisaab
        public String status = "";    // "main gym me hu"
    }

    public static Assist parseAssist(String utterance) {
        Assist a = new Assist();
        String w = norm(utterance);
        if (w.length() < 6) {
            return a;
        }
        boolean named = w.matches(".*\\bcall\\s+assistant\\b.*");
        boolean sub = w.matches(".*\\b(?:mere\\s+badle|meri\\s+jagah|mere\\s+liye)\\b.*\\bcalls?\\b.*"
                + "\\b(?:utha|uthana|uthalo|uthao|receive|sunna|baat)\\w*.*")
                || w.matches(".*\\bwhatsapp\\s+calls?\\b.*\\b(?:utha|uthana|uthao|receive)\\w*.*\\b(?:mere|meri)\\b.*");
        boolean log = (named && w.matches(".*\\b(?:summary|kya|log|history|batao|baat)\\b.*")
                && !w.matches(".*\\b(?:on|chalu|off|band|start|shuru)\\b.*"))
                || w.matches(".*\\bjarvis\\s+ne\\b.*\\b(?:call|baat)\\b.*\\b(?:kya|kisse|kis\\s+se)\\b.*");
        if (log) {
            a.kind = 3;
            return a;
        }
        if (!named && !sub) {
            return a;
        }
        a.kind = w.matches(".*\\b(?:off|band|mat|stop|nahi|nhi|hata|disable)\\b.*") ? 2 : 1;
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(
                "(?:bolna|bolo|batana|batao|bol\\s+dena|keh\\s+dena|kehna|kahna)\\s+(?:ki\\s+)?(.+)$").matcher(w);
        if (a.kind == 1 && m.find()) {
            a.status = m.group(1).trim();
        }
        return a;
    }

    public static boolean isGoodbye(String utterance) {
        String w = norm(utterance);
        return w.matches(".*\\b(?:bye|alvida|rakhta\\s+hu|rakhti\\s+hu|dhanyavaad|dhanyawad|thank\\s+you|thanks|shukriya|"
                + "chalo\\s+phir|theek\\s+hai\\s+bata\\s+dena|okay\\s+bye|ok\\s+bye)\\b.*");
    }

    /** "main gym me hu" -> "unka gym me hain" (Jarvis teesre insaan me bolta hai). */
    public static String thirdPerson(String status) {
        String t = " " + norm(status) + " ";
        t = t.replace(" main ", " ").replace(" mai ", " ").replace(" mein ", " mein ");
        t = t.replace(" mera ", " unka ").replace(" meri ", " unki ").replace(" mere ", " unke ")
                .replace(" mujhe ", " unhe ").replace(" hu ", " hain ").replace(" hun ", " hain ")
                .replace(" hoon ", " hain ").replace(" raha hu ", " raha hain ");
        return t.trim().replaceAll("\\s+", " ");
    }
}
