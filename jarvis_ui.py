"""JARVIS UI module: visual layout and animated logo kept separate from main.py."""
import math
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle

class JarvisCore(Widget):
    """Procedurally drawn, animated JARVIS reactor logo (no external assets)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phase = 0.0
        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_interval(self._tick, 1.0 / 24.0)
        self.redraw()

    def _tick(self, dt):
        self.phase = (self.phase + dt * 0.75) % (2 * math.pi)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        radius = max(dp(35), min(self.width, self.height) * 0.34)
        pulse = 1.0 + 0.035 * math.sin(self.phase * 2.0)
        with self.canvas:
            # Soft cyan aura and deep central reactor.
            Color(0.02, 0.62, 1.0, 0.055)
            Ellipse(pos=(cx-radius*1.28, cy-radius*1.28), size=(radius*2.56, radius*2.56))
            Color(0.02, 0.55, 1.0, 0.10)
            Ellipse(pos=(cx-radius*1.08, cy-radius*1.08), size=(radius*2.16, radius*2.16))
            Color(0.015, 0.035, 0.075, 1)
            Ellipse(pos=(cx-radius*0.78, cy-radius*0.78), size=(radius*1.56, radius*1.56))
            # Layered rings.
            Color(0.12, 0.78, 1.0, 0.95)
            Line(circle=(cx, cy, radius*pulse), width=dp(1.5))
            Color(0.20, 0.55, 1.0, 0.72)
            Line(circle=(cx, cy, radius*0.86), width=dp(1.0))
            Color(0.20, 0.90, 1.0, 0.90)
            Line(circle=(cx, cy, radius*0.68), width=dp(1.2))
            # Segmented rotating arcs.
            for ring_r, count, offset, arc_len in ((radius*1.12, 4, self.phase, 0.48), (radius*0.94, 6, -self.phase*1.3, 0.25)):
                for i in range(count):
                    start = offset + (2*math.pi*i/count)
                    pts = []
                    for j in range(17):
                        a = start + arc_len*j/16.0
                        pts.extend((cx + ring_r*math.cos(a), cy + ring_r*math.sin(a)))
                    Color(0.10, 0.78, 1.0, 0.92 if ring_r > radius else 0.68)
                    Line(points=pts, width=dp(2.0 if ring_r > radius else 1.4))
            # Inner glowing core.
            Color(0.05, 0.58, 1.0, 0.22)
            Ellipse(pos=(cx-radius*0.49, cy-radius*0.49), size=(radius*0.98, radius*0.98))
            Color(0.12, 0.85, 1.0, 0.92)
            Line(circle=(cx, cy, radius*0.43), width=dp(1.4))
            Color(0.36, 0.94, 1.0, 1)
            Ellipse(pos=(cx-radius*0.22, cy-radius*0.22), size=(radius*0.44, radius*0.44))
            Color(0.015, 0.09, 0.16, 1)
            Ellipse(pos=(cx-radius*0.16, cy-radius*0.16), size=(radius*0.32, radius*0.32))
            # Orbit nodes.
            for i in range(8):
                a = self.phase * (1 if i % 2 else -1) + (2*math.pi*i/8)
                rr = radius * (1.12 if i % 2 == 0 else 0.86)
                x, y = cx + rr*math.cos(a), cy + rr*math.sin(a)
                Color(0.35, 0.94, 1.0, 0.95)
                Ellipse(pos=(x-dp(2.3), y-dp(2.3)), size=(dp(4.6), dp(4.6)))


def build_jarvis_ui(app):
    """Build and return the UI, attaching widget references to the app."""
    # v0.28 premium futuristic interface. Existing command logic stays unchanged.
    app.root_layout = BoxLayout(
        orientation="vertical", spacing=dp(7), padding=[dp(14), dp(10), dp(14), dp(10)]
    )
    with app.root_layout.canvas.before:
        Color(0.012, 0.022, 0.048, 1)
        app._background_rect = RoundedRectangle(pos=app.root_layout.pos, size=app.root_layout.size, radius=[0])
    app.root_layout.bind(pos=app._update_background, size=app._update_background)

    header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(62), spacing=dp(1))
    title_label = Label(
        text="J.A.R.V.I.S", font_size="27sp", bold=True,
        color=(0.35, 0.88, 1, 1), size_hint_y=None, height=dp(36)
    )
    subtitle_label = Label(
        text="PERSONAL AI  /  VOICE INTERFACE", font_size="10sp",
        color=(0.35, 0.62, 0.78, 1), size_hint_y=None, height=dp(20)
    )
    header.add_widget(title_label)
    header.add_widget(subtitle_label)
    app.root_layout.add_widget(header)

    app.core_widget = JarvisCore(size_hint_y=0.56)
    app.root_layout.add_widget(app.core_widget)

    app.status_label = Label(
        text="JARVIS starting...", font_size="16sp", bold=True,
        color=(0.46, 0.91, 1, 1), size_hint_y=None, height=dp(44),
        halign="center", valign="middle"
    )
    app.status_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    app.root_layout.add_widget(app.status_label)

    app.calc_panel = BoxLayout(
        orientation="vertical", spacing=dp(5), size_hint_y=None, height=dp(118),
        padding=[dp(12), dp(7), dp(12), dp(7)]
    )
    with app.calc_panel.canvas.before:
        Color(0.025, 0.055, 0.095, 0.96)
        app._calc_panel_bg = RoundedRectangle(pos=app.calc_panel.pos, size=app.calc_panel.size, radius=[dp(14)])
    app.calc_panel.bind(pos=app._update_calc_panel_bg, size=app._update_calc_panel_bg)
    app.calc_question_label = Label(
        text="QUESTION  /  Apna maths question boliye", font_size="13sp",
        color=(0.52, 0.69, 0.79, 1), size_hint_y=None, height=dp(38),
        halign="left", valign="middle"
    )
    app.calc_question_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    app.calc_answer_label = Label(
        text="ANSWER  /  --", font_size="21sp", bold=True,
        color=(0.35, 0.91, 1, 1), size_hint_y=None, height=dp(48),
        halign="left", valign="middle"
    )
    app.calc_answer_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    app.calc_panel.add_widget(app.calc_question_label)
    app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display = TextInput(text="", hint_text="Optional: type expression", multiline=False, readonly=False, font_size="22sp", size_hint_y=None, height=dp(48))
    # Voice-first UI: no manual keypad or bottom calculator control buttons.
    app.calc_angle_mode = "DEG"
    app.calc_history = []
    grid = GridLayout(cols=5, spacing=dp(4), size_hint_y=None, height=dp(260))
    app.calc_buttons = [
        ("AC", "clear"), ("DEL", "delete"), ("(", "("), (")", ")"), ("÷", "/"),
        ("sin", "sin("), ("cos", "cos("), ("tan", "tan("), ("√", "sqrt("), ("x²", "**2"),
        ("7", "7"), ("8", "8"), ("9", "9"), ("×", "*"), ("π", "pi"),
        ("4", "4"), ("5", "5"), ("6", "6"), ("−", "-"), ("e", "e"),
        ("1", "1"), ("2", "2"), ("3", "3"), ("+", "+"), ("%", "%"),
        ("0", "0"), (".", "."), ("xʸ", "**"), ("log", "log10("), ("=", "equals")
    ]
    for label, value in app.calc_buttons:
        b = Button(text=label, font_size="16sp", size_hint_y=None, height=dp(40))
        b.bind(on_release=lambda btn, v=value: app._calculator_button(v))
        grid.add_widget(b)
    app.root_layout.add_widget(app.calc_panel)

    # v0.26 hands-free calculator: no separate Open Scientific Calculator button.
    # The calculator question/answer panel is visible as soon as the app opens.


    return app.root_layout
