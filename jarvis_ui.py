"""JARVIS UI module: Safe, clean and crash-free professional layout."""
import math
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.uix.scrollview import ScrollView

class JarvisCore(Widget):
    """Procedurally drawn, animated JARVIS reactor logo."""

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
        radius = max(dp(25), min(self.width, self.height) * 0.35)
        pulse = 1.0 + 0.035 * math.sin(self.phase * 2.0)
        with self.canvas:
            Color(0.02, 0.62, 1.0, 0.06)
            Ellipse(pos=(cx-radius*1.2, cy-radius*1.2), size=(radius*2.4, radius*2.4))
            Color(0.015, 0.035, 0.075, 1)
            Ellipse(pos=(cx-radius*0.8, cy-radius*0.8), size=(radius*1.6, radius*1.6))
            Color(0.12, 0.78, 1.0, 0.95)
            Line(circle=(cx, cy, radius*pulse), width=dp(1.5))
            Color(0.20, 0.90, 1.0, 0.90)
            Line(circle=(cx, cy, radius*0.7), width=dp(1.2))
            Color(0.12, 0.85, 1.0, 0.92)
            Line(circle=(cx, cy, radius*0.4), width=dp(1.4))
            Color(0.36, 0.94, 1.0, 1)
            Ellipse(pos=(cx-radius*0.2, cy-radius*0.2), size=(radius*0.4, radius*0.4))


def build_jarvis_ui(app):
    """Build and return safe professional UI layout without crash risks."""
    root = BoxLayout(
        orientation='vertical',
        spacing=dp(6),
        padding=[dp(10), dp(10), dp(10), dp(10)]
    )

    # Deep obsidian black background
    with root.canvas.before:
        Color(0.012, 0.022, 0.048, 1)
        app._background_rect = RoundedRectangle(pos=root.pos, size=root.size, radius=[0])
    root.bind(pos=app._update_background, size=app._update_background)

    # ========================================================
    # TOP HEADER SECTION (Alex AI + Online Dot + Settings Gear)
    # ========================================================
    header_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(48),
        padding=[dp(5), dp(2), dp(5), dp(2)]
    )

    title_box = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_x=0.85)
    title_label = Label(
        text="Alex AI",
        font_size='22sp',
        bold=True,
        color=(0.35, 0.88, 1, 1),
        halign='left',
        valign='middle'
    )
    title_label.bind(size=title_label.setter('text_size'))
    title_box.add_widget(title_label)

    online_dot = Widget(size_hint=(None, None), size=dp(10), pos_hint={'center_y': 0.5})
    with online_dot.canvas.before:
        Color(0, 1, 0.4, 1)
        Ellipse(pos=online_dot.pos, size=online_dot.size)
    title_box.add_widget(online_dot)
    header_layout.add_widget(title_box)

    # Settings Button
    settings_btn = Button(
        text="⚙",
        font_size='20sp',
        size_hint=(None, None),
        size=dp(40),
        pos_hint={'center_y': 0.5},
        background_color=(0, 0, 0, 0),
        color=(0.35, 0.88, 1, 1)
    )
    header_layout.add_widget(settings_btn)
    root.add_widget(header_layout)

    # Status Label
    app.status_label = Label(
        text="Alex AI online...",
        font_size='13sp',
        bold=True,
        color=(0.46, 0.91, 1, 1),
        size_hint=(1, None),
        height=dp(28),
        halign='center',
        valign='middle'
    )
    app.status_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    root.add_widget(app.status_label)

    # ========================================================
    # MIDDLE CONTENT AREA (Visualizer & Voice Options Panel)
    # ========================================================
    middle_box = BoxLayout(
        orientation='horizontal',
        size_hint=(1, 1),
        spacing=dp(8)
    )

    # Left side: Visualizer + Chat Bubbles container
    left_content = BoxLayout(
        orientation='vertical',
        size_hint=(0.6, 1),
        spacing=dp(6)
    )

    # Chat bubble sample 1
    chat_1 = Label(
        text="Alex AI voice interface ready.",
        font_size='10sp',
        color=(0.7, 0.9, 1, 1),
        size_hint=(1, None),
        height=dp(32),
        halign='left',
        valign='middle',
        padding=[dp(8), dp(4)]
    )
    chat_1.bind(size=chat_1.setter('text_size'))
    with chat_1.canvas.before:
        Color(0.04, 0.12, 0.22, 0.85)
        RoundedRectangle(pos=chat_1.pos, size=chat_1.size, radius=[dp(10)])
    left_content.add_widget(chat_1)

    # Core Visualizer
    core_view = JarvisCore(size_hint=(1, 1))
    left_content.add_widget(core_view)

    # Chat bubble sample 2
    chat_2 = Label(
        text="Listening for commands...",
        font_size='10sp',
        color=(0.7, 0.95, 1, 1),
        size_hint=(1, None),
        height=dp(32),
        halign='left',
        valign='middle',
        padding=[dp(8), dp(4)]
    )
    chat_2.bind(size=chat_2.setter('text_size'))
    with chat_2.canvas.before:
        Color(0.04, 0.12, 0.22, 0.85)
        RoundedRectangle(pos=chat_2.pos, size=chat_2.size, radius=[dp(10)])
    left_content.add_widget(chat_2)

    middle_box.add_widget(left_content)

    # Right side: Voice Selection Panel (Collapsible via Settings gear)
    settings_panel = BoxLayout(
        orientation='vertical',
        size_hint=(0.4, 1),
        padding=dp(8),
        spacing=dp(4)
    )
    with settings_panel.canvas.before:
        Color(0.03, 0.07, 0.14, 0.95)
        RoundedRectangle(pos=settings_panel.pos, size=settings_panel.size, radius=[dp(10)])
        Color(0.1, 0.6, 0.9, 0.4)
        Line(rounded_rectangle=(settings_panel.x, settings_panel.y, settings_panel.width, settings_panel.height, dp(10)), width=1)

    panel_title = Label(
        text="Voice Selection",
        font_size='11sp',
        bold=True,
        color=(0.35, 0.88, 1, 1),
        size_hint=(1, None),
        height=dp(22)
    )
    settings_panel.add_widget(panel_title)

    voices = ["Alate troiina", "Tioteerabuh", "Wardsolstae", "Suienger fight", "Mginall shceratioe", "Etseoabrck"]
    voices_scroll = ScrollView(size_hint=(1, 1))
    voices_col = BoxLayout(orientation='vertical', spacing=dp(3), size_hint_y=None)
    voices_col.bind(minimum_height=voices_col.setter('height'))

    for v in voices:
        vb = Button(
            text=v,
            font_size='9sp',
            size_hint=(1, None),
            height=dp(28),
            background_color=(0, 0, 0, 0),
            color=(0.8, 0.9, 1, 1),
            halign='left'
        )
        vb.bind(size=vb.setter('text_size'))
        voices_col.add_widget(vb)

    voices_scroll.add_widget(voices_col)
    settings_panel.add_widget(voices_scroll)

    wake_lbl = Label(
        text="Wake: Chene",
        font_size='9sp',
        color=(0.5, 0.7, 0.85, 1),
        size_hint=(1, None),
        height=dp(24),
        halign='left'
    )
    wake_lbl.bind(size=wake_lbl.setter('text_size'))
    settings_panel.add_widget(wake_lbl)

    middle_box.add_widget(settings_panel)
    root.add_widget(middle_box)

    # Toggle panel visibility smoothly when settings gear is clicked
    def toggle_panel(instance):
        settings_panel.opacity = 0 if settings_panel.opacity == 1 else 1
    settings_btn.bind(on_press=toggle_panel)

    # ========================================================
    # QUICK ACTION BUTTONS BAR (Alarms, Reminders, Weather, Messages)
    # ========================================================
    quick_actions = GridLayout(
        cols=4,
        spacing=dp(6),
        size_hint=(1, None),
        height=dp(52)
    )

    actions_data = [
        ("⏰ Alarms", lambda x: app.set_status("Alarms menu")),
        ("📅 Reminders", lambda x: app.open_calendar()),
        ("⛅ Weather", lambda x: app.google_web_search("weather forecast")),
        ("💬 Messages", lambda x: app.open_messages())
    ]

    for title, callback in actions_data:
        btn = Button(
            text=title,
            font_size='9sp',
            halign='center',
            valign='middle',
            background_color=(0, 0, 0, 0),
            color=(0.8, 0.95, 1, 1)
        )
        btn.bind(size=btn.setter('text_size'))
        btn.bind(on_press=callback)
        
        with btn.canvas.before:
            Color(0.04, 0.1, 0.18, 0.85)
            RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            Color(0.1, 0.6, 0.9, 0.35)
            Line(rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, dp(8)), width=1)
        
        quick_actions.add_widget(btn)
    root.add_widget(quick_actions)

    # ========================================================
    # BOTTOM BAR & BIOMETRIC FINGERPRINT SCANNER
    # ========================================================
    bottom_bar = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(48),
        padding=[dp(8), dp(2), dp(8), dp(2)],
        spacing=dp(8)
    )
    with bottom_bar.canvas.before:
        Color(0.03, 0.07, 0.14, 0.95)
        RoundedRectangle(pos=bottom_bar.pos, size=bottom_bar.size, radius=[dp(10)])
        Color(0.1, 0.6, 0.9, 0.4)
        Line(rounded_rectangle=(bottom_bar.x, bottom_bar.y, bottom_bar.width, bottom_bar.height, dp(10)), width=1)

    history_btn = Button(
        text="History",
        font_size='10sp',
        size_hint=(0.3, 1),
        background_color=(0, 0, 0, 0),
        color=(0.7, 0.85, 1, 1)
    )
    history_btn.bind(on_press=lambda x: app.set_status("Voice history active"))

    fingerprint_btn = Button(
        text="🔒",
        font_size='16sp',
        size_hint=(None, None),
        size=dp(38),
        pos_hint={'center_y': 0.5},
        background_color=(0, 0, 0, 0),
        color=(0, 0.9, 1, 1)
    )
    fingerprint_btn.bind(on_press=lambda x: app.speak("Biometric verification active."))

    settings_shortcut_btn = Button(
        text="Settings",
        font_size='10sp',
        size_hint=(0.3, 1),
        background_color=(0, 0, 0, 0),
        color=(0.7, 0.85, 1, 1)
    )
    settings_shortcut_btn.bind(on_press=toggle_panel)

    bottom_bar.add_widget(history_btn)
    bottom_bar.add_widget(fingerprint_btn)
    bottom_bar.add_widget(settings_shortcut_btn)
    root.add_widget(bottom_bar)

    # Required variables referenced by main.py
    app.calc_angle_mode = "DEG"
    app.calc_history = []

    return root
