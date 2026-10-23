"""JARVIS v0.29 - reference-inspired premium Android UI.
Kivy UI module. Keeps assistant logic in main.py; no third-party UI dependency.
"""
import math
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.animation import Animation
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

# Palette based on the supplied reference: near-black teal, aqua accents, soft white.
BG = (0.018, 0.035, 0.040, 1)
PANEL = (0.055, 0.085, 0.090, 0.98)
PANEL2 = (0.075, 0.105, 0.110, 0.98)
EDGE = (0.25, 0.39, 0.40, 0.72)
CYAN = (0.35, 0.91, 0.90, 1)
CYAN_DIM = (0.22, 0.64, 0.67, 1)
WHITE = (0.89, 0.94, 0.94, 1)
MUTED = (0.57, 0.68, 0.69, 1)
GREEN = (0.12, 0.95, 0.52, 1)
GOLD = (0.78, 0.84, 0.82, 1)


def _rgba(c, a=None):
    return (c[0], c[1], c[2], c[3] if a is None and len(c) > 3 else (1 if a is None else a))


def make_label(text, size=14, color=WHITE, bold=False, align='left'):
    w = Label(text=text, font_size=f'{size}sp', color=color, bold=bold,
              halign=align, valign='middle', shorten=True, shorten_from='right')
    w.bind(size=lambda obj, val: setattr(obj, 'text_size', (max(0, val[0]-dp(5)), val[1])))
    return w


def plate(widget, fill=PANEL, edge=EDGE, radius=dp(16), line_width=1.0):
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


def ui_button(text, callback, size=13, color=WHITE, bg=(0, 0, 0, 0), height=dp(42)):
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


class GearIcon(Widget):
    """Draw a settings icon with canvas lines, avoiding missing-font square glyphs."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()
    def draw(self, *_):
        self.canvas.clear(); x, y = self.center; r = min(self.width, self.height) * .22
        with self.canvas:
            Color(*GOLD)
            Line(circle=(x, y, r), width=dp(1.5))
            Line(circle=(x, y, r*.43), width=dp(1.3))
            for i in range(8):
                a = math.pi*2*i/8
                x1, y1 = x+math.cos(a)*r*1.12, y+math.sin(a)*r*1.12
                x2, y2 = x+math.cos(a)*r*1.48, y+math.sin(a)*r*1.48
                Line(points=[x1,y1,x2,y2], width=dp(2.2), cap='round')


class PaperPlane(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs); self.bind(pos=self.draw, size=self.draw); self.draw()
    def draw(self, *_):
        self.canvas.clear(); x,y=self.center; w=min(self.width,self.height)*.34
        with self.canvas:
            Color(*CYAN)
            Line(points=[x-w,y-w*.15,x+w,y+w*.4,x+w*.12,y-w*.48,x-w,y-w*.15], close=True, width=dp(1.7))
            Line(points=[x-w*.05,y-w*.02,x+w,y+w*.4,x+w*.12,y-w*.48], width=dp(1.1))


class OrbCore(Widget):
    """Soft luminous orb. The sphere stays in place; its glow and sound wave breathe."""
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
        if self.collide_point(*touch.pos) and getattr(self, 'on_tap', None):
            self.on_tap()
            return True
        return super().on_touch_down(touch)
    def draw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = max(dp(20), min(self.width, self.height)*.31)
        active = self.listening or self.speaking
        pulse = .5 + .5*math.sin(self.phase*2.0)
        scale = 1 + (0.035 if active else 0.012)*math.sin(self.phase*2.1)
        r *= scale
        with self.canvas:
            # broad teal halo
            for mul, alpha in [(1.62,.025),(1.48,.035),(1.34,.055),(1.20,.075)]:
                Color(.20,.90,.88,alpha + (0.025*pulse if active else 0.008*pulse))
                Ellipse(pos=(cx-r*mul, cy-r*mul), size=(2*r*mul,2*r*mul))
            # spherical body and luminous lower/upper colour fields
            Color(.08,.27,.72,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(.14,.42,.92,.95); Ellipse(pos=(cx-r*.96,cy-r*.82),size=(1.92*r,1.66*r))
            Color(.25,.61,.98,.90); Ellipse(pos=(cx-r*.88,cy-r*.43),size=(1.76*r,1.15*r))
            Color(.65,.82,1,.92); Ellipse(pos=(cx-r*.77,cy-r*.08),size=(1.54*r,.87*r))
            Color(.77,.88,1,.88); Ellipse(pos=(cx-r*.66,cy-r*.02),size=(1.32*r,.64*r))
            # subtle upper highlight, no rotating rings
            Color(.88,.97,1,.17)
            Ellipse(pos=(cx-r*.66,cy+r*.35),size=(r*.62,r*.15))
            # live voice waveform across orb, amplitude follows listening/speaking state
            amp = r*(.10 if not active else .25)
            pts=[]; n=49
            for i in range(n):
                xx = cx-r*.76 + (2*r*.76)*i/(n-1)
                env = math.sin(math.pi*i/(n-1))**.55
                wave = math.sin(i*.77+self.phase*(2.7 if active else .85))
                yy = cy + wave*amp*env
                pts.extend([xx,yy])
            Color(.88,.98,1,.52 if not active else .86)
            Line(points=pts,width=dp(1.0 if not active else 1.6),smooth=True)
            if active:
                # compact vertical equalizer peaks while JARVIS hears/speaks
                for i in range(15):
                    xx=cx-r*.65+i*(r*1.30/14)
                    h=r*(.04+.13*abs(math.sin(i*1.3+self.phase*3))*math.sin(math.pi*i/14))
                    Color(.72,.96,1,.72)
                    Line(points=[xx,cy-h,xx,cy+h],width=dp(1.0),cap='round')


class FingerprintIcon(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs); self.bind(pos=self.draw, size=self.draw); self.draw()
    def draw(self, *_):
        self.canvas.clear(); x,y=self.center; r=min(self.width,self.height)*.30
        with self.canvas:
            Color(.12,.58,.64,.20); Ellipse(pos=(x-r*1.6,y-r*1.6),size=(r*3.2,r*3.2))
            Color(*CYAN); Line(circle=(x,y,r*1.18),width=dp(1.0))
            for k in range(5):
                pts=[]; half=r*(.25+k*.12)
                for j in range(26):
                    t=j/25
                    pts.extend([x+half*math.sin(math.pi*t), y+r*(.57-t*1.13)])
                Color(.55,.95,.94,.92-k*.08); Line(points=pts,width=dp(1.15),cap='round')


class SectionCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(7), **kwargs)
        plate(self, PANEL2, EDGE, dp(13), .9)


def build_jarvis_ui(app):
    root = FloatLayout()
    with root.canvas.before:
        Color(*BG); root._bg = RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(14)])
        Color(.09,.18,.19,.8); root._border = Line(rounded_rectangle=(root.x,root.y,root.width,root.height,dp(14)),width=.8)
    def sync_root(*_):
        root._bg.pos=root.pos; root._bg.size=root.size
        root._border.rounded_rectangle=(root.x,root.y,root.width,root.height,dp(14))
    root.bind(pos=sync_root,size=sync_root)

    # Home and Settings are separate full-screen layers; no awkward settings drawer over the orb.
    home = FloatLayout()
    settings_page = BoxLayout(orientation='vertical', padding=[dp(12),dp(7),dp(12),dp(10)], spacing=dp(8), opacity=0, disabled=True)
    root.add_widget(home); root.add_widget(settings_page)

    # Header: exact composition from reference (JARVIS + green dot, gear on right).
    header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(60),
                       padding=[dp(18), dp(4), dp(16), dp(4)], spacing=dp(8), pos_hint={'x': 0, 'top': 1})
    
    brand_box = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(dp(140), dp(40)), spacing=dp(8), pos_hint={'center_y': 0.5})
    brand_box.add_widget(make_label('JARVIS', 24, WHITE, False))
    dot = StatusDot(size_hint=(None, None), size=(dp(28), dp(28)), pos_hint={'center_y': 0.5})
    brand_box.add_widget(dot)
    header.add_widget(brand_box)
    
    header.add_widget(Widget())
    
    gear_btn = FloatLayout(size_hint=(None, None), size=(dp(48), dp(48)), pos_hint={'center_y': 0.5})
    plate(gear_btn, (.05, .08, .085, 1), EDGE, dp(22), .8)
    gear_icon = GearIcon(size_hint=(1, 1), pos_hint={'center_x': .5, 'center_y': .5})
    gear_btn.add_widget(gear_icon)
    
    def on_gear_touch(instance, touch):
        if instance.collide_point(*touch.pos):
            show_settings()
            return True
        return False
    gear_btn.bind(on_touch_down=on_gear_touch)
    
    header.add_widget(gear_btn)
    home.add_widget(header)

    # Core and listening status. Use relative geometry so it scales on Redmi 8 portrait.
    orb = OrbCore(size_hint=(.78,.37), pos_hint={'center_x':.5,'center_y':.59})
    home.add_widget(orb); app.core_widget=orb
    status = make_label('Ready when you are',14,MUTED,False,'center')
    status.size_hint=(.9,None); status.height=dp(30); status.pos_hint={'center_x':.5,'center_y':.365}
    home.add_widget(status); app.status_label=status

    # Optional tiny interaction history caption as in the reference phone footer.
    history_caption = make_label('JARVIS • PERSONAL ASSISTANT',9,(.36,.48,.49,1),False,'center')
    history_caption.size_hint=(.9,None); history_caption.height=dp(18); history_caption.pos_hint={'center_x':.5,'y':.125}
    home.add_widget(history_caption)

    # Message composer remains fixed at the bottom of the home screen.
    composer = BoxLayout(orientation='horizontal', size_hint=(.88,None), height=dp(48), spacing=dp(6),
                         padding=[dp(12),dp(4),dp(6),dp(4)], pos_hint={'center_x':.48,'y':.055})
    plate(composer,(.10,.14,.15,1),(.28,.39,.40,.85),dp(25),.8)
    chat = TextInput(hint_text='Message...', multiline=False, font_size='14sp', foreground_color=WHITE,
                     hint_text_color=MUTED, cursor_color=CYAN, background_normal='',background_active='',
                     background_color=(0,0,0,0), padding=[dp(3),dp(8)])
    app.chat_input=chat
    def send_message(*_):
        message=chat.text.strip()
        if not message: return
        chat.text=''
        set_status('You: '+message)
        try: app.process_command(message)
        except Exception as exc: set_status('Message could not be processed')
    chat.bind(on_text_validate=send_message)
    composer.add_widget(chat)
    send = Button(text='',size_hint=(None,1),width=dp(42),background_normal='',background_down='',background_color=(0,0,0,0))
    send.add_widget(PaperPlane(size_hint=(1,1))); send.bind(on_release=send_message); composer.add_widget(send)
    home.add_widget(composer)

    # Settings screen matching the provided right-side configuration board, opened by gear.
    settings_header=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(8))
    close_btn=ui_button('< Close',lambda:None,12,WHITE,(.12,.17,.18,1),dp(34))
    settings_title=make_label('JARVIS Settings',17,WHITE,True)
    settings_header.add_widget(close_btn); settings_header.add_widget(settings_title); settings_page.add_widget(settings_header)

    scroll=ScrollView(do_scroll_x=False,bar_width=dp(2),scroll_type=['bars','content'])
    content=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(9),padding=[0,dp(2),0,dp(8)])
    content.bind(minimum_height=content.setter('height'))

    # Voice Selection card
    voice_card=SectionCard(size_hint_y=None,height=dp(170))
    voice_title=make_label('Voice Selection',16,WHITE,True); voice_card.add_widget(voice_title)
    current_voice=make_label('Current: System default',11,MUTED); voice_card.add_widget(current_voice)
    voice_grid=GridLayout(cols=3,spacing=dp(7),size_hint_y=None,height=dp(80))
    voice_items=[('Female\nBeta','Female Beta'),('Formal\nGamma','Formal Gamma'),('Casual\nDelta','Casual Delta')]
    for label, value in voice_items:
        cell=BoxLayout(orientation='vertical',spacing=dp(3))
        avatar=make_label('●',24,CYAN,True,'center')
        cell.add_widget(avatar)
        cell.add_widget(make_label(label,10,WHITE,False,'center'))
        def choose(v=value, lab=label):
            app.selected_voice=v
            current_voice.text='Current: '+v
            set_status('Voice selected: '+v)
        cell.add_widget(ui_button('Select',lambda v=value,lab=label: choose(v,lab),10,CYAN,(.08,.16,.17,1),dp(26)))
        voice_grid.add_widget(cell)
    voice_card.add_widget(voice_grid); content.add_widget(voice_card)

    # History card
    history_card=SectionCard(size_hint_y=None,height=dp(150))
    history_card.add_widget(make_label('History',16,WHITE,True))
    history_text=make_label('Recent interactions will appear here.',11,MUTED)
    history_card.add_widget(history_text)
    history_card.add_widget(ui_button('Clear history',lambda: setattr(history_text,'text','History cleared.'),11,CYAN,(.08,.16,.17,1),dp(30)))
    content.add_widget(history_card)

    # Wake word
    wake_card=SectionCard(size_hint_y=None,height=dp(105))
    wake_card.add_widget(make_label('Wake Word Customization',15,WHITE,True))
    wake_input=TextInput(text=getattr(app,'wake_word','Hey JARVIS'),hint_text='Hey JARVIS',multiline=False,size_hint_y=None,height=dp(38),font_size='14sp',foreground_color=WHITE,hint_text_color=MUTED,background_normal='',background_active='',background_color=(.025,.055,.06,1),cursor_color=CYAN,padding=[dp(10),dp(8)])
    wake_input.bind(text=lambda _,v:setattr(app,'wake_word',v.strip() or 'Hey JARVIS'))
    wake_card.add_widget(wake_input); content.add_widget(wake_card)

    # Response verbosity
    verbosity=SectionCard(size_hint_y=None,height=dp(115))
    verbosity.add_widget(make_label('Response Verbosity',15,WHITE,True))
    slider=Slider(min=0,max=2,value=1,step=1,cursor_size=(dp(18),dp(18)),size_hint_y=None,height=dp(30))
    verbosity.add_widget(slider)
    verbosity_labels=make_label('Detailed  |  Balanced  |  Concise',10,MUTED)
    verbosity.add_widget(verbosity_labels); content.add_widget(verbosity)

    # Privacy & security
    privacy=SectionCard(size_hint_y=None,height=dp(118))
    privacy.add_widget(make_label('Data Privacy & Security',15,WHITE,True))
    privacy.add_widget(make_label('Manage stored data\nClear history\nPrivacy settings',11,MUTED))
    privacy.add_widget(ui_button('Clear visible history',lambda: setattr(history_text,'text','History cleared.'),10,CYAN,(.08,.16,.17,1),dp(28)))
    content.add_widget(privacy)

    # Appearance
    appearance=SectionCard(size_hint_y=None,height=dp(100))
    appearance.add_widget(make_label('Appearance',15,WHITE,True))
    theme_row=BoxLayout(size_hint_y=None,height=dp(34),spacing=dp(5))
    for t in ('Light','Dark','System'):
        theme_row.add_widget(ui_button(t,lambda val=t:set_status('Theme: '+val),11,CYAN,(.08,.16,.17,1),dp(32)))
    appearance.add_widget(theme_row); content.add_widget(appearance)

    # Integration Settings
    integration=SectionCard(size_hint_y=None,height=dp(120))
    integration.add_widget(make_label('Integration Settings',15,WHITE,True))
    integration.add_widget(make_label('Connect smart home\nSync calendar\nLink accounts',11,MUTED))
    content.add_widget(integration)
    scroll.add_widget(content); settings_page.add_widget(scroll)

    def set_status(text):
        try:
            status.text=str(text)
            if hasattr(app,'set_status'): app.set_status(str(text))
        except Exception:
            status.text=str(text)
    def set_listening(active=True):
        orb.listening=active; orb.speaking=False
        status.text='Listening...' if active else 'Ready when you are'
    def start_listening(*_):
        set_listening(True)
        try: app.listen()
        except Exception: set_status('Listening...')
        Clock.schedule_once(lambda dt:setattr(orb,'listening',False),6)
    def show_settings(*_):
        home.opacity=0; home.disabled=True
        settings_page.opacity=1; settings_page.disabled=False
    def hide_settings(*_):
        settings_page.opacity=0; settings_page.disabled=True
        home.opacity=1; home.disabled=False
    close_btn.bind(on_release=hide_settings)
    orb.on_tap = start_listening
    
    app.toggle_voice_selection=show_settings
    app.open_jarvis_settings=show_settings
    app.start_jarvis_listening=start_listening

    app.calc_panel=BoxLayout(orientation='vertical',size_hint_y=None,height=0,opacity=0,disabled=True)
    app.calc_question_label=make_label('',10); app.calc_answer_label=make_label('',12,CYAN,True)
    app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})(); app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]
    app.root_layout=root
    return root
