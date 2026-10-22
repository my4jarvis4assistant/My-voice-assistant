"""JARVIS v0.31 responsive reference-style UI for portrait Android screens."""
import math
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView

BG=(0.008,0.018,0.032,1); CYAN=(0.20,0.88,1,1); GOLD=(0.94,0.79,0.53,1); MUTED=(0.78,0.88,0.94,1)
def label(text,size=14,color=MUTED,bold=False,halign='left'):
    w=Label(text=text,font_size=f'{size}sp',color=color,bold=bold,halign=halign,valign='middle')
    w.bind(size=lambda a,v:setattr(a,'text_size',(max(0,v[0]-dp(5)),v[1])))
    return w
def style_panel(w,bg=(.018,.05,.075,.96),border=(.12,.67,.82,.8),r=dp(16)):
    with w.canvas.before:
        Color(*bg); w._bg=RoundedRectangle(pos=w.pos,size=w.size,radius=[r])
        Color(*border); w._line=Line(rounded_rectangle=(w.x,w.y,w.width,w.height,r),width=1.1)
    def upd(*_):
        w._bg.pos=w.pos; w._bg.size=w.size; w._line.rounded_rectangle=(w.x,w.y,w.width,w.height,r)
    w.bind(pos=upd,size=upd); return w
def btn(text,cb,size=13,color=MUTED):
    b=Button(text=text,font_size=f'{size}sp',color=color,background_normal='',background_down='',background_color=(.025,.105,.15,.98),halign='center',valign='middle')
    b.bind(on_release=lambda *_:cb()); return b
class JarvisCore(Widget):
    """Fixed rings with a non-rotating voice-reactive breathing/pulse effect."""
    def __init__(self,**kw):
        super().__init__(**kw); self.phase=0.; self.listening=False; self.speaking=False
        self.bind(pos=self.draw,size=self.draw); self.draw(); Clock.schedule_interval(self.tick,1/20)
    def tick(self,dt): self.phase+=dt*(3.2 if self.listening or self.speaking else .8); self.draw()
    def draw(self,*_):
        self.canvas.clear(); cx,cy=self.center; r=max(dp(12),min(self.width,self.height)*.32)
        amp=.07 if self.listening or self.speaking else .022; pulse=1+amp*math.sin(self.phase*2)
        with self.canvas:
            Color(.0,.55,.95,.06+.04*(.5+.5*math.sin(self.phase*2))); Ellipse(pos=(cx-r*1.5,cy-r*1.5),size=(r*3,r*3))
            Color(.015,.06,.11,1); Ellipse(pos=(cx-r,cy-r),size=(r*2,r*2))
            for rr,co,wi in [(1.25,(.13,.75,1,.65),1),(1.08,(.2,.86,1,.9),1.6),(.91,(.28,.55,1,.75),1),(.72,(.15,.84,1,.9),1.4),(.48,(.22,.8,1,.85),1.2)]:
                Color(co[0],co[1],co[2],co[3]*(.75+.25*(.5+.5*math.sin(self.phase*2))))
                Line(circle=(cx,cy,r*rr*(pulse if rr>1 else 1)),width=dp(wi))
            # Voice waveform bars gently change height only while listening/speaking.
            for i in range(13):
                x=cx+(i-6)*r*.105
                base=(.18+.42*abs(math.sin(i*1.73+self.phase*(2.5 if self.listening or self.speaking else .35))))
                hh=r*base*(1.3 if self.listening or self.speaking else .8)
                Color(.20,.88,1,.95); Line(points=[x,cy-hh,x,cy+hh],width=dp(2.2),cap='round')
            Color(.72,.93,1,1); Ellipse(pos=(cx-dp(3),cy-dp(3)),size=(dp(6),dp(6)))
class FingerprintButton(Button):
    def __init__(self,**kw):
        super().__init__(**kw); self.text=''; self.background_normal=''; self.background_down=''; self.background_color=(0,0,0,0); self.bind(pos=self.draw,size=self.draw,state=self.draw); self.draw()
    def draw(self,*_):
        self.canvas.clear(); cx,cy=self.center; r=min(self.width,self.height)*.39
        with self.canvas:
            Color(.02,.5,.8,.2); Ellipse(pos=(cx-r*1.3,cy-r*1.3),size=(r*2.6,r*2.6))
            Color(.38,.73,.84,1); Line(circle=(cx,cy,r*1.12),width=dp(1.5))
            Color(.025,.075,.11,1); Ellipse(pos=(cx-r,cy-r),size=(2*r,2*r))
            Color(.18,.86,1,1); Line(circle=(cx,cy,r*.88),width=dp(1.5))
            for k in range(5):
                w=r*(.22+k*.12); pts=[]
                for j in range(33):
                    t=j/32; x=cx+w*math.sin(math.pi*t); y=cy+r*(.55-t*1.12)
                    pts.extend((x,y))
                Line(points=pts,width=dp(1.25))
def build_jarvis_ui(app):
    root=FloatLayout()
    with root.canvas.before:
        Color(*BG); root._bg=RoundedRectangle(pos=root.pos,size=root.size,radius=[dp(18)])
    root.bind(pos=lambda w,_:setattr(w._bg,'pos',w.pos),size=lambda w,_:setattr(w._bg,'size',w.size))
    # Fixed-height bottom rails; upper area flexes on Redmi 8 portrait dimensions.
    header=BoxLayout(orientation='horizontal',spacing=dp(8),padding=[dp(10),dp(3),dp(8),dp(3)],size_hint=(1,None),height=dp(54),pos_hint={'x':0,'top':1})
    header.add_widget(label('JARVIS',23,CYAN,True)); dot=label('●',16,(.15,1,.55,1),True); dot.size_hint_x=None; dot.width=dp(24); header.add_widget(dot); header.add_widget(Widget())
    gear=btn('⚙',lambda:getattr(app,'open_settings',lambda:None)(),22,GOLD); gear.size_hint=(None,1); gear.width=dp(48); header.add_widget(gear); root.add_widget(header)
    # Main stage leaves space for controls and bottom chat.
    stage=FloatLayout(size_hint=(1,None),height=dp(530),pos_hint={'x':0,'top':1},y=-dp(58))
    # Chat-like left lane and core, matching the reference composition.
    status=label('VOICE INTERFACE  /  PERSONAL AI',12,CYAN,True); status.size_hint=(.96,None); status.height=dp(30); status.pos_hint={'x':.02,'top':1}; stage.add_widget(status); app.status_label=label('JARVIS ready hai.',13,CYAN,True); app.status_label.size_hint=(.96,None); app.status_label.height=dp(30); app.status_label.pos_hint={'x':.02,'top':.92}; stage.add_widget(app.status_label)
    core=JarvisCore(size_hint=(.62,None),height=dp(260),pos_hint={'x':.02,'top':.83}); stage.add_widget(core); app.core_widget=core
    chatlog=BoxLayout(orientation='vertical',spacing=dp(5),size_hint=(.60,None),height=dp(120),pos_hint={'x':.02,'y':.05})
    for t in ('◉  Hello! Main JARVIS hoon.','◉  Aap voice ya message se baat kar sakte hain.'):
        row=style_panel(BoxLayout(padding=dp(8))); row.add_widget(label(t,11,MUTED)); chatlog.add_widget(row)
    stage.add_widget(chatlog)
    # Voice drawer floats on right, rather than stealing a whole column from the core.
    drawer=style_panel(BoxLayout(orientation='vertical',spacing=dp(5),padding=dp(8),size_hint=(.43,.79),pos_hint={'right':.99,'top':.91}),(.012,.035,.052,.98),(.28,.68,.79,.9),dp(16))
    dh=BoxLayout(size_hint_y=None,height=dp(32)); dh.add_widget(label('Voice Selection',13,GOLD,True)); dh.add_widget(btn('•••',lambda:toggle_drawer(),18,GOLD)); drawer.add_widget(dh)
    sc=ScrollView(do_scroll_x=False); vl=GridLayout(cols=1,spacing=dp(5),size_hint_y=None); vl.bind(minimum_height=vl.setter('height'))
    for v in ('System default','English (India)','English (US)','Hindi (India)'):
        vl.add_widget(btn('♙  '+v,lambda choice=v:select_voice(choice),12))
    sc.add_widget(vl); drawer.add_widget(sc); drawer.add_widget(label('Tap a voice to select',10,MUTED)); drawer.add_widget(label('Wake-word',12,GOLD,True))
    wake=TextInput(text='JARVIS',multiline=False,size_hint_y=None,height=dp(34),font_size='14sp',foreground_color=MUTED,background_normal='',background_active='',background_color=(.025,.07,.09,1),cursor_color=CYAN); wake.bind(text=lambda _,v:setattr(app,'wake_word',v.strip() or 'JARVIS')); drawer.add_widget(wake)
    drawer.add_widget(btn('Theme  →',lambda:set_status('Theme: Cyan / Gold'),14,GOLD)); stage.add_widget(drawer); drawer.opacity=0; drawer.disabled=True
    def set_status(s):
        try: app.set_status(s)
        except Exception: app.status_label.text=s
    def select_voice(v):
        app.selected_voice=v; set_status('Voice selected: '+v)
        # Best-effort apply language to existing Android TTS object.
        try:
            from jnius import autoclass
            Locale=autoclass('java.util.Locale')
            loc={'English (India)':Locale('en','IN'),'English (US)':Locale.US,'Hindi (India)':Locale('hi','IN')}.get(v)
            if getattr(app,'tts',None) and loc: app.tts.setLanguage(loc)
        except Exception: pass
    def toggle_drawer(*_):
        opened=drawer.opacity==0
        drawer.opacity=1 if opened else 0; drawer.disabled=not opened
        core.pos_hint={'x':.0 if opened else .02,'top':.78 if opened else .83}
        core.size_hint_x=.53 if opened else .62
        set_status('Voice Selection khula' if opened else 'Voice Selection band')
    app.toggle_voice_selection=toggle_drawer
    root.add_widget(stage)
    # Voice Selection trigger near upper right under header.
    vt=btn('VOICE SELECTION  •••',toggle_drawer,12,GOLD); vt.size_hint=(.44,None); vt.height=dp(34); vt.pos_hint={'right':.98,'top':.615}; root.add_widget(vt)
    # Quick actions five columns.
    quick=style_panel(BoxLayout(orientation='horizontal',spacing=dp(3),padding=dp(5),size_hint=(.95,None),height=dp(65),pos_hint={'center_x':.5,'y':.215}),(.02,.075,.105,.98),(.16,.78,.9,.95),dp(17))
    def qaction(text,cmd,method=None):
        def go():
            try:
                if method and hasattr(app,method): getattr(app,method)(); return
            except Exception: pass
            set_status('Boliye: '+cmd)
            try:
                if getattr(app,'tts',None): app.tts.speak('Kripya '+cmd+' boliye.',0,None)
            except Exception: pass
        quick.add_widget(btn(text,go,10,MUTED))
    qaction('◷\nAlarm','alarm lagao'); qaction('▦\nReminder','reminder banao'); qaction('☼\nWeather','weather batao'); qaction('▤\nMessage','messages kholo','open_messages'); qaction('☎\nCall','phone kholo','open_phone'); root.add_widget(quick)
    footer=BoxLayout(orientation='horizontal',spacing=dp(8),padding=[dp(12),dp(3),dp(12),dp(3)],size_hint=(1,None),height=dp(64),pos_hint={'x':0,'y':.125})
    footer.add_widget(btn('History',lambda:set_status('History'),12,GOLD)); fp=FingerprintButton(size_hint_x=1); fp.bind(on_release=lambda *_:start_listening()); footer.add_widget(fp); footer.add_widget(btn('Settings',lambda:getattr(app,'open_settings',lambda:None)(),12,GOLD)); root.add_widget(footer)
    def start_listening():
        core.listening=True; Clock.schedule_once(lambda _dt:setattr(core,'listening',False),5)
        try: app.listen()
        except Exception: set_status('Listening...')
    # Bottom message composer.
    composer=style_panel(BoxLayout(orientation='horizontal',spacing=dp(5),padding=dp(5),size_hint=(.96,None),height=dp(48),pos_hint={'center_x':.5,'y':.025}),(.015,.04,.06,.98),(.10,.62,.76,.9),dp(22))
    app.chat_input=TextInput(hint_text='JARVIS ko message likhein...',multiline=False,font_size='13sp',foreground_color=(.93,.97,1,1),hint_text_color=(.5,.66,.74,1),background_normal='',background_active='',background_color=(.02,.06,.08,1),cursor_color=CYAN)
    def send_chat(*_):
        msg=app.chat_input.text.strip()
        if not msg:return
        app.chat_input.text=''; set_status('Aap: '+msg)
        try: app.process_command(msg)
        except Exception as e:set_status('Message process nahi hua: '+str(e))
    app.chat_input.bind(on_text_validate=send_chat); composer.add_widget(app.chat_input); composer.add_widget(btn('➤',send_chat,18,CYAN)); root.add_widget(composer)
    # Compatibility attributes for existing calculator/command logic.
    app.calc_panel=BoxLayout(orientation='vertical',size_hint_y=None,height=0,opacity=0,disabled=True); app.calc_question_label=label('',10); app.calc_answer_label=label('',12,CYAN,True); app.calc_panel.add_widget(app.calc_question_label); app.calc_panel.add_widget(app.calc_answer_label); app.calc_display=type('VoiceOnlyDisplay',(),{'text':''})(); app.calc_angle_mode='DEG'; app.calc_history=[]; app.calc_buttons=[]
    app.root_layout=root
    return root
