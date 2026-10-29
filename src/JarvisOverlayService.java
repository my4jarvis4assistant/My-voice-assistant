package org.myassistant.myvoiceassistant;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;

/**
 * Jarvis ka floating panel: home screen ke upar hi sunta hai, jawab deta hai aur kaam karta hai.
 * Ye Python/Kivy app par depend nahi karta (app band ho tab bhi chalta hai).
 */
public class JarvisOverlayService extends Service {
    public static final String ACTION_TALK = "org.myassistant.TALK";
    public static final String ACTION_WAKE_ON = "org.myassistant.WAKE_ON";
    public static final String ACTION_WAKE_OFF = "org.myassistant.WAKE_OFF";
    private static final String CHANNEL_ID = "jarvis_overlay";
    private static final int NOTIF_ID = 4711;

    private static final int MODE_IDLE = 0;
    private static final int MODE_LISTEN = 1;
    private static final int MODE_THINK = 2;

    private final Handler main = new Handler(Looper.getMainLooper());
    private WindowManager wm;
    private LinearLayout panel;
    private TextView statusView;
    private TextView heardView;
    private View orbView;
    private GradientDrawable orbShape;
    private SpeechRecognizer recognizer;
    private TextToSpeech tts;
    private boolean ttsReady = false;
    private String pendingSpeech = null;
    private boolean speaking = false;
    private boolean beepMuted = false;
    private int mode = MODE_IDLE;
    private float level = 0f;
    private float targetLevel = 0f;
    private double clock = 0;
    private boolean alive = true;
    private long gen = 0;          // purane jawab ko radd karne ke liye

    // --- "Jarvis" bolne par jaagna (Picovoice Porcupine, reflection se: build kabhi nahi tootta) ---
    private Object porcupine = null;
    private boolean wakeEnabled = false;
    private boolean wakeRunning = false;
    private JarvisVoskWake vosk = null;
    private boolean useVosk = false;

    // ----------------------------------------------------------- lifecycle --
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        try {
            if (action == null) {
                // system ne service dobara chalayi: wake word chalu tha to wahi karo
                action = prefs().getBoolean("wake_enabled", false) ? ACTION_WAKE_ON : ACTION_WAKE_OFF;
            }
            startAsForeground(ACTION_TALK.equals(action) || panel != null);
            if (ACTION_WAKE_OFF.equals(action)) {
                wakeEnabled = false;
                stopWake(true);
                setWakeStatus("band");
                if (panel == null) {
                    stopForeground(true);
                    stopSelf();
                }
                return START_NOT_STICKY;
            }
            if (ACTION_WAKE_ON.equals(action)) {
                wakeEnabled = true;
                if (panel == null) {
                    startWake();
                }
                return START_STICKY;
            }
            talk();
        } catch (Exception e) {
            toastError("Jarvis shuru nahi ho paya: " + e);
            setWakeStatus("error: " + e);
            shutdown();
        }
        return wakeEnabled ? START_STICKY : START_NOT_STICKY;
    }

    /** Panel dikhao aur sunna shuru karo (button ya wake word se). */
    private void talk() {
        if (panel == null) {
            alive = true;
            wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
            stopWake(false);              // mic ek hi cheez use kar sakti hai
            showPanel();
            initTts();
            main.post(ticker);
        }
        startListening();
    }

    @Override
    public void onDestroy() {
        stopWake(true);
        cleanup();
        super.onDestroy();
    }

    // ------------------------------------------------------------ wake word --
    private void setWakeStatus(String s) {
        try {
            prefs().edit().putString("wake_status", s).apply();
        } catch (Exception ignored) {
        }
    }

    private static Throwable root(Throwable t) {
        while (t.getCause() != null && t.getCause() != t) {
            t = t.getCause();
        }
        return t;
    }

    private void startWake() {
        if (!wakeEnabled) {
            return;
        }
        if (wakeRunning) {
            return;
        }
        String key = prefs().getString("picovoice_key", "").trim();
        if (key.length() == 0 || useVosk) {
            startVosk();           // key nahi: offline Vosk
            return;
        }
        try {
            if (porcupine == null) {
                Class<?> bClass = Class.forName("ai.picovoice.porcupine.PorcupineManager$Builder");
                Object builder = bClass.getConstructor().newInstance();
                bClass.getMethod("setAccessKey", String.class).invoke(builder, key);
                Class<?> kwClass = Class.forName("ai.picovoice.porcupine.Porcupine$BuiltInKeyword");
                Object jarvis = null;
                for (Object k : kwClass.getEnumConstants()) {
                    if ("JARVIS".equals(String.valueOf(k))) {
                        jarvis = k;
                    }
                }
                if (jarvis == null) {
                    throw new IllegalStateException("JARVIS keyword is version me nahi hai");
                }
                bClass.getMethod("setKeyword", kwClass).invoke(builder, jarvis);
                try {
                    bClass.getMethod("setSensitivity", float.class).invoke(builder, 0.7f);
                } catch (NoSuchMethodException ignored) {
                }
                Class<?> cbClass = Class.forName("ai.picovoice.porcupine.PorcupineManagerCallback");
                Object cb = java.lang.reflect.Proxy.newProxyInstance(cbClass.getClassLoader(),
                        new Class<?>[]{cbClass}, new java.lang.reflect.InvocationHandler() {
                            @Override
                            public Object invoke(Object proxy, java.lang.reflect.Method method,
                                                 Object[] args) {
                                String n = method.getName();
                                if ("invoke".equals(n)) {
                                    main.post(new Runnable() {
                                        @Override
                                        public void run() {
                                            onWakeWord();
                                        }
                                    });
                                    return null;
                                }
                                if ("hashCode".equals(n)) {
                                    return Integer.valueOf(System.identityHashCode(proxy));
                                }
                                if ("equals".equals(n)) {
                                    return Boolean.valueOf(args != null && args.length > 0 && proxy == args[0]);
                                }
                                if ("toString".equals(n)) {
                                    return "JarvisWakeCallback";
                                }
                                return null;
                            }
                        });
                porcupine = bClass.getMethod("build", Context.class, cbClass)
                        .invoke(builder, getApplicationContext(), cb);
            }
            porcupine.getClass().getMethod("start").invoke(porcupine);
            wakeRunning = true;
            setWakeStatus("sun raha hai");
        } catch (Throwable t) {
            wakeRunning = false;
            Throwable r = root(t);
            String msg = r.getClass().getSimpleName() + ": " + r.getMessage();
            setWakeStatus("error: " + msg);
            toastError("Wake word shuru nahi hua: " + msg);
            if (r instanceof ClassNotFoundException || r instanceof NoClassDefFoundError) {
                useVosk = true;
                startVosk();
            }
        }
    }

    private void startVosk() {
        if (vosk == null) {
            vosk = new JarvisVoskWake(this, new JarvisVoskWake.Listener() {
                @Override
                public void onWake() {
                    main.post(new Runnable() {
                        @Override
                        public void run() {
                            wakeRunning = false;
                            onWakeWord();
                        }
                    });
                }

                @Override
                public void onStatus(String status) {
                    setWakeStatus(status);
                }
            });
        }
        vosk.start();
        wakeRunning = true;
    }

    /** delete=true: poori tarah band; false: sirf mic chhodne ke liye roko. */
    private void stopWake(boolean delete) {
        if (vosk != null) {
            if (delete) {
                vosk.release();
                vosk = null;
            } else {
                vosk.stop();
            }
        }
        if (porcupine == null) {
            wakeRunning = false;
            return;
        }
        try {
            if (wakeRunning) {
                porcupine.getClass().getMethod("stop").invoke(porcupine);
            }
        } catch (Throwable ignored) {
        }
        wakeRunning = false;
        if (delete) {
            try {
                porcupine.getClass().getMethod("delete").invoke(porcupine);
            } catch (Throwable ignored) {
            }
            porcupine = null;
        }
    }

    private void onWakeWord() {
        if (panel != null) {
            return;
        }
        try {
            startAsForeground(true);
            talk();
        } catch (Exception e) {
            toastError("Jarvis panel nahi khul paya: " + e);
            shutdown();
        }
    }

    private void startAsForeground(boolean talking) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder nb;
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL_ID, "Jarvis",
                    NotificationManager.IMPORTANCE_LOW);
            nm.createNotificationChannel(ch);
            nb = new Notification.Builder(this, CHANNEL_ID);
        } else {
            nb = new Notification.Builder(this);
        }
        nb.setContentTitle("JARVIS")
                .setContentText(talking ? "Jarvis sun raha hai" : "'Jarvis' bolne ka intezaar hai")
                .setSmallIcon(getApplicationInfo().icon).setOngoing(true);
        Notification n = nb.build();
        if (Build.VERSION.SDK_INT >= 30) {
            startForeground(NOTIF_ID, n, 128);   // 128 = FOREGROUND_SERVICE_TYPE_MICROPHONE
        } else {
            startForeground(NOTIF_ID, n);
        }
    }

    private void shutdown() {
        cleanup();
        if (wakeEnabled) {
            try {
                startAsForeground(false);
            } catch (Exception ignored) {
            }
            // mic ko thoda waqt do (SpeechRecognizer chhodta hai), phir wake word dobara chalu
            main.postDelayed(new Runnable() {
                @Override
                public void run() {
                    if (panel == null) {
                        startWake();
                    }
                }
            }, 900);
            return;
        }
        try {
            stopForeground(true);
        } catch (Exception ignored) {
        }
        stopSelf();
    }

    private void cleanup() {
        alive = false;
        gen++;
        main.removeCallbacksAndMessages(null);
        muteBeep(false);
        try {
            if (recognizer != null) {
                recognizer.cancel();
                recognizer.destroy();
            }
        } catch (Exception ignored) {
        }
        recognizer = null;
        try {
            if (tts != null) {
                tts.stop();
                tts.shutdown();
            }
        } catch (Exception ignored) {
        }
        tts = null;
        ttsReady = false;
        try {
            if (panel != null && wm != null) {
                wm.removeView(panel);
            }
        } catch (Exception ignored) {
        }
        panel = null;
    }

    private void toastError(String msg) {
        try {
            android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_LONG).show();
        } catch (Exception ignored) {
        }
    }

    // ------------------------------------------------------------------ UI --
    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void showPanel() {
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.parseColor("#F2101A1D"));
        bg.setCornerRadius(dp(28));
        bg.setStroke(dp(1), Color.parseColor("#33FFFFFF"));

        panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setBackground(bg);
        panel.setPadding(dp(18), dp(14), dp(18), dp(16));

        // header: JARVIS + green dot + close
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        TextView title = new TextView(this);
        title.setText("JARVIS");
        title.setTextColor(Color.parseColor("#E6F2F5"));
        title.setTextSize(18);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        header.addView(title);
        View dot = new View(this);
        GradientDrawable dotShape = new GradientDrawable();
        dotShape.setShape(GradientDrawable.OVAL);
        dotShape.setColor(Color.parseColor("#1FF285"));
        dot.setBackground(dotShape);
        LinearLayout.LayoutParams dlp = new LinearLayout.LayoutParams(dp(8), dp(8));
        dlp.leftMargin = dp(8);
        header.addView(dot, dlp);
        View spacer = new View(this);
        header.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1f));
        TextView close = new TextView(this);
        close.setText("✕");
        close.setTextColor(Color.parseColor("#8CA8AD"));
        close.setTextSize(20);
        close.setPadding(dp(12), dp(4), dp(4), dp(4));
        close.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                shutdown();
            }
        });
        header.addView(close);
        panel.addView(header);

        // orb
        orbView = new View(this);
        orbShape = new GradientDrawable();
        orbShape.setShape(GradientDrawable.OVAL);
        orbShape.setGradientType(GradientDrawable.RADIAL_GRADIENT);
        orbShape.setGradientRadius(dp(44));
        orbShape.setGradientCenter(0.5f, 0.38f);
        orbShape.setColors(new int[]{Color.parseColor("#C4D6FF"), Color.parseColor("#6D93F0"),
                Color.parseColor("#3F6BE0")});
        orbView.setBackground(orbShape);
        LinearLayout.LayoutParams olp = new LinearLayout.LayoutParams(dp(72), dp(72));
        olp.gravity = Gravity.CENTER_HORIZONTAL;
        olp.topMargin = dp(10);
        olp.bottomMargin = dp(10);
        panel.addView(orbView, olp);

        // text
        statusView = new TextView(this);
        statusView.setTextColor(Color.parseColor("#E6F2F5"));
        statusView.setTextSize(17);
        statusView.setGravity(Gravity.CENTER);
        statusView.setText("Listening...");
        ScrollView sv = new ScrollView(this);
        sv.addView(statusView);
        panel.addView(sv, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(110)));

        heardView = new TextView(this);
        heardView.setTextColor(Color.parseColor("#7F979B"));
        heardView.setTextSize(12);
        heardView.setGravity(Gravity.CENTER);
        panel.addView(heardView);

        // mic button
        TextView again = new TextView(this);
        again.setText("Dobara bolein");
        again.setTextColor(Color.parseColor("#06201F"));
        again.setTextSize(14);
        again.setGravity(Gravity.CENTER);
        GradientDrawable pill = new GradientDrawable();
        pill.setColor(Color.parseColor("#4DE0D9"));
        pill.setCornerRadius(dp(20));
        again.setBackground(pill);
        again.setPadding(dp(22), dp(9), dp(22), dp(9));
        again.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startListening();
            }
        });
        LinearLayout.LayoutParams alp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        alp.gravity = Gravity.CENTER_HORIZONTAL;
        alp.topMargin = dp(8);
        panel.addView(again, alp);

        DisplayMetrics dm = getResources().getDisplayMetrics();
        int type = Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                dm.widthPixels - dp(24), WindowManager.LayoutParams.WRAP_CONTENT, type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
        lp.y = dp(28);
        wm.addView(panel, lp);
    }

    private void setStatus(final String text, final int newMode) {
        main.post(new Runnable() {
            @Override
            public void run() {
                if (statusView != null) {
                    statusView.setText(text);
                }
                mode = newMode;
            }
        });
    }

    private final Runnable ticker = new Runnable() {
        @Override
        public void run() {
            if (!alive || orbView == null) {
                return;
            }
            clock += 0.033;
            float target;
            if (speaking) {
                target = (float) (0.55 + 0.45 * Math.abs(Math.sin(clock * 5.1)));
            } else if (mode == MODE_THINK) {
                target = (float) (0.35 + 0.30 * Math.sin(clock * 4.2));
            } else if (mode == MODE_LISTEN) {
                target = Math.max(0.25f + (float) (0.15 * Math.sin(clock * 2.2)), targetLevel);
            } else {
                target = 0f;
            }
            level += (target - level) * 0.18f;
            float scale = 1f + 0.05f * (float) Math.sin(clock * 1.3) + 0.22f * level;
            orbView.setScaleX(scale);
            orbView.setScaleY(scale);
            targetLevel *= 0.9f;
            main.postDelayed(this, 33);
        }
    };

    // ----------------------------------------------------------------- TTS --
    private void initTts() {
        tts = new TextToSpeech(this, new TextToSpeech.OnInitListener() {
            @Override
            public void onInit(int status) {
                if (!alive || tts == null) {
                    return;
                }
                if (status != TextToSpeech.SUCCESS) {
                    return;
                }
                try {
                    if (tts.setLanguage(new Locale("en", "IN")) < 0) {
                        tts.setLanguage(Locale.US);
                    }
                    SharedPreferences p = prefs();
                    tts.setPitch(p.getFloat("pitch", 1.0f));
                    tts.setSpeechRate(p.getFloat("rate", 1.0f));
                    tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                        @Override
                        public void onStart(String utteranceId) {
                            speaking = true;
                        }

                        @Override
                        public void onDone(String utteranceId) {
                            speaking = false;
                            main.post(new Runnable() {
                                @Override
                                public void run() {
                                    scheduleClose(5000);
                                }
                            });
                        }

                        @Override
                        public void onError(String utteranceId) {
                            speaking = false;
                        }
                    });
                    ttsReady = true;
                    if (pendingSpeech != null) {
                        String s = pendingSpeech;
                        pendingSpeech = null;
                        speak(s);
                    }
                } catch (Exception ignored) {
                }
            }
        });
    }

    private void speak(String text) {
        if (!ttsReady || tts == null) {
            pendingSpeech = text;
            return;
        }
        muteBeep(false);
        try {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis");
        } catch (Exception ignored) {
        }
    }

    private final Runnable closeRunnable = new Runnable() {
        @Override
        public void run() {
            shutdown();
        }
    };

    private void scheduleClose(long ms) {
        main.removeCallbacks(closeRunnable);
        main.postDelayed(closeRunnable, ms);
    }

    private void cancelClose() {
        main.removeCallbacks(closeRunnable);
    }

    // ------------------------------------------------------------ listening --
    private SharedPreferences prefs() {
        return getSharedPreferences("jarvis_prefs", Context.MODE_PRIVATE);
    }

    private void muteBeep(boolean on) {
        if (on == beepMuted) {
            return;
        }
        beepMuted = on;
        try {
            AudioManager am = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
            int flag = on ? AudioManager.ADJUST_MUTE : AudioManager.ADJUST_UNMUTE;
            int[] streams = {AudioManager.STREAM_MUSIC, AudioManager.STREAM_NOTIFICATION,
                    AudioManager.STREAM_SYSTEM};
            for (int s : streams) {
                try {
                    am.adjustStreamVolume(s, flag, 0);
                } catch (Exception ignored) {
                }
            }
        } catch (Exception ignored) {
        }
    }

    private final Runnable unmuteRunnable = new Runnable() {
        @Override
        public void run() {
            muteBeep(false);
        }
    };

    private void startListening() {
        cancelClose();
        gen++;
        try {
            if (tts != null) {
                tts.stop();
            }
        } catch (Exception ignored) {
        }
        speaking = false;
        if (Build.VERSION.SDK_INT >= 23
                && checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            setStatus("Mic ki permission nahi hai. Jarvis app ek baar kholkar Allow kijiye.", MODE_IDLE);
            scheduleClose(8000);
            return;
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            setStatus("Is phone me speech recognition available nahi hai.", MODE_IDLE);
            scheduleClose(6000);
            return;
        }
        setStatus("Listening...", MODE_LISTEN);
        if (heardView != null) {
            heardView.setText("");
        }
        muteBeep(true);
        main.removeCallbacks(unmuteRunnable);
        main.postDelayed(unmuteRunnable, 12000);
        try {
            if (recognizer == null) {
                recognizer = SpeechRecognizer.createSpeechRecognizer(this);
                recognizer.setRecognitionListener(listener);
            } else {
                recognizer.cancel();
            }
            Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-IN");
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "en-IN");
            i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            recognizer.startListening(i);
        } catch (Exception e) {
            muteBeep(false);
            setStatus("Mic shuru nahi ho paya: " + e, MODE_IDLE);
            scheduleClose(6000);
        }
    }

    private final RecognitionListener listener = new RecognitionListener() {
        @Override
        public void onReadyForSpeech(Bundle params) {
        }

        @Override
        public void onBeginningOfSpeech() {
        }

        @Override
        public void onRmsChanged(float rmsdB) {
            float v = Math.max(0f, Math.min(1f, (rmsdB + 2f) / 12f));
            if (v > targetLevel) {
                targetLevel = v;
            }
        }

        @Override
        public void onBufferReceived(byte[] buffer) {
        }

        @Override
        public void onEndOfSpeech() {
        }

        @Override
        public void onError(int error) {
            muteBeep(false);
            if (!alive) {
                return;
            }
            if (error == SpeechRecognizer.ERROR_NO_MATCH
                    || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                setStatus("Kuch sunai nahi diya. 'Dobara bolein' dabaiye.", MODE_IDLE);
            } else if (error == SpeechRecognizer.ERROR_NETWORK
                    || error == SpeechRecognizer.ERROR_NETWORK_TIMEOUT) {
                setStatus("Speech ke liye internet chahiye. Connection check kijiye.", MODE_IDLE);
            } else if (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY) {
                setStatus("Mic abhi busy hai. Dobara dabaiye.", MODE_IDLE);
            } else {
                setStatus("Mic error (" + error + "). Dobara try kijiye.", MODE_IDLE);
            }
            scheduleClose(7000);
        }

        @Override
        public void onResults(Bundle results) {
            muteBeep(false);
            ArrayList<String> list = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (list == null || list.isEmpty()) {
                setStatus("Kuch sunai nahi diya. 'Dobara bolein' dabaiye.", MODE_IDLE);
                scheduleClose(7000);
                return;
            }
            handleCommand(list.get(0));
        }

        @Override
        public void onPartialResults(Bundle partial) {
            ArrayList<String> list = partial.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (list != null && !list.isEmpty() && heardView != null) {
                heardView.setText(list.get(0));
            }
        }

        @Override
        public void onEvent(int eventType, Bundle params) {
        }
    };

    // -------------------------------------------------------------- command --
    private void handleCommand(final String text) {
        final long myGen = ++gen;
        if (heardView != null) {
            heardView.setText("\"" + text + "\"");
        }
        String quick = JarvisBrain.creatorReply(text);
        if (quick != null) {
            reply(quick);
            return;
        }
        final SharedPreferences p = prefs();
        final String key = p.getString("gemini_key", "");
        if (key.trim().length() == 0 || !p.getBoolean("ai_enabled", true)) {
            reply("Gemini key set nahi hai ya AI band hai. Jarvis app ki Settings me key daaliye.");
            return;
        }
        setStatus("Soch raha hoon...", MODE_THINK);
        new Thread(new Runnable() {
            @Override
            public void run() {
                final JarvisBrain.Result r = JarvisBrain.ask(key, p.getString("ai_model", ""),
                        p.getString("verbosity", "Balanced"), text);
                main.post(new Runnable() {
                    @Override
                    public void run() {
                        if (!alive || myGen != gen) {
                            return;
                        }
                        if (r.error != null) {
                            reply(r.error);
                        } else if (r.function != null) {
                            reply(runFunction(r.function, r.args));
                        } else {
                            reply(r.reply);
                        }
                        if (r.error == null && JarvisBrain.lastModel.length() > 0) {
                            p.edit().putString("ai_model", JarvisBrain.lastModel).apply();
                        }
                    }
                });
            }
        }).start();
    }

    private void reply(String text) {
        setStatus(text, MODE_IDLE);
        speak(JarvisBrain.speechText(text));
        // TTS ready na ho ya bolna shuru na ho to bhi panel kuch der baad band ho jaye
        scheduleClose(Math.max(9000, text.length() * 90L));
    }

    // -------------------------------------------------------------- actions --
    private String runFunction(String name, JSONObject a) {
        try {
            if ("set_alarm".equals(name)) {
                return setAlarm(a.optInt("hour", -1), a.optInt("minute", 0));
            } else if ("set_timer".equals(name)) {
                return setTimer(a.optInt("seconds", 0));
            } else if ("open_app".equals(name)) {
                return openApp(a.optString("app_name", ""));
            } else if ("call_contact".equals(name)) {
                return callContact(a.optString("name", ""));
            } else if ("flashlight".equals(name)) {
                return flashlight(a.optBoolean("on", true));
            } else if ("web_search".equals(name)) {
                return openUrl("https://www.google.com/search?q="
                        + URLEncoder.encode(a.optString("query", ""), "UTF-8"), "Google par search kar raha hoon.");
            } else if ("youtube_search".equals(name)) {
                return openUrl("https://www.youtube.com/results?search_query="
                        + URLEncoder.encode(a.optString("query", ""), "UTF-8"), "YouTube par dhoondh raha hoon.");
            }
        } catch (Exception e) {
            return "Ye kaam nahi ho paya: " + e.getMessage();
        }
        return "Ye kaam abhi mujhe nahi aata.";
    }

    private String setAlarm(int hour, int minute) {
        if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
            return "Alarm ka samay samajh nahi aaya. Dobara boliye.";
        }
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, hour);
        cal.set(Calendar.MINUTE, minute);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        if (cal.getTimeInMillis() <= System.currentTimeMillis()) {
            cal.add(Calendar.DAY_OF_YEAR, 1);
        }
        AlarmManager am = (AlarmManager) getSystemService(Context.ALARM_SERVICE);
        Intent i = new Intent(this, JarvisAlarmReceiver.class);
        i.putExtra("jarvis_type", "alarm");
        i.putExtra("jarvis_message", "JARVIS alarm");
        int f = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) {
            f |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi = PendingIntent.getBroadcast(this, 9001, i, f);
        if (Build.VERSION.SDK_INT >= 23) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cal.getTimeInMillis(), pi);
        } else {
            am.setExact(AlarmManager.RTC_WAKEUP, cal.getTimeInMillis(), pi);
        }
        String shown = new java.text.SimpleDateFormat("hh:mm a", Locale.ENGLISH).format(cal.getTime());
        return "Alarm " + shown + " ke liye set ho gaya.";
    }

    private String setTimer(int seconds) {
        if (seconds <= 0 || seconds > 86400) {
            return "Timer ka samay samajh nahi aaya. Dobara boliye.";
        }
        AlarmManager am = (AlarmManager) getSystemService(Context.ALARM_SERVICE);
        Intent i = new Intent(this, JarvisAlarmReceiver.class);
        i.putExtra("jarvis_type", "timer");
        i.putExtra("jarvis_message", "JARVIS timer complete");
        int f = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) {
            f |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi = PendingIntent.getBroadcast(this, 9002, i, f);
        long at = SystemClock.elapsedRealtime() + seconds * 1000L;
        if (Build.VERSION.SDK_INT >= 23) {
            am.setExactAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, pi);
        } else {
            am.setExact(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, pi);
        }
        String shown = seconds >= 60 ? (seconds / 60) + " minute" + (seconds % 60 > 0 ? " " + (seconds % 60)
                + " second" : "") : seconds + " second";
        return "Timer " + shown + " ke liye start ho gaya.";
    }

    private String openApp(String wanted) {
        String w = wanted.toLowerCase(Locale.ENGLISH).trim();
        if (w.length() == 0) {
            return "Kaun sa app kholna hai?";
        }
        PackageManager pm = getPackageManager();
        Intent mainIntent = new Intent(Intent.ACTION_MAIN);
        mainIntent.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> apps = pm.queryIntentActivities(mainIntent, 0);
        ResolveInfo best = null;
        int bestScore = 0;
        for (ResolveInfo ri : apps) {
            String label = String.valueOf(ri.loadLabel(pm)).toLowerCase(Locale.ENGLISH);
            int score = 0;
            if (label.equals(w)) {
                score = 3;
            } else if (label.startsWith(w) || w.startsWith(label)) {
                score = 2;
            } else if (label.contains(w) || w.contains(label)) {
                score = 1;
            }
            if (score > bestScore) {
                bestScore = score;
                best = ri;
            }
        }
        if (best == null) {
            return wanted + " naam ka app mujhe nahi mila.";
        }
        Intent launch = pm.getLaunchIntentForPackage(best.activityInfo.packageName);
        if (launch == null) {
            return wanted + " khul nahi paya.";
        }
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(launch);
        return String.valueOf(best.loadLabel(pm)) + " khol raha hoon.";
    }

    private boolean granted(String perm) {
        return Build.VERSION.SDK_INT < 23
                || checkSelfPermission(perm) == PackageManager.PERMISSION_GRANTED;
    }

    private String callContact(String wanted) {
        String w = wanted.toLowerCase(Locale.ENGLISH).trim();
        if (w.length() == 0) {
            return "Kisko call karna hai?";
        }
        if (!granted("android.permission.READ_CONTACTS")) {
            return "Contacts ki permission nahi hai. Jarvis app ki Settings me 'Calling permission allow karo' dabaiye.";
        }
        String bestName = null;
        String bestNumber = null;
        int bestScore = 0;
        android.database.Cursor c = null;
        try {
            c = getContentResolver().query(
                    android.provider.ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    new String[]{android.provider.ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                            android.provider.ContactsContract.CommonDataKinds.Phone.NUMBER},
                    null, null, null);
            while (c != null && c.moveToNext()) {
                String n = c.getString(0);
                String num = c.getString(1);
                if (n == null || num == null) {
                    continue;
                }
                String low = n.toLowerCase(Locale.ENGLISH);
                int score = 0;
                if (low.equals(w)) {
                    score = 4;
                } else if (low.startsWith(w)) {
                    score = 3;
                } else if (low.contains(w)) {
                    score = 2;
                } else {
                    String[] parts = w.split("\\s+");
                    boolean all = parts.length > 0;
                    for (String part : parts) {
                        if (part.length() == 0 || !low.contains(part)) {
                            all = false;
                        }
                    }
                    if (all) {
                        score = 1;
                    }
                }
                if (score > bestScore) {
                    bestScore = score;
                    bestName = n;
                    bestNumber = num;
                }
            }
        } finally {
            if (c != null) {
                c.close();
            }
        }
        if (bestNumber == null) {
            return wanted + " naam ka contact nahi mila.";
        }
        String clean = bestNumber.replaceAll("[^0-9+]", "");
        boolean direct = granted("android.permission.CALL_PHONE");
        Intent i = new Intent(direct ? Intent.ACTION_CALL : Intent.ACTION_DIAL,
                Uri.parse("tel:" + clean));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(i);
        return direct ? bestName + " ko call kar raha hoon." : bestName + " ka number dialer me khol diya.";
    }

    private String flashlight(boolean on) {
        try {
            CameraManager cm = (CameraManager) getSystemService(Context.CAMERA_SERVICE);
            String[] ids = cm.getCameraIdList();
            if (ids.length == 0) {
                return "Is phone me torch nahi mili.";
            }
            cm.setTorchMode(ids[0], on);
            return on ? "Torch on kar di." : "Torch band kar di.";
        } catch (Exception e) {
            return "Torch chalu nahi ho paayi.";
        }
    }

    private String openUrl(String url, String say) {
        Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(i);
        return say;
    }
}
