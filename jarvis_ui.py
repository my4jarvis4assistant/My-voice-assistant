"""JARVIS v0.30 - professional UI module (main.py ke saath kaam karta hai).

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

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
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
VOICES = {
    "Male Alpha": (0.85, 1.00),
    "Female Beta": (1.25, 1.00),
    "Formal Gamma": (0.95, 0.90),
    "Casual Delta": (1.10, 1.05),
}


# ---------------------------------------------------------------- TEXTURES --
def _make_texture(w, h, pixel_fn):
    """pixel_fn(u, v) -> (r, g, b, a); u, v 0..1 (v neeche se upar)."""
    buf = bytearray(w * h * 4)
    i = 0
    for y in range(h):
        v = y / (h - 1)
        for x in range(w):
            r, g, b, a = pixel_fn(x / (w - 1), v)
            buf[i] = int(255 * min(1.0, max(0.0, r)))
            buf[i + 1] = int(255 * min(1.0, max(0.0, g)))
            buf[i + 2] = int(255 * min(1.0, max(0.0, b)))
            buf[i + 3] = int(255 * min(1.0, max(0.0, a)))
            i += 4
    tex = Texture.create(size=(w, h), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.mag_filter = "linear"
    tex.min_filter = "linear"
    return tex


def orb_pixel(u, v):
    """3D glass sphere: roshni upar-left se, neeche gehra neela, teal kinaara."""
    lx, ly, lz = -0.45, 0.55, 0.70
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    dx, dy = (u - 0.5) * 2, (v - 0.5) * 2
    d = math.hypot(dx, dy)
    if d >= 1:
        return 0.10, 0.35, 0.90, 0.0
    nz = math.sqrt(1 - d * d)
    lam = max(0.0, dx * lx + dy * ly + nz * lz)
    t = lam ** 0.9
    r = 0.05 + 0.45 * t
    g = 0.20 + 0.58 * t
    b = 0.68 + 0.32 * t
    cloud = 0.5 + 0.5 * math.sin(dx * 5 + dy * 3) * math.sin(dy * 4 - dx * 2)
    k = 0.10 * cloud * lam
    spec = lam ** 28 * 0.55
    rim = d ** 5 * 0.35
    r = r + k + spec
    g = g + k + spec + rim * 0.5
    b = b + k + spec + rim * 0.3
    alpha = min(1.0, (1 - d) * 40)          # smooth kinaara
    return r, g, b, alpha


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
        if name == "orb":
            _TEX[name] = _make_texture(128, 128, orb_pixel)
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


class IconButton(ButtonBehavior, Widget):
    """Canvas se bana icon button (font/image ki zaroorat nahi)."""

    def __init__(self, kind, circle=False, **kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.circle = circle
        self.bind(pos=self._draw, size=self._draw, state=self._draw)
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.center
        side = min(self.width, self.height)
        a = 0.55 if self.state == "down" else 1.0
        with self.canvas:
            if self.circle:
                Color(*PILL)
                Ellipse(pos=(x - side / 2, y - side / 2), size=(side, side))
                Color(*EDGE)
                Line(circle=(x, y, side / 2), width=1)
            if self.kind == "send":
                Color(CYAN[0], CYAN[1], CYAN[2], a)
            else:
                Color(0.80, 0.86, 0.85, a)
            if self.kind == "gear":
                r = side * 0.20
                Line(circle=(x, y, r), width=dp(1.5))
                Line(circle=(x, y, r * 0.42), width=dp(1.4))
                for i in range(8):
                    ang = math.pi * 2 * i / 8
                    Line(points=[x + math.cos(ang) * r * 1.15, y + math.sin(ang) * r * 1.15,
                                 x + math.cos(ang) * r * 1.65, y + math.sin(ang) * r * 1.65],
                         width=dp(2.2), cap="round")
            else:
                s = side * 0.30
                Line(points=[x - s, y - s * .25, x + s, y + s * .45, x + s * .12,
                             y - s * .48, x - s, y - s * .25],
                     close=True, width=dp(1.7), joint="round")
                Line(points=[x - s * .10, y - s * .03, x + s, y + s * .45], width=dp(1.4))
                Line(points=[x - s * .10, y - s * .03, x - s * .32, y - s * .38],
                     width=dp(1.4))


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
        r = min(self.width, self.height) * 0.18
        rr = r * (1 + 2.2 * self.pulse)
        with self.canvas:
            Color(GREEN[0], GREEN[1], GREEN[2], 0.35 * (1 - self.pulse))
            Ellipse(pos=(x - rr, y - rr), size=(rr * 2, rr * 2))
            Color(*GREEN)
            Ellipse(pos=(x - r, y - r), size=(r * 2, r * 2))


class Orb(ButtonBehavior, Widget):
    """Glass orb + glow + andar chalti wave. mode: idle / listening, speaking: bool."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "idle"
        self.speaking = False
        self.paused = False
        self._phase = 0.0
        self._t = 0.0
        self._amp = 0.10
        self._d = 1.0
        with self.canvas:
            self._glow_c = Color(1, 1, 1, 0.8)
            self._glow = Rectangle(texture=get_texture("glow"))
            Color(1, 1, 1, 1)
            self._orb = Rectangle(texture=get_texture("orb"))
            Color(0.92, 0.98, 1, 0.9)
            self._wave = Line(points=[0, 0, 0, 0], width=dp(1.6), cap="round",
                              joint="round")
        self.bind(pos=self._tick, size=self._tick)
        self._ev = Clock.schedule_interval(self._tick, 1 / 30.0)

    def _tick(self, dt=0, *_):
        if not isinstance(dt, (int, float)):
            dt = 0                      # pos/size change se bula: sirf layout update
        elif self.paused:
            return                      # settings khuli hai: animation roko
        self._t += dt
        if self.speaking:
            target, speed = 0.85, 8.0
        elif self.mode == "listening":
            target, speed = 1.0, 5.5
        else:
            target, speed = 0.10, 1.6
        self._amp += (target - self._amp) * min(1.0, dt * 6.0)
        self._phase += dt * speed

        cx, cy = self.center
        side = min(self.width, self.height)
        d = side * 0.56
        self._d = d
        pulse = 0.5 + 0.5 * math.sin(self._t * 2.2)
        g = side * (0.86 + 0.08 * pulse * (0.4 + self._amp))
        self._glow.size = (g, g)
        self._glow.pos = (cx - g / 2, cy - g / 2)
        self._glow_c.a = 0.70 + 0.30 * pulse
        self._orb.size = (d, d)
        self._orb.pos = (cx - d / 2, cy - d / 2)

        n = 40
        span = d * 0.80
        x0 = cx - span / 2
        y0 = cy - d * 0.04
        pts = []
        for i in range(n):
            f = i / (n - 1)
            env = math.sin(math.pi * f) ** 1.2
            val = (math.sin(f * 9 + self._phase) * 0.65
                   + math.sin(f * 15 - self._phase * 0.8) * 0.35)
            pts += [x0 + span * f, y0 + self._amp * d * 0.075 * env * val]
        self._wave.points = pts


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
                       padding=[dp(22), dp(8), dp(18), dp(8)], spacing=dp(10),
                       pos_hint={"top": 1})
    title = make_label("JARVIS", 26, WHITE)
    title.size_hint_x = None
    title.width = dp(124)
    header.add_widget(title)
    header.add_widget(StatusDot(size_hint=(None, None), size=(dp(26), dp(26)),
                                pos_hint={"center_y": 0.52}))
    header.add_widget(Widget())
    gear_btn = IconButton("gear", circle=True, size_hint=(None, None),
                          size=(dp(46), dp(46)), pos_hint={"center_y": 0.5})
    header.add_widget(gear_btn)
    home.add_widget(header)

    orb = Orb(size_hint=(1, 0.44), pos_hint={"center_x": 0.5, "center_y": 0.60})
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
