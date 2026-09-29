# ============================================================
# MY VOICE ASSISTANT
# VERSION 0.21.1
# BASE: v0.20
# NEW: PHONE + CONTACTS ACTIONS
# FIX: WIFI COMMAND
# ============================================================

import re
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

Intent = autoclass("android.content.Intent")
Settings = autoclass("android.provider.Settings")
Uri = autoclass("android.net.Uri")

SpeechRecognizer = autoclass(
    "android.speech.SpeechRecognizer"
)

RecognizerIntent = autoclass(
    "android.speech.RecognizerIntent"
)

TextToSpeech = autoclass(
    "android.speech.tts.TextToSpeech"
)

Locale = autoclass(
    "java.util.Locale"
)


# ============================================================
# MAIN THREAD RUNNER
# ============================================================

class MainThreadRunnable(PythonJavaClass):

    __javainterfaces__ = [
        "java/lang/Runnable"
    ]

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method("()V")
    def run(self):
        try:
            self.callback()
        except Exception as e:
            print("MainThread error:", e)


def run_on_android_thread(callback):
    activity = PythonActivity.mActivity
    runnable = MainThreadRunnable(callback)
    activity.runOnUiThread(runnable)


# ============================================================
# SPEECH RECOGNITION LISTENER
# ============================================================

class RecognitionListener(PythonJavaClass):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant

    @java_method("()V")
    def onReadyForSpeech(self, params):
        print("Ready for speech")

    @java_method("()V")
    def onBeginningOfSpeech(self):
        print("Listening...")

    @java_method("()V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("()V")
    def onEndOfSpeech(self):
        print("Speech ended")

    @java_method("(I)V")
    def onError(self, error):
        print("Speech error:", error)

        # Error 5 = client error.
        # Silently retry instead of showing an error.
        if error == 5:
            Clock.schedule_once(
                lambda dt: self.assistant.start_listening(),
                0.4
            )
            return

        # Temporary speech errors.
        if error in (6, 7, 8, 9):
            Clock.schedule_once(
                lambda dt: self.assistant.start_listening(),
                0.5
            )
            return

        Clock.schedule_once(
            lambda dt: self.assistant.start_listening(),
            0.8
        )

    @java_method("([Ljava/lang/String;)V")
    def onResults(self, results):
        try:
            if results is None:
                self.assistant.start_listening()
                return

            if results.size() == 0:
                self.assistant.start_listening()
                return

            command = results.get(0)

            if command is None:
                self.assistant.start_listening()
                return

            command = str(command).strip()

            print("Recognized:", command)

            if command:
                self.assistant.process_command(command)
            else:
                self.assistant.start_listening()

        except Exception as e:
            print("Result error:", e)
            self.assistant.start_listening()

    @java_method("([Ljava/lang/String;)V")
    def onPartialResults(self, partial_results):
        pass

    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, event_type, params):
        pass


# ============================================================
# MAIN ASSISTANT
# ============================================================

class VoiceAssistant:

    def __init__(self, app):
        self.app = app

        self.speech_recognizer = None
        self.recognition_listener = None
        self.tts = None

        self.is_listening = False
        self.tts_ready = False

        self.setup_android()


    # ========================================================
    # ANDROID SETUP
    # ========================================================

    def setup_android(self):

        def setup():

            try:
                activity = PythonActivity.mActivity

                # --------------------------------------------
                # TEXT TO SPEECH
                # --------------------------------------------

                def tts_init(status):

                    try:
                        if status == TextToSpeech.SUCCESS:
                            self.tts_ready = True

                            try:
                                self.tts.setLanguage(
                                    Locale.US
                                )
                            except Exception:
                                pass

                            print("TTS ready")

                    except Exception as e:
                        print("TTS setup error:", e)

                self.tts = TextToSpeech(
                    activity,
                    tts_init
                )

                # --------------------------------------------
                # SPEECH RECOGNIZER
                # --------------------------------------------

                self.recognition_listener = (
                    RecognitionListener(self)
                )

                if SpeechRecognizer.isRecognitionAvailable(
                    activity
                ):
                    self.speech_recognizer = (
                        SpeechRecognizer
                        .createSpeechRecognizer(activity)
                    )

                    self.speech_recognizer.setRecognitionListener(
                        self.recognition_listener
                    )

                    print("SpeechRecognizer ready")

                else:
                    print(
                        "Speech recognition is not available"
                    )

                Clock.schedule_once(
                    lambda dt: self.speak(
                        "Voice assistant ready."
                    ),
                    1.0
                )

            except Exception as e:
                print("Android setup error:", e)


        # IMPORTANT:
        # SpeechRecognizer must be created on Android main thread.
        run_on_android_thread(setup)


    # ========================================================
    # TTS
    # ========================================================

    def speak(self, text):

        print("Assistant:", text)

        if self.tts is None:
            return

        def speak_now():

            try:
                self.tts.speak(
                    str(text),
                    TextToSpeech.QUEUE_FLUSH,
                    None,
                    "jarvis"
                )

            except Exception as e:
                print("TTS speak error:", e)

        run_on_android_thread(speak_now)


    # ========================================================
    # START LISTENING
    # ========================================================

    def start_listening(self):

        if self.speech_recognizer is None:
            print("SpeechRecognizer not ready")
            return

        def start():

            try:

                if self.speech_recognizer is None:
                    return

                try:
                    self.speech_recognizer.cancel()
                except Exception:
                    pass

                intent = Intent(
                    RecognizerIntent.ACTION_RECOGNIZE_SPEECH
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE,
                    "en-IN"
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,
                    "en-IN"
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_PARTIAL_RESULTS,
                    False
                )

                intent.putExtra(
                    RecognizerIntent.EXTRA_MAX_RESULTS,
                    3
                )

                self.is_listening = True

                self.speech_recognizer.startListening(
                    intent
                )

                print("Listening started")

            except Exception as e:
                print("Start listening error:", e)

                Clock.schedule_once(
                    lambda dt: self.start_listening(),
                    1.0
                )


        # MAIN THREAD
        run_on_android_thread(start)


    # ========================================================
    # STOP LISTENING
    # ========================================================

    def stop_listening(self):

        if self.speech_recognizer is None:
            return

        def stop():

            try:
                self.speech_recognizer.stopListening()
            except Exception as e:
                print("Stop listening error:", e)

            self.is_listening = False

        run_on_android_thread(stop)


    # ========================================================
    # NORMALIZE COMMAND
    # ========================================================

    def normalize(self, command):

        command = str(command).lower().strip()

        command = command.replace(
            "wi fi",
            "wifi"
        )

        command = command.replace(
            "wi-fi",
            "wifi"
        )

        command = re.sub(
            r"\s+",
            " ",
            command
        )

        return command


    # ========================================================
    # OPEN INTENT
    # ========================================================

    def open_intent(
        self,
        action,
        data=None,
        package_name=None,
        categories=None
    ):

        def open_now():

            try:

                intent = Intent(action)

                if data:
                    intent.setData(
                        Uri.parse(str(data))
                    )

                if package_name:
                    intent.setPackage(
                        package_name
                    )

                if categories:

                    for category in categories:
                        intent.addCategory(
                            category
                        )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                PythonActivity.mActivity.startActivity(
                    intent
                )

                return True

            except Exception as e:
                print(
                    "Open intent error:",
                    e
                )
                return False

        run_on_android_thread(open_now)


    # ========================================================
    # GOOGLE SEARCH
    # ========================================================

    def google_search(self, query):

        query = query.strip()

        if not query:
            self.speak("Google search ke liye kya search karna hai?")
            Clock.schedule_once(
                lambda dt: self.start_listening(),
                1.0
            )
            return

        url = (
            "https://www.google.com/search?q="
            + Uri.encode(query)
        )

        self.speak(
            "Google par search kar raha hoon."
        )

        self.open_intent(
            Intent.ACTION_VIEW,
            url
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
                lambda dt: self.start_listening(),
                1.0
            )
            return

        url = (
            "https://www.youtube.com/results?search_query="
            + Uri.encode(query)
        )

        self.speak(
            "YouTube par search kar raha hoon."
        )

        self.open_intent(
            Intent.ACTION_VIEW,
            url
        )


    # ========================================================
    # MUSIC SEARCH
    # ========================================================

    def music_search(self, query):

        query = query.strip()

        if not query:
            self.speak(
                "Music mein kya search karna hai?"
            )
            Clock.schedule_once(
                lambda dt: self.start_listening(),
                1.0
            )
            return

        url = (
            "https://music.youtube.com/search?q="
            + Uri.encode(query)
        )

        self.speak(
            "Music search kar raha hoon."
        )

        self.open_intent(
            Intent.ACTION_VIEW,
            url
        )

    # ========================================================
    # WHATSAPP
    # ========================================================

    def open_whatsapp(self):

        def open_now():

            try:

                activity = PythonActivity.mActivity

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                intent.setPackage(
                    "com.whatsapp"
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                try:

                    activity.startActivity(intent)

                    self.speak(
                        "WhatsApp khol raha hoon."
                    )

                    return

                except Exception:
                    pass

                # WhatsApp Business fallback

                intent.setPackage(
                    "com.whatsapp.w4b"
                )

                try:

                    activity.startActivity(intent)

                    self.speak(
                        "WhatsApp khol raha hoon."
                    )

                    return

                except Exception:
                    pass

                self.speak(
                    "WhatsApp installed nahi hai."
                )

            except Exception as e:

                print(
                    "WhatsApp error:",
                    e
                )

                self.speak(
                    "WhatsApp open nahi ho saka."
                )

        run_on_android_thread(open_now)


    # ========================================================
    # CALCULATOR
    # ========================================================

    def open_calculator(self):

        def open_now():

            activity = PythonActivity.mActivity

            packages = [
                "com.miui.calculator",
                "com.google.android.calculator",
                "com.android.calculator2"
            ]

            for package_name in packages:

                try:

                    intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    intent.addCategory(
                        Intent.CATEGORY_LAUNCHER
                    )

                    intent.setPackage(
                        package_name
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(intent)

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

                activity.startActivity(intent)

                self.speak(
                    "Calculator khol raha hoon."
                )

                return

            except Exception:
                pass

            self.speak(
                "Calculator open nahi ho saka."
            )


        run_on_android_thread(open_now)


    # ========================================================
    # CAMERA
    # ========================================================

    def open_camera(self):

        self.speak(
            "Camera khol raha hoon."
        )

        self.open_intent(
            "android.media.action.IMAGE_CAPTURE"
        )


    # ========================================================
    # CHROME
    # ========================================================

    def open_chrome(self):

        def open_now():

            try:

                activity = PythonActivity.mActivity

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                intent.setPackage(
                    "com.android.chrome"
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                try:

                    activity.startActivity(intent)

                    self.speak(
                        "Chrome khol raha hoon."
                    )

                    return

                except Exception:
                    pass

                # Fallback browser

                intent = Intent(
                    Intent.ACTION_VIEW
                )

                intent.setData(
                    Uri.parse(
                        "https://www.google.com"
                    )
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(intent)

                self.speak(
                    "Browser khol raha hoon."
                )

            except Exception as e:

                print(
                    "Chrome error:",
                    e
                )

                self.speak(
                    "Chrome open nahi ho saka."
                )


        run_on_android_thread(open_now)


    # ========================================================
    # YOUTUBE APP
    # ========================================================

    def open_youtube(self):

        def open_now():

            try:

                activity = PythonActivity.mActivity

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                intent.setPackage(
                    "com.google.android.youtube"
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                try:

                    activity.startActivity(intent)

                    self.speak(
                        "YouTube khol raha hoon."
                    )

                    return

                except Exception:
                    pass

                intent = Intent(
                    Intent.ACTION_VIEW
                )

                intent.setData(
                    Uri.parse(
                        "https://www.youtube.com"
                    )
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(intent)

                self.speak(
                    "YouTube khol raha hoon."
                )

            except Exception as e:

                print(
                    "YouTube error:",
                    e
                )

                self.speak(
                    "YouTube open nahi ho saka."
                )


        run_on_android_thread(open_now)


    # ========================================================
    # PHONE / DIALER
    # ========================================================

    def open_phone(self):

        def open_now():

            try:

                intent = Intent(
                    Intent.ACTION_DIAL
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                PythonActivity.mActivity.startActivity(
                    intent
                )

                self.speak(
                    "Dialer khol raha hoon."
                )

            except Exception as e:

                print(
                    "Phone error:",
                    e
                )

                self.speak(
                    "Dialer open nahi ho saka."
                )


        run_on_android_thread(open_now)


    # ========================================================
    # DIAL NUMBER
    # ========================================================

    def dial_number(self, number):

        number = re.sub(
            r"[^0-9+]",
            "",
            number
        )

        if not number:
            self.speak(
                "Number samajh nahi aaya."
            )

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                1.0
            )

            return

        def open_now():

            try:

                intent = Intent(
                    Intent.ACTION_DIAL
                )

                intent.setData(
                    Uri.parse(
                        "tel:" + number
                    )
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                PythonActivity.mActivity.startActivity(
                    intent
                )

                self.speak(
                    "Number dialer mein khol raha hoon."
                )

            except Exception as e:

                print(
                    "Dial number error:",
                    e
                )

                self.speak(
                    "Number dialer mein open nahi ho saka."
                )


        run_on_android_thread(open_now)


    # ========================================================
    # CONTACTS
    # ========================================================

    def open_contacts(self):

        def open_now():

            try:

                activity = PythonActivity.mActivity

                # ContactsContract is deliberately loaded
                # ONLY when Contacts is requested.
                # This avoids unnecessary startup class loading.

                try:

                    ContactsContract = autoclass(
                        "android.provider.ContactsContract"
                    )

                    intent = Intent(
                        Intent.ACTION_VIEW
                    )

                    intent.setData(
                        ContactsContract.Contacts.CONTENT_URI
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(intent)

                    self.speak(
                        "Contacts khol raha hoon."
                    )

                    return

                except Exception as e:

                    print(
                        "ContactsContract error:",
                        e
                    )

                # Fallback

                try:

                    intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    intent.addCategory(
                        Intent.CATEGORY_APP_CONTACTS
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    activity.startActivity(intent)

                    self.speak(
                        "Contacts khol raha hoon."
                    )

                    return

                except Exception:
                    pass

                self.speak(
                    "Contacts open nahi ho sake."
                )

            except Exception as e:

                print(
                    "Contacts error:",
                    e
                )

                self.speak(
                    "Contacts open nahi ho sake."
                )


        run_on_android_thread(open_now)


    # ========================================================
    # WIFI
    # ========================================================

    def open_wifi(self):

        self.speak(
            "Wi-Fi settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_WIFI_SETTINGS
        )


    # ========================================================
    # BLUETOOTH
    # ========================================================

    def open_bluetooth(self):

        self.speak(
            "Bluetooth settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_BLUETOOTH_SETTINGS
        )


    # ========================================================
    # DISPLAY
    # ========================================================

    def open_display(self):

        self.speak(
            "Display settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_DISPLAY_SETTINGS
        )


    # ========================================================
    # BATTERY
    # ========================================================

    def open_battery(self):

        self.speak(
            "Battery settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_BATTERY_SAVER_SETTINGS
        )


    # ========================================================
    # LOCATION
    # ========================================================

    def open_location(self):

        self.speak(
            "Location settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_LOCATION_SOURCE_SETTINGS
        )


    # ========================================================
    # SECURITY
    # ========================================================

    def open_security(self):

        self.speak(
            "Security settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_SECURITY_SETTINGS
        )


    # ========================================================
    # MOBILE NETWORK
    # ========================================================

    def open_mobile_network(self):

        self.speak(
            "Mobile network settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_NETWORK_OPERATOR_SETTINGS
        )


    # ========================================================
    # MAIN SETTINGS
    # ========================================================

    def open_settings(self):

        self.speak(
            "Settings khol raha hoon."
        )

        self.open_intent(
            Settings.ACTION_SETTINGS
                )

    # ========================================================
    # INSTALLED APP LAUNCHER
    # ========================================================

    def open_installed_app(self, app_name):

        app_name = app_name.strip().lower()

        if not app_name:
            self.speak(
                "Kaunsa app kholna hai?"
            )
            return

        def open_now():

            try:

                activity = PythonActivity.mActivity

                # Lazy loading:
                # PackageManager is needed only when
                # searching for an installed application.

                PackageManager = autoclass(
                    "android.content.pm.PackageManager"
                )

                pm = activity.getPackageManager()

                packages = pm.getInstalledApplications(
                    PackageManager.GET_META_DATA
                )

                found_package = None
                found_label = None

                for info in packages:

                    try:

                        label = str(
                            pm.getApplicationLabel(info)
                        )

                        package_name = str(
                            info.packageName
                        )

                        label_lower = label.lower()

                        if (
                            app_name == label_lower
                            or app_name in label_lower
                        ):
                            found_package = package_name
                            found_label = label
                            break

                    except Exception:
                        continue

                if found_package is None:

                    self.speak(
                        app_name
                        + " app nahi mila."
                    )

                    return

                launch_intent = (
                    pm.getLaunchIntentForPackage(
                        found_package
                    )
                )

                if launch_intent is None:

                    self.speak(
                        found_label
                        + " launch nahi ho sakta."
                    )

                    return

                launch_intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                activity.startActivity(
                    launch_intent
                )

                self.speak(
                    found_label
                    + " khol raha hoon."
                )

            except Exception as e:

                print(
                    "Installed app error:",
                    e
                )

                self.speak(
                    "App open nahi ho saka."
                )


        run_on_android_thread(open_now)


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


    # ========================================================
    # DATE
    # ========================================================

    def tell_date(self):

        current_date = datetime.now().strftime(
            "%d %B %Y"
        )

        self.speak(
            "Aaj "
            + current_date
        )


    # ========================================================
    # GREETING
    # ========================================================

    def greeting(self):

        self.speak(
            "Hello. Main tumhara voice assistant hoon."
        )


    # ========================================================
    # NAME
    # ========================================================

    def tell_name(self):

        self.speak(
            "Mera naam My Voice Assistant hai."
        )


    # ========================================================
    # COMMAND PROCESSOR
    # ========================================================

    def process_command(self, command):

        command = self.normalize(command)

        print(
            "Processing command:",
            command
        )

        # ----------------------------------------------------
        # EMPTY COMMAND
        # ----------------------------------------------------

        if not command:

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                0.5
            )

            return


        # ----------------------------------------------------
        # GREETINGS
        # ----------------------------------------------------

        if command in (
            "hello",
            "hi",
            "hey",
            "hello assistant",
            "hi assistant",
            "hey assistant",
            "namaste"
        ):

            self.greeting()

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                2.0
            )

            return


        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if (
            "what is your name" in command
            or "what's your name" in command
            or "your name" in command
            or "tumhara naam" in command
            or "aapka naam" in command
            or "apna naam" in command
        ):

            self.tell_name()

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                2.0
            )

            return


        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        if (
            command == "time"
            or "time batao" in command
            or "time bata" in command
            or "what is the time" in command
            or "what's the time" in command
            or "current time" in command
        ):

            self.tell_time()

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                2.0
            )

            return


        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        if (
            command == "date"
            or "date batao" in command
            or "date bata" in command
            or "today date" in command
            or "what is today's date" in command
            or "what is the date" in command
        ):

            self.tell_date()

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                2.0
            )

            return


        # ----------------------------------------------------
        # WIFI
        # ----------------------------------------------------

        if (
            "wifi" in command
            or "wi fi" in command
            or "wi-fi" in command
        ):

            self.open_wifi()

            return


        # ----------------------------------------------------
        # BLUETOOTH
        # ----------------------------------------------------

        if (
            "bluetooth" in command
            or "blue tooth" in command
        ):

            self.open_bluetooth()

            return


        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        if (
            "display settings" in command
            or "display setting" in command
            or "display kholo" in command
            or "display khol" in command
        ):

            self.open_display()

            return


        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        if (
            "battery settings" in command
            or "battery setting" in command
            or "battery kholo" in command
            or "battery khol" in command
        ):

            self.open_battery()

            return


        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        if (
            "location settings" in command
            or "location setting" in command
            or "location kholo" in command
            or "location khol" in command
        ):

            self.open_location()

            return


        # ----------------------------------------------------
        # SECURITY
        # ----------------------------------------------------

        if (
            "security settings" in command
            or "security setting" in command
            or "security kholo" in command
            or "security khol" in command
        ):

            self.open_security()

            return


        # ----------------------------------------------------
        # MOBILE NETWORK
        # ----------------------------------------------------

        if (
            "mobile network" in command
            or "mobile data settings" in command
            or "mobile data setting" in command
            or "network settings" in command
        ):

            self.open_mobile_network()

            return


        # ----------------------------------------------------
        # MAIN SETTINGS
        # ----------------------------------------------------

        if (
            command == "settings"
            or "settings kholo" in command
            or "settings khol" in command
            or "open settings" in command
        ):

            self.open_settings()

            return


        # ----------------------------------------------------
        # PHONE / DIALER
        # ----------------------------------------------------

        if (
            "dialer kholo" in command
            or "dialer khol" in command
            or "phone kholo" in command
            or "phone khol" in command
            or "open phone" in command
            or "open dialer" in command
            or command == "phone"
            or command == "dialer"
        ):

            self.open_phone()

            return


        # ----------------------------------------------------
        # CONTACTS
        # ----------------------------------------------------

        if (
            "contacts kholo" in command
            or "contacts khol" in command
            or "contact kholo" in command
            or "contact khol" in command
            or "open contacts" in command
            or "open contact" in command
            or command == "contacts"
            or command == "contact"
        ):

            self.open_contacts()

            return


        # ----------------------------------------------------
        # CALL / DIAL NUMBER
        # ----------------------------------------------------

        if (
            command.startswith("call ")
            or command.startswith("dial ")
            or command.startswith("phone ")
        ):

            if command.startswith("call "):
                number = command[5:].strip()

            elif command.startswith("dial "):
                number = command[5:].strip()

            else:
                number = command[6:].strip()

            # Remove common spoken separators
            number = number.replace(
                " ",
                ""
            )

            number = number.replace(
                "-",
                ""
            )

            number = number.replace(
                "(",
                ""
            )

            number = number.replace(
                ")",
                ""
            )

            self.dial_number(number)

            return


        # ----------------------------------------------------
        # WHATSAPP
        # ----------------------------------------------------

        if (
            "whatsapp kholo" in command
            or "whatsapp khol" in command
            or "open whatsapp" in command
            or command == "whatsapp"
        ):

            self.open_whatsapp()

            return


        # ----------------------------------------------------
        # CALCULATOR
        # ----------------------------------------------------

        if (
            "calculator kholo" in command
            or "calculator khol" in command
            or "open calculator" in command
            or command == "calculator"
        ):

            self.open_calculator()

            return


        # ----------------------------------------------------
        # CAMERA
        # ----------------------------------------------------

        if (
            "camera kholo" in command
            or "camera khol" in command
            or "open camera" in command
            or command == "camera"
        ):

            self.open_camera()

            return


        # ----------------------------------------------------
        # CHROME
        # ----------------------------------------------------

        if (
            "chrome kholo" in command
            or "chrome khol" in command
            or "open chrome" in command
            or command == "chrome"
        ):

            self.open_chrome()

            return


        # ----------------------------------------------------
        # YOUTUBE APP
        # ----------------------------------------------------

        if (
            command == "youtube"
            or "youtube kholo" in command
            or "youtube khol" in command
            or "open youtube" in command
        ):

            self.open_youtube()

            return


        # ----------------------------------------------------
        # GOOGLE SEARCH
        # ----------------------------------------------------

        google_match = re.search(
            r"(?:google|search google|google par search)"
            r"(?:\s+par)?\s+(?:search\s+)?(?:karo|kar)?\s*(.+)",
            command
        )

        if google_match:

            query = google_match.group(1).strip()

            if query:
                self.google_search(query)
                return


        # ----------------------------------------------------
        # YOUTUBE SEARCH
        # ----------------------------------------------------

        youtube_match = re.search(
            r"youtube(?:\s+par|\s+pe)?\s+"
            r"(?:search\s+)?(?:karo|kar)?\s*(.+)",
            command
        )

        if youtube_match:

            query = youtube_match.group(1).strip()

            if query:

                self.youtube_search(query)

                return


        # ----------------------------------------------------
        # MUSIC SEARCH
        # ----------------------------------------------------

        music_match = re.search(
            r"(?:music|song)"
            r"(?:\s+search)?"
            r"(?:\s+karo|\s+kar)?\s+(.+)",
            command
        )

        if music_match:

            query = music_match.group(1).strip()

            if query:

                self.music_search(query)

                return


        # ----------------------------------------------------
        # INSTALLED APP
        # ----------------------------------------------------

        app_patterns = [
            "open ",
            "khol ",
            "kholna ",
            "kholo "
        ]

        for pattern in app_patterns:

            if command.startswith(pattern):

                app_name = command[
                    len(pattern):
                ].strip()

                known_non_app_words = (
                    "settings",
                    "phone",
                    "dialer",
                    "contacts",
                    "contact",
                    "wifi",
                    "bluetooth",
                    "camera",
                    "chrome",
                    "youtube",
                    "whatsapp",
                    "calculator"
                )

                if app_name and app_name not in known_non_app_words:

                    self.open_installed_app(
                        app_name
                    )

                    return


        # ----------------------------------------------------
        # UNKNOWN COMMAND
        # ----------------------------------------------------

        self.speak(
            "Command samajh nahi aaya."
        )

        Clock.schedule_once(
            lambda dt: self.start_listening(),
            1.5
        )


    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self):

        def cleanup_now():

            try:

                if self.speech_recognizer:

                    try:
                        self.speech_recognizer.cancel()
                    except Exception:
                        pass

                    try:
                        self.speech_recognizer.destroy()
                    except Exception:
                        pass

                    self.speech_recognizer = None

            except Exception as e:

                print(
                    "Speech cleanup error:",
                    e
                )

            try:

                if self.tts:

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


        run_on_android_thread(cleanup_now)


# ============================================================
# KIVY APP
# ============================================================

class MyVoiceAssistantApp(App):

    def build(self):

        layout = BoxLayout(
            orientation="vertical"
        )

        self.status_label = Label(
            text="My Voice Assistant\n\nStarting...",
            halign="center",
            valign="middle"
        )

        self.status_label.bind(
            size=self.status_label.setter(
                "text_size"
            )
        )

        layout.add_widget(
            self.status_label
        )

        self.assistant = VoiceAssistant(
            self
        )

        return layout


    def on_start(self):

        Clock.schedule_once(
            lambda dt: self.assistant.start_listening(),
            3.0
        )


    def on_stop(self):

        try:
            self.assistant.cleanup()
        except Exception as e:
            print(
                "App cleanup error:",
                e
            )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    MyVoiceAssistantApp().run()
