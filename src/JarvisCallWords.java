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
}
