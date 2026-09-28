from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

from jnius import autoclass, PythonJavaClass, java_method
from datetime import datetime


# =========================================================
# ANDROID MAIN THREAD RUNNER
# =========================================================

class MainThreadRunnable(PythonJavaClass):

    __javainterfaces__ = [
        "java/lang/Runnable"
    ]

    __javacontext__ = "app"

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

    __javacontext__ = "app"

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant

    # -----------------------------------------------------
    # READY
    # -----------------------------------------------------

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):

        if not self.assistant.external_action:
            self.assistant.label.text = (
                "🎤 Listening..."
            )

    # -----------------------------------------------------
    # BEGINNING
    # -----------------------------------------------------

    @java_method("()V")
    def onBeginningOfSpeech(self):

        if not self.assistant.external_action:
            self.assistant.label.text = (
                "👂 Sun raha hoon..."
            )

    # -----------------------------------------------------
    # RMS
    # -----------------------------------------------------

    @java_method("(F)V")
    def onRmsChanged(self, rmsdB):
        pass

    # -----------------------------------------------------
    # BUFFER
    # -----------------------------------------------------

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    # -----------------------------------------------------
    # END
    # -----------------------------------------------------

    @java_method("()V")
    def onEndOfSpeech(self):

        if not self.assistant.external_action:
            self.assistant.label.text = (
                "🧠 Samajh raha hoon..."
            )

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    @java_method("(I)V")
    def onError(self, error):

        # -----------------------------------------------
        # ERROR 5 = ERROR_CLIENT
        #
        # Do NOT show it on screen.
        # This commonly happens around cancel/stop
        # while changing recognition state.
        # -----------------------------------------------

        if error == 5:
            if not self.assistant.external_action:
                Clock.schedule_once(
                    self.assistant.listen_again,
                    1
                )
            return

        # -----------------------------------------------
        # If another app/settings is opening,
        # ignore all speech errors.
        # -----------------------------------------------

        if self.assistant.external_action:
            return

        self.assistant.label.text = (
            "❌ Speech Error: "
            + str(error)
        )

        Clock.schedule_once(
            self.assistant.listen_again,
            1
        )

    # -----------------------------------------------------
    # RESULTS
    # -----------------------------------------------------

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):

        if self.assistant.external_action:
            return

        try:

            matches = results.getStringArrayList(
                "results_recognition"
            )

            if matches and matches.size() > 0:

                command = str(
                    matches.get(0)
                )

                self.assistant.label.text = (
                    "You said:\n"
                    + command
                )

                self.assistant.process_command(
                    command
                )

            else:

                self.assistant.label.text = (
                    "Kuch samajh nahi aaya."
                )

                Clock.schedule_once(
                    self.assistant.listen_again,
                    1
                )

        except Exception as e:

            self.assistant.label.text = (
                "Recognition Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.assistant.listen_again,
                1
            )

    # -----------------------------------------------------
    # PARTIAL
    # -----------------------------------------------------

    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, results):
        pass

    # -----------------------------------------------------
    # EVENT
    # -----------------------------------------------------

    @java_method(
        "(ILandroid/os/Bundle;)V"
    )
    def onEvent(self, eventType, params):
        pass


# =========================================================
# VOICE ASSISTANT
# =========================================================

class VoiceAssistant(App):

    def build(self):

        self.activity = autoclass(
            "org.kivy.android.PythonActivity"
        ).mActivity

        self.TextToSpeech = None
        self.Locale = None
        self.tts = None

        self.SpeechRecognizer = None
        self.RecognizerIntent = None
        self.recognizer = None
        self.listener = None
        self.intent = None

        self.external_action = False

        self.label = Label(
            text=(
                "JARVIS Voice Assistant\n"
                "Starting..."
            ),
            halign="center",
            valign="middle",
            font_size="22sp"
        )

        return self.label

    # =====================================================
    # APP START
    # =====================================================

    def on_start(self):

        Clock.schedule_once(
            self.start_setup,
            1
        )

    # =====================================================
    # START SETUP
    # =====================================================

    def start_setup(self, dt):

        try:

            runnable = MainThreadRunnable(
                self.setup_speech
            )

            self.activity.runOnUiThread(
                runnable
            )

        except Exception as e:

            self.label.text = (
                "Setup Error:\n"
                + str(e)
            )

    # =====================================================
    # SPEECH + TTS SETUP
    # =====================================================

    def setup_speech(self):

        try:

            # -------------------------------------------------
            # TEXT TO SPEECH
            # -------------------------------------------------

            self.TextToSpeech = autoclass(
                "android.speech.tts.TextToSpeech"
            )

            self.Locale = autoclass(
                "java.util.Locale"
            )

            self.tts = self.TextToSpeech(
                self.activity,
                None
            )

            self.tts.setLanguage(
                self.Locale.US
            )

            # -------------------------------------------------
            # SPEECH RECOGNIZER
            # -------------------------------------------------

            self.SpeechRecognizer = autoclass(
                "android.speech.SpeechRecognizer"
            )

            self.RecognizerIntent = autoclass(
                "android.content.Intent"
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

            self.intent.putExtra(
                "android.speech.extra.PARTIAL_RESULTS",
                False
            )

            self.recognizer = (
                self.SpeechRecognizer
                .createSpeechRecognizer(
                    self.activity
                )
            )

            self.recognizer.setRecognitionListener(
                self.listener
            )

            self.label.text = (
                "JARVIS Voice Assistant\n"
                "Ready..."
            )

            Clock.schedule_once(
                self.start_listening_request,
                1
            )

        except Exception as e:

            self.label.text = (
                "Setup Error:\n"
                + str(e)
            )

    # =====================================================
    # START LISTENING REQUEST
    # =====================================================

    def start_listening_request(self, dt):

        if self.external_action:
            return

        try:

            runnable = MainThreadRunnable(
                self.start_listening
            )

            self.activity.runOnUiThread(
                runnable
            )

        except Exception as e:

            self.label.text = (
                "Listening Error:\n"
                + str(e)
            )

    # =====================================================
    # START LISTENING
    # =====================================================

    def start_listening(self):

        if self.external_action:
            return

        try:

            if self.recognizer is not None:

                self.label.text = (
                    "🎤 Listening..."
                )

                self.recognizer.startListening(
                    self.intent
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
            None
        )

    # =====================================================
    # STOP LISTENING
    # =====================================================

    def stop_listening(self):

        try:

            if self.recognizer is not None:
                self.recognizer.cancel()

        except Exception:
            pass

        try:

            if self.recognizer is not None:
                self.recognizer.stopListening()

        except Exception:
            pass

    # =====================================================
    # YOUTUBE
    # =====================================================

    def open_youtube(self, dt):

        try:

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

    # =====================================================
    # CALCULATOR
    # =====================================================

    def open_calculator(self, dt):

        try:

            self.label.text = (
                "🧮 Calculator khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            packages = [
                "com.google.android.calculator",
                "com.miui.calculator",
                "com.android.calculator2"
            ]

            for package_name in packages:

                try:

                    intent = (
                        pm.getLaunchIntentForPackage(
                            package_name
                        )
                    )

                    if intent is not None:

                        self.activity.startActivity(
                            intent
                        )

                        return

                except Exception:
                    pass

            intent = self.RecognizerIntent(
                "android.intent.action.MAIN"
            )

            intent.addCategory(
                "android.intent.category.APP_CALCULATOR"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            self.label.text = (
                "Calculator app nahi mili."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Calculator Error:\n"
                + str(e)
            )

    # =====================================================
    # CAMERA
    # =====================================================

    def open_camera(self, dt):

        try:

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

    # =====================================================
    # CHROME
    # =====================================================

    def open_chrome(self, dt):

        try:

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

                self.label.text = (
                    "Chrome nahi mila."
                )

                self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Chrome Error:\n"
                + str(e)
            )

    # =====================================================
    # WHATSAPP
    # =====================================================

    def open_whatsapp(self, dt):

        try:

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
                    "WhatsApp nahi mila."
                )

                self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "WhatsApp Error:\n"
                + str(e)
            )

    # =====================================================
    # MAIN SETTINGS
    # =====================================================

    def open_settings(self, dt):

        try:

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

    # =====================================================
    # WIFI
    # =====================================================

    def open_wifi_settings(self, dt):

        try:

            self.label.text = (
                "📶 Wi-Fi Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.WIFI_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            intent = self.RecognizerIntent(
                "android.settings.WIRELESS_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            self.label.text = (
                "Wi-Fi Settings available nahi hai."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Wi-Fi Error:\n"
                + str(e)
            )

    # =====================================================
    # BLUETOOTH
    # =====================================================

    def open_bluetooth_settings(self, dt):

        try:

            self.label.text = (
                "🔵 Bluetooth Settings khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            intent = self.RecognizerIntent(
                "android.settings.BLUETOOTH_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            self.label.text = (
                "Bluetooth Settings available nahi hai."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Bluetooth Error:\n"
                + str(e)
            )

    # =====================================================
    # DISPLAY
    # =====================================================

    def open_display_settings(self, dt):

        try:

            self.label.text = (
                "☀️ Display Settings khol raha hoon..."
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

            self.label.text = (
                "Display Settings available nahi hai."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Display Error:\n"
                + str(e)
            )

    # =====================================================
    # BATTERY
    # =====================================================

    def open_battery_settings(self, dt):

        try:

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

            self.label.text = (
                "Battery Settings available nahi hai."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Battery Error:\n"
                + str(e)
            )

    # =====================================================
    # LOCATION
    # =====================================================

    def open_location_settings(self, dt):

        try:

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

            self.label.text = (
                "Location Settings available nahi hai."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Location Error:\n"
                + str(e)
            )

    # =====================================================
    # SECURITY
    # =====================================================

    def open_security_settings(self, dt):

        try:

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

            self.label.text = (
                "Security Settings available nahi hai."
            )

            self.external_action = False

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Security Error:\n"
                + str(e)
            )

    # =====================================================
    # MOBILE NETWORK / DATA
    # =====================================================

    def open_mobile_network_settings(self, dt):

        try:

            self.label.text = (
                "📶 Mobile Network Settings "
                "khol raha hoon..."
            )

            pm = self.activity.getPackageManager()

            # ---------------------------------------------
            # 1. MOBILE NETWORK SETTINGS
            # ---------------------------------------------

            intent = self.RecognizerIntent(
                "android.settings.MOBILE_NETWORK_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            # ---------------------------------------------
            # 2. NETWORK OPERATOR SETTINGS
            # ---------------------------------------------

            intent = self.RecognizerIntent(
                "android.settings.NETWORK_OPERATOR_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            # ---------------------------------------------
            # 3. DATA ROAMING SETTINGS
            # ---------------------------------------------

            intent = self.RecognizerIntent(
                "android.settings.DATA_ROAMING_SETTINGS"
            )

            if intent.resolveActivity(pm):

                self.activity.startActivity(
                    intent
                )

                return

            # ---------------------------------------------
            # IMPORTANT:
            # DO NOT OPEN GENERAL SETTINGS.
            # ---------------------------------------------

            self.label.text = (
                "❌ Mobile Network Settings "
                "is phone par available nahi hai."
            )

            self.external_action = False

            Clock.schedule_once(
                self.listen_again,
                2
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
    # COMMAND PROCESSING
    # =====================================================

    def process_command(self, command):

        try:

            command = str(
                command
            ).lower().strip()

            # -------------------------------------------------
            # WIFI NORMALIZATION
            # -------------------------------------------------

            command = command.replace(
                "वाई-फाई",
                "wifi"
            )

            command = command.replace(
                "वाई फाई",
                "wifi"
            )

            command = command.replace(
                "वाईफाई",
                "wifi"
            )

            command = command.replace(
                "wi fi",
                "wifi"
            )

            command = command.replace(
                "wi-fi",
                "wifi"
            )

            command = " ".join(
                command.split()
            )

            self.label.text = (
                "You said:\n"
                + command
            )

            # =================================================
            # YOUTUBE
            # =================================================

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

                return

            # =================================================
            # CALCULATOR
            # =================================================

            elif (
                "calculator kholo" in command
                or "calculator khol" in command
                or "calculator open karo" in command
                or "open calculator" in command
                or "calc kholo" in command
                or "calc khol" in command
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

                return

            # =================================================
            # CAMERA
            # =================================================

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

                return

            # =================================================
            # CHROME
            # =================================================

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

                return

            # =================================================
            # WHATSAPP
            # =================================================
            
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

                return

            # =================================================
            # WIFI
            # =================================================

            elif (
                "wifi kholo" in command
                or "wifi khol" in command
                or "wifi settings kholo" in command
                or "wifi settings khol" in command
                or "wifi open karo" in command
                or "open wifi" in command
                or "open wifi settings" in command
                or "wifi dikhao" in command
                or "wifi settings dikhao" in command
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

                return

            # =================================================
            # BLUETOOTH
            # =================================================

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

                return

            # =================================================
            # DISPLAY
            # =================================================

            elif (
                "display kholo" in command
                or "display khol" in command
                or "display settings kholo" in command
                or "display settings khol" in command
                or "open display" in command
                or "open display settings" in command
                or "screen settings kholo" in command
                or "screen settings khol" in command
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

                return

            # =================================================
            # BATTERY
            # =================================================

            elif (
                "battery kholo" in command
                or "battery khol" in command
                or "battery settings kholo" in command
                or "battery settings khol" in command
                or "open battery" in command
                or "open battery settings" in command
                or "battery dikhao" in command
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

                return

            # =================================================
            # LOCATION
            # =================================================

            elif (
                "location kholo" in command
                or "location khol" in command
                or "location settings kholo" in command
                or "location settings khol" in command
                or "open location" in command
                or "open location settings" in command
                or "gps kholo" in command
                or "gps khol" in command
                or "gps settings kholo" in command
                or "gps settings khol" in command
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

                return

            # =================================================
            # SECURITY
            # =================================================

            elif (
                "security kholo" in command
                or "security khol" in command
                or "security settings kholo" in command
                or "security settings khol" in command
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

                return

            # =================================================
            # MOBILE NETWORK / DATA
            # =================================================

            elif (
                "mobile network kholo" in command
                or "mobile network khol" in command
                or "mobile network settings kholo" in command
                or "mobile network settings khol" in command
                or "mobile data settings kholo" in command
                or "mobile data settings khol" in command
                or "mobile data kholo" in command
                or "mobile data khol" in command
                or "mobile data open karo" in command
                or "mobile network open karo" in command
                or "open mobile network" in command
                or "open mobile network settings" in command
                or "open mobile data" in command
                or "open mobile data settings" in command
                or "data settings kholo" in command
                or "data settings khol" in command
                or "data open karo" in command
                or "network settings kholo" in command
                or "network settings khol" in command
                or "mobile bada kholo" in command
                or "mobile bada khol" in command
                or "mobile bada" in command
                or command == "mobile network"
                or command == "mobile data"
                or command == "network settings"
            ):

                self.external_action = True
                self.stop_listening()

                self.speak(
                    "Mobile network settings "
                    "khol raha hoon.",
                    restart=False
                )

                Clock.schedule_once(
                    self.open_mobile_network_settings,
                    2.5
                )

                return

            # =================================================
            # MAIN SETTINGS
            # =================================================

            elif (
                "settings kholo" in command
                or "settings khol" in command
                or "setting kholo" in command
                or "setting khol" in command
                or "settings open karo" in command
                or "setting open karo" in command
                or "open settings" in command
                or "open setting" in command
                or command == "settings"
                or command == "setting"
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

                return

            # =================================================
            # TIME
            # =================================================

            elif (
                "time batao" in command
                or "time kya hai" in command
                or "kitne baje" in command
                or "what time" in command
                or command == "time"
            ):

                now = datetime.now().strftime(
                    "%I:%M %p"
                )

                self.speak(
                    "Abhi time hai " + now,
                    restart=True
                )

                return

            # =================================================
            # DATE
            # =================================================

            elif (
                "date batao" in command
                or "aaj ki date" in command
                or "today date" in command
                or "what is the date" in command
                or command == "date"
            ):

                today = datetime.now().strftime(
                    "%d %B %Y"
                )

                self.speak(
                    "Aaj ki date hai " + today,
                    restart=True
                )

                return

            # =================================================
            # STOP
            # =================================================

            elif (
                "stop listening" in command
                or "listening stop karo" in command
                or "sunna band karo" in command
            ):

                self.stop_listening()

                self.label.text = (
                    "Listening stopped."
                )

                return

            # =================================================
            # UNKNOWN
            # =================================================

            else:

                self.speak(
                    "Maine suna: " + command,
                    restart=True
                )

        except Exception as e:

            self.label.text = (
                "Command Error:\n"
                + str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # =====================================================
    # TEXT TO SPEECH
    # =====================================================

    def speak(self, text, restart=True):

        try:

            self.label.text = (
                "🔊 JARVIS:\n"
                + text
            )

            if self.tts is not None:

                self.tts.speak(
                    text,
                    self.TextToSpeech.QUEUE_FLUSH,
                    None
                )

            if restart and not self.external_action:

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
# RUN
# =========================================================

VoiceAssistant().run()
