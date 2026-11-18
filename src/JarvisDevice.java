package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.content.Intent;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.net.Uri;
import android.provider.Settings;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Phone ke settings bolkar badalna: torch, wifi, bluetooth, data, hotspot, airplane, location... on/off;
 * brightness aur volume kam/zyada/percent; battery; aapki location ka mausam.
 * Home-screen bubble aur app dono yahi use karte hain.
 *
 * handle(): null = ye mera kaam nahi. "@wait" = kaam peeche chal raha hai (working()/pending() dekho).
 * Warna turant ka jawab.
 */
public final class JarvisDevice {
    private JarvisDevice() {
    }

    // ------------------------------------------------------------------ parsing --
    public static final class Cmd {
        public String kind = "";          // toggle, brightness, volume, battery, weather, lock
        public String name = "";          // dikhane wala naam (wifi, bluetooth...)
        public String key = "";           // toggle ka key
        public String[] labels = new String[0];
        public int on = -1;               // 1 on, 0 off, -1 ulta
        public int percent = -1;          // 0-100 (seedha)
        public int step = 0;              // +/- percent (relative)
        public boolean auto = false;
        public boolean mute = false, unmute = false;
        public String stream = "music";
        public boolean tomorrow = false;
    }

    private static final String[][] TOGGLES = {
            // key, display, aliases (comma), tile labels (comma)
            {"torch", "Torch", "torch,flashlight,flash light,tarch,tourch,torchlight,torch light,flash", ""},
            {"wifi", "Wi-Fi", "wifi,wi fi,wlan,wireless", "wi-fi,wifi,wlan,internet,connected,!bluetooth,!hotspot,!mobile"},
            {"bluetooth", "Bluetooth", "bluetooth,blutooth,blue tooth,bluetooh,bt", "bluetooth,blue"},
            {"data", "Mobile data", "mobile data,internet data,cellular,mobile network,network,data,net,internet",
                    "mobile data,mobile network,cellular,data,internet"},
            {"hotspot", "Hotspot", "hotspot,hot spot,tethering", "hotspot,tethering,portable hotspot"},
            {"airplane", "Airplane mode", "airplane mode,aeroplane mode,flight mode,airplane,aeroplane,flight,plane mode",
                    "airplane,aeroplane,flight"},
            {"location", "Location", "location,gps", "location,gps"},
            {"rotate", "Auto-rotate", "auto rotate,autorotate,rotation,rotate", "auto-rotate,auto rotate,rotation,portrait,landscape"},
            {"saver", "Battery saver", "battery saver,power saver,power saving,battery saving,saver", "battery saver,power saving,power saver"},
            {"dnd", "Do not disturb", "do not disturb,dnd,disturb", "do not disturb,dnd"},
            {"nfc", "NFC", "nfc", "nfc"},
            {"dark", "Dark mode", "dark mode,dark theme,dark", "dark theme,dark mode,dark"},
    };

    private static final Set<String> ON_W = new HashSet<String>(Arrays.asList("on", "chalu", "chalao", "chala", "start",
            "enable", "activate", "jalao", "jala", "laga", "lagao", "kholo", "khol", "turn"));
    private static final Set<String> OFF_W = new HashSet<String>(Arrays.asList("off", "band", "bandh", "bund", "disable",
            "bujha", "bujhao", "bujhado", "stop", "hata", "hatao", "deactivate"));
    private static final Set<String> NOISE = new HashSet<String>(Arrays.asList("karo", "kro", "kar", "do", "de", "dijiye",
            "kijiye", "kariye", "kardo", "krdo", "dena", "please", "plz", "jarvis", "hey", "ab", "abhi", "zara", "jara",
            "ko", "ka", "ki", "ke", "se", "par", "pe", "me", "mein", "to", "the", "a", "aur", "phir", "bhi", "mera", "meri",
            "mere", "apna", "apni", "phone", "mobile", "ye", "wo", "isko", "usko", "ek", "turn", "switch", "set", "hi", "na",
            "hai", "h", "bas", "sirf", "theek", "thik", "wala", "wali"));
    private static final Set<String> GENERIC_BLOCK = new HashSet<String>(Arrays.asList("jarvis", "mic", "microphone", "screen",
            "display", "sunna", "listening", "wake", "agent", "mode", "silent", "vibrate", "sound", "volume", "brightness",
            "call", "message", "msg", "whatsapp", "instagram", "reels", "video", "music", "gaana", "song", "alarm", "timer",
            "app", "chrome", "youtube", "memory", "style", "busy", "driving", "routine", "briefing", "inbox", "auto", "reply"));

    static List<String> words(String text) {
        StringBuilder sb = new StringBuilder();
        for (char ch : (text == null ? "" : text).toLowerCase(Locale.ENGLISH).toCharArray()) {
            sb.append(Character.isLetterOrDigit(ch) || ch == '%' ? ch : ' ');
        }
        List<String> out = new ArrayList<String>();
        for (String w : sb.toString().trim().split("\\s+")) {
            if (w.length() > 0) {
                out.add(w);
            }
        }
        return out;
    }

    private static boolean any(List<String> w, String... xs) {
        for (String x : xs) {
            if (w.contains(x)) {
                return true;
            }
        }
        return false;
    }

    private static int numberIn(List<String> w) {
        for (String t : w) {
            String d = t.replace("%", "");
            if (d.length() > 0 && d.length() <= 3 && d.matches("\\d+")) {
                return Math.min(100, Integer.parseInt(d));
            }
        }
        String[][] words = {{"zero", "0"}, {"das", "10"}, {"bees", "20"}, {"tees", "30"}, {"chalis", "40"}, {"pachas", "50"},
                {"aadha", "50"}, {"half", "50"}, {"saath", "60"}, {"sattar", "70"}, {"assi", "80"}, {"nabbe", "90"},
                {"sau", "100"}, {"pachees", "25"}, {"paintees", "35"}, {"pachhattar", "75"}, {"pandrah", "15"}};
        for (String t : w) {
            for (String[] p : words) {
                if (t.equals(p[0])) {
                    return Integer.parseInt(p[1]);
                }
            }
        }
        return -1;
    }

    private static boolean containsPhrase(String joined, String phrase) {
        return (" " + joined + " ").contains(" " + phrase + " ");
    }

    /** null = ye device command nahi. */
    public static Cmd parse(String text) {
        List<String> w = words(text);
        if (w.isEmpty() || w.size() > 14) {
            return null;
        }
        StringBuilder jb = new StringBuilder();
        for (String t : w) {
            jb.append(t).append(' ');
        }
        String joined = jb.toString().trim();
        boolean question = (any(w, "kya", "kitna", "kitni", "status") && !any(w, "karo", "kro", "kar", "do"));

        // ---- battery
        if (any(w, "battery", "bettery", "batri") && !containsPhrase(joined, "battery saver")
                && !containsPhrase(joined, "power saver")
                && any(w, "kitni", "kitna", "level", "percent", "percentage", "kya", "status", "charge", "charging", "bachi", "bacha", "batao", "bata")) {
            Cmd c = new Cmd();
            c.kind = "battery";
            return c;
        }
        // ---- mausam
        if (any(w, "mausam", "weather", "temperature", "taapmaan", "tapman", "mosam")) {
            Set<String> filler = new HashSet<String>(Arrays.asList("mausam", "weather", "temperature", "taapmaan", "tapman",
                    "mosam", "aaj", "abhi", "kaisa", "kaisi", "hai", "batao", "bata", "do", "kya", "ka", "ki", "ke", "mera",
                    "mere", "yaha", "yahan", "yahaan", "here", "current", "today", "kal", "shehar", "city", "jarvis", "hey",
                    "is", "iska", "meri", "location", "ke", "liye", "report", "update", "janna", "jaanna", "chahta", "chahiye",
                    "tell", "me", "what", "whats", "the", "how", "is", "it", "outside", "bahar", "kitna", "kitni", "kaise",
                    "please", "pls", "dikhao", "sunao", "sunana", "bataiye", "bataye", "hu", "hoon", "main", "mai", "me", "mein",
                    "par", "pe", "abhi", "right", "now", "aaj", "kaisa", "rahega", "rahegi", "hoga", "hogi", "barish", "garmi", "sardi"));
            for (String t : w) {
                if (!filler.contains(t)) {
                    return null;                 // kisi shehar ka naam hai: purana mausam-wala hissa sambhale
                }
            }
            Cmd c = new Cmd();
            c.kind = "weather";
            c.tomorrow = any(w, "kal", "tomorrow");
            return c;
        }
        // ---- screen lock
        if (any(w, "screen", "display", "phone") && any(w, "lock", "off", "band", "bandh") && any(w, "karo", "kro", "kar", "do", "kardo")
                && !any(w, "brightness", "volume", "wifi", "data")) {
            Cmd c = new Cmd();
            c.kind = "lock";
            return c;
        }
        // ---- brightness
        if (any(w, "brightness", "brightnes", "roshni", "brightnessnahi", "birghtness", "britness")) {
            Cmd c = new Cmd();
            c.kind = "brightness";
            if (any(w, "auto", "automatic")) {
                c.auto = true;
                c.on = any(w, "off", "band", "bandh", "disable") ? 0 : 1;
                return c;
            }
            int n = numberIn(w);
            if (n >= 0) {
                c.percent = n;
            } else if (any(w, "max", "maximum", "full", "poori", "pura", "puri", "sabse", "zyada") && !any(w, "kam")) {
                c.percent = 100;
                if (any(w, "kam", "low", "min", "minimum")) {
                    c.percent = 5;
                }
            } else if (any(w, "min", "minimum", "lowest", "sabse") && any(w, "kam", "low", "min", "minimum", "lowest")) {
                c.percent = 3;
            } else if (any(w, "kam", "kum", "ghata", "ghatao", "low", "halka", "halki", "dim", "decrease", "down", "less", "lower",
                    "kamm", "kam")) {
                c.step = -20;
            } else if (any(w, "badha", "badhao", "badhado", "bada", "badi", "zyada", "jyada", "tez", "high", "increase", "up",
                    "more", "higher", "ziyada", "tej")) {
                c.step = 20;
            } else {
                return null;
            }
            if (any(w, "thora", "thoda", "thodi", "zara", "jara", "little", "bit", "slightly") && c.step != 0) {
                c.step = c.step > 0 ? 10 : -10;
            }
            if (any(w, "bahut", "kaafi", "kafi", "very", "zyada") && c.step != 0 && !any(w, "badhao", "badha")) {
                c.step = c.step > 0 ? 35 : -35;
            }
            return c;
        }
        // ---- volume / awaaz
        if (any(w, "volume", "vol", "awaaz", "aawaz", "avaaz", "awaz", "sound", "mute", "unmute", "silent")
                && !any(w, "alarm") || (any(w, "volume") && any(w, "alarm"))) {
            Cmd c = new Cmd();
            c.kind = "volume";
            if (any(w, "ring", "ringtone", "ringer", "ringing")) {
                c.stream = "ring";
            } else if (any(w, "alarm")) {
                c.stream = "alarm";
            } else if (any(w, "call", "calling")) {
                c.stream = "voice";
            } else if (any(w, "notification", "notifications")) {
                c.stream = "notif";
            }
            if (any(w, "silent", "chup") && c.stream.equals("music") && !any(w, "volume", "media", "music")) {
                c.stream = "ring";
            }
            if (any(w, "unmute", "unsilent") || (any(w, "sound", "awaaz", "aawaz") && any(w, "on", "chalu", "wapas", "vapas"))) {
                c.unmute = true;
                return c;
            }
            if (any(w, "mute", "silent", "chup") || (any(w, "sound", "awaaz", "aawaz", "volume") && any(w, "off", "band", "bandh"))) {
                c.mute = true;
                return c;
            }
            int n = numberIn(w);
            if (n >= 0) {
                c.percent = n;
            } else if (any(w, "max", "maximum", "full", "poori", "pura", "puri") && !any(w, "kam")) {
                c.percent = 100;
            } else if (any(w, "min", "minimum", "lowest")) {
                c.percent = 5;
            } else if (any(w, "kam", "kum", "ghata", "ghatao", "low", "halka", "halki", "dheema", "dheemi", "dheere", "decrease",
                    "down", "less", "lower", "kamm", "slow", "dhima")) {
                c.step = -15;
            } else if (any(w, "badha", "badhao", "badhado", "bada", "badi", "zyada", "jyada", "tez", "tej", "high", "increase",
                    "up", "more", "higher", "ziyada", "loud", "jor", "zor")) {
                c.step = 15;
            } else {
                return null;
            }
            if (any(w, "thora", "thoda", "thodi", "zara", "jara", "little", "bit", "slightly") && c.step != 0) {
                c.step = c.step > 0 ? 8 : -8;
            }
            return c;
        }
        // ---- toggles (torch, wifi, bluetooth...)
        int state = -2;
        for (String t : w) {
            if (ON_W.contains(t)) {
                state = 1;
            } else if (OFF_W.contains(t)) {
                state = 0;
            }
        }
        if (state == -2) {
            return null;
        }
        if (any(w, "kholo", "khol") && !any(w, "on")) {
            // "wifi kholo" = on; lekin "settings kholo" jaisa app-kholna nahi, isliye aage naam ka match zaroori hai
        }
        if (question) {
            return null;
        }
        for (String[] row : TOGGLES) {
            for (String alias : row[2].split(",")) {
                if (containsPhrase(joined, alias)) {
                    if (row[0].equals("torch") && alias.equals("flash") && w.size() > 4) {
                        continue;
                    }
                    Cmd c = new Cmd();
                    c.kind = "toggle";
                    c.key = row[0];
                    c.name = row[1];
                    c.labels = row[3].length() == 0 ? new String[0] : row[3].split(",");
                    c.on = state;
                    return c;
                }
            }
        }
        // ---- koi bhi aur tile ("screen cast on karo", "sync on karo"): sirf saaf "on/off" ke saath
        boolean explicit = any(w, "on", "off", "chalu", "enable", "disable");
        if (explicit && w.size() <= 5) {
            List<String> nm = new ArrayList<String>();
            for (String t : w) {
                if (ON_W.contains(t) || OFF_W.contains(t) || NOISE.contains(t)) {
                    continue;
                }
                if (GENERIC_BLOCK.contains(t)) {
                    return null;
                }
                nm.add(t);
            }
            if (!nm.isEmpty() && nm.size() <= 3) {
                StringBuilder s = new StringBuilder();
                for (String t : nm) {
                    if (s.length() > 0) {
                        s.append(' ');
                    }
                    s.append(t);
                }
                Cmd c = new Cmd();
                c.kind = "toggle";
                c.key = "other";
                c.name = s.toString();
                c.labels = new String[]{s.toString()};
                c.on = state;
                return c;
            }
        }
        return null;
    }

    // ---------------------------------------------------------------- execution --
    private static volatile boolean working = false;
    private static volatile String pending = "";
    private static boolean torchOn = false;

    public static boolean working() {
        return working;
    }

    /** Peeche wale kaam ka aakhri jawab (ek baar). */
    public static synchronized String pending() {
        String p = pending;
        pending = "";
        return p;
    }

    public static String handle(final Context ctx, String text) {
        final Cmd c;
        try {
            c = parse(text);
        } catch (Throwable t) {
            return null;
        }
        if (c == null) {
            return null;
        }
        try {
            if ("battery".equals(c.kind)) {
                return battery(ctx);
            } else if ("brightness".equals(c.kind)) {
                return brightness(ctx, c);
            } else if ("volume".equals(c.kind)) {
                return volume(ctx, c);
            } else if ("lock".equals(c.kind)) {
                JarvisAccessService svc = JarvisAccessService.instance;
                if (svc != null && svc.lockScreen()) {
                    return "Screen lock kar di.";
                }
                return "Screen lock karne ke liye Accessibility me JARVIS chalu hona chahiye (Android 9 ya naya).";
            } else if ("weather".equals(c.kind)) {
                if (working) {
                    return "Main abhi ek kaam kar raha hoon, thoda ruko.";
                }
                working = true;
                pending = "";
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        String r;
                        try {
                            r = JarvisWeather.fetch(ctx, c.tomorrow);
                        } catch (Throwable t) {
                            r = "Mausam abhi nahi mil paya. Internet check karke dobara poochho.";
                        }
                        finish(r);
                    }
                }).start();
                return "@wait";
            } else if ("toggle".equals(c.kind)) {
                if ("torch".equals(c.key)) {
                    return torchSmart(ctx, c);
                }
                return tile(ctx, c);
            }
        } catch (Throwable t) {
            return "Ye kaam nahi ho paya: " + t.getMessage();
        }
        return null;
    }

    private static synchronized void finish(String r) {
        pending = r;
        working = false;
    }

    /** Asli haalat: 1 on, 0 off, -1 pata nahi. */
    static int stateOf(Context ctx, String key) {
        Context app = ctx.getApplicationContext() == null ? ctx : ctx.getApplicationContext();
        try {
            if ("wifi".equals(key)) {
                int v = Settings.Global.getInt(app.getContentResolver(), "wifi_on", -1);
                return v < 0 ? -1 : (v == 0 ? 0 : 1);
            } else if ("bluetooth".equals(key)) {
                int v = Settings.Global.getInt(app.getContentResolver(), "bluetooth_on", -1);
                return v < 0 ? -1 : (v == 0 ? 0 : 1);
            } else if ("airplane".equals(key)) {
                return Settings.Global.getInt(app.getContentResolver(), "airplane_mode_on", 0) != 0 ? 1 : 0;
            } else if ("data".equals(key)) {
                int v = Settings.Global.getInt(app.getContentResolver(), "mobile_data", -1);
                return v < 0 ? -1 : (v == 0 ? 0 : 1);
            } else if ("location".equals(key)) {
                int m = Settings.Secure.getInt(app.getContentResolver(), "location_mode", -1);
                return m < 0 ? -1 : (m == 0 ? 0 : 1);
            } else if ("rotate".equals(key)) {
                return Settings.System.getInt(app.getContentResolver(), "accelerometer_rotation", 0) != 0 ? 1 : 0;
            } else if ("saver".equals(key)) {
                android.os.PowerManager pm = (android.os.PowerManager) app.getSystemService(Context.POWER_SERVICE);
                return pm != null && pm.isPowerSaveMode() ? 1 : 0;
            } else if ("dnd".equals(key)) {
                android.app.NotificationManager nm = (android.app.NotificationManager) app.getSystemService(Context.NOTIFICATION_SERVICE);
                if (nm == null || android.os.Build.VERSION.SDK_INT < 23) {
                    return -1;
                }
                return nm.getCurrentInterruptionFilter() == android.app.NotificationManager.INTERRUPTION_FILTER_ALL ? 0 : 1;
            } else if ("hotspot".equals(key)) {
                android.net.wifi.WifiManager wm = (android.net.wifi.WifiManager) app.getSystemService(Context.WIFI_SERVICE);
                java.lang.reflect.Method m = wm.getClass().getDeclaredMethod("isWifiApEnabled");
                m.setAccessible(true);
                return ((Boolean) m.invoke(wm)).booleanValue() ? 1 : 0;
            } else if ("nfc".equals(key)) {
                android.nfc.NfcAdapter na = android.nfc.NfcAdapter.getDefaultAdapter(app);
                return na == null ? -1 : (na.isEnabled() ? 1 : 0);
            } else if ("torch".equals(key)) {
                torchWatch(app);
                return torchKnown ? (torchOn ? 1 : 0) : -1;
            }
        } catch (Throwable t) {
            return -1;
        }
        return -1;
    }

    private static boolean torchKnown = false, torchWatching = false;

    private static synchronized void torchWatch(Context app) {
        if (torchWatching) {
            return;
        }
        torchWatching = true;
        try {
            CameraManager cm = (CameraManager) app.getSystemService(Context.CAMERA_SERVICE);
            cm.registerTorchCallback(new CameraManager.TorchCallback() {
                @Override
                public void onTorchModeChanged(String id, boolean enabled) {
                    torchKnown = true;
                    torchOn = enabled;
                }
            }, new android.os.Handler(android.os.Looper.getMainLooper()));
            Thread.sleep(400);
        } catch (Throwable ignored) {
        }
    }

    private static String tile(final Context ctx, final Cmd c) {
        final JarvisAccessService svc = JarvisAccessService.instance;
        if (svc == null) {
            return "Ye karne ke liye Accessibility me JARVIS ko on karna hoga. Settings me Accessibility kholkar JARVIS on kijiye.";
        }
        if (working) {
            return "Main abhi ek kaam kar raha hoon, thoda ruko.";
        }
        working = true;
        pending = "";
        new Thread(new Runnable() {
            @Override
            public void run() {
                String r;
                try {
                    final String key = c.key;
                    JarvisAccessService.Probe probe = "other".equals(key) ? null : new JarvisAccessService.Probe() {
                        @Override
                        public int get() {
                            return stateOf(ctx, key);
                        }
                    };
                    int res = svc.quickTile(c.labels, c.on, probe);
                    String st = c.on == 1 ? "on" : c.on == 0 ? "off" : "";
                    int now = probe == null ? -1 : stateOf(ctx, key);
                    String nowTxt = now == 1 ? "on" : now == 0 ? "off" : st;
                    if (res == 1) {
                        r = c.name + " " + nowTxt + " ho gaya.";
                    } else if (res == 2) {
                        r = c.name + " pehle se " + (st.length() == 0 ? nowTxt : st) + " hai.";
                    } else if (res == 3) {
                        r = c.name + " ka button daba diya. Asli haalat main check nahi kar paya, ek baar dekh lena.";
                    } else if (res == 4) {
                        r = c.name + " badal nahi paya, button dabane par bhi " + nowTxt
                                + " hi raha. Ho sakta hai phone use rok raha ho (jaise SIM na ho ya system ne roka ho).";
                    } else if (res == 0) {
                        r = c.name + " ka button Quick Settings me nahi mila. Use panel me jod lo ya naam alag bolo.";
                    } else {
                        r = "Quick Settings panel nahi khul paya. Accessibility me JARVIS on hai ya nahi dekho.";
                    }
                } catch (Throwable t) {
                    r = "Ye kaam nahi ho paya: " + t.getMessage();
                }
                finish(r);
            }
        }).start();
        return "@wait";
    }

    /** Torch: pehle Quick Settings ki tile se (taaki panel me bhi sahi dikhe), na ho to seedha. */
    private static String torchSmart(final Context ctx, final Cmd c) {
        JarvisAccessService svc = JarvisAccessService.instance;
        if (svc == null) {
            return torch(ctx, c.on);
        }
        stateOf(ctx, "torch");
        int cur = stateOf(ctx, "torch");
        if (c.on >= 0 && cur == c.on) {
            return c.on == 1 ? "Torch pehle se on hai." : "Torch pehle se band hai.";
        }
        if (working) {
            return "Main abhi ek kaam kar raha hoon, thoda ruko.";
        }
        working = true;
        pending = "";
        final Cmd cc = c;
        new Thread(new Runnable() {
            @Override
            public void run() {
                String r;
                try {
                    JarvisAccessService s = JarvisAccessService.instance;
                    int res = s == null ? -1 : s.quickTile(new String[]{"flashlight", "torch", "flash"}, cc.on,
                            new JarvisAccessService.Probe() {
                                @Override
                                public int get() {
                                    return stateOf(ctx, "torch");
                                }
                            });
                    if (res == 1 || res == 2) {
                        r = stateOf(ctx, "torch") == 1 ? "Torch on ho gayi." : "Torch band ho gayi.";
                    } else {
                        r = torch(ctx, cc.on);
                    }
                } catch (Throwable t) {
                    r = torch(ctx, cc.on);
                }
                finish(r);
            }
        }).start();
        return "@wait";
    }

    private static String torch(Context ctx, int on) {
        try {
            CameraManager cm = (CameraManager) ctx.getSystemService(Context.CAMERA_SERVICE);
            String id = null;
            for (String s : cm.getCameraIdList()) {
                CameraCharacteristics ch = cm.getCameraCharacteristics(s);
                Boolean flash = ch.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
                Integer facing = ch.get(CameraCharacteristics.LENS_FACING);
                if (flash != null && flash && facing != null && facing == CameraCharacteristics.LENS_FACING_BACK) {
                    id = s;
                    break;
                }
            }
            if (id == null) {
                return "Is phone me torch nahi mili.";
            }
            boolean want = on < 0 ? !torchOn : on == 1;
            cm.setTorchMode(id, want);
            torchOn = want;
            return want ? "Torch on kar di." : "Torch band kar di.";
        } catch (Throwable t) {
            return "Torch nahi chal paayi. Camera kisi aur app me khula ho sakta hai.";
        }
    }

    private static String battery(Context ctx) {
        Intent b = ctx.registerReceiver(null, new android.content.IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        int level = b == null ? -1 : b.getIntExtra("level", -1);
        int scale = b == null ? 100 : b.getIntExtra("scale", 100);
        int status = b == null ? 0 : b.getIntExtra("status", 0);
        boolean charging = status == 2 || status == 5;
        int pct = level < 0 ? -1 : Math.round(level * 100f / Math.max(1, scale));
        return pct < 0 ? "Battery ka pata nahi chal paya."
                : "Battery " + pct + " percent hai" + (charging ? " aur charge ho rahi hai." : ".");
    }

    private static String brightness(Context ctx, Cmd c) {
        if (!Settings.System.canWrite(ctx)) {
            try {
                Intent i = new Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS, Uri.parse("package:" + ctx.getPackageName()));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                ctx.startActivity(i);
            } catch (Throwable ignored) {
            }
            return "Brightness badalne ke liye is screen me JARVIS ko allow kijiye, phir dobara bolo.";
        }
        android.content.ContentResolver cr = ctx.getContentResolver();
        if (c.auto) {
            Settings.System.putInt(cr, Settings.System.SCREEN_BRIGHTNESS_MODE, c.on == 1 ? 1 : 0);
            return c.on == 1 ? "Auto brightness on kar di." : "Auto brightness band kar di.";
        }
        int cur;
        try {
            cur = Settings.System.getInt(cr, Settings.System.SCREEN_BRIGHTNESS);
        } catch (Exception e) {
            cur = 128;
        }
        int curPct = Math.round(cur * 100f / 255f);
        int target = c.percent >= 0 ? c.percent : Math.max(1, Math.min(100, curPct + c.step));
        target = Math.max(1, Math.min(100, target));
        Settings.System.putInt(cr, Settings.System.SCREEN_BRIGHTNESS_MODE, Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL);
        Settings.System.putInt(cr, Settings.System.SCREEN_BRIGHTNESS, Math.max(1, Math.round(target * 255f / 100f)));
        return "Brightness " + target + " percent kar di.";
    }

    private static int streamOf(String s) {
        if ("ring".equals(s)) return AudioManager.STREAM_RING;
        if ("alarm".equals(s)) return AudioManager.STREAM_ALARM;
        if ("voice".equals(s)) return AudioManager.STREAM_VOICE_CALL;
        if ("notif".equals(s)) return AudioManager.STREAM_NOTIFICATION;
        return AudioManager.STREAM_MUSIC;
    }

    private static String volume(Context ctx, Cmd c) {
        AudioManager am = (AudioManager) ctx.getSystemService(Context.AUDIO_SERVICE);
        int st = streamOf(c.stream);
        String nm = "ring".equals(c.stream) ? "Ringtone" : "alarm".equals(c.stream) ? "Alarm"
                : "voice".equals(c.stream) ? "Call" : "notif".equals(c.stream) ? "Notification" : "Volume";
        int max = Math.max(1, am.getStreamMaxVolume(st));
        if (c.mute) {
            if (st == AudioManager.STREAM_RING || st == AudioManager.STREAM_NOTIFICATION) {
                try {
                    am.setRingerMode(AudioManager.RINGER_MODE_SILENT);
                    return "Phone silent kar diya.";
                } catch (SecurityException e) {
                    try {
                        am.setRingerMode(AudioManager.RINGER_MODE_VIBRATE);
                        return "Silent ki permission nahi hai, isliye vibrate par kar diya.";
                    } catch (Throwable t) {
                        return "Silent karne ke liye Do Not Disturb access chahiye.";
                    }
                }
            }
            am.setStreamVolume(st, 0, AudioManager.FLAG_SHOW_UI);
            return nm + " mute kar diya.";
        }
        if (c.unmute) {
            try {
                am.setRingerMode(AudioManager.RINGER_MODE_NORMAL);
            } catch (Throwable ignored) {
            }
            int v = Math.max(1, Math.round(max * 0.5f));
            if (am.getStreamVolume(st) == 0) {
                am.setStreamVolume(st, v, AudioManager.FLAG_SHOW_UI);
            }
            return "Awaaz wapas chalu kar di.";
        }
        int curPct = Math.round(am.getStreamVolume(st) * 100f / max);
        int target = c.percent >= 0 ? c.percent : Math.max(0, Math.min(100, curPct + c.step));
        int val = Math.max(c.percent == 0 ? 0 : (target > 0 ? 1 : 0), Math.round(max * target / 100f));
        try {
            if (st == AudioManager.STREAM_RING || st == AudioManager.STREAM_NOTIFICATION) {
                am.setRingerMode(AudioManager.RINGER_MODE_NORMAL);
            }
        } catch (Throwable ignored) {
        }
        am.setStreamVolume(st, Math.min(max, val), AudioManager.FLAG_SHOW_UI);
        return nm + " " + target + " percent kar diya.";
    }
}
