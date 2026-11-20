package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.View;

import java.util.Random;

/**
 * Home screen bubble ka dots wala orb (app ke orb jaisa hi). Shaant me sirf left-right ghoomta hai;
 * jab aap bolo ya Jarvis bole to thoda bada hokar dots bikharte aur simatte hain.
 * Hamesha chalta rehta hai (sote waqt bhi), lekin koi awaaz nahi nikalta.
 */
public class DotOrbView extends View {
    private final float[] sx, sy, sz, cx, cy, cz, ph;
    private final int n;
    private final Paint pBack = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint pMid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint pFront = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float[] back, mid, front;
    private final long t0 = System.nanoTime();
    private long last = 0L;
    private float level = 0f;
    private float lvl = 0f;
    private float m = 0f;
    private boolean active = false;
    private final String style;

    public DotOrbView(Context ctx, String style) {
        super(ctx);
        this.style = style;
        int rowsN = 23 + 8;
        int per = 36;
        n = rowsN * per + 60;
        sx = new float[n]; sy = new float[n]; sz = new float[n];
        cx = new float[n]; cy = new float[n]; cz = new float[n];
        ph = new float[n];
        back = new float[n * 2]; mid = new float[n * 2]; front = new float[n * 2];
        double[] rows = new double[rowsN];
        int r = 0;
        for (int i = 0; i < 23; i++) {
            rows[r++] = Math.toRadians(-78 + 156.0 * i / 22.0);
        }
        double[] ex = {82.0, 85.0, 87.5, 89.0};
        for (double e : ex) {
            rows[r++] = Math.toRadians(e);
            rows[r++] = Math.toRadians(-e);
        }
        int k = 0;
        for (double lat : rows) {
            for (int j = 0; j < per; j++) {
                double lon = 2.0 * Math.PI * j / per + (Math.abs(lat) < 1.4 ? 0.0 : 0.09 * Math.abs(lat));
                sx[k] = (float) (Math.cos(lat) * Math.cos(lon));
                sy[k] = (float) Math.sin(lat);
                sz[k] = (float) (Math.cos(lat) * Math.sin(lon));
                k++;
            }
        }
        for (int j = 0; j < 60; j++) {
            double lon = 2.0 * Math.PI * (j + 0.5) / 60;
            sx[k] = (float) Math.cos(lon);
            sy[k] = 0f;
            sz[k] = (float) Math.sin(lon);
            k++;
        }
        Random rnd = new Random(7);
        for (int i = 0; i < n; i++) {
            float f = (float) (0.64 + 0.56 * Math.pow(rnd.nextDouble(), 0.8));
            float pull = (float) (0.10 + 0.45 * Math.pow(rnd.nextDouble(), 2));
            float ty = sy[i] + ((sy[i] >= 0 ? 1f : -1f) * 0.92f - sy[i]) * pull;
            float hz = (float) Math.sqrt(sx[i] * sx[i] + sz[i] * sz[i]);
            float kk = (float) (Math.sqrt(Math.max(0.0, 1.0 - ty * ty)) / Math.max(0.05, hz));
            cx[i] = sx[i] * kk * f + (float) ((rnd.nextDouble() - 0.5) * 0.34);
            cy[i] = ty * f + (float) ((rnd.nextDouble() - 0.5) * 0.26);
            cz[i] = sz[i] * kk * f + (float) ((rnd.nextDouble() - 0.5) * 0.34);
            ph[i] = (float) (rnd.nextDouble() * 6.283185);
        }
        int base = baseColor(style);
        int lightC = Color.rgb(
                Math.min(255, Color.red(base) + (255 - Color.red(base)) * 35 / 100),
                Math.min(255, Color.green(base) + (255 - Color.green(base)) * 35 / 100),
                Math.min(255, Color.blue(base) + (255 - Color.blue(base)) * 35 / 100));
        for (Paint p : new Paint[]{pBack, pMid, pFront}) {
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeCap(Paint.Cap.ROUND);
        }
        pBack.setColor(base);
        pBack.setAlpha(100);
        pMid.setColor(base);
        pMid.setAlpha(200);
        pFront.setColor(lightC);
    }

    private static int baseColor(String s) {
        if ("red".equals(s)) return Color.rgb(255, 61, 51);
        if ("gold".equals(s)) return Color.rgb(255, 194, 46);
        if ("green".equals(s)) return Color.rgb(41, 242, 133);
        if ("purple".equals(s)) return Color.rgb(179, 102, 255);
        return Color.rgb(77, 107, 255);
    }

    public String getStyle() {
        return style;
    }

    public void setLevel(float l) {
        level = l;
    }

    public void setActive(boolean a) {
        active = a;
    }

    @Override
    protected void onDraw(Canvas c) {
        long now = System.nanoTime();
        float dt = last == 0L ? 0.033f : Math.min(0.1f, (now - last) / 1e9f);
        last = now;
        float t = (now - t0) / 1e9f;
        float target = active ? Math.min(1f, level) : 0f;
        lvl += (target - lvl) * Math.min(1f, dt * (target > lvl ? 16f : 5.5f));
        if (lvl < 0.003f && target == 0f) {
            lvl = 0f;
        }
        // bikhrav seedha awaaz ke level ke hisaab se: zor se bolo to zyada, dheere bolo to kam, chup to gol
        float tm = Math.min(1f, lvl * 1.30f);
        m += (tm - m) * Math.min(1f, dt * (tm > m ? 14f : 5f));
        float mm = m > 0.006f ? m : 0f;
        float yaw = (float) (0.75 * Math.sin(t * 0.55) + 0.25 * Math.sin(t * 0.21 + 1.0));
        float tilt = (float) (0.20 + 0.05 * Math.sin(t * 0.37));
        float w = getWidth(), h = getHeight();
        float size = Math.min(w, h);
        float R = size * (0.30f + 0.08f * Math.min(1f, lvl));
        float mx = w / 2f, my = h / 2f;
        float ca = (float) Math.cos(yaw), sa = (float) Math.sin(yaw);
        float ct = (float) Math.cos(tilt), st = (float) Math.sin(tilt);
        int nb = 0, nm = 0, nf = 0;
        for (int i = 0; i < n; i++) {
            float x, y, z;
            if (mm > 0f) {
                float mi = mm * (0.80f + 0.20f * (float) Math.sin(t * 2.1f + ph[i]));
                float k = 1f - mi;
                x = sx[i] * k + cx[i] * mi;
                y = sy[i] * k + cy[i] * mi;
                z = sz[i] * k + cz[i] * mi;
            } else {
                x = sx[i]; y = sy[i]; z = sz[i];
            }
            float x2 = x * ca + z * sa;
            float z2 = -x * sa + z * ca;
            float y3 = y * ct - z2 * st;
            float z3 = y * st + z2 * ct;
            float px = mx + x2 * R;
            float py = my + y3 * R;
            if (z3 > 0.3f) {
                front[nf++] = px; front[nf++] = py;
            } else if (z3 > -0.3f) {
                mid[nm++] = px; mid[nm++] = py;
            } else {
                back[nb++] = px; back[nb++] = py;
            }
        }
        float sw = Math.max(getResources().getDisplayMetrics().density * 1.3f, R * 0.034f);
        pBack.setStrokeWidth(sw * 0.85f);
        pMid.setStrokeWidth(sw);
        pFront.setStrokeWidth(sw * 1.15f);
        c.drawPoints(back, 0, nb, pBack);
        c.drawPoints(mid, 0, nm, pMid);
        c.drawPoints(front, 0, nf, pFront);
        postInvalidateDelayed(40);
    }
}
