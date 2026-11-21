package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

/**
 * Gemini ki free awaaz (floating panel / bubble ke liye), aapki Gemini key se.
 * Tez: jawab chhote tukdon me banta hai. Pehla tukda (ek chhota vakya) banate hi bolna shuru, baaki tukde
 * bolte-bolte peeche ban jaate hain. Awaaz seedha AudioTrack se bajti hai (file/MediaPlayer ka intezaar nahi).
 * API: speak(), stop(), busy().
 */
public final class JarvisGeminiTts {
    public interface Callback {
        void onDone(boolean ok, String error);
    }

    private static final String[] MODELS = {"gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"};
    private static final String STYLE = "Say naturally with a clear Indian accent: ";
    private static final int MAX_CHARS = 900;

    private int gen = 0;
    private volatile boolean busy = false;
    private volatile AudioTrack track = null;

    public boolean busy() {
        return busy;
    }

    public synchronized void stop() {
        gen++;
        busy = false;
        AudioTrack t = track;
        track = null;
        if (t != null) {
            try {
                t.pause();
                t.flush();
            } catch (Throwable ignored) {
            }
            try {
                t.release();
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
            if (k.length() >= 8 && !k.startsWith("gsk_") && !k.startsWith("csk-") && !k.startsWith("sk-")
                    && !out.contains(k)) {
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

    /** Pehla tukda chhota (jaldi bolna shuru), baaki ~220 akshar ke. */
    static List<String> chunks(String text) {
        List<String> sentences = new ArrayList<String>();
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            cur.append(ch);
            boolean end = ch == '.' || ch == '?' || ch == '!' || ch == '।' || ch == '\n';
            if (end && (i + 1 >= text.length() || text.charAt(i + 1) == ' ' || ch == '\n')) {
                String s = cur.toString().trim();
                if (s.length() > 0) {
                    sentences.add(s);
                }
                cur.setLength(0);
            }
        }
        if (cur.toString().trim().length() > 0) {
            sentences.add(cur.toString().trim());
        }
        List<String> out = new ArrayList<String>();
        StringBuilder acc = new StringBuilder();
        for (String s : sentences) {
            if (out.isEmpty() && acc.length() == 0) {
                if (s.length() > 130) {                       // lamba pehla vakya: komma/space par kaat do
                    int cut = Math.max(s.lastIndexOf(", ", 110), s.lastIndexOf(' ', 100));
                    if (cut < 40) {
                        cut = Math.min(s.length(), 100);
                    }
                    out.add(s.substring(0, cut + 1).trim());
                    acc.append(s.substring(cut + 1).trim());
                } else {
                    out.add(s);
                }
                continue;
            }
            if (acc.length() > 0 && acc.length() + s.length() + 1 > 220) {
                out.add(acc.toString().trim());
                acc.setLength(0);
            }
            acc.append(acc.length() > 0 ? " " : "").append(s);
        }
        if (acc.toString().trim().length() > 0) {
            out.add(acc.toString().trim());
        }
        return out;
    }

    /** Ek tukde ki awaaz (PCM) mangao. Galti par Exception(message). */
    private byte[] fetch(List<String> ks, String voice, String t, int my) throws Exception {
        JSONObject body = new JSONObject();
        JSONArray contents = new JSONArray();
        JSONObject c0 = new JSONObject();
        c0.put("parts", new JSONArray().put(new JSONObject().put("text", STYLE + t)));
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
        for (String model : MODELS) {
            for (String key : ks) {
                for (int attempt = 0; attempt < 2; attempt++) {
                    if (my != gen) {
                        throw new Exception("roka gaya");
                    }
                    int http;
                    String resp;
                    HttpURLConnection c = (HttpURLConnection) new URL(
                            "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent")
                            .openConnection();
                    try {
                        c.setRequestMethod("POST");
                        c.setConnectTimeout(12000);
                        c.setReadTimeout(40000);
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
                                    byte[] pcm = Base64.decode(inl.getString("data"), Base64.DEFAULT);
                                    if (pcm.length > 400) {
                                        return pcm;
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
        throw new Exception(limited ? "Gemini awaaz ki free limit khatam (kal ya thodi der baad)" : last);
    }

    public void speak(final Context ctx, final String rawKeys, final String voice, final String text, final Callback cb) {
        final int my;
        synchronized (this) {
            stop();
            my = ++gen;
            busy = true;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                boolean ok = false;
                String err = null;
                AudioTrack at = null;
                try {
                    final List<String> ks = keys(rawKeys);
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
                    final List<String> parts = chunks(t);
                    final int n = parts.size();
                    final byte[][] pcm = new byte[n][];
                    final String[] errs = new String[n];
                    final boolean[] done = new boolean[n];
                    final Object lock = new Object();
                    final int[] next = {0};
                    int workers = Math.min(2, n);
                    for (int w = 0; w < workers; w++) {
                        new Thread(new Runnable() {
                            @Override
                            public void run() {
                                while (true) {
                                    int i;
                                    synchronized (lock) {
                                        if (next[0] >= n || my != gen) {
                                            return;
                                        }
                                        i = next[0]++;
                                    }
                                    byte[] r = null;
                                    String e = null;
                                    try {
                                        r = fetch(ks, voice, parts.get(i), my);
                                    } catch (Throwable ex) {
                                        e = ex.getMessage() == null ? "Gemini awaaz nahi bani" : ex.getMessage();
                                    }
                                    synchronized (lock) {
                                        pcm[i] = r;
                                        errs[i] = e;
                                        done[i] = true;
                                        lock.notifyAll();
                                    }
                                }
                            }
                        }).start();
                    }
                    final int rate = 24000;
                    int minBuf = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO,
                            AudioFormat.ENCODING_PCM_16BIT);
                    at = new AudioTrack(AudioManager.STREAM_MUSIC, rate, AudioFormat.CHANNEL_OUT_MONO,
                            AudioFormat.ENCODING_PCM_16BIT, Math.max(minBuf, rate / 2), AudioTrack.MODE_STREAM);
                    synchronized (JarvisGeminiTts.this) {
                        if (my != gen) {
                            at.release();
                            return;
                        }
                        track = at;
                    }
                    at.play();
                    long frames = 0;
                    for (int i = 0; i < n; i++) {
                        byte[] data;
                        synchronized (lock) {
                            while (!done[i] && my == gen) {
                                lock.wait(200);
                            }
                            if (my != gen) {
                                return;
                            }
                            data = pcm[i];
                            if (data == null) {
                                throw new Exception(errs[i] == null ? "Gemini awaaz nahi bani" : errs[i]);
                            }
                        }
                        int off = 0;
                        while (off < data.length && my == gen) {
                            int w = at.write(data, off, Math.min(4096, data.length - off));
                            if (w <= 0) {
                                break;
                            }
                            off += w;
                        }
                        frames += data.length / 2;
                    }
                    long limit = System.currentTimeMillis() + 120000;
                    while (my == gen && System.currentTimeMillis() < limit) {
                        int head;
                        try {
                            head = at.getPlaybackHeadPosition();
                        } catch (Throwable e) {
                            break;
                        }
                        if (head >= frames - 200) {
                            break;
                        }
                        Thread.sleep(60);
                    }
                    ok = true;
                } catch (Throwable e) {
                    err = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
                } finally {
                    boolean current = my == gen;
                    if (current) {
                        synchronized (JarvisGeminiTts.this) {
                            track = null;
                        }
                        busy = false;
                    }
                    if (at != null) {
                        try {
                            at.stop();
                        } catch (Throwable ignored) {
                        }
                        try {
                            at.release();
                        } catch (Throwable ignored) {
                        }
                    }
                    if (current && cb != null) {
                        final boolean fok = ok;
                        final String ferr = err;
                        new android.os.Handler(android.os.Looper.getMainLooper()).post(new Runnable() {
                            @Override
                            public void run() {
                                cb.onDone(fok, ferr);       // SpeechRecognizer/UI sirf main thread par chalte hain
                            }
                        });
                    }
                }
            }
        }).start();
    }
}
