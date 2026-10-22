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
        self.redraw()

    def _tick(self, dt):
        # Static reactor: no rotating rings, matching the requested voice-assistant core.
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
    from kivy.uix.textinput import TextInput
    from kivy.uix.scrollview import ScrollView

    root = BoxLayout(orientation='vertical', spacing=dp(6), padding=[dp(8), dp(7), dp(8), dp(7)])
    with root.canvas.before:
        Color(*BG); root._bg = RoundedRectangle(pos=root.pos, size=root.size, radius=[0])
    root.bind(pos=lambda w, _: setattr(w._bg, 'pos', w.pos), size=lambda w, _: setattr(w._bg, 'size', w.size))

    # Header: JARVIS + green online dot on left, settings gear on right.
    header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8), padding=[dp(7), dp(2), dp(3), dp(2)])
    title = txt('JARVIS', 22, CYAN, True); header.add_widget(title)
    dot = txt('●', 17, (0.12, 1.0, 0.58, 1), True); dot.size_hint_x = None; dot.width = dp(22); header.add_widget(dot)
    spacer = Widget(); header.add_widget(spacer)
    gear = action_button('⚙', lambda: getattr(app, 'open_settings', lambda: _safe_status(app, 'Settings'))(), 42)
    gear.size_hint_x = None; gear.width = dp(48); gear.color = GOLD; gear.font_size = '23sp'; header.add_widget(gear)
    root.add_widget(header)

    # Main area. The right voice drawer opens/closes; the reactor shifts left while open.
    body = BoxLayout(orientation='horizontal', spacing=dp(6))
    left = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_x=1)
    app.status_label = txt('JARVIS ready hai.', 13, CYAN, True)
    status_box = BoxLayout(size_hint_y=None, height=dp(38), padding=[dp(8), dp(3), dp(8), dp(3)])
    panel(status_box, (0.018,0.052,0.075,0.92), dp(12), (0.12,0.48,0.62,0.55)); status_box.add_widget(app.status_label); left.add_widget(status_box)

    app.core_widget = JarvisCore(size_hint=(1, 1)); left.add_widget(app.core_widget)
    # Animated waveform is intentionally omitted; the core glows/pulses without spinning.

    # Wake word and theme below the core, as requested.
    prefs = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None, height=dp(78), padding=[dp(6),dp(4),dp(6),dp(4)])
    panel(prefs, (0.022,0.052,0.071,0.98), dp(13), (0.22,0.62,0.72,0.55))
    prefs.add_widget(txt('Wake-word', 11, GOLD, True))
    wake = TextInput(text='JARVIS', multiline=False, size_hint_y=None, height=dp(30), font_size='13sp', foreground_color=(0.9,0.95,0.98,1), background_normal='', background_active='', background_color=(0.025,0.07,0.09,1), cursor_color=CYAN)
    wake.bind(text=lambda _w, val: setattr(app, 'wake_word', val.strip() or 'JARVIS'))
    prefs.add_widget(wake)
    theme_btn = action_button('Theme  →', lambda: _safe_status(app, 'Theme: Dark cyan / gold'), 30); prefs.add_widget(theme_btn)
    left.add_widget(prefs)
    body.add_widget(left)

    drawer = BoxLayout(orientation='vertical', spacing=dp(5), padding=[dp(7),dp(7),dp(7),dp(7)], size_hint_x=None, width=dp(0))
    panel(drawer, (0.018,0.04,0.055,0.98), dp(15), (0.32,0.75,0.84,0.75))
    dhead = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(3))
    dhead.add_widget(txt('Voice Selection', 13, GOLD, True))
    dots = action_button('•••', lambda: _safe_status(app, 'Voice options'), 30); dots.size_hint_x=None; dots.width=dp(35); dhead.add_widget(dots); drawer.add_widget(dhead)
    voice_scroll = ScrollView(do_scroll_x=False)
    voice_list = GridLayout(cols=1, spacing=dp(5), size_hint_y=None); voice_list.bind(minimum_height=voice_list.setter('height'))
    # These are Android TTS voice/language choices, not invented installed voice packs.
    for label in ('System default', 'English (India)', 'English (US)', 'Hindi (India)'):
        voice_list.add_widget(action_button(label, lambda choice=label: _safe_status(app, 'Voice selected: '+choice), 38))
    voice_scroll.add_widget(voice_list); drawer.add_widget(voice_scroll)
    drawer.add_widget(txt('Tap a voice to select', 10, MUTED))
    body.add_widget(drawer)

    def toggle_voice(*_):
        opened = drawer.width < dp(100)
        drawer.width = dp(178) if opened else dp(0)
        drawer.opacity = 1 if opened else 0
        drawer.disabled = not opened
        left.size_hint_x = 0.72 if opened else 1
        # core stays still; only its layout position changes.
        _safe_status(app, 'Voice Selection khula' if opened else 'Voice Selection band')
    voice_toggle = action_button('Voice Selection  •••', toggle_voice, 34)
    voice_toggle.size_hint_y = None; voice_toggle.height = dp(34); root.add_widget(body); root.add_widget(voice_toggle)

    # Five shortcuts: Alarm, Reminder, Weather, Message and Call.
    quick = BoxLayout(orientation='horizontal', spacing=dp(3), size_hint_y=None, height=dp(58), padding=[dp(3),dp(4),dp(3),dp(4)])
    panel(quick, (0.025,0.09,0.12,0.96), dp(15), (0.32,0.83,0.93,0.78))
    def quick_action(label, command, method=None):
        def run():
            if method and hasattr(app, method):
                try: getattr(app, method)(); return
                except Exception: pass
            _voice_action(app, command)
        b=action_button(label, run, 44); b.size_hint_x=1; b.font_size='10sp'; quick.add_widget(b)
    quick_action('Alarm', 'alarm lagao')
    quick_action('Reminder', 'reminder banao')
    quick_action('Weather', 'weather batao')
    quick_action('Message', 'messages kholo', 'open_messages')
    quick_action('Call', 'phone kholo', 'open_phone')
    root.add_widget(quick)

    # Bottom rail: History | fingerprint | Settings.
    footer = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(66), padding=[dp(3),dp(2),dp(3),dp(2)])
    hist=action_button('History', lambda: _voice_action(app,'recent history batao'), 42); hist.size_hint_x=1
    fp=FingerprintButton(size_hint_x=1, size_hint_y=1); fp.bind(on_release=lambda *_: getattr(app,'listen',lambda: _safe_status(app,'Listening...'))())
    sett=action_button('Settings', lambda: getattr(app,'open_settings',lambda: _safe_status(app,'Settings'))(),42); sett.size_hint_x=1
    footer.add_widget(hist); footer.add_widget(fp); footer.add_widget(sett); root.add_widget(footer)

    # WhatsApp-like text conversation entry, replacing the old calculator prompt.
    chat = BoxLayout(orientation='horizontal', spacing=dp(5), size_hint_y=None, height=dp(44), padding=[dp(3),dp(2),dp(3),dp(2)])
    panel(chat, (0.018,0.045,0.065,0.96), dp(14), (0.10,0.62,0.73,0.75))
    app.chat_input = TextInput(hint_text='JARVIS ko message likhein...', multiline=False, font_size='13sp', foreground_color=(0.92,0.97,1,1), hint_text_color=(0.48,0.65,0.72,1), background_normal='', background_active='', background_color=(0.025,0.07,0.09,1), cursor_color=CYAN)
    def send_chat(*_):
        message = app.chat_input.text.strip()
        if not message: return
        app.chat_input.text = ''
        _safe_status(app, 'Aap: ' + message)
        try:
            app.process_command(message)
        except Exception as exc:
            _safe_status(app, 'Message process nahi hua: ' + str(exc))
    app.chat_input.bind(on_text_validate=send_chat)
    chat.add_widget(app.chat_input)
    send=action_button('Send', send_chat, 36); send.size_hint_x=None; send.width=dp(60); chat.add_widget(send)
    root.add_widget(chat)

    # Keep old calculator attributes so existing v0.26 logic does not crash, but do not show calculator text.
    app.calc_panel=BoxLayout(orientation='vertical', size_hint_y=None, height=dp(0), opacity=0, disabled=True)
    app.calc_question_label=txt('',10,MUTED); app.calc_answer_label=txt('',12,CYAN,True)
    app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})(); app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]
    root.add_widget(app.calc_panel)
    app.root_layout=root
    return root
