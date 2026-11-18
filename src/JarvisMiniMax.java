package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.media.MediaPlayer;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * MiniMax awaaz (text-to-speech) floating panel / bubble ke liye. App wala Python (minimax.py) yahi karta hai.
 * speak(): peeche thread me mp3 banata hai, bajata hai, phir callback. stop(): turant chup.
 */
public final class JarvisMiniMax {
    public interface Callback {
        void onDone(boolean ok, String error);
    }

    private static final String API = "https://api.minimax.io/v1/t2a_v2";
    private static final String[] MODELS = {"speech-2.8-turbo", "speech-2.6-turbo", "speech-02-turbo"};
    private static final int MAX_CHARS = 900;

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

    static String message(int http, int status, String msg) {
        String low = msg == null ? "" : msg.toLowerCase();
        if (http == 401 || status == 1004 || status == 2049) {
            return "MiniMax key galat hai";
        }
        if (status == 1008 || status == 1039 || low.contains("balance") || low.contains("insufficient")) {
            return "MiniMax me balance/credits khatam hain";
        }
        if (status == 1002 || http == 429) {
            return "MiniMax: bahut requests, thodi der baad";
        }
        if (low.contains("voice") && (low.contains("not") || low.contains("exist") || low.contains("invalid"))) {
            return "MiniMax: Voice ID galat hai";
        }
        return "MiniMax error " + (status != 0 ? status : http) + " " + (msg == null ? "" : msg);
    }

    static byte[] unhex(String s) {
        int n = s.length() / 2;
        byte[] out = new byte[n];
        for (int i = 0; i < n; i++) {
            out[i] = (byte) ((Character.digit(s.charAt(2 * i), 16) << 4) | Character.digit(s.charAt(2 * i + 1), 16));
        }
        return out;
    }

    public void speak(final Context ctx, final String key, final String voiceId, final String text, final Callback cb) {
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
                File f = new File(dir, "jarvis_minimax_" + my + ".mp3");
                boolean ok = false;
                String err = null;
                try {
                    String t = trim(text);
                    if (key == null || key.trim().length() == 0) {
                        throw new Exception("MiniMax key nahi hai");
                    }
                    if (voiceId == null || voiceId.trim().length() == 0) {
                        throw new Exception("Voice ID nahi hai");
                    }
                    if (t.length() == 0) {
                        throw new Exception("khali text");
                    }
                    String last = "MiniMax se awaaz nahi aayi";
                    byte[] audio = null;
                    for (String model : MODELS) {
                        if (my != gen) {
                            return;
                        }
                        JSONObject body = new JSONObject();
                        body.put("model", model);
                        body.put("text", t);
                        body.put("stream", false);
                        body.put("language_boost", "auto");
                        JSONObject vs = new JSONObject();
                        vs.put("voice_id", voiceId.trim());
                        vs.put("speed", 1.0);
                        vs.put("vol", 1.0);
                        vs.put("pitch", 0);
                        body.put("voice_setting", vs);
                        JSONObject as = new JSONObject();
                        as.put("sample_rate", 32000);
                        as.put("bitrate", 128000);
                        as.put("format", "mp3");
                        as.put("channel", 1);
                        body.put("audio_setting", as);
                        int http;
                        String resp;
                        HttpURLConnection c = (HttpURLConnection) new URL(API).openConnection();
                        try {
                            c.setRequestMethod("POST");
                            c.setConnectTimeout(15000);
                            c.setReadTimeout(45000);
                            c.setRequestProperty("Authorization", "Bearer " + key.trim());
                            c.setRequestProperty("Content-Type", "application/json");
                            c.setDoOutput(true);
                            OutputStream os = c.getOutputStream();
                            os.write(body.toString().getBytes("UTF-8"));
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
                        JSONObject j;
                        try {
                            j = new JSONObject(resp);
                        } catch (Exception e) {
                            j = new JSONObject();
                        }
                        JSONObject br = j.optJSONObject("base_resp");
                        int status = br == null ? 0 : br.optInt("status_code", 0);
                        String smsg = br == null ? "" : br.optString("status_msg", "");
                        JSONObject d = j.optJSONObject("data");
                        String hex = d == null ? "" : d.optString("audio", "");
                        if (http < 400 && status == 0 && hex.length() > 400) {
                            audio = unhex(hex);
                            break;
                        }
                        last = message(http, status, smsg);
                        if (smsg.toLowerCase().contains("model") || status == 2013) {
                            continue;
                        }
                        break;
                    }
                    if (audio == null) {
                        throw new Exception(last);
                    }
                    FileOutputStream fo = new FileOutputStream(f);
                    fo.write(audio);
                    fo.close();
                    if (my != gen) {
                        return;
                    }
                    MediaPlayer mp = new MediaPlayer();
                    synchronized (JarvisMiniMax.this) {
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
