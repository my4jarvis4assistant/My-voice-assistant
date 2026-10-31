package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.media.MediaPlayer;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/** ElevenLabs awaaz (bubble/panel ke liye). Galti par callback me ok=false, tab service phone ki awaaz se bolti hai. */
public class JarvisEleven {
    public interface Callback {
        /** Main thread par bulaya jata hai. ok=true: bolna poora hua. */
        void onDone(boolean ok, String error);
    }

    private static final String API = "https://api.elevenlabs.io/v1/text-to-speech/";
    private static final String MODEL = "eleven_flash_v2_5";
    private static final int MAX_CHARS = 700;

    private final Handler main = new Handler(Looper.getMainLooper());
    private MediaPlayer player = null;
    private volatile int token = 0;
    private volatile boolean busy = false;

    public boolean isBusy() {
        return busy;
    }

    public void stop() {
        token++;
        busy = false;
        releasePlayer();
    }

    private void releasePlayer() {
        MediaPlayer p = player;
        player = null;
        if (p != null) {
            try {
                p.stop();
            } catch (Exception ignored) {
            }
            try {
                p.release();
            } catch (Exception ignored) {
            }
        }
    }

    static String trim(String text) {
        String t = text.replaceAll("\\s+", " ").trim();
        if (t.length() <= MAX_CHARS) {
            return t;
        }
        String cut = t.substring(0, MAX_CHARS);
        int best = Math.max(Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("? ")),
                Math.max(cut.lastIndexOf("! "), cut.lastIndexOf(", ")));
        return best > MAX_CHARS / 2 ? cut.substring(0, best + 1) : cut;
    }

    static String errorFor(int code, String body) {
        String low = body == null ? "" : body.toLowerCase();
        if (code == 401) {
            return "ElevenLabs key galat hai";
        }
        if (code == 402 || code == 403 || low.contains("paid") || low.contains("payment")) {
            return "ElevenLabs: is voice/plan ke liye paid plan chahiye";
        }
        if (code == 404 || low.contains("voice_not_found")) {
            return "ElevenLabs: Voice ID galat hai";
        }
        if (code == 429 || low.contains("quota")) {
            return "ElevenLabs ka quota khatam hai";
        }
        return "ElevenLabs error " + code;
    }

    public void speak(final Context ctx, final String key, final String voiceId, final String text,
                      final Callback cb) {
        final int my = ++token;
        busy = true;
        releasePlayer();
        new Thread(new Runnable() {
            @Override
            public void run() {
                File out = null;
                String err = null;
                try {
                    String t = trim(text);
                    if (t.length() == 0) {
                        throw new Exception("khali text");
                    }
                    out = new File(ctx.getCacheDir(), "jarvis_eleven_" + my + ".mp3");
                    JSONObject body = new JSONObject();
                    body.put("text", t);
                    body.put("model_id", MODEL);
                    HttpURLConnection conn = (HttpURLConnection) new URL(API + voiceId.trim()
                            + "?output_format=mp3_44100_64").openConnection();
                    try {
                        conn.setRequestMethod("POST");
                        conn.setConnectTimeout(15000);
                        conn.setReadTimeout(40000);
                        conn.setDoOutput(true);
                        conn.setRequestProperty("xi-api-key", key.trim());
                        conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                        conn.setRequestProperty("Accept", "audio/mpeg");
                        OutputStream os = conn.getOutputStream();
                        os.write(body.toString().getBytes("UTF-8"));
                        os.flush();
                        os.close();
                        int code = conn.getResponseCode();
                        if (code >= 400) {
                            String b = "";
                            InputStream es = conn.getErrorStream();
                            if (es != null) {
                                b = readAll(es);
                            }
                            err = errorFor(code, b);
                        } else {
                            InputStream is = conn.getInputStream();
                            FileOutputStream fos = new FileOutputStream(out);
                            byte[] buf = new byte[8192];
                            int n;
                            while ((n = is.read(buf)) > 0) {
                                fos.write(buf, 0, n);
                            }
                            fos.close();
                            is.close();
                            if (out.length() < 200) {
                                err = "ElevenLabs se awaaz nahi aayi";
                            }
                        }
                    } finally {
                        conn.disconnect();
                    }
                } catch (Exception e) {
                    err = "ElevenLabs tak internet nahi pahunch paya";
                }
                final String fe = err;
                final File ff = out;
                main.post(new Runnable() {
                    @Override
                    public void run() {
                        if (my != token) {
                            if (ff != null) {
                                ff.delete();
                            }
                            return;
                        }
                        if (fe != null) {
                            busy = false;
                            if (ff != null) {
                                ff.delete();
                            }
                            cb.onDone(false, fe);
                            return;
                        }
                        play(ff, my, cb);
                    }
                });
            }
        }).start();
    }

    private static String readAll(InputStream is) throws Exception {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] buf = new byte[2048];
        int n;
        while ((n = is.read(buf)) > 0) {
            bo.write(buf, 0, n);
        }
        is.close();
        return bo.toString("UTF-8");
    }

    private void play(final File f, final int my, final Callback cb) {
        try {
            final MediaPlayer mp = new MediaPlayer();
            player = mp;
            mp.setDataSource(f.getAbsolutePath());
            mp.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
                @Override
                public void onCompletion(MediaPlayer m) {
                    f.delete();
                    if (my == token) {
                        busy = false;
                        releasePlayer();
                        cb.onDone(true, null);
                    }
                }
            });
            mp.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                @Override
                public boolean onError(MediaPlayer m, int what, int extra) {
                    f.delete();
                    if (my == token) {
                        busy = false;
                        releasePlayer();
                        cb.onDone(false, "Awaaz bajane me galti");
                    }
                    return true;
                }
            });
            mp.prepare();
            mp.start();
        } catch (Exception e) {
            f.delete();
            busy = false;
            cb.onDone(false, "Awaaz bajane me galti");
        }
    }
}
