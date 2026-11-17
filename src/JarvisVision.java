package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.graphics.SurfaceTexture;
import android.hardware.Camera;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Jarvis ki aankhein: camera se ek photo leta hai aur Gemini se poochta hai ki isme kya hai.
 * Python aur Java dono ise chalate hain: start() turant lautta hai, phir state()/result() dekhte raho.
 */
@SuppressWarnings("deprecation")
public class JarvisVision {
    public static final int IDLE = 0, WORKING = 1, DONE = 2, ERROR = 3;
    private static final String BASE = "https://generativelanguage.googleapis.com/v1beta";
    private static final String[] MODELS = {"gemini-2.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash-lite",
            "gemini-2.0-flash", "gemini-flash-latest"};
    private static volatile int state = IDLE;
    private static volatile String result = "";
    private static volatile boolean busy = false;

    private static final String SYSTEM = "Tum JARVIS ho, Shakshm Jha ke personal voice assistant. Tumhe phone ke camera se "
            + "abhi li gayi ek photo di gayi hai. Photo dekhkar Hinglish (Roman me likhi Hindi) me chhota, saaf aur seedha jawab do "
            + "(zyada se zyada 3 vaakya). Agar user ne kuch poocha hai to sirf usi ka jawab do, warna batao ki kya dikh raha hai. "
            + "Agar photo dhundhli/andhere me ho to saaf bolo. Markdown, bullet ya emoji mat use karo.";

    public static int state() {
        return state;
    }

    public static String result() {
        return result == null ? "" : result;
    }

    public static boolean hasCameraPermission(Context ctx) {
        try {
            return ctx.checkSelfPermission("android.permission.CAMERA") == android.content.pm.PackageManager.PERMISSION_GRANTED;
        } catch (Throwable t) {
            return false;
        }
    }

    /** Photo lo + Gemini se poochho. Jawab ke liye state()/result() dekho. */
    public static synchronized boolean start(final Context ctx, final boolean front, final String question,
                                             final String rawKeys, final String prefModel) {
        if (busy) {
            return false;
        }
        busy = true;
        state = WORKING;
        result = "";
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    byte[] jpg = capture(front);
                    String ans = askGemini(rawKeys, jpg, question, prefModel);
                    if (ans == null || ans.trim().length() == 0) {
                        result = "Photo li par abhi jawab nahi bana paya. Internet ya Gemini limit check karo.";
                        state = ERROR;
                    } else {
                        result = ans.trim();
                        state = DONE;
                    }
                } catch (Throwable t) {
                    String m = String.valueOf(t.getMessage());
                    if (m.contains("permission") || m.contains("Permission") || m.contains("disabled")
                            || m.contains("connect") || m.contains("Fail to connect")) {
                        result = "Camera nahi khul paya. Permission ya background rok ho sakti hai. "
                                + "Jarvis app kholkar camera button dabao.";
                    } else {
                        result = "Camera me dikkat aayi: " + m;
                    }
                    state = ERROR;
                } finally {
                    busy = false;
                }
            }
        }).start();
        return true;
    }

    // ------------------------------------------------------------------ camera --
    private static byte[] capture(boolean front) throws Exception {
        int want = front ? Camera.CameraInfo.CAMERA_FACING_FRONT : Camera.CameraInfo.CAMERA_FACING_BACK;
        int id = -1;
        Camera.CameraInfo info = new Camera.CameraInfo();
        int n = Camera.getNumberOfCameras();
        for (int i = 0; i < n; i++) {
            Camera.getCameraInfo(i, info);
            if (info.facing == want) {
                id = i;
                break;
            }
        }
        if (id < 0) {
            if (n == 0) {
                throw new Exception("is phone me camera nahi mila");
            }
            id = 0;
            Camera.getCameraInfo(0, info);
        }
        Camera cam = Camera.open(id);
        SurfaceTexture st = new SurfaceTexture(10);
        try {
            cam.setPreviewTexture(st);
            Camera.Parameters pr = cam.getParameters();
            try {
                List<String> fm = pr.getSupportedFocusModes();
                if (fm != null && fm.contains(Camera.Parameters.FOCUS_MODE_CONTINUOUS_PICTURE)) {
                    pr.setFocusMode(Camera.Parameters.FOCUS_MODE_CONTINUOUS_PICTURE);
                }
            } catch (Throwable ignored) {
            }
            Camera.Size best = null;
            for (Camera.Size s : pr.getSupportedPictureSizes()) {
                long px = (long) s.width * s.height;
                if (px <= 2500000L && (best == null || px > (long) best.width * best.height)) {
                    best = s;
                }
            }
            if (best != null) {
                pr.setPictureSize(best.width, best.height);
            }
            pr.setJpegQuality(88);
            cam.setParameters(pr);
            try {
                cam.enableShutterSound(false);
            } catch (Throwable ignored) {
            }
            cam.startPreview();
            Thread.sleep(1500);                       // focus aur roshni set hone do
            final CountDownLatch latch = new CountDownLatch(1);
            final byte[][] out = new byte[1][];
            cam.takePicture(null, null, new Camera.PictureCallback() {
                @Override
                public void onPictureTaken(byte[] data, Camera c) {
                    out[0] = data;
                    latch.countDown();
                }
            });
            if (!latch.await(8, TimeUnit.SECONDS) || out[0] == null) {
                throw new Exception("photo nahi aayi");
            }
            return prepare(out[0], info.orientation, info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT);
        } finally {
            try {
                cam.stopPreview();
            } catch (Throwable ignored) {
            }
            try {
                cam.release();
            } catch (Throwable ignored) {
            }
            try {
                st.release();
            } catch (Throwable ignored) {
            }
        }
    }

    /** Seedha karo (sensor landscape hota hai) aur chhota karo taaki jaldi upload ho. */
    private static byte[] prepare(byte[] raw, int rot, boolean mirror) {
        BitmapFactory.Options o = new BitmapFactory.Options();
        o.inJustDecodeBounds = true;
        BitmapFactory.decodeByteArray(raw, 0, raw.length, o);
        int sample = 1;
        while (Math.max(o.outWidth, o.outHeight) / sample > 2200) {
            sample *= 2;
        }
        BitmapFactory.Options o2 = new BitmapFactory.Options();
        o2.inSampleSize = sample;
        Bitmap b = BitmapFactory.decodeByteArray(raw, 0, raw.length, o2);
        if (b == null) {
            return raw;
        }
        Matrix m = new Matrix();
        m.postRotate(rot);
        if (mirror) {
            m.postScale(-1f, 1f);
        }
        float sc = 1024f / Math.max(b.getWidth(), b.getHeight());
        if (sc < 1f) {
            m.postScale(sc, sc);
        }
        Bitmap r = Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), m, true);
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        r.compress(Bitmap.CompressFormat.JPEG, 82, bos);
        return bos.toByteArray();
    }

    // ------------------------------------------------------------------ gemini --
    private static String askGemini(String rawKeys, byte[] jpg, String question, String prefModel) throws Exception {
        List<String> keys = new ArrayList<String>();
        for (String k : JarvisBrain.splitKeys(rawKeys)) {
            if (!k.startsWith("gsk_") && !k.startsWith("csk-")) {
                keys.add(k);
            }
        }
        if (keys.isEmpty()) {
            throw new Exception("Gemini key nahi hai (camera ke liye Gemini key chahiye)");
        }
        String q = (question == null || question.trim().length() == 0)
                ? "Is photo me jo dikh raha hai wo batao." : question.trim();
        JSONObject body = new JSONObject();
        body.put("systemInstruction", new JSONObject().put("parts", new JSONArray().put(new JSONObject().put("text", SYSTEM))));
        JSONArray parts = new JSONArray();
        parts.put(new JSONObject().put("inlineData", new JSONObject().put("mimeType", "image/jpeg")
                .put("data", Base64.encodeToString(jpg, Base64.NO_WRAP))));
        parts.put(new JSONObject().put("text", "User ne kaha: " + q));
        body.put("contents", new JSONArray().put(new JSONObject().put("role", "user").put("parts", parts)));
        body.put("generationConfig", new JSONObject().put("maxOutputTokens", 500).put("temperature", 0.4));
        String json = body.toString();
        List<String> models = new ArrayList<String>();
        if (prefModel != null && prefModel.trim().length() > 0) {
            models.add(prefModel.trim());
        }
        for (String m : MODELS) {
            if (!models.contains(m)) {
                models.add(m);
            }
        }
        StringBuilder errs = new StringBuilder();
        String lastErr = "";
        boolean discovered = false;
        for (int mi = 0; mi < models.size(); mi++) {
            String model = models.get(mi);
            boolean skipModel = false;
            for (String key : keys) {
                if (skipModel) {
                    break;
                }
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(BASE + "/models/" + model
                            + ":generateContent").openConnection();
                    try {
                        c.setRequestMethod("POST");
                        c.setConnectTimeout(15000);
                        c.setReadTimeout(45000);
                        c.setDoOutput(true);
                        c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                        c.setRequestProperty("x-goog-api-key", key.trim());
                        OutputStream os = c.getOutputStream();
                        os.write(json.getBytes("UTF-8"));
                        os.flush();
                        os.close();
                        int code = c.getResponseCode();
                        InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream();
                        StringBuilder sb = new StringBuilder();
                        if (in != null) {
                            BufferedReader br = new BufferedReader(new InputStreamReader(in, "UTF-8"));
                            String line;
                            while ((line = br.readLine()) != null) {
                                sb.append(line).append('\n');
                            }
                            br.close();
                        }
                        if (code >= 400) {
                            lastErr = model + " HTTP " + code;
                            if (errs.length() < 160) {
                                errs.append(model).append(':').append(code).append(' ');
                            }
                            if (code == 404 || code == 400) {
                                skipModel = true;       // is model me photo nahi chalti / naam galat: agla model
                            }
                            continue;
                        }
                        JSONObject o = new JSONObject(sb.toString());
                        JSONArray cands = o.optJSONArray("candidates");
                        if (cands == null || cands.length() == 0) {
                            lastErr = "khaali jawab";
                            continue;
                        }
                        JSONArray ps = cands.getJSONObject(0).getJSONObject("content").optJSONArray("parts");
                        StringBuilder t = new StringBuilder();
                        if (ps != null) {
                            for (int i = 0; i < ps.length(); i++) {
                                t.append(ps.getJSONObject(i).optString("text", ""));
                            }
                        }
                        String out = JarvisBrain.clean(t.toString());
                        if (out.length() > 0) {
                            return out;
                        }
                    } finally {
                        c.disconnect();
                    }
                } catch (java.io.IOException e) {
                    lastErr = "internet: " + e.getMessage();
                }
            }
        }
        // Sab model 404 the: Google se is key ke chalne wale flash models ki list mangao aur wo try karo.
        try {
            for (String key : keys) {
                HttpURLConnection c = (HttpURLConnection) new URL(BASE + "/models?pageSize=100").openConnection();
                c.setConnectTimeout(10000);
                c.setReadTimeout(15000);
                c.setRequestProperty("x-goog-api-key", key.trim());
                if (c.getResponseCode() >= 400) {
                    continue;
                }
                BufferedReader br = new BufferedReader(new InputStreamReader(c.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) {
                    sb.append(line);
                }
                br.close();
                JSONArray arr = new JSONObject(sb.toString()).optJSONArray("models");
                List<String> found = new ArrayList<String>();
                if (arr != null) {
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject mo = arr.getJSONObject(i);
                        String nm = mo.optString("name", "").replace("models/", "");
                        String meths = String.valueOf(mo.optJSONArray("supportedGenerationMethods"));
                        if (nm.contains("flash") && meths.contains("generateContent") && !models.contains(nm)
                                && !nm.contains("tts") && !nm.contains("image") && !nm.contains("live")
                                && !nm.contains("audio") && !nm.contains("thinking")) {
                            found.add(nm);
                        }
                    }
                }
                for (int fi = 0; fi < found.size() && fi < 4; fi++) {
                    String out = tryModel(found.get(fi), key, json);
                    if (out != null) {
                        return out;
                    }
                }
                break;
            }
        } catch (Exception e) {
            errs.append("list:").append(e.getMessage());
        }
        lastErr = errs.toString().trim();
        throw new Exception("Gemini se jawab nahi mila (" + lastErr + ")");
    }

    private static String tryModel(String model, String key, String json) {
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(BASE + "/models/" + model + ":generateContent").openConnection();
            try {
                c.setRequestMethod("POST");
                c.setConnectTimeout(15000);
                c.setReadTimeout(45000);
                c.setDoOutput(true);
                c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                c.setRequestProperty("x-goog-api-key", key.trim());
                OutputStream os = c.getOutputStream();
                os.write(json.getBytes("UTF-8"));
                os.close();
                if (c.getResponseCode() >= 400) {
                    return null;
                }
                BufferedReader br = new BufferedReader(new InputStreamReader(c.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) {
                    sb.append(line).append('\n');
                }
                br.close();
                JSONArray cands = new JSONObject(sb.toString()).optJSONArray("candidates");
                if (cands == null || cands.length() == 0) {
                    return null;
                }
                JSONArray ps = cands.getJSONObject(0).getJSONObject("content").optJSONArray("parts");
                StringBuilder t = new StringBuilder();
                if (ps != null) {
                    for (int i = 0; i < ps.length(); i++) {
                        t.append(ps.getJSONObject(i).optString("text", ""));
                    }
                }
                String out = JarvisBrain.clean(t.toString());
                return out.length() > 0 ? out : null;
            } finally {
                c.disconnect();
            }
        } catch (Exception e) {
            return null;
        }
    }

    // ------------------------------------------------------------------ words --
    /** "jarvis dekho", "pichhe kya dikh raha hai", "camera se batao" jaisi baat pehchano. Nahi to null. */
    public static String[] parse(String text) {
        if (text == null) {
            return null;
        }
        String low = " " + text.toLowerCase().replaceAll("[^\\p{L}\\p{N} ]", " ").replaceAll("\\s+", " ").trim() + " ";
        if (low.trim().length() < 4) {
            return null;
        }
        String[] noWords = {" screen ", " skreen ", " display ", " reel", " video", " movie", " film", " series",
                " song ", " gaana", " gana ", " youtube", " instagram", " whatsapp", " status ", " story ", " message",
                " msg ", " notification", " scroll", " click", " type "};
        for (String w : noWords) {
            if (low.contains(w)) {
                return null;
            }
        }
        boolean cam = low.contains(" camera") || low.contains(" kemra") || low.contains(" selfie");
        boolean dikh = low.contains("kya dikh") || low.contains("kya dikhai") || low.contains("kya nazar")
                || low.contains("kya najar") || low.contains("what do you see") || low.contains("look at this")
                || low.contains("kya dekh rahe") || low.contains("kya dekh raha");
        boolean dekho = (low.contains(" dekho") || low.contains(" dekh ") || low.contains(" dekhna ")
                || low.contains(" dekhiye") || low.contains(" see "))
                && (low.contains(" ye ") || low.contains(" yeh ") || low.contains(" is ") || low.contains(" isko ")
                || low.contains(" ise ") || low.contains(" yaha") || low.contains(" yahan") || low.contains(" samne")
                || low.contains(" saamne") || low.contains(" piche") || low.contains(" pichhe") || low.contains(" peeche")
                || low.contains(" kya ") || low.contains(" bata") || low.contains(" haath") || low.contains(" mujhe")
                || low.endsWith(" dekho ") || low.endsWith(" dekh "));
        if (!(cam || dikh || dekho)) {
            return null;
        }
        boolean front = low.contains("selfie") || low.contains("front") || low.contains("mujhe dekho")
                || low.contains("meri taraf") || low.contains("mera chehra") || low.contains("main kaisa")
                || low.contains("mai kaisa") || low.contains("me kaisa") || low.contains("mujhe dikh");
        String q = text.trim().replaceAll("(?i)^(hey |hello |hi )?jarvis[ ,]*", "").trim();
        return new String[]{front ? "front" : "back", q.length() == 0 ? "Jo dikh raha hai wo batao" : q};
    }
}
