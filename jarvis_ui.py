"""JARVIS v0.64 - professional UI module (main.py ke saath kaam karta hai).

main.py ko sirf yahi chahiye:
    from jarvis_ui import build_jarvis_ui
    self.root_layout = build_jarvis_ui(self)

Is file ka contract (main.py yeh cheezein use karta hai, sab yahan set hoti hain):
    app.status_label, app.calc_panel, app.calc_display, app.calc_question_label,
    app.calc_answer_label, app.calc_angle_mode, app.calc_history, app.root_layout

Professional look ke rules jo yahan follow hue hain:
  1. Ek hi colour palette (neeche) - har widget wahi use karta hai
  2. Har size dp()/sp() me, taaki har phone par same dikhe
  3. Kivy ki default grey button/textinput skin hata di gayi hai
  4. Orb, glow aur background gradient TEXTURE hain (flat colour nahi)
  5. Rounded cards + patli border + ek jaisi spacing
"""
import json
import math
import os
import random
import re
import threading

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, Line, Rectangle, RenderContext,
                           RoundedRectangle, StencilPop, StencilPush,
                           StencilUnUse, StencilUse)
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

# ----------------------------------------------------------------- PALETTE --
BG_TOP = (0.050, 0.105, 0.120)
BG_BOTTOM = (0.012, 0.022, 0.026)
PANEL = (0.062, 0.092, 0.100, 1)
INPUT = (0.040, 0.070, 0.076, 1)
PILL = (0.085, 0.125, 0.135, 1)
EDGE = (1, 1, 1, 0.09)
CYAN = (0.30, 0.88, 0.85, 1)
CYAN_12 = (0.30, 0.88, 0.85, 0.12)
CYAN_60 = (0.30, 0.88, 0.85, 0.60)
WHITE = (0.90, 0.95, 0.96, 1)
MUTED = (0.55, 0.66, 0.68, 1)
FAINT = (0.36, 0.48, 0.49, 1)
GREEN = (0.12, 0.95, 0.52, 1)
CLEAR = (0, 0, 0, 0)
DARK_TEXT = (0.02, 0.09, 0.09, 1)

# Voice name -> (TTS pitch, TTS speech rate). Sirf awaaz ka andaaz badalta hai.
ORB_GLOW = 0.30      # orb ke peeche halki teal chamak (0 = bilkul band)

VOICES = {
    "Male Alpha": (0.85, 1.00),
    "Female Beta": (1.25, 1.00),
    "Formal Gamma": (0.95, 0.90),
    "Casual Delta": (1.10, 1.05),
}


# ---------------------------------------------------------------- TEXTURES --
def _make_texture(w, h, pixel_fn, periodic=False):
    """pixel_fn(u, v) -> (r, g, b, a); u, v 0..1 (v neeche se upar).
    periodic=True: texture dono taraf se seamless repeat hota hai."""
    buf = bytearray(w * h * 4)
    i = 0
    for y in range(h):
        v = y / (h if periodic else h - 1)
        for x in range(w):
            r, g, b, a = pixel_fn(x / (w if periodic else w - 1), v)
            buf[i] = int(255 * min(1.0, max(0.0, r)))
            buf[i + 1] = int(255 * min(1.0, max(0.0, g)))
            buf[i + 2] = int(255 * min(1.0, max(0.0, b)))
            buf[i + 3] = int(255 * min(1.0, max(0.0, a)))
            i += 4
    tex = Texture.create(size=(w, h), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.mag_filter = "linear"
    tex.min_filter = "linear"
    if periodic:
        tex.wrap = "repeat"
    return tex


SKY_STOPS = [   # (upar se kitna neeche 0..1, rang) - ChatGPT ke orb se naape gaye
    (0.00, (0.275, 0.467, 0.910)),
    (0.10, (0.302, 0.498, 0.922)),
    (0.19, (0.357, 0.541, 0.933)),
    (0.28, (0.471, 0.631, 0.945)),
    (0.375, (0.616, 0.729, 0.961)),
    (0.466, (0.741, 0.824, 0.969)),
    (0.557, (0.850, 0.890, 0.975)),
    (0.648, (0.830, 0.885, 0.972)),
    (0.739, (0.760, 0.824, 0.973)),
    (0.83, (0.710, 0.784, 0.968)),
    (1.00, (0.698, 0.769, 0.965)),
]


def sky_pixel(u, v):
    """ChatGPT jaisa aasmaan: upar gehra neela, beech safed, neeche halka lavender."""
    t = 1.0 - v
    for i in range(len(SKY_STOPS) - 1):
        t0, c0 = SKY_STOPS[i]
        t1, c1 = SKY_STOPS[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            f = max(0.0, min(1.0, f))
            return (c0[0] + (c1[0] - c0[0]) * f, c0[1] + (c1[1] - c0[1]) * f,
                    c0[2] + (c1[2] - c0[2]) * f, 1.0)
    return SKY_STOPS[-1][1] + (1.0,)


def _smooth(x):
    return x * x * (3 - 2 * x)


def _sstep(lo, hi, x):
    f = max(0.0, min(1.0, (x - lo) / (hi - lo)))
    return f * f * (3 - 2 * f)


def make_cloud_pixel_fn():
    """Seamless (tile hone wala) baadal. Alpha = baadal ki ghani-ta, beech ki patti me zyada."""
    rnd = random.Random(11)
    octaves = [(4, 4, 1.0), (8, 8, 0.55), (16, 16, 0.30)]
    grids = [[rnd.random() for _ in range(gx * gy)] for gx, gy, _ in octaves]
    total = sum(o[2] for o in octaves)

    def noise(u, v):
        acc = 0.0
        for (gx, gy, amp), g in zip(octaves, grids):
            x, y = u * gx, v * gy
            xi, yi = int(x), int(y)
            fx, fy = _smooth(x - xi), _smooth(y - yi)
            x0, x1 = xi % gx, (xi + 1) % gx
            y0, y1 = yi % gy, (yi + 1) % gy
            a, b = g[y0 * gx + x0], g[y0 * gx + x1]
            c, d = g[y1 * gx + x0], g[y1 * gx + x1]
            top = a + (b - a) * fx
            bot = c + (d - c) * fx
            acc += amp * (top + (bot - top) * fy)
        return acc / total

    def px(u, v):
        density = _sstep(0.42, 0.72, noise(u, v))
        band = math.exp(-((v - 0.46) / 0.17) ** 2)
        return 0.97, 0.985, 1.0, density * band

    return px


def glow_pixel(u, v):
    d = math.hypot((u - 0.5) * 2, (v - 0.5) * 2)
    if d >= 1:
        a = 0.0
    elif d < 0.55:
        a = 0.50
    else:
        a = (1 - (d - 0.55) / 0.45) ** 2.4 * 0.50
    return 0.18, 0.85, 0.90, a


def blob_pixel(u, v):
    """Naram gol dhabba (beech me saaf, kinaare par gayab) - Safe orb ke behte baadal."""
    d = min(1.0, math.hypot((u - 0.5) * 2, (v - 0.5) * 2))
    a = (1 - d * d) ** 1.6
    return 1.0, 1.0, 1.0, a


def bg_pixel(u, v):
    return (BG_BOTTOM[0] + (BG_TOP[0] - BG_BOTTOM[0]) * v,
            BG_BOTTOM[1] + (BG_TOP[1] - BG_BOTTOM[1]) * v,
            BG_BOTTOM[2] + (BG_TOP[2] - BG_BOTTOM[2]) * v, 1)


_TEX = {}


def get_texture(name):
    if name not in _TEX:
        if name == "sky":
            _TEX[name] = _make_texture(2, 128, sky_pixel)
        elif name == "cloud":
            _TEX[name] = _make_texture(128, 128, make_cloud_pixel_fn(), periodic=True)
        elif name == "glow":
            _TEX[name] = _make_texture(64, 64, glow_pixel)
        elif name == "blob":
            _TEX[name] = _make_texture(64, 64, blob_pixel)
        else:
            _TEX[name] = _make_texture(2, 64, bg_pixel)
    return _TEX[name]


# ----------------------------------------------------------------- HELPERS --
def make_label(text, size=14, color=WHITE, bold=False, align="left",
               height=None, lines=1):
    """Left/center aligned label. height dene par fixed-height ban jata hai."""
    kw = {}
    if height is not None:
        kw["size_hint_y"] = None
        kw["height"] = height
    w = Label(text=text, font_size=sp(size), color=color, bold=bold,
              halign=align, valign="middle", max_lines=lines, **kw)
    w.bind(size=lambda obj, val: setattr(obj, "text_size", (val[0], val[1])))
    return w


def style_input(ti):
    """TextInput ki default grey skin hatao aur text ko vertically center karo."""
    ti.multiline = False
    ti.write_tab = False
    ti.background_normal = ""
    ti.background_active = ""
    ti.background_disabled_normal = ""
    ti.background_color = CLEAR
    ti.foreground_color = WHITE
    ti.hint_text_color = MUTED
    ti.cursor_color = CYAN
    ti.selection_color = (CYAN[0], CYAN[1], CYAN[2], 0.35)

    def fit(*_):
        ti.padding = [dp(4), max(0, (ti.height - ti.line_height) / 2), dp(4), 0]

    ti.bind(size=fit)
    Clock.schedule_once(fit, 0)
    return ti


class PlateBox(BoxLayout):
    """BoxLayout jiske peeche rounded rectangle + patli border hoti hai."""

    def __init__(self, fill=PANEL, edge=EDGE, radius=None, **kwargs):
        super().__init__(**kwargs)
        self._radius = dp(18) if radius is None else radius
        with self.canvas.before:
            self._fill_c = Color(*fill)
            self._plate = RoundedRectangle(pos=self.pos, size=self.size,
                                           radius=[self._radius])
            self._edge_c = Color(*edge)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width,
                                                 self.height, self._radius),
                              width=1)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        r = min(self._radius, self.height / 2)
        self._plate.pos = self.pos
        self._plate.size = self.size
        self._plate.radius = [r]
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, r)


class PillButton(ButtonBehavior, Label):
    """Gol kinaare wala flat button (Close, Edit, Light/Dark ...)."""

    def __init__(self, text="", fg=CYAN, fill=CYAN_12, edge=CYAN_60, fsize=13, **kwargs):
        super().__init__(text=text, color=fg, font_size=sp(fsize), halign="center",
                         valign="middle", **kwargs)
        self._fill = fill
        with self.canvas.before:
            self._fill_c = Color(*fill)
            self._plate = RoundedRectangle(pos=self.pos, size=self.size,
                                           radius=[dp(18)])
            self._edge_c = Color(*edge)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width,
                                                 self.height, dp(18)), width=1)
        self.bind(pos=self._sync, size=self._sync, state=self._press)

    def _sync(self, *_):
        r = self.height / 2
        self.text_size = self.size
        self._plate.pos = self.pos
        self._plate.size = self.size
        self._plate.radius = [r]
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, r)

    def _press(self, *_):
        a = min(1.0, self._fill[3] + 0.14) if self.state == "down" else self._fill[3]
        self._fill_c.rgba = (self._fill[0], self._fill[1], self._fill[2], a)

    def set_style(self, fg, fill, edge):
        self._fill = fill
        self.color = fg
        self._fill_c.rgba = fill
        self._edge_c.rgba = edge


class Segmented(PlateBox):
    """Detailed | Balanced | Concise jaisa selector."""

    def __init__(self, options, value, on_change=None, **kwargs):
        super().__init__(fill=INPUT, edge=EDGE, radius=dp(21), orientation="horizontal",
                         padding=dp(3), spacing=dp(2), size_hint_y=None,
                         height=dp(42), **kwargs)
        self.value = value
        self._on_change = on_change
        self._buttons = {}
        for name in options:
            b = PillButton(text=name, fg=MUTED, fill=CLEAR, edge=CLEAR, fsize=13)
            b.bind(on_release=lambda w, n=name: self.select(n, True))
            self._buttons[name] = b
            self.add_widget(b)
        self.select(value, False)

    def select(self, name, notify=True):
        self.value = name
        for n, b in self._buttons.items():
            if n == name:
                b.set_style(DARK_TEXT, CYAN, CYAN)
            else:
                b.set_style(MUTED, CLEAR, CLEAR)
        if notify and self._on_change:
            self._on_change(name)


def gear_points(cx, cy, r_out, r_in, teeth=8):
    """Gear ka bahari kinaara (daant wala) - ek band line ke roop me."""
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = i * step
        for ang, rad in ((a - 0.30 * step, r_in), (a - 0.17 * step, r_out),
                         (a + 0.17 * step, r_out), (a + 0.30 * step, r_in),
                         (a + 0.50 * step, r_in)):
            pts += [cx + math.cos(ang) * rad, cy + math.sin(ang) * rad]
    return pts


class IconButton(ButtonBehavior, Widget):
    """Canvas se bana icon button (font/image ki zaroorat nahi).
    kind='gear': gol dark button par gear.  kind='send': teal gol button par upar ka teer."""

    def __init__(self, kind, **kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.bind(pos=self._draw, size=self._draw, state=self._draw)
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.center
        side = min(self.width, self.height)
        down = self.state == "down"
        with self.canvas:
            if self.kind == "gear":
                Color(*PILL)
                Ellipse(pos=(x - side / 2, y - side / 2), size=(side, side))
                Color(1, 1, 1, 0.14 if not down else 0.30)
                Line(circle=(x, y, side / 2 - 0.5), width=1)
                Color(0.82, 0.92, 0.92, 0.65 if down else 1)
                big = side * 0.265
                Line(points=gear_points(x, y, big, big * 0.78), close=True,
                     width=dp(1.5), joint="round")
                Line(circle=(x, y, big * 0.36), width=dp(1.5))
            else:
                Color(CYAN[0], CYAN[1], CYAN[2], 0.75 if down else 1)
                Ellipse(pos=(x - side / 2, y - side / 2), size=(side, side))
                a = side * 0.205                   # upar ka teer (arrow)
                Color(*DARK_TEXT)
                Line(points=[x, y - a, x, y + a * 0.95], width=dp(2.2), cap="round")
                Line(points=[x - a * 0.85, y + a * 0.10, x, y + a * 1.00,
                             x + a * 0.85, y + a * 0.10],
                     width=dp(2.2), cap="round", joint="round")


class StatusDot(Widget):
    """Hari dot jiske charon taraf halka ring failta rehta hai."""
    pulse = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, pulse=self._draw)
        self._draw()
        anim = Animation(pulse=1, d=1.6, t="out_quad") + Animation(pulse=0, d=0.01)
        anim.repeat = True
        anim.start(self)

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.center
        r = min(self.width, self.height) * 0.24
        rr = r * (1 + 2.2 * self.pulse)
        with self.canvas:
            Color(GREEN[0], GREEN[1], GREEN[2], 0.35 * (1 - self.pulse))
            Ellipse(pos=(x - rr, y - rr), size=(rr * 2, rr * 2))
            Color(*GREEN)
            Ellipse(pos=(x - r, y - r), size=(r * 2, r * 2))


class TextureOrb(ButtonBehavior, Widget):
    """FALLBACK orb (shader na chale to): aasmaan ka disc, andar behte baadal.
    mode: idle / listening, speaking: bool (jab Jarvis bol raha ho)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "idle"
        self.speaking = False
        self.paused = False
        self._ticks = 0
        self._t = 0.0
        self._lvl = 0.0          # 0 = shaant, 1 = poori halchal
        self._flow = 0.045       # baadal ki raftaar
        self._u1 = 0.0
        self._u2 = 0.0
        sky, cloud = get_texture("sky"), get_texture("cloud")
        with self.canvas:
            self._glow_c = Color(1, 1, 1, ORB_GLOW)
            self._glow = Rectangle(texture=get_texture("glow"))
            StencilPush()
            self._mask1 = Ellipse(segments=96)
            StencilUse()
            Color(1, 1, 1, 1)
            self._sky = Rectangle(texture=sky)
            self._c1_col = Color(1, 1, 1, 0.45)
            self._c1 = Rectangle(texture=cloud)
            self._c2_col = Color(1, 1, 1, 0.30)
            self._c2 = Rectangle(texture=cloud)
            StencilUnUse()
            self._mask2 = Ellipse(segments=96)
            StencilPop()
        self.bind(pos=self._tick, size=self._tick)
        self._ev = Clock.schedule_interval(self._tick, 1 / 30.0)

    def stop(self):
        try:
            self._ev.cancel()
        except Exception:
            pass

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0                      # pos/size change se bula: sirf layout update
        elif self.paused:
            return                      # settings khuli hai: animation roko
        self._t += dt
        if dt > 0:
            self._ticks += 1
        t = self._t

        # --- halchal ka star (voice jaisa utaar-chadhaav jab bol raha ho) ---
        if self.speaking:
            target = 0.55 + 0.45 * (0.6 * abs(math.sin(t * 5.1))
                                    + 0.4 * abs(math.sin(t * 2.3 + 1.0)))
            flow_t = 0.20
        elif self.mode in ("listening", "thinking"):
            target = 0.30 + 0.20 * math.sin(t * (4.2 if self.mode == "thinking" else 2.2))
            flow_t = 0.11
        else:
            target, flow_t = 0.0, 0.045
        self._lvl += (target - self._lvl) * min(1.0, dt * 8.0)
        self._flow += (flow_t - self._flow) * min(1.0, dt * 3.0)
        self._u1 = (self._u1 + dt * self._flow) % 1.0
        self._u2 = (self._u2 - dt * self._flow * 0.65) % 1.0

        # --- size / position ---
        cx, cy = self.center
        base = min(self.width * 0.60, self.height * 0.80)
        d = base * (1 + 0.018 * math.sin(t * 1.5) + 0.075 * self._lvl)
        cy += math.sin(t * 1.1) * base * 0.010 - self._lvl * base * 0.02
        x0, y0 = cx - d / 2, cy - d / 2

        g = d * (1.45 + 0.20 * self._lvl)
        self._glow.size = (g, g)
        self._glow.pos = (cx - g / 2, cy - g / 2)
        self._glow_c.a = ORB_GLOW * (0.75 + 0.25 * self._lvl)
        for m in (self._mask1, self._mask2):
            m.pos = (x0, y0)
            m.size = (d, d)
        self._sky.pos = (x0, y0)
        self._sky.size = (d, d)
        for r in (self._c1, self._c2):
            r.pos = (x0, y0)
            r.size = (d, d)

        # --- baadal: texture coordinates khiskao ---
        ov1 = -0.02 + 0.03 * math.sin(t * 0.7)
        self._c1.tex_coords = (self._u1, ov1, self._u1 + 1.0, ov1,
                               self._u1 + 1.0, ov1 + 1.0, self._u1, ov1 + 1.0)
        ov2 = 0.08 + 0.03 * math.sin(t * 0.5 + 1.0)
        self._c2.tex_coords = (self._u2 + 0.3, ov2, self._u2 + 1.0, ov2,
                               self._u2 + 1.0, ov2 + 0.8, self._u2 + 0.3, ov2 + 0.8)
        self._c1_col.a = 0.42 + 0.10 * self._lvl
        self._c2_col.a = 0.28 + 0.10 * self._lvl


# ------------------------------------------------------------ SHADER ORB ----
# ChatGPT jaisa orb GPU shader se banta hai: behte hue baadal, saans jaisa phoolna.
# Agar kisi phone ka GPU ye shader na chala sake to apne aap TextureOrb (upar) chalta hai.
ORB_FRAG = """$HEADER$
uniform float time;
uniform float energy;
uniform float squash;
uniform float glow;

float hash21(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float vnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash21(i);
    float b = hash21(i + vec2(1.0, 0.0));
    float c = hash21(i + vec2(0.0, 1.0));
    float d = hash21(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
        v += a * vnoise(p);
        p = p * 2.03 + vec2(1.7, 9.2);
        a *= 0.5;
    }
    return v;
}

void main(void) {
    vec2 uv = tex_coord0 * 2.0 - 1.0;
    float R = 0.62;
    vec2 s = vec2(uv.x * (1.0 + squash), uv.y * (1.0 - squash));
    float rr = length(s) / R;

    float disc = 1.0 - smoothstep(0.988, 1.0, rr);
    float over = max(rr - 1.0, 0.0);
    float glowA = exp(-over * 3.4) * (0.10 + 0.30 * energy) * glow;

    vec2 p = s / R;                       // -1..1 inside the disc
    float t = time;

    // slow domain warp -> cloud shapes that morph
    vec2 q = vec2(fbm(p * 1.3 + vec2(t * 0.11, -t * 0.07)),
                  fbm(p * 1.3 + vec2(5.2 - t * 0.09, 1.3 + t * 0.12)));
    vec2 w = p + (q - 0.5) * (0.55 + 0.35 * energy);

    float n  = fbm(w * 1.9 + vec2(t * 0.10, t * 0.04));
    float n2 = fbm(w * 4.2 - vec2(t * 0.07, t * 0.09));

    // wavy white band, drifting up / down
    float band = -0.13 + 0.10 * sin(t * 0.55 + p.x * 1.4)
               + 0.05 * sin(t * 0.83 - p.x * 2.6)
               + (n - 0.5) * 0.42;
    float k = smoothstep(band + 0.70, band - 0.08, p.y);        // 0 = blue, 1 = white
    float low = smoothstep(band - 0.05, band - 0.62, p.y);      // 1 = periwinkle

    vec3 blue = vec3(0.275, 0.465, 0.910);
    vec3 white = vec3(0.890, 0.925, 0.985);
    vec3 peri = vec3(0.710, 0.785, 0.968);

    vec3 col = mix(blue, white, k);
    col = mix(col, peri, low);

    // soft wisps near the band
    float near = clamp(1.0 - abs(p.y - band) * 1.7, 0.0, 1.0);
    float wisp = smoothstep(0.42, 0.88, n2) * near;
    col = mix(col, vec3(0.97, 0.985, 1.0), wisp * 0.55);
    // faint darker streaks inside the blue part
    float streak = smoothstep(0.50, 0.85, fbm(w * 3.0 + vec2(-t * 0.05, t * 0.06)));
    col = mix(col, blue * 0.95, streak * (1.0 - k) * 0.30);

    vec3 glowCol = vec3(0.30, 0.50, 1.00);
    vec3 outc = mix(glowCol, col, disc);
    float a = disc + (1.0 - disc) * glowA;
    gl_FragColor = vec4(outc, a);
}
"""


def _shader_supported():
    try:
        rc = RenderContext()
        rc.shader.fs = ORB_FRAG
        return bool(rc.shader.success)
    except Exception as exc:
        print("JARVIS orb shader unavailable:", exc)
        return False


class ShaderOrb(ButtonBehavior, Widget):
    """mode: idle / listening, speaking: bool (jab Jarvis bol raha ho)."""

    def __init__(self, **kwargs):
        try:
            self.canvas = RenderContext(use_parent_projection=True,
                                        use_parent_modelview=True,
                                        use_parent_frag_modelview=True)
        except TypeError:
            self.canvas = RenderContext(use_parent_projection=True,
                                        use_parent_modelview=True)
        self.canvas.shader.fs = ORB_FRAG
        super().__init__(**kwargs)
        self.mode = "idle"
        self.speaking = False
        self.paused = False
        self._ticks = 0
        self._t = 0.0
        self._time = 0.0         # baadal ka samay (halchal ke saath tez hota hai)
        self._e = 0.0            # 0 = shaant, 1 = poori halchal
        with self.canvas:
            Color(1, 1, 1, 1)
            self._quad = Rectangle(pos=self.pos, size=self.size)
        self.canvas["time"] = 0.0
        self.canvas["energy"] = 0.0
        self.canvas["squash"] = 0.0
        self.canvas["glow"] = float(ORB_GLOW / 0.30)
        self.bind(pos=self._tick, size=self._tick)
        self._ev = Clock.schedule_interval(self._tick, 1 / 30.0)

    def stop(self):
        try:
            self._ev.cancel()
        except Exception:
            pass

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0                      # pos/size change se bula: sirf layout update
        elif self.paused:
            return                      # settings khuli hai: animation roko
        self._t += dt
        if dt > 0:
            self._ticks += 1
        t = self._t
        if self.speaking:
            target = 0.65 + 0.35 * (0.6 * abs(math.sin(t * 5.1))
                                    + 0.4 * abs(math.sin(t * 2.3 + 1.0)))
        elif self.mode in ("listening", "thinking"):
            target = 0.55 + 0.10 * math.sin(t * (4.2 if self.mode == "thinking" else 2.2))
        else:
            target = 0.0
        e = self._e = self._e + (target - self._e) * min(1.0, dt * 3.0)
        self._time += dt * (1.6 + 2.2 * e)      # idle me bhi baadal saaf behte dikhen

        breath = (math.sin(t * (1.2 + 1.4 * e)) * (0.010 + 0.030 * e)
                  + math.sin(t * 2.7 + 1.0) * 0.008 * e)
        squash = math.sin(t * 1.7) * 0.020 * e + math.sin(t * 3.1) * 0.006 * e
        cx, cy = self.center
        base = min(self.width * 0.60, self.height * 0.80)
        d = base * (1 + breath)
        q = d / 0.62                    # shader ka disc quad ka 62% hai, baaki glow
        self._quad.size = (q, q)
        self._quad.pos = (cx - q / 2, cy - q / 2)
        self.canvas["time"] = float(self._time)
        self.canvas["energy"] = float(e)
        self.canvas["squash"] = float(squash)


class SimpleOrb(ButtonBehavior, Widget):
    """SAFE orb: sirf Ellipse/Rectangle + chhoti textures (koi shader ya stencil nahi).
    Aasmaani disc ke andar naram safed/neele dhabbe (blobs) lagatar behte rehte hain."""

    # (x-raftaar, y-raftaar, x-phase, y-phase, x-failaav, y-failaav, y-jagah, size, alpha) (d ke hisaab se)
    LIGHT = ((0.55, 0.41, 0.0, 1.3, 0.16, 0.05, -0.02, 0.62, 0.60),
             (0.37, 0.63, 2.1, 0.4, 0.15, 0.06, 0.08, 0.52, 0.55),
             (0.71, 0.29, 4.0, 2.2, 0.14, 0.07, -0.12, 0.46, 0.50),
             (0.47, 0.52, 1.1, 3.1, 0.17, 0.05, 0.15, 0.40, 0.45))
    DARK = ((0.43, 0.33, 0.5, 2.0, 0.12, 0.05, 0.20, 0.34, 0.40),
            (0.61, 0.47, 3.3, 0.9, 0.12, 0.05, 0.14, 0.32, 0.35))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "idle"
        self.speaking = False
        self.paused = False
        self._ticks = 0
        self._t = 0.0
        self._tt = 0.0
        self._lvl = 0.0
        blob = get_texture("blob")
        self._blobs = []
        with self.canvas:
            self._glow_c = Color(1, 1, 1, ORB_GLOW)
            self._glow = Rectangle(texture=get_texture("glow"))
            Color(1, 1, 1, 1)
            self._disc = Ellipse(texture=get_texture("sky"), segments=64)
            for spec, rgb in [(b, (0.28, 0.47, 0.91)) for b in self.DARK] + \
                             [(b, (0.97, 0.985, 1.0)) for b in self.LIGHT]:
                col = Color(rgb[0], rgb[1], rgb[2], spec[8])
                rect = Rectangle(texture=blob)
                self._blobs.append((spec, col, rect))
        self.bind(pos=self._tick, size=self._tick)
        self._ev = Clock.schedule_interval(self._tick, 1 / 30.0)

    def stop(self):
        try:
            self._ev.cancel()
        except Exception:
            pass

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0
        elif self.paused:
            return
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
        self._tt += dt * (0.9 + 2.4 * self._lvl)          # shaant me bhi dhabbe behte dikhen
        tt = self._tt
        cx, cy = self.center
        base = min(self.width * 0.60, self.height * 0.80)
        d = base * (1 + 0.025 * math.sin(t * 1.4) + 0.08 * self._lvl)
        g = d * (1.45 + 0.2 * self._lvl)
        self._glow.size = (g, g)
        self._glow.pos = (cx - g / 2, cy - g / 2)
        self._glow_c.a = ORB_GLOW * (0.75 + 0.25 * self._lvl)
        self._disc.size = (d, d)
        self._disc.pos = (cx - d / 2, cy - d / 2)
        grow = 1.0 + 0.10 * self._lvl
        for (fx, fy, px, py, ax, ay, by, size, alpha), col, rect in self._blobs:
            bx = cx + math.sin(tt * fx + px) * ax * d * (1 + 0.5 * self._lvl)
            byy = cy + (by + math.sin(tt * fy + py) * ay) * d
            sz = size * d * grow * (1 + 0.06 * math.sin(tt * 1.3 + px))
            rect.size = (sz, sz)
            rect.pos = (bx - sz / 2, byy - sz / 2)
            col.a = alpha * (0.85 + 0.15 * math.sin(tt * 0.9 + py))


class OrbHost(FloatLayout):
    """Orb ka dibba: Settings me Advanced/Safe badalte hi bina app band kiye orb badal jata hai.
    main.py/jarvis_ui ke baaki hisse isse seedha orb ki tarah use karte hain (mode, speaking, paused)."""
    __events__ = ("on_release",)

    def __init__(self, level=0, **kwargs):
        super().__init__(**kwargs)
        self.orb = None
        self.engine = ""
        self.level = level
        self._mode = "idle"
        self._speaking = False
        self._paused = False
        self.set_level(level)

    def on_release(self, *args):
        pass

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        if self.orb is not None:
            self.orb.mode = value

    @property
    def speaking(self):
        return self._speaking

    @speaking.setter
    def speaking(self, value):
        self._speaking = bool(value)
        if self.orb is not None:
            self.orb.speaking = self._speaking

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, value):
        self._paused = bool(value)
        if self.orb is not None:
            self.orb.paused = self._paused

    @property
    def _ticks(self):
        return getattr(self.orb, "_ticks", 0) if self.orb is not None else 0

    def set_level(self, level):
        """level 0 = Advanced (GPU), 2 = Safe. Asli chalne wale orb ka naam lautata hai."""
        old = self.orb
        if old is not None:
            try:
                old.stop()
                self.remove_widget(old)
            except Exception as exc:
                print("JARVIS orb remove error:", exc)
        orb = make_orb(level, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        orb.mode = self._mode
        orb.speaking = self._speaking
        orb.paused = self._paused
        orb.bind(on_release=lambda *a: self.dispatch("on_release"))
        self.add_widget(orb)
        self.orb = orb
        self.level = level
        if isinstance(orb, ShaderOrb):
            self.engine = "Advanced (GPU shader)"
        elif isinstance(orb, TextureOrb):
            self.engine = "Texture (GPU shader is phone par nahi chala)"
        else:
            self.engine = "Safe"
        return self.engine


def make_orb(level=0, **kwargs):
    """level 0: GPU shader orb, 1: texture orb, 2: simple orb (sabse safe).
    Jo level fail ho jaye, uske neeche wala apne aap chalta hai."""
    if level <= 0 and _shader_supported():
        try:
            return ShaderOrb(**kwargs)
        except Exception as exc:
            print("JARVIS ShaderOrb failed:", exc)
    if level <= 1:
        try:
            return TextureOrb(**kwargs)
        except Exception as exc:
            print("JARVIS TextureOrb failed:", exc)
    return SimpleOrb(**kwargs)


class VoiceChip(ButtonBehavior, BoxLayout):
    """Gol avatar + naam. Selected hone par teal ring aata hai."""

    def __init__(self, name, letter, tint, **kwargs):
        super().__init__(orientation="vertical", padding=dp(4), spacing=dp(5), **kwargs)
        self.name = name
        self.tint = tint
        self.selected = False
        self.avatar = FloatLayout(size_hint=(None, None), size=(dp(44), dp(44)),
                                  pos_hint={"center_x": 0.5})
        self.avatar.add_widget(Label(text=letter, bold=True, font_size=sp(17),
                                     color=(1, 1, 1, 1)))
        self.title = make_label(name.replace(" ", "\n"), 11, MUTED, False, "center",
                                height=dp(32), lines=2)
        self.add_widget(self.avatar)
        self.add_widget(self.title)
        self.bind(pos=self._draw, size=self._draw)
        self.avatar.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_):
        a = self.avatar
        self.canvas.before.clear()
        a.canvas.before.clear()
        with self.canvas.before:
            if self.selected:
                Color(*CYAN_12)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        with a.canvas.before:
            Color(*self.tint)
            Ellipse(pos=a.pos, size=a.size)
            if self.selected:
                Color(*CYAN)
                Line(circle=(a.center_x, a.center_y, a.width / 2 + dp(3)),
                     width=dp(1.6))

    def set_selected(self, flag):
        self.selected = flag
        self.title.color = WHITE if flag else MUTED
        self._draw()


class ActionRow(ButtonBehavior, BoxLayout):
    """Ek line ka option: text + chhota '>' + neeche patli line."""

    def __init__(self, text, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(46),
                         **kwargs)
        self.add_widget(make_label(text, 14, WHITE))
        self._chev = Widget(size_hint=(None, 1), width=dp(18))
        self.add_widget(self._chev)
        with self.canvas.before:
            self._hl = Color(1, 1, 1, 0)
            self._hl_rect = Rectangle(pos=self.pos, size=self.size)
        with self.canvas.after:
            Color(*EDGE)
            self._div = Line(points=[self.x, self.y, self.right, self.y], width=1)
        self.bind(pos=self._sync, size=self._sync, state=self._press)
        self._chev.bind(pos=self._draw_chev, size=self._draw_chev)

    def _sync(self, *_):
        self._hl_rect.pos = self.pos
        self._hl_rect.size = self.size
        self._div.points = [self.x, self.y, self.right, self.y]

    def _press(self, *_):
        self._hl.a = 0.06 if self.state == "down" else 0

    def _draw_chev(self, *_):
        c = self._chev
        c.canvas.clear()
        x, y = c.center
        s = dp(5)
        with c.canvas:
            Color(*MUTED)
            Line(points=[x - s / 2, y + s, x + s / 2, y, x - s / 2, y - s],
                 width=dp(1.5), cap="round", joint="round")


class Toast(Label):
    """Neeche aane wala chhota message."""

    def __init__(self, **kwargs):
        super().__init__(size_hint=(None, None), opacity=0, font_size=sp(13),
                         color=WHITE, **kwargs)
        self.pos_hint = {"center_x": 0.5}
        self.y = dp(104)
        with self.canvas.before:
            Color(0.11, 0.16, 0.17, 1)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(19)])
            Color(*CYAN_60)
            self._ln = Line(rounded_rectangle=(self.x, self.y, self.width, self.height,
                                               dp(19)), width=1)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ln.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(19))

    def show(self, message):
        self.text = str(message)
        self.texture_update()
        self.size = (self.texture_size[0] + dp(36), dp(38))
        Animation.cancel_all(self)
        (Animation(opacity=1, d=0.15) + Animation(opacity=1, d=1.7)
         + Animation(opacity=0, d=0.3)).start(self)


# ------------------------------------------------------------ SETTINGS CARD --
def accent_bar():
    w = Widget(size_hint=(None, None), size=(dp(4), dp(18)), pos_hint={"center_y": 0.5})
    with w.canvas:
        Color(*CYAN)
        rect = RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(2)])
    w.bind(pos=lambda o, v: setattr(rect, "pos", v))
    return w


def make_card(title):
    card = PlateBox(orientation="vertical", padding=dp(16), spacing=dp(10),
                    size_hint_y=None)
    card.bind(minimum_height=card.setter("height"))
    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(26),
                    spacing=dp(10))
    row.add_widget(accent_bar())
    row.add_widget(make_label(title, 16, WHITE, True))
    card.add_widget(row)
    return card


# -------------------------------------------------- BOOT GUARD + SAFETY NET --
_SAFE = {"installed": False}


def _data_file(app, name):
    try:
        return os.path.join(app.user_data_dir, name)
    except Exception:
        return None


def _write_json(path, data):
    try:
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
    except Exception as exc:
        print("JARVIS write error:", exc)


def boot_level(app):
    """Orb ka level chuno. Agar pichhli baar app shuru hote hi band ho gaya tha
    (pending bacha hua hai) to ek level safe wala chalao."""
    path = _data_file(app, "jarvis_ui_boot.json")
    level, pending = 0, False
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                st = json.load(fh)
            level = int(st.get("level", 0))
            pending = bool(st.get("pending", False))
    except Exception:
        pass
    level = max(0, min(2, level))
    if pending:
        level = min(2, level + 1)
    _write_json(path, {"level": level, "pending": True})
    return level


def boot_ok(app, level):
    """App theek se chal gaya: pending hata do."""
    _write_json(_data_file(app, "jarvis_ui_boot.json"), {"level": level, "pending": False})


def set_orb_level(app, level):
    _write_json(_data_file(app, "jarvis_ui_boot.json"), {"level": level, "pending": False})


def install_safety_net(app, on_error):
    """Python ki koi bhi galti (animation, button...) app ko band na kare:
    error file me likho aur screen par dikhao."""
    if _SAFE["installed"]:
        return
    _SAFE["installed"] = True
    try:
        from kivy.base import ExceptionHandler, ExceptionManager
    except Exception:
        return

    class JarvisHandler(ExceptionHandler):
        def handle_exception(self, inst):
            if isinstance(inst, (SystemExit, KeyboardInterrupt)):
                return ExceptionManager.RAISE
            try:
                import traceback
                text = "".join(traceback.format_exception(type(inst), inst,
                                                          inst.__traceback__))
                print("JARVIS UI EXCEPTION:\n" + text)
                path = _data_file(app, "jarvis_ui_error.log")
                if path:
                    with open(path, "a", encoding="utf-8") as fh:
                        fh.write(text[-1500:] + "\n----\n")
                on_error(text)
            except Exception:
                pass
            return ExceptionManager.PASS

    ExceptionManager.add_handler(JarvisHandler())


# --------------------------------------------------------------- STATE FILE --
def _state_path(app):
    try:
        return os.path.join(app.user_data_dir, "jarvis_ui.json")
    except Exception:
        return None


def _load_state(app):
    path = _state_path(app)
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except Exception as exc:
        print("JARVIS UI state load error:", exc)
    return {}


ELEVEN_SLOTS = 7


def eleven_voice_id(app):
    """Chuni hui awaaz ElevenLabs ki ho to uski Voice ID, warna ''."""
    sel = getattr(app, "selected_voice", "")
    for name, vid in getattr(app, "eleven_voices", []):
        if name == sel and vid:
            return vid
    return ""


def _clean_slots(raw):
    out = []
    for item in list(raw or [])[:ELEVEN_SLOTS]:
        try:
            out.append([str(item[0]).strip(), str(item[1]).strip()])
        except Exception:
            out.append(["", ""])
    while len(out) < ELEVEN_SLOTS:
        out.append(["", ""])
    return out


def _sync_prefs(app):
    """Key/voice waghera Android SharedPreferences me bhi likho taaki floating panel
    (JarvisOverlayService, Java) bina app khole use kar sake."""
    try:
        prefs = app.activity.getSharedPreferences("jarvis_prefs", 0)
        ed = prefs.edit()
        ed.putString("gemini_key", str(getattr(app, "gemini_key", "") or ""))
        ed.putString("ai_model", str(getattr(app, "ai_model", "") or ""))
        ed.putString("verbosity", str(getattr(app, "verbosity", "Balanced")))
        ed.putBoolean("ai_enabled", bool(getattr(app, "ai_enabled", True)))
        ed.putBoolean("wake_enabled", bool(getattr(app, "wake_enabled", False)))
        pitch, rate = VOICES.get(getattr(app, "selected_voice", "Male Alpha"), (1.0, 1.0))
        ed.putFloat("pitch", float(pitch))
        ed.putFloat("rate", float(rate))
        ed.putString("eleven_key", str(getattr(app, "eleven_key", "") or ""))
        ed.putString("eleven_voice_id", eleven_voice_id(app))
        ed.apply()
    except Exception as exc:
        print("Prefs sync skipped:", exc)


def _save_state(app):
    _sync_prefs(app)
    path = _state_path(app)
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "voice": app.selected_voice,
                "wake_word": app.wake_word,
                "verbosity": app.verbosity,
                "history": app.history[:30],
                "gemini_key": getattr(app, "gemini_key", ""),
                "ai_enabled": getattr(app, "ai_enabled", True),
                "ai_model": getattr(app, "ai_model", ""),
                "eleven_key": getattr(app, "eleven_key", ""),
                "eleven_slots": getattr(app, "eleven_slots", []),
                "wake_enabled": getattr(app, "wake_enabled", False),
            }, fh, ensure_ascii=False)
    except Exception as exc:
        print("JARVIS UI state save error:", exc)


# ================================================================ BUILD UI ===
TALK_ACTION = "org.myassistant.TALK"
UI_VERSION = "0.64"


def build_jarvis_ui(app):
    # main.py ke asli functions sabse pehle yaad rakho (neeche wrap honge).
    original_set_status = getattr(app, "set_status", None)
    original_speak = getattr(app, "speak", None)
    original_process = getattr(app, "process_command", None)

    try:
        Window.softinput_mode = "below_target"   # keyboard aane par message bar upar uthe
    except Exception:
        pass

    # ---- saved settings ----
    state = _load_state(app)
    app.selected_voice = state.get("voice", "Male Alpha")
    app.eleven_key = str(state.get("eleven_key", "") or "").strip()
    app.eleven_slots = _clean_slots(state.get("eleven_slots"))
    try:
        import jarvis_secrets as _sec          # build ke waqt GitHub Secrets se banti hai (repo me nahi)
    except Exception:
        _sec = None
    app.eleven_voices = []
    app.wake_word = state.get("wake_word", "Hey JARVIS")
    app.verbosity = state.get("verbosity", "Balanced")
    app.theme = "Dark"
    app.history = list(state.get("history", []))
    app.gemini_key = str(state.get("gemini_key", "") or "").strip()
    if _sec is not None:                       # saved key ho to wahi chalegi; khali ho tab APK wali use hogi
        try:
            if not app.gemini_key:
                app.gemini_key = str(getattr(_sec, "GEMINI_KEY", "") or "").strip()
            if not app.eleven_key:
                app.eleven_key = str(getattr(_sec, "ELEVEN_KEY", "") or "").strip()
            if not any(v for _n, v in app.eleven_slots):
                app.eleven_slots = _clean_slots(getattr(_sec, "ELEVEN_VOICES", []))
            ck = str(getattr(_sec, "CONVERSATION_KEY", "") or "").strip()
            if ck and not getattr(app, "_conversation_key", "") and hasattr(app, "_save_conversation_key"):
                app._save_conversation_key(ck)
        except Exception as exc:
            print("secrets seed error:", exc)
    app.eleven_voices = [[n, v] for n, v in app.eleven_slots if n and v]
    if app.selected_voice not in VOICES and app.selected_voice not in [n for n, _v in app.eleven_voices]:
        app.selected_voice = "Male Alpha"
    app.ai_enabled = bool(state.get("ai_enabled", True))
    app.ai_model = str(state.get("ai_model", "") or "")
    app.wake_enabled = bool(state.get("wake_enabled", False))
    try:                                   # notification / tile se On-Off kiya ho to wahi sach hai
        _sp = app.activity.getSharedPreferences("jarvis_prefs", 0)
        if _sp.contains("wake_enabled"):
            app.wake_enabled = bool(_sp.getBoolean("wake_enabled", False))
    except Exception:
        pass
    try:
        import ai_brain
    except Exception as exc:                    # AI file na mile to baaki app chalta rahe
        print("ai_brain import error:", exc)
        ai_brain = None
    try:
        import jarvis_actions as actions_mod
    except Exception as exc:
        print("jarvis_actions import error:", exc)
        actions_mod = None
    ai = {"busy": False, "last": "", "gen": 0, "typed": False, "from_typed": False,
          "relisten": None}
    client = None
    if ai_brain is not None:
        def _remember_model(name):
            app.ai_model = name
            _save_state(app)

        client = ai_brain.GeminiClient(
            get_key=lambda: app.gemini_key, get_verbosity=lambda: app.verbosity,
            get_model=lambda: app.ai_model or None, set_model=_remember_model)
    orb_level = boot_level(app)       # 0 = GPU, 1 = texture, 2 = simple

    # ---- root with gradient background ----
    root = FloatLayout()
    with root.canvas.before:
        Color(1, 1, 1, 1)
        bg_rect = Rectangle(texture=get_texture("bg"), pos=root.pos, size=root.size)
    root.bind(pos=lambda o, v: setattr(bg_rect, "pos", v),
              size=lambda o, v: setattr(bg_rect, "size", v))

    home = FloatLayout()
    settings_page = BoxLayout(orientation="vertical",
                              padding=[dp(16), dp(12), dp(16), 0], spacing=dp(12))
    root.add_widget(home)

    toast_widget = Toast()
    root.add_widget(toast_widget)

    def toast(message):
        toast_widget.show(message)

    # ------------------------------------------------------------- HOME ----
    header = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(64),
                       padding=[dp(22), dp(8), dp(18), dp(8)], spacing=dp(4),
                       pos_hint={"top": 1})
    title = Label(text="JARVIS", font_size=sp(26), color=WHITE, size_hint_x=None,
                  width=dp(100), halign="left")
    title.bind(texture_size=lambda obj, ts: setattr(obj, "width", ts[0]))
    header.add_widget(title)
    header.add_widget(StatusDot(size_hint=(None, None), size=(dp(20), dp(20)),
                                pos_hint={"center_y": 0.52}))
    header.add_widget(Widget())
    gear_btn = IconButton("gear", size_hint=(None, None),
                          size=(dp(46), dp(46)), pos_hint={"center_y": 0.5})
    header.add_widget(gear_btn)
    home.add_widget(header)

    orb = OrbHost(orb_level, size_hint=(1, 0.44),
                  pos_hint={"center_x": 0.5, "center_y": 0.60})
    home.add_widget(orb)

    # Agar UI me koi galti aaye to app band nahi hoga, yahan chhoti laal line dikhegi.
    err_label = Label(text="", font_size=sp(10), color=(1.0, 0.55, 0.55, 1),
                      halign="center", valign="top", max_lines=3,
                      size_hint=(0.94, None), height=dp(44),
                      pos_hint={"center_x": 0.5, "top": 0.925})
    err_label.bind(size=lambda obj, val: setattr(obj, "text_size", (val[0], val[1])))
    home.add_widget(err_label)

    def on_ui_error(text):
        lines = [ln for ln in str(text).strip().splitlines() if ln.strip()]
        shown = "UI error: " + (lines[-1] if lines else "unknown")
        Clock.schedule_once(lambda dt: setattr(err_label, "text", shown[:220]), 0)

    install_safety_net(app, on_ui_error)

    def boot_check(dt):
        if getattr(orb, "_ticks", 0) >= 12:     # ~0.4 sec animation chali = shuru ho gaya
            boot_ok(app, orb_level)
            return False
        return True

    Clock.schedule_interval(boot_check, 0.25)

    status_scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), size_hint=(0.88, None),
                               height=dp(80), pos_hint={"center_x": 0.5, "top": 0.385})
    status = Label(text="Ready when you are", font_size=sp(17), color=MUTED,
                   halign="center", valign="top", size_hint_y=None, height=dp(80))

    def fit_status(*_):
        status.text_size = (status_scroll.width, None)
        status.height = max(status.texture_size[1] + dp(8), status_scroll.height)

    def fit_status_scroll(*_):
        status_scroll.height = max(dp(60), home.height * 0.385 - dp(100))

    status.bind(texture_size=fit_status)
    status_scroll.bind(size=fit_status)
    status.bind(text=lambda *_: setattr(status_scroll, "scroll_y", 1))
    home.bind(size=fit_status_scroll)
    status_scroll.add_widget(status)
    home.add_widget(status_scroll)

    caption = make_label("JARVIS  •  PERSONAL ASSISTANT", 9.5, FAINT, False,
                         "center", height=dp(18))
    caption.size_hint_x = 0.9
    caption.pos_hint = {"center_x": 0.5}
    caption.y = dp(90)
    home.add_widget(caption)

    composer = PlateBox(fill=PILL, edge=EDGE, radius=dp(27), orientation="horizontal",
                        padding=[dp(18), dp(4), dp(6), dp(4)], spacing=dp(4),
                        size_hint=(0.90, None), height=dp(54),
                        pos_hint={"center_x": 0.5})
    composer.y = dp(28)
    chat = style_input(TextInput(hint_text="Message...", font_size=sp(16)))
    composer.add_widget(chat)
    send_btn = IconButton("send", size_hint=(None, 1), width=dp(46))
    composer.add_widget(send_btn)
    home.add_widget(composer)

    # ------------------------------------------------------------ SETTINGS --
    sheader = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44),
                        spacing=dp(14))
    close_btn = PillButton(text="<  Close", size_hint=(None, None), size=(dp(92), dp(36)),
                           pos_hint={"center_y": 0.5})
    sheader.add_widget(close_btn)
    sheader.add_widget(make_label("JARVIS Settings", 19, WHITE, True))
    settings_page.add_widget(sheader)

    scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), scroll_type=["bars", "content"])
    content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14),
                        padding=[0, dp(2), 0, dp(28)])
    content.bind(minimum_height=content.setter("height"))
    scroll.add_widget(content)
    settings_page.add_widget(scroll)

    # 1) Voice
    voice_card = make_card("Voice Selection")
    current_voice = make_label("Current: " + app.selected_voice, 12, MUTED, height=dp(20))
    voice_card.add_widget(current_voice)
    voice_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(96),
                          spacing=dp(4))
    chips = []
    for vname, letter, tint in [("Male Alpha", "M", (0.20, 0.45, 0.90, 1)),
                                ("Female Beta", "F", (0.85, 0.35, 0.55, 1)),
                                ("Formal Gamma", "G", (0.40, 0.48, 0.60, 1)),
                                ("Casual Delta", "D", (0.30, 0.68, 0.40, 1))]:
        chip = VoiceChip(vname, letter, tint)
        chips.append(chip)
        voice_row.add_widget(chip)
    voice_card.add_widget(voice_row)
    eleven_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    eleven_box.bind(minimum_height=eleven_box.setter("height"))
    voice_card.add_widget(eleven_box)
    content.add_widget(voice_card)

    def apply_voice(*_):
        """TTS ki pitch/speed badlo (TTS tab tak ready na ho to skip)."""
        tts = getattr(app, "tts", None)
        if tts is None:
            return
        pitch, rate = VOICES.get(app.selected_voice, (1.0, 1.0))

        def work():
            try:
                if not getattr(app, "_ui_locale_set", False):
                    app._ui_locale_set = True
                    from jnius import autoclass
                    Locale = autoclass("java.util.Locale")
                    if int(tts.setLanguage(Locale("en", "IN"))) < 0:
                        tts.setLanguage(Locale.US)
            except Exception as exc:
                print("Locale error:", exc)
            try:
                tts.setPitch(float(pitch))
                tts.setSpeechRate(float(rate))
            except Exception as exc:
                print("Voice apply error:", exc)

        try:
            app.run_on_android_thread(work)
            app._ui_voice_tts = tts
        except Exception as exc:
            print("Voice apply error:", exc)

    def choose_voice(chip):
        app.selected_voice = chip.name
        for c in chips:
            c.set_selected(c is chip)
        current_voice.text = "Current: " + chip.name
        apply_voice()
        _save_state(app)
        toast("Voice: " + chip.name)

    for c in chips:
        c.set_selected(c.name == app.selected_voice)
        c.bind(on_release=choose_voice)

    # 1b) ElevenLabs awaazein (key + 7 Voice ID)
    try:
        import eleven as eleven_mod
    except Exception as exc:
        print("eleven import error:", exc)
        eleven_mod = None
    speaker = None
    if eleven_mod is not None:
        try:
            cache_dir = str(app.activity.getCacheDir().getAbsolutePath())
        except Exception:
            cache_dir = getattr(app, "user_data_dir", "") or "."
        speaker = eleven_mod.ElevenSpeaker(cache_dir)

    ELEVEN_TINTS = [(0.55, 0.35, 0.85, 1), (0.85, 0.55, 0.20, 1), (0.20, 0.65, 0.70, 1),
                    (0.80, 0.30, 0.35, 1), (0.35, 0.60, 0.30, 1), (0.30, 0.45, 0.80, 1),
                    (0.70, 0.60, 0.25, 1)]
    eleven_chips = []

    def rebuild_eleven_chips():
        for c in eleven_chips:
            if c in chips:
                chips.remove(c)
        del eleven_chips[:]
        eleven_box.clear_widgets()
        voices = list(app.eleven_voices)
        for start in range(0, len(voices), 4):
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(96),
                            spacing=dp(4))
            for idx in range(start, min(start + 4, len(voices))):
                name = voices[idx][0]
                chip = VoiceChip(name, name[:1].upper() or "E", ELEVEN_TINTS[idx % len(ELEVEN_TINTS)])
                chip.set_selected(name == app.selected_voice)
                chip.bind(on_release=choose_voice)
                chips.append(chip)
                eleven_chips.append(chip)
                row.add_widget(chip)
            for _ in range(4 - min(4, len(voices) - start)):
                row.add_widget(Widget())
            eleven_box.add_widget(row)

    eleven_card = make_card("ElevenLabs Voices")
    eleven_info = make_label("", 12, MUTED, height=dp(48), lines=3)
    eleven_card.add_widget(eleven_info)

    def refresh_eleven_info():
        if not app.eleven_key:
            eleven_info.text = "Key set nahi hai. ElevenLabs API key paste karke Save dabaiye."
        elif not app.eleven_voices:
            eleven_info.text = "Key saved. Neeche naam + Voice ID bharkar 'Voices save karo' dabaiye."
        else:
            eleven_info.text = (str(len(app.eleven_voices)) + " voice taiyaar. Upar Voice Selection me "
                                "chuniye. Galti aaye to phone ki awaaz se bolega.")

    ek_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
    ek_wrap = PlateBox(fill=INPUT, edge=EDGE, radius=dp(12), orientation="horizontal",
                       padding=[dp(10), 0, dp(10), 0])
    ek_input = style_input(TextInput(text="", hint_text="ElevenLabs API key (sk_...)",
                                     font_size=sp(14), password=True))
    ek_wrap.add_widget(ek_input)
    ek_row.add_widget(ek_wrap)
    ek_btn = PillButton(text="Save", size_hint=(None, None), width=dp(72), height=dp(36),
                        pos_hint={"center_y": 0.5})
    ek_row.add_widget(ek_btn)
    eleven_card.add_widget(ek_row)

    def save_eleven_key(*_):
        txt = ek_input.text.strip()
        if txt:
            app.eleven_key = txt
            ek_input.text = ""
            ek_input.focus = False
        _save_state(app)
        refresh_eleven_info()
        toast("ElevenLabs key save ho gayi" if app.eleven_key else "Key khali hai")

    ek_btn.bind(on_release=save_eleven_key)

    slot_inputs = []
    for i in range(ELEVEN_SLOTS):
        srow = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        nwrap = PlateBox(fill=INPUT, edge=EDGE, radius=dp(12), orientation="horizontal",
                         size_hint_x=0.34, padding=[dp(10), 0, dp(6), 0])
        ninp = style_input(TextInput(text=app.eleven_slots[i][0], hint_text="Naam " + str(i + 1),
                                     font_size=sp(13)))
        nwrap.add_widget(ninp)
        iwrap = PlateBox(fill=INPUT, edge=EDGE, radius=dp(12), orientation="horizontal",
                         padding=[dp(10), 0, dp(6), 0])
        iinp = style_input(TextInput(text=app.eleven_slots[i][1], hint_text="Voice ID",
                                     font_size=sp(13)))
        iwrap.add_widget(iinp)
        srow.add_widget(nwrap)
        srow.add_widget(iwrap)
        eleven_card.add_widget(srow)
        slot_inputs.append((ninp, iinp))

    def save_eleven_voices(*_):
        app.eleven_slots = _clean_slots([[n.text, v.text] for n, v in slot_inputs])
        names = set(VOICES.keys())
        app.eleven_voices = [[n, v] for n, v in app.eleven_slots if n and v and n not in names]
        if app.selected_voice not in VOICES and \
                app.selected_voice not in [n for n, _v in app.eleven_voices]:
            app.selected_voice = "Male Alpha"
            for c in chips:
                c.set_selected(c.name == app.selected_voice)
            current_voice.text = "Current: " + app.selected_voice
        _save_state(app)
        rebuild_eleven_chips()
        refresh_eleven_info()
        toast(str(len(app.eleven_voices)) + " voice save hui")

    def test_eleven(*_):
        app.speak("Namaste, main Jarvis hoon. Aapki awaaz ab aisi sunai degi.")

    def fill_free_voices(*_):
        """Key se account ki sirf FREE (premade) awaazein lakar 7 slot bhar do."""
        if eleven_mod is None:
            toast("eleven.py nahi mili")
            return
        key = ek_input.text.strip() or app.eleven_key
        if not key:
            toast("Pehle ElevenLabs key daaliye")
            return
        if ek_input.text.strip():
            save_eleven_key()
        toast("Free voices la raha hoon...")

        def work():
            try:
                found = eleven_mod.list_free_voices(key, ELEVEN_SLOTS)
                err = "" if found else "Is key par koi free voice nahi mili"
            except Exception as exc:
                found, err = [], str(exc)

            def done(dt):
                if err:
                    toast(err[:90])
                    return
                for i, (n, v) in enumerate(slot_inputs):
                    n.text = found[i][0] if i < len(found) else ""
                    v.text = found[i][1] if i < len(found) else ""
                save_eleven_voices()

            Clock.schedule_once(done, 0)

        threading.Thread(target=work, daemon=True).start()

    for label, fn in [("Free voices apne aap bharo (key se)", fill_free_voices),
                      ("Voices save karo", save_eleven_voices),
                      ("Chuni hui awaaz test karo", test_eleven)]:
        row = ActionRow(label)
        row.bind(on_release=lambda w, f=fn: f())
        eleven_card.add_widget(row)
    eleven_card.add_widget(make_label("Key aur Voice ID sirf is phone me save hote hain. Kabhi GitHub par "
                                      "mat daaliye.", 11, MUTED, height=dp(34), lines=2))
    content.add_widget(eleven_card)
    rebuild_eleven_chips()
    refresh_eleven_info()

    # 2) History
    history_card = make_card("History")
    history_rows = [make_label("", 13, WHITE, height=dp(26)) for _ in range(3)]
    for r in history_rows:
        r.shorten = True
        r.shorten_from = "right"
        history_card.add_widget(r)
    content.add_widget(history_card)

    def refresh_history():
        items = app.history[:3]
        for i, row in enumerate(history_rows):
            if i < len(items):
                row.text = '"' + items[i] + '"'
                row.color = WHITE
            elif i == 0:
                row.text = "Abhi koi interaction nahi"
                row.color = MUTED
            else:
                row.text = ""

    def add_history(text):
        text = " ".join(str(text).split())
        if text and (not app.history or app.history[0] != text):
            app.history.insert(0, text)
            del app.history[30:]
            _save_state(app)

    def clear_history(*_):
        app.history = []
        refresh_history()
        _save_state(app)
        toast("History clear ho gayi")

    # 3) Wake word
    wake_card = make_card("Wake Word Customization")
    wake_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44),
                         spacing=dp(10))
    wake_wrap = PlateBox(fill=INPUT, edge=EDGE, radius=dp(12), orientation="horizontal",
                         padding=[dp(10), 0, dp(10), 0])
    wake_input = style_input(TextInput(text=app.wake_word, hint_text="Hey JARVIS",
                                       font_size=sp(15), readonly=True))
    wake_wrap.add_widget(wake_input)
    wake_row.add_widget(wake_wrap)
    wake_btn = PillButton(text="Edit", size_hint=(None, None),
                          width=dp(72), height=dp(36), pos_hint={"center_y": 0.5})
    wake_row.add_widget(wake_btn)
    wake_card.add_widget(wake_row)
    wake_card.add_widget(make_label('Default: "Hey JARVIS"', 12, MUTED, height=dp(20)))
    content.add_widget(wake_card)

    def toggle_wake(*_):
        if wake_input.readonly:
            wake_input.readonly = False
            wake_input.focus = True
            wake_btn.text = "Save"
        else:
            wake_input.readonly = True
            app.wake_word = wake_input.text.strip() or "Hey JARVIS"
            wake_input.text = app.wake_word
            wake_btn.text = "Edit"
            _save_state(app)
            toast("Wake word saved")

    wake_btn.bind(on_release=toggle_wake)

    # 4) Verbosity
    verb_card = make_card("Response Verbosity")

    def on_verbosity(value):
        app.verbosity = value
        _save_state(app)
        toast("Verbosity: " + value)

    verb_card.add_widget(Segmented(["Detailed", "Balanced", "Concise"], app.verbosity,
                                   on_verbosity))
    content.add_widget(verb_card)

    # 4b) Gemini AI
    ai_card = make_card("Gemini AI (baat-cheet)")
    ai_info = make_label("", 12, MUTED, height=dp(64), lines=4)
    ai_card.add_widget(ai_info)

    def refresh_ai_info():
        if ai_brain is None:
            ai_info.text = "ai_brain.py file nahi mili - GitHub par upload kijiye."
        elif not app.gemini_key:
            ai_info.text = "Key set nahi hai. Neeche paste karke Save dabaiye."
        elif app.ai_enabled:
            ai_info.text = "AI chalu hai. Jo command samajh na aaye, Gemini jawab dega."
        else:
            ai_info.text = "AI band hai (key saved)."

    key_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44),
                        spacing=dp(10))
    key_wrap = PlateBox(fill=INPUT, edge=EDGE, radius=dp(12), orientation="horizontal",
                        padding=[dp(10), 0, dp(10), 0])
    key_input = style_input(TextInput(text="", hint_text="Gemini API key paste kijiye",
                                      font_size=sp(14), password=True))
    key_wrap.add_widget(key_input)
    key_row.add_widget(key_wrap)
    key_btn = PillButton(text="Save", size_hint=(None, None), width=dp(72), height=dp(36),
                         pos_hint={"center_y": 0.5})
    key_row.add_widget(key_btn)
    ai_card.add_widget(key_row)

    def save_key(*_):
        app.gemini_key = key_input.text.strip() or ""
        if key_input.text.strip():
            key_input.text = ""
            key_input.focus = False
        if client is not None:
            client.model = None
        app.ai_model = ""
        _save_state(app)
        refresh_ai_info()
        toast("Key save ho gayi" if app.gemini_key else "Key hata di gayi")

    key_btn.bind(on_release=save_key)

    def on_ai_toggle(value):
        app.ai_enabled = (value == "On")
        _save_state(app)
        refresh_ai_info()
        toast("AI " + ("chalu" if app.ai_enabled else "band"))

    ai_card.add_widget(Segmented(["On", "Off"], "On" if app.ai_enabled else "Off",
                                 on_ai_toggle))

    def open_key_page(*_):
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://aistudio.google.com/apikey"))
            app.open_intent(intent)
        except Exception as exc:
            print("Key page error:", exc)
            toast("Browser me aistudio.google.com/apikey kholiye")

    def clear_ai_memory(*_):
        if client is not None:
            client.clear()
        toast("AI ki yaaddasht saaf")

    def test_ai(*_):
        if client is None or not app.gemini_key:
            toast("Pehle key save kijiye")
            return
        toast("Test ho raha hai...")

        def work():
            ok, reply = client.ask("Ek chhota sa namaste bolo.")
            client.clear()
            detail = getattr(client, "last_detail", "")

            def show(dt):
                if ok:
                    toast("AI theek chal raha hai")
                    refresh_ai_info()
                else:
                    toast("Test fail")
                    ai_info.text = reply + ("\nDetail: " + detail[:150] if detail else "")

            Clock.schedule_once(show, 0)

        threading.Thread(target=work, daemon=True).start()

    for label, fn in [("Free key banaiye (Google AI Studio)", open_key_page),
                      ("Connection test", test_ai),
                      ("AI memory clear", clear_ai_memory)]:
        row = ActionRow(label)
        row.bind(on_release=lambda w, f=fn: f())
        ai_card.add_widget(row)
    ai_card.add_widget(make_label("Key sirf is phone me save hoti hai. Kabhi GitHub par mat "
                                  "daaliye.", 11, MUTED, height=dp(34), lines=2))
    content.add_widget(ai_card)

    # 4c) Home screen button + floating panel
    home_card = make_card("Home Screen Jarvis")
    home_card.add_widget(make_label(
        "Screen par chhota safed gola (bubble) rehta hai, pakad kar kahin bhi rakhiye. Dhundhla = so "
        "raha hai. 'Jarvis' bolne ya gole par tap karne se jaagta hai, sunta hai aur kaam karta hai. "
        "'Jarvis ab tum ja sakte ho' bolne ya dobara tap karne par so jata hai.",
        12, MUTED, height=dp(84), lines=5))
    PKG_CLASS = "org.myassistant.myvoiceassistant.JarvisTriggerActivity"

    def get_activity():
        act = getattr(app, "activity", None)
        if act is None:
            from jnius import autoclass
            act = autoclass("org.kivy.android.PythonActivity").mActivity
        return act

    def get_context():
        """pyjnius kabhi PythonActivity ko 'Context' nahi maanta; Application context hamesha chalta hai."""
        return get_activity().getApplicationContext()

    def trigger_intent():
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        intent = Intent()
        intent.setClassName(get_activity().getPackageName(), PKG_CLASS)
        intent.setAction(TALK_ACTION)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return intent

    def add_home_shortcut(*_):
        if not parts_ok("JarvisTriggerActivity"):
            refresh_parts()
            toast("Panel is APK me nahi hai, isliye button kaam nahi karta. Pehle rebuild kijiye")
            return
        step = "start"
        try:
            from jnius import autoclass, cast
            ctx = get_activity()
            Build = autoclass("android.os.Build$VERSION")
            if int(Build.SDK_INT) >= 26:
                step = "pin-api"
                Context = autoclass("android.content.Context")
                ShortcutInfo = autoclass("android.content.pm.ShortcutInfo")
                ShortcutBuilder = autoclass("android.content.pm.ShortcutInfo$Builder")
                Icon = autoclass("android.graphics.drawable.Icon")
                actx = get_context()
                sm = cast("android.content.pm.ShortcutManager",
                          actx.getSystemService(Context.SHORTCUT_SERVICE))
                if not sm.isRequestPinShortcutSupported():
                    raise RuntimeError("launcher pin support nahi")
                step = "icon"
                icon = Icon.createWithResource(actx, int(ctx.getApplicationInfo().icon))
                step = "builder"
                b = ShortcutBuilder(actx, "jarvis_talk")
                b.setShortLabel("Jarvis")
                b.setLongLabel("Talk to Jarvis")
                b.setIcon(icon)
                b.setIntent(trigger_intent())
                info = b.build()
                step = "request"
                sm.requestPinShortcut(info, None)
                toast("Allow dabaiye. Na dikhe to phone ki app settings me 'Home screen shortcut' allow kijiye")
                return
            raise RuntimeError("old android")
        except Exception as exc:
            print("Home shortcut error at", step, ":", exc)
            # purana tareeka (kuch launchers, jaise MIUI, ye hi maante hain)
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                ctx = get_activity()
                ShortcutIconResource = autoclass("android.content.Intent$ShortcutIconResource")
                legacy = Intent("com.android.launcher.action.INSTALL_SHORTCUT")
                legacy.putExtra(Intent.EXTRA_SHORTCUT_NAME, "Jarvis")
                legacy.putExtra(Intent.EXTRA_SHORTCUT_INTENT, trigger_intent())
                legacy.putExtra(Intent.EXTRA_SHORTCUT_ICON_RESOURCE,
                                ShortcutIconResource.fromContext(get_context(), int(ctx.getApplicationInfo().icon)))
                ctx.sendBroadcast(legacy)
                toast("Button bhej diya. Na dikhe to app settings me 'Home screen shortcut' allow kijiye")
            except Exception as exc2:
                print("Legacy shortcut error:", exc2)
                toast("Button fail [" + step + "]: " + str(exc)[:70])

    def allow_overlay(*_):
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            Uri.parse("package:" + get_activity().getPackageName()))
            app.open_intent(intent)
            toast("Jarvis ke aage 'Allow display over other apps' chalu kijiye")
        except Exception as exc:
            print("Overlay permission error:", exc)
            toast("Settings > Apps > Jarvis > Display over other apps chalu kijiye")

    PKG_PREFIX = "org.myassistant.myvoiceassistant."
    PARTS = (("Panel (Trigger)", "JarvisTriggerActivity", "activity"),
             ("Sunne wali service", "JarvisOverlayService", "service"),
             ("Quick tile", "JarvisTileService", "service"),
             ("Alarm receiver", "JarvisAlarmReceiver", "receiver"),
             ("WhatsApp auto-send", "JarvisAccessService", "service"))

    def check_parts():
        """Installed APK me Jarvis ke Java hisse (manifest me) hain ya nahi: [(naam, hai?)]."""
        out = []
        try:
            from jnius import autoclass
            ComponentName = autoclass("android.content.ComponentName")
            act = get_activity()
            pm = act.getPackageManager()
            pkg = act.getPackageName()
            for label, cls, kind in PARTS:
                ok = True
                try:
                    cn = ComponentName(pkg, PKG_PREFIX + cls)
                    if kind == "activity":
                        pm.getActivityInfo(cn, 0)
                    elif kind == "service":
                        pm.getServiceInfo(cn, 0)
                    else:
                        pm.getReceiverInfo(cn, 0)
                except Exception:
                    ok = False
                out.append((label, ok))
        except Exception as exc:
            print("Parts check error:", exc)
        return out

    def parts_text():
        res = check_parts()
        if not res:
            return "UI v" + UI_VERSION + "  (parts check nahi ho paya)"
        lines = ["UI v" + UI_VERSION + "  |  APK ke hisse:"]
        missing = [lbl for lbl, ok in res if not ok]
        for lbl, ok in res:
            lines.append(("  OK   " if ok else "  NAHI ") + lbl)
        if missing:
            lines.append("-> Ye APK me juda hi nahi. p4a_hook.py repo me daal kar naya build kijiye.")
        return "\n".join(lines)

    def refresh_parts(*_):
        try:
            parts_label.text = parts_text()
        except Exception as exc:
            print("refresh_parts error:", exc)

    def parts_ok(cls):
        for (lbl, c, k), (_l, ok) in zip(PARTS, check_parts()):
            if c == cls:
                return ok
        return True

    def test_panel(*_):
        refresh_parts()
        if not parts_ok("JarvisTriggerActivity"):
            toast("Panel is APK me nahi hai. Neeche list dekhiye, p4a_hook.py jodkar rebuild kijiye")
            return
        try:
            get_activity().startActivity(trigger_intent())
        except Exception as exc:
            print("Panel test error:", exc)
            toast("Panel nahi khul paya: " + str(exc)[:70])

    for label, fn in [("1. Display over other apps allow karo", allow_overlay),
                      ("2. Home screen par button lagao", add_home_shortcut),
                      ("Panel abhi test karo", test_panel),
                      ("APK ke hisse dobara check karo", refresh_parts)]:
        row = ActionRow(label)
        row.bind(on_release=lambda w, f=fn: f())
        home_card.add_widget(row)
    parts_label = make_label("", 12, MUTED, height=dp(150), lines=8)
    home_card.add_widget(parts_label)
    Clock.schedule_once(refresh_parts, 1.0)
    content.add_widget(home_card)

    # 4d) "Jarvis" bolkar kahin se bhi jagana
    wake_ai_card = make_card("Hey Jarvis (kahin se bhi)")
    wake_info = make_label("", 12, MUTED, height=dp(64), lines=4)
    wake_ai_card.add_widget(wake_info)

    def read_wake_status():
        try:
            return str(get_activity().getSharedPreferences("jarvis_prefs", 0)
                       .getString("wake_status", ""))
        except Exception:
            return ""

    def refresh_wake_info(*_):
        st = read_wake_status()
        engine = "offline"
        if app.wake_enabled:
            waited = Clock.get_time() - wake_poll["since"] if wake_poll["since"] else 0
            if not st and waited > 6:
                st = ("service ne koi jawab nahi diya. Manifest (JarvisOverlayService) ya "
                      "Battery 'No restrictions' check kijiye")
            wake_info.text = "Chalu [" + engine + "]: " + (st or "shuru ho raha hai...") + \
                "\nBolo: 'Jarvis' ya 'Hey Jarvis'"
        else:
            wake_info.text = ("Band hai. On karne par Jarvis 'Jarvis' bolne ka intezaar karega "
                              "(offline, kisi key ki zaroorat nahi). Pehli baar ~40 MB model download hoga.")

    wake_poll = {"ev": None, "since": 0}

    def wake_service(action):
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Build = autoclass("android.os.Build$VERSION")
        ctx = get_context()
        intent = Intent()
        intent.setClassName(get_activity().getPackageName(),
                            "org.myassistant.myvoiceassistant.JarvisOverlayService")
        intent.setAction(action)
        if int(Build.SDK_INT) >= 26:
            comp = ctx.startForegroundService(intent)
        else:
            comp = ctx.startService(intent)
        if comp is None:
            raise RuntimeError("JarvisOverlayService manifest me nahi mili")
        wake_poll["since"] = Clock.get_time()

    def apply_wake(announce=True):
        try:
            if app.wake_enabled:
                from jnius import autoclass
                Settings = autoclass("android.provider.Settings")
                if not Settings.canDrawOverlays(get_context()):
                    toast("Pehle 'Display over other apps' allow kijiye")
                    allow_overlay()
                    return
                wake_service("org.myassistant.WAKE_ON")
                if announce:
                    toast("Hey Jarvis chalu ho raha hai")
            else:
                wake_service("org.myassistant.WAKE_OFF")
                if announce:
                    toast("Hey Jarvis band")
        except Exception as exc:
            print("Wake service error:", exc)
            toast("Wake word shuru nahi hua: " + str(exc)[:60])
        refresh_wake_info()
        poll_wake_status()

    def poll_wake_status(*_):
        """Settings khuli ho tab tak har 2 second status (download % waghera) dikhao."""
        if wake_poll["ev"] is not None:
            return

        def tick(dt):
            refresh_wake_info()
            if not view["settings"]:
                wake_poll["ev"] = None
                return False
            return True

        wake_poll["ev"] = Clock.schedule_interval(tick, 2.0)

    def on_wake_toggle(value):
        app.wake_enabled = (value == "On")
        _save_state(app)
        apply_wake()

    wake_ai_card.add_widget(Segmented(["On", "Off"], "On" if app.wake_enabled else "Off",
                                      on_wake_toggle))

    def open_battery(*_):
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(Uri.fromParts("package", get_activity().getPackageName(), None))
            app.open_intent(intent)
            toast("Battery > No restrictions aur Autostart chalu kijiye")
        except Exception as exc:
            print("Battery settings error:", exc)

    def allow_calling(*_):
        try:
            from android.permissions import request_permissions
            request_permissions(["android.permission.READ_CONTACTS",
                                 "android.permission.CALL_PHONE"])
            toast("Contacts aur Call ki permission Allow kijiye")
        except Exception as exc:
            print("Calling permission error:", exc)
            toast("Phone Settings > Apps > Jarvis > Permissions me Contacts aur Phone allow kijiye")

    def open_accessibility(*_):
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            app.open_intent(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            toast("Installed apps/Downloaded apps me 'JARVIS auto-send' On kijiye")
        except Exception as exc:
            print("Accessibility settings error:", exc)
            toast("Phone Settings > Accessibility me 'JARVIS auto-send' On kijiye")

    for label, fn in [("Calling permission allow karo (Contacts + Phone)", allow_calling),
                      ("WhatsApp auto-send: Accessibility On karo", open_accessibility),
                      ("Battery / Autostart settings", open_battery)]:
        row = ActionRow(label)
        row.bind(on_release=lambda w, f=fn: f())
        wake_ai_card.add_widget(row)
    content.add_widget(wake_ai_card)

    # 5) Privacy
    privacy_card = make_card("Data Privacy & Security")

    def manage_data(*_):
        toast("Saved history: " + str(len(app.history)) + " items")

    def open_privacy(*_):
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            package = get_activity().getPackageName()
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(Uri.fromParts("package", package, None))
            app.open_intent(intent)
        except Exception as exc:
            print("Privacy settings error:", exc)
            toast("Privacy settings khul nahi saki")

    for label, fn in [("Manage stored data", manage_data),
                      ("Clear history", clear_history),
                      ("Privacy settings", open_privacy)]:
        row = ActionRow(label)
        row.bind(on_release=lambda w, f=fn: f())
        privacy_card.add_widget(row)
    content.add_widget(privacy_card)

    # 6) Appearance
    look_card = make_card("Appearance")

    def on_theme(value):
        if value != "Dark":
            look_card_seg.select("Dark", False)
            toast(value + " theme abhi available nahi hai")

    look_card_seg = Segmented(["Light", "Dark", "System"], "Dark", on_theme)
    look_card.add_widget(look_card_seg)
    content.add_widget(look_card)

    # 6b) Orb animation
    orb_card = make_card("Orb Animation")

    orb_preview = OrbHost(orb_level, size_hint=(1, None), height=dp(150))
    orb_preview.mode = "listening"
    orb_preview.paused = True
    orb_info = make_label("", 11, MUTED, height=dp(34), lines=2)

    def show_orb_info():
        orb_info.text = ("Abhi chal raha hai: " + orb.engine +
                         "\nAdvanced = behte baadal (GPU). Safe = sabse halka, kabhi nahi atkta.")

    def on_orb_style(value):
        level = 0 if value == "Advanced" else 2
        set_orb_level(app, level)
        try:
            orb.set_level(level)                 # bina app band kiye turant badlo
            orb_preview.set_level(level)
        except Exception as exc:
            print("Orb switch error:", exc)
            toast("Orb badalne me galti: " + str(exc)[:50])
            return
        show_orb_info()
        if level == 0 and not isinstance(orb.orb, ShaderOrb):
            toast("Is phone ka GPU Advanced nahi chala paya, Texture orb chal raha hai")
        else:
            toast(("Advanced" if level == 0 else "Safe") + " orb chalu")

    orb_card.add_widget(orb_preview)
    orb_card.add_widget(Segmented(["Advanced", "Safe"],
                                  "Advanced" if orb_level == 0 else "Safe", on_orb_style))
    orb_card.add_widget(orb_info)
    show_orb_info()
    content.add_widget(orb_card)

    # 7) Integrations
    integ_card = make_card("Integration Settings")
    for label in ("Connect Smart Home", "Sync Calendar", "Link Accounts"):
        row = ActionRow(label)
        row.bind(on_release=lambda w, t=label: toast(t + " - jaldi aa raha hai"))
        integ_card.add_widget(row)
    content.add_widget(integ_card)

    # ---------------------------------------------------------- NAVIGATION --
    view = {"settings": False}

    def show_settings(*_):
        if view["settings"]:
            return
        view["settings"] = True
        chat.focus = False
        orb.paused = True
        orb_preview.paused = False
        show_orb_info()
        refresh_parts()
        refresh_history()
        refresh_wake_info()
        if app.wake_enabled:
            poll_wake_status()
        root.remove_widget(home)
        settings_page.opacity = 0
        root.add_widget(settings_page, index=len(root.children))
        Animation(opacity=1, d=0.18).start(settings_page)

    def hide_settings(*_):
        if not view["settings"]:
            return
        view["settings"] = False
        _save_state(app)
        wake_input.focus = False
        root.remove_widget(settings_page)
        root.add_widget(home, index=len(root.children))
        orb.paused = False
        orb_preview.paused = True

    def on_key(window, key, *args):
        if key == 27 and view["settings"]:      # Android back button
            hide_settings()
            return True
        return False

    Window.bind(on_keyboard=on_key)
    Window.bind(on_pause=lambda *a: unmute_beep())
    _show_settings_ui = show_settings
    _hide_settings_ui = hide_settings

    def _on_main(fn):
        def wrapper(*args):
            if threading.current_thread() is threading.main_thread():
                return fn()
            Clock.schedule_once(lambda dt: fn(), 0)
        return wrapper

    show_settings = _on_main(_show_settings_ui)
    hide_settings = _on_main(_hide_settings_ui)
    gear_btn.bind(on_release=show_settings)
    close_btn.bind(on_release=hide_settings)

    # ------------------------------------------------- CONNECT TO main.py ----
    speak_timer = {"ev": None}

    def sync_orb(text):
        if str(text).lower().startswith("listening"):
            orb.mode = "listening"
        else:
            orb.mode = "thinking" if ai["busy"] else "idle"

    # ---- Google ki "ting" awaaz band: listen shuru hote hi streams mute, jawab/bolne par unmute ----
    beep = {"muted": False, "ev": None}

    def _set_beep_mute(on):
        try:
            from jnius import autoclass
            Context = autoclass("android.content.Context")
            AudioManager = autoclass("android.media.AudioManager")
            am = app.activity.getSystemService(Context.AUDIO_SERVICE)
            flag = AudioManager.ADJUST_MUTE if on else AudioManager.ADJUST_UNMUTE
            for stream in (AudioManager.STREAM_MUSIC, AudioManager.STREAM_NOTIFICATION,
                           AudioManager.STREAM_SYSTEM):
                try:
                    am.adjustStreamVolume(stream, flag, 0)
                except Exception:               # DND policy waghera: ek stream fail ho to baaki chalein
                    pass
        except Exception as exc:
            print("Beep mute error:", exc)

    def unmute_beep(*_):
        if beep["ev"] is not None:
            beep["ev"].cancel()
            beep["ev"] = None
        if beep["muted"]:
            beep["muted"] = False
            _set_beep_mute(False)

    def mute_beep():
        if not beep["muted"]:
            beep["muted"] = True
            _set_beep_mute(True)
        if beep["ev"] is not None:
            beep["ev"].cancel()
        beep["ev"] = Clock.schedule_once(unmute_beep, 12)    # safety: kabhi mute atka na rahe

    def tts_busy():
        try:
            if speaker is not None and speaker.busy():
                return True
        except Exception:
            pass
        try:
            t = getattr(app, "tts", None)
            return bool(t is not None and t.isSpeaking())
        except Exception:
            return False

    def when_speech_done(callback, max_wait=90.0):
        """Jab tak Jarvis bol raha hai ruko, bolna khatam hote hi callback chalao."""
        st = {"t": 0.0, "started": False}

        def poll(dt):
            st["t"] += 0.3
            if tts_busy():
                st["started"] = True
            elif st["started"] or st["t"] >= 2.5 or getattr(app, "tts", None) is None:
                callback()
                return False
            if st["t"] >= max_wait:
                callback()
                return False
            return True

        return Clock.schedule_interval(poll, 0.3)

    def ai_ready():
        return bool(client is not None and app.ai_enabled and app.gemini_key.strip())

    def cancel_relisten():
        ev = ai.get("relisten")
        if ev is not None:
            ev.cancel()
            ai["relisten"] = None

    def deliver(gen, ok, reply):
        if gen != ai["gen"]:                      # beech me user ne orb dabaya: purana jawab chhodo
            return
        ai["busy"] = False
        set_status(reply)
        spoken = ai_brain.speech_text(reply) if ok else reply
        speak(spoken)
        if not ai["from_typed"]:
            def go():
                ai["relisten"] = Clock.schedule_once(lambda dt: app.listen(), 0.5)

            ai["relisten"] = when_speech_done(go)       # pura bol chuke tabhi mic khule

    def ask_ai(text):
        """Sawaal Gemini ko bhejo (background me); jawab aane par bolo."""
        ai["busy"] = True
        ai["gen"] += 1
        gen = ai["gen"]
        cancel_relisten()
        orb.mode = "thinking"
        status.text = "Soch raha hoon..."
        status.color = MUTED

        def work():
            ok, reply = client.ask(text)
            Clock.schedule_once(lambda dt: deliver(gen, ok, reply), 0)

        threading.Thread(target=work, daemon=True).start()

    app.ask_ai = ask_ai

    def set_status(message):
        message = str(message)
        if message.lower().startswith("command clear nahi hui"):
            m = re.search(r"Heard:\s*(.*)", message)
            question = (m.group(1).strip() if m else "") or ai["last"]
            if ai_ready() and question:
                ai["busy"] = True            # main.py ka peeche aane wala listen() ruk jayega
                Clock.schedule_once(lambda dt: ask_ai(question), 0)
                return
            if ai_brain is not None and not app.gemini_key:
                message += "\n(AI ke liye Settings me Gemini key daaliye)"
        if original_set_status is not None:
            original_set_status(message)          # main.py ka thread-safe version
        else:
            Clock.schedule_once(lambda dt: setattr(status, "text", message), 0)
        Clock.schedule_once(lambda dt: sync_orb(message), 0)

    def speak(text):
        if ai["busy"] and "command clear nahi hui" in str(text).lower():
            return                                 # purana "samajh nahi aaya" jawab band
        unmute_beep()                              # bolne se pehle awaaz wapas
        # TTS ready hote hi chuni hui voice lagao
        try:
            tts = getattr(app, "tts", None)
            if tts is not None and getattr(app, "_ui_voice_tts", None) is not tts:
                apply_voice()
        except Exception:
            pass
        used_eleven = False
        vid = eleven_voice_id(app)
        if speaker is not None and app.eleven_key and vid and str(text).strip():
            def fail(msg, _t=text):
                def fallback(dt):
                    toast(str(msg) + ". Phone ki awaaz se bol raha hoon")
                    if original_speak is not None:
                        original_speak(_t)
                Clock.schedule_once(fallback, 0)
            try:
                try:
                    tts0 = getattr(app, "tts", None)
                    if tts0 is not None:
                        tts0.stop()                     # phone ki awaaz chup
                except Exception:
                    pass
                speaker.speak(app.eleven_key, vid, str(text), on_error=fail)
                used_eleven = True
            except Exception as exc:
                print("eleven speak error:", exc)
        if not used_eleven and original_speak is not None:
            original_speak(text)
        length = len(str(text))

        def start(dt):
            orb.speaking = True
            if speak_timer["ev"] is not None:
                speak_timer["ev"].cancel()
            speak_timer["ev"] = Clock.schedule_once(
                lambda dt2: setattr(orb, "speaking", False),
                min(12.0, max(1.2, 0.6 + length * 0.065)))

        Clock.schedule_once(start, 0)

    AI_FIRST = ("what is ", "what's ", "whats ", "solve ", "calculate ", "compute ")
    DEVICE_WORDS = ("time", "date", "day", "battery", "name", "weather", "temperature",
                    "alarm", "timer", "volume", "brightness", "wifi", "wi-fi", "bluetooth",
                    "flashlight", "torch", "calculator")

    def should_route_ai(cmd):
        """'what is inflation' jaise sawal calculator me na jaayein, seedhe AI ke paas."""
        low = " ".join(cmd.lower().split())
        low = re.sub(r"^(hey |hello |hi )?jarvis[ ,]+", "", low)
        if not low.startswith(AI_FIRST):
            return False
        if any(w in low.split() or w in low for w in DEVICE_WORDS):
            return False
        return not ai_brain.is_simple_math(low)

    def process_command(command):
        cmd = " ".join(str(command).split())
        if actions_mod is not None:
            normalized = actions_mod.normalize_alarm_command(cmd)
            if normalized != cmd:
                command = normalized
        ai["last"] = cmd
        ai["from_typed"] = ai["typed"]
        Clock.schedule_once(lambda dt: unmute_beep(), 0)
        ai["typed"] = False
        Clock.schedule_once(lambda dt: add_history(cmd), 0)
        if ai_brain is not None:
            quick = ai_brain.creator_reply(cmd)
            if quick:                                   # turant jawab, internet ki zaroorat nahi
                ai["busy"] = True
                ai["gen"] += 1
                gen = ai["gen"]
                Clock.schedule_once(lambda dt: deliver(gen, True, quick), 0)
                return
        try_social = getattr(app, "_jarvis_try_social", None)
        if try_social is not None:
            try:
                if try_social(cmd):                     # WhatsApp message / call
                    return
            except Exception as exc:
                print("social flow error:", repr(exc))
        try_call = getattr(app, "_jarvis_try_call", None)
        if try_call is not None:
            try:
                if try_call(cmd):                       # "saket ko call karo" / "2 ko call karo"
                    return
            except Exception as exc:
                print("call flow error:", repr(exc))
        if ai_ready() and should_route_ai(cmd):
            ai["busy"] = True
            Clock.schedule_once(lambda dt: ask_ai(cmd), 0)
            return
        if original_process is not None:
            return original_process(command)

    app.set_status = set_status
    original_listen = getattr(app, "listen", None)
    if original_listen is not None:
        def listen(*args):
            if ai["busy"]:
                return None                       # AI jawab de raha hai: abhi mic mat kholo
            if tts_busy():                        # Jarvis bol raha hai: khatam hone ka intezaar
                if not ai.get("listen_wait"):
                    ai["listen_wait"] = True

                    def go():
                        ai["listen_wait"] = False
                        listen()

                    when_speech_done(go, 60.0)
                return None
            mute_beep()
            return original_listen(*args)

        app.listen = listen

    original_listen_again = getattr(app, "listen_again", None)
    if original_listen_again is not None:
        def listen_again(*args):
            mute_beep()
            return original_listen_again(*args)

        app.listen_again = listen_again
    app.speak = speak
    if original_process is not None:
        app.process_command = process_command

    def send_message(*_):
        message = chat.text.strip()
        if not message:
            return
        chat.text = ""
        set_status("You: " + message)
        ai["typed"] = True
        try:
            app.process_command(message)
        except Exception as exc:
            print("Message error:", exc)
            set_status("Message could not be processed")

    chat.bind(on_text_validate=send_message)
    send_btn.bind(on_release=send_message)

    def start_listening(*_):
        ai["gen"] += 1                      # chal raha AI jawab radd
        ai["busy"] = False
        cancel_relisten()
        try:
            if speaker is not None:
                speaker.stop()
        except Exception:
            pass
        try:
            t = getattr(app, "tts", None)
            if t is not None:
                t.stop()                          # orb dabane par Jarvis chup ho jaye
        except Exception:
            pass
        orb.mode = "listening"
        set_status("Listening...")
        try:
            if hasattr(app, "listen_again"):
                app.listen_again()       # pehle purani session cancel, phir naya
            else:
                app.listen()
        except Exception as exc:
            print("Orb tap error:", exc)

    orb.bind(on_release=start_listening)

    # Home screen button / shortcut se app khule to turant sunna shuru
    def talk_from_shortcut(*_):
        if view["settings"]:
            hide_settings()
        start_listening()

    def on_new_intent(intent):
        try:
            if str(intent.getAction()) == TALK_ACTION:
                Clock.schedule_once(talk_from_shortcut, 0.4)
        except Exception as exc:
            print("New intent error:", exc)

    try:
        from android import activity as android_activity
        android_activity.bind(on_new_intent=on_new_intent)
    except Exception as exc:
        print("on_new_intent bind skipped:", exc)

    # Purane code ke saath compatibility (main.py in naamon ko use karta hai)
    app.status_label = status
    app.core_widget = orb
    app.chat_input = chat
    app.toggle_voice_selection = show_settings
    app.open_jarvis_settings = show_settings
    # NOTE: app.open_settings main.py ka apna method hai (wifi/display/... Android settings kholta hai);
    # use yahan override mat karo, warna 'wifi settings kholo' par UI kharab ho jata hai.
    app.start_jarvis_listening = start_listening

    app.calc_panel = BoxLayout(orientation="vertical", size_hint_y=None, height=0,
                               opacity=0, disabled=True)
    app.calc_question_label = make_label("", 10)
    app.calc_answer_label = make_label("", 12, CYAN, True)
    app.calc_panel.add_widget(app.calc_question_label)
    app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display = type("VoiceOnlyDisplay", (), {"text": ""})()
    app.calc_angle_mode = "DEG"
    app.calc_history = []
    app.calc_buttons = []
    app.root_layout = root

    apply_voice()
    refresh_ai_info()
    _sync_prefs(app)
    if app.wake_enabled:
        Clock.schedule_once(lambda dt: apply_wake(False), 3.0)    # app khulte hi wake word wapas chalu
    refresh_wake_info()
    if actions_mod is not None:
        try:
            actions_mod.install_actions(app)       # alarm / timer / reminder fix
        except Exception as exc:
            print("install_actions failed:", exc)
    try:
        import jarvis_calls
        jarvis_calls.install_calls(app)            # naam se call + kai match par chunav
    except Exception as exc:
        print("install_calls failed:", exc)
    try:
        import jarvis_social
        jarvis_social.install_social(app)          # WhatsApp message / voice / video call
    except Exception as exc:
        print("install_social failed:", exc)
    return root
