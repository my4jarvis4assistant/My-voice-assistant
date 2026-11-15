package org.myassistant.myvoiceassistant;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.view.View;

/**
 * Home screen ka bubble: paani jaisa neela gola. Hamesha halka behta rehta hai (sone par bhi);
 * jab Jarvis sun raha / bol raha ho (level badhe) to zyada lehrata hai aur chamakta hai.
 */
public class WaterOrbView extends View {
    private static final int POINTS = 44;

    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint glowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint band = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint spec = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path blob = new Path();
    private final RectF oval = new RectF();
    private final long t0 = System.nanoTime();
    private float level = 0f;
    private float shown = 0f;
    private float act = 0f;
    private boolean active = false;

    public WaterOrbView(Context c) {
        super(c);
        band.setStyle(Paint.Style.STROKE);
        band.setStrokeCap(Paint.Cap.ROUND);
    }

    public void setLevel(float l) {
        level = Math.max(0f, Math.min(1f, l));
    }

    public void setActive(boolean a) {
        active = a;
    }

    @Override
    protected void onSizeChanged(int w, int h, int ow, int oh) {
        super.onSizeChanged(w, h, ow, oh);
        float cx = w / 2f;
        float cy = h / 2f;
        float r = Math.min(w, h) / 2f * 0.72f;
        fill.setShader(new RadialGradient(cx - 0.30f * r, cy - 0.34f * r, r * 1.45f,
                new int[]{0xFF9CCBFF, 0xFF3B78FF, 0xFF1230D0, 0xFF060F72},
                new float[]{0f, 0.30f, 0.68f, 1f}, Shader.TileMode.CLAMP));
        glowPaint.setShader(new RadialGradient(cx, cy, Math.min(w, h) / 2f,
                new int[]{0xAA4B86FF, 0x554B86FF, 0x00000000},
                new float[]{0.55f, 0.78f, 1f}, Shader.TileMode.CLAMP));
        spec.setShader(new RadialGradient(cx - 0.34f * r, cy - 0.42f * r, r * 0.34f,
                new int[]{0xCCFFFFFF, 0x00FFFFFF}, null, Shader.TileMode.CLAMP));
    }

    @Override
    protected void onDraw(Canvas c) {
        float t = (System.nanoTime() - t0) / 1e9f;
        shown += (level - shown) * 0.15f;
        act += ((active ? 1f : 0f) - act) * 0.12f;
        float w = getWidth();
        float h = getHeight();
        float cx = w / 2f;
        float cy = h / 2f;
        float r = Math.min(w, h) / 2f * 0.72f;
        float amp = 0.024f + 0.045f * shown + 0.015f * act;
        float sp = 0.9f + 1.4f * shown + 0.5f * act;

        // halka chamak (active par zyada)
        glowPaint.setAlpha((int) (110 + 110 * act + 35 * shown));
        c.drawCircle(cx, cy, Math.min(w, h) / 2f, glowPaint);

        // behta hua gola: radius har kone par thoda upar-neeche
        blob.reset();
        for (int i = 0; i <= POINTS; i++) {
            double a = i * 2 * Math.PI / POINTS;
            float rr = r * (1f + amp * (float) Math.sin(3 * a + t * sp * 1.1)
                    + amp * 0.75f * (float) Math.sin(2 * a - t * sp * 1.7)
                    + amp * 0.45f * (float) Math.sin(5 * a + t * sp * 2.3));
            float x = cx + rr * (float) Math.cos(a);
            float y = cy + rr * (float) Math.sin(a);
            if (i == 0) {
                blob.moveTo(x, y);
            } else {
                blob.lineTo(x, y);
            }
        }
        blob.close();
        c.drawPath(blob, fill);

        // paani ki dhaariyan (gole ke andar hi)
        c.save();
        c.clipPath(blob);
        c.rotate(25f * (float) Math.sin(t * 0.45f * sp) - 18f, cx, cy);
        band.setStrokeWidth(r * 0.085f);
        for (int i = 0; i < 4; i++) {
            float yy = cy + r * (-0.62f + 0.40f * i) + r * 0.07f * (float) Math.sin(t * sp * 1.3 + i * 1.7);
            float half = r * (0.95f - 0.12f * Math.abs(i - 1.5f));
            oval.set(cx - half, yy - r * 0.16f, cx + half, yy + r * 0.16f);
            band.setColor(0xFFB4D8FF);
            band.setAlpha((int) (60 + 40 * shown));
            c.drawArc(oval, 10f, 160f, false, band);
        }
        c.restore();

        // chamak ka dhabba
        c.drawCircle(cx - 0.34f * r, cy - 0.42f * r, r * 0.34f, spec);

        postInvalidateDelayed(40);
    }
}
