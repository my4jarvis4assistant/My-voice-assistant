package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.media.MediaPlayer;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

/**
 * Gemini ki free awaaz (floating panel / bubble ke liye). Aapki Gemini key se hi chalti hai.
 * App wala Python (gemini_voice.py) yahi karta hai. API MiniMax wale jaisi: speak(), stop(), busy().
 */
public final class JarvisGeminiTts {
    public interface Callback {
        void onDone(boolean ok, String error);
    }

    private static final String[] MODELS = {"gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"};
    private static final String STYLE = "Say in a calm, natural, clear Indian accent: ";
    private static final int MAX_CHARS = 700;

    private int gen = 0;
    private volatile boolean busy = false;
    private volatile MediaPlayer player = null;

    public boolean busy() {
        return busy;
    }

    public synchronized void stop() {
        gen++;
        busy = false;
        MediaPlayer p = player;
        player = null;
        if (p != null) {
            try {
                p.stop();
            } catch (Throwable ignored) {
            }
            try {
                p.release();
            } catch (Throwable ignored) {
            }
        }
    }

    static List<String> keys(String raw) {
        List<String> out = new ArrayList<String>();
        if (raw == null) {
            return out;
        }
        for (String k : raw.split("[\\s,;]+")) {
            k = k.trim();
            if (k.length() >= 8 && !k.startsWith("gsk_") && !k.startsWith("csk-") && !k.startsWith("sk-") && !out.contains(k)) {
                out.add(k);
            }
        }
        return out;
    }

    static String trim(String text) {
        String t = text == null ? "" : text.replaceAll("\\s+", " ").trim();
        if (t.length() <= MAX_CHARS) {
            return t;
        }
        String cut = t.substring(0, MAX_CHARS);
        String[] seps = {". ", "? ", "! ", "। ", ", "};
        for (String s : seps) {
            int i = cut.lastIndexOf(s);
            if (i > MAX_CHARS * 0.5) {
                return cut.substring(0, i + 1);
            }
        }
        return cut;
    }

    static byte[] wav(byte[] pcm, int rate) {
        int n = pcm.length;
        byte[] h = new byte[44];
        put(h, 0, "RIFF");
        le32(h, 4, 36 + n);
        put(h, 8, "WAVE");
        put(h, 12, "fmt ");
        le32(h, 16, 16);
        h[20] = 1;
        h[22] = 1;
        le32(h, 24, rate);
        le32(h, 28, rate * 2);
        h[32] = 2;
        h[34] = 16;
        put(h, 36, "data");
        le32(h, 40, n);
        byte[] out = new byte[44 + n];
        System.arraycopy(h, 0, out, 0, 44);
        System.arraycopy(pcm, 0, out, 44, n);
        return out;
    }

    private static void put(byte[] b, int at, String s) {
        for (int i = 0; i < s.length(); i++) {
            b[at + i] = (byte) s.charAt(i);
        }
    }

    private static void le32(byte[] b, int at, int v) {
        b[at] = (byte) v;
        b[at + 1] = (byte) (v >> 8);
        b[at + 2] = (byte) (v >> 16);
        b[at + 3] = (byte) (v >> 24);
    }

    public void speak(final Context ctx, final String rawKeys, final String voice, final String text, final Callback cb) {
        final int my;
        synchronized (this) {
            stop();
            my = ++gen;
            busy = true;
        }
        final File dir = ctx.getCacheDir();
        new Thread(new Runnable() {
            @Override
            public void run() {
                File f = new File(dir, "jarvis_gemini_" + my + ".wav");
                boolean ok = false;
                String err = null;
                try {
                    List<String> ks = keys(rawKeys);
                    if (ks.isEmpty()) {
                        throw new Exception("Gemini key nahi hai (AI card me Gemini key daaliye)");
                    }
                    if (voice == null || voice.trim().length() == 0) {
                        throw new Exception("Voice nahi chuni");
                    }
                    String t = trim(text);
                    if (t.length() == 0) {
                        throw new Exception("khali text");
                    }
                    JSONObject body = new JSONObject();
                    JSONArray contents = new JSONArray();
                    JSONObject c0 = new JSONObject();
                    JSONArray parts = new JSONArray();
                    parts.put(new JSONObject().put("text", STYLE + t));
                    c0.put("parts", parts);
                    contents.put(c0);
                    body.put("contents", contents);
                    JSONObject gc = new JSONObject();
                    gc.put("responseModalities", new JSONArray().put("AUDIO"));
                    gc.put("speechConfig", new JSONObject().put("voiceConfig", new JSONObject().put("prebuiltVoiceConfig",
                            new JSONObject().put("voiceName", voice.trim()))));
                    body.put("generationConfig", gc);
                    byte[] payload = body.toString().getBytes("UTF-8");

                    String last = "Gemini se awaaz nahi aayi";
                    boolean limited = false;
                    byte[] wavData = null;
                    outer:
                    for (String model : MODELS) {
                        for (String key : ks) {
                            for (int attempt = 0; attempt < 2; attempt++) {
                                if (my != gen) {
                                    return;
                                }
                                int http;
                                String resp;
                                HttpURLConnection c = (HttpURLConnection) new URL(
                                        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent")
                                        .openConnection();
                                try {
                                    c.setRequestMethod("POST");
                                    c.setConnectTimeout(15000);
                                    c.setReadTimeout(60000);
                                    c.setRequestProperty("x-goog-api-key", key);
                                    c.setRequestProperty("Content-Type", "application/json");
                                    c.setDoOutput(true);
                                    OutputStream os = c.getOutputStream();
                                    os.write(payload);
                                    os.flush();
                                    os.close();
                                    http = c.getResponseCode();
                                    InputStream is = http >= 400 ? c.getErrorStream() : c.getInputStream();
                                    ByteArrayOutputStream bo = new ByteArrayOutputStream();
                                    if (is != null) {
                                        byte[] buf = new byte[16384];
                                        int n;
                                        while ((n = is.read(buf)) > 0) {
                                            bo.write(buf, 0, n);
                                        }
                                        is.close();
                                    }
                                    resp = bo.toString("UTF-8");
                                } finally {
                                    c.disconnect();
                                }
                                if (http < 400) {
                                    try {
                                        JSONArray ps = new JSONObject(resp).getJSONArray("candidates").getJSONObject(0)
                                                .getJSONObject("content").getJSONArray("parts");
                                        for (int i = 0; i < ps.length(); i++) {
                                            JSONObject inl = ps.getJSONObject(i).optJSONObject("inlineData");
                                            if (inl != null && inl.optString("data").length() > 0) {
                                                int rate = 24000;
                                                String mime = inl.optString("mimeType", "");
                                                int ri = mime.indexOf("rate=");
                                                if (ri >= 0) {
                                                    try {
                                                        rate = Integer.parseInt(mime.substring(ri + 5).replaceAll("[^0-9].*$", ""));
                                                    } catch (Exception ignored) {
                                                    }
                                                }
                                                byte[] pcm = Base64.decode(inl.getString("data"), Base64.DEFAULT);
                                                if (pcm.length > 400) {
                                                    wavData = wav(pcm, rate);
                                                    break outer;
                                                }
                                            }
                                        }
                                    } catch (Exception ignored) {
                                    }
                                    last = "Gemini ne awaaz khali bheji";
                                    continue;
                                }
                                if (http == 429) {
                                    limited = true;
                                    last = "Gemini awaaz ki free limit khatam (kal ya thodi der baad)";
                                } else if ((http == 400 || http == 403) && resp.toLowerCase().contains("api key")) {
                                    last = "Gemini key galat hai";
                                } else if (http == 404) {
                                    last = "Gemini awaaz model nahi mila";
                                } else {
                                    last = "Gemini awaaz error " + http;
                                }
                                break;
                            }
                        }
                    }
                    if (wavData == null) {
                        throw new Exception(limited ? "Gemini awaaz ki free limit khatam (kal ya thodi der baad)" : last);
                    }
                    FileOutputStream fo = new FileOutputStream(f);
                    fo.write(wavData);
                    fo.close();
                    if (my != gen) {
                        return;
                    }
                    MediaPlayer mp = new MediaPlayer();
                    synchronized (JarvisGeminiTts.this) {
                        if (my != gen) {
                            mp.release();
                            return;
                        }
                        player = mp;
                    }
                    mp.setDataSource(f.getAbsolutePath());
                    mp.prepare();
                    mp.start();
                    long started = System.currentTimeMillis();
                    while (my == gen) {
                        Thread.sleep(100);
                        long el = System.currentTimeMillis() - started;
                        boolean playing;
                        try {
                            playing = mp.isPlaying();
                        } catch (Throwable e) {
                            break;
                        }
                        if ((!playing && el > 400) || el > 120000) {
                            break;
                        }
                    }
                    ok = true;
                } catch (Throwable e) {
                    err = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
                } finally {
                    boolean current = my == gen;
                    try {
                        f.delete();
                    } catch (Throwable ignored) {
                    }
                    MediaPlayer p = player;
                    if (current) {
                        player = null;
                        busy = false;
                        if (p != null) {
                            try {
                                p.stop();
                            } catch (Throwable ignored) {
                            }
                            try {
                                p.release();
                            } catch (Throwable ignored) {
                            }
                        }
                        if (cb != null) {
                            cb.onDone(ok, err);
                        }
                    }
                }
            }
        }).start();
    }
}
