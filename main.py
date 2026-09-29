# ============================================================
# MY VOICE ASSISTANT - v0.21
# BASE: v0.20 SUCCESS
# NEW:
#   1. Phone / Dialer Actions
#   2. Contacts Actions
#   3. Wi-Fi command fix
# ============================================================

import re
import time
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

from jnius import autoclass, PythonJavaClass, java_method


# ============================================================
# ANDROID CLASSES
# ============================================================

PythonActivity = autoclass("org.kivy.android.PythonActivity")
activity = PythonActivity.mActivity

Intent = autoclass("android.content.Intent")
Settings = autoclass("android.provider.Settings")
Uri = autoclass("android.net.Uri")

RecognizerIntent = autoclass(
    "android.speech.RecognizerIntent"
)

SpeechRecognizer = autoclass(
    "android.speech.SpeechRecognizer"
)

RecognitionListener = autoclass(
    "android.speech.RecognitionListener"
)

TextToSpeech = autoclass(
    "android.speech.tts.TextToSpeech"
)

Locale = autoclass(
    "java.util.Locale"
)

PackageManager = autoclass(
    "android.content.pm.PackageManager"
)

ContactsContract = autoclass(
    "android.provider.ContactsContract"
)


# ============================================================
# MAIN THREAD RUNNER
# ============================================================

Runnable = autoclass("java.lang.Runnable")


class MainThreadRunnable(PythonJavaClass):

    __javainterfaces__ = [
        "java/lang/Runnable"
    ]

    def __init__(self, function):
        super().__init__()
        self.function = function

    @java_method("()V")
    def run(self):
        try:
            self.function()
        except Exception as e:
            print("MainThread Error:", e)


def run_on_android_thread(function):
    try:
        activity.runOnUiThread(
            MainThreadRunnable(function)
        )
    except Exception as e:
        print("run_on_android_thread error:", e)


# ============================================================
# SPEECH RECOGNITION LISTENER
# ============================================================

class MyRecognitionListener(
    PythonJavaClass,
    RecognitionListener
):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant

    @java_method("()V")
    def onReadyForSpeech(self, params):
        self.assistant.on_ready()

    @java_method("()V")
    def onBeginningOfSpeech(self):
        self.assistant.on_beginning()

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("(F)V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("([B)V")
    def onEndOfSpeech(self):
        self.assistant.on_end()

    @java_method("(I)V")
    def onError(self, error):
        self.assistant.on_error(error)

    @java_method("([Ljava/lang/String;)V")
    def onResults(self, results):
        self.assistant.on_results(results)

    @java_method("([Ljava/lang/String;)V")
    def onPartialResults(self, results):
        pass

    @java_method("(Landroid/os/Bundle;)V")
    def onEvent(self, eventType, params):
        pass


# ============================================================
# TTS INIT LISTENER
# ============================================================

class TTSInitListener(
    PythonJavaClass
):

    __javainterfaces__ = [
        "android/speech/tts/TextToSpeech$OnInitListener"
    ]

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant

    @java_method("(I)V")
    def onInit(self, status):
        try:
            if status == TextToSpeech.SUCCESS:
                self.assistant.tts_ready = True

                try:
                    self.assistant.tts.setLanguage(
                        Locale.getDefault()
                    )
                except Exception:
                    pass

                print("TTS ready")

            else:
                self.assistant.tts_ready = False
                print("TTS initialization failed")

        except Exception as e:
            print("TTS init error:", e)


# ============================================================
# MAIN APP
# ============================================================

class VoiceAssistantApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.speech = None
        self.listener = None

        self.tts = None
        self.tts_ready = False

        self.is_listening = False
        self.is_stopping = False

        self.retry_event = None

        self.status_label = None

        # Prevent multiple recognition starts
        self.starting_recognition = False


    # ========================================================
    # BUILD
    # ========================================================

    def build(self):

        layout = BoxLayout(
            orientation="vertical",
            padding=30,
            spacing=20
        )

        self.status_label = Label(
            text="My Voice Assistant\nv0.21",
            font_size="24sp"
        )

        layout.add_widget(
            self.status_label
        )

        return layout


    # ========================================================
    # APP START
    # ========================================================

    def on_start(self):

        print("Voice Assistant v0.21 started")

        self.update_status(
            "Voice Assistant\nStarting..."
        )

        Clock.schedule_once(
            self.setup_android,
            0.5
        )


    # ========================================================
    # ANDROID SETUP
    # ========================================================

    def setup_android(self, dt=None):

        run_on_android_thread(
            self.setup_android_main
        )


    def setup_android_main(self):

        try:

            # ------------------------------------------------
            # TEXT TO SPEECH
            # ------------------------------------------------

            self.tts = TextToSpeech(
                activity,
                TTSInitListener(self)
            )

            # ------------------------------------------------
            # SPEECH RECOGNIZER
            # ------------------------------------------------

            if not SpeechRecognizer.isRecognitionAvailable(
                activity
            ):
                print(
                    "Speech recognition is not available"
                )

                self.update_status(
                    "Speech Recognition unavailable"
                )

                return

            self.listener = MyRecognitionListener(
                self
            )

            self.speech = SpeechRecognizer.createSpeechRecognizer(
                activity
            )

            self.speech.setRecognitionListener(
                self.listener
            )

            print(
                "SpeechRecognizer created on main thread"
            )

            self.update_status(
                "Ready"
            )

            Clock.schedule_once(
                lambda dt: self.speak(
                    "Hello! Main tumhara voice assistant hoon."
                ),
                0.8
            )

            Clock.schedule_once(
                self.start_listening,
                2.5
            )

        except Exception as e:

            print(
                "Android setup error:",
                e
            )

            self.update_status(
                "Setup Error"
            )


    # ========================================================
    # STATUS
    # ========================================================

    def update_status(self, text):

        try:

            Clock.schedule_once(
                lambda dt: self._update_status(text),
                0
            )

        except Exception:
            pass


    def _update_status(self, text):

        try:

            if self.status_label:
                self.status_label.text = text

        except Exception:
            pass


    # ========================================================
    # TEXT TO SPEECH
    # ========================================================

    def speak(self, text):

        if not text:
            return

        print(
            "Assistant:",
            text
        )

        self.update_status(
            text
        )

        def do_speak():

            try:

                if (
                    self.tts is not None
                    and self.tts_ready
                ):

                    self.tts.speak(
                        str(text),
                        TextToSpeech.QUEUE_FLUSH,
                        None,
                        "assistant_utterance"
                    )

            except Exception as e:

                print(
                    "TTS speak error:",
                    e
                )

        run_on_android_thread(
            do_speak
        )


    # ========================================================
    # SPEECH LISTENING
    # ========================================================

    def start_listening(self, dt=None):

        if self.speech is None:
            return

        if self.starting_recognition:
            return

        self.starting_recognition = True

        def start():

            try:

                self.starting_recognition = False

                intent = Intent(
                    RecognizerIntent.ACTION_RECOGNIZE_SPEECH
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE,
                    "hi-IN"
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,
                    "hi-IN"
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_PARTIAL_RESULTS,
                    False
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_MAX_RESULTS,
                    5
                )

                self.is_listening = True

                self.update_status(
                    "Listening..."
                )

                self.speech.startListening(
                    intent
                )

            except Exception as e:

                self.starting_recognition = False

                print(
                    "Start listening error:",
                    e
                )

                self.is_listening = False

                Clock.schedule_once(
                    self.start_listening,
                    1.0
                )

        run_on_android_thread(
            start
        )


    # ========================================================
    # STOP LISTENING
    # ========================================================

    def stop_listening(self):

        def stop():

            try:

                if self.speech is not None:

                    self.speech.stopListening()

                self.is_listening = False

            except Exception as e:

                print(
                    "Stop listening error:",
                    e
                )

        run_on_android_thread(
            stop
        )


    # ========================================================
    # SPEECH CALLBACKS
    # ========================================================

    def on_ready(self):

        self.update_status(
            "Listening..."
        )


    def on_beginning(self):

        self.update_status(
            "Listening..."
        )


    def on_end(self):

        self.is_listening = False

        self.update_status(
            "Processing..."
        )


    # ========================================================
    # SPEECH ERROR
    # ========================================================

    def on_error(self, error):

        self.is_listening = False

        print(
            "Speech error:",
            error
        )

        # Error 5 = client error.
        # Silently retry, as in v0.20.
        if error == 5:

            Clock.schedule_once(
                self.start_listening,
                0.5
            )

            return

        # Common temporary recognition errors
        if error in (
            6,
            7,
            8,
            9
        ):

            Clock.schedule_once(
                self.start_listening,
                0.8
            )

            return

        Clock.schedule_once(
            self.start_listening,
            1.0
        )


    # ========================================================
    # SPEECH RESULTS
    # ========================================================

    def on_results(self, results):

        try:

            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )

            if matches is None:
                Clock.schedule_once(
                    self.start_listening,
                    0.5
                )
                return

            if matches.size() == 0:
                Clock.schedule_once(
                    self.start_listening,
                    0.5
                )
                return

            command = str(
                matches.get(0)
            ).strip()

            if not command:
                Clock.schedule_once(
                    self.start_listening,
                    0.5
                )
                return

            print(
                "Recognized:",
                command
            )

            self.process_command(
                command
            )

        except Exception as e:

            print(
                "Results error:",
                e
            )

            Clock.schedule_once(
                self.start_listening,
                0.8
            )


    # ========================================================
    # NORMALIZE COMMAND
    # ========================================================

    def normalize_command(self, command):

        command = command.lower().strip()

        command = command.replace(
            "wi-fi",
            "wifi"
        )

        command = command.replace(
            "wi fi",
            "wifi"
        )

        command = re.sub(
            r"[^\w\s+.-]",
            " ",
            command,
            flags=re.UNICODE
        )

        command = re.sub(
            r"\s+",
            " ",
            command
        ).strip()

        return command


    # ========================================================
    # OPEN INTENT
    # ========================================================

    def open_intent(
        self,
        intent,
        success_message=None,
        fail_message="Open nahi ho paya."
    ):

        def do_open():

            try:

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(
                    intent
                )

                if success_message:
                    self.speak(
                        success_message
                    )

            except Exception as e:

                print(
                    "Intent open error:",
                    e
                )

                self.speak(
                    fail_message
                )

        run_on_android_thread(
            do_open
        )


# ============================================================
# END PART 1
# ============================================================

# ============================================================
# PART 2/3
# COMMAND ACTIONS
# ============================================================


    # ========================================================
    # GOOGLE WEB SEARCH
    # ========================================================

    def google_search(self, query):

        query = query.strip()

        if not query:
            self.speak(
                "Kya search karna hai?"
            )
            Clock.schedule_once(
                self.start_listening,
                1.5
            )
            return

        try:

            encoded = Uri.encode(
                query
            )

            url = (
                "https://www.google.com/search?q="
                + str(encoded)
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent,
                "Google search khol raha hoon."
            )

        except Exception as e:

            print(
                "Google search error:",
                e
            )

            self.speak(
                "Google search open nahi ho paya."
            )


    # ========================================================
    # YOUTUBE SEARCH
    # ========================================================

    def youtube_search(self, query):

        query = query.strip()

        if not query:
            self.speak(
                "YouTube par kya search karna hai?"
            )
            Clock.schedule_once(
                self.start_listening,
                1.5
            )
            return

        try:

            encoded = Uri.encode(
                query
            )

            url = (
                "https://www.youtube.com/results?search_query="
                + str(encoded)
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent,
                "YouTube search khol raha hoon."
            )

        except Exception as e:

            print(
                "YouTube search error:",
                e
            )

            self.speak(
                "YouTube search open nahi ho paya."
            )


    # ========================================================
    # MUSIC SEARCH
    # ========================================================

    def music_search(self, query):

        query = query.strip()

        if not query:
            self.speak(
                "Kaunsa music search karna hai?"
            )
            Clock.schedule_once(
                self.start_listening,
                1.5
            )
            return

        try:

            encoded = Uri.encode(
                query
            )

            url = (
                "https://music.youtube.com/search?q="
                + str(encoded)
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent,
                "Music search khol raha hoon."
            )

        except Exception as e:

            print(
                "Music search error:",
                e
            )

            self.speak(
                "Music search open nahi ho paya."
            )


    # ========================================================
    # WHATSAPP
    # ========================================================

    def open_whatsapp(self):

        packages = [
            "com.whatsapp",
            "com.whatsapp.w4b"
        ]

        def do_open():

            try:

                pm = activity.getPackageManager()

                for package_name in packages:

                    try:

                        package_info = (
                            pm.getPackageInfo(
                                package_name,
                                0
                            )
                        )

                        if package_info:

                            intent = (
                                pm.getLaunchIntentForPackage(
                                    package_name
                                )
                            )

                            if intent:

                                intent.addFlags(
                                    Intent.FLAG_ACTIVITY_NEW_TASK
                                )

                                activity.startActivity(
                                    intent
                                )

                                self.speak(
                                    "WhatsApp khol raha hoon."
                                )

                                return

                    except Exception:
                        continue

                self.speak(
                    "WhatsApp installed nahi mila."
                )

            except Exception as e:

                print(
                    "WhatsApp error:",
                    e
                )

                self.speak(
                    "WhatsApp open nahi ho paya."
                )

        run_on_android_thread(
            do_open
        )


    # ========================================================
    # CALCULATOR
    # ========================================================

    def open_calculator(self):

        packages = [
            "com.miui.calculator",
            "com.google.android.calculator",
            "com.android.calculator2"
        ]

        def do_open():

            try:

                pm = activity.getPackageManager()

                for package_name in packages:

                    try:

                        intent = (
                            pm.getLaunchIntentForPackage(
                                package_name
                            )
                        )

                        if intent:

                            intent.addFlags(
                                Intent.FLAG_ACTIVITY_NEW_TASK
                            )

                            activity.startActivity(
                                intent
                            )

                            self.speak(
                                "Calculator khol raha hoon."
                            )

                            return

                    except Exception:
                        continue

                # Generic calculator fallback
                try:

                    intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    intent.addCategory(
                        Intent.CATEGORY_APP_CALCULATOR
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(
                        intent
                    )

                    self.speak(
                        "Calculator khol raha hoon."
                    )

                    return

                except Exception:
                    pass

                self.speak(
                    "Calculator open nahi ho paya."
                )

            except Exception as e:

                print(
                    "Calculator error:",
                    e
                )

                self.speak(
                    "Calculator open nahi ho paya."
                )

        run_on_android_thread(
            do_open
        )


    # ========================================================
    # CAMERA
    # ========================================================

    def open_camera(self):

        try:

            intent = Intent(
                "android.media.action.IMAGE_CAPTURE"
            )

            self.open_intent(
                intent,
                "Camera khol raha hoon."
            )

        except Exception as e:

            print(
                "Camera error:",
                e
            )

            self.speak(
                "Camera open nahi ho paya."
            )


    # ========================================================
    # CHROME
    # ========================================================

    def open_chrome(self):

        def do_open():

            try:

                pm = activity.getPackageManager()

                intent = (
                    pm.getLaunchIntentForPackage(
                        "com.android.chrome"
                    )
                )

                if intent:

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(
                        intent
                    )

                    self.speak(
                        "Chrome khol raha hoon."
                    )

                    return

                # Browser fallback
                intent = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(
                        "https://www.google.com"
                    )
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(
                    intent
                )

                self.speak(
                    "Browser khol raha hoon."
                )

            except Exception as e:

                print(
                    "Chrome error:",
                    e
                )

                self.speak(
                    "Chrome open nahi ho paya."
                )

        run_on_android_thread(
            do_open
        )


    # ========================================================
    # YOUTUBE APP
    # ========================================================

    def open_youtube(self):

        def do_open():

            try:

                pm = activity.getPackageManager()

                intent = (
                    pm.getLaunchIntentForPackage(
                        "com.google.android.youtube"
                    )
                )

                if intent:

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(
                        intent
                    )

                    self.speak(
                        "YouTube khol raha hoon."
                    )

                    return

                intent = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(
                        "https://www.youtube.com"
                    )
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(
                    intent
                )

                self.speak(
                    "YouTube khol raha hoon."
                )

            except Exception as e:

                print(
                    "YouTube error:",
                    e
                )

                self.speak(
                    "YouTube open nahi ho paya."
                )

        run_on_android_thread(
            do_open
        )


    # ========================================================
    # SETTINGS - MAIN
    # ========================================================

    def open_settings(self):

        intent = Intent(
            Settings.ACTION_SETTINGS
        )

        self.open_intent(
            intent,
            "Settings khol raha hoon."
        )


    # ========================================================
    # WIFI - FIXED
    # ========================================================

    def open_wifi(self):

        try:

            intent = Intent(
                Settings.ACTION_WIFI_SETTINGS
            )

            self.open_intent(
                intent,
                "Wi-Fi settings khol raha hoon.",
                "Wi-Fi settings open nahi ho paya."
            )

        except Exception as e:

            print(
                "Wi-Fi error:",
                e
            )

            self.speak(
                "Wi-Fi settings open nahi ho paya."
            )


    # ========================================================
    # BLUETOOTH
    # ========================================================

    def open_bluetooth(self):

        try:

            intent = Intent(
                Settings.ACTION_BLUETOOTH_SETTINGS
            )

            self.open_intent(
                intent,
                "Bluetooth settings khol raha hoon."
            )

        except Exception as e:

            print(
                "Bluetooth error:",
                e
            )

            self.speak(
                "Bluetooth settings open nahi ho paya."
            )


    # ========================================================
    # DISPLAY
    # ========================================================

    def open_display(self):

        try:

            intent = Intent(
                Settings.ACTION_DISPLAY_SETTINGS
            )

            self.open_intent(
                intent,
                "Display settings khol raha hoon."
            )

        except Exception as e:

            print(
                "Display error:",
                e
            )

            self.speak(
                "Display settings open nahi ho paya."
            )


    # ========================================================
    # BATTERY
    # ========================================================

    def open_battery(self):

        try:

            intent = Intent(
                Settings.ACTION_BATTERY_SAVER_SETTINGS
            )

            self.open_intent(
                intent,
                "Battery settings khol raha hoon."
            )

        except Exception as e:

            print(
                "Battery error:",
                e
            )

            self.speak(
                "Battery settings open nahi ho paya."
            )


    # ========================================================
    # LOCATION
    # ========================================================

    def open_location(self):

        try:

            intent = Intent(
                Settings.ACTION_LOCATION_SOURCE_SETTINGS
            )

            self.open_intent(
                intent,
                "Location settings khol raha hoon."
            )

        except Exception as e:

            print(
                "Location error:",
                e
            )

            self.speak(
                "Location settings open nahi ho paya."
            )


    # ========================================================
    # SECURITY
    # ========================================================

    def open_security(self):

        try:

            intent = Intent(
                Settings.ACTION_SECURITY_SETTINGS
            )

            self.open_intent(
                intent,
                "Security settings khol raha hoon."
            )

        except Exception as e:

            print(
                "Security error:",
                e
            )

            self.speak(
                "Security settings open nahi ho paya."
            )


    # ========================================================
    # MOBILE NETWORK
    # ========================================================

    def open_mobile_network(self):

        try:

            intent = Intent(
                Settings.ACTION_NETWORK_OPERATOR_SETTINGS
            )

            self.open_intent(
                intent,
                "Mobile network settings khol raha hoon."
            )

        except Exception as e:

            print(
                "Mobile network error:",
                e
            )

            self.speak(
                "Mobile network settings open nahi ho paya."
            )


    # ========================================================
    # PHONE / DIALER - v0.21 NEW
    # ========================================================

    def open_phone(self):

        try:

            intent = Intent(
                Intent.ACTION_DIAL
            )

            self.open_intent(
                intent,
                "Phone khol raha hoon.",
                "Phone open nahi ho paya."
            )

        except Exception as e:

            print(
                "Phone error:",
                e
            )

            self.speak(
                "Phone open nahi ho paya."
            )


    # ========================================================
    # CONTACTS - v0.21 NEW
    # ========================================================

    def open_contacts(self):

        def do_open():

            try:

                intent = Intent(
                    Intent.ACTION_VIEW
                )

                intent.setData(
                    ContactsContract.Contacts.CONTENT_URI
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(
                    intent
                )

                self.speak(
                    "Contacts khol raha hoon."
                )

            except Exception as e:

                print(
                    "Contacts error:",
                    e
                )

                # Fallback: generic contacts app
                try:

                    pm = activity.getPackageManager()

                    intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    intent.addCategory(
                        Intent.CATEGORY_APP_CONTACTS
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(
                        intent
                    )

                    self.speak(
                        "Contacts khol raha hoon."
                    )

                except Exception:

                    self.speak(
                        "Contacts open nahi ho paye."
                    )

        run_on_android_thread(
            do_open
        )


    # ========================================================
    # DIAL NUMBER - v0.21 NEW
    # ========================================================

    def dial_number(self, number):

        number = number.strip()

        # Keep only phone-number characters
        cleaned = re.sub(
            r"[^0-9+*#]",
            "",
            number
        )

        if not cleaned:

            self.speak(
                "Phone number samajh nahi aaya."
            )

            Clock.schedule_once(
                self.start_listening,
                1.5
            )

            return

        try:

            intent = Intent(
                Intent.ACTION_DIAL
            )

            intent.setData(
                Uri.parse(
                    "tel:" + cleaned
                )
            )

            self.open_intent(
                intent,
                "Dialer mein number khol raha hoon.",
                "Dialer open nahi ho paya."
            )

        except Exception as e:

            print(
                "Dial number error:",
                e
            )

            self.speak(
                "Number dialer mein open nahi ho paya."
            )


    # ========================================================
    # TIME
    # ========================================================

    def tell_time(self):

        current_time = datetime.now().strftime(
            "%I:%M %p"
        )

        self.speak(
            "Abhi time hai "
            + current_time
        )

        Clock.schedule_once(
            self.start_listening,
            2.0
        )


    # ========================================================
    # DATE
    # ========================================================

    def tell_date(self):

        current_date = datetime.now().strftime(
            "%d %B %Y"
        )

        self.speak(
            "Aaj ki date hai "
            + current_date
        )

        Clock.schedule_once(
            self.start_listening,
            2.0
        )


# ============================================================
# END PART 2
# ============================================================

# ============================================================
# PART 3/3
# INSTALLED APPS + COMMAND PROCESSOR + CLEANUP
# ============================================================


    # ========================================================
    # INSTALLED APPS
    # ========================================================

    def open_installed_app(self, app_name):

        app_name = app_name.strip().lower()

        if not app_name:
            self.speak(
                "Kaunsa app kholna hai?"
            )
            Clock.schedule_once(
                self.start_listening,
                1.5
            )
            return

        def do_open():

            try:

                pm = activity.getPackageManager()

                packages = pm.getInstalledApplications(
                    PackageManager.GET_META_DATA
                )

                exact_match = None
                partial_match = None

                for i in range(
                    packages.size()
                ):

                    try:

                        info = packages.get(i)

                        label = str(
                            pm.getApplicationLabel(
                                info
                            )
                        ).strip()

                        label_lower = (
                            label.lower()
                        )

                        if label_lower == app_name:

                            exact_match = info
                            break

                        if (
                            app_name in label_lower
                            and partial_match is None
                        ):

                            partial_match = info

                    except Exception:
                        continue

                selected = (
                    exact_match
                    if exact_match is not None
                    else partial_match
                )

                if selected is None:

                    self.speak(
                        app_name
                        + " app nahi mila."
                    )

                    return

                package_name = str(
                    selected.packageName
                )

                intent = (
                    pm.getLaunchIntentForPackage(
                        package_name
                    )
                )

                if intent is None:

                    self.speak(
                        app_name
                        + " ko launch nahi kar paya."
                    )

                    return

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(
                    intent
                )

                self.speak(
                    app_name
                    + " khol raha hoon."
                )

            except Exception as e:

                print(
                    "Installed app error:",
                    e
                )

                self.speak(
                    app_name
                    + " open nahi ho paya."
                )

        run_on_android_thread(
            do_open
        )


    # ========================================================
    # REMOVE COMMAND PREFIX
    # ========================================================

    def remove_prefix(
        self,
        text,
        prefixes
    ):

        for prefix in prefixes:

            if text.startswith(prefix):

                return text[
                    len(prefix):
                ].strip()

        return ""


    # ========================================================
    # PROCESS COMMAND
    # ========================================================

    def process_command(self, command):

        original = command

        command = self.normalize_command(
            command
        )

        print(
            "Command:",
            command
        )

        # ----------------------------------------------------
        # EMPTY COMMAND
        # ----------------------------------------------------

        if not command:

            Clock.schedule_once(
                self.start_listening,
                0.5
            )

            return


        # ====================================================
        # GREETINGS
        # ====================================================

        greetings = [
            "hello",
            "hi",
            "hey",
            "namaste",
            "hii",
            "helo"
        ]

        if command in greetings:

            self.speak(
                "Hello! Main tumhara voice assistant hoon."
            )

            Clock.schedule_once(
                self.start_listening,
                2.0
            )

            return


        # ====================================================
        # WHO ARE YOU
        # ====================================================

        if (
            "who are you" in command
            or "tum kaun ho" in command
            or "aap kaun ho" in command
            or "ap kaun ho" in command
            or "tum kon ho" in command
        ):

            self.speak(
                "Main tumhara voice assistant hoon."
            )

            Clock.schedule_once(
                self.start_listening,
                2.0
            )

            return


        # ====================================================
        # NAME
        # ====================================================

        if (
            "your name" in command
            or "tumhara naam" in command
            or "aapka naam" in command
            or "apka naam" in command
        ):

            self.speak(
                "Mera naam My Voice Assistant hai."
            )

            Clock.schedule_once(
                self.start_listening,
                2.0
            )

            return


        # ====================================================
        # TIME
        # ====================================================

        if (
            command == "time"
            or "time batao" in command
            or "time kya hai" in command
            or "kitna time hua" in command
            or "samay batao" in command
        ):

            self.tell_time()
            return


        # ====================================================
        # DATE
        # ====================================================

        if (
            command == "date"
            or "date batao" in command
            or "aaj ki date" in command
            or "aaj kya date hai" in command
            or "tarikh batao" in command
        ):

            self.tell_date()
            return


        # ====================================================
        # WIFI - FIX
        # ====================================================
        # IMPORTANT:
        # This is checked BEFORE generic settings commands.
        #
        # Examples:
        #   open wifi
        #   wifi kholo
        #   wifi khol
        #   wifi open karo
        #   wifi settings kholo
        #   wi-fi kholo
        # ====================================================

        wifi_words = [
            "wifi",
            "wi fi",
            "wi-fi"
        ]

        has_wifi = False

        for wifi_word in wifi_words:

            if wifi_word in command:
                has_wifi = True
                break

        if has_wifi:

            self.open_wifi()
            return


        # ====================================================
        # BLUETOOTH
        # ====================================================

        if (
            "bluetooth" in command
            and (
                "open" in command
                or "khol" in command
                or "setting" in command
            )
        ):

            self.open_bluetooth()
            return


        # ====================================================
        # DISPLAY
        # ====================================================

        if (
            "display" in command
            or "screen setting" in command
            or "display setting" in command
        ):

            self.open_display()
            return


        # ====================================================
        # BATTERY
        # ====================================================

        if (
            "battery" in command
            and (
                "setting" in command
                or "open" in command
                or "khol" in command
            )
        ):

            self.open_battery()
            return


        # ====================================================
        # LOCATION
        # ====================================================

        if (
            "location" in command
            and (
                "setting" in command
                or "open" in command
                or "khol" in command
            )
        ):

            self.open_location()
            return


        # ====================================================
        # SECURITY
        # ====================================================

        if (
            "security" in command
            and (
                "setting" in command
                or "open" in command
                or "khol" in command
            )
        ):

            self.open_security()
            return


        # ====================================================
        # MOBILE NETWORK
        # ====================================================

        if (
            (
                "mobile network" in command
                or "mobile data" in command
                or "data setting" in command
                or "network setting" in command
            )
            and (
                "open" in command
                or "khol" in command
                or "setting" in command
            )
        ):

            self.open_mobile_network()
            return


        # ====================================================
        # MAIN SETTINGS
        # ====================================================

        if (
            command == "settings"
            or command == "setting"
            or command == "settings kholo"
            or command == "setting kholo"
            or command == "settings khol"
            or command == "setting khol"
            or "open settings" in command
            or "settings open karo" in command
        ):

            self.open_settings()
            return


        # ====================================================
        # PHONE / DIALER - v0.21
        # ====================================================

        if (
            command in (
                "phone",
                "phone kholo",
                "phone khol",
                "phone open karo",
                "open phone",
                "dialer",
                "dialer kholo",
                "dialer khol",
                "dialer open karo",
                "open dialer"
            )
        ):

            self.open_phone()
            return


        # ====================================================
        # CONTACTS - v0.21
        # ====================================================

        if (
            command in (
                "contacts",
                "contact",
                "contacts kholo",
                "contact kholo",
                "contacts khol",
                "contact khol",
                "contacts open karo",
                "contact open karo",
                "open contacts",
                "open contact"
            )
        ):

            self.open_contacts()
            return


        # ====================================================
        # CALL / DIAL NUMBER - v0.21
        # ====================================================

        call_prefixes = [
            "call ",
            "dial ",
            "number dial karo ",
            "number call karo ",
            "number milao "
        ]

        for prefix in call_prefixes:

            if command.startswith(prefix):

                number = command[
                    len(prefix):
                ].strip()

                # If speech recognition gives
                # "call 9876543210"
                # this opens the Android Dialer
                # with the number filled in.
                self.dial_number(
                    number
                )

                return


        # ====================================================
        # GOOGLE SEARCH
        # ====================================================

        google_prefixes = [
            "google search ",
            "google pe search ",
            "google par search ",
            "google me search ",
            "search on google ",
            "google kholo aur search "
        ]

        for prefix in google_prefixes:

            if command.startswith(prefix):

                query = command[
                    len(prefix):
                ].strip()

                self.google_search(
                    query
                )

                return


        # ====================================================
        # SIMPLE GOOGLE SEARCH
        # ====================================================

        if command.startswith(
            "search "
        ):

            query = command[
                len("search "):
            ].strip()

            self.google_search(
                query
            )

            return


        # ====================================================
        # YOUTUBE SEARCH
        # ====================================================

        youtube_search_prefixes = [
            "youtube pe search ",
            "youtube par search ",
            "youtube me search ",
            "youtube search ",
            "search on youtube "
        ]

        for prefix in youtube_search_prefixes:

            if command.startswith(prefix):

                query = command[
                    len(prefix):
                ].strip()

                self.youtube_search(
                    query
                )

                return


        # ====================================================
        # MUSIC SEARCH
        # ====================================================

        music_prefixes = [
            "music search ",
            "music me search ",
            "music par search ",
            "music pe search ",
            "song search ",
            "songs search "
        ]

        for prefix in music_prefixes:

            if command.startswith(prefix):

                query = command[
                    len(prefix):
                ].strip()

                self.music_search(
                    query
                )

                return


        # ====================================================
        # WHATSAPP
        # ====================================================

        if (
            command in (
                "whatsapp",
                "whatsapp kholo",
                "whatsapp khol",
                "whatsapp open karo",
                "open whatsapp"
            )
            or "whatsapp kholo" in command
            or "whatsapp khol" in command
        ):

            self.open_whatsapp()
            return


        # ====================================================
        # CALCULATOR
        # ====================================================

        if (
            command in (
                "calculator",
                "calculator kholo",
                "calculator khol",
                "calculator open karo",
                "open calculator"
            )
            or "calculator kholo" in command
            or "calculator khol" in command
        ):

            self.open_calculator()
            return


        # ====================================================
        # CAMERA
        # ====================================================

        if (
            command in (
                "camera",
                "camera kholo",
                "camera khol",
                "camera open karo",
                "open camera"
            )
            or "camera kholo" in command
            or "camera khol" in command
        ):

            self.open_camera()
            return


        # ====================================================
        # CHROME
        # ====================================================

        if (
            command in (
                "chrome",
                "chrome kholo",
                "chrome khol",
                "chrome open karo",
                "open chrome"
            )
            or "chrome kholo" in command
            or "chrome khol" in command
        ):

            self.open_chrome()
            return


        # ====================================================
        # YOUTUBE APP
        # ====================================================

        if (
            command in (
                "youtube",
                "youtube kholo",
                "youtube khol",
                "youtube open karo",
                "open youtube"
            )
            or "youtube kholo" in command
            or "youtube khol" in command
        ):

            self.open_youtube()
            return


        # ====================================================
        # INSTALLED APP COMMAND
        # ====================================================

        app_prefixes = [
            "open app ",
            "open the app ",
            "app open ",
            "app kholo ",
            "app khol ",
            "application kholo ",
            "application khol ",
            "khol do ",
            "kholna "
        ]

        for prefix in app_prefixes:

            if command.startswith(prefix):

                app_name = command[
                    len(prefix):
                ].strip()

                if app_name:

                    self.open_installed_app(
                        app_name
                    )

                    return


        # ====================================================
        # GENERIC "OPEN X" APP COMMAND
        # ====================================================

        if command.startswith(
            "open "
        ):

            target = command[
                len("open "):
            ].strip()

            if target:

                # Known settings/app commands have
                # already been handled above.
                self.open_installed_app(
                    target
                )

                return


        # ====================================================
        # GENERIC "X KHOLO" APP COMMAND
        # ====================================================

        if command.endswith(
            " kholo"
        ):

            target = command[
                :-len(" kholo")
            ].strip()

            if target:

                self.open_installed_app(
                    target
                )

                return


        # ====================================================
        # GENERIC "X KHOL" APP COMMAND
        # ====================================================

        if command.endswith(
            " khol"
        ):

            target = command[
                :-len(" khol")
            ].strip()

            if target:

                self.open_installed_app(
                    target
                )

                return


        # ====================================================
        # UNKNOWN COMMAND
        # ====================================================

        print(
            "Unknown command:",
            original
        )

        self.speak(
            "Command samajh nahi aaya."
        )

        Clock.schedule_once(
            self.start_listening,
            2.0
        )


    # ========================================================
    # APP STOP / CLEANUP
    # ========================================================

    def on_stop(self):

        self.is_stopping = True

        try:

            if self.retry_event is not None:

                self.retry_event.cancel()

        except Exception:
            pass

        def cleanup():

            try:

                if self.speech is not None:

                    try:
                        self.speech.stopListening()
                    except Exception:
                        pass

                    try:
                        self.speech.cancel()
                    except Exception:
                        pass

                    try:
                        self.speech.destroy()
                    except Exception:
                        pass

                    self.speech = None

            except Exception as e:

                print(
                    "Speech cleanup error:",
                    e
                )

            try:

                if self.tts is not None:

                    try:
                        self.tts.stop()
                    except Exception:
                        pass

                    try:
                        self.tts.shutdown()
                    except Exception:
                        pass

                    self.tts = None

            except Exception as e:

                print(
                    "TTS cleanup error:",
                    e
                )

        try:

            run_on_android_thread(
                cleanup
            )

        except Exception:
            pass


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    VoiceAssistantApp().run()


# ============================================================
# v0.21 END
# ============================================================
