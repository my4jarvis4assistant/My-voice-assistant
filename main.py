from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

from jnius import autoclass
from jnius import PythonJavaClass
from jnius import java_method

from datetime import datetime


# =========================================================
# MAIN THREAD RUNNABLE
# =========================================================

class MainThreadRunnable(PythonJavaClass):

    __javainterfaces__ = [
        "java/lang/Runnable"
    ]

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method("()V")
    def run(self):
        self.callback()


# =========================================================
# SPEECH RECOGNITION LISTENER
# =========================================================

class RecognitionListener(PythonJavaClass):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):
        self.assistant.label.text = "🎤 Sun raha hoon..."

    @java_method("()V")
    def onBeginningOfSpeech(self):
        self.assistant.label.text = "🎤 Boliyega..."

    @java_method("(F)V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("()V")
    def onEndOfSpeech(self):
        self.assistant.label.text = "⏳ Samajh raha hoon..."

    @java_method("(I)V")
    def onError(self, error):
        if not self.assistant.external_action:
            Clock.schedule_once(
                self.assistant.listen_again,
                1
            )

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):
        try:
            matches = results.getStringArrayList(
                "results_recognition"
            )

            if matches and matches.size() > 0:
                command = str(matches.get(0))
                self.assistant.process_command(command)

        except Exception as e:
            self.assistant.label.text = (
                "Speech Error:\n" + str(e)
            )

    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, partialResults):
        pass

    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, eventType, params):
        pass


# =========================================================
# VOICE ASSISTANT
# =========================================================

class VoiceAssistant(App):

    def build(self):

        self.external_action = False

        self.activity = autoclass(
            "org.kivy.android.PythonActivity"
        ).mActivity

        self.RecognizerIntent = autoclass(
            "android.content.Intent"
        )

        self.SpeechRecognizer = autoclass(
            "android.speech.SpeechRecognizer"
        )

        self.TextToSpeech = autoclass(
            "android.speech.tts.TextToSpeech"
        )

        self.Locale = autoclass(
            "java.util.Locale"
        )

        self.label = Label(
            text="🤖 JARVIS\nStarting...",
            halign="center",
            valign="middle"
        )

        return self.label

    # =====================================================
    # START SETUP
    # =====================================================

    def on_start(self):
        Clock.schedule_once(
            self.start_setup,
            1
        )

    def start_setup(self, dt):

        try:
            self.setup_speech()

        except Exception as e:

            self.label.text = (
                "Setup Error:\n" + str(e)
            )

    # =====================================================
    # SPEECH SETUP
    # =====================================================

    def setup_speech(self):

        self.tts = self.TextToSpeech(
            self.activity,
            None
        )

        self.tts.setLanguage(
            self.Locale.US
        )

        self.listener = RecognitionListener(
            self
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

        self.speech = (
            self.SpeechRecognizer
            .createSpeechRecognizer(
                self.activity
            )
        )

        self.speech.setRecognitionListener(
            self.listener
        )

        self.label.text = (
            "🤖 JARVIS Ready\n"
            "Boliye..."
        )

        Clock.schedule_once(
            self.start_listening_request,
            1
        )

    # =====================================================
    # START LISTENING REQUEST
    # =====================================================

    def start_listening_request(self, dt):

        if self.external_action:
            return

        runnable = MainThreadRunnable(
            self.start_listening
        )

        self.activity.runOnUiThread(
            runnable
        )

    # =====================================================
    # START LISTENING
    # =====================================================

    def start_listening(self):

        try:

            if self.external_action:
                return

            self.speech.startListening(
                self.intent
            )

            self.label.text = (
                "🎤 Listening..."
            )

        except Exception as e:

            self.label.text = (
                "Listening Error:\n"
                + str(e)
            )

    # =====================================================
    # LISTEN AGAIN
    # =====================================================

    def listen_again(self, dt):

        if self.external_action:
            return

        self.start_listening_request(
            0
        )

    # =====================================================
    # STOP LISTENING
    # =====================================================

    def stop_listening(self):

        try:
            self.speech.stopListening()

        except Exception:
            pass

    # =====================================================
    # YOUTUBE
    # =====================================================

    def open_youtube(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "▶️ YouTube khol raha hoon..."
            )

            intent = self.RecognizerIntent(
                "android.intent.action.VIEW"
            )

            intent.setData(
                autoclass(
                    "android.net.Uri"
                ).parse(
                    "https://www.youtube.com"
                )
            )

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

    # =====================================================
    # CALCULATOR
    # =====================================================

    def open_calculator(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🧮 Calculator khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            packages = [
                "com.google.android.calculator",
                "com.android.calculator2",
                "com.miui.calculator"
            ]

            for package_name in packages:

                intent = pm.getLaunchIntentForPackage(
                    package_name
                )

                if intent is not None:

                    self.activity.startActivity(
                        intent
                    )

                    return

            intent = self.RecognizerIntent(
                "android.intent.action.MAIN"
            )

            self.activity.startActivity(
                intent
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

    # =====================================================
    # CAMERA
    # =====================================================

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

    # =====================================================
    # CHROME
    # =====================================================

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

            if intent is not None:

                self.activity.startActivity(
                    intent
                )

            else:

                intent = self.RecognizerIntent(
                    "android.intent.action.VIEW"
                )

                intent.setData(
                    autoclass(
                        "android.net.Uri"
                    ).parse(
                        "https://www.google.com"
                    )
                )

                self.activity.startActivity(
                    intent
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

    # =====================================================
    # WHATSAPP
    # =====================================================

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

            if intent is not None:

                self.activity.startActivity(
                    intent
                )

            else:

                self.label.text = (
                    "WhatsApp installed nahi hai."
                )

                self.external_action = False

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

    # =====================================================
    # MAIN SETTINGS
    # =====================================================

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

    # =====================================================
    # WIFI SETTINGS
    # =====================================================

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
                "Wi-Fi Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # BLUETOOTH SETTINGS
    # =====================================================

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
                "Bluetooth Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # DISPLAY SETTINGS
    # =====================================================

    def open_display_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "💡 Display Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.DISPLAY_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
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

    # =====================================================
    # BATTERY SETTINGS
    # =====================================================

    def open_battery_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🔋 Battery Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.BATTERY_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.intent.action.POWER_USAGE_SUMMARY"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
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

    # =====================================================
    # LOCATION SETTINGS
    # =====================================================

    def open_location_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "📍 Location Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.LOCATION_SOURCE_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.LOCATION_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Location Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # SECURITY SETTINGS
    # =====================================================

    def open_security_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🔐 Security Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.SECURITY_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Security Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # SECURITY SETTINGS
    # =====================================================

    def open_security_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "🔐 Security Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.SECURITY_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Security Settings Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # MOBILE NETWORK / DATA SETTINGS
    # VERSION 0.17
    # =====================================================

    def open_mobile_network_settings(self, dt):

        try:

            self.external_action = True
            self.stop_listening()

            self.label.text = (
                "📶 Mobile Network Settings "
                "khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            # First try Mobile Network Settings
            intent = self.RecognizerIntent(
                "android.settings.MOBILE_NETWORK_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            # Fallback: Wireless Settings
            intent = self.RecognizerIntent(
                "android.settings.WIRELESS_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            # Final fallback: Main Settings
            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Mobile Network Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # PROCESS COMMAND
    # =====================================================

    def process_command(self, command):

        command = command.lower().strip()

        self.label.text = (
            "You said:\n" + command
        )

        # -------------------------------------------------
        # YOUTUBE
        # -------------------------------------------------

        if (
            "youtube kholo" in command
            or "youtube khol" in command
            or "youtube open karo" in command
            or "open youtube" in command
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

        # -------------------------------------------------
        # CALCULATOR
        # -------------------------------------------------

        elif (
            "calculator kholo" in command
            or "calculator khol" in command
            or "calculator open karo" in command
            or "open calculator" in command
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

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        elif (
            "camera kholo" in command
            or "camera khol" in command
            or "camera open karo" in command
            or "open camera" in command
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

        # -------------------------------------------------
        # CHROME
        # -------------------------------------------------

        elif (
            "chrome kholo" in command
            or "chrome khol" in command
            or "chrome open karo" in command
            or "open chrome" in command
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

        # -------------------------------------------------
        # WHATSAPP
        # -------------------------------------------------

        elif (
            "whatsapp kholo" in command
            or "whatsapp khol" in command
            or "whatsapp open karo" in command
            or "open whatsapp" in command
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

        # -------------------------------------------------
        # WIFI
        # -------------------------------------------------

        elif (
            "wifi kholo" in command
            or "wifi khol" in command
            or "wifi settings kholo" in command
            or "wifi settings khol" in command
            or "wifi open karo" in command
            or "open wifi" in command
            or "open wifi settings" in command
            or command == "wifi"
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

        # -------------------------------------------------
        # BLUETOOTH
        # -------------------------------------------------

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

        # -------------------------------------------------
        # DISPLAY
        # -------------------------------------------------

        elif (
            "display kholo" in command
            or "display khol" in command
            or "display settings kholo" in command
            or "display settings khol" in command
            or "display open karo" in command
            or "open display" in command
            or "open display settings" in command
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

        # -------------------------------------------------
        # BATTERY
        # -------------------------------------------------

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

        # -------------------------------------------------
        # LOCATION
        # -------------------------------------------------

        elif (
            "location kholo" in command
            or "location khol" in command
            or "location settings kholo" in command
            or "location settings khol" in command
            or "location open karo" in command
            or "open location" in command
            or "open location settings" in command
            or "gps kholo" in command
            or "gps khol" in command
            or "gps settings kholo" in command
            or "gps settings khol" in command
            or "location on karo" in command
            or "location on" in command
            or command == "location"
            or command == "gps"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Location settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_location_settings,
                2.5
            )

        # -------------------------------------------------
        # SECURITY
        # -------------------------------------------------

        elif (
            "security kholo" in command
            or "security khol" in command
            or "security settings kholo" in command
            or "security settings khol" in command
            or "security open karo" in command
            or "open security" in command
            or "open security settings" in command
            or "lock settings kholo" in command
            or "lock settings khol" in command
            or command == "security"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Security settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_security_settings,
                2.5
            )

        # -------------------------------------------------
        # MOBILE NETWORK / DATA
        # VERSION 0.17
        # -------------------------------------------------

        elif (
            "mobile network kholo" in command
            or "mobile network khol" in command
            or "mobile network settings kholo" in command
            or "mobile network settings khol" in command
            or "mobile data settings kholo" in command
            or "mobile data settings khol" in command
            or "data settings kholo" in command
            or "data settings khol" in command
            or "network settings kholo" in command
            or "network settings khol" in command
            or "mobile network open karo" in command
            or "mobile data open karo" in command
            or "open mobile network" in command
            or "open mobile network settings" in command
            or "open mobile data settings" in command
            or command == "mobile network"
            or command == "mobile data"
            or command == "network settings"
        ):

            self.external_action = True
            self.stop_listening()

            self.speak(
                "Mobile network settings khol raha hoon.",
                restart=False
            )

            Clock.schedule_once(
                self.open_mobile_network_settings,
                2.5
            )

        # -------------------------------------------------
        # GENERAL SETTINGS
        # -------------------------------------------------

        elif (
            "settings kholo" in command
            or "settings khol" in command
            or "settings open karo" in command
            or "open settings" in command
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

        # -------------------------------------------------
        # TIME
        # -------------------------------------------------

        elif (
            "time kya hai" in command
            or "kitne baje" in command
            or "time batao" in command
        ):

            now = datetime.now()

            current_time = now.strftime(
                "%I:%M %p"
            )

            self.speak(
                "Abhi time hai "
                + current_time
            )

        # -------------------------------------------------
        # HELLO
        # -------------------------------------------------

        elif (
            "hello" in command
            or "hi" in command
            or "hey" in command
            or "namaste" in command
        ):

            self.speak(
                "Hello! Main JARVIS hoon."
            )

        # -------------------------------------------------
        # UNKNOWN COMMAND
        # -------------------------------------------------

        else:

            self.speak(
                "Maine suna: "
                + command
            )

    # =====================================================
    # TEXT TO SPEECH
    # =====================================================

    def speak(
        self,
        text,
        restart=True
    ):

        try:

            self.tts.speak(
                text,
                self.TextToSpeech.QUEUE_FLUSH,
                None
            )

            self.label.text = (
                "🤖 " + text
            )

            if restart:

                Clock.schedule_once(
                    self.listen_again,
                    2.5
                )

        except Exception as e:

            self.label.text = (
                "TTS Error:\n"
                + str(e)
            )


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    VoiceAssistant().run()
