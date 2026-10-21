from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp

def build_jarvis_ui(app):
    root = FloatLayout()

    # 1. Background (Deep obsidian black with subtle sci-fi tones)
    with root.canvas.before:
        Color(0.02, 0.04, 0.07, 1)
        app._background_rect = RoundedRectangle(pos=root.pos, size=root.size, radius=[0])
    root.bind(pos=app._update_background, size=app._update_background)

    # ========================================================
    # TOP HEADER SECTION (Alex AI + Online Indicator + Settings)
    # ========================================================
    header_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(60),
        pos_hint={'top': 1, 'center_x': 0.5},
        padding=[dp(20), dp(10), dp(20), dp(10)]
    )

    # Title & Online status
    title_layout = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_x=0.8)
    title_label = Label(
        text="Alex AI",
        font_size='22sp',
        bold=True,
        color=(0.1, 0.8, 1, 1),
        halign='left',
        valign='middle'
    )
    title_label.bind(size=title_label.setter('text_size'))
    title_layout.add_widget(title_label)

    # Online Dot indicator
    online_dot = Widget(size_hint=(None, None), size=dp(12), pos_hint={'center_y': 0.5})
    with online_dot.canvas.before:
        Color(0, 1, 0.4, 1)
        Ellipse(pos=online_dot.pos, size=online_dot.size)
    title_layout.add_widget(online_dot)
    header_layout.add_widget(title_layout)

    # Top Right Settings Button (Triggers Voice/Settings Panel)
    settings_btn = Button(
        text="⚙",
        font_size='22sp',
        size_hint=(None, None),
        size=dp(45),
        pos_hint={'center_y': 0.5},
        background_color=(0, 0, 0, 0),
        color=(0.1, 0.8, 1, 1)
    )
    
    # Status label for voice recognition feedback
    app.status_label = Label(
        text="Initializing Alex AI...",
        font_size='12sp',
        color=(0.7, 0.85, 1, 0.8),
        size_hint=(1, None),
        height=dp(25),
        pos_hint={'top': 0.93, 'center_x': 0.5},
        halign='center'
    )

    # ========================================================
    # MAIN CENTER AREA (Visualizer + Chat Bubbles)
    # ========================================================
    center_area = FloatLayout(
        size_hint=(1, None),
        height=dp(380),
        pos_hint={'center_x': 0.5, 'center_y': 0.52}
    )

    # Holographic Voice Visualizer (Simulated glowing center ring)
    visualizer_widget = Widget(
        size_hint=(None, None),
        size=dp(180),
        pos_hint={'center_x': 0.35, 'center_y': 0.55}
    )
    with visualizer_widget.canvas.before:
        Color(0.1, 0.6, 0.9, 0.3)
        Line(circle=(90, 90, 80), width=1.5)
        Color(1, 0.8, 0.2, 0.4)
        Line(circle=(90, 90, 60), width=1)
        Color(0, 0.9, 1, 0.8)
        Line(circle=(90, 90, 40), width=2)
    center_area.add_widget(visualizer_widget)

    # Chat Bubbles (User & AI interactions)
    chat_box = BoxLayout(
        orientation='vertical',
        spacing=dp(10),
        size_hint=(0.85, None),
        height=dp(200),
        pos_hint={'center_x': 0.5, 'center_y': 0.5}
    )

    user_bubble = Label(
        text="How can you assist today, Alex?",
        font_size='13sp',
        color=(1, 1, 1, 1),
        size_hint=(1, None),
        height=dp(35),
        halign='left',
        valign='middle'
    )
    user_bubble.bind(size=user_bubble.setter('text_size'))
    
    ai_bubble = Label(
        text="Accessing Neural Core. Systems nominal, Commander. Ready for input.",
        font_size='13sp',
        color=(0.7, 0.95, 1, 1),
        size_hint=(1, None),
        height=dp(45),
        halign='left',
        valign='middle'
    )
    ai_bubble.bind(size=ai_bubble.setter('text_size'))

    chat_box.add_widget(user_bubble)
    chat_box.add_widget(ai_bubble)
    center_area.add_widget(chat_box)

    # ========================================================
    # RIGHT SIDE PANEL (Voice Selection & Settings Menu)
    # ========================================================
    settings_panel = FloatLayout(
        size_hint=(None, None),
        size=(dp(220), dp(320)),
        pos_hint={'right': 0.96, 'center_y': 0.55},
        opacity=1 # Set to 0 if you want to hide it by default and toggle with settings button
    )
    with settings_panel.canvas.before:
        Color(0.04, 0.08, 0.15, 0.95)
        RoundedRectangle(pos=settings_panel.pos, size=settings_panel.size, radius=[dp(12)])
        Color(0.1, 0.7, 1, 0.4)
        Line(rounded_rectangle=(settings_panel.x, settings_panel.y, settings_panel.width, settings_panel.height, dp(12)), width=1.2)

    panel_content = BoxLayout(
        orientation='vertical',
        padding=dp(12),
        spacing=dp(8),
        size_hint=(1, 1)
    )

    panel_title = Label(
        text="Voice Selection",
        font_size='14sp',
        bold=True,
        color=(0.1, 0.8, 1, 1),
        size_hint=(1, None),
        height=dp(25)
    )
    panel_content.add_widget(panel_title)

    # 5-10 AI Voices Options
    voices = [
        "Alate Carolina", "Tioteerabuh", "Wardsolstae", 
        "Suienger fight", "Mginall shceratioe", "Etseoabrck"
    ]
    
    voices_scroll = ScrollView(size_hint=(1, None), height=dp(140))
    voices_layout = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
    voices_layout.bind(minimum_height=voices_layout.setter('height'))

    for voice in voices:
        v_btn = Button(
            text=f"🎙  {voice}",
            font_size='11sp',
            size_hint=(1, None),
            height=dp(30),
            background_color=(0, 0, 0, 0),
            color=(0.8, 0.9, 1, 1),
            halign='left'
        )
        v_btn.bind(size=v_btn.setter('text_size'))
        voices_layout.add_widget(v_btn)
    
    voices_scroll.add_widget(voices_layout)
    panel_content.add_widget(voices_scroll)

    # Wake-word & Theme section inside panel
    wake_label = Label(text="Wake-word: Alex", font_size='11sp', color=(0.6, 0.7, 0.8, 1), size_hint=(1, None), height=dp(20), halign='left')
    wake_label.bind(size=wake_label.setter('text_size'))
    panel_content.add_widget(wake_label)

    theme_label = Label(text="Theme: Cyberpunk Dark", font_size='11sp', color=(0.6, 0.7, 0.8, 1), size_hint=(1, None), height=dp(20), halign='left')
    theme_label.bind(size=theme_label.setter('text_size'))
    panel_content.add_widget(theme_label)

    settings_panel.add_widget(panel_content)

    # Toggle settings panel visibility when settings button is clicked
    def toggle_settings(instance):
        settings_panel.opacity = 0 if settings_panel.opacity == 1 else 1
    settings_btn.bind(on_press=toggle_settings)
    header_layout.add_widget(settings_btn)

    # ========================================================
    # QUICK ACTION BUTTONS BAR (Alarms, Reminders, Weather, Messages)
    # ========================================================
    quick_actions = GridLayout(
        cols=4,
        spacing=dp(10),
        size_hint=(0.9, None),
        height=dp(70),
        pos_hint={'center_x': 0.5, 'y': 0.18}
    )

    actions_data = [
        ("⏰\nAlarms", lambda x: app.set_status("Alarms menu selected")),
        ("📅\nReminders", lambda x: app.open_calendar()),
        ("⛅\nWeather", lambda x: app.google_web_search("weather forecast")),
        ("💬\nMessages", lambda x: app.open_messages())
    ]

    for title, callback in actions_data:
        btn = Button(
            text=title,
            font_size='11sp',
            halign='center',
            valign='middle',
            background_color=(0, 0, 0, 0),
            color=(0.8, 0.95, 1, 1)
        )
        btn.bind(size=btn.setter('text_size'))
        btn.bind(on_press=callback)
        
        # Add glassmorphism background to action buttons
        with btn.canvas.before:
            Color(0.06, 0.12, 0.22, 0.8)
            RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])
            Color(0.1, 0.6, 0.9, 0.3)
            Line(rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, dp(10)), width=1)
        
        quick_actions.add_widget(btn)

    # ========================================================
    # BOTTOM BAR & BIOMETRIC FINGERPRINT SCANNER
    # ========================================================
    bottom_bar = BoxLayout(
        orientation='horizontal',
        size_hint=(0.95, None),
        height=dp(65),
        pos_hint={'center_x': 0.5, 'y': 0.02},
        padding=[dp(10), dp(5), dp(10), dp(5)],
        spacing=dp(15)
    )
    with bottom_bar.canvas.before:
        Color(0.04, 0.08, 0.15, 0.95)
        RoundedRectangle(pos=bottom_bar.pos, size=bottom_bar.size, radius=[dp(12)])
        Color(0.1, 0.6, 0.9, 0.4)
        Line(rounded_rectangle=(bottom_bar.x, bottom_bar.y, bottom_bar.width, bottom_bar.height, dp(12)), width=1)

    history_btn = Button(
        text="History",
        font_size='12sp',
        size_hint=(0.3, 1),
        background_color=(0, 0, 0, 0),
        color=(0.7, 0.85, 1, 1)
    )
    history_btn.bind(on_press=lambda x: app.set_status("Voice history logs active"))

    # Glowing Biometric Fingerprint Center Button
    fingerprint_btn = Button(
        text="🔒",
        font_size='20sp',
        size_hint=(None, None),
        size=dp(50),
        pos_hint={'center_y': 0.5},
        background_color=(0, 0, 0, 0),
        color=(0, 0.9, 1, 1)
    )
    fingerprint_btn.bind(on_press=lambda x: app.speak("Biometric verification successful. Alex AI is secure."))

    settings_shortcut_btn = Button(
        text="Settings",
        font_size='12sp',
        size_hint=(0.3, 1),
        background_color=(0, 0, 0, 0),
        color=(0.7, 0.85, 1, 1)
    )
    settings_shortcut_btn.bind(on_press=toggle_settings)

    bottom_bar.add_widget(history_btn)
    bottom_bar.add_widget(fingerprint_btn)
    bottom_bar.add_widget(settings_shortcut_btn)

    # Adding all components to main root layout
    root.add_widget(header_layout)
    root.add_widget(app.status_label)
    root.add_widget(center_area)
    root.add_widget(settings_panel)
    root.add_widget(quick_actions)
    root.add_widget(bottom_bar)

    return root
