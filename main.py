from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

from jnius import autoclass, PythonJavaClass, java_method


# ============================================================
# ANDROID CLASSES
# ============================================================

PythonActivity = autoclass(
    "org.kivy.android.PythonActivity"
)

Intent = autoclass(
    "android.content.Intent"
)

Settings = autoclass(
    "android.provider.Settings"
)

Uri = autoclass(
    "android.net.Uri"
)

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
# ANDROID MAIN THREAD RUNNER
# ============================================================

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


# ============================================================
# SPEECH RECOGNITION LISTENER
# ============================================================

class RecognitionListener(PythonJavaClass):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    __javacontext__ = "app"

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):
        pass

    @java_method("()V")
    def onBeginningOfSpeech(self):
        pass

    @java_method("(F)V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("()V")
    def onEndOfSpeech(self):
        pass

    @java_method("(I)V")
    def onError(self, error):

        # ERROR_CLIENT
        # Is error ko screen par nahi dikhana.
        if error == 5:
            Clock.schedule_once(
                lambda dt: self.assistant.listen_again(),
                0.4
            )
            return

        # Temporary recognition errors
        if error in (
            1, 2, 3, 4, 6, 7,
            8, 9, 10, 11, 12, 13
        ):
            Clock.schedule_once(
                lambda dt: self.assistant.listen_again(),
                0.6
            )

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):

        try:

            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )

            if matches is not None:

                if matches.size() > 0:

                    command = str(
                        matches.get(0)
                    ).strip()

                    if command:

                        self.assistant.process_command(
                            command
                        )

                        return

        except Exception:
            pass

        Clock.schedule_once(
            lambda dt: self.assistant.listen_again(),
            0.5
        )

    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, results):
        pass

    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, eventType, params):
        pass


# ============================================================
# VOICE ASSISTANT APP
# ============================================================

class VoiceAssistant(App):

    def build(self):

        self.label = Label(
            text=(
                "JARVIS v0.18\n"
                "Starting..."
            ),
            font_size="22sp"
        )

        self.tts = None
        self.speech_recognizer = None
        self.recognition_listener = None
        self.listening = False

        Clock.schedule_once(
            self.start_setup_on_android_main_thread,
            0.5
        )

        return self.label

    # ========================================================
    # START SETUP ON ANDROID MAIN THREAD
    # ========================================================

    def start_setup_on_android_main_thread(
        self,
        dt
    ):

        try:

            activity = PythonActivity.mActivity

            runnable = MainThreadRunnable(
                self.setup_speech_and_tts
            )

            activity.runOnUiThread(
                runnable
            )

        except Exception as e:

            self.label.text = (
                "Setup Error:\n" +
                str(e)
            )

    # ========================================================
    # SPEECH + TTS SETUP
    # ========================================================

    def setup_speech_and_tts(self):

        try:

            activity = PythonActivity.mActivity

            # ------------------------------------------------
            # TEXT TO SPEECH
            # ------------------------------------------------

            self.tts = TextToSpeech(
                activity,
                None
            )

            self.tts.setLanguage(
                Locale.US
            )

            # ------------------------------------------------
            # SPEECH RECOGNIZER
            # ------------------------------------------------

            self.speech_recognizer = (
                SpeechRecognizer.createSpeechRecognizer(
                    activity
                )
            )

            self.recognition_listener = (
                RecognitionListener(self)
            )

            self.speech_recognizer.setRecognitionListener(
                self.recognition_listener
            )

            self.label.text = (
                "JARVIS v0.18\n"
                "Ready...\n"
                "Bolkar command dein."
            )

            Clock.schedule_once(
                lambda dt: self.speak(
                    "Hello! Main Jarvis hoon. "
                    "Aapki madad ke liye ready hoon."
                ),
                0.5
            )

            Clock.schedule_once(
                lambda dt: self.start_listening(),
                2.5
            )

        except Exception as e:

            self.label.text = (
                "Speech/TTS Setup Error:\n" +
                str(e)
            )

    # ========================================================
    # TEXT TO SPEECH
    # ========================================================

    def speak(self, text):

        try:

            if self.tts is not None:

                self.tts.speak(
                    text,
                    TextToSpeech.QUEUE_FLUSH,
                    None
                )

        except Exception:
            pass

    # ========================================================
    # START LISTENING REQUEST
    # ========================================================

    def start_listening(self):

        try:

            if self.speech_recognizer is None:
                return

            activity = PythonActivity.mActivity

            runnable = MainThreadRunnable(
                self._start_listening_main
            )

            activity.runOnUiThread(
                runnable
            )

        except Exception:
            pass

    # ========================================================
    # START LISTENING
    # ========================================================

    def _start_listening_main(self):

        try:

            if self.speech_recognizer is None:
                return

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
                3
            )

            self.listening = True

            self.speech_recognizer.startListening(
                intent
            )

        except Exception:

            self.listening = False

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                0.7
            )

    # ========================================================
    # LISTEN AGAIN
    # ========================================================

    def listen_again(self):

        if self.speech_recognizer is None:
            return

        self.start_listening()

    # ========================================================
    # STOP LISTENING
    # ========================================================

    def stop_listening(self):

        try:

            self.listening = False

            if self.speech_recognizer is not None:

                self.speech_recognizer.cancel()

                self.speech_recognizer.stopListening()

        except Exception:
            pass

    # ========================================================
    # OPEN INTENT
    # ========================================================

    def open_intent(self, action):

        try:

            activity = PythonActivity.mActivity

            intent = Intent(action)

            activity.startActivity(intent)

            return True

        except Exception:

            return False

    # ========================================================
    # OPEN URL
    # ========================================================

    def open_url(self, url):

        try:

            activity = PythonActivity.mActivity

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            activity.startActivity(intent)

            return True

        except Exception:

            return False

    # ========================================================
    # YOUTUBE
    # ========================================================

    def open_youtube(self):

        if self.open_url(
            "https://www.youtube.com"
        ):

            self.speak(
                "YouTube khol raha hoon."
            )

            return True

        self.speak(
            "YouTube nahi khul paya."
        )

        return False

    # ========================================================
    # CALCULATOR
    # ========================================================

    def open_calculator(self):

        try:

            activity = PythonActivity.mActivity

            package_manager = (
                activity.getPackageManager()
            )

            packages = (
                package_manager.getInstalledPackages(0)
            )

            calculator_packages = [
                "com.google.android.calculator",
                "com.miui.calculator",
                "com.android.calculator2"
            ]

            for i in range(
                packages.size()
            ):

                package_info = packages.get(i)

                package_name = str(
                    package_info.packageName
                )

                if package_name in calculator_packages:

                    launch_intent = (
                        package_manager
                        .getLaunchIntentForPackage(
                            package_name
                        )
                    )

                    if launch_intent is not None:

                        activity.startActivity(
                            launch_intent
                        )

                        self.speak(
                            "Calculator khol raha hoon."
                        )

                        return True

        except Exception:
            pass

        if self.open_url(
            "https://www.google.com/search?q=calculator"
        ):

            self.speak(
                "Calculator khol raha hoon."
            )

            return True

        self.speak(
            "Calculator nahi khul paya."
        )

        return False

    # ========================================================
    # CAMERA
    # ========================================================

    def open_camera(self):

        if self.open_intent(
            "android.media.action.IMAGE_CAPTURE"
        ):

            self.speak(
                "Camera khol raha hoon."
            )

            return True

        self.speak(
            "Camera nahi khul paya."
        )

        return False

    # ========================================================
    # CHROME
    # ========================================================

    def open_chrome(self):

        try:

            activity = PythonActivity.mActivity

            package_manager = (
                activity.getPackageManager()
            )

            launch_intent = (
                package_manager
                .getLaunchIntentForPackage(
                    "com.android.chrome"
                )
            )

            if launch_intent is not None:

                activity.startActivity(
                    launch_intent
                )

                self.speak(
                    "Chrome khol raha hoon."
                )

                return True

        except Exception:
            pass

        if self.open_url(
            "https://www.google.com"
        ):

            self.speak(
                "Browser khol raha hoon."
            )

            return True

        self.speak(
            "Chrome nahi khul paya."
        )

        return False

    # ========================================================
    # WHATSAPP
    # ========================================================

    def open_whatsapp(self):

        try:

            activity = PythonActivity.mActivity

            package_manager = (
                activity.getPackageManager()
            )

            launch_intent = (
                package_manager
                .getLaunchIntentForPackage(
                    "com.whatsapp"
                )
            )

            if launch_intent is not None:

                activity.startActivity(
                    launch_intent
                )

                self.speak(
                    "WhatsApp khol raha hoon."
                )

                return True

        except Exception:
            pass

        self.speak(
            "WhatsApp nahi khul paya."
        )

        return False

    # ========================================================
    # MAIN SETTINGS
    # ========================================================

    def open_main_settings(self):

        if self.open_intent(
            Settings.ACTION_SETTINGS
        ):

            self.speak(
                "Settings khol raha hoon."
            )

            return True

        self.speak(
            "Settings nahi khul paya."
        )

        return False

    # ========================================================
    # WIFI SETTINGS
    # ========================================================

    def open_wifi_settings(self):

        if self.open_intent(
            Settings.ACTION_WIFI_SETTINGS
        ):

            self.speak(
                "Wi-Fi settings khol raha hoon."
            )

            return True

        self.speak(
            "Wi-Fi settings nahi khul payi."
        )

        return False

    # ========================================================
    # BLUETOOTH SETTINGS
    # ========================================================

    def open_bluetooth_settings(self):

        if self.open_intent(
            Settings.ACTION_BLUETOOTH_SETTINGS
        ):

            self.speak(
                "Bluetooth settings khol raha hoon."
            )

            return True

        self.speak(
            "Bluetooth settings nahi khul payi."
        )

        return False

    # ========================================================
    # DISPLAY SETTINGS
    # ========================================================

    def open_display_settings(self):

        if self.open_intent(
            Settings.ACTION_DISPLAY_SETTINGS
        ):

            self.speak(
                "Display settings khol raha hoon."
            )

            return True

        self.speak(
            "Display settings nahi khul payi."
        )

        return False

    # ========================================================
    # BATTERY SETTINGS
    # ========================================================

    def open_battery_settings(self):

        if self.open_intent(
            Settings.ACTION_BATTERY_SAVER_SETTINGS
        ):

            self.speak(
                "Battery settings khol raha hoon."
            )

            return True

        if self.open_intent(
            Settings.ACTION_BATTERY_SETTINGS
        ):

            self.speak(
                "Battery settings khol raha hoon."
            )

            return True

        self.speak(
            "Battery settings nahi khul payi."
        )

        return False

    # ========================================================
    # LOCATION SETTINGS
    # ========================================================

    def open_location_settings(self):

        if self.open_intent(
            Settings.ACTION_LOCATION_SOURCE_SETTINGS
        ):

            self.speak(
                "Location settings khol raha hoon."
            )

            return True

        self.speak(
            "Location settings nahi khul payi."
        )

        return False

    # ========================================================
    # SECURITY SETTINGS
    # ========================================================

    def open_security_settings(self):

        if self.open_intent(
            Settings.ACTION_SECURITY_SETTINGS
        ):

            self.speak(
                "Security settings khol raha hoon."
            )

            return True

        self.speak(
            "Security settings nahi khul payi."
        )

        return False

    # ========================================================
    # MOBILE NETWORK / DATA SETTINGS
    # ========================================================

    def open_mobile_network_settings(self):

        activity = PythonActivity.mActivity

        actions = [
            "android.settings.MOBILE_NETWORK_SETTINGS",
            "android.settings.NETWORK_OPERATOR_SETTINGS",
            "android.settings.DATA_ROAMING_SETTINGS"
        ]

        for action in actions:

            try:

                intent = Intent(action)

                activity.startActivity(intent)

                self.speak(
                    "Mobile Network settings "
                    "khol raha hoon."
                )

                return True

            except Exception:
                continue

        self.speak(
            "Mobile Network settings "
            "available nahi hai."
        )

        return False
    # ========================================================
    # INSTALLED APPS - MAIN FUNCTION
    # ========================================================

    def open_installed_app(self, app_name):

        try:

            activity = PythonActivity.mActivity

            package_manager = (
                activity.getPackageManager()
            )

            # ------------------------------------------------
            # Launcher applications ki list
            # ------------------------------------------------

            launcher_intent = Intent(
                Intent.ACTION_MAIN
            )

            launcher_intent.addCategory(
                Intent.CATEGORY_LAUNCHER
            )

            activities = (
                package_manager.queryIntentActivities(
                    launcher_intent,
                    0
                )
            )

            if activities is None:
                self.speak(
                    "Installed app nahi mili."
                )
                return False

            wanted_name = (
                app_name
                .strip()
                .lower()
            )

            # Extra words remove karna
            removable_words = [
                "app",
                "application",
                "ko",
                "please",
                "the"
            ]

            words = wanted_name.split()

            clean_words = []

            for word in words:

                if word not in removable_words:
                    clean_words.append(word)

            wanted_name = " ".join(
                clean_words
            ).strip()

            exact_package = None
            partial_package = None
            package_by_name = None

            # ------------------------------------------------
            # Installed apps ko search karo
            # ------------------------------------------------

            for i in range(
                activities.size()
            ):

                try:

                    resolve_info = (
                        activities.get(i)
                    )

                    activity_info = (
                        resolve_info.activityInfo
                    )

                    if activity_info is None:
                        continue

                    package_name = str(
                        activity_info.packageName
                    )

                    label = str(
                        activity_info.loadLabel(
                            package_manager
                        )
                    )

                    label_lower = (
                        label.lower().strip()
                    )

                    package_lower = (
                        package_name.lower()
                    )

                    # ----------------------------------------
                    # Exact app name
                    # ----------------------------------------

                    if label_lower == wanted_name:

                        exact_package = (
                            package_name
                        )

                        break

                    # ----------------------------------------
                    # App name ke andar match
                    # ----------------------------------------

                    if (
                        wanted_name
                        and wanted_name in label_lower
                    ):

                        if partial_package is None:

                            partial_package = (
                                package_name
                            )

                    # ----------------------------------------
                    # Package name match
                    # ----------------------------------------

                    if (
                        wanted_name
                        and wanted_name in package_lower
                    ):

                        if package_by_name is None:

                            package_by_name = (
                                package_name
                            )

                except Exception:
                    continue

            # ------------------------------------------------
            # Match select karo
            # ------------------------------------------------

            selected_package = None

            if exact_package is not None:

                selected_package = (
                    exact_package
                )

            elif partial_package is not None:

                selected_package = (
                    partial_package
                )

            elif package_by_name is not None:

                selected_package = (
                    package_by_name
                )

            # ------------------------------------------------
            # App nahi mili
            # ------------------------------------------------

            if selected_package is None:

                self.speak(
                    app_name +
                    " app nahi mili."
                )

                Clock.schedule_once(
                    lambda dt: self.listen_again(),
                    1.5
                )

                return False

            # ------------------------------------------------
            # Launch intent
            # ------------------------------------------------

            launch_intent = (
                package_manager
                .getLaunchIntentForPackage(
                    selected_package
                )
            )

            if launch_intent is None:

                self.speak(
                    app_name +
                    " ko open nahi kar paya."
                )

                Clock.schedule_once(
                    lambda dt: self.listen_again(),
                    1.5
                )

                return False

            # ------------------------------------------------
            # App launch
            # ------------------------------------------------

            activity.startActivity(
                launch_intent
            )

            self.speak(
                app_name +
                " khol raha hoon."
            )

            return True

        except Exception:

            self.speak(
                app_name +
                " app open nahi ho payi."
            )

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                1.5
            )

            return False

    # ========================================================
    # FIND APP NAME FROM NATURAL COMMAND
    # ========================================================

    def extract_app_name(self, command):

        command = command.strip().lower()

        prefixes = [
            "app kholo ",
            "app khol ",
            "application kholo ",
            "application khol ",
            "open app ",
            "open application ",
            "app open karo ",
            "app open kar ",
            "application open karo ",
            "application open kar "
        ]

        for prefix in prefixes:

            if command.startswith(prefix):

                name = command[
                    len(prefix):
                ].strip()

                if name:
                    return name

        suffixes = [
            " kholo",
            " khol",
            " open karo",
            " open kar",
            " ko kholo",
            " ko khol",
            " ko open karo",
            " ko open kar"
        ]

        for suffix in suffixes:

            if command.endswith(suffix):

                name = command[
                    :-len(suffix)
                ].strip()

                if name:
                    return name

        return None

    # ========================================================
    # NATURAL INSTALLED APP COMMAND
    # ========================================================

    def try_open_natural_app(self, command):

        # ----------------------------------------------------
        # Known non-app commands ko yahan ignore karo
        # ----------------------------------------------------

        blocked_words = [
            "settings",
            "setting",
            "mobile network",
            "mobile data",
            "wifi",
            "wi-fi",
            "bluetooth",
            "display",
            "battery",
            "location",
            "security",
            "calculator",
            "camera",
            "youtube",
            "chrome",
            "whatsapp"
        ]

        for word in blocked_words:

            if word in command:
                return False

        # ----------------------------------------------------
        # App name command se nikalo
        # ----------------------------------------------------

        app_name = self.extract_app_name(
            command
        )

        if app_name:

            return self.open_installed_app(
                app_name
            )

        # ----------------------------------------------------
        # Direct natural command:
        #
        # Instagram kholo
        # Instagram khol
        # Instagram open karo
        # Instagram open kar
        # ----------------------------------------------------

        endings = [
            " kholo",
            " khol",
            " open karo",
            " open kar"
        ]

        for ending in endings:

            if command.endswith(ending):

                app_name = command[
                    :-len(ending)
                ].strip()

                if app_name:

                    return self.open_installed_app(
                        app_name
                    )

        return False

    # ========================================================
    # PROCESS COMMAND
    # ========================================================

    def process_command(self, command):

        command = (
            command
            .lower()
            .strip()
        )

        self.label.text = (
            "JARVIS v0.18\n"
            "Maine suna: " +
            command
        )

        # ====================================================
        # HELLO JARVIS
        # ====================================================

        if command in [
            "hello jarvis",
            "hey jarvis",
            "hi jarvis",
            "hello",
            "hi",
            "hey"
        ]:

            self.speak(
                "Hello! Main Jarvis hoon. "
                "Aapki madad ke liye ready hoon."
            )

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # NAME
        # ====================================================

        if command in [
            "what is your name",
            "what's your name",
            "what is your name jarvis",
            "your name",
            "tumhara naam kya hai",
            "aapka naam kya hai",
            "naam kya hai"
        ]:

            self.speak(
                "Mera naam Jarvis hai."
            )

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # WHO ARE YOU
        # ====================================================

        if command in [
            "who are you",
            "tum kaun ho",
            "aap kaun ho",
            "who are you jarvis"
        ]:

            self.speak(
                "Main aapka voice assistant "
                "Jarvis hoon."
            )

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # STOP
        # ====================================================

        if command in [
            "stop",
            "stop listening",
            "listening stop",
            "sunna band karo",
            "band ho jao",
            "jarvis stop",
            "stop jarvis"
        ]:

            self.stop_listening()

            self.speak(
                "Theek hai."
            )

            return

        # ====================================================
        # YOUTUBE
        # ====================================================

        if (
            "youtube" in command
            and (
                "khol" in command
                or "open" in command
            )
        ):

            self.open_youtube()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # CALCULATOR
        # ====================================================

        if (
            "calculator" in command
            and (
                "khol" in command
                or "open" in command
            )
        ):

            self.open_calculator()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # CAMERA
        # ====================================================

        if (
            "camera" in command
            and (
                "khol" in command
                or "open" in command
            )
        ):

            self.open_camera()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # CHROME
        # ====================================================

        if (
            "chrome" in command
            and (
                "khol" in command
                or "open" in command
            )
        ):

            self.open_chrome()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # WHATSAPP
        # ====================================================

        if (
            "whatsapp" in command
            and (
                "khol" in command
                or "open" in command
            )
        ):

            self.open_whatsapp()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # MAIN SETTINGS
        # ====================================================

        if (
            (
                "settings" in command
                or "setting" in command
            )
            and not any(
                x in command
                for x in [
                    "wifi",
                    "wi-fi",
                    "bluetooth",
                    "display",
                    "battery",
                    "location",
                    "security",
                    "mobile",
                    "network",
                    "data"
                ]
            )
        ):

            self.open_main_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # WIFI
        # ====================================================

        if (
            (
                "wifi" in command
                or "wi-fi" in command
                or "wi fi" in command
            )
            and (
                "khol" in command
                or "open" in command
                or "setting" in command
            )
        ):

            self.open_wifi_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # BLUETOOTH
        # ====================================================

        if (
            "bluetooth" in command
            and (
                "khol" in command
                or "open" in command
                or "setting" in command
            )
        ):

            self.open_bluetooth_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # DISPLAY
        # ====================================================

        if (
            "display" in command
            and (
                "khol" in command
                or "open" in command
                or "setting" in command
            )
        ):

            self.open_display_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # BATTERY
        # ====================================================

        if (
            "battery" in command
            and (
                "khol" in command
                or "open" in command
                or "setting" in command
            )
        ):

            self.open_battery_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # LOCATION
        # ====================================================

        if (
            "location" in command
            and (
                "khol" in command
                or "open" in command
                or "setting" in command
            )
        ):

            self.open_location_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # SECURITY
        # ====================================================

        if (
            "security" in command
            and (
                "khol" in command
                or "open" in command
                or "setting" in command
            )
        ):

            self.open_security_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # MOBILE NETWORK / DATA
        # ====================================================

        mobile_network_words = [
            "mobile network",
            "mobile networks",
            "mobile data",
            "mobile network settings",
            "mobile data settings",
            "mobile bada",
            "mobile bada kholo",
            "mobile bada khol"
        ]

        is_mobile_network = False

        for word in mobile_network_words:

            if word in command:

                is_mobile_network = True

                break

        if (
            is_mobile_network
            or (
                "mobile" in command
                and "network" in command
            )
            or (
                "mobile" in command
                and "data" in command
            )
        ):

            self.open_mobile_network_settings()

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # INSTALLED APP
        #
        # Is point par naye/downloaded apps handle honge.
        #
        # Examples:
        # Instagram kholo
        # Instagram khol
        # Instagram open karo
        # App kholo Instagram
        # Open app Instagram
        # ====================================================

        app_opened = self.try_open_natural_app(
            command
        )

        if app_opened:

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                2
            )

            return

        # ====================================================
        # UNKNOWN COMMAND
        # ====================================================

        self.speak(
            "Maine suna: " +
            command
        )

        Clock.schedule_once(
            lambda dt: self.listen_again(),
            2
        )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    VoiceAssistant().run()
