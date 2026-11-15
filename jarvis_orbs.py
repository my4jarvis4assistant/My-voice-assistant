"""Jarvis ke orb: 5 rang ke dots wale gole (ghoomta hua sphere jo bikharta aur simatta hai)
aur ek paani jaisa neela gola. Sirf Kivy canvas (Point / Mesh / Line / Ellipse): koi shader nahi,
isliye phone par kabhi nahi atkta. Interface SimpleOrb jaisa hi hai: mode, speaking, paused, stop()."""

import math
import random

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Mesh, Point
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

    def _start(self):
        self.bind(pos=self._tick, size=self._tick)
        self._ev = Clock.schedule_interval(self._tick, 1.0 / self.FPS)

    def stop(self):
        try:
            self._ev.cancel()
        except Exception:
            pass

    def _advance(self, dt):
        """Samay aage badhao aur 'level' (0 shaant ... 1 josh) nikalo."""
        self._t += dt
        if dt > 0:
            self._ticks += 1
        t = self._t
        if self.speaking:
            target = 0.6 + 0.4 * abs(math.sin(t * 4.3))
        elif self.mode in ("listening", "thinking"):
            target = 0.45 + 0.15 * math.sin(t * (4.2 if self.mode == "thinking" else 2.2))
        else:
            target = 0.0
        self._lvl += (target - self._lvl) * min(1.0, dt * 6.0)
        return t


class ParticleOrb(_OrbBase):
    """Dots ka sphere: shaant me dheere ghoomta hai, bolte/sunte waqt bikharta aur simatta hai."""
    COUNT = 520

    def __init__(self, color="blue", **kwargs):
        super().__init__(**kwargs)
        self._rgb = PALETTE.get(color, PALETTE["blue"])
        rnd = random.Random(11)
        self._sph, self._cloud, self._ph = [], [], []
        n = self.COUNT
        for i in range(n):
            y = 1.0 - 2.0 * (i + 0.5) / n
            r = math.sqrt(max(0.0, 1.0 - y * y))
            th = i * 2.399963
            self._sph.append((math.cos(th) * r, y, math.sin(th) * r))
            u = rnd.random() * 2.0 - 1.0
            a = rnd.random() * 6.283185
            s = math.sqrt(max(0.0, 1.0 - u * u))
            rr = 0.15 + 1.1 * (rnd.random() ** 0.7)
            self._cloud.append((s * math.cos(a) * rr, u * rr * 0.95, s * math.sin(a) * rr))
            self._ph.append(rnd.random() * 6.283185)
        r0, g0, b0 = self._rgb
        light = (r0 + (1 - r0) * 0.45, g0 + (1 - g0) * 0.45, b0 + (1 - b0) * 0.45)
        with self.canvas:
            self._glows = []
            for k in range(3):
                c = Color(r0, g0, b0, 0.045)
                e = Ellipse()
                self._glows.append((c, e))
            Color(r0, g0, b0, 0.38)
            self._back = Point(points=[], pointsize=dp(1.0))
            Color(r0, g0, b0, 0.80)
            self._mid = Point(points=[], pointsize=dp(1.4))
            Color(light[0], light[1], light[2], 1.0)
            self._front = Point(points=[], pointsize=dp(1.9))
        self._yaw = 0.0
        self._start()

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0
        elif self.paused:
            return
        t = self._advance(dt)
        lvl = self._lvl
        self._yaw += dt * (0.45 + 1.1 * lvl)
        # bikhrav: shaant me thoda, bolte/sunte waqt zyada (lehron me)
        m = 0.012 + 0.05 * (0.5 + 0.5 * math.sin(t * 0.6)) + 0.62 * lvl * (0.5 + 0.5 * math.sin(t * 1.9))
        m = min(0.85, m)
        cx, cy = self.center
        R = min(self.width, self.height) * 0.38 * (1.0 + 0.03 * math.sin(t * 1.4) + 0.06 * lvl)
        cy_a, sy_a = math.cos(self._yaw), math.sin(self._yaw)
        tilt = 0.38
        ct, st = math.cos(tilt), math.sin(tilt)
        back, mid, front = [], [], []
        sph, cloud, ph = self._sph, self._cloud, self._ph
        for i in range(self.COUNT):
            mi = m + 0.30 * m * math.sin(t * 1.3 + ph[i])
            if mi < 0.0:
                mi = 0.0
            k = 1.0 - mi
            sx, sy, sz = sph[i]
            qx, qy, qz = cloud[i]
            x = sx * k + qx * mi
            y = sy * k + qy * mi
            z = sz * k + qz * mi
            x2 = x * cy_a + z * sy_a
            z2 = -x * sy_a + z * cy_a
            y3 = y * ct - z2 * st
            z3 = y * st + z2 * ct
            px = cx + x2 * R
            py = cy + y3 * R
            if z3 > 0.35:
                front.append(px)
                front.append(py)
            elif z3 > -0.35:
                mid.append(px)
                mid.append(py)
            else:
                back.append(px)
                back.append(py)
        self._back.points = back
        self._mid.points = mid
        self._front.points = front
        for idx, (c, e) in enumerate(self._glows):
            d = R * (2.0 + 0.55 * idx) * (1.0 + 0.08 * lvl)
            e.size = (d, d)
            e.pos = (cx - d / 2, cy - d / 2)
            c.a = (0.05 + 0.04 * lvl) / (1 + idx * 0.6)


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


def make_orb_for(style, **kwargs):
    if style == "water":
        return WaterOrb(**kwargs)
    return ParticleOrb(style if style in PALETTE else "blue", **kwargs)
