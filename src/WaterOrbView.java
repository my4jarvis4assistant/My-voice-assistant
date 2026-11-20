package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;

/**
 * Home screen bubble ka paani wala orb: chamakdaar gehra neela gola jisme ubhri hui ghumti lakeeren hain
 * (app ke water orb jaisa hi). Hamesha halka behta rehta hai; bolne par (level badhe) zyada lehrata hai.
 * Chhota bitmap CPU se banta hai (lookup-table sin), isliye bubble me bhi koi shader/GPU ki zaroorat nahi.
 */
public class WaterOrbView extends View {
    private static final int S = 84;                     // bitmap ka size (chhota rakha taaki tez chale)
    private static final int TN = 4096;
    private static final float[] SIN = new float[TN];

    static {
        for (int i = 0; i < TN; i++) {
            SIN[i] = (float) Math.sin(i * 2.0 * Math.PI / TN);
        }
    }

    private static float sin(float x) {
        float k = x * (TN / 6.2831853f);
        int i = (int) Math.floor(k);
        float f = k - i;
        int a = i & (TN - 1);
        return SIN[a] + (SIN[(a + 1) & (TN - 1)] - SIN[a]) * f;
    }

    private static float cos(float x) {
        return sin(x + 1.5707963f);
    }

    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final Bitmap bmp = Bitmap.createBitmap(S, S, Bitmap.Config.ARGB_8888);
    private final int[] px = new int[S * S];
    private final RectF dst = new RectF();
    private final long t0 = System.nanoTime();
    private long last = 0L;
    private float level = 0f;
    private float shown = 0f;
    private float time = 0f;
    private boolean active = false;

    public WaterOrbView(Context c) {
        super(c);
    }

    public void setLevel(float l) {
        level = Math.max(0f, Math.min(1f, l));
    }

    public void setActive(boolean a) {
        active = a;
    }

    private static float hf(float ux, float uy, float cy, float sy, float ct, float st, float ca, float sna,
                            float t, float spd, float sa) {
        float z = (float) Math.sqrt(Math.max(0f, 1f - (ux * ux + uy * uy)));
        float x1 = ux * cy + z * sy;
        float z1 = -ux * sy + z * cy;
        float y2 = uy * ct - z1 * st;
        float z2 = uy * st + z1 * ct;
        float ph = 9f * (y2 * ca + x1 * sna) + 2.4f * sin(2.3f * x1 + t * 0.9f)
                + 1.8f * sin(2.0f * z2 - t * 0.7f) + spd;
        return sa * (0.5f + 0.5f * sin(ph));
    }

    private static float clamp(float v, float a, float b) {
        return v < a ? a : (v > b ? b : v);
    }

    private void render(float t, float lvl) {
        float amp = 0.6f + 1.3f * lvl;
        float yaw = 0.9f * sin(t * 0.45f) + 0.15f * t;
        float tilt = 0.35f + 0.25f * sin(t * 0.31f);
        float a = 0.55f + 0.6f * sin(t * 0.37f);
        float sa = (0.55f + 0.45f * (0.5f + 0.5f * sin(t * 0.62f - 1.3f))) * (0.9f + 0.6f * lvl);
        float cy = cos(yaw), sy = sin(yaw), ct = cos(tilt), st = sin(tilt), ca = cos(a), sna = sin(a);
        float spd = t * (1f + 1.2f * lvl);
        float e = 0.012f;
        float lx = -0.45f, ly = 0.62f, lz = 0.64f;
        float ll = (float) Math.sqrt(lx * lx + ly * ly + lz * lz);
        lx /= ll;
        ly /= ll;
        lz /= ll;
        float hx0 = lx, hy0 = ly, hz0 = lz + 1f;
        float hl = (float) Math.sqrt(hx0 * hx0 + hy0 * hy0 + hz0 * hz0);
        hx0 /= hl;
        hy0 /= hl;
        hz0 /= hl;
        for (int j = 0; j < S; j++) {
            float uvy = -((j + 0.5f) / S * 2f - 1f);
            for (int i = 0; i < S; i++) {
                float uvx = (i + 0.5f) / S * 2f - 1f;
                float ang = (float) Math.atan2(uvy, uvx + 0.00001f);
                float lump = 1f + amp * (0.040f * sin(3f * ang + t * 0.9f) + 0.030f * sin(2f * ang - t * 0.7f + 1f)
                        + 0.022f * sin(5f * ang + t * 1.4f));
                float R = 0.74f * lump * (1f + 0.05f * lvl);
                float ux = uvx / R, uy = uvy / R;
                float ru = (float) Math.sqrt(ux * ux + uy * uy);
                if (ru > 1.08f) {
                    px[j * S + i] = 0;
                    continue;
                }
                float hx = (hf(ux + e, uy, cy, sy, ct, st, ca, sna, t, spd, sa)
                        - hf(ux - e, uy, cy, sy, ct, st, ca, sna, t, spd, sa)) / (2f * e);
                float hy = (hf(ux, uy + e, cy, sy, ct, st, ca, sna, t, spd, sa)
                        - hf(ux, uy - e, cy, sy, ct, st, ca, sna, t, spd, sa)) / (2f * e);
                float h = hf(ux, uy, cy, sy, ct, st, ca, sna, t, spd, sa);
                float z = (float) Math.sqrt(clamp(1f - ru * ru, 0f, 1f)) + 0.0001f;
                float nx = ux - 0.42f * hx, ny = uy - 0.42f * hy, nz = z;
                float nl = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
                nx /= nl;
                ny /= nl;
                nz /= nl;
                float diff = clamp(nx * lx + ny * ly + nz * lz, 0f, 1f);
                float sp = clamp(nx * hx0 + ny * hy0 + nz * hz0, 0f, 1f);
                float s2 = sp * sp;
                float s4 = s2 * s2;
                float s8 = s4 * s4;
                float spec = s8 * s8 * s8 * s8 * s8;        // sp^40
                float inv = 1f - clamp(nz, 0f, 1f);
                float fres = inv * inv * (float) Math.sqrt(inv);
                float hl2 = clamp(diff - 0.55f, 0f, 1f);
                float lite = hl2 * (float) Math.sqrt(hl2) * 0.9f;
                float val = 1f - h;
                float k = 0.72f + 0.28f * (1f - val);
                float vio = val * 0.10f * (1f - diff);
                float r = (0.01f + (0.14f - 0.01f) * diff + 0.52f * lite) * k + 0.30f * vio + spec * 0.55f + 0.52f * fres * 0.25f;
                float g = (0.04f + (0.26f - 0.04f) * diff + 0.66f * lite) * k + 0.08f * vio + spec * 0.55f + 0.66f * fres * 0.25f;
                float b = (0.62f + (0.93f - 0.62f) * diff + 1.00f * lite) * k + 0.55f * vio + spec * 0.55f + 1.00f * fres * 0.25f;
                float al = clamp((1f - ru) / 0.05f, 0f, 1f);
                int ir = (int) (clamp(r, 0f, 1f) * 255f);
                int ig = (int) (clamp(g, 0f, 1f) * 255f);
                int ib = (int) (clamp(b, 0f, 1f) * 255f);
                int ia = (int) (al * 255f);
                px[j * S + i] = (ia << 24) | (ir << 16) | (ig << 8) | ib;
            }
        }
        bmp.setPixels(px, 0, S, 0, 0, S, S);
    }

    @Override
    protected void onDraw(Canvas c) {
        long now = System.nanoTime();
        float dt = last == 0L ? 0.04f : Math.min(0.1f, (now - last) / 1e9f);
        last = now;
        float target = active ? level : 0f;
        shown += (target - shown) * Math.min(1f, dt * (target > shown ? 16f : 5.5f));
        time += dt * (1f + 0.6f * shown);
        if (time > 3000f) {
            time -= 3000f;
        }
        render(time, shown);
        float w = getWidth(), h = getHeight();
        float s = Math.min(w, h);
        dst.set((w - s) / 2f, (h - s) / 2f, (w + s) / 2f, (h + s) / 2f);
        c.drawBitmap(bmp, null, dst, paint);
        postInvalidateDelayed(40);
    }
}
