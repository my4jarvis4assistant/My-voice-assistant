from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle
import math

class VoiceCircleWidget(FloatLayout):
    def __init__(self, **kwargs):
        super(VoiceCircleWidget, self).__init__(**kwargs)
        self.angle = 0
        # Animation tick for the voice circle effect
        Clock.schedule_interval(self.update_animation, 1.0 / 30.0)

    def update_animation(self, dt):
        self.angle = (self.angle + 5) % 360
        self.canvas.ask_update()

class JarvisMainScreen(Screen):
    def __init__(self, **kwargs):
        super(JarvisMainScreen, self).__init__(**kwargs)
        
        # Main layout using FloatLayout for absolute positioning & layering
        layout = FloatLayout()

        # 1. Background Color (Dark Theme)
        with layout.canvas.before:
            Color(0.05, 0.07, 0.1, 1)  # Dark futuristic background
            self.bg = Rectangle(size=(1000, 2000), pos=(0, 0))
        self.bind(size=self._update_bg, pos=self._update_bg)

        # 2. Top Bar: "JARVIS", Green Dot, Settings Icon
        top_bar = BoxLayout(size_hint=(1, None), height='50dp', pos_hint={'top': 0.98, 'center_x': 0.5}, padding=[20, 0])
        
        title_label = Label(text="JARVIS", font_size='22sp', bold=True, color=(1, 1, 1, 1), size_hint_x=None, width=100)
        
        # Green active indicator dot
        dot_layout = FloatLayout(size_hint_x=None, width=30)
        with dot_layout.canvas:
            Color(0.1, 0.9, 0.3, 1)
            self.dot = Ellipse(size=(12, 12), pos=(10, 18))
        
        top_bar.add_widget(title_label)
        top_bar.add_widget(dot_layout)
        
        # Spacer to push settings icon to the right
        top_bar.add_widget(Label(size_hint_x=1))

        settings_btn = Button(
            text="⚙", 
            font_size='20sp',
            size_hint=(None, None), 
            size=('45dp', '45dp'),
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1)
        )
        settings_btn.bind(on_release=self.open_settings)
        top_bar.add_widget(settings_btn)
        layout.add_widget(top_bar)

        # 3. Chat History Layer (Passing behind the central voice circle)
        chat_box = BoxLayout(orientation='vertical', size_hint=(0.85, 0.4), pos_hint={'top': 0.82, 'center_x': 0.5}, spacing=10)
        
        msg_1 = Label(text="User: hi", color=(0.7, 0.7, 0.7, 0.9), font_size='14sp', halign='left')
        msg_2 = Label(text="J.A.R.V.I.S: hlo btaiye kya Aapko mujh se Kuchh kaam hai", color=(0.8, 0.9, 1, 0.9), font_size='14sp', halign='left')
        msg_3 = Label(text="User: tum kya kya kar sakte ho", color=(0.7, 0.7, 0.7, 0.9), font_size='14sp', halign='left')
        msg_4 = Label(text="J.A.R.V.I.S: mein app open kar sakta hu, message bhej sakta hu etc.", color=(0.8, 0.9, 1, 0.9), font_size='14sp', halign='left')
        
        chat_box.add_widget(msg_1)
        chat_box.add_widget(msg_2)
        chat_box.add_widget(msg_3)
        chat_box.add_widget(msg_4)
        layout.add_widget(chat_box)

        # 4. Central Dynamic Voice Circle (Layered above chat background with depth effect)
        self.voice_circle = VoiceCircleWidget(size_hint=(None, None), size=('220dp', '220dp'), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        with self.voice_circle.canvas:
            Color(0.1, 0.6, 0.9, 0.4)
            self.outer_ring = Ellipse(size=(220, 220), pos=(0, 0))
            Color(0.2, 0.8, 1, 0.8)
            self.inner_circle = Ellipse(size=(160, 160), pos=(30, 30))
        layout.add_widget(self.voice_circle)

        # 5. Bottom Input Bar & Send Button
        bottom_bar = BoxLayout(size_hint=(0.9, None), height='50dp', pos_hint={'bottom': 0.08, 'center_x': 0.5}, spacing=10)
        
        self.text_input = TextInput(
            hint_text='Message...', 
            multiline=False,
            background_color=(0.15, 0.18, 0.25, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            padding=[15, 12, 15, 12]
        )
        bottom_bar.add_widget(self.text_input)

        send_btn = Button(
            text="➤",
            font_size='18sp',
            size_hint=(None, None),
            size=('50dp', '50dp'),
            background_color=(0.1, 0.5, 0.8, 1),
            color=(1, 1, 1, 1)
        )
        send_btn.bind(on_release=self.send_message)
        bottom_bar.add_widget(send_btn)

        layout.add_widget(bottom_bar)
        self.add_widget(layout)

    def _update_bg(self, instance, value):
        self.bg.size = instance.size
        self.bg.pos = instance.pos

    def open_settings(self, instance):
        print("Settings opened successfully!")
        self.manager.current = 'settings_screen'

    def send_message(self, instance):
        txt = self.text_input.text
        if txt.strip():
            print(f"Sending message: {txt}")
            self.text_input.text = ""

class JarvisSettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(JarvisSettingsScreen, self).__init__(**kwargs)
        layout = FloatLayout()
        
        with layout.canvas.before:
            Color(0.05, 0.07, 0.1, 1)
            self.bg = Rectangle(size=(1000, 2000), pos=(0, 0))
        self.bind(size=self._update_bg, pos=self._update_bg)

        # Settings Title & Close Button
        back_btn = Button(
            text="< Close Settings", 
            size_hint=(None, None), 
            size=('150dp', '40dp'), 
            pos_hint={'top': 0.93, 'left': 0.05},
            background_color=(0.2, 0.2, 0.3, 1),
            color=(1, 1, 1, 1)
        )
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)

        # Voice Options label inside settings
        lbl = Label(text="Voice Selection: Male Alpha 1 / Beta / Gamma", color=(1, 1, 1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.6})
        layout.add_widget(lbl)

        self.add_widget(layout)

    def _update_bg(self, instance, value):
        self.bg.size = instance.size
        self.bg.pos = instance.pos

    def go_back(self, instance):
        self.manager.current = 'main_screen'

class JarvisApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(JarvisMainScreen(name='main_screen'))
        sm.add_widget(JarvisSettingsScreen(name='settings_screen'))
        return sm

if __name__ == '__main__':
    JarvisApp().run()
