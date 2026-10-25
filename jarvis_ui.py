
"""JARVIS v0.29 reference-inspired Android UI.
UI module for the existing main.py. Keeps assistant logic in main.py.
"""
import math
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider

BG = (0.018, 0.035, 0.040, 1)
PANEL = (0.055, 0.085, 0.090, 0.98)
PANEL2 = (0.075, 0.105, 0.110, 0.98)
EDGE = (0.25, 0.39, 0.40, 0.72)
CYAN = (0.35, 0.91, 0.90, 1)
WHITE = (0.89, 0.94, 0.94, 1)
MUTED = (0.57, 0.68, 0.69, 1)
GREEN = (0.12, 0.95, 0.52, 1)
GOLD = (0.78, 0.84, 0.82, 1)


def make_label(text, size=14, color=WHITE, bold=False, align='left'):
    w = Label(text=text, font_size=f'{size}sp', color=color, bold=bold,
              halign=align, valign='middle', shorten=True, shorten_from='right')
    w.bind(size=lambda obj, val: setattr(obj, 'text_size', (max(0, val[0]-dp(5)), val[1])))
    return w


def plate(widget, fill=PANEL, edge=EDGE, radius=None, line_width=1.0):
    if radius is None:
        radius = dp(16)
    with widget.canvas.before:
        Color(*fill)
        widget._plate = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        Color(*edge)
        widget._edge = Line(rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, radius), width=line_width)
    def sync(*_):
        widget._plate.pos = widget.pos
        widget._plate.size = widget.size
        widget._edge.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, radius)
    widget.bind(pos=sync, size=sync)
    return widget


def ui_button(text, callback, size=13, color=WHITE, bg=(0, 0, 0, 0), height=None):
    if height is None:
        height = dp(42)
    b = Button(text=text, font_size=f'{size}sp', color=color, size_hint_y=None, height=height,
               background_normal='', background_down='', background_color=bg,
               halign='center', valign='middle')
    b.bind(size=lambda obj, val: setattr(obj, 'text_size', (max(0, val[0]-dp(8)), val[1])))
    b.bind(on_release=lambda *_: callback())
    return b


class StatusDot(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        x, y = self.center
        r = min(self.width, self.height) * .19
        with self.canvas:
            Color(GREEN[0], GREEN[1], GREEN[2], .12)
            Ellipse(pos=(x-r*2.4, y-r*2.4), size=(r*4.8, r*4.8))
            Color(*GREEN)
            Ellipse(pos=(x-r, y-r), size=(r*2, r*2))


class GearButton(Button):
    """A real clickable button; gear is drawn directly on its own canvas."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ''
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0.05, 0.08, 0.085, 1)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.after.clear()
        x, y = self.center
        r = min(self.width, self.height) * .25
        with self.canvas.after:
            Color(*GOLD)
            Line(circle=(x, y, r), width=dp(1.5))
            Line(circle=(x, y, r*.42), width=dp(1.4))
            for i in range(8):
                a = math.pi * 2 * i / 8
                Line(points=[x+math.cos(a)*r*1.12, y+math.sin(a)*r*1.12,
                             x+math.cos(a)*r*1.55, y+math.sin(a)*r*1.55], width=dp(2.2))


class PaperPlane(Widget):
    """Canvas-drawn send icon; avoids unsupported Unicode glyphs on Android."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        x, y = self.center
        s = min(self.width, self.height) * .36
        with self.canvas:
            Color(*CYAN)
            Line(points=[x-s, y-s*.25, x+s, y+s*.45, x+s*.12, y-s*.48, x-s, y-s*.25],
                 close=True, width=dp(1.8))
            Line(points=[x-s*.10, y-s*.03, x+s, y+s*.45], width=dp(1.4))
            Line(points=[x-s*.10, y-s*.03, x-s*.32, y-s*.38], width=dp(1.4))


class PaperPlaneButton(Button):
    """Clickable send button with a canvas-drawn plane icon."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ''
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *_):
        self.canvas.after.clear()
        x, y = self.center
        s = min(self.width, self.height) * .34
        with self.canvas.after:
            Color(*CYAN)
            Line(points=[x-s, y-s*.25, x+s, y+s*.45, x+s*.12, y-s*.48, x-s, y-s*.25],
                 close=True, width=dp(1.8))
            Line(points=[x-s*.10, y-s*.03, x+s, y+s*.45], width=dp(1.4))
            Line(points=[x-s*.10, y-s*.03, x-s*.32, y-s*.38], width=dp(1.4))


class OrbCore(Widget):
    """Soft blue orb with a gently animated sound wave."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.phase = 0.0
        self.listening = False
        self.speaking = False
        self.bind(pos=self.draw, size=self.draw)
        self._event = Clock.schedule_interval(self.tick, 1/24)
        self.draw()

    def tick(self, dt):
        self.phase += dt * (5.0 if (self.listening or self.speaking) else 1.7)
        self.draw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            callback = getattr(self, 'on_tap', None)
            if callback:
                callback()
                return True
        return super().on_touch_down(touch)

    def draw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = max(dp(20), min(self.width, self.height)*.31)
        active = self.listening or self.speaking
        pulse = .5 + .5*math.sin(self.phase*2.0)
        r *= 1 + (0.035 if active else 0.012)*math.sin(self.phase*2.1)
        with self.canvas:
            for mul, alpha in [(1.62,.025),(1.48,.035),(1.34,.055),(1.20,.075)]:
                Color(.20,.90,.88,alpha+(0.025*pulse if active else 0.008*pulse))
                Ellipse(pos=(cx-r*mul,cy-r*mul),size=(2*r*mul,2*r*mul))
            Color(.08,.27,.72,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(.14,.42,.92,.95); Ellipse(pos=(cx-r*.96,cy-r*.82),size=(1.92*r,1.66*r))
            Color(.25,.61,.98,.90); Ellipse(pos=(cx-r*.88,cy-r*.43),size=(1.76*r,1.15*r))
            Color(.65,.82,1,.92); Ellipse(pos=(cx-r*.77,cy-r*.08),size=(1.54*r,.87*r))
            Color(.77,.88,1,.88); Ellipse(pos=(cx-r*.66,cy-r*.02),size=(1.32*r,.64*r))
            Color(.88,.97,1,.17); Ellipse(pos=(cx-r*.66,cy+r*.35),size=(r*.62,r*.15))
            amp = r*(.10 if not active else .25)
            pts=[]
            for i in range(49):
                xx=cx-r*.76+(2*r*.76)*i/48
                env=math.sin(math.pi*i/48)**.55
                yy=cy+math.sin(i*.77+self.phase*(2.7 if active else .85))*amp*env
                pts.extend([xx,yy])
            Color(.88,.98,1,.52 if not active else .86)
            Line(points=pts,width=dp(1.0 if not active else 1.6),smooth=True)


class SectionCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(7), **kwargs)
        plate(self, PANEL2, EDGE, dp(13), .9)


def build_jarvis_ui(app):
    root = FloatLayout()
    with root.canvas.before:
        Color(*BG)
        root._bg = RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(14)])
        Color(.09,.18,.19,.8)
        root._border = Line(rounded_rectangle=(root.x,root.y,root.width,root.height,dp(14)),width=.8)

    def sync_root(*_):
        root._bg.pos=root.pos
        root._bg.size=root.size
        root._border.rounded_rectangle=(root.x,root.y,root.width,root.height,dp(14))

    root.bind(pos=sync_root,size=sync_root)

    home = FloatLayout()
    settings_page = BoxLayout(orientation='vertical', padding=[dp(12),dp(7),dp(12),dp(10)], spacing=dp(8), opacity=0, disabled=True)
    root.add_widget(home)
    root.add_widget(settings_page)

    # Header: the only settings gear in the home UI; anchored at top-right.
    header = BoxLayout(orientation='horizontal', size_hint=(1,None), height=dp(60),
                       padding=[dp(16),dp(7),dp(16),dp(7)], spacing=dp(8), pos_hint={'top':1})
    
    brand = BoxLayout(
        orientation='horizontal',
        size_hint=(None, 1),
        width=dp(142),
        spacing=dp(4)
    )

    brand.add_widget(make_label('JARVIS', 24, WHITE))

    dot = StatusDot(
        size_hint=(None, None),
        size=(dp(25), dp(25)),
        pos_hint={'center_y': 0.58}
    )
    brand.add_widget(dot)

    header.add_widget(brand)
    header.add_widget(Widget())

    gear_btn = GearButton(
        size_hint=(None, None),
        size=(dp(46), dp(46))
    )
    plate(gear_btn, (.05, .08, .085, 1), EDGE, dp(23), 1.0)
    header.add_widget(gear_btn)

    home.add_widget(header)

    orb = OrbCore(size_hint=(.78,.37), pos_hint={'center_x':.5,'center_y':.59})
    home.add_widget(orb)
    app.core_widget = orb

    status = make_label('Ready when you are',14,MUTED,False,'center')
    status.size_hint=(.9,None)
    status.height=dp(30)
    status.pos_hint={'center_x':.5,'center_y':.365}
    home.add_widget(status)
    app.status_label = status

    caption = make_label('JARVIS • PERSONAL ASSISTANT',9,(.36,.48,.49,1),False,'center')
    caption.size_hint=(.9,None)
    caption.height=dp(18)
    caption.pos_hint={'center_x':.5,'y':.125}
    home.add_widget(caption)

    # Message field + send button share one horizontal row. Send button width is fixed.
    composer = BoxLayout(orientation='horizontal', size_hint=(.88,None), height=dp(52),
                         padding=[dp(14),dp(4),dp(5),dp(4)], spacing=dp(4),
                         pos_hint={'center_x':.47,'y':.04})
    plate(composer,(.10,.14,.15,1),(.28,.39,.40,.85),dp(26),1.0)

    chat = TextInput(hint_text='Message...',multiline=False,font_size='15sp',
                     foreground_color=WHITE,hint_text_color=MUTED,cursor_color=CYAN,
                     background_normal='',background_active='',background_color=(0,0,0,0),
                     size_hint=(1,1),padding=[dp(5),dp(10),dp(3),dp(5)])
    app.chat_input = chat

    def send_message(*_):
        message = chat.text.strip()
        if not message:
            return
        chat.text = ''
        set_status('You: ' + message)
        try:
            app.process_command(message)
        except Exception:
            set_status('Message could not be processed')

    chat.bind(on_text_validate=send_message)
    composer.add_widget(chat)

    send_btn = PaperPlaneButton(size_hint=(None,1),width=dp(42))
    send_btn.bind(on_release=send_message)
    composer.add_widget(send_btn)
    home.add_widget(composer)

    # Settings header and scrollable options.
    settings_header = BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(8))
    close_btn = ui_button('< Close',lambda:None,12,WHITE,(.12,.17,.18,1),dp(34))
    settings_header.add_widget(close_btn)
    settings_header.add_widget(make_label('JARVIS Settings',17,WHITE,True))
    settings_page.add_widget(settings_header)

    scroll = ScrollView(do_scroll_x=False,bar_width=dp(2),scroll_type=['bars','content'])
    content = BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(9),padding=[0,dp(2),0,dp(8)])
    content.bind(minimum_height=content.setter('height'))

    voice_card=SectionCard(size_hint_y=None,height=dp(170))
    voice_card.add_widget(make_label('Voice Selection',16,WHITE,True))
    current_voice=make_label('Current: System default',11,MUTED)
    voice_card.add_widget(current_voice)
    voice_grid=GridLayout(cols=3,spacing=dp(7),size_hint_y=None,height=dp(80))

    for label,value in [('Female\nBeta','Female Beta'),('Formal\nGamma','Formal Gamma'),('Casual\nDelta','Casual Delta')]:
        cell=BoxLayout(orientation='vertical',spacing=dp(3))
        cell.add_widget(make_label('●',24,CYAN,True,'center'))
        cell.add_widget(make_label(label,10,WHITE,False,'center'))

        def choose(v=value):
            app.selected_voice=v
            current_voice.text='Current: '+v
            set_status('Voice selected: '+v)

        cell.add_widget(ui_button('Select',lambda v=value:choose(v),10,CYAN,(.08,.16,.17,1),dp(26)))
        voice_grid.add_widget(cell)

    voice_card.add_widget(voice_grid)
    content.add_widget(voice_card)

    history_card=SectionCard(size_hint_y=None,height=dp(150))
    history_card.add_widget(make_label('History',16,WHITE,True))
    history_text=make_label('Recent interactions will appear here.',11,MUTED)
    history_card.add_widget(history_text)
    history_card.add_widget(ui_button('Clear history',lambda:setattr(history_text,'text','History cleared.'),11,CYAN,(.08,.16,.17,1),dp(30)))
    content.add_widget(history_card)

    wake_card=SectionCard(size_hint_y=None,height=dp(105))
    wake_card.add_widget(make_label('Wake Word Customization',15,WHITE,True))
    wake_input=TextInput(text=getattr(app,'wake_word','Hey JARVIS'),hint_text='Hey JARVIS',multiline=False,
                         size_hint_y=None,height=dp(38),font_size='14sp',foreground_color=WHITE,
                         hint_text_color=MUTED,background_normal='',background_active='',
                         background_color=(.025,.055,.06,1),cursor_color=CYAN,padding=[dp(10),dp(8)])
    wake_input.bind(text=lambda _,v:setattr(app,'wake_word',v.strip() or 'Hey JARVIS'))
    wake_card.add_widget(wake_input)
    content.add_widget(wake_card)

    verbosity=SectionCard(size_hint_y=None,height=dp(115))
    verbosity.add_widget(make_label('Response Verbosity',15,WHITE,True))
    slider=Slider(min=0,max=2,value=1,step=1,cursor_size=(dp(18),dp(18)),size_hint_y=None,height=dp(30))
    verbosity.add_widget(slider)
    verbosity.add_widget(make_label('Detailed  |  Balanced  |  Concise',10,MUTED))
    content.add_widget(verbosity)

    privacy=SectionCard(size_hint_y=None,height=dp(118))
    privacy.add_widget(make_label('Data Privacy & Security',15,WHITE,True))
    privacy.add_widget(make_label('Manage stored data\nClear history\nPrivacy settings',11,MUTED))
    privacy.add_widget(ui_button('Clear visible history',lambda:setattr(history_text,'text','History cleared.'),10,CYAN,(.08,.16,.17,1),dp(28)))
    content.add_widget(privacy)

    appearance=SectionCard(size_hint_y=None,height=dp(100))
    appearance.add_widget(make_label('Appearance',15,WHITE,True))
    theme_row=BoxLayout(size_hint_y=None,height=dp(34),spacing=dp(5))

    for theme_name in ('Light','Dark','System'):
        theme_row.add_widget(ui_button(theme_name,lambda val=theme_name:set_status('Theme: '+val),11,CYAN,(.08,.16,.17,1),dp(32)))

    appearance.add_widget(theme_row)
    content.add_widget(appearance)

    integration=SectionCard(size_hint_y=None,height=dp(120))
    integration.add_widget(make_label('Integration Settings',15,WHITE,True))
    integration.add_widget(make_label('Connect smart home\nSync calendar\nLink accounts',11,MUTED))
    content.add_widget(integration)

    scroll.add_widget(content)
    settings_page.add_widget(scroll)

    def set_status(message):
        try:
            status.text=str(message)
            if hasattr(app,'set_status'):
                app.set_status(str(message))
        except Exception:
            status.text=str(message)

    def set_listening(active=True):
        orb.listening=active
        orb.speaking=False
        status.text='Listening...' if active else 'Ready when you are'

    def start_listening(*_):
        set_listening(True)
        try:
            app.listen()
        except Exception:
            set_status('Listening...')
        Clock.schedule_once(lambda dt:setattr(orb,'listening',False),6)

    def show_settings(*_):
        home.opacity=0
        home.disabled=True
        settings_page.opacity=1
        settings_page.disabled=False

    def hide_settings(*_):
        settings_page.opacity=0
        settings_page.disabled=True
        home.opacity=1
        home.disabled=False

    gear_btn.bind(on_release=show_settings)
    close_btn.bind(on_release=hide_settings)
    orb.on_tap=start_listening

    app.toggle_voice_selection=show_settings
    app.open_jarvis_settings=show_settings
    app.open_settings=show_settings
    app.start_jarvis_listening=start_listening

    # Compatibility references used by the existing calculator code in main.py.
    app.calc_panel=BoxLayout(orientation='vertical',size_hint_y=None,height=0,opacity=0,disabled=True)
    app.calc_question_label=make_label('',10)
    app.calc_answer_label=make_label('',12,CYAN,True)
    app.calc_panel.add_widget(app.calc_question_label)
    app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})()
    app.calc_angle_mode='DEG'
    app.calc_history=[]
    app.calc_buttons=[]
    app.root_layout=root
    return root
