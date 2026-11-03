package org.myassistant.myvoiceassistant;

import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Screen samajhna: "ye padh kar batao", "is message ka summary do", "iska jawab kya du".
 * Accessibility se screen ka text liya jata hai aur Gemini se sawal ka jawab banta hai.
 * Is class me Android ka kuch nahi.
 */
public final class JarvisScreen {
    private JarvisScreen() {
    }

    private static final String OBJ = "(?:screen|message|msg|massage|article|page|post|chat|email|mail|news|story|"
            + "comment|comments|reel|video|text|paragraph|line|notification|caption|description|review)";
    private static final String DEIX = "(?:ye|yeh|is|iss|isko|ise|iska|iski|iske|isme|yahan|yaha|yehi|screen)";
    private static final String QV = "(?:padh\\w*|summar\\w*|saransh|samjh\\w*|translate|anuvad|matlab|likha|likhi|"
            + "explain|bata\\w*|dekh\\w*|bol\\w*|sunao|suna\\w*)";
    private static final String QV_OBJ = "(?:padh\\w*|summar\\w*|saransh|samjh\\w*|translate|anuvad|matlab|likha|likhi|"
            + "explain)";

    private static final Pattern[] ASK = {
            // "screen padh kar batao", "screen par kya hai"
            Pattern.compile(".*\\bscreen\\b.*\\b" + QV + ".*"),
            Pattern.compile(".*\\b" + QV + ".*\\bscreen\\b.*"),
            Pattern.compile(".*\\bscreen\\b.*\\bkya\\b.*"),
            Pattern.compile(".*\\bkya\\b.*\\bscreen\\b.*"),
            // "is message ka summary do", "is article ko samjhao"
            Pattern.compile(".*\\b" + DEIX + "\\s+" + OBJ + "\\b.*\\b" + QV_OBJ + ".*"),
            Pattern.compile(".*\\b" + QV_OBJ + ".*\\b" + DEIX + "\\s+" + OBJ + "\\b.*"),
            // "ye kya likha hai", "yahan kya likha hai"
            Pattern.compile(".*\\b(?:ye|yeh|yahan|yaha|isme|isme\\s+kya)\\s+(?:kya\\s+)?likha\\b.*"),
            Pattern.compile(".*\\bkya\\s+likha\\s+hai\\b.*"),
            // "ye padho", "isko padh ke sunao"
            Pattern.compile("^(?:jarvis\\s+)?(?:ye|yeh|isko|ise|isse|ise)\\s+(?:padh\\w*|samjh\\w*).*"),
            // "iska summary", "iska matlab batao"
            Pattern.compile(".*\\b(?:iska|iski|iske|is\\s+ka|is\\s+ki)\\s+(?:summary|saransh|matlab|translation|anuvad)\\b.*"),
            // "iska jawab kya du", "is message ka reply kya du", "kya reply du"
            Pattern.compile(".*\\b(?:iska|iski|is\\s+message\\s+ka|is\\s+msg\\s+ka|isko)\\s+(?:jawab|reply|jawaab)\\s+"
                    + "(?:kya|kaise|kuch)\\b.*"),
            Pattern.compile(".*\\bkya\\s+(?:jawab|reply|jawaab)\\s+(?:du|doon|dun|karu|karun)\\b.*"),
            // "ye hindi me batao", "isko english me samjhao"
            Pattern.compile("^(?:jarvis\\s+)?(?:ye|yeh|isko|ise|iska)\\s+.*\\b(?:hindi|english|angrezi)\\s+(?:me|mein)\\b.*"),
    };

    // jinme ye shabd hon unko hum kabhi screen-sawal nahi maante (alag flow ka kaam)
    private static final Pattern BLOCK = Pattern.compile(
            ".*\\b(?:bhejo|bhej|send|call|alarm|timer|reminder|yaad|bhool|whatsapp|kholo|khol|open)\\b.*");

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

    public static boolean isAsk(String utterance) {
        try {
            String w = norm(utterance);
            if (w.length() < 4 || BLOCK.matcher(w).matches()) {
                return false;
            }
            for (Pattern p : ASK) {
                if (p.matcher(w).matches()) {
                    return true;
                }
            }
        } catch (Throwable ignored) {
        }
        return false;
    }

    static final String SYSTEM = "Tum JARVIS ho, user ke phone par chalne wala voice assistant. Tumhe "
            + JarvisBrain.CREATOR + " ne banaya hai. User ne apne phone ki screen ke baare me sawal poochha "
            + "hai. Neeche screen par dikh rahe text ki list hai (ispe buttons, menu aur tabs ke naam bhi mix ho "
            + "sakte hain, unhe nazarandaaz karo aur asli content par dhyan do). Sawal ka jawab natural Hinglish "
            + "(Hindi Roman letters me) me do. Jawab bolkar sunaya jayega, isliye markdown, bullet, emoji, symbols "
            + "aur link mat likho. Summary maange to chaar vaakya me do. Reply ya jawab ka sujhav maange to "
            + "seedha wo message likh kar do jo user bhej sake, aur kisi ko bheja nahi gaya hai ye mat kaho. "
            + "Translate maange to translate karke sunao. Agar screen par sawal ka jawab nahi hai to saaf bolo, "
            + "andaza mat lagao.";

    /** Screen ke text par sawal ka jawab. "" = nahi bana (JarvisBrain.lastError dekho). */
    public static String answer(String key, String memory, String app, String screenText, String question) {
        String user = "Screen par dikh raha text (app: " + (app == null ? "" : app) + "):\n" + screenText
                + "\n\nUser ka sawal: " + question;
        return JarvisBrain.generate(key, "", SYSTEM + (memory == null ? "" : memory), user, false);
    }
}
