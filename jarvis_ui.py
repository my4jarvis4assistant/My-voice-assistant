"""JARVIS v0.31 - professional UI module (main.py ke saath kaam karta hai).

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
            _TEX[name] = _make_texture(96, 96, make_cloud_pixel_fn(), periodic=True)
        elif name == "glow":
            _TEX[name] = _make_texture(64, 64, glow_pixel)
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
        self._t = 0.0
        self._lvl = 0.0          # 0 = shaant, 1 = poori halchal
        self._flow = 0.012       # baadal ki raftaar
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

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0                      # pos/size change se bula: sirf layout update
        elif self.paused:
            return                      # settings khuli hai: animation roko
        self._t += dt
        t = self._t

        # --- halchal ka star (voice jaisa utaar-chadhaav jab bol raha ho) ---
        if self.speaking:
            target = 0.55 + 0.45 * (0.6 * abs(math.sin(t * 5.1))
                                    + 0.4 * abs(math.sin(t * 2.3 + 1.0)))
            flow_t = 0.075
        elif self.mode == "listening":
            target = 0.30 + 0.20 * math.sin(t * 2.2)
            flow_t = 0.035
        else:
            target, flow_t = 0.0, 0.012
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

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
        v += a * noise(p);
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

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0                      # pos/size change se bula: sirf layout update
        elif self.paused:
            return                      # settings khuli hai: animation roko
        self._t += dt
        t = self._t
        if self.speaking:
            target = 0.65 + 0.35 * (0.6 * abs(math.sin(t * 5.1))
                                    + 0.4 * abs(math.sin(t * 2.3 + 1.0)))
        elif self.mode == "listening":
            target = 0.55 + 0.10 * math.sin(t * 2.2)
        else:
            target = 0.0
        e = self._e = self._e + (target - self._e) * min(1.0, dt * 3.0)
        self._time += dt * (0.55 + 0.9 * e)

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


def make_orb(**kwargs):
    """Shader orb agar chal sakta hai, warna texture wala orb."""
    if _shader_supported():
        try:
            return ShaderOrb(**kwargs)
        except Exception as exc:
            print("JARVIS ShaderOrb failed, using TextureOrb:", exc)
    return TextureOrb(**kwargs)


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


def _save_state(app):
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
            }, fh, ensure_ascii=False)
    except Exception as exc:
        print("JARVIS UI state save error:", exc)


# ================================================================ BUILD UI ===
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
    if app.selected_voice not in VOICES:
        app.selected_voice = "Male Alpha"
    app.wake_word = state.get("wake_word", "Hey JARVIS")
    app.verbosity = state.get("verbosity", "Balanced")
    app.theme = "Dark"
    app.history = list(state.get("history", []))

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

    orb = make_orb(size_hint=(1, 0.44), pos_hint={"center_x": 0.5, "center_y": 0.60})
    home.add_widget(orb)

    status = Label(text="Ready when you are", font_size=sp(17), color=MUTED,
                   halign="center", valign="top", max_lines=2,
                   size_hint=(0.88, None), height=dp(56),
                   pos_hint={"center_x": 0.5, "top": 0.385})
    status.bind(size=lambda obj, val: setattr(obj, "text_size", (val[0], val[1])))
    home.add_widget(status)

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
    content.add_widget(voice_card)

    def apply_voice(*_):
        """TTS ki pitch/speed badlo (TTS tab tak ready na ho to skip)."""
        tts = getattr(app, "tts", None)
        if tts is None:
            return
        pitch, rate = VOICES.get(app.selected_voice, (1.0, 1.0))

        def work():
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
            package = app.activity.getPackageName()
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
        refresh_history()
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

    def on_key(window, key, *args):
        if key == 27 and view["settings"]:      # Android back button
            hide_settings()
            return True
        return False

    Window.bind(on_keyboard=on_key)
    gear_btn.bind(on_release=show_settings)
    close_btn.bind(on_release=hide_settings)

    # ------------------------------------------------- CONNECT TO main.py ----
    speak_timer = {"ev": None}

    def sync_orb(text):
        orb.mode = "listening" if str(text).lower().startswith("listening") else "idle"

    def set_status(message):
        message = str(message)
        if original_set_status is not None:
            original_set_status(message)          # main.py ka thread-safe version
        else:
            Clock.schedule_once(lambda dt: setattr(status, "text", message), 0)
        Clock.schedule_once(lambda dt: sync_orb(message), 0)

    def speak(text):
        # TTS ready hote hi chuni hui voice lagao
        try:
            tts = getattr(app, "tts", None)
            if tts is not None and getattr(app, "_ui_voice_tts", None) is not tts:
                apply_voice()
        except Exception:
            pass
        if original_speak is not None:
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

    def process_command(command):
        Clock.schedule_once(lambda dt: add_history(command), 0)
        if original_process is not None:
            return original_process(command)

    app.set_status = set_status
    app.speak = speak
    if original_process is not None:
        app.process_command = process_command

    def send_message(*_):
        message = chat.text.strip()
        if not message:
            return
        chat.text = ""
        set_status("You: " + message)
        try:
            app.process_command(message)
        except Exception as exc:
            print("Message error:", exc)
            set_status("Message could not be processed")

    chat.bind(on_text_validate=send_message)
    send_btn.bind(on_release=send_message)

    def start_listening(*_):
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

    # Purane code ke saath compatibility (main.py in naamon ko use karta hai)
    app.status_label = status
    app.core_widget = orb
    app.chat_input = chat
    app.toggle_voice_selection = show_settings
    app.open_jarvis_settings = show_settings
    app.open_settings = show_settings
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
    return root
