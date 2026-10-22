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
            # Fingerprint ridges, drawn as smooth open curves.
            Color(0.32, 0.91, 1.0, 1)
            for idx in range(6):
                half_w = r * (0.12 + idx * 0.095)
                top = cy + r * (0.55 - idx * 0.035)
                bottom = cy - r * (0.55 - idx * 0.045)
                pts = []
                steps = 44
                for j in range(steps + 1):
                    t = j / steps
                    y = top - (top-bottom)*t
                    # Rounded arch at top, then slightly narrowing lower ridges.
                    xoff = half_w * math.sin(math.pi * t * 0.92)
                    x = cx + xoff * math.sin(math.pi * (t*0.88 + 0.06))
                    pts.extend((x, y))
                if len(pts) >= 4:
                    Line(points=pts, width=dp(1.35), cap='round')
            # Center ridge / sensor glint.
            Color(0.78, 0.95, 1.0, 0.95)
            Line(points=[cx, cy-r*0.43, cx, cy+r*0.20], width=dp(1.15), cap='round')



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
    """v0.30 polished responsive portrait dashboard; preserves main.py integration."""
    # Use a scroll container on short screens so controls never disappear off-screen.
    page = BoxLayout(orientation='vertical', spacing=dp(7), padding=[dp(10),dp(7),dp(10),dp(7)])
    with page.canvas.before:
        Color(*BG)
        page._bg = RoundedRectangle(pos=page.pos, size=page.size, radius=[0])
    page.bind(pos=lambda w,_: setattr(w._bg,'pos',w.pos), size=lambda w,_: setattr(w._bg,'size',w.size))

    # Header: strong wordmark, compact status light, and gold settings control.
    header=BoxLayout(size_hint_y=None,height=dp(51),spacing=dp(8),padding=[dp(7),dp(2),dp(3),dp(2)])
    name=txt('JARVIS',23,CYAN,True); name.size_hint_x=1
    header.add_widget(name)
    light=txt('●',13,(0.25,1.0,0.72,1),True); light.size_hint_x=None; light.width=dp(18)
    header.add_widget(light)
    gear=action_button('⚙',lambda: getattr(app,'open_settings',lambda: _safe_status(app,'Settings'))(),44)
    gear.size_hint_x=None; gear.width=dp(48); gear.color=GOLD; gear.font_size='23sp'
    header.add_widget(gear); page.add_widget(header)

    # Status panel uses consistent inset, border, and hierarchy.
    conversation=BoxLayout(orientation='vertical',spacing=dp(3),padding=[dp(11),dp(6),dp(11),dp(6)],size_hint_y=None,height=dp(78))
    panel(conversation,(0.018,0.045,0.066,0.98),dp(16),(0.12,0.58,0.72,0.72))
    conversation.add_widget(txt('VOICE INTERFACE  /  PERSONAL AI',10,(0.38,0.82,0.91,1),True))
    app.status_label=txt('JARVIS starting...',15,CYAN,True)
    conversation.add_widget(app.status_label); page.add_widget(conversation)

    # Reactor has a bounded height for predictable alignment across phone sizes.
    core_card=BoxLayout(orientation='vertical',spacing=0,padding=[dp(2),dp(1),dp(2),dp(1)],size_hint_y=None,height=dp(160))
    app.core_widget=JarvisCore(size_hint=(1,1)); core_card.add_widget(app.core_widget); page.add_widget(core_card)

    transcript=BoxLayout(orientation='vertical',spacing=dp(2),size_hint_y=None,height=dp(47),padding=[dp(7),dp(1),dp(7),dp(1)])
    transcript.add_widget(txt('◉  JARVIS  ·  Ready to assist',12,(0.78,0.92,0.97,1)))
    transcript.add_widget(txt('Speak naturally — your commands stay voice-first.',10,(0.48,0.74,0.82,1)))
    page.add_widget(transcript)

    # Settings strip: two evenly sized, aligned controls and a readable status line.
    settings_card=BoxLayout(orientation='vertical',spacing=dp(4),padding=[dp(9),dp(6),dp(9),dp(6)],size_hint_y=None,height=dp(94))
    panel(settings_card,(0.022,0.048,0.067,0.99),dp(16),(0.35,0.67,0.74,0.66))
    settings_card.add_widget(txt('VOICE SELECTION   ·   THEME',11,GOLD,True))
    opts=GridLayout(cols=2,spacing=dp(6),size_hint_y=None,height=dp(34))
    opts.add_widget(action_button('Voice options',lambda: _voice_action(app,'voice selection settings'),36))
    opts.add_widget(action_button('Theme  ◈',lambda: _safe_status(app,'Theme: Dark cyan / gold'),36))
    settings_card.add_widget(opts)
    settings_card.add_widget(txt('Wake word: JARVIS    •    AI Share: Ready',10,MUTED))
    page.add_widget(settings_card)

    # Four shortcuts in a single consistent rail, with the same working callbacks.
    quick=BoxLayout(orientation='horizontal',spacing=dp(5),size_hint_y=None,height=dp(57),padding=[dp(4),dp(4),dp(4),dp(4)])
    panel(quick,(0.025,0.075,0.105,0.99),dp(17),(0.30,0.82,0.94,0.9))
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
    page.add_widget(quick)

    # Footer: history | fingerprint control | settings, with balanced spacing.
    footer=BoxLayout(orientation='horizontal',spacing=dp(8),size_hint_y=None,height=dp(76),padding=[dp(3),dp(2),dp(3),dp(2)])
    hist=action_button('History',lambda: _voice_action(app,'recent history batao'),42)
    hist.size_hint_x=1; hist.font_size='12sp'
    mic=FingerprintButton(size_hint_x=0.86,size_hint_y=1)
    mic.bind(on_release=lambda *_: getattr(app,'listen',lambda: _safe_status(app,'Listening...'))())
    sett=action_button('Settings',lambda: getattr(app,'open_settings',lambda: _safe_status(app,'Settings'))(),42)
    sett.size_hint_x=1; sett.font_size='12sp'
    footer.add_widget(hist); footer.add_widget(mic); footer.add_widget(sett); page.add_widget(footer)

    # Keep all v0.26+ calculator attributes expected by main.py.
    app.calc_panel=BoxLayout(orientation='vertical',spacing=dp(1),size_hint_y=None,height=dp(43),padding=[dp(9),dp(2),dp(9),dp(2)])
    panel(app.calc_panel,(0.018,0.045,0.065,0.98),dp(12),(0.10,0.48,0.59,0.68))
    app.calc_question_label=txt('CALCULATOR  /  Ask a maths question by voice',10,MUTED)
    app.calc_answer_label=txt('ANSWER  /  --',12,CYAN,True)
    app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})()
    app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]
    page.add_widget(app.calc_panel)

    # Scroll fallback preserves every control on short displays; normal phones show full page.
    scroll=ScrollView(do_scroll_x=False,do_scroll_y=True,bar_width=dp(2),scroll_type=['bars','content'])
    scroll.add_widget(page)
    app.root_layout=page
    return scroll
