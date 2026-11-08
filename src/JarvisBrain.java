package org.myassistant.myvoiceassistant;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/** Gemini se baat aur "kaam" (function calling). Overlay isi ko use karta hai. */
public class JarvisBrain {
    public static class Result {
        public String reply = "";
        public String function = null;
        public JSONObject args = null;
        public String error = null;
        public boolean quota = false;     // free limit khatam
        public boolean badKey = false;    // key galat/band
        public boolean net = false;       // internet nahi
    }

    public static final String CREATOR = "Shakshm Jha";
    private static final String BASE = "https://generativelanguage.googleapis.com/v1beta";
    private static final String[] FALLBACK = {"gemini-2.5-flash", "gemini-3-flash-preview",
            "gemini-2.0-flash"};
    private static final List<String[]> HISTORY = new ArrayList<String[]>();
    public static String lastModel = "";
    /** Yaaddasht ka text (JarvisMemory.block). Har baat-cheet ke system prompt me judta hai. */
    public static volatile String memory = "";

    // ------------------------------------------------------------------ ask --
    private static Result askOne(String key, String model, String verbosity, String text) {
        Result r = new Result();
        List<String> models = new ArrayList<String>();
        if (model != null && model.length() > 0) {
            models.add(model);
        }
        for (String m : FALLBACK) {
            if (!models.contains(m)) {
                models.add(m);
            }
        }
        String lastError = "Gemini ka koi model abhi available nahi mila. Thodi der baad try kijiye.";
        boolean quotaHit = false;
        try {
            for (String m : models) {
                int[] status = new int[1];
                String body = post(key, m, buildBody(m, verbosity, text, true), status);
                if (status[0] == 400 && body.toLowerCase(Locale.ENGLISH).contains("thinking")) {
                    body = post(key, m, buildBody(m, verbosity, text, false), status);
                }
                if (status[0] == 200) {
                    parse(body, r);
                    if (r.error == null) {
                        lastModel = m;
                        remember(text, r);
                    }
                    return r;
                }
                String low = body.toLowerCase(Locale.ENGLISH);
                if (low.contains("api key") || status[0] == 401) {
                    r.error = "Gemini API key sahi nahi lag rahi. Jarvis app ki Settings me key dobara check kijiye.";
                    r.badKey = true;
                    return r;
                }
                if (status[0] == 429 || low.contains("quota") || low.contains("resource_exhausted")) {
                    lastError = "Abhi Gemini ki free limit poori ho gayi hai. Thodi der baad dobara poochiye.";
                    quotaHit = true;
                    continue;
                }
                if (status[0] == 404 || (status[0] == 400 && low.contains("model"))) {
                    continue;
                }
                if (status[0] == 403) {
                    r.error = "Gemini ne is key ko allow nahi kiya. Key ya uski permission check kijiye.";
                    r.badKey = true;
                    return r;
                }
                if (status[0] >= 500) {
                    r.error = "Gemini server abhi busy hai. Thodi der baad dobara try kijiye.";
                    return r;
                }
                r.error = "AI se baat karte waqt kuch gadbad ho gayi. Dobara try kijiye.";
                return r;
            }
            r.error = lastError;
            r.quota = quotaHit;
        } catch (IOException e) {
            r.error = "Internet nahi chal raha lagta hai. Connection check karke dobara boliye.";
            r.net = true;
        } catch (Exception e) {
            r.error = "AI se baat karte waqt kuch gadbad ho gayi. Dobara try kijiye.";
        }
        return r;
    }

    public static String lastError = "";
    private static int failKind = 0;     // 0 theek, 1 free limit, 2 galat key, 3 anya, 4 internet

    /** Bina history/tools ke seedha text banao (message ka reply likhne ke liye). "" = nahi ban paya. */
    public static String generate(String key, String model, String system, String user) {
        return generate(key, model, system, user, false);
    }

    private static final java.util.Map<String, String> HINDI_CACHE = new java.util.HashMap<String, String>();
    private static final String HINDI_SYSTEM = "Tum Hinglish (Roman me likhi Hindi) ko Devanagari Hindi me badalte ho "
            + "taaki text-to-speech asli Indian Hindi jaisa bole. Matlab aur shabd bilkul na badlo, sirf lipi badlo. "
            + "English shabd (WhatsApp, message, call, Instagram) Devanagari me likho (jaise व्हाट्सएप, मैसेज). "
            + "Naam Devanagari me likho. Sankhya/time jaise 5 baje ko '5 बजे' likho. "
            + "Agar poora text sirf English sentence hai to use bilkul waisa hi lautao. "
            + "Sirf badla hua text do, koi samjhaish ya quote nahi.";

    public static boolean hasDevanagari(String t) {
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            if (c >= 0x0900 && c <= 0x097f) {
                return true;
            }
        }
        return false;
    }

    /** Hinglish -> Devanagari (Indian lehje ke liye). Na ban paye to null (matlab jaisa tha waisa bolo). */
    public static String devanagari(String key, String text) {
        if (key == null || key.trim().length() == 0 || text == null || text.trim().length() == 0) {
            return null;
        }
        if (hasDevanagari(text)) {
            return text;
        }
        synchronized (HINDI_CACHE) {
            String c = HINDI_CACHE.get(text);
            if (c != null) {
                return c.length() == 0 ? null : c;
            }
        }
        String out = generateImpl(key, "", HINDI_SYSTEM, text, true, false);   // Hindi lipi: Gemini hi behtar
        String res = (out != null && out.trim().length() > 0 && hasDevanagari(out)) ? out.trim() : "";
        if (out != null && out.trim().length() > 0) {
            synchronized (HINDI_CACHE) {
                if (HINDI_CACHE.size() > 200) {
                    HINDI_CACHE.clear();
                }
                HINDI_CACHE.put(text, res);
            }
        }
        return res.length() == 0 ? null : res;
    }

    private static final String[] FAST = {"gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"};

    /** fast = sabse tez model pehle, chhota jawab, kam intezaar (auto-reply ke liye: 1-2 second). */
    private static String generateOne(String key, String model, String system, String user, boolean fast) {
        lastError = "";
        failKind = 0;
        List<String> models = new ArrayList<String>();
        if (fast) {
            for (String m : FAST) {
                models.add(m);
            }
        }
        if (model != null && model.length() > 0 && !models.contains(model)) {
            models.add(model);
        }
        for (String m : FALLBACK) {
            if (!models.contains(m)) {
                models.add(m);
            }
        }
        try {
            for (String m : models) {
                int[] status = new int[1];
                String body = post(key, m, plainBody(m, system, user, true, fast), status, fast ? 9000 : 45000);
                if (status[0] == 400 && body.toLowerCase(Locale.ENGLISH).contains("thinking")) {
                    body = post(key, m, plainBody(m, system, user, false, fast), status, fast ? 9000 : 45000);
                }
                if (status[0] == 200) {
                    Result r = new Result();
                    parse(body, r);
                    if (r.error == null && r.reply.length() > 0) {
                        lastModel = m;
                        return r.reply;
                    }
                    lastError = r.error == null ? "khali jawab" : r.error;
                    return "";
                }
                lastError = "Gemini error " + status[0];
                String lowb = body.toLowerCase(Locale.ENGLISH);
                if (status[0] == 429 || lowb.contains("resource_exhausted")) {
                    failKind = 1;
                    continue;
                }
                if (status[0] == 401 || status[0] == 403 || (status[0] == 400 && lowb.contains("api key"))) {
                    failKind = 2;
                    return "";
                }
                if (status[0] == 404 || (status[0] == 400 && lowb.contains("model"))) {
                    continue;
                }
                failKind = 3;
                return "";
            }
        } catch (Exception e) {
            lastError = "internet/AI galti";
            failKind = 4;
        }
        return "";
    }


    // ============================================ kai keys + doosre free AI (limit khatam ho to) ==
    private static final java.util.Map<String, Long> BLOCKED = new java.util.HashMap<String, Long>();
    private static final long BLOCK_MS = 2 * 60 * 1000L;
    private static final String[][] COMPAT = {
            {"gsk_", "https://api.groq.com/openai/v1", "Groq"},
            {"csk-", "https://api.cerebras.ai/v1", "Cerebras"}};
    private static final java.util.Map<String, List<String>> COMPAT_MODELS = new java.util.HashMap<String, List<String>>();

    /** Settings me ek se zyada keys (comma/space/nayi line se alag) ho sakti hain. */
    public static List<String> splitKeys(String raw) {
        List<String> out = new ArrayList<String>();
        if (raw == null) {
            return out;
        }
        for (String k : raw.split("[,;\\s]+")) {
            k = k.trim();
            if (k.length() >= 8 && !out.contains(k)) {
                out.add(k);
            }
        }
        return out;
    }

    private static String[] compatOf(String key) {
        for (String[] c : COMPAT) {
            if (key.startsWith(c[0])) {
                return c;
            }
        }
        return null;
    }

    private static List<String> geminiKeys(String raw) {
        List<String> g = new ArrayList<String>();
        for (String k : splitKeys(raw)) {
            if (compatOf(k) == null) {
                g.add(k);
            }
        }
        if (g.isEmpty() && splitKeys(raw).isEmpty() && raw != null && raw.trim().length() > 0) {
            g.add(raw.trim());
        }
        return g;
    }

    private static List<String> compatKeys(String raw) {
        List<String> g = new ArrayList<String>();
        for (String k : splitKeys(raw)) {
            if (compatOf(k) != null) {
                g.add(k);
            }
        }
        return g;
    }

    private static synchronized boolean isBlocked(String key) {
        Long t = BLOCKED.get(key);
        return t != null && t > System.currentTimeMillis();
    }

    private static final java.util.Map<String, Integer> BLOCK_HITS = new java.util.HashMap<String, Integer>();

    /** Limit lagi: pehli baar 2 min, lagataar lagti rahe to 4, 8, 16... max 1 ghanta (din ki limit me bekaar koshish nahi). */
    private static synchronized void block(String key) {
        Integer h = BLOCK_HITS.get(key);
        int hits = h == null ? 1 : Math.min(h + 1, 6);
        BLOCK_HITS.put(key, hits);
        long ms = Math.min(BLOCK_MS * (1L << (hits - 1)), 60L * 60 * 1000L);
        BLOCKED.put(key, System.currentTimeMillis() + ms);
    }

    private static synchronized void good(String key) {
        BLOCK_HITS.remove(key);
    }

    /** Chalne layak keys: jinki limit abhi khatam nahi mani gayi pehle; sab blocked ho to sab. */
    private static List<String> usable(List<String> keys) {
        List<String> ok = new ArrayList<String>();
        for (String k : keys) {
            if (!isBlocked(k)) {
                ok.add(k);
            }
        }
        return ok;
    }

    public static synchronized Result ask(String key, String model, String verbosity, String text) {
        List<String> gem = geminiKeys(key);
        List<String> alt = compatKeys(key);
        Result last = null;
        for (String k : usable(gem)) {
            Result r = askOne(k, model, verbosity, text);
            if (r.error == null) {
                good(k);
                return r;
            }
            last = r;
            if (r.quota) {
                block(k);
            }
            if (r.quota || r.badKey) {
                continue;
            }
            if (r.net) {
                return r;
            }
            break;
        }
        if (!alt.isEmpty()) {
            Result f = askCompat(alt, verbosity, text);
            if (f.error == null) {
                return f;
            }
            if (last == null) {
                last = f;
            }
        }
        if (last == null && !gem.isEmpty()) {
            last = askOne(gem.get(0), model, verbosity, text);   // sab "blocked" the: ek aakhri koshish
        }
        if (last == null) {
            last = new Result();
            last.error = "Gemini API key set nahi hai. Jarvis app ki Settings me key daaliye.";
        }
        if (last.quota && gem.size() + alt.size() < 2) {
            last.error += " Aur free keys jodne se limit ka masla kam hota hai.";
        }
        return last;
    }

    public static String generate(String key, String model, String system, String user, boolean fast) {
        return generateImpl(key, model, system, user, fast, fast);
    }

    /**
     * groqFirst: Groq/Cerebras key jodi ho to pehle wahi (roz ke chhote kaam: message likhna, agent, auto-reply),
     * taaki Gemini ki limit bachi rahe. Na chale ya limit ho to Gemini.
     */
    private static String generateImpl(String key, String model, String system, String user, boolean fast,
                                       boolean groqFirst) {
        List<String> gem = geminiKeys(key);
        List<String> alt = compatKeys(key);
        int kind = 0;
        String err = "";
        boolean triedAlt = false;
        if (groqFirst && !alt.isEmpty()) {
            triedAlt = true;
            String first = generateCompat(alt, system, user, false);
            if (first.length() > 0) {
                return first;
            }
            err = lastError;
        }
        for (String k : usable(gem)) {
            String out = generateOne(k, model, system, user, fast);
            if (out.length() > 0) {
                good(k);
                return out;
            }
            kind = failKind;
            err = lastError;
            if (kind == 1) {
                block(k);
            }
            if (kind == 1 || kind == 2) {
                continue;
            }
            if (kind == 4) {
                return "";
            }
            break;
        }
        if (!alt.isEmpty() && !triedAlt) {
            String out = generateCompat(alt, system, user, fast);
            if (out.length() > 0) {
                return out;
            }
            if (err.length() == 0) {
                err = lastError;
            }
        }
        if (err.length() == 0 && !gem.isEmpty() && usable(gem).isEmpty()) {
            return generateOne(gem.get(0), model, system, user, fast);
        }
        lastError = err;
        return "";
    }

    // ---- OpenAI-jaisi free services (Groq, Cerebras) ----
    private static String compatHttp(String method, String url, String key, String json, int[] status, int timeout)
            throws IOException {
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        try {
            conn.setRequestMethod(method);
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(timeout);
            conn.setRequestProperty("Authorization", "Bearer " + key.trim());
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setRequestProperty("User-Agent", "Jarvis/1.0");
            if (json != null) {
                conn.setDoOutput(true);
                OutputStream out = conn.getOutputStream();
                out.write(json.getBytes("UTF-8"));
                out.flush();
                out.close();
            }
            int code = conn.getResponseCode();
            status[0] = code;
            InputStream in = code < 400 ? conn.getInputStream() : conn.getErrorStream();
            if (in == null) {
                return "";
            }
            BufferedReader br = new BufferedReader(new InputStreamReader(in, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line).append('\n');
            }
            br.close();
            return sb.toString();
        } finally {
            conn.disconnect();
        }
    }

    /** Us service ke chat models, behtar pehle (70b), phir chhote (8b). Cache hota hai. */
    private static synchronized List<String> compatModels(String base, String key, boolean fast) {
        String ck = base + (fast ? "#f" : "#s");
        List<String> cached = COMPAT_MODELS.get(ck);
        if (cached != null) {
            return cached;
        }
        List<String> big = new ArrayList<String>();
        List<String> small = new ArrayList<String>();
        List<String> other = new ArrayList<String>();
        try {
            int[] st = new int[1];
            String body = compatHttp("GET", base + "/models", key, null, st, 10000);
            if (st[0] == 200) {
                JSONArray arr = new JSONObject(body).optJSONArray("data");
                for (int i = 0; arr != null && i < arr.length(); i++) {
                    String id = arr.getJSONObject(i).optString("id", "");
                    String l = id.toLowerCase(Locale.ENGLISH);
                    if (id.length() == 0 || l.contains("whisper") || l.contains("tts") || l.contains("guard")
                            || l.contains("embed") || l.contains("orpheus") || l.contains("safeguard")
                            || l.contains("vision") || l.contains("distil")) {
                        continue;
                    }
                    if (l.contains("70b") || l.contains("120b") || l.contains("maverick")) {
                        big.add(id);
                    } else if (l.contains("8b") || l.contains("20b") || l.contains("scout")) {
                        small.add(id);
                    } else {
                        other.add(id);
                    }
                }
            }
        } catch (Exception ignored) {
        }
        List<String> order = new ArrayList<String>();
        if (fast) {
            order.addAll(small);
            order.addAll(big);
        } else {
            order.addAll(big);
            order.addAll(small);
        }
        order.addAll(other);
        if (order.isEmpty()) {
            return order;                          // abhi nahi mila: cache mat karo
        }
        while (order.size() > 4) {
            order.remove(order.size() - 1);
        }
        COMPAT_MODELS.put(ck, order);
        return order;
    }

    private static String compatChat(String[] prov, String key, String system, List<String[]> hist, String user,
                                     boolean fast, int maxTokens) {
        List<String> models = compatModels(prov[1], key, fast);
        for (String m : models) {
            try {
                JSONArray msgs = new JSONArray();
                msgs.put(new JSONObject().put("role", "system").put("content", system));
                if (hist != null) {
                    for (String[] h : hist) {
                        msgs.put(new JSONObject().put("role", h[0].equals("model") ? "assistant" : "user")
                                .put("content", h[1]));
                    }
                }
                msgs.put(new JSONObject().put("role", "user").put("content", user));
                JSONObject root = new JSONObject();
                root.put("model", m);
                root.put("messages", msgs);
                root.put("temperature", 0.7);
                root.put("max_tokens", maxTokens);
                int[] st = new int[1];
                String body = compatHttp("POST", prov[1] + "/chat/completions", key, root.toString(), st,
                        fast ? 12000 : 30000);
                if (st[0] == 200) {
                    JSONArray ch = new JSONObject(body).optJSONArray("choices");
                    if (ch != null && ch.length() > 0) {
                        String c = ch.getJSONObject(0).getJSONObject("message").optString("content", "").trim();
                        c = c.replaceAll("(?s)<think>.*?</think>", "").trim();
                        if (c.length() > 0) {
                            lastModel = prov[2] + ":" + m;
                            return c;
                        }
                    }
                    continue;
                }
                lastError = prov[2] + " error " + st[0];
                if (st[0] == 401 || st[0] == 403) {
                    return null;                   // is service ki key galat
                }
            } catch (Exception e) {
                lastError = prov[2] + " se baat nahi ho payi";
            }
        }
        return "";
    }

    private static Result askCompat(List<String> keys, String verbosity, String text) {
        Result r = new Result();
        List<String[]> hist = new ArrayList<String[]>(HISTORY);
        String sys = systemPrompt(verbosity);
        for (String k : keys) {
            String[] prov = compatOf(k);
            if (prov == null || isBlocked(k)) {
                continue;
            }
            String out = compatChat(prov, k, sys, hist, text, false, 700);
            if (out != null && out.length() > 0) {
                good(k);
                r.reply = out;
                lastModel = prov[2];
                remember(text, r);
                return r;
            }
            if (out != null) {
                block(k);
            }
        }
        r.error = "Abhi saari free AI limits poori hain. Thodi der baad dobara poochiye, ya Settings me aur free key jodiye.";
        r.quota = true;
        return r;
    }

    private static String generateCompat(List<String> keys, String system, String user, boolean fast) {
        for (String k : keys) {
            String[] prov = compatOf(k);
            if (prov == null || isBlocked(k)) {
                continue;
            }
            int max = fast ? Math.min(700, Math.max(120, user.length() * 2)) : 400;
            String out = compatChat(prov, k, system, null, user, fast, max);
            if (out != null && out.length() > 0) {
                good(k);
                return out;
            }
            if (out != null) {
                block(k);
            }
        }
        return "";
    }

    private static String plainBody(String model, String system, String user, boolean thinking, boolean fast)
            throws Exception {
        JSONObject root = new JSONObject();
        root.put("systemInstruction", new JSONObject().put("parts",
                new JSONArray().put(new JSONObject().put("text", system))));
        root.put("contents", new JSONArray().put(new JSONObject().put("role", "user")
                .put("parts", new JSONArray().put(new JSONObject().put("text", user)))));
        JSONObject gen = new JSONObject();
        gen.put("temperature", 0.7);
        gen.put("maxOutputTokens", fast ? Math.min(700, Math.max(120, user.length() * 2)) : 300);
        if (thinking) {
            if (model.contains("gemini-3")) {
                gen.put("thinkingConfig", new JSONObject().put("thinkingLevel", "minimal"));
            } else if (model.contains("2.5")) {
                gen.put("thinkingConfig", new JSONObject().put("thinkingBudget", 0));
            }
        }
        root.put("generationConfig", gen);
        return root.toString();
    }

    public static synchronized void clearHistory() {
        HISTORY.clear();
    }

    private static void remember(String user, Result r) {
        HISTORY.add(new String[]{"user", user});
        String modelText = r.reply;
        if (r.function != null) {
            modelText = "(kaam kiya: " + r.function + ")";
        }
        if (modelText == null || modelText.length() == 0) {
            modelText = "ok";
        }
        HISTORY.add(new String[]{"model", modelText});
        while (HISTORY.size() > 12) {
            HISTORY.remove(0);
        }
    }

    // ----------------------------------------------------------------- body --
    private static String buildBody(String model, String verbosity, String text, boolean thinking)
            throws Exception {
        JSONObject root = new JSONObject();
        JSONObject sys = new JSONObject();
        sys.put("parts", new JSONArray().put(new JSONObject().put("text", systemPrompt(verbosity))));
        root.put("systemInstruction", sys);

        JSONArray contents = new JSONArray();
        for (String[] h : HISTORY) {
            contents.put(new JSONObject().put("role", h[0])
                    .put("parts", new JSONArray().put(new JSONObject().put("text", h[1]))));
        }
        contents.put(new JSONObject().put("role", "user")
                .put("parts", new JSONArray().put(new JSONObject().put("text", text))));
        root.put("contents", contents);
        root.put("tools", tools());

        JSONObject gen = new JSONObject();
        gen.put("temperature", 0.6);
        gen.put("maxOutputTokens", 1024);
        if (thinking) {
            boolean hard = text.length() > 90;
            if (model.contains("gemini-3")) {
                gen.put("thinkingConfig", new JSONObject().put("thinkingLevel", hard ? "low" : "minimal"));
            } else if (model.contains("2.5")) {
                gen.put("thinkingConfig", new JSONObject().put("thinkingBudget", hard ? 1024 : 0));
            }
        }
        root.put("generationConfig", gen);
        return root.toString();
    }

    private static String systemPrompt(String verbosity) {
        String rule = "Jawab chhota rakho: do se chaar vaakya.";
        if ("Concise".equals(verbosity)) {
            rule = "Jawab bahut chhota rakho: ek ya do vaakya.";
        } else if ("Detailed".equals(verbosity)) {
            rule = "Jawab detail me do par 150 shabd se zyada nahi.";
        }
        String now = new SimpleDateFormat("EEEE, dd MMMM yyyy, hh:mm a", Locale.ENGLISH).format(new Date());
        return "Tum JARVIS ho, user ke phone par chalne wala personal voice assistant. Tumhe "
                + CREATOR + " ne banaya hai. Koi poochhe ki tumhe kisne banaya to yahi batao. Khud ko "
                + "Gemini ya Google ka product mat batao. User se ek samajhdar dost ki tarah natural "
                + "Hinglish me baat karo (Hindi shabd Roman letters me). Jawab bolkar sunaya jayega, "
                + "isliye markdown, bullet, emoji, symbols aur link mat likho. " + rule + " "
                + "Agar user koi kaam kehta hai (alarm, timer, app kholna, call karna, torch, web ya YouTube search) "
                + "to uske liye function call karo, lamba jawab mat do. Alarm ke liye 24 ghante ka "
                + "samay nikaalo (subah 4:50 = hour 4 minute 50, shaam 5 baje = hour 17). Baaki sawal ya "
                + "baat-cheet ka seedha jawab do. Pata na ho to saaf bol do, andaza mat lagao. "
                + "Abhi ka samay: " + now + "." + memory;
    }

    private static JSONObject prop(String type, String desc) throws Exception {
        return new JSONObject().put("type", type).put("description", desc);
    }

    private static JSONObject fn(String name, String desc, JSONObject props, String... required)
            throws Exception {
        JSONObject params = new JSONObject();
        params.put("type", "OBJECT");
        params.put("properties", props);
        if (required.length > 0) {
            JSONArray req = new JSONArray();
            for (String s : required) {
                req.put(s);
            }
            params.put("required", req);
        }
        return new JSONObject().put("name", name).put("description", desc).put("parameters", params);
    }

    private static JSONArray tools() throws Exception {
        JSONArray fns = new JSONArray();
        fns.put(fn("set_alarm", "Phone me alarm lagao.",
                new JSONObject().put("hour", prop("INTEGER", "0 se 23 (24 ghante)"))
                        .put("minute", prop("INTEGER", "0 se 59")), "hour", "minute"));
        fns.put(fn("set_timer", "Countdown timer lagao.",
                new JSONObject().put("seconds", prop("INTEGER", "Timer kitne second ka")), "seconds"));
        fns.put(fn("open_app", "Phone ka koi app kholo.",
                new JSONObject().put("app_name", prop("STRING", "App ka naam, jaise WhatsApp, Camera")),
                "app_name"));
        fns.put(fn("call_contact", "Contacts me se kisi ko call lagao (naam se).",
                new JSONObject().put("name", prop("STRING", "Contact ka naam, jaise Priya Bhai, Mummy")),
                "name"));
        fns.put(fn("flashlight", "Torch (flashlight) on ya off karo.",
                new JSONObject().put("on", prop("BOOLEAN", "true = on, false = off")), "on"));
        fns.put(fn("web_search", "Google par kuch search karo.",
                new JSONObject().put("query", prop("STRING", "Search ka text")), "query"));
        fns.put(fn("youtube_search", "YouTube par kuch dhoondo ya chalao.",
                new JSONObject().put("query", prop("STRING", "YouTube search ka text")), "query"));
        return new JSONArray().put(new JSONObject().put("functionDeclarations", fns));
    }

    // ----------------------------------------------------------------- http --
    private static String post(String key, String model, String json, int[] status) throws IOException {
        return post(key, model, json, status, 45000);
    }

    private static String post(String key, String model, String json, int[] status, int readTimeout)
            throws IOException {
        HttpURLConnection conn = (HttpURLConnection) new URL(BASE + "/models/" + model
                + ":generateContent").openConnection();
        try {
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(readTimeout < 45000 ? 6000 : 15000);
            conn.setReadTimeout(readTimeout);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setRequestProperty("x-goog-api-key", key.trim());
            OutputStream out = conn.getOutputStream();
            out.write(json.getBytes("UTF-8"));
            out.flush();
            out.close();
            int code = conn.getResponseCode();
            status[0] = code;
            InputStream in = code < 400 ? conn.getInputStream() : conn.getErrorStream();
            if (in == null) {
                return "";
            }
            BufferedReader br = new BufferedReader(new InputStreamReader(in, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line).append('\n');
            }
            br.close();
            return sb.toString();
        } finally {
            conn.disconnect();
        }
    }

    private static void parse(String body, Result r) throws Exception {
        JSONObject data = new JSONObject(body);
        JSONObject feedback = data.optJSONObject("promptFeedback");
        if (feedback != null && feedback.has("blockReason")) {
            r.error = "Is sawal ka jawab main nahi de sakta. Kuch aur poochiye.";
            return;
        }
        JSONArray cands = data.optJSONArray("candidates");
        if (cands == null || cands.length() == 0) {
            r.error = "Gemini se jawab nahi mil paya. Dobara poochiye.";
            return;
        }
        JSONObject content = cands.getJSONObject(0).optJSONObject("content");
        JSONArray parts = content == null ? null : content.optJSONArray("parts");
        StringBuilder text = new StringBuilder();
        if (parts != null) {
            for (int i = 0; i < parts.length(); i++) {
                JSONObject p = parts.getJSONObject(i);
                JSONObject call = p.optJSONObject("functionCall");
                if (call != null && r.function == null) {
                    r.function = call.optString("name", "");
                    r.args = call.optJSONObject("args");
                    if (r.args == null) {
                        r.args = new JSONObject();
                    }
                } else if (p.has("text") && !p.optBoolean("thought", false)) {
                    text.append(p.optString("text", ""));
                }
            }
        }
        r.reply = clean(text.toString());
        if (r.function == null && r.reply.length() == 0) {
            r.error = "Gemini se jawab nahi mil paya. Dobara poochiye.";
        }
    }

    // ---------------------------------------------------------------- clean --
    public static String clean(String t) {
        if (t == null) {
            return "";
        }
        t = t.replace("**", "").replace("__", "").replace("`", "");
        t = t.replaceAll("(?m)^\\s{0,3}#{1,6}\\s*", "");
        t = t.replaceAll("(?m)^\\s*[\\*\\-\\u2022]\\s+", "");
        t = t.replaceAll("https?://\\S+", "");
        t = t.replaceAll("[\\uD83C-\\uDBFF\\uDC00-\\uDFFF\\u2600-\\u27BF\\uFE0F]", "");
        t = t.replaceAll("[ \\t]+", " ").replaceAll("\\n{3,}", "\n\n");
        return t.trim();
    }

    /** Bolne ke liye: ek line me, lamba ho to vaakya par kaat do. */
    public static String speechText(String t) {
        t = clean(t).replaceAll("\\s*\\n+\\s*", ". ").replaceAll("\\.\\s*\\.", ".");
        int limit = 650;
        if (t.length() <= limit) {
            return t;
        }
        String cut = t.substring(0, limit);
        int end = Math.max(cut.lastIndexOf(". "), Math.max(cut.lastIndexOf("? "), cut.lastIndexOf("! ")));
        if (end < limit * 0.4) {
            end = cut.lastIndexOf(' ');
        }
        return cut.substring(0, end + 1).trim() + " Baaki jawab screen par hai.";
    }

    /** "Tumhe kisne banaya" ka turant jawab (internet ya key ke bina). */
    public static String creatorReply(String text) {
        String t = text.toLowerCase(Locale.ENGLISH).trim();
        if (t.length() > 70) {
            return null;
        }
        boolean who = t.matches(".*\\b(tumhe|aapko|tujhe|tumko|jarvis ko)\\s+kisne\\b.*")
                || t.matches(".*\\bkisne\\s+(tumhe|aapko|tujhe|tumko|jarvis ko)\\b.*")
                || t.matches(".*\\bwho\\s+(made|created|built|developed|designed|programmed)\\s+(you|jarvis)\\b.*")
                || t.matches(".*\\b(your|tumhara|aapka|tera)\\s+(creator|developer|maker|owner)\\b.*");
        if (who) {
            return "Mujhe " + CREATOR + " ne banaya hai. Main JARVIS hoon, unka personal voice assistant.";
        }
        return null;
    }
}
