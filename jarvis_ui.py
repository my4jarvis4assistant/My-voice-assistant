"""JARVIS UI module: Professional futuristic layout integrated cleanly with main.py."""
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
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout

class JarvisCore(Widget):
    """Procedurally drawn, animated JARVIS reactor logo for visualizer area."""

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
        radius = max(dp(30), min(self.width, self.height) * 0.32)
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


def build_jarvis_ui(app):
    """Build and return the professional UI layout, attaching widget references to the app."""
    root = FloatLayout()

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
        height=dp(55),
        pos_hint={'top': 0.98, 'center_x': 0.5},
        padding=[dp(18), dp(5), dp(18), dp(5)]
    )

    title_box = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_x=0.85)
    title_label = Label(
        text="Alex AI",
        font_size='24sp',
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

    # Top Right Settings Gear Button
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

    # Status Label for feedback
    app.status_label = Label(
        text="Alex AI online...",
        font_size='13sp',
        bold=True,
        color=(0.46, 0.91, 1, 1),
        size_hint=(1, None),
        height=dp(25),
        pos_hint={'top': 0.90, 'center_x': 0.5},
        halign='center',
        valign='middle'
    )
    app.status_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    root.add_widget(app.status_label)

    # ========================================================
    # MAIN CENTER AREA (Visualizer + Chat Bubbles)
    # ========================================================
    center_area = FloatLayout(
        size_hint=(1, None),
        height=dp(340),
        pos_hint={'center_x': 0.5, 'center_y': 0.54}
    )

    # Holographic Reactor / Visualizer in Center-Left
    core_view = JarvisCore(
        size_hint=(None, None),
        size=(dp(160), dp(160)),
        pos_hint={'center_x': 0.32, 'center_y': 0.52}
    )
    center_area.add_widget(core_view)

    # Chat Bubbles (User & AI conversation layout)
    user_bubble_1 = Label(
        text="Eapholecrocotinfs legsts - Ce",
        font_size='11sp',
        color=(0.7, 0.9, 1, 1),
        size_hint=(None, None),
        size=(dp(200), dp(28)),
        pos_hint={'center_x': 0.32, 'center_y': 0.82},
        halign='left',
        valign='middle'
    )
    user_bubble_1.bind(size=user_bubble_1.setter('text_size'))
    with user_bubble_1.canvas.before:
        Color(0.04, 0.12, 0.22, 0.85)
        RoundedRectangle(pos=user_bubble_1.pos, size=user_bubble_1.size, radius=[dp(14)])
        Color(0.1, 0.6, 0.9, 0.3)
        Line(rounded_rectangle=(user_bubble_1.x, user_bubble_1.y, user_bubble_1.width, user_bubble_1.height, dp(14)), width=1)
    center_area.add_widget(user_bubble_1)

    ai_bubble_1 = Label(
        text="Suretiers dnopiity of A clara yetyer temanie of tromathy AIT",
        font_size='11sp',
        color=(0.7, 0.95, 1, 1),
        size_hint=(None, None),
        size=(dp(210), dp(45)),
        pos_hint={'center_x': 0.32, 'center_y': 0.68},
        halign='left',
        valign='middle'
    )
    ai_bubble_1.bind(size=ai_bubble_1.setter('text_size'))
    with ai_bubble_1.canvas.before:
        Color(0.04, 0.12, 0.22, 0.85)
        RoundedRectangle(pos=ai_bubble_1.pos, size=ai_bubble_1.size, radius=[dp(14)])
        Color(0.1, 0.6, 0.9, 0.3)
        Line(rounded_rectangle=(ai_bubble_1.x, ai_bubble_1.y, ai_bubble_1.width, ai_bubble_1.height, dp(14)), width=1)
    center_area.add_widget(ai_bubble_1)

    ai_bubble_2 = Label(
        text="Siesthonwf fore clnig ivaluars Ale ouonpotris ale we in furt sevistorerabhy AIT",
        font_size='11sp',
        color=(0.7, 0.95, 1, 1),
        size_hint=(None, None),
        size=(dp(210), dp(45)),
        pos_hint={'center_x': 0.32, 'center_y': 0.25},
        halign='left',
        valign='middle'
    )
    ai_bubble_2.bind(size=ai_bubble_2.setter('text_size'))
    with ai_bubble_2.canvas.before:
        Color(0.04, 0.12, 0.22, 0.85)
        RoundedRectangle(pos=ai_bubble_2.pos, size=ai_bubble_2.size, radius=[dp(14)])
        Color(0.1, 0.6, 0.9, 0.3)
        Line(rounded_rectangle=(ai_bubble_2.x, ai_bubble_2.y, ai_bubble_2.width, ai_bubble_2.height, dp(14)), width=1)
    center_area.add_widget(ai_bubble_2)

    ai_bubble_3 = Label(
        text="Aist action westatliy c tirence",
        font_size='11sp',
        color=(0.7, 0.95, 1, 1),
        size_hint=(None, None),
        size=(dp(200), dp(28)),
        pos_hint={'center_x': 0.32, 'center_y': 0.10},
        halign='left',
        valign='middle'
    )
    ai_bubble_3.bind(size=ai_bubble_3.setter('text_size'))
    with ai_bubble_3.canvas.before:
        Color(0.04, 0.12, 0.22, 0.85)
        RoundedRectangle(pos=ai_bubble_3.pos, size=ai_bubble_3.size, radius=[dp(14)])
        Color(0.1, 0.6, 0.9, 0.3)
        Line(rounded_rectangle=(ai_bubble_3.x, ai_bubble_3.y, ai_bubble_3.width, ai_bubble_3.height, dp(14)), width=1)
    center_area.add_widget(ai_bubble_3)

    # ========================================================
    # RIGHT SIDE PANEL (Voice Selection & Settings Menu)
    # ========================================================
    settings_panel = FloatLayout(
        size_hint=(None, None),
        size=(dp(165), dp(300)),
        pos_hint={'right': 0.97, 'center_y': 0.54}
    )
    with settings_panel.canvas.before:
        Color(0.03, 0.07, 0.14, 0.95)
        RoundedRectangle(pos=settings_panel.pos, size=settings_panel.size, radius=[dp(12)])
        Color(0.1, 0.6, 0.9, 0.4)
        Line(rounded_rectangle=(settings_panel.x, settings_panel.y, settings_panel.width, settings_panel.height, dp(12)), width=1.1)

    panel_layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6), size_hint=(1, 1))
    
    panel_title = Label(text="Voice Selection", font_size='12sp', bold=True, color=(0.35, 0.88, 1, 1), size_hint=(1, None), height=dp(20))
    panel_layout.add_widget(panel_title)

    # Voices list inside panel
    voices = ["Alate troiina", "Tioteerabuh", "Wardsolstae", "Suienger fight", "Mginall shceratioe", "Etseoabrck"]
    voices_scroll = ScrollView(size_hint=(1, None), height=dp(130))
    voices_col = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None)
    voices_col.bind(minimum_height=voices_col.setter('height'))

    for v in voices:
        vb = Button(text=f"🎙  {v}", font_size='10sp', size_hint=(1, None), height=dp(24), background_color=(0,0,0,0), color=(0.8, 0.9, 1, 1), halign='left')
        vb.bind(size=vb.setter('text_size'))
        voices_col.add_widget(vb)
    voices_scroll.add_widget(voices_col)
    panel_layout.add_widget(voices_scroll)

    wake_lbl = Label(text="Wake-word\nChene", font_size='10sp', color=(0.5, 0.7, 0.85, 1), size_hint=(1, None), height=dp(32), halign='left')
    wake_lbl.bind(size=wake_lbl.setter('text_size'))
    panel_layout.add_widget(wake_lbl)

    theme_lbl = Label(text="Theme\nAl Shere  🟢", font_size='10sp', color=(0.5, 0.7, 0.85, 1), size_hint=(1, None), height=dp(32), halign='left')
    theme_lbl.bind(size=theme_lbl.setter('text_size'))
    panel_layout.add_widget(theme_lbl)

    settings_panel.add_widget(panel_layout)
    center_area.add_widget(settings_panel)
    root.add_widget(center_area)

    # Toggle panel visibility when settings gear is clicked
    def toggle_panel(instance):
        settings_panel.opacity = 0 if settings_panel.opacity == 1 else 1
    settings_btn.bind(on_press=toggle_panel)

    # ========================================================
    # QUICK ACTION BUTTONS BAR (Alarms, Reminders, Weather, Messages)
    # ========================================================
    quick_actions = GridLayout(
        cols=4,
        spacing=dp(8),
        size_hint=(0.95, None),
        height=dp(60),
        pos_hint={'center_x': 0.5, 'y': 0.13}
    )

    actions_data = [
        ("⏰\nAlarms", lambda x: app.set_status("Alarms menu")),
        ("📅\nReminders", lambda x: app.open_calendar()),
        ("⛅\nWeather", lambda x: app.google_web_search("weather forecast")),
        ("💬\nMessages", lambda x: app.open_messages())
    ]

    for title, callback in actions_data:
        btn = Button(
            text=title,
            font_size='10sp',
            halign='center',
            valign='middle',
            background_color=(0, 0, 0, 0),
            color=(0.8, 0.95, 1, 1)
        )
        btn.bind(size=btn.setter('text_size'))
        btn.bind(on_press=callback)
        
        with btn.canvas.before:
            Color(0.04, 0.1, 0.18, 0.85)
            RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])
            Color(0.1, 0.6, 0.9, 0.35)
            Line(rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, dp(10)), width=1)
        
        quick_actions.add_widget(btn)
    root.add_widget(quick_actions)

    # ========================================================
    # BOTTOM BAR & BIOMETRIC FINGERPRINT SCANNER
    # ========================================================
    bottom_bar = BoxLayout(
        orientation='horizontal',
        size_hint=(0.95, None),
        height=dp(55),
        pos_hint={'center_x': 0.5, 'y': 0.02},
        padding=[dp(10), dp(4), dp(10), dp(4)],
        spacing=dp(10)
    )
    with bottom_bar.canvas.before:
        Color(0.03, 0.07, 0.14, 0.95)
        RoundedRectangle(pos=bottom_bar.pos, size=bottom_bar.size, radius=[dp(12)])
        Color(0.1, 0.6, 0.9, 0.4)
        Line(rounded_rectangle=(bottom_bar.x, bottom_bar.y, bottom_bar.width, bottom_bar.height, dp(12)), width=1)

    history_btn = Button(
        text="History",
        font_size='11sp',
        size_hint=(0.3, 1),
        background_color=(0, 0, 0, 0),
        color=(0.7, 0.85, 1, 1)
    )
    history_btn.bind(on_press=lambda x: app.set_status("Voice history active"))

    fingerprint_btn = Button(
        text="🔒",
        font_size='18sp',
        size_hint=(None, None),
        size=dp(42),
        pos_hint={'center_y': 0.5},
        background_color=(0, 0, 0, 0),
        color=(0, 0.9, 1, 1)
    )
    fingerprint_btn.bind(on_press=lambda x: app.speak("Biometric verification active."))

    settings_shortcut_btn = Button(
        text="Settings",
        font_size='11sp',
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
