from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method
from datetime import datetime


# ==========================================
# Android Main Thread Runnable
# ==========================================

class MainThreadRunnable(PythonJavaClass):

    __javainterfaces__ = ['java/lang/Runnable']
    __javacontext__ = 'app'

    def __init__(self, function):
        super().__init__()
        self.function = function

    @java_method('()V')
    def run(self):
        self.function()


# ==========================================
# Speech Recognition Listener
# ==========================================

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


# ==========================================
# JARVIS
# ==========================================

class VoiceAssistant(App):

    def build(self):

        self.label = Label(
            text="🤖 JARVIS\n\nStarting...",
            font_size="22sp"
        )

        # External Android app/action
        self.external_action = False

        # ----------------------------------
        # Android Classes
        # ----------------------------------

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

        # ----------------------------------
        # Text To Speech
        # ----------------------------------

        self.tts = self.TextToSpeech(
            self.activity,
            None
        )

        self.tts.setLanguage(
            self.Locale.US
        )

        # ----------------------------------
        # Speech Recognition
        # ----------------------------------

        self.listener = RecognitionListener(
            self
        )

        self.setup_runnable = MainThreadRunnable(
            self.setup_speech
        )

        Clock.schedule_once(
            self.start_setup,
            0.5
        )

        return self.label

    # ======================================
    # Speech Setup
    # ======================================

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
                "Speech Setup Error:\n" +
                str(e)
            )

    # ======================================
    # Start Listening
    # ======================================

    def start_listening_request(self, dt):

        if self.external_action:
            return

        try:

            self.activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Listening Thread Error:\n" +
                str(e)
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
                "Start Error:\n" +
                str(e)
            )

    # ======================================
    # Listen Again
    # ======================================

    def listen_again(self, dt):

        if self.external_action:
            return

        try:

            self.activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Restart Error:\n" +
                str(e)
            )

    # ======================================
    # Stop Listening
    # ======================================

    def stop_listening(self):

        try:
            self.recognizer.stopListening()
        except Exception:
            pass

        try:
            self.recognizer.cancel()
        except Exception:
            pass

    # ======================================
    # Open Android App
    # ======================================

    def open_package(self, package_names, app_name):

        try:

            self.external_action = True

            self.stop_listening()

            self.speak(
                app_name + " khol raha hoon.",
                restart=False
            )

            # TTS ke baad app open hoga
            Clock.schedule_once(
                lambda dt: self.launch_package(
                    package_names,
                    app_name
                ),
                2.5
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                app_name +
                " Error:\n" +
                str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # ======================================
    # Launch Package
    # ======================================

    def launch_package(
        self,
        package_names,
        app_name
    ):

        launched = False

        try:

            for package_name in package_names:

                try:

                    intent = self.RecognizerIntent(
                        "android.intent.action.MAIN"
                    )

                    intent.addCategory(
                        "android.intent.category.LAUNCHER"
                    )

                    intent.setPackage(
                        package_name
                    )

                    self.activity.startActivity(
                        intent
                    )

                    launched = True
                    break

                except Exception:
                    pass

            if not launched:

                self.external_action = False

                self.label.text = (
                    "❌ " +
                    app_name +
                    " nahi mila."
                )

                Clock.schedule_once(
                    self.listen_again,
                    2
                )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "❌ App Error:\n" +
                str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # ======================================
    # YouTube
    # ======================================

    def open_youtube(self, dt):

        try:

            self.external_action = True

            self.stop_listening()

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
                "YouTube Error:\n" +
                str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # ======================================
    # Camera
    # ======================================

    def open_camera(self, dt):

        try:

            self.external_action = True

            self.stop_listening()

            intent = self.RecognizerIntent(
                "android.media.action.IMAGE_CAPTURE"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Camera Error:\n" +
                str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # ======================================
    # Settings
    # ======================================

    def open_settings(self, dt):

        try:

            self.external_action = True

            self.stop_listening()

            intent = self.RecognizerIntent(
                "android.settings.SETTINGS"
            )

            self.activity.startActivity(
                intent
            )

        except Exception as e:

            self.external_action = False

            self.label.text = (
                "Settings Error:\n" +
                str(e)
            )

            Clock.schedule_once(
                self.listen_again,
                2
            )

    # ======================================
    # Command Processing
    # ======================================

    def process_command(self, text):

        command = text.lower().strip()

        # ----------------------------------
        # 1. Hello Jarvis
        # ----------------------------------

        if "hello jarvis" in command:

            self.speak(
                "Hello! Main ready hoon."
            )

        # ----------------------------------
        # 2. Name
        # ----------------------------------

        elif (
            "tumhara naam kya hai" in command
            or "what is your name" in command
            or "your name" in command
        ):

            self.speak(
                "Mera naam JARVIS hai."
            )

        # ----------------------------------
        # 3. Time
        # ----------------------------------

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

        # ----------------------------------
        # 4. Date
        # ----------------------------------

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

        # ----------------------------------
        # 5. YouTube
        # ----------------------------------

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

        # ----------------------------------
        # 6. Calculator
        # ----------------------------------

        elif (
            "calculator kholo" in command
            or "calculator khol" in command
            or "calculator open karo" in command
            or "open calculator" in command
            or "calculator open" in command
            or command == "calculator"
        ):

            self.open_package(
                [
                    "com.google.android.calculator",
                    "com.google.android.calculator2"
                ],
                "Calculator"
            )

        # ----------------------------------
        # 7. Camera
        # ----------------------------------

        elif (
            "camera kholo" in command
            or "camera khol" in command
            or "camera open karo" in command
            or "open camera" in command
            or "camera open" in command
            or command == "camera"
        ):

            self.speak(
                "Camera khol raha hoon.",
                restart=False
            )

            self.external_action = True

            self.stop_listening()

            Clock.schedule_once(
                self.open_camera,
                2.5
            )

        # ----------------------------------
        # 8. Chrome
        # ----------------------------------

        elif (
            "chrome kholo" in command
            or "chrome khol" in command
            or "chrome open karo" in command
            or "open chrome" in command
            or "chrome open" in command
            or command == "chrome"
        ):

            self.open_package(
                [
                    "com.android.chrome"
                ],
                "Chrome"
            )

        # ----------------------------------
        # 9. WhatsApp
        # ----------------------------------

        elif (
            "whatsapp kholo" in command
            or "whatsapp khol" in command
            or "whatsapp open karo" in command
            or "open whatsapp" in command
            or "whatsapp open" in command
            or command == "whatsapp"
        ):

            self.open_package(
                [
                    "com.whatsapp"
                ],
                "WhatsApp"
            )

        # ----------------------------------
        # 10. Gallery / Photos
        # ----------------------------------

        elif (
            "gallery kholo" in command
            or "gallery khol" in command
            or "gallery open karo" in command
            or "open gallery" in command
            or "photos kholo" in command
            or "photos open karo" in command
            or "open photos" in command
            or command == "gallery"
            or command == "photos"
        ):

            self.open_package(
                [
                    "com.google.android.apps.photos",
                    "com.miui.gallery"
                ],
                "Gallery"
            )

        # ----------------------------------
        # 11. Settings
        # ----------------------------------

        elif (
            "settings kholo" in command
            or "settings khol" in command
            or "settings open karo" in command
            or "open settings" in command
            or "settings open" in command
            or command == "settings"
        ):

            self.speak(
                "Settings khol raha hoon.",
                restart=False
            )

            self.external_action = True

            self.stop_listening()

            Clock.schedule_once(
                self.open_settings,
                2.5
            )

        # ----------------------------------
        # 12. Play Store
        # ----------------------------------

        elif (
            "play store kholo" in command
            or "play store khol" in command
            or "play store open karo" in command
            or "open play store" in command
            or "play store open" in command
            or command == "play store"
        ):

            self.open_package(
                [
                    "com.android.vending"
                ],
                "Play Store"
            )

        # ----------------------------------
        # 13. Phone
        # ----------------------------------

        elif (
            "phone kholo" in command
            or "phone khol" in command
            or "phone open karo" in command
            or "open phone" in command
            or "phone open" in command
        ):

            self.open_package(
                [
                    "com.google.android.dialer",
                    "com.android.dialer",
                    "com.android.contacts"
                ],
                "Phone"
            )

        # ----------------------------------
        # 14. Messages
        # ----------------------------------

        elif (
            "messages kholo" in command
            or "message kholo" in command
            or "messages khol" in command
            or "open messages" in command
            or "open message" in command
            or "messages open karo" in command
        ):

            self.open_package(
                [
                    "com.google.android.apps.messaging",
                    "com.android.mms"
      ,
