"""Jarvis ke orb: 5 rang ke dots wale gole (ghoomta hua sphere jo bikharta aur simatta hai)
aur ek paani jaisa neela gola. Sirf Kivy canvas (Point / Mesh / Line / Ellipse): koi shader nahi,
isliye phone par kabhi nahi atkta. Interface SimpleOrb jaisa hi hai: mode, speaking, paused, stop()."""

import math
import random
import time

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Mesh, Point, Rectangle, RenderContext
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget

# (naam jo settings me dikhega, style)
ORB_CHOICES = [("Neela", "blue"), ("Laal", "red"), ("Sunehra", "gold"),
               ("Hara", "green"), ("Jamuni", "purple"), ("Paani", "water")]

PALETTE = {
    "blue": (0.30, 0.42, 1.00),
    "red": (1.00, 0.24, 0.20),
    "gold": (1.00, 0.76, 0.18),
    "green": (0.16, 0.95, 0.52),
    "purple": (0.70, 0.40, 1.00),
}


def style_name(style):
    for name, st in ORB_CHOICES:
        if st == style:
            return name
    return "Neela"


class _OrbBase(ButtonBehavior, Widget):
    FPS = 30.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "idle"
        self.speaking = False
        self.paused = False
        self._ticks = 0
        self._t = 0.0
        self._lvl = 0.0
        self._ext = 0.0          # asli awaaz ka level (mic ya Jarvis ki awaaz se)
        self._ext_t = 0.0
        self._ext_seen = False

    def feed(self, level):
        """Asli awaaz ka level 0..1 (kisi bhi thread se bulao). Bolte waqt har ~50ms me bhejo."""
        try:
            self._ext = max(0.0, min(1.0, float(level)))
            self._ext_t = time.time()
            self._ext_seen = True
        except Exception:
            pass

    def _start(self):
        self.bind(pos=self._tick, size=self._tick)
        self._ev = Clock.schedule_interval(self._tick, 1.0 / self.FPS)

    def stop(self):
        try:
            self._ev.cancel()
        except Exception:
            pass

    def _advance(self, dt):
        """Samay aage badhao aur 'level' (0 shaant ... 1 zor se bolna) nikalo.
        Asli awaaz ka level mile to wahi; na mile to bolne ka natural utaar-chadhav."""
        self._t += dt
        if dt > 0:
            self._ticks += 1
        t = self._t
        if time.time() - self._ext_t < 0.4:
            target = self._ext                           # asli awaaz: zor se bolo to zyada
        elif self.speaking:
            burst = abs(math.sin(t * 5.3)) * (0.55 + 0.45 * math.sin(t * 1.3 + 0.7))
            target = 0.25 + 0.55 * burst + 0.12 * math.sin(t * 9.1)
        elif self.mode == "listening" and not self._ext_seen:
            target = 0.0 if isinstance(self, ParticleOrb) else 0.35 + 0.1 * math.sin(t * 2.2)
        elif self.mode == "thinking":
            target = 0.0 if isinstance(self, ParticleOrb) else 0.30 + 0.10 * math.sin(t * 4.2)
        else:
            target = 0.0
        target = max(0.0, min(1.0, target))
        k = 16.0 if target > self._lvl else 5.5          # tezi se bikhro, araam se simto
        self._lvl += (target - self._lvl) * min(1.0, dt * k)
        if self._lvl < 0.003 and target == 0.0:
            self._lvl = 0.0
        return t


def _dot_texture():
    """Chhota gol, naram kinaare wala dot (Kivy ka Point warna chorus dikhta hai)."""
    try:
        from kivy.graphics.texture import Texture
        n = 16
        buf = bytearray()
        for yy in range(n):
            for xx in range(n):
                d = math.hypot(xx - 7.5, yy - 7.5) / 7.8
                a = max(0.0, min(1.0, (1.0 - d) * 2.4))
                buf += bytes((255, 255, 255, int(255 * a)))
        tex = Texture.create(size=(n, n), colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = "linear"
        tex.min_filter = "linear"
        return tex
    except Exception:
        return None


def grid_points():
    """Reference jaisa lat-long grid: har ring me barabar dots, isliye upar-neeche ghane
    gol rings banti hain aur beech me seedhi line."""
    rows = [math.radians(-78 + 156.0 * i / 22.0) for i in range(23)]
    for extra in (82.0, 85.0, 87.5, 89.0):
        rows.append(math.radians(extra))
        rows.append(math.radians(-extra))
    pts = []
    for lat in rows:
        n = 36
        for j in range(n):
            lon = 2.0 * math.pi * j / n + (0.0 if abs(lat) < 1.4 else 0.09 * abs(lat))
            pts.append((math.cos(lat) * math.cos(lon), math.sin(lat), math.cos(lat) * math.sin(lon)))
    for j in range(60):                      # equator ki line thodi ghani
        lon = 2.0 * math.pi * (j + 0.5) / 60
        pts.append((math.cos(lon), 0.0, math.sin(lon)))
    return pts


class ParticleOrb(_OrbBase):
    """Dots ka gola. Shaant me sirf left-right ghoomta hai (dots jame rehte hain).
    Jab aap bolo ya Jarvis bole tab thoda bada hokar dots bikharte aur simatte hain."""

    def __init__(self, color="blue", **kwargs):
        super().__init__(**kwargs)
        self._rgb = PALETTE.get(color, PALETTE["blue"])
        rnd = random.Random(7)
        self._sph = grid_points()
        n = len(self._sph)
        self._cloud, self._ph = [], []
        for (sx, sy, sz) in self._sph:
            f = 0.64 + 0.56 * (rnd.random() ** 0.8)
            pull = 0.10 + 0.45 * (rnd.random() ** 2)      # dots upar/neeche ke paas jhund banate hain
            ty = sy + ((1.0 if sy >= 0 else -1.0) * 0.92 - sy) * pull
            k = math.sqrt(max(0.0, 1.0 - ty * ty)) / max(0.05, math.sqrt(sx * sx + sz * sz))
            jx = (rnd.random() - 0.5) * 0.34
            jy = (rnd.random() - 0.5) * 0.26
            jz = (rnd.random() - 0.5) * 0.34
            self._cloud.append(((sx * k) * f + jx, ty * f + jy, (sz * k) * f + jz))
            self._ph.append(rnd.random() * 6.283185)
        r0, g0, b0 = self._rgb
        light = (r0 + (1 - r0) * 0.35, g0 + (1 - g0) * 0.35, b0 + (1 - b0) * 0.35)
        tex = _dot_texture()

        def build(kw):
            self.canvas.clear()
            with self.canvas:
                Color(r0, g0, b0, 0.40)
                self._back = Point(points=[], pointsize=1.2, **kw)
                Color(r0, g0, b0, 0.78)
                self._mid = Point(points=[], pointsize=1.4, **kw)
                Color(light[0], light[1], light[2], 1.0)
                self._front = Point(points=[], pointsize=1.6, **kw)
        try:
            build({"texture": tex} if tex is not None else {})
        except Exception:
            build({})                      # gol dot texture na chale to bhi orb chalega
        self._m = 0.0
        self._start()

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0
        elif self.paused:
            return
        t = self._advance(dt)
        lvl = self._lvl
        # bikhrav seedha awaaz ke level ke hisaab se: zor se bolo to zyada, dheere bolo to kam, chup to bilkul nahi
        target = min(1.0, lvl * 1.30)
        k = 14.0 if target > self._m else 5.0
        self._m += (target - self._m) * min(1.0, dt * k)
        m = self._m if self._m > 0.006 else 0.0
        yaw = 0.75 * math.sin(t * 0.55) + 0.25 * math.sin(t * 0.21 + 1.0)
        tilt = 0.20 + 0.05 * math.sin(t * 0.37)
        cx, cy = self.center
        R = min(self.width, self.height) * 0.36 * (1.0 + 0.012 * math.sin(t * 1.3) + 0.12 * min(1.0, lvl))
        ps = max(0.9, R * 0.0062)
        cy_a, sy_a = math.cos(yaw), math.sin(yaw)
        ct, st = math.cos(tilt), math.sin(tilt)
        back, mid, front = [], [], []
        sph, cloud, ph = self._sph, self._cloud, self._ph
        for i in range(len(sph)):
            sx, sy, sz = sph[i]
            if m:
                mi = m * (0.80 + 0.20 * math.sin(t * 2.1 + ph[i]))
                qx, qy, qz = cloud[i]
                k = 1.0 - mi
                x = sx * k + qx * mi
                y = sy * k + qy * mi
                z = sz * k + qz * mi
            else:
                x, y, z = sx, sy, sz
            x2 = x * cy_a + z * sy_a
            z2 = -x * sy_a + z * cy_a
            y3 = y * ct - z2 * st
            z3 = y * st + z2 * ct
            px = cx + x2 * R
            py = cy + y3 * R
            if z3 > 0.3:
                front.append(px)
                front.append(py)
            elif z3 > -0.3:
                mid.append(px)
                mid.append(py)
            else:
                back.append(px)
                back.append(py)
        self._back.points = back
        self._mid.points = mid
        self._front.points = front
        self._back.pointsize = ps * 0.85
        self._mid.pointsize = ps
        self._front.pointsize = ps * 1.15


class WaterOrb(_OrbBase):
    """Paani jaisa neela gola: lehrata hua, chamakdaar. Bolte/sunte waqt zyada lehrata hai."""
    POINTS = 40
    # (size, dx, dy, (r, g, b, a)): pehle gehra bada, phir upar-baayen taraf halke chhote parat
    LAYERS = ((1.00, 0.00, 0.00, (0.02, 0.05, 0.40, 1.0)),
              (0.95, -0.02, 0.03, (0.04, 0.11, 0.62, 0.95)),
              (0.86, -0.05, 0.06, (0.08, 0.20, 0.84, 0.90)),
              (0.74, -0.09, 0.11, (0.15, 0.34, 0.96, 0.85)),
              (0.60, -0.13, 0.16, (0.26, 0.50, 1.00, 0.80)),
              (0.46, -0.17, 0.21, (0.45, 0.68, 1.00, 0.75)),
              (0.32, -0.21, 0.26, (0.66, 0.84, 1.00, 0.70)),
              (0.18, -0.25, 0.30, (0.88, 0.95, 1.00, 0.70)))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        n = self.POINTS
        self._idx = list(range(n + 2))
        with self.canvas:
            self._glow_c = Color(0.25, 0.45, 1.0, 0.10)
            self._glow = Ellipse()
            self._glow2_c = Color(0.25, 0.45, 1.0, 0.07)
            self._glow2 = Ellipse()
            self._meshes = []
            for (_s, _dx, _dy, rgba) in self.LAYERS:
                Color(*rgba)
                mesh = Mesh(vertices=[0.0, 0.0, 0.0, 0.0] * (n + 2), indices=self._idx, mode="triangle_fan")
                self._meshes.append(mesh)
            self._band_c = Color(0.72, 0.85, 1.0, 0.28)
            self._bands = [Line(points=[0, 0, 0, 0], width=dp(1.6)) for _ in range(3)]
        self._start()

    @staticmethod
    def _wob(a, t, sp, amp, ph):
        return 1.0 + amp * (math.sin(3 * a + t * sp * 1.1 + ph)
                            + 0.75 * math.sin(2 * a - t * sp * 1.7 + ph * 1.3)
                            + 0.45 * math.sin(5 * a + t * sp * 2.3 - ph))

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0
        elif self.paused:
            return
        t = self._advance(dt)
        lvl = self._lvl
        cx, cy = self.center
        R = min(self.width, self.height) * 0.34 * (1.0 + 0.04 * math.sin(t * 1.3) + 0.07 * lvl)
        amp = 0.022 + 0.045 * lvl
        sp = 0.9 + 1.4 * lvl
        n = self.POINTS
        for li, (size, dx, dy, _rgba) in enumerate(self.LAYERS):
            ox = cx + dx * R
            oy = cy + dy * R
            verts = [ox, oy, 0.0, 0.0]
            rr0 = R * size
            for i in range(n + 1):
                a = i * 2.0 * math.pi / n
                rr = rr0 * self._wob(a, t, sp, amp * (0.6 + 0.4 * size), li * 0.9)
                verts.extend((ox + rr * math.cos(a), oy + rr * math.sin(a), 0.0, 0.0))
            self._meshes[li].vertices = verts
        # paani ki dhaariyan
        rot = 0.45 * math.sin(t * 0.45 * sp) - 0.3
        cr, sr = math.cos(rot), math.sin(rot)
        for bi, line in enumerate(self._bands):
            yy = (-0.45 + 0.42 * bi) + 0.05 * math.sin(t * sp * 1.3 + bi * 1.7)
            half = 0.80 - 0.10 * abs(bi - 1)
            pts = []
            for j in range(13):
                u = -half + 2 * half * j / 12.0
                v = yy - 0.16 * (1 - (u / half) ** 2) * 0.9
                x = u * cr - v * sr
                y = u * sr + v * cr
                pts.extend((cx + x * R * 0.92, cy + y * R * 0.92))
            line.points = pts
        self._band_c.a = 0.22 + 0.12 * lvl
        g = R * (2.5 + 0.2 * lvl)
        self._glow.size = (g, g)
        self._glow.pos = (cx - g / 2, cy - g / 2)
        g2 = R * 3.1
        self._glow2.size = (g2, g2)
        self._glow2.pos = (cx - g2 / 2, cy - g2 / 2)
        self._glow_c.a = 0.10 + 0.07 * lvl
        self._glow2_c.a = 0.06 + 0.05 * lvl


WATER_FRAG = """$HEADER$
uniform float time;
uniform float lvl;

float hf(vec2 u, float cy, float sy, float ct, float st, float ca, float sna,
         float t, float spd, float sa) {
    float z = sqrt(max(0.0, 1.0 - dot(u, u)));
    float x1 = u.x * cy + z * sy;
    float z1 = -u.x * sy + z * cy;
    float y2 = u.y * ct - z1 * st;
    float z2 = u.y * st + z1 * ct;
    float ph = 9.0 * (y2 * ca + x1 * sna) + 2.4 * sin(2.3 * x1 + t * 0.9)
             + 1.8 * sin(2.0 * z2 - t * 0.7) + spd;
    return sa * (0.5 + 0.5 * sin(ph));
}

void main(void) {
    vec2 uv = tex_coord0 * 2.0 - 1.0;
    float t = time;
    float ang = atan(uv.y, uv.x + 0.00001);
    float amp = 0.6 + 1.3 * lvl;
    float lump = 1.0 + amp * (0.040 * sin(3.0 * ang + t * 0.9)
                            + 0.030 * sin(2.0 * ang - t * 0.7 + 1.0)
                            + 0.022 * sin(5.0 * ang + t * 1.4));
    float R = 0.74 * lump * (1.0 + 0.05 * lvl);
    vec2 u = uv / R;
    float ru = length(u);
    if (ru > 1.08) {
        gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
        return;
    }
    float yaw = 0.9 * sin(t * 0.45) + 0.15 * t;
    float tilt = 0.35 + 0.25 * sin(t * 0.31);
    float a = 0.55 + 0.6 * sin(t * 0.37);
    float sa = (0.55 + 0.45 * (0.5 + 0.5 * sin(t * 0.62 - 1.3))) * (0.9 + 0.6 * lvl);
    float cy = cos(yaw);
    float sy = sin(yaw);
    float ct = cos(tilt);
    float st = sin(tilt);
    float ca = cos(a);
    float sna = sin(a);
    float spd = t * (1.0 + 1.2 * lvl);
    float e = 0.012;
    float hx = (hf(u + vec2(e, 0.0), cy, sy, ct, st, ca, sna, t, spd, sa)
              - hf(u - vec2(e, 0.0), cy, sy, ct, st, ca, sna, t, spd, sa)) / (2.0 * e);
    float hy = (hf(u + vec2(0.0, e), cy, sy, ct, st, ca, sna, t, spd, sa)
              - hf(u - vec2(0.0, e), cy, sy, ct, st, ca, sna, t, spd, sa)) / (2.0 * e);
    float h = hf(u, cy, sy, ct, st, ca, sna, t, spd, sa);
    float z = sqrt(clamp(1.0 - ru * ru, 0.0, 1.0));
    vec3 n = normalize(vec3(u.x - 0.42 * hx, u.y - 0.42 * hy, z + 0.0001));
    vec3 L = normalize(vec3(-0.45, 0.62, 0.64));
    vec3 Hh = normalize(L + vec3(0.0, 0.0, 1.0));
    float diff = clamp(dot(n, L), 0.0, 1.0);
    float spec = pow(clamp(dot(n, Hh), 0.0, 1.0), 40.0);
    float fres = pow(1.0 - clamp(n.z, 0.0, 1.0), 2.2);
    vec3 navy = vec3(0.01, 0.04, 0.62);
    vec3 royal = vec3(0.14, 0.26, 0.93);
    vec3 lite = vec3(0.52, 0.66, 1.0);
    vec3 col = mix(navy, royal, diff);
    col += lite * pow(clamp(diff - 0.55, 0.0, 1.0), 1.5) * 0.9;
    float val = 1.0 - h;
    col = col * (0.72 + 0.28 * (1.0 - val)) + vec3(0.30, 0.08, 0.55) * (val * 0.10 * (1.0 - diff));
    col += vec3(spec * 0.55) + fres * lite * 0.25;
    float alpha = clamp((1.0 - ru) / 0.05, 0.0, 1.0);
    gl_FragColor = vec4(clamp(col, 0.0, 1.0), alpha);
}
"""


class WaterGLOrb(_OrbBase):
    """Paani/chamakdaar neela gola (reference jaisa): ubhri hui ghumti lakeeren, lehrata kinara.
    GPU shader se banta hai. Shader na chale to make_orb_for purana WaterOrb de deta hai."""

    def __init__(self, **kwargs):
        try:
            self.canvas = RenderContext(use_parent_projection=True, use_parent_modelview=True,
                                        use_parent_frag_modelview=True)
        except TypeError:
            self.canvas = RenderContext(use_parent_projection=True, use_parent_modelview=True)
        self.canvas.shader.fs = WATER_FRAG
        if hasattr(self.canvas.shader, "success") and not self.canvas.shader.success:
            raise RuntimeError("water shader compile nahi hua")
        super().__init__(**kwargs)
        self._time = 0.0
        with self.canvas:
            Color(1, 1, 1, 1)
            self._quad = Rectangle(pos=self.pos, size=self.size)
        self.canvas["time"] = 0.0
        self.canvas["lvl"] = 0.0
        self._start()

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0
        elif self.paused:
            return
        self._advance(dt)
        lvl = self._lvl
        self._time += dt * (1.0 + 0.6 * lvl)
        if self._time > 3000.0:
            self._time -= 3000.0
        q = min(self.width, self.height) * 0.98
        cx, cy = self.center
        self._quad.size = (q, q)
        self._quad.pos = (cx - q / 2, cy - q / 2)
        self.canvas["time"] = float(self._time)
        self.canvas["lvl"] = float(lvl)


def make_orb_for(style, **kwargs):
    if style == "water":
        try:
            return WaterGLOrb(**kwargs)
        except Exception as exc:
            print("WaterGLOrb nahi chala, purana paani wala orb:", exc)
        return WaterOrb(**kwargs)
    return ParticleOrb(style if style in PALETTE else "blue", **kwargs)
