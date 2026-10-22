"""JARVIS v0.32 - premium portrait HUD UI for Kivy/Android.
UI-only replacement. Existing assistant logic stays in main.py.
"""
import math
from kivy.metrics import dp
from kivy.clock import Clock
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

BG=(.008,.018,.030,1); PANEL=(.018,.050,.071,.97); CYAN=(.20,.88,1,1); GOLD=(.94,.79,.53,1); WHITE=(.87,.94,.98,1); MUTED=(.48,.66,.73,1)

def lbl(text,size=14,color=WHITE,bold=False,halign='left'):
    w=Label(text=text,font_size=f'{size}sp',color=color,bold=bold,halign=halign,valign='middle',markup=False)
    w.bind(size=lambda o,v:setattr(o,'text_size',(max(0,v[0]-dp(5)),v[1])))
    return w

def panel(w,bg=PANEL,edge=(.10,.56,.70,.8),radius=dp(16)):
    with w.canvas.before:
        Color(*bg); w._plate=RoundedRectangle(pos=w.pos,size=w.size,radius=[radius])
        Color(*edge); w._edge=Line(rounded_rectangle=(w.x,w.y,w.width,w.height,radius),width=1.0)
    def sync(*_):
        w._plate.pos=w.pos; w._plate.size=w.size; w._edge.rounded_rectangle=(w.x,w.y,w.width,w.height,radius)
    w.bind(pos=sync,size=sync); return w

def button(text,callback,size=13,color=WHITE,bg=(.025,.09,.13,1)):
    b=Button(text=text,font_size=f'{size}sp',color=color,background_normal='',background_down='',background_color=bg,halign='center',valign='middle')
    b.bind(on_release=lambda *_: callback())
    return b

class StatusDot(Widget):
    def __init__(self,**kw):
        super().__init__(**kw); self.bind(pos=self.draw,size=self.draw); self.draw()
    def draw(self,*_):
        self.canvas.clear(); x,y=self.center; r=min(self.width,self.height)*.23
        with self.canvas:
            Color(.05,.9,.48,.16); Ellipse(pos=(x-r*2,y-r*2),size=(r*4,r*4))
            Color(.10,1,.55,1); Ellipse(pos=(x-r,y-r),size=(r*2,r*2))

class PremiumCore(Widget):
    """Non-rotating concentric HUD rings; waveform and glow pulse with state."""
    def __init__(self,**kw):
        super().__init__(**kw); self.phase=0.; self.listening=False; self.speaking=False; self.bind(pos=self.draw,size=self.draw); Clock.schedule_interval(self.tick,1/24)
    def tick(self,dt):
        self.phase += dt*(4.4 if self.listening or self.speaking else 1.25); self.draw()
    def draw(self,*_):
        self.canvas.clear(); cx,cy=self.center; r=max(dp(18),min(self.width,self.height)*.34); active=self.listening or self.speaking
        pulse=1+(.045 if active else .018)*math.sin(self.phase*2.1)
        with self.canvas:
            # Soft halo, stationary rings; only glow strength and waveform breathe.
            Color(.02,.56,.98,.06+.05*(.5+.5*math.sin(self.phase*2))); Ellipse(pos=(cx-r*1.48,cy-r*1.48),size=(r*2.96,r*2.96))
            Color(.012,.035,.058,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            for idx,(factor,col,width) in enumerate([(1.30,(.16,.69,.91,.42),.8),(1.12,(.18,.82,1,.88),1.35),(.98,(.30,.65,.96,.7),.9),(.82,(.18,.77,.98,.9),1.25),(.65,(.20,.56,.82,.75),.8),(.48,(.23,.83,1,.8),1.1)]):
                Color(col[0],col[1],col[2],col[3]*(.7+.3*(.5+.5*math.sin(self.phase*2+idx))))
                Line(circle=(cx,cy,r*factor*(pulse if idx in (1,3) else 1)),width=dp(width))
            # Small gold/cyan arc segments, no rotation.
            for start,end,col in [(28,73,GOLD),(205,247,GOLD),(88,124,CYAN),(270,308,CYAN)]:
                pts=[]
                for j in range(25):
                    a=math.radians(start+(end-start)*j/24); pts.extend([cx+math.cos(a)*r*1.18,cy+math.sin(a)*r*1.18])
                Color(*col[:3],.86); Line(points=pts,width=dp(2))
            # Dynamic central waveform.
            count=17; gap=r*.075
            for i in range(count):
                rel=i-(count-1)/2
                wave=abs(math.sin(i*1.17+self.phase*(2.8 if active else .7)))
                height=r*(.12+wave*(.28 if active else .19))
                if i==count//2: height*=1.22
                x=cx+rel*gap
                Color(.22,.88,1,.96 if active else .78); Line(points=[x,cy-height,x,cy+height],width=dp(2.1),cap='round')
            Color(.7,.95,1,.9); Ellipse(pos=(cx-dp(2),cy-dp(2)),size=(dp(4),dp(4)))

class FingerprintButton(Button):
    def __init__(self,**kw):
        super().__init__(**kw); self.text=''; self.background_normal=''; self.background_down=''; self.background_color=(0,0,0,0); self.bind(pos=self.draw,size=self.draw); self.draw()
    def draw(self,*_):
        self.canvas.clear(); cx,cy=self.center; r=min(self.width,self.height)*.36
        with self.canvas:
            Color(.02,.65,.91,.14); Ellipse(pos=(cx-r*1.5,cy-r*1.5),size=(r*3,r*3))
            Color(.26,.75,.88,.9); Line(circle=(cx,cy,r*1.28),width=dp(1.2))
            Color(.012,.04,.065,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(.22,.88,1,1); Line(circle=(cx,cy,r*.99),width=dp(1.2))
            # Fingerprint ridges using open curves.
            for k in range(5):
                pts=[]; width=r*(.24+k*.105)
                for j in range(31):
                    t=j/30; x=cx+width*math.sin(math.pi*t); y=cy+r*(.56-t*1.12)
                    pts.extend((x,y))
                Color(.30,.88,1,.92); Line(points=pts,width=dp(1.15))

def build_jarvis_ui(app):
    root=FloatLayout()
    with root.canvas.before:
        Color(*BG); root._bg=RoundedRectangle(pos=root.pos,size=root.size,radius=[dp(18)])
        Color(.02,.22,.31,.7); root._border=Line(rounded_rectangle=(root.x,root.y,root.width,root.height,dp(18)),width=1)
    def sync_root(*_): root._bg.pos=root.pos; root._bg.size=root.size; root._border.rounded_rectangle=(root.x,root.y,root.width,root.height,dp(18))
    root.bind(pos=sync_root,size=sync_root)
    # Header
    header=BoxLayout(orientation='horizontal',size_hint=(1,None),height=dp(58),padding=[dp(16),dp(4),dp(12),dp(4)],spacing=dp(4),pos_hint={'x':0,'top':1})
    header.add_widget(lbl('JARVIS',24,CYAN,True)); dot=StatusDot(size_hint=(None,1),width=dp(26)); header.add_widget(dot); header.add_widget(Widget())
    gear=button('⚙',lambda:getattr(app,'open_settings',lambda:None)(),23,GOLD,(.02,.07,.10,1)); gear.size_hint=(None,1); gear.width=dp(48); header.add_widget(gear); root.add_widget(header)
    # Main viewport: flexible proportions, designed for portrait screens.
    stage=FloatLayout(size_hint=(1,.64),pos_hint={'x':0,'top':.925})
    app.status_label=lbl('JARVIS READY',11,CYAN,True); app.status_label.size_hint=(.53,None); app.status_label.height=dp(25); app.status_label.pos_hint={'x':.035,'top':.99}; stage.add_widget(app.status_label)
    # chat bubbles like reference, in left lane
    b1=panel(BoxLayout(padding=[dp(10),dp(4)],size_hint=(.49,None),height=dp(40),pos_hint={'x':.13,'top':.91}),(.025,.075,.105,.95),(.15,.66,.78,.8),dp(18)); b1.add_widget(lbl('JARVIS online  •',11,WHITE)); stage.add_widget(b1)
    b2=panel(BoxLayout(padding=dp(8),size_hint=(.47,None),height=dp(58),pos_hint={'x':.13,'top':.79}),(.02,.20,.28,.95),(.10,.72,.88,.85),dp(17)); b2.add_widget(lbl('Boliye, main sun raha hoon.',11,WHITE)); stage.add_widget(b2)
    core=PremiumCore(size_hint=(.58,.51),pos_hint={'x':.005,'y':.18}); stage.add_widget(core); app.core_widget=core
    b3=panel(BoxLayout(padding=dp(8),size_hint=(.48,None),height=dp(56),pos_hint={'x':.13,'y':.045}),(.02,.18,.25,.95),(.12,.65,.80,.85),dp(17)); b3.add_widget(lbl('Aap voice ya message se baat kar sakte hain.',10,WHITE)); stage.add_widget(b3)
    # Right-side drawer stays in reference position; collapsed mode gives core more room.
    drawer=panel(BoxLayout(orientation='vertical',spacing=dp(5),padding=dp(8),size_hint=(.43,.88),pos_hint={'right':.985,'top':.97}),(.012,.032,.05,.98),(.22,.58,.68,.9),dp(17))
    dhead=BoxLayout(size_hint_y=None,height=dp(32),spacing=dp(3)); dhead.add_widget(lbl('Voice Selection',13,GOLD,True)); dhead.add_widget(button('•••',lambda:toggle_drawer(),17,GOLD,(0,0,0,0))); drawer.add_widget(dhead)
    sep=Widget(size_hint_y=None,height=dp(1)); drawer.add_widget(sep)
    scroll=ScrollView(do_scroll_x=False,bar_width=dp(2)); voices=GridLayout(cols=1,spacing=dp(5),size_hint_y=None); voices.bind(minimum_height=voices.setter('height'))
    voice_choices=('System default','English (India)','English (US)','Hindi (India)')
    for v in voice_choices:
        voices.add_widget(button('♙   '+v,lambda choice=v:select_voice(choice),11,WHITE,(.025,.075,.10,1)))
    scroll.add_widget(voices); drawer.add_widget(scroll); drawer.add_widget(lbl('Tap a voice to select',9,MUTED))
    drawer.add_widget(lbl('Wake-word',12,GOLD,True)); wake=TextInput(text=getattr(app,'wake_word','JARVIS'),multiline=False,size_hint_y=None,height=dp(32),font_size='13sp',foreground_color=WHITE,background_normal='',background_active='',background_color=(.025,.07,.09,1),cursor_color=CYAN,padding=[dp(8),dp(6)])
    wake.bind(text=lambda _,v:setattr(app,'wake_word',v.strip() or 'JARVIS')); drawer.add_widget(wake)
    drawer.add_widget(button('Theme       →',lambda:set_status('Theme settings'),13,GOLD,(.02,.06,.09,1)))
    stage.add_widget(drawer)
    def set_status(s):
        try: app.set_status(s)
        except Exception: app.status_label.text=s
    def select_voice(v):
        app.selected_voice=v; set_status('Voice selected: '+v)
        try:
            from jnius import autoclass
            Locale=autoclass('java.util.Locale'); loc={'English (India)':Locale('en','IN'),'English (US)':Locale.US,'Hindi (India)':Locale('hi','IN')}.get(v)
            if getattr(app,'tts',None) and loc: app.tts.setLanguage(loc)
        except Exception: pass
    drawer_open=True
    def toggle_drawer(*_):
        nonlocal drawer_open
        drawer_open=not drawer_open
        drawer.opacity=1 if drawer_open else 0; drawer.disabled=not drawer_open
        core.size_hint_x=.58 if drawer_open else .82
        core.pos_hint={'x':.005 if drawer_open else .08,'y':.18}
        # Keep left chat lane visible, but give the core more width when drawer is hidden.
        set_status('VOICE SELECTION OPEN' if drawer_open else 'JARVIS READY')
    app.toggle_voice_selection=toggle_drawer
    # Dedicated trigger below top settings, matching reference composition.
    trigger=button('VOICE SELECTION   •••',toggle_drawer,11,GOLD,(.025,.065,.09,1)); trigger.size_hint=(.43,None); trigger.height=dp(30); trigger.pos_hint={'right':.985,'top':.665}; root.add_widget(stage)
    root.add_widget(trigger)
    # Quick actions panel
    quick=panel(BoxLayout(orientation='horizontal',spacing=dp(2),padding=dp(5),size_hint=(.95,None),height=dp(76),pos_hint={'center_x':.5,'y':.205}),(.02,.075,.105,.98),(.16,.72,.84,.92),dp(18))
    def quick_action(title,command,method=None):
        def run():
            if method and hasattr(app,method):
                try: getattr(app,method)(); return
                except Exception: pass
            set_status('Boliye: '+command)
            try:
                if getattr(app,'tts',None): app.tts.speak('Kripya '+command+' boliye.',0,None)
            except Exception: pass
        cell=BoxLayout(orientation='vertical',spacing=dp(1)); cell.add_widget(lbl({'Alarm':'◷','Reminder':'▦','Weather':'◉','Message':'▤','Call':'☎'}.get(title,'•'),21,CYAN,True,'center')); cell.add_widget(button(title,run,10,WHITE,(.01,.04,.06,0))); quick.add_widget(cell)
    quick_action('Alarm','alarm lagao'); quick_action('Reminder','reminder banao'); quick_action('Weather','weather batao'); quick_action('Message','messages kholo','open_messages'); quick_action('Call','phone kholo','open_phone'); root.add_widget(quick)
    # Lower rail: History / central fingerprint / Settings
    footer=BoxLayout(orientation='horizontal',spacing=dp(8),padding=[dp(12),dp(3),dp(12),dp(3)],size_hint=(1,None),height=dp(64),pos_hint={'x':0,'y':.125})
    footer.add_widget(button('History',lambda:set_status('History'),12,GOLD,(.02,.06,.09,1)))
    fp=FingerprintButton(size_hint=(None,1),width=dp(70)); fp.bind(on_release=lambda *_:start_listening()); footer.add_widget(fp)
    footer.add_widget(button('Settings',lambda:getattr(app,'open_settings',lambda:None)(),12,GOLD,(.02,.06,.09,1))); root.add_widget(footer)
    def start_listening():
        core.listening=True; Clock.schedule_once(lambda _dt:setattr(core,'listening',False),6)
        try: app.listen()
        except Exception: set_status('Listening...')
    # Chat composer
    composer=panel(BoxLayout(orientation='horizontal',spacing=dp(5),padding=dp(5),size_hint=(.96,None),height=dp(47),pos_hint={'center_x':.5,'y':.025}),(.015,.04,.06,.98),(.10,.62,.76,.9),dp(22))
    app.chat_input=TextInput(hint_text='JARVIS ko message likhein...',multiline=False,font_size='13sp',foreground_color=WHITE,hint_text_color=MUTED,background_normal='',background_active='',background_color=(.02,.06,.08,1),cursor_color=CYAN,padding=[dp(8),dp(8)])
    def send_chat(*_):
        msg=app.chat_input.text.strip()
        if not msg:return
        app.chat_input.text=''; set_status('Aap: '+msg)
        try: app.process_command(msg)
        except Exception as e:set_status('Message process nahi hua: '+str(e))
    app.chat_input.bind(on_text_validate=send_chat); composer.add_widget(app.chat_input); composer.add_widget(button('➤',send_chat,17,CYAN,(.02,.15,.22,1))); root.add_widget(composer)
    # Preserve legacy calculator attributes expected by main.py.
    app.calc_panel=BoxLayout(orientation='vertical',size_hint_y=None,height=0,opacity=0,disabled=True)
    app.calc_question_label=lbl('',10); app.calc_answer_label=lbl('',12,CYAN,True); app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label)
    app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})(); app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]; app.root_layout=root
    return root
