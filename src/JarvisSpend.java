package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.json.JSONArray;

/**
 * Paise ka hisaab: bank SMS aur UPI apps ke notification se "Rs 250 debited / paid to Zomato" jaisi baatein
 * apne aap note karta hai (sirf phone me, kahin bheja nahi jata) aur poochhne par batata hai:
 * "aaj kitna kharch hua", "is mahine ka kharch", "sabse zyada kahan kharch hua".
 * Is class me Android ka kaam sirf SharedPreferences hai.
 */
public final class JarvisSpend {
    private JarvisSpend() {
    }

    private static final String PREF = "jarvis_spend";
    private static final int MAX = 600;

    public static final class Entry {
        public long time;
        public double amt;
        public boolean debit;
        public String who = "";
    }

    // ---------------------------------------------------------------- notification --
    private static final Pattern AMT1 = Pattern.compile("(?:rs\\.?|inr|₹|rupees?)\\s*([0-9][0-9,]*(?:\\.[0-9]{1,2})?)");
    private static final Pattern AMT2 = Pattern.compile("([0-9][0-9,]*(?:\\.[0-9]{1,2})?)\\s*(?:rs\\b|inr\\b|rupees?\\b)");
    private static final Pattern NOT_MONEY = Pattern.compile(
            ".*\\b(?:otp|one time password|offer|offers|win|loan|apply|pre-?approved|credit limit|limit|reward|rewards|"
                    + "cashback of|upto|up to|avail|due|will be|request|requested|requests|collect|failed|declined|"
                    + "unsuccessful|could not|couldn't|pending|insufficient|reversed|expire|expires|expiring|"
                    + "get flat|flat|discount|emi of|click|apply now|voucher|coupon)\\b.*",
            Pattern.DOTALL);
    private static final Pattern DEBIT = Pattern.compile(
            ".*\\b(?:debited|debit|spent|paid|sent|withdrawn|purchase|payment of|transferred|txn of)\\b.*", Pattern.DOTALL);
    private static final Pattern CREDIT = Pattern.compile(
            ".*\\b(?:credited|credit|received|deposited|refunded|refund of)\\b.*", Pattern.DOTALL);
    private static final Pattern PAYEE = Pattern.compile(
            "(?:\\bto|\\bat|\\btowards|\\bmerchant|\\bfrom)\\s+([a-z0-9][a-z0-9 .&'@_\\-]{1,28}?)"
                    + "(?:\\s+(?:on|via|using|ref|upi|from|a/c|ac|avl|bal|for|has|is|was|successful)\\b|[.,;(]|\\s-\\s|$)");

    /** Ye package paise ki khabar de sakta hai? (SMS, UPI apps, bank apps) */
    static boolean moneyPkg(String pkg) {
        if (pkg == null) {
            return false;
        }
        String p = pkg.toLowerCase(Locale.ENGLISH);
        String[] keys = {"messag", "mms", "sms", "paisa", "phonepe", "paytm", "bank", "upi", "pay", "cred", "hdfc",
                "icici", "sbi", "axis", "kotak", "bhim", "mobikwik", "freecharge", "imobile", "yono", "idfc", "pnb"};
        for (String k : keys) {
            if (p.contains(k)) {
                return true;
            }
        }
        return false;
    }

    public static double parseAmount(String low) {
        Matcher m = AMT1.matcher(low);
        String s = null;
        if (m.find()) {
            s = m.group(1);
        } else {
            m = AMT2.matcher(low);
            if (m.find()) {
                s = m.group(1);
            }
        }
        if (s == null) {
            return -1;
        }
        try {
            return Double.parseDouble(s.replace(",", ""));
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    /** Notification se kharch/aamdani nikalo. null = ye paise ki khabar nahi hai. */
    public static Entry detect(String pkg, String title, String text, long time) {
        if (!moneyPkg(pkg)) {
            return null;
        }
        String low = (title + " " + text).toLowerCase(Locale.ENGLISH).replace('\n', ' ');
        if (low.length() < 10 || NOT_MONEY.matcher(low).matches()) {
            return null;
        }
        double amt = parseAmount(low);
        if (amt < 1 || amt > 10000000) {
            return null;
        }
        boolean deb = DEBIT.matcher(low).matches();
        boolean cre = CREDIT.matcher(low).matches();
        if (!deb && !cre) {
            return null;
        }
        Entry e = new Entry();
        e.time = time > 0 ? time : System.currentTimeMillis();
        e.amt = amt;
        e.debit = deb;                    // "debited ... credited to X" me bhi debit hi maana jata hai
        Matcher m = PAYEE.matcher(low);
        String who = "";
        while (m.find()) {
            String c = m.group(1).trim();
            if (!c.matches("^(?:your|you|a/c|ac|account|bank|upi|rs|inr|the|an?|my)\\b.*") && !c.matches("^[0-9 ]+$")) {
                who = c;
                break;
            }
        }
        e.who = tidy(who);
        return e;
    }

    private static String tidy(String w) {
        String t = w.replaceAll("\\s+", " ").trim();
        if (t.length() > 24) {
            t = t.substring(0, 24).trim();
        }
        return t;
    }

    // ------------------------------------------------------------------ store --
    private static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public static boolean tracking(Context c) {
        return sp(c).getString("off", "").length() == 0;
    }

    public static void setTracking(Context c, boolean on) {
        if (on) {
            sp(c).edit().remove("off").apply();
        } else {
            sp(c).edit().putString("off", "1").apply();
        }
    }

    private static String enc(Entry e) {
        return e.time + "|" + (e.debit ? "d" : "c") + "|" + e.amt + "|" + e.who.replace("|", " ");
    }

    private static Entry dec(String s) {
        try {
            String[] p = s.split("\\|", 4);
            Entry e = new Entry();
            e.time = Long.parseLong(p[0]);
            e.debit = p[1].equals("d");
            e.amt = Double.parseDouble(p[2]);
            e.who = p.length > 3 ? p[3] : "";
            return e;
        } catch (Exception ex) {
            return null;
        }
    }

    public static synchronized List<Entry> all(Context c) {
        List<Entry> out = new ArrayList<Entry>();
        try {
            JSONArray a = new JSONArray(sp(c).getString("items", "[]"));
            for (int i = 0; i < a.length(); i++) {
                Entry e = dec(a.optString(i, ""));
                if (e != null) {
                    out.add(e);
                }
            }
        } catch (Exception ignored) {
        }
        return out;
    }

    private static void saveAll(Context c, List<Entry> l) {
        JSONArray a = new JSONArray();
        for (Entry e : l) {
            a.put(enc(e));
        }
        sp(c).edit().putString("items", a.toString()).apply();
    }

    /** Naya notification aaya: paise ki khabar ho to note karo. true = note hua. */
    public static synchronized boolean onNotification(Context c, String pkg, String title, String text, long time) {
        try {
            if (!tracking(c)) {
                return false;
            }
            Entry e = detect(pkg, title, text, time);
            if (e == null) {
                return false;
            }
            List<Entry> all = all(c);
            for (Entry o : all) {
                // SMS aur UPI app dono batate hain: 5 minute me wahi rakam wahi disha = ek hi lenden
                if (o.debit == e.debit && Math.abs(o.amt - e.amt) < 0.01 && Math.abs(o.time - e.time) < 5 * 60000L) {
                    return false;
                }
            }
            all.add(e);
            while (all.size() > MAX) {
                all.remove(0);
            }
            saveAll(c, all);
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    public static synchronized void clear(Context c) {
        sp(c).edit().remove("items").apply();
    }

    // ------------------------------------------------------------------ parse --
    public static final int NONE = 0, REPORT = 1, TOP = 2, CLEAR = 3, TRACK_ON = 4, TRACK_OFF = 5;
    public static final int TODAY = 0, YESTERDAY = 1, WEEK = 2, MONTH = 3;

    public static final class Cmd {
        public int kind = NONE;
        public int range = TODAY;
        public String rangeName = "aaj";
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

    public static Cmd parse(String utterance) {
        Cmd c = new Cmd();
        String w = norm(utterance);
        if (w.length() < 5) {
            return c;
        }
        boolean money = w.matches(".*\\b(?:kharch|kharcha|kharche|spend|spent|spending|hisaab|hisab|expense|expenses)\\b.*");
        boolean income = w.matches(".*\\b(?:paisa|paise|rupaye|rupay|rupees|amount|money)\\b.*")
                && w.matches(".*\\b(?:aaye|aaya|aayi|mile|mila|credit|credited|received)\\b.*");
        boolean earn = w.matches(".*\\b(?:kamaya|kamai|income)\\b.*");
        if (!money && !income && !earn) {
            return c;
        }
        if (w.matches(".*\\b(?:saaf|clear|reset|delete|mita|hata)\\w*.*") && money) {
            c.kind = CLEAR;
            return c;
        }
        if (w.matches(".*\\b(?:track|tracking|note)\\b.*") && money) {
            boolean off = w.matches(".*\\b(?:band|off|mat|stop|nahi|nhi)\\b.*");
            c.kind = off ? TRACK_OFF : TRACK_ON;
            return c;
        }
        if (w.matches(".*\\b(?:sabse\\s+zyada|sabse\\s+jyada|kahan|kaha|kis\\s+par|kisko|top)\\b.*")) {
            c.kind = TOP;
        } else {
            c.kind = REPORT;
        }
        if (w.matches(".*\\b(?:mahine|mahina|month|mahine\\s+ka)\\b.*")) {
            c.range = MONTH;
            c.rangeName = "is mahine";
        } else if (w.matches(".*\\b(?:hafte|hafta|week|saptah)\\b.*")) {
            c.range = WEEK;
            c.rangeName = "is hafte";
        } else if (w.matches(".*\\b(?:kal|yesterday|beete\\s+kal)\\b.*")) {
            c.range = YESTERDAY;
            c.rangeName = "kal";
        } else {
            c.range = TODAY;
            c.rangeName = "aaj";
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

    // ----------------------------------------------------------------- answer --
    static String num(double v) {
        long r = Math.round(v);
        if (Math.abs(v - r) < 0.005 || v >= 100) {
            return String.valueOf(r);
        }
        return String.format(Locale.ENGLISH, "%.2f", v);
    }

    private static long startOf(int range, Calendar now) {
        Calendar c = (Calendar) now.clone();
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        if (range == YESTERDAY) {
            c.add(Calendar.DAY_OF_MONTH, -1);
        } else if (range == WEEK) {
            c.add(Calendar.DAY_OF_MONTH, -6);
        } else if (range == MONTH) {
            c.set(Calendar.DAY_OF_MONTH, 1);
        }
        return c.getTimeInMillis();
    }

    private static long endOf(int range, Calendar now) {
        if (range == YESTERDAY) {
            Calendar c = (Calendar) now.clone();
            c.set(Calendar.HOUR_OF_DAY, 0);
            c.set(Calendar.MINUTE, 0);
            c.set(Calendar.SECOND, 0);
            c.set(Calendar.MILLISECOND, 0);
            return c.getTimeInMillis();
        }
        return Long.MAX_VALUE;
    }

    /** Sunane layak jawab. */
    public static String answer(List<Entry> all, Cmd cmd, long nowMs) {
        Calendar now = Calendar.getInstance();
        now.setTimeInMillis(nowMs);
        long from = startOf(cmd.range, now);
        long to = endOf(cmd.range, now);
        double spent = 0, got = 0;
        int ns = 0, ng = 0;
        Map<String, Double> by = new HashMap<String, Double>();
        for (Entry e : all) {
            if (e.time < from || e.time >= to) {
                continue;
            }
            if (e.debit) {
                spent += e.amt;
                ns++;
                String k = e.who.length() == 0 ? "kisi aur" : e.who;
                Double o = by.get(k);
                by.put(k, (o == null ? 0 : o) + e.amt);
            } else {
                got += e.amt;
                ng++;
            }
        }
        if (ns == 0 && ng == 0) {
            return cmd.rangeName + " ka koi lenden mujhe nahi dikha. Main tabhi note karta hu jab bank SMS ya UPI app ka "
                    + "notification aata hai.";
        }
        List<Map.Entry<String, Double>> top = new ArrayList<Map.Entry<String, Double>>(by.entrySet());
        java.util.Collections.sort(top, new java.util.Comparator<Map.Entry<String, Double>>() {
            @Override
            public int compare(Map.Entry<String, Double> a, Map.Entry<String, Double> b) {
                return Double.compare(b.getValue(), a.getValue());
            }
        });
        StringBuilder sb = new StringBuilder();
        if (cmd.kind == TOP) {
            if (ns == 0) {
                return cmd.rangeName + " koi kharch nahi hua, sirf " + num(got) + " rupaye aaye.";
            }
            sb.append(cmd.rangeName).append(" sabse zyada ");
            int n = Math.min(3, top.size());
            for (int i = 0; i < n; i++) {
                sb.append(i > 0 ? ", phir " : "").append(top.get(i).getKey()).append(" par ")
                        .append(num(top.get(i).getValue())).append(" rupaye");
            }
            sb.append(" kharch hue. Kul ").append(num(spent)).append(" rupaye.");
            return sb.toString();
        }
        if (ns > 0) {
            sb.append(cmd.rangeName.substring(0, 1).toUpperCase(Locale.ENGLISH)).append(cmd.rangeName.substring(1))
                    .append(" ").append(ns).append(ns > 1 ? " baar" : " baar").append(" mein kul ").append(num(spent))
                    .append(" rupaye kharch hue. ");
            if (!top.isEmpty() && top.size() > 1) {
                sb.append("Sabse zyada ").append(top.get(0).getKey()).append(" par, ").append(num(top.get(0).getValue()))
                        .append(" rupaye. ");
            } else if (top.size() == 1 && !top.get(0).getKey().equals("kisi aur")) {
                sb.append("Ye ").append(top.get(0).getKey()).append(" par gaye. ");
            }
        } else {
            sb.append(cmd.rangeName.substring(0, 1).toUpperCase(Locale.ENGLISH)).append(cmd.rangeName.substring(1))
                    .append(" koi kharch nahi hua. ");
        }
        if (ng > 0) {
            sb.append(ng).append(" baar mein ").append(num(got)).append(" rupaye aaye.");
        }
        return sb.toString().trim();
    }
}
