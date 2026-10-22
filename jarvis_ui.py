"""JARVIS v0.29 visual module: responsive cyan/gold core and central fingerprint control. Keep UI isolated from main.py."""
import math
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView

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



class FingerprintButton(Button):
    """Custom central microphone/fingerprint-style control inspired by the reference."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ''
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        r = min(self.width, self.height) * 0.43
        pressed = self.state == 'down'
        with self.canvas:
            # Outer metallic housing and cyan aura.
            Color(0.02, 0.55, 0.82, 0.14 if not pressed else 0.24)
            Ellipse(pos=(cx-r*1.22, cy-r*1.22), size=(r*2.44, r*2.44))
            Color(0.48, 0.68, 0.75, 0.95)
            Line(circle=(cx, cy, r*1.08), width=dp(1.5))
            Color(0.06, 0.15, 0.20, 1)
            Ellipse(pos=(cx-r, cy-r), size=(r*2, r*2))
            Color(0.16, 0.84, 0.96, 0.95)
            Line(circle=(cx, cy, r*0.88), width=dp(1.5))
            Color(0.025, 0.055, 0.08, 1)
            Ellipse(pos=(cx-r*0.76, cy-r*0.76), size=(r*1.52, r*1.52))
            # Symmetrical fingerprint ridges. The previous curve used only positive
            # X offsets, which could make the icon look like a play/speaker symbol.
            Color(0.32, 0.91, 1.0, 1)
            for idx in range(6):
                half_w = r * (0.24 + idx * 0.105)
                top_y = cy + r * (0.42 - idx * 0.035)
                depth = r * (0.34 + idx * 0.018)
                pts = []
                steps = 48
                for j in range(steps + 1):
                    t = j / steps
                    xoff = half_w * (2.0 * t - 1.0)
                    # Rounded arch with both left and right halves, centered on sensor.
                    y = top_y - depth * ((xoff / half_w) ** 2)
                    pts.extend((cx + xoff, y))
                Line(points=pts, width=dp(1.25), cap='round')
            # Short lower fingerprint tails and central sensor glint.
            Color(0.32, 0.91, 1.0, 1)
            Line(points=[cx-r*0.28, cy-r*0.18, cx-r*0.22, cy-r*0.43], width=dp(1.25), cap='round')
            Line(points=[cx+r*0.28, cy-r*0.18, cx+r*0.22, cy-r*0.43], width=dp(1.25), cap='round')
            Color(0.78, 0.95, 1.0, 0.95)
            Line(points=[cx, cy-r*0.30, cx, cy+r*0.22], width=dp(1.15), cap='round')



BG = (0.012, 0.025, 0.043, 1)
CYAN = (0.25, 0.88, 1, 1)
GOLD = (0.91, 0.76, 0.48, 1)
MUTED = (0.61, 0.75, 0.83, 1)


def panel(widget, color=(0.025, 0.065, 0.09, 0.94), radius=dp(18), border=(0.18,0.73,0.88,0.65)):
    with widget.canvas.before:
        Color(*color)
        widget._panel_bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        Color(*border)
        widget._panel_line = Line(rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, radius), width=1.05)
    def update(*_):
        widget._panel_bg.pos = widget.pos; widget._panel_bg.size = widget.size
        widget._panel_line.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, radius)
    widget.bind(pos=update, size=update)
    return widget


def txt(text, size=14, color=MUTED, bold=False, halign='left'):
    w=Label(text=text, font_size=f'{size}sp', color=color, bold=bold, halign=halign, valign='middle')
    w.bind(size=lambda inst, val: setattr(inst, 'text_size', (max(0, val[0]-dp(8)), val[1])))
    return w


def action_button(text, callback, height=42):
    b=Button(text=text, size_hint_y=None, height=dp(height), font_size='13sp', color=(0.84,0.94,0.98,1),
             background_normal='', background_down='', background_color=(0.025,0.12,0.17,0.98))
    b.bind(on_release=lambda *_: callback())
    return b


def _safe_status(app, message):
    try: app.set_status(message)
    except Exception: pass


def _voice_action(app, command):
    # Voice-first: use existing recognizer for microphone; otherwise announce the feature.
    try:
        app.set_status('Boliye: ' + command)
        if getattr(app, 'tts', None): app.tts.speak('Kripya ' + command + ' boliye.', 0, None)
    except Exception:
        pass


def build_jarvis_ui(app):
    root=BoxLayout(orientation='vertical', spacing=dp(7), padding=[dp(10),dp(8),dp(10),dp(8)])
    with root.canvas.before:
        Color(*BG); root._bg=RoundedRectangle(pos=root.pos,size=root.size,radius=[0])
    root.bind(pos=lambda w,_: setattr(w._bg,'pos',w.pos), size=lambda w,_: setattr(w._bg,'size',w.size))

    # Header inspired by the supplied reference, scales with the device width.
    header=BoxLayout(size_hint_y=None,height=dp(53),spacing=dp(8),padding=[dp(10),dp(3),dp(5),dp(3)])
    name=txt('JARVIS  ●',22,CYAN,True)
    name.size_hint_x=1
    header.add_widget(name)
    gear=action_button('⚙',lambda: getattr(app,'open_settings',lambda: _safe_status(app,'Settings'))(),45)
    gear.size_hint_x=None; gear.width=dp(50); gear.color=GOLD; gear.font_size='24sp'
    header.add_widget(gear); root.add_widget(header)

    # Compact status / conversation region.
    conversation=BoxLayout(orientation='vertical',spacing=dp(4),padding=[dp(9),dp(7),dp(9),dp(7)],size_hint_y=None,height=dp(88))
    panel(conversation,(0.018,0.052,0.075,0.92),dp(16),(0.12,0.48,0.62,0.55))
    conversation.add_widget(txt('VOICE INTERFACE  /  PERSONAL AI',10,(0.32,0.76,0.86,1),True))
    app.status_label=txt('JARVIS starting...',14,CYAN,True)
    conversation.add_widget(app.status_label)
    root.add_widget(conversation)

    # Core is given flexible space so it scales to short and tall screens.
    core_card=BoxLayout(orientation='vertical',spacing=dp(1),padding=[dp(4),dp(2),dp(4),dp(2)])
    app.core_widget=JarvisCore(size_hint=(1,1))
    core_card.add_widget(app.core_widget)
    root.add_widget(core_card)

    # Conversation bubbles, kept concise for portrait screens.
    transcript=BoxLayout(orientation='vertical',spacing=dp(4),size_hint_y=None,height=dp(66),padding=[dp(5),dp(2),dp(5),dp(2)])
    transcript.add_widget(txt('◉  JARVIS  ·  Ready to assist',12,(0.76,0.91,0.96,1)))
    transcript.add_widget(txt('Speak naturally — your commands stay voice-first.',11,(0.43,0.72,0.80,1)))
    root.add_widget(transcript)

    # Voice selection/settings card: real options are surfaced as voice guidance rather than fake selectors.
    settings_card=BoxLayout(orientation='vertical',spacing=dp(5),padding=[dp(9),dp(7),dp(9),dp(7)],size_hint_y=None,height=dp(102))
    panel(settings_card,(0.022,0.052,0.071,0.98),dp(16),(0.35,0.65,0.72,0.55))
    settings_card.add_widget(txt('VOICE SELECTION   ·   THEME',11,GOLD,True))
    opts=GridLayout(cols=2,spacing=dp(6),size_hint_y=None,height=dp(36))
    opts.add_widget(action_button('Voice options',lambda: _voice_action(app,'voice selection settings')))
    opts.add_widget(action_button('Theme  →',lambda: _safe_status(app,'Theme: Dark cyan / gold')))
    settings_card.add_widget(opts)
    settings_card.add_widget(txt('Wake word: JARVIS     •     AI Share: Ready',10,MUTED))
    root.add_widget(settings_card)

    # Quick action rail matching the four reference shortcuts.
    quick=BoxLayout(orientation='horizontal',spacing=dp(5),size_hint_y=None,height=dp(57),padding=[dp(4),dp(4),dp(4),dp(4)])
    panel(quick,(0.025,0.09,0.12,0.96),dp(17),(0.32,0.83,0.93,0.78))
    def quick_action(label, command, method=None):
        def run():
            if method and hasattr(app,method):
                try: getattr(app,method)(); return
                except Exception: pass
            _voice_action(app,command)
        b=action_button(label,run,43); b.size_hint_x=1; b.font_size='11sp'; quick.add_widget(b)
    quick_action('Alarms','alarm lagao')
    quick_action('Reminders','reminder banao')
    quick_action('Weather','weather batao')
    quick_action('Messages','messages kholo','open_messages')
    root.add_widget(quick)

    # Footer controls: a large central fingerprint/microphone control inspired by the supplied reference.
    footer=BoxLayout(orientation='horizontal',spacing=dp(7),size_hint_y=None,height=dp(82),padding=[dp(2),dp(2),dp(2),dp(2)])
    hist=action_button('History',lambda: _voice_action(app,'recent history batao'),40)
    hist.size_hint_x=1
    hist.font_size='12sp'
    mic=FingerprintButton(size_hint_x=0.92, size_hint_y=1)
    mic.bind(on_release=lambda *_: getattr(app,'listen',lambda: _safe_status(app,'Listening...'))())
    sett=action_button('Settings',lambda: getattr(app,'open_settings',lambda: _safe_status(app,'Settings'))(),40)
    sett.size_hint_x=1
    sett.font_size='12sp'
    footer.add_widget(hist); footer.add_widget(mic); footer.add_widget(sett)
    root.add_widget(footer)

    # Keep calculator references required by existing v0.26 voice-calculator logic.
    # The panel is compact and voice-first; no keypad or manual input buttons are displayed.
    app.calc_panel=BoxLayout(orientation='vertical',spacing=dp(1),size_hint_y=None,height=dp(42),padding=[dp(9),dp(2),dp(9),dp(2)])
    panel(app.calc_panel,(0.018,0.045,0.065,0.92),dp(12),(0.10,0.42,0.53,0.5))
    app.calc_question_label=txt('CALCULATOR  /  Ask a maths question by voice',10,MUTED)
    app.calc_answer_label=txt('ANSWER  /  --',12,CYAN,True)
    app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})()
    app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]
    root.add_widget(app.calc_panel)
    app.root_layout=root
    return root
