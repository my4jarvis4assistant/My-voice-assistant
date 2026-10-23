from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.clock import Clock

class JarvisMainScreen(Screen):
    def __init__(self, **kwargs):
        super(JarvisMainScreen, self).__init__(**kwargs)
        
        # Main layout
        layout = FloatLayout()

        # Dark background (Exact professional dark theme matching reference)
        with layout.canvas.before:
            Color(0.06, 0.08, 0.11, 1)
            self.bg = Rectangle(size=(2000, 2000), pos=(0, 0))
        self.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Top Bar: "JARVIS", Green Dot & Settings Icon at Top-Right
        top_bar = FloatLayout(size_hint=(1, None), height='60dp', pos_hint={'top': 0.98, 'center_x': 0.5})
        
        # JARVIS Title
        title_lbl = Label(
            text="JARVIS", 
            font_size='24sp', 
            bold=True, 
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=('120dp', '40dp'),
            pos_hint={'top': 0.8, 'x': 0.05},
            halign='left', valign='middle'
        )
        top_bar.add_widget(title_lbl)

        # Active Green Dot beside title
        dot_layout = FloatLayout(size_hint=(None, None), size=('30dp', '30dp'), pos_hint={'top': 0.72, 'x': 0.35})
        with dot_layout.canvas:
            Color(0.1, 0.9, 0.4, 1)
            self.dot_ellipse = Ellipse(size=(12, 12), pos=(5, 5))
        top_bar.add_widget(dot_layout)

        # Settings Icon Button at Top-Right (Professional Placement)
        settings_btn = Button(
            text="⚙", 
            font_size='22sp',
            size_hint=(None, None), 
            size=('45dp', '45dp'),
            pos_hint={'top': 0.85, 'right': 0.95},
            background_color=(0, 0, 0, 0),
            color=(0.8, 0.8, 0.8, 1)
        )
        settings_btn.bind(on_release=self.open_settings)
        top_bar.add_widget(settings_btn)
        
        layout.add_widget(top_bar)

        # 2. Central Animated Blue Voice Circle (Exact reference match)
        voice_layout = FloatLayout(size_hint=(None, None), size=('240dp', '240dp'), pos_hint={'center_x': 0.5, 'center_y': 0.58})
        with voice_layout.canvas:
            # Outer glowing aura layers
            Color(0.1, 0.4, 0.6, 0.3)
            Ellipse(size=(240, 240), pos=(0, 0))
            Color(0.15, 0.5, 0.7, 0.5)
            Ellipse(size=(200, 200), pos=(20, 20))
            # Main central gradient/blue sphere
            Color(0.2, 0.6, 0.95, 1)
            self.main_sphere = Ellipse(size=(160, 160), pos=(40, 40))
        
        # "Listening..." text below the circle
        status_lbl = Label(
            text="Listening...", 
            font_size='16sp', 
            color=(0.7, 0.75, 0.85, 1),
            size_hint=(None, None),
            size=('200dp', '30dp'),
            pos_hint={'center_x': 0.5, 'y': 0.35}
        )
        layout.add_widget(status_lbl)
        layout.add_widget(voice_layout)

        # 3. Bottom Input Bar & Send Button
        bottom_bar = FloatLayout(size_hint=(0.9, None), height='55dp', pos_hint={'bottom': 0.08, 'center_x': 0.5})
        
        with bottom_bar.canvas.before:
            Color(0.12, 0.16, 0.22, 1)
            self.input_bg = RoundedRectangle(size=(340, 50), pos=(0, 0), radius=[25])
        
        self.text_input = TextInput(
            hint_text='Message...', 
            multiline=False,
            background_color=(0, 0, 0, 0),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            size_hint=(0.8, None),
            height='45dp',
            pos_hint={'center_y': 0.5, 'x': 0.03},
            padding=[15, 12, 0, 0]
        )
        bottom_bar.add_widget(self.text_input)

        send_btn = Button(
            text="➤",
            font_size='18sp',
            size_hint=(None, None),
            size=('45dp', '45dp'),
            pos_hint={'center_y': 0.5, 'right': 0.98},
            background_color=(0, 0, 0, 0),
            color=(0.3, 0.7, 1, 1)
        )
        send_btn.bind(on_release=self.send_message)
        bottom_bar.add_widget(send_btn)

        layout.add_widget(bottom_bar)
        
        # Footer branding label
        brand_lbl = Label(
            text="JARVIS · PERSONAL ASSISTANT",
            font_size='10sp',
            color=(0.4, 0.45, 0.55, 1),
            size_hint=(None, None),
            size=('200dp', '20dp'),
            pos_hint={'center_x': 0.5, 'bottom': 0.02}
        )
        layout.add_widget(brand_lbl)

        self.add_widget(layout)

    def _update_bg(self, instance, value):
        self.bg.size = instance.size
        self.bg.pos = instance.pos

    def open_settings(self, instance):
        self.manager.current = 'settings_screen'

    def send_message(self, instance):
        txt = self.text_input.text
        if txt.strip():
            print(f"Message sent: {txt}")
            self.text_input.text = ""

class JarvisSettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(JarvisSettingsScreen, self).__init__(**kwargs)
        layout = FloatLayout()
        
        with layout.canvas.before:
            Color(0.06, 0.08, 0.11, 1)
            self.bg = Rectangle(size=(2000, 2000), pos=(0, 0))
        self.bind(size=self._update_bg, pos=self._update_bg)

        # Close Settings Button (Top-Left)
        close_btn = Button(
            text="< Close", 
            size_hint=(None, None), 
            size=('90dp', '35dp'), 
            pos_hint={'top': 0.95, 'x': 0.05},
            background_color=(0.15, 0.2, 0.28, 1),
            color=(1, 1, 1, 1)
        )
        close_btn.bind(on_release=self.go_back)
        layout.add_widget(close_btn)

        # Settings Header Title
        settings_title = Label(
            text="JARVIS Settings", 
            font_size='20sp', 
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=('200dp', '40dp'),
            pos_hint={'top': 0.95, 'center_x': 0.5}
        )
        layout.add_widget(settings_title)

        # Voice Selection Section Box
        voice_lbl = Label(
            text="Voice Selection\n(Current: Male Alpha 1)", 
            font_size='14sp', 
            color=(0.8, 0.85, 0.9, 1),
            size_hint=(None, None),
            size=('300dp', '80dp'),
            pos_hint={'top': 0.83, 'center_x': 0.5},
            halign='center'
        )
        layout.add_widget(voice_lbl)

        # History Section Box
        history_lbl = Label(
            text="History:\nSecure Interaction Log, Advanced Data Privacy", 
            font_size='13sp', 
            color=(0.7, 0.75, 0.8, 1),
            size_hint=(None, None),
            size=('300dp', '80dp'),
            pos_hint={'top': 0.65, 'center_x': 0.5},
            halign='center'
        )
        layout.add_widget(history_lbl)

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
