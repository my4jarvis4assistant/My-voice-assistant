"""Alex AI / JARVIS reference-layout UI, isolated from assistant logic.
UI-only update: does not alter main.py or alarm/timer/reminder/calculator handlers.
"""
import math
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView

BG=(.008,.018,.030,1); PANEL=(.018,.040,.057,.97); PANEL2=(.026,.060,.079,.98)
CYAN=(.27,.91,1,1); CYAN2=(.10,.62,.78,1); GOLD=(.96,.77,.43,1)
WHITE=(.88,.94,.98,1); MUTED=(.52,.68,.76,1); GREEN=(.27,.98,.61,1)


def make_label(text, size=12, color=WHITE, bold=False, align='left'):
    w=Label(text=text,font_size=f'{size}sp',color=color,bold=bold,halign=align,valign='middle',shorten=True,shorten_from='right')
    w.bind(size=lambda o,s:setattr(o,'text_size',(max(0,s[0]-dp(8)),s[1])))
    return w

def panel(widget, fill=PANEL, edge=CYAN2, radius=dp(15), width=1):
    with widget.canvas.before:
        Color(*fill); widget._panel_bg=RoundedRectangle(pos=widget.pos,size=widget.size,radius=[radius])
        Color(*edge); widget._panel_line=Line(rounded_rectangle=(widget.x,widget.y,widget.width,widget.height,radius),width=width)
    def sync(*_):
        widget._panel_bg.pos=widget.pos; widget._panel_bg.size=widget.size
        widget._panel_line.rounded_rectangle=(widget.x,widget.y,widget.width,widget.height,radius)
    widget.bind(pos=sync,size=sync)
    return widget

def make_button(text, callback, h=dp(38), color=WHITE, bg=(.025,.075,.096,1), fs=11):
    b=Button(text=text,size_hint_y=None,height=h,font_size=f'{fs}sp',bold=True,color=color,
             background_normal='',background_down='',background_color=bg)
    b.bind(on_release=lambda *_: callback())
    return b

def set_status(app,text):
    try: app.set_status(text)
    except Exception:
        try: app.status_label.text=text
        except Exception: pass

def prompt(app,text):
    set_status(app,'READY • '+text.upper())
    try:
        if getattr(app,'tts',None): app.tts.speak(text,0,None)
    except Exception: pass

class Reactor(Widget):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); self.phase=0; self.bind(pos=self.draw,size=self.draw); Clock.schedule_interval(self.tick,1/30); self.draw()
    def tick(self,dt): self.phase=(self.phase+dt*.55)%(math.pi*2); self.draw()
    def draw(self,*_):
        self.canvas.clear(); cx,cy=self.center; r=max(dp(18),min(self.width,self.height)*.30); ph=self.phase
        with self.canvas:
            Color(.0,.52,.92,.035); Ellipse(pos=(cx-r*1.65,cy-r*1.65),size=(r*3.3,r*3.3))
            Color(.0,.7,1,.06); Ellipse(pos=(cx-r*1.32,cy-r*1.32),size=(r*2.64,r*2.64))
            Color(.012,.035,.052,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(*CYAN); Line(circle=(cx,cy,r),width=dp(1.5))
            Color(*GOLD); Line(circle=(cx,cy,r*.91),width=dp(.8))
            Color(.08,.5,.7,.9); Line(circle=(cx,cy,r*.78),width=dp(1.2))
            for i in range(72):
                a=2*math.pi*i/72+ph*.06; ri=r*(1.04 if i%6==0 else .99); ro=r*(1.12 if i%6==0 else 1.025)
                Color(*(GOLD if i%6==0 else CYAN2)); Line(points=[cx+ri*math.cos(a),cy+ri*math.sin(a),cx+ro*math.cos(a),cy+ro*math.sin(a)],width=dp(.9))
            for rad,n,off,col in ((.68,8,ph,CYAN),(.55,7,-ph*1.1,GOLD),(.42,9,ph*.8,CYAN2)):
                for i in range(n):
                    a=off+2*math.pi*i/n; pts=[]
                    for j in range(12):
                        aa=a+j*.035; rr=r*rad*(1+.04*math.sin(ph*2+j*.5)); pts += [cx+rr*math.cos(aa),cy+rr*math.sin(aa)]
                    Color(*col); Line(points=pts,width=dp(1.5))
            Color(.02,.14,.2,1); Ellipse(pos=(cx-r*.34,cy-r*.34),size=(r*.68,r*.68))
            Color(*CYAN); Line(circle=(cx,cy,r*.31),width=dp(1.2))
            Color(.35,.9,1,.9); Ellipse(pos=(cx-r*.07,cy-r*.07),size=(r*.14,r*.14))
            # Horizontal audio waveform through reactor.
            Color(.3,.9,1,.9); pts=[]; count=45
            for i in range(count):
                x=cx-r*1.25+(r*2.5*i/(count-1)); amp=r*(.08+.30*abs(math.sin(i*.83+ph*2))*abs(math.sin(i*.23+ph)))
                pts += [x,cy-amp,x,cy+amp]
            Line(points=pts,width=dp(1.05))
            for i in range(4):
                a=ph*(1 if i%2 else -1)+i*math.pi/2; rr=r*(.95 if i%2 else 1.06)
                Color(*(GOLD if i in (0,2) else CYAN)); Ellipse(pos=(cx+rr*math.cos(a)-dp(2),cy+rr*math.sin(a)-dp(2)),size=(dp(4),dp(4)))

class FingerprintButton(Button):
    """Fingerprint-style visual trigger. Not Android biometric authentication."""
    def __init__(self,**kw):
        super().__init__(text='',background_normal='',background_down='',background_color=(0,0,0,0),**kw); self.bind(pos=self.draw,size=self.draw); self.draw()
    def draw(self,*_):
        self.canvas.clear(); cx,cy=self.center; r=max(dp(12),min(self.width,self.height)*.39)
        with self.canvas:
            Color(.0,.7,1,.10); Ellipse(pos=(cx-r*1.35,cy-r*1.35),size=(r*2.7,r*2.7))
            Color(.018,.06,.085,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(*GOLD); Line(circle=(cx,cy,r*1.04),width=dp(1))
            Color(*CYAN); Line(circle=(cx,cy,r*.92),width=dp(1.6))
            Color(.035,.12,.16,1); Ellipse(pos=(cx-r*.74,cy-r*.74),size=(r*1.48,r*1.48))
            Color(.48,.94,1,1)
            # Rounded, nested fingerprint ridges drawn as smooth segmented lines.
            for i in range(7):
                half=r*(.18+i*.075); top=cy+r*(.52-i*.035); bottom=cy-r*(.40-i*.022); pts=[]
                for j in range(31):
                    t=j/30; y=top-(top-bottom)*t; x=cx+half*math.sin(math.pi*t)
                    pts += [x,y]
                Line(points=pts,width=dp(1.0))
            Color(*GOLD); Line(points=[cx,cy-r*.18,cx,cy+r*.13],width=dp(1.0))

class SettingsPanel(BoxLayout):
    def __init__(self,app,on_close,**kwargs):
        super().__init__(orientation='vertical',spacing=dp(5),padding=[dp(9),dp(8),dp(9),dp(8)],**kwargs)
        self.app=app; self.on_close=on_close; panel(self,(.014,.033,.049,.985),(.20,.67,.79,.95),dp(18),1.2)
        head=BoxLayout(size_hint_y=None,height=dp(32),spacing=dp(3)); head.add_widget(make_label('Voice Selection',15,GOLD,True))
        head.add_widget(make_button('×',on_close,dp(30),GOLD,(.05,.10,.13,1),17)); self.add_widget(head)
        names=['Alate troiina','Tioteerabuh','Wardsolstae','Suienger fight','Mginall shceratioe','Etseoabrck']
        self.voice_buttons=[]
        for i,name in enumerate(names):
            def choose(n=name,idx=i): self.select_voice(n,idx)
            b=make_button('◉   '+name+'    ···',choose,dp(38),CYAN if i==0 else WHITE,(.025,.064,.083,1),10)
            panel(b,(.025,.064,.083,1),(.20,.38,.47,.85),dp(16),.8); self.voice_buttons.append(b); self.add_widget(b)
        self.add_widget(make_label('Wake-word',11,WHITE,True))
        self.wake_input=TextInput(text=getattr(app,'wake_word','Chene'),hint_text='Chene',multiline=False,size_hint_y=None,height=dp(37),font_size='13sp',foreground_color=WHITE,cursor_color=CYAN,background_normal='',background_active='',background_color=(.018,.045,.061,1),padding=[dp(10),dp(9)])
        self.add_widget(self.wake_input)
        save=make_button('SAVE WAKE-WORD',self.save_wake,dp(31),CYAN,(.025,.08,.10,1),9); self.add_widget(save)
        self.add_widget(make_label('Theme',11,WHITE,True))
        row=BoxLayout(size_hint_y=None,height=dp(39),spacing=dp(5)); row.add_widget(make_label('AI Share / Glow',10,MUTED))
        self.theme_btn=make_button('ON  ◉',self.toggle_theme,dp(36),CYAN,(.025,.08,.10,1),10); row.add_widget(self.theme_btn); self.add_widget(row)
        self.theme_on=True
    def select_voice(self,name,idx):
        self.app.selected_voice=name
        # Six genuine selectable TTS profiles using available Android TTS controls.
        try:
            tts=getattr(self.app,'tts',None)
            if tts:
                rates=[.86,.94,1.0,1.08,1.16,.98]; pitches=[.88,1.0,1.12,.94,1.06,.82]
                tts.setSpeechRate(rates[idx]); tts.setPitch(pitches[idx])
                tts.speak('Voice selected: '+name,0,None)
        except Exception: pass
        for i,b in enumerate(self.voice_buttons): b.color=CYAN if i==idx else WHITE
        set_status(self.app,'VOICE SELECTED • '+name.upper())
    def save_wake(self):
        value=self.wake_input.text.strip()
        if not value: value='Chene'; self.wake_input.text=value
        self.app.wake_word=value
        set_status(self.app,'WAKE-WORD SAVED • '+value.upper())
    def toggle_theme(self):
        self.theme_on=not self.theme_on
        self.theme_btn.text='ON  ◉' if self.theme_on else 'OFF  ○'
        self.theme_btn.color=CYAN if self.theme_on else GOLD
        set_status(self.app,'AI SHARE / GLOW '+('ON' if self.theme_on else 'OFF'))

def build_jarvis_ui(app):
    root=FloatLayout()
    with root.canvas.before:
        Color(*BG); root._bg=RoundedRectangle(pos=root.pos,size=root.size,radius=[0])
        Color(.0,.28,.45,.09); root._halo=Ellipse(pos=(0,0),size=(dp(400),dp(400)))
    def sync_bg(*_):
        root._bg.pos=root.pos; root._bg.size=root.size; root._halo.pos=(root.center_x-dp(200),root.center_y-dp(160))
    root.bind(pos=sync_bg,size=sync_bg)
    # Content is vertical and proportionally sized for portrait phones.
    body=BoxLayout(orientation='vertical',padding=[dp(10),dp(8),dp(10),dp(7)],spacing=dp(6),size_hint=(1,1),pos_hint={'x':0,'y':0})
    root.add_widget(body)
    header=BoxLayout(size_hint_y=None,height=dp(47),spacing=dp(7))
    header.add_widget(make_label('Alex AI',25,CYAN,True))
    online=make_label('●',16,GREEN,True); online.size_hint_x=None; online.width=dp(18); header.add_widget(online)
    header.add_widget(make_label('ONLINE',9,GREEN,True))
    gear=make_button('⚙',lambda:toggle_panel(),dp(42),GOLD,(.035,.065,.085,1),22); gear.size_hint_x=None; gear.width=dp(48); header.add_widget(gear)
    body.add_widget(header)
    # Main region: chat + reactor, while settings floats over right side like reference.
    stage=FloatLayout(size_hint_y=1)
    body.add_widget(stage)
    main_col=BoxLayout(orientation='vertical',spacing=dp(5),size_hint=(1,1),pos_hint={'x':0,'y':0},padding=[dp(1),dp(2),dp(1),dp(1)])
    stage.add_widget(main_col)
    # Short chat bubbles above visualizer.
    bubble1=BoxLayout(size_hint_y=None,height=dp(43),padding=[dp(9),dp(3),dp(9),dp(3)])
    panel(bubble1,(.035,.065,.086,.96),(.62,.49,.28,.8),dp(18),.8)
    bubble1.add_widget(make_label('◉  ALEX AI   /   READY TO ASSIST',10,GOLD,True)); main_col.add_widget(bubble1)
    app.status_label=make_label('Hello! I am listening for your command.',12,WHITE,False)
    status_card=BoxLayout(size_hint_y=None,height=dp(48),padding=[dp(9),dp(3),dp(9),dp(3)])
    panel(status_card,(.025,.075,.098,.97),(.12,.62,.76,.9),dp(16),1)
    status_card.add_widget(app.status_label); main_col.add_widget(status_card)
    corebox=BoxLayout(size_hint_y=1,padding=[dp(1),dp(1),dp(1),dp(1)])
    app.core_widget=Reactor(); corebox.add_widget(app.core_widget); main_col.add_widget(corebox)
    # Chat response bubble under reactor.
    response=BoxLayout(size_hint_y=None,height=dp(48),padding=[dp(9),dp(3),dp(9),dp(3)])
    panel(response,(.03,.07,.09,.96),(.12,.55,.68,.8),dp(17),.8)
    response.add_widget(make_label('◉  VOICE INTERFACE  •  TAP FINGERPRINT TO SPEAK',9,CYAN,True)); main_col.add_widget(response)
    # Overlay panel at upper-right, toggled by header and bottom settings.
    app.ui_settings_panel=SettingsPanel(app,lambda:toggle_panel(),size_hint=(.69,.70),pos_hint={'right':.99,'top':.985})
    app.ui_settings_panel.opacity=1; app.ui_settings_panel.disabled=False
    stage.add_widget(app.ui_settings_panel)
    panel_state={'open':True}
    def toggle_panel(*_):
        panel_state['open']=not panel_state['open']
        app.ui_settings_panel.opacity=1 if panel_state['open'] else 0
        app.ui_settings_panel.disabled=not panel_state['open']
        if panel_state['open']: set_status(app,'VOICE SELECTION PANEL OPEN')
    # Header gear callback toggles the floating panel.
    # Four compact action buttons in one glowing rounded bar.
    quick=GridLayout(cols=4,spacing=dp(4),size_hint_y=None,height=dp(67),padding=[dp(5),dp(5),dp(5),dp(4)])
    panel(quick,(.025,.075,.09,.98),(.22,.70,.81,.95),dp(20),1.2)
    def run_command(text):
        set_status(app,'COMMAND • '+text.upper())
        try:
            if getattr(app,'tts',None): app.tts.speak(text,0,None)
        except Exception: pass
    for title,icon,cmd,method in [('Alarms','◷','alarm lagao',None),('Reminders','⌂','reminder banao',None),('Weather','☼','weather batao',None),('Messages','▤','messages kholo','open_messages')]:
        cell=BoxLayout(orientation='vertical',spacing=dp(1))
        b=make_button(icon,lambda c=cmd,m=method: (getattr(app,m)() if m and hasattr(app,m) else run_command(c)),dp(35),GOLD if title=='Alarms' else CYAN,(.025,.08,.10,1),19)
        cell.add_widget(b); cell.add_widget(make_label(title,9,WHITE,True,'center')); quick.add_widget(cell)
    body.add_widget(quick)
    footer=BoxLayout(size_hint_y=None,height=dp(69),spacing=dp(8),padding=[dp(4),dp(2),dp(4),dp(1)])
    hist=make_button('History',lambda:run_command('recent history batao'),dp(54),GOLD,(.022,.045,.062,1),12); panel(hist,(.022,.045,.062,1),(.45,.36,.23,.9),dp(22),.8)
    fp=FingerprintButton(size_hint_x=1.0,size_hint_y=1)
    fp.bind(on_release=lambda *_:getattr(app,'listen',lambda:set_status(app,'Listening…'))())
    settings=make_button('Settings',toggle_panel,dp(54),GOLD,(.022,.045,.062,1),12); panel(settings,(.022,.045,.062,1),(.45,.36,.23,.9),dp(22),.8)
    footer.add_widget(hist); footer.add_widget(fp); footer.add_widget(settings); body.add_widget(footer)
    # Keep calculator integration contract expected by main.py.
    app.calc_panel=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(34),padding=[dp(8),dp(1),dp(8),dp(1)],spacing=0)
    panel(app.calc_panel,(.02,.038,.055,.97),(.15,.42,.53,.6),dp(9),.7)
    app.calc_question_label=make_label('CALCULATOR / VOICE INPUT',8,MUTED,True)
    app.calc_answer_label=make_label('ANSWER / —',10,CYAN,True)
    app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})(); app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]
    body.add_widget(app.calc_panel)
    app.root_layout=root
    return root
