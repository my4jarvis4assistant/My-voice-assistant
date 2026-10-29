package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * "Jarvis" shabd ka intezaar (offline, bina key): Vosk speech engine + chhota English model.
 * Model pehli baar internet se download hota hai (~40 MB), phir hamesha offline chalta hai.
 * Vosk library reflection se chalayi jati hai, taaki library na ho to bhi app build ho jaye.
 */
public class JarvisVoskWake {
    public interface Listener {
        void onWake();

        void onStatus(String status);
    }

    private static final String MODEL_URL =
            "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip";
    static String modelUrl = MODEL_URL;      // sirf test ke liye badla ja sakta hai
    private static final int SAMPLE_RATE = 16000;
    private static final String GRAMMAR = "[\"jarvis\", \"hey jarvis\", \"hello jarvis\", \"[unk]\"]";

    private final Context ctx;
    private final Listener listener;
    private volatile boolean running = false;
    private volatile boolean stopRequested = false;
    private Thread thread = null;
    private Object model = null;

    public JarvisVoskWake(Context ctx, Listener listener) {
        this.ctx = ctx;
        this.listener = listener;
    }

    public synchronized void start() {
        if (running) {
            return;
        }
        running = true;
        stopRequested = false;
        thread = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    loop();
                } catch (Throwable t) {
                    if (stopRequested) {
                        return;
                    }
                    Throwable r = t;
                    while (r.getCause() != null && r.getCause() != r) {
                        r = r.getCause();
                    }
                    String msg = r.getClass().getSimpleName() + ": " + r.getMessage();
                    if (r instanceof ClassNotFoundException) {
                        msg = "Vosk library APK me nahi judi (buildozer.spec ki gradle_dependencies check kijiye)";
                    }
                    listener.onStatus("error: " + msg);
                } finally {
                    running = false;
                }
            }
        }, "jarvis-vosk-wake");
        thread.start();
    }

    /** Mic chhodne ke baad hi lautata hai (SpeechRecognizer ko mic chahiye). */
    public synchronized void stop() {
        stopRequested = true;
        running = false;
        Thread t = thread;
        thread = null;
        if (t != null && t != Thread.currentThread()) {
            try {
                t.join(2000);
            } catch (InterruptedException ignored) {
            }
        }
    }

    public synchronized void release() {
        stop();
        if (model != null) {
            try {
                model.getClass().getMethod("close").invoke(model);
            } catch (Throwable ignored) {
            }
            model = null;
        }
    }

    // ------------------------------------------------------------- model ----
    private File modelDir() {
        return new File(ctx.getFilesDir(), "vosk-model");
    }

    private boolean modelReady() {
        return new File(modelDir(), "ready.txt").exists();
    }

    private void downloadModel() throws Exception {
        File dir = modelDir();
        listener.onStatus("model download ho raha hai (40 MB, pehli baar)...");
        HttpURLConnection conn = (HttpURLConnection) new URL(modelUrl).openConnection();
        conn.setConnectTimeout(20000);
        conn.setReadTimeout(60000);
        conn.setInstanceFollowRedirects(true);
        int code = conn.getResponseCode();
        if (code != 200) {
            throw new IllegalStateException("model download fail (HTTP " + code + ")");
        }
        long total = conn.getContentLength();
        InputStream in = conn.getInputStream();
        ZipInputStream zin = new ZipInputStream(new java.io.BufferedInputStream(in));
        String canonicalRoot = dir.getCanonicalPath();
        byte[] buf = new byte[16384];
        long read = 0;
        int lastPct = -1;
        ZipEntry e;
        while ((e = zin.getNextEntry()) != null && running) {
            String name = e.getName();
            int slash = name.indexOf('/');
            if (slash < 0) {
                continue;
            }
            String rel = name.substring(slash + 1);      // upar ka folder hata do
            if (rel.length() == 0) {
                continue;
            }
            File out = new File(dir, rel);
            if (!out.getCanonicalPath().startsWith(canonicalRoot)) {
                continue;                                  // zip-slip se bachav
            }
            if (e.isDirectory()) {
                out.mkdirs();
                continue;
            }
            out.getParentFile().mkdirs();
            FileOutputStream fos = new FileOutputStream(out);
            int n;
            while ((n = zin.read(buf)) > 0) {
                fos.write(buf, 0, n);
                read += n;
                if (total > 0) {
                    int pct = (int) Math.min(99, read * 100 / (total * 11 / 10));  // zip se bada hota hai
                    if (pct != lastPct && pct % 5 == 0) {
                        lastPct = pct;
                        listener.onStatus("model download ho raha hai... " + pct + "%");
                    }
                }
            }
            fos.close();
        }
        zin.close();
        if (!running) {
            throw new IllegalStateException("download beech me ruka");
        }
        FileOutputStream mark = new FileOutputStream(new File(dir, "ready.txt"));
        mark.write("ok".getBytes("UTF-8"));
        mark.close();
    }

    private void ensureModel() throws Exception {
        if (model != null) {
            return;
        }
        if (!modelReady()) {
            downloadModel();
        }
        listener.onStatus("model load ho raha hai...");
        Class<?> modelClass = Class.forName("org.vosk.Model");
        model = modelClass.getConstructor(String.class).newInstance(modelDir().getAbsolutePath());
    }

    // -------------------------------------------------------------- loop ----
    private static String text(Object json, String key) {
        try {
            return new JSONObject(String.valueOf(json)).optString(key, "").toLowerCase();
        } catch (Exception e) {
            return "";
        }
    }

    private static boolean isWake(String t) {
        return t.contains("jarvis") || t.contains("jar vis");
    }

    private void loop() throws Throwable {
        ensureModel();
        if (!running) {
            return;
        }
        Class<?> modelClass = Class.forName("org.vosk.Model");
        Class<?> recClass = Class.forName("org.vosk.Recognizer");
        Object rec = recClass.getConstructor(modelClass, float.class, String.class)
                .newInstance(model, (float) SAMPLE_RATE, GRAMMAR);
        Method accept = recClass.getMethod("acceptWaveForm", short[].class, int.class);
        Method partial = recClass.getMethod("getPartialResult");
        Method result = recClass.getMethod("getResult");
        Method close = recClass.getMethod("close");

        int minBuf = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT);
        AudioRecord ar = new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, Math.max(minBuf, 8000) * 2);
        try {
            if (ar.getState() != AudioRecord.STATE_INITIALIZED) {
                throw new IllegalStateException("mic shuru nahi hua (permission ya mic busy)");
            }
            ar.startRecording();
            listener.onStatus("sun raha hai");
            short[] buf = new short[2000];
            boolean woke = false;
            while (running) {
                int n = ar.read(buf, 0, buf.length);
                if (n <= 0) {
                    Thread.sleep(20);
                    continue;
                }
                String t;
                try {
                    boolean fin = (Boolean) accept.invoke(rec, buf, n);
                    t = fin ? text(result.invoke(rec), "text") : text(partial.invoke(rec), "partial");
                } catch (InvocationTargetException ite) {
                    throw ite.getCause() != null ? ite.getCause() : ite;
                }
                if (isWake(t)) {
                    woke = true;
                    break;
                }
            }
            if (woke) {
                running = false;
                try {
                    ar.stop();
                } catch (Exception ignored) {
                }
                ar.release();
                ar = null;
                try {
                    close.invoke(rec);
                } catch (Throwable ignored) {
                }
                rec = null;
                listener.onWake();
            }
        } finally {
            if (ar != null) {
                try {
                    ar.stop();
                } catch (Exception ignored) {
                }
                ar.release();
            }
            if (rec != null) {
                try {
                    close.invoke(rec);
                } catch (Throwable ignored) {
                }
            }
        }
    }
}
