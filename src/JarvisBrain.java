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
    }

    public static final String CREATOR = "Shakshm Jha";
    private static final String BASE = "https://generativelanguage.googleapis.com/v1beta";
    private static final String[] FALLBACK = {"gemini-2.5-flash", "gemini-3-flash-preview",
            "gemini-2.0-flash"};
    private static final List<String[]> HISTORY = new ArrayList<String[]>();
    public static String lastModel = "";

    // ------------------------------------------------------------------ ask --
    public static synchronized Result ask(String key, String model, String verbosity, String text) {
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
                    return r;
                }
                if (status[0] == 429 || low.contains("quota") || low.contains("resource_exhausted")) {
                    lastError = "Abhi Gemini ki free limit poori ho gayi hai. Thodi der baad dobara poochiye.";
                    continue;
                }
                if (status[0] == 404 || (status[0] == 400 && low.contains("model"))) {
                    continue;
                }
                if (status[0] == 403) {
                    r.error = "Gemini ne is key ko allow nahi kiya. Key ya uski permission check kijiye.";
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
        } catch (IOException e) {
            r.error = "Internet nahi chal raha lagta hai. Connection check karke dobara boliye.";
        } catch (Exception e) {
            r.error = "AI se baat karte waqt kuch gadbad ho gayi. Dobara try kijiye.";
        }
        return r;
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
                + "Abhi ka samay: " + now + ".";
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
        HttpURLConnection conn = (HttpURLConnection) new URL(BASE + "/models/" + model
                + ":generateContent").openConnection();
        try {
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(45000);
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
