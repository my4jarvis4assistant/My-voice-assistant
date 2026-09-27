from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method
from datetime import datetime


class MainThreadRunnable(PythonJavaClass):
    __javainterfaces__ = ['java/lang/Runnable']
    __javacontext__ = 'app'

    def __init__(self, function):
        super().__init__()
        self.function = function

    @java_method('()V')
    def run(self):
        self.function()


class RecognitionListener(PythonJavaClass):
    __javainterfaces__ = ['android/speech/RecognitionListener']
    __javacontext__ = 'app'

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method('(Landroid/os/Bundle;)V')
    def onReadyForSpeech(self, params):
        self.app.label.text = "🎤 Bolna shuru kijiye..."

    @java_method('()V')
    def onBeginningOfSpeech(self):
        self.app.label.text = "👂 Sun raha hoon..."

    @java_method('(F)V')
    def onRmsChanged(self, rmsdB):
        pass

    @java_method('([B)V')
    def onBufferReceived(self, buffer):
        pass

    @java_method('()V')
    def onEndOfSpeech(self):
        self.app.label.text = "🧠 Samajh raha hoon..."

    @java_method('(ILjava/lang/String;)V')
    def onError(self, error):
        self.app.label.text = (
            "❌ Speech Error: " + str(error)
        )

        if not self.app.external_action:
            Clock.schedule_once(
                self.app.listen_again,
                1
            )

    @java_method('(Landroid/os/Bundle;)V')
    def onResults(self, results):
        matches = results.getStringArrayList(
            "results_recognition"
        )

        if matches and matches.size() > 0:
            text = matches.get(0)

            self.app.label.text = (
                "Aapne kaha:\n" + text
            )

            self.app.process_command(text)

        else:
            self.app.label.text = (
                "Kuch samajh nahi aaya."
            )

            if not self.app.external_action:
                Clock.schedule_once(
                    self.app.listen_again,
                    1
                )


class VoiceAssistant(App):

    def build(self):

        self.label = Label(
            text="🤖 JARVIS\n\nStarting...",
            font_size="22sp"
        )

        self.external_action = False

        self.PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )

        self.SpeechRecognizer = autoclass(
            "android.speech.SpeechRecognizer"
        )

        self.RecognizerIntent = autoclass(
            "android.content.Intent"
        )

        self.TextToSpeech = autoclass(
            "android.speech.tts.TextToSpeech"
        )

        self.Uri = autoclass(
            "android.net.Uri"
        )

        self.Locale = autoclass(
            "java.util.Locale"
        )

        self.activity = (
            self.PythonActivity.mActivity
        )

        self.tts = self.TextToSpeech(
            self.activity,
            None
        )

        self.tts.setLanguage(
            self.Locale.US
        )

        self.listener = RecognitionListener(self)

        self.setup_runnable = MainThreadRunnable(
            self.setup_speech
        )

        Clock.schedule_once(
            self.start_setup,
            0.5
        )

        return self.label

    def start_setup(self, dt):

        try:
            self.activity.runOnUiThread(
                self.setup_runnable
            )

        except Exception as e:
            self.label.text = (
                "Thread Error:\n" + str(e)
            )

    def setup_speech(self):

        try:

            self.recognizer = (
                self.SpeechRecognizer
                .createSpeechRecognizer(
                    self.activity
                )
            )

            self.recognizer.setRecognitionListener(
                self.listener
            )

            self.intent = self.RecognizerIntent(
                "android.speech.action.RECOGNIZE_SPEECH"
            )

            self.intent.putExtra(
                "android.speech.extra.LANGUAGE_MODEL",
                "free_form"
            )

            self.intent.putExtra(
                "android.speech.extra.LANGUAGE",
                "hi-IN"
            )

            self.label.text = (
                "🤖 JARVIS\n\n"
                "2 second baad boliye..."
            )

            self.listen_runnable = MainThreadRunnable(
                self.start_listening
            )

            Clock.schedule_once(
                self.start_listening_request,
                2
            )

        except Exception as e:

            self.label.text = (
                "Speech Setup Error:\n"
                + str(e)
            )

    def start_listening_request(self, dt):

        if self.external_action:
            return

        try:
            self.activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Listening Thread Error:\n"
                + str(e)
            )

    def start_listening(self):

        if self.external_action:
            return

        try:

            self.label.text = (
                "🎤 Bolna shuru kijiye..."
            )

            self.recognizer.startListening(
                self.intent
            )

        except Exception as e:

            self.label.text = (
                "Start Error:\n" + str(e)
            )

    def listen_again(self, dt):

        if self.external_action:
            return

        try:

            self.activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Restart Error:\n" + str(e)
            )

    def stop_listening(self):

        try:
            self.recognizer.stopListening()
        except Exception:
            pass

        try:
            self.recognizer.cancel()
        except Exception:
            pass

    def open_youtube(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "📺 YouTube khol raha hoon..."
            )

            uri = self.Uri.parse(
                "https://www.youtube.com/"
            )

            intent = self.RecognizerIntent(
                "android.intent.action.VIEW"
            )

            intent.setData(uri)

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "YouTube Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_calculator(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🧮 Calculator khol raha hoon..."
            )

            packages = [
                "com.google.android.calculator",
                "com.miui.calculator",
                "com.android.calculator2"
            ]

            pm = self.activity.getPackageManager()

            for package_name in packages:

                try:

                    intent = (
                        pm.getLaunchIntentForPackage(
                            package_name
                        )
                    )

                    if intent:
                        self.activity.startActivity(
                            intent
                        )
                        return

                except Exception:
                    pass

            self.external_action = False

            self.label.text = (
                "Calculator nahi mila."
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Calculator Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_camera(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "📷 Camera khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.media.action.IMAGE_CAPTURE"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Camera Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_chrome(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🌐 Chrome khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = pm.getLaunchIntentForPackage(
                "com.android.chrome"
            )

            if intent:

                self.activity.startActivity(
                    intent
                )

            else:

                self.external_action = False

                self.label.text = (
                    "Chrome nahi mila."
                )

                Clock.schedule_once(
                    self.listen_again,
                    2
                )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Chrome Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_whatsapp(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "💬 WhatsApp khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = pm.getLaunchIntentForPackage(
                "com.whatsapp"
            )

            if intent:

                self.activity.startActivity(
                    intent
                )

            else:

                self.external_action = False

                self.label.text = (
                    "WhatsApp nahi mila."
                )

                Clock.schedule_once(
                    self.listen_again,
                    2
                )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "WhatsApp Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "⚙️ Settings khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_wifi_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "📶 Wi-Fi Settings khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.settings.WIFI_SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Wi-Fi Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_bluetooth_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🔵 Bluetooth Settings khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.settings.BLUETOOTH_SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Bluetooth Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_display_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🖥️ Display Settings khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.settings.DISPLAY_SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Display Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def open_battery_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🔋 Battery Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            # First try: Battery Settings
            intent = self.RecognizerIntent(
                "android.settings.BATTERY_SETTINGS"
            )

            if intent.resolveActivity(pm):
                self.activity.startActivity(intent)
                return

            # Second try: Power Usage Summary
            intent = self.RecognizerIntent(
                "android.intent.action.POWER_USAGE_SUMMARY"
            )

            if intent.resolveActivity(pm):
                self.activity.startActivity(intent)
                return

            # Final fallback: Main Settings
            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(intent)

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Battery Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🔋 Battery Settings khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.settings.BATTERY_SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Battery Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    def process_command(self, text):

        command = text.lower().strip()

        if "hello jarvis" in command:

            self.speak(
                "Hello! Main ready hoon."
            )

        elif (
            "tumhara naam kya hai" in command
            or "what is your name" in command
            or "your name" in command
        ):

            self.speak(
                "Mera naam JARVIS hai."
            )

        elif (
            "time kya hai" in command
            or "what time is it" in command
            or command == "time"
        ):

            current_time = datetime.now().strftime(
                "%I:%M %p"
            )

            self.speak(
                "Abhi time hai "
                + current_time
            )

        elif (
            "date kya hai" in command
            or "aaj ki date" in command
            or "what is the date" in command
            or "today's date" in command
            or "today date" in command
        ):

            today = datetime.now()

            day = today.strftime("%d")
            month = today.strftime("%B")
            year = today.strftime("%Y")

            self.speak(
                "Aaj "
                + day
                + " "
                + month
                + " "
                + year
                + " hai."
            )

        elif (
            "youtube kholo" in command
            or "youtube khol" in command
            or "youtube open karo" in command
            or "open youtube" in command
            or "youtube open" in command
            or command == "youtube"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "YouTube khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_youtube,
                2.5
            )

        elif (
            "calculator kholo" in command
            or "calculator khol" in command
            or "calculator open karo" in command
            or "open calculator" in command
            or "calculator open" in command
            or command == "calculator"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Calculator khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_calculator,
                2.5
            )

        elif (
            "camera kholo" in command
            or "camera khol" in command
            or "camera open karo" in command
            or "open camera" in command
            or "camera open" in command
            or command == "camera"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Camera khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_camera,
                2.5
            )

        elif (
            "chrome kholo" in command
            or "chrome khol" in command
            or "chrome open karo" in command
            or "open chrome" in command
            or "chrome open" in command
            or command == "chrome"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Chrome khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_chrome,
                2.5
            )

        elif (
            "whatsapp kholo" in command
            or "whatsapp khol" in command
            or "whatsapp open karo" in command
            or "open whatsapp" in command
            or "whatsapp open" in command
            or command == "whatsapp"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "WhatsApp khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_whatsapp,
                2.5
            )

        elif (
            "settings kholo" in command
            or "settings khol" in command
            or "settings open karo" in command
            or "open settings" in command
            or "settings open" in command
            or command == "settings"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_settings,
                2.5
            )

        elif (
            "wifi kholo" in command
            or "wifi khol" in command
            or "wifi settings kholo" in command
            or "wifi settings khol" in command
            or "wifi open karo" in command
            or "open wifi" in command
            or "open wifi settings" in command
            or "wi-fi kholo" in command
            or "wi-fi khol" in command
            or "wi-fi settings kholo" in command
            or "wi-fi settings khol" in command
            or command == "wifi"
            or command == "wi-fi"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Wi-Fi settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_wifi_settings,
                2.5
            )

        elif (
            "bluetooth kholo" in command
            or "bluetooth khol" in command
            or "bluetooth settings kholo" in command
            or "bluetooth settings khol" in command
            or "bluetooth open karo" in command
            or "open bluetooth" in command
            or "open bluetooth settings" in command
            or command == "bluetooth"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Bluetooth settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_bluetooth_settings,
                2.5
            )

        elif (
            "display kholo" in command
            or "display khol" in command
            or "display settings kholo" in command
            or "display settings khol" in command
            or "display open karo" in command
            or "open display" in command
            or "open display settings" in command
            or "screen settings kholo" in command
            or "screen settings khol" in command
            or "screen display kholo" in command
            or command == "display"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Display settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_display_settings,
                2.5
            )

        elif (
            "battery kholo" in command
            or "battery khol" in command
            or "battery settings kholo" in command
            or "battery settings khol" in command
            or "battery open karo" in command
            or "open battery" in command
            or "open battery settings" in command
            or command == "battery"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Battery settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_battery_settings,
                2.5
            )

        else:

            self.speak(
                "Maine suna: " + text
            )

    def speak(self, text, restart=True):

        try:

            self.label.text = (
                "🔊 JARVIS:\n" + text
            )

            self.tts.speak(
                text,
                self.TextToSpeech.QUEUE_FLUSH,
                None
            )

            if restart and not self.external_action:

                Clock.schedule_once(
                    self.listen_again,
                    3
                )

        except Exception as e:

            self.label.text = (
                "TTS Error:\n" + str(e)
            )


VoiceAssistant().run()
