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
    private final JarvisEleven eleven = new JarvisEleven();
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

    // --- "Jarvis" bolne par jaagna (offline Vosk, kisi key ki zaroorat nahi) ---
    private boolean wakeEnabled = false;
    private boolean wakeRunning = false;
    private JarvisVoskWake vosk = null;

    // --- naam se call: kai match hon to list dikhakar number se chunna ---
    private List<JarvisContactMatch.Scored> pendingChoices = null;
    private boolean awaitingName = false;     // "Kisko call karun?" ke baad agla jawab naam hai
    private boolean listenAfterSpeech = false; // bolna khatam hote hi dobara sunna

    // --- WhatsApp message / call ---
    private JarvisSocial.Job sJob = null;
    private List<JarvisContactMatch.Scored> sChoices = null;
    private final java.util.Map<String, JarvisWhatsApp.Person> sByCid = new java.util.HashMap<String, JarvisWhatsApp.Person>();
    private boolean sAwaitBody = false;
    private boolean sConfirm = false;
    private boolean sAwaitName = false;

    // --- floating bubble (hamesha dikhta hai; sleep = dhundhla, active = chamakta) ---
    private WindowManager.LayoutParams bubbleLp = null;
    private boolean session = false;          // True = Jarvis abhi sun/bol raha hai (baatcheet chal rahi hai)
    private int idleCount = 0;                // lagataar kitni baar kuch sunai nahi diya

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
            startAsForeground(ACTION_TALK.equals(action) || session);
            if (ACTION_WAKE_OFF.equals(action)) {
                wakeEnabled = false;
                prefs().edit().putBoolean("wake_enabled", false).apply();
                stopWake(true);
                cleanup();
                removeBubble();
                setWakeStatus("band");
                stopForeground(true);
                stopSelf();
                return START_NOT_STICKY;
            }
            if (ACTION_WAKE_ON.equals(action)) {
                wakeEnabled = true;
                prefs().edit().putBoolean("wake_enabled", true).apply();
                ensureBubble();
                if (!session) {
                    setBubbleActive(false);
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
        if (!session) {
            session = true;
            alive = true;
            idleCount = 0;
            stopWake(false);              // mic ek hi cheez use kar sakti hai
            ensureBubble();
            setBubbleActive(true);
            initTts();
            main.post(ticker);
        }
        startListening();
    }

    @Override
    public void onDestroy() {
        stopWake(true);
        cleanup();
        removeBubble();
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
        if (!wakeEnabled || wakeRunning) {
            return;
        }
        try {
            startVosk();
        } catch (Throwable th) {
            wakeRunning = false;
            Throwable r = root(th);
            String msg = r.getClass().getSimpleName() + ": " + r.getMessage();
            setWakeStatus("error: " + msg);
            toastError("Wake word shuru nahi hua: " + msg);
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
        wakeRunning = false;
    }

    private void onWakeWord() {
        if (session) {
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
                .setOngoing(true);
        if (Build.VERSION.SDK_INT >= 23) {
            // status bar me chhota safed gola (white dot)
            android.graphics.Bitmap bmp = android.graphics.Bitmap.createBitmap(96, 96,
                    android.graphics.Bitmap.Config.ARGB_8888);
            android.graphics.Canvas cv = new android.graphics.Canvas(bmp);
            android.graphics.Paint pt = new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
            pt.setColor(Color.WHITE);
            cv.drawCircle(48, 48, 34, pt);
            nb.setSmallIcon(android.graphics.drawable.Icon.createWithBitmap(bmp));
            Intent off = new Intent(this, JarvisOverlayService.class);
            off.setAction(ACTION_WAKE_OFF);
            int f = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
            PendingIntent pi = Build.VERSION.SDK_INT >= 26
                    ? PendingIntent.getForegroundService(this, 77, off, f)
                    : PendingIntent.getService(this, 77, off, f);
            nb.addAction(new Notification.Action.Builder(
                    android.graphics.drawable.Icon.createWithBitmap(bmp), "Band karo (Off)", pi).build());
        } else {
            nb.setSmallIcon(getApplicationInfo().icon);
        }
        Notification n = nb.build();
        if (Build.VERSION.SDK_INT >= 30) {
            startForeground(NOTIF_ID, n, 128);   // 128 = FOREGROUND_SERVICE_TYPE_MICROPHONE
        } else {
            startForeground(NOTIF_ID, n);
        }
    }

    /** Baatcheet khatam: bubble dhundhla (sleep) ho jata hai aur sirf "Jarvis" ka intezaar chalta hai. */
    private void shutdown() {
        cleanup();
        pendingChoices = null;
        awaitingName = false;
        listenAfterSpeech = false;
        if (wakeEnabled) {
            setBubbleActive(false);
            try {
                startAsForeground(false);
            } catch (Exception ignored) {
            }
            // mic ko thoda waqt do (SpeechRecognizer chhodta hai), phir wake word dobara chalu
            main.postDelayed(new Runnable() {
                @Override
                public void run() {
                    if (!session) {
                        startWake();
                    }
                }
            }, 900);
            return;
        }
        removeBubble();
        try {
            stopForeground(true);
        } catch (Exception ignored) {
        }
        stopSelf();
    }

    private void cleanup() {
        alive = false;
        session = false;
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
            eleven.stop();
            if (tts != null) {
                tts.stop();
                tts.shutdown();
            }
        } catch (Exception ignored) {
        }
        tts = null;
        ttsReady = false;
    }

    private void removeBubble() {
        try {
            if (panel != null && wm != null) {
                wm.removeView(panel);
            }
        } catch (Exception ignored) {
        }
        panel = null;
        orbView = null;
        bubbleLp = null;
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

    /** Chhota safed gola (bubble): hamesha dikhta hai. Pakad kar kahin bhi rakh sakte hain, tap = on/off. */
    private void ensureBubble() {
        if (panel != null) {
            return;
        }
        try {
            if (Build.VERSION.SDK_INT >= 23 && !android.provider.Settings.canDrawOverlays(this)) {
                toastError("Jarvis bubble ke liye 'Display over other apps' allow kijiye");
                return;
            }
            wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
            panel = new LinearLayout(this);
            panel.setOrientation(LinearLayout.VERTICAL);
            orbView = new View(this);
            orbShape = new GradientDrawable();
            orbShape.setShape(GradientDrawable.OVAL);
            orbShape.setColor(Color.WHITE);
            orbShape.setStroke(dp(1), Color.parseColor("#55000000"));
            orbView.setBackground(orbShape);
            panel.addView(orbView, new LinearLayout.LayoutParams(dp(18), dp(18)));
            panel.setPadding(dp(12), dp(12), dp(12), dp(12));
            int type = Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                    : WindowManager.LayoutParams.TYPE_PHONE;
            bubbleLp = new WindowManager.LayoutParams(
                    WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT, type,
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                            | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                    PixelFormat.TRANSLUCENT);
            bubbleLp.gravity = Gravity.TOP | Gravity.LEFT;
            DisplayMetrics dm = getResources().getDisplayMetrics();
            SharedPreferences p = prefs();
            bubbleLp.x = p.getInt("bubble_x", dm.widthPixels / 2 - dp(21));
            bubbleLp.y = p.getInt("bubble_y", dp(28));
            clampBubble();
            panel.setOnTouchListener(bubbleTouch);
            wm.addView(panel, bubbleLp);
        } catch (Exception e) {
            toastError("Bubble nahi ban paya: " + e);
            panel = null;
            orbView = null;
            bubbleLp = null;
        }
    }

    private void clampBubble() {
        if (bubbleLp == null) {
            return;
        }
        DisplayMetrics dm = getResources().getDisplayMetrics();
        int size = dp(42);
        bubbleLp.x = Math.max(0, Math.min(dm.widthPixels - size, bubbleLp.x));
        bubbleLp.y = Math.max(0, Math.min(dm.heightPixels - size, bubbleLp.y));
    }

    /** active = chamakta safed (sun raha hai); warna dhundhla (so raha hai, sirf 'Jarvis' ka intezaar). */
    private void setBubbleActive(boolean active) {
        if (orbView == null) {
            return;
        }
        orbView.setAlpha(active ? 1.0f : 0.40f);
        orbView.setScaleX(1f);
        orbView.setScaleY(1f);
    }

    private final View.OnTouchListener bubbleTouch = new View.OnTouchListener() {
        private float downX, downY;
        private int startX, startY;
        private boolean dragging = false;

        @Override
        public boolean onTouch(View v, android.view.MotionEvent e) {
            if (bubbleLp == null) {
                return false;
            }
            switch (e.getActionMasked()) {
                case android.view.MotionEvent.ACTION_DOWN:
                    downX = e.getRawX();
                    downY = e.getRawY();
                    startX = bubbleLp.x;
                    startY = bubbleLp.y;
                    dragging = false;
                    return true;
                case android.view.MotionEvent.ACTION_MOVE:
                    float dx = e.getRawX() - downX;
                    float dy = e.getRawY() - downY;
                    if (!dragging && Math.abs(dx) + Math.abs(dy) > dp(8)) {
                        dragging = true;
                    }
                    if (dragging) {
                        bubbleLp.x = startX + (int) dx;
                        bubbleLp.y = startY + (int) dy;
                        clampBubble();
                        try {
                            wm.updateViewLayout(panel, bubbleLp);
                        } catch (Exception ignored) {
                        }
                    }
                    return true;
                case android.view.MotionEvent.ACTION_UP:
                    if (dragging) {
                        prefs().edit().putInt("bubble_x", bubbleLp.x).putInt("bubble_y", bubbleLp.y).apply();
                    } else {
                        onBubbleTap();
                    }
                    return true;
                default:
                    return true;
            }
        }
    };

    /** Tap: so raha ho to jagao (sunna shuru), jaag raha ho to sula do. */
    private void onBubbleTap() {
        if (session) {
            shutdown();
        } else {
            onWakeWord();
        }
    }

    private void showText(String text) {
        try {
            android.widget.Toast.makeText(this, text, text.length() > 60
                    ? android.widget.Toast.LENGTH_LONG : android.widget.Toast.LENGTH_SHORT).show();
        } catch (Exception ignored) {
        }
    }

    private void setStatus(final String text, final int newMode) {
        main.post(new Runnable() {
            @Override
            public void run() {
                if (statusView != null) {
                    statusView.setText(text);
                } else if (newMode == MODE_IDLE && text != null && text.length() > 0 && alive) {
                    showText(text);
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
                                    afterSpeech();
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
                        speakSystem(s);
                    }
                } catch (Exception ignored) {
                }
            }
        });
    }

    /** Bolna khatam: baatcheet jaari ho to sunna, warna thodi der me so jao. */
    private void afterSpeech() {
        if (listenAfterSpeech && alive) {
            listenAfterSpeech = false;
            startListening();
        } else if (alive) {
            scheduleClose(700);
        }
    }

    /** ElevenLabs ki awaaz chuni ho to wahi, warna (ya galti par) phone ki awaaz. */
    private void speak(final String text) {
        SharedPreferences p = prefs();
        String ek = p.getString("eleven_key", "");
        String vid = p.getString("eleven_voice_id", "");
        if (ek.trim().length() > 0 && vid.trim().length() > 0) {
            muteBeep(false);
            try {
                if (tts != null) {
                    tts.stop();
                }
            } catch (Exception ignored) {
            }
            speaking = true;
            eleven.speak(this, ek, vid, text, new JarvisEleven.Callback() {
                @Override
                public void onDone(boolean ok, String error) {
                    speaking = false;
                    if (!alive) {
                        return;
                    }
                    if (ok) {
                        afterSpeech();
                    } else {
                        showText(error + ". Phone ki awaaz se bol raha hoon");
                        speakSystem(text);
                    }
                }
            });
            return;
        }
        speakSystem(text);
    }

    private void speakSystem(String text) {
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
            eleven.stop();
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
                idleCount++;
                if (idleCount < 3) {
                    main.postDelayed(new Runnable() {
                        @Override
                        public void run() {
                            if (alive && session) {
                                startListening();
                            }
                        }
                    }, 300);
                    return;
                }
                setStatus("Kuch sunai nahi diya. Jarvis so gaya.", MODE_IDLE);
                scheduleClose(1500);
                return;
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
                onError(SpeechRecognizer.ERROR_NO_MATCH);
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
        idleCount = 0;
        if (!isDismiss(text) && handleSocialFlow(text)) {
            return;
        }
        if (isDismiss(text)) {
            pendingChoices = null;
            awaitingName = false;
            listenAfterSpeech = false;
            String bye = "Theek hai. Jab zaroorat ho, Jarvis bolkar bula lena.";
            setStatus(bye, MODE_IDLE);
            speak(bye);
            scheduleClose(4500);
            return;
        }
        if (handleCallFlow(text)) {
            return;
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
                            String out = runFunction(r.function, r.args);
                            if (out != null) {
                                reply(out);
                            }
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

    /** Jawab bolo, phir baatcheet jaari: bolna khatam hote hi dobara sunna. */
    private void reply(String text) {
        replyAndListen(text, JarvisBrain.speechText(text));
    }

    /** Kaam ho gaya (call/message laga): bolo aur baatcheet band, bubble so jaye. */
    private void replyDone(String text) {
        cancelClose();
        listenAfterSpeech = false;
        setStatus(text, MODE_IDLE);
        speak(JarvisBrain.speechText(text));
        scheduleClose(Math.max(5000L, text.length() * 90L));
    }

    // ------------------------------------------------------- WhatsApp flow --
    private void socialReset() {
        sJob = null;
        sChoices = null;
        sAwaitBody = false;
        sConfirm = false;
        sAwaitName = false;
    }

    private boolean handleSocialFlow(String text) {
        if (sConfirm) {
            String ans = JarvisSocial.yesNo(text);
            if (ans.equals("yes")) {
                sConfirm = false;
                socialSend();
                return true;
            }
            if (ans.equals("no")) {
                socialReset();
                reply("Theek hai, message nahi bheja.");
                return true;
            }
            if (JarvisSocial.parse(text) == null) {
                replyAndListen("Bhej dun? Haan ya nahi boliye.", "Bhej dun? Haan ya nahi boliye.");
                return true;
            }
            socialReset();
        }
        if (sAwaitBody) {
            sAwaitBody = false;
            if (JarvisSocial.parse(text) == null || JarvisSocial.yesNo(text).length() == 0) {
                sJob.body = text.trim();
                socialAskConfirm();
                return true;
            }
            socialReset();
        }
        if (sAwaitName) {
            sAwaitName = false;
            List<String> keep = new ArrayList<String>();
            for (String t : JarvisContactMatch.words(text)) {
                if (!JarvisSocial.SKIP.contains(t)) {
                    keep.add(t);
                }
            }
            sJob.name = JarvisSocial.join(keep);
            socialResolve();
            return true;
        }
        if (sChoices != null) {
            int pick = JarvisContactMatch.parseChoice(text, sChoices.size());
            if (pick > 0) {
                JarvisWhatsApp.Person p = sByCid.get(sChoices.get(pick - 1).contact.number);
                sChoices = null;
                socialAct(p);
                return true;
            }
            if (pick < 0) {
                socialReset();
                reply("Theek hai, rehne diya.");
                return true;
            }
            if (JarvisSocial.parse(text) == null) {
                replyAndListen("Number boliye, jaise do.", "Samajh nahi aaya. Number boliye, jaise do.");
                return true;
            }
            sChoices = null;
        }
        JarvisSocial.Job j = JarvisSocial.parse(text);
        if (j == null) {
            return false;
        }
        if (!j.app.equals("whatsapp")) {
            String nm = j.app.substring(0, 1).toUpperCase(Locale.ENGLISH) + j.app.substring(1);
            reply(nm + " par message ya call Android me bahar se mumkin nahi hai. "
                    + "WhatsApp par kar sakta hoon, WhatsApp bolkar dekhiye.");
            return true;
        }
        sJob = j;
        socialResolve();
        return true;
    }

    private void socialResolve() {
        if (!granted("android.permission.READ_CONTACTS")) {
            reply("Contacts ki permission nahi hai. Jarvis app ki Settings me 'Calling permission allow karo' dabaiye.");
            socialReset();
            return;
        }
        List<JarvisContactMatch.Contact> contacts = new ArrayList<JarvisContactMatch.Contact>();
        try {
            sByCid.clear();
            for (JarvisWhatsApp.Person p : JarvisWhatsApp.load(this)) {
                contacts.add(new JarvisContactMatch.Contact(p.name, String.valueOf(p.cid)));
                sByCid.put(String.valueOf(p.cid), p);
            }
        } catch (Exception e) {
            reply("WhatsApp contacts padh nahi paya: " + e.getMessage());
            socialReset();
            return;
        }
        String name = sJob.name;
        if (sJob.kind.equals("message") && sJob.ambiguous && sJob.body == null) {
            String[] nb = JarvisSocial.splitNameBody(JarvisContactMatch.words(name), contacts);
            sJob.name = nb[0];
            sJob.body = nb[1];
            name = nb[0];
        }
        if (name.trim().length() == 0) {
            sAwaitName = true;
            replyAndListen("Kisko?", "Kisko?");
            return;
        }
        List<JarvisContactMatch.Scored> found = JarvisContactMatch.find(name, contacts, 4);
        if (found.isEmpty()) {
            reply(name + " naam ka WhatsApp contact nahi mila.");
            socialReset();
        } else if (found.size() == 1) {
            socialAct(sByCid.get(found.get(0).contact.number));
        } else {
            sChoices = found;
            StringBuilder sb = new StringBuilder("Ye WhatsApp contacts mile. Bolkar chuniye (jaise \"2\"):\n");
            for (int i = 0; i < found.size(); i++) {
                sb.append("\n").append(i + 1).append(".  ").append(found.get(i).contact.name);
            }
            replyAndListen(sb.toString(), choicesSpeech(found));
        }
    }

    private void socialAct(JarvisWhatsApp.Person p) {
        if (p == null || sJob == null) {
            socialReset();
            return;
        }
        String shown = JarvisContactMatch.speakable(p.name);
        if (sJob.kind.equals("call")) {
            try {
                JarvisWhatsApp.call(this, p, sJob.video);
                replyDone(shown + " ko WhatsApp par " + (sJob.video ? "video" : "voice") + " call laga raha hoon.");
            } catch (Exception e) {
                replyDone(e.getMessage() != null && e.getMessage().contains("WhatsApp")
                        ? e.getMessage() : "WhatsApp call nahi lag paya.");
            }
            socialReset();
            return;
        }
        sJob.person = p;
        if (sJob.body == null || sJob.body.length() == 0) {
            sAwaitBody = true;
            replyAndListen(shown + " ko kya message bhejna hai?", shown + " ko kya message bhejna hai?");
            return;
        }
        socialAskConfirm();
    }

    private void socialAskConfirm() {
        String shown = JarvisContactMatch.speakable(sJob.person.name);
        sConfirm = true;
        replyAndListen(shown + " ko WhatsApp par bhejna hai: " + sJob.body + "\nBhej dun?",
                shown + " ko WhatsApp par bhejna hai. " + sJob.body + ". Bhej dun?");
    }

    private void socialSend() {
        JarvisSocial.Job job = sJob;
        String shown = JarvisContactMatch.speakable(job.person.name);
        try {
            String number = JarvisWhatsApp.phoneFor(this, job.person.cid);
            if (number.length() == 0) {
                replyDone(shown + " ka number nahi mila.");
            } else {
                JarvisWhatsApp.chat(this, job.person, number, job.body);
                replyDone(JarvisWhatsApp.accessibilityOn(this)
                        ? shown + " ko message bhej raha hoon."
                        : "Chat khol di hai. Bas Send dabaiye. Apne aap bhejne ke liye Accessibility me JARVIS auto-send On kijiye.");
            }
        } catch (Exception e) {
            replyDone("WhatsApp khul nahi paya.");
        }
        socialReset();
    }

    private boolean isDismiss(String text) {
        StringBuilder sbw = new StringBuilder(" ");
        for (String w : JarvisContactMatch.words(text)) {
            sbw.append(w).append(' ');
        }
        String t = sbw.toString();
        String[] device = {" wifi ", " bluetooth ", " torch ", " flashlight ", " data ", " hotspot ", " volume ",
                " screen ", " brightness ", " music ", " gaana ", " alarm ", " timer ", " call "};
        for (String d : device) {
            if (t.contains(d)) {
                return false;
            }
        }
        String[] phrases = {" kaam ho gaya ", " kam ho gaya ", " ja sakte ho ", " ja sakta hai ", " tum ja ", " tu ja ",
                " tum jao ", " ab jao ", " ab tum jao ", " off ho jao ", " off ho ja ", " band ho jao ", " band ho ja ",
                " bond ho ", " bandh ho ", " ab off ", " tum off ", " tu off ", " jarvis off ", " jarvis band ",
                " bye ", " bye bye ", " goodbye ", " good bye ", " alvida ", " so jao ", " so ja ", " go to sleep ",
                " sleep ", " stop listening ", " chup ho ", " chup raho ", " thats all ", " that s all ",
                " bas itna ", " bas ab ", " go away ", " shut down ", " shutdown ", " tata ", " you can go ",
                " dismiss ", " exit ", " sunna band ", " sunna band karo "};
        for (String ph : phrases) {
            if (t.contains(ph)) {
                return true;
            }
        }
        String[] thanks = {" thank you ", " thanks ", " dhanyavad ", " shukriya ", " thank u "};
        int n = JarvisContactMatch.words(text).size();
        for (String th : thanks) {
            if (t.contains(th) && n <= 4) {
                return true;
            }
        }
        return false;
    }

    /** Jawab dikhao + bolo, phir bolna khatam hote hi mic dobara kholo (jawab ka intezaar). */
    private void replyAndListen(String shown, String spoken) {
        cancelClose();
        setStatus(shown, MODE_IDLE);
        listenAfterSpeech = true;
        speak(spoken);
        // TTS na chale to bhi 20 second baad mic khul jaye
        main.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (listenAfterSpeech && alive && !speaking) {
                    listenAfterSpeech = false;
                    startListening();
                }
            }
        }, Math.max(6000L, spoken.length() * 110L));
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
                callByName(a.optString("name", ""));
                return null;
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
        try {
            // phone ki asli Clock app se: ye hamesha bajta hai (AlarmManager receiver MIUI par chup rehta tha)
            Intent i = new Intent(android.provider.AlarmClock.ACTION_SET_ALARM);
            i.putExtra(android.provider.AlarmClock.EXTRA_HOUR, hour);
            i.putExtra(android.provider.AlarmClock.EXTRA_MINUTES, minute);
            i.putExtra(android.provider.AlarmClock.EXTRA_MESSAGE, "JARVIS");
            i.putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (Exception e) {
            return "Alarm set nahi ho paya: " + e.getMessage();
        }
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, hour);
        cal.set(Calendar.MINUTE, minute);
        String shown = new java.text.SimpleDateFormat("hh:mm a", Locale.ENGLISH).format(cal.getTime());
        return "Alarm " + shown + " ke liye set ho gaya.";
    }

    private String setTimer(int seconds) {
        if (seconds <= 0 || seconds > 86400) {
            return "Timer ka samay samajh nahi aaya. Dobara boliye.";
        }
        try {
            Intent i = new Intent(android.provider.AlarmClock.ACTION_SET_TIMER);
            i.putExtra(android.provider.AlarmClock.EXTRA_LENGTH, seconds);
            i.putExtra(android.provider.AlarmClock.EXTRA_MESSAGE, "JARVIS");
            i.putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (Exception e) {
            return "Timer start nahi ho paya: " + e.getMessage();
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

    // ------------------------------------------------------------- calling --
    /** Call se judi baat ho to yahin sambhal lo (true = ho gaya). Gemini ki zaroorat nahi. */
    private boolean handleCallFlow(String text) {
        if (pendingChoices != null) {
            int pick = JarvisContactMatch.parseChoice(text, pendingChoices.size());
            if (pick > 0) {
                JarvisContactMatch.Scored s = pendingChoices.get(pick - 1);
                pendingChoices = null;
                replyDone(dial(s.contact));
                return true;
            }
            if (pick < 0) {
                pendingChoices = null;
                reply("Theek hai, call nahi kar raha.");
                return true;
            }
            String again = JarvisContactMatch.parseCallRequest(text);
            if (again == null || again.length() == 0) {
                replyAndListen(choicesText(pendingChoices),
                        "Samajh nahi aaya. Number boliye, jaise do.");
                return true;
            }
            pendingChoices = null;       // naya naam bola: usse dhoondo
        }
        if (awaitingName) {
            awaitingName = false;
            String nm = JarvisContactMatch.parseCallRequest("call " + text);
            callByName(nm == null || nm.length() == 0 ? text : nm);
            return true;
        }
        String name = JarvisContactMatch.parseCallRequest(text);
        if (name == null) {
            return false;
        }
        if (name.length() == 0) {
            awaitingName = true;
            replyAndListen("Kisko call karun?", "Kisko call karun?");
            return true;
        }
        callByName(name);
        return true;
    }

    private List<JarvisContactMatch.Contact> loadContacts() {
        List<JarvisContactMatch.Contact> out = new ArrayList<JarvisContactMatch.Contact>();
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
                if (n != null && num != null) {
                    out.add(new JarvisContactMatch.Contact(n, num));
                }
            }
        } finally {
            if (c != null) {
                c.close();
            }
        }
        return out;
    }

    private String choicesText(List<JarvisContactMatch.Scored> list) {
        StringBuilder sb = new StringBuilder("Ye contacts mile. Bolkar chuniye (jaise \"2 ko call karo\"):\n");
        for (int i = 0; i < list.size(); i++) {
            JarvisContactMatch.Contact c = list.get(i).contact;
            sb.append("\n").append(i + 1).append(".  ").append(c.name).append("\n     ").append(c.number);
        }
        return sb.toString();
    }

    private String choicesSpeech(List<JarvisContactMatch.Scored> list) {
        StringBuilder sb = new StringBuilder("Mujhe " + list.size() + " contacts mile. ");
        for (int i = 0; i < list.size(); i++) {
            JarvisContactMatch.Contact c = list.get(i).contact;
            String d = JarvisContactMatch.digits(c.number);
            boolean sameName = false;
            for (int j = 0; j < list.size(); j++) {
                if (j != i && JarvisContactMatch.speakable(list.get(j).contact.name)
                        .equalsIgnoreCase(JarvisContactMatch.speakable(c.name))) {
                    sameName = true;
                }
            }
            sb.append("Number ").append(i + 1).append(", ").append(JarvisContactMatch.speakable(c.name));
            if (sameName && d.length() >= 4) {
                sb.append(", number ").append(d.substring(d.length() - 4).replaceAll("(.)", "$1 ")).append("par khatam");
            }
            sb.append(". ");
        }
        sb.append("Kaun sa call karun?");
        return sb.toString();
    }

    private void callByName(String wanted) {
        String w = wanted == null ? "" : wanted.trim();
        if (w.length() == 0) {
            awaitingName = true;
            replyAndListen("Kisko call karun?", "Kisko call karun?");
            return;
        }
        if (!granted("android.permission.READ_CONTACTS")) {
            reply("Contacts ki permission nahi hai. Jarvis app ki Settings me 'Calling permission allow karo' dabaiye.");
            return;
        }
        List<JarvisContactMatch.Scored> found;
        try {
            found = JarvisContactMatch.find(w, loadContacts(), 4);
        } catch (Exception e) {
            reply("Contacts padh nahi paya: " + e.getMessage());
            return;
        }
        if (found.isEmpty()) {
            reply(w + " naam ka contact nahi mila.");
        } else if (found.size() == 1) {
            replyDone(dial(found.get(0).contact));
        } else {
            pendingChoices = found;
            replyAndListen(choicesText(found), choicesSpeech(found));
        }
    }

    private String dial(JarvisContactMatch.Contact c) {
        String clean = c.number.replaceAll("[^0-9+]", "");
        String say = JarvisContactMatch.speakable(c.name);
        try {
            boolean direct = granted("android.permission.CALL_PHONE");
            Intent i = new Intent(direct ? Intent.ACTION_CALL : Intent.ACTION_DIAL, Uri.parse("tel:" + clean));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
            return direct ? say + " ko call kar raha hoon." : say + " ka number dialer me khol diya.";
        } catch (Exception e) {
            return "Call nahi lag paya: " + e.getMessage();
        }
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
