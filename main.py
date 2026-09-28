# ============================================================
# JARVIS VOICE ASSISTANT
# VERSION 0.19
# BASE: v0.18 SUCCESS
# NEW: GOOGLE / WEB VOICE SEARCH
# ============================================================

from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

from jnius import autoclass, PythonJavaClass, java_method


# ============================================================
# ANDROID CLASSES
# ============================================================

PythonActivity = autoclass("org.kivy.android.PythonActivity")

Intent = autoclass("android.content.Intent")
Context = autoclass("android.content.Context")
Uri = autoclass("android.net.Uri")

Settings = autoclass("android.provider.Settings")
RecognizerIntent = autoclass("android.speech.RecognizerIntent")
SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")

TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
Locale = autoclass("java.util.Locale")

PackageManager = autoclass("android.content.pm.PackageManager")


# ============================================================
# ANDROID MAIN THREAD RUNNER
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
        self.callback()


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

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):
        Clock.schedule_once(
            lambda dt: self.assistant.set_status("Sun raha hoon..."),
            0
        )

    @java_method("()V")
    def onBeginningOfSpeech(self):
        Clock.schedule_once(
            lambda dt: self.assistant.set_status("Sun raha hoon..."),
            0
        )

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
        # Error 5 = client-side error.
        # Isko screen par unnecessary error ke roop mein nahi dikhayenge.
        if error == 5:
            Clock.schedule_once(
                lambda dt: self.assistant.listen_again(),
                0.2
            )
            return

        Clock.schedule_once(
            lambda dt: self.assistant.handle_speech_error(error),
            0
        )

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):
        try:
            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )

            if matches is not None and matches.size() > 0:
                text = str(matches.get(0))

                Clock.schedule_once(
                    lambda dt: self.assistant.process_command(text),
                    0
                )
            else:
                Clock.schedule_once(
                    lambda dt: self.assistant.listen_again(),
                    0
                )

        except Exception:
            Clock.schedule_once(
                lambda dt: self.assistant.listen_again(),
                0
            )

    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, partialResults):
        pass

    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(self, eventType, params):
        pass


# ============================================================
# MAIN VOICE ASSISTANT
# ============================================================

class VoiceAssistant(App):

    def build(self):

        self.label = Label(
            text="JARVIS v0.19\nStarting...",
            halign="center",
            valign="middle"
        )

        self.label.bind(
            size=self.update_text_size
        )

        Clock.schedule_once(
            self.start_setup,
            1
        )

        return self.label

    # ========================================================
    # TEXT / STATUS
    # ========================================================

    def update_text_size(self, instance, value):
        self.label.text_size = value

    def set_status(self, text):
        self.label.text = "JARVIS\n\n" + text

    # ========================================================
    # START SETUP
    # ========================================================

    def start_setup(self, dt):

        try:
            activity = PythonActivity.mActivity

            self.activity = activity

            # ------------------------------------------------
            # TEXT TO SPEECH
            # ------------------------------------------------

            self.tts = TextToSpeech(
                activity,
                None
            )

            try:
                self.tts.setLanguage(
                    Locale.US
                )
            except Exception:
                pass

            # ------------------------------------------------
            # SPEECH RECOGNIZER
            # ------------------------------------------------

            self.speech_recognizer = SpeechRecognizer.createSpeechRecognizer(
                activity
            )

            self.listener = RecognitionListener(
                self
            )

            self.speech_recognizer.setRecognitionListener(
                self.listener
            )

            # ------------------------------------------------
            # RECOGNIZER INTENT
            # ------------------------------------------------

            self.recognizer_intent = Intent(
                RecognizerIntent.ACTION_RECOGNIZE_SPEECH
            )

            self.recognizer_intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
            )

            self.recognizer_intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE,
                "en-IN"
            )

            self.recognizer_intent.putExtra(
                RecognizerIntent.EXTRA_PARTIAL_RESULTS,
                False
            )

            self.recognizer_intent.putExtra(
                RecognizerIntent.EXTRA_MAX_RESULTS,
                3
            )

            # ------------------------------------------------
            # START
            # ------------------------------------------------

            self.set_status(
                "Jarvis v0.19 ready..."
            )

            Clock.schedule_once(
                lambda dt: self.speak(
                    "Hello! Main Jarvis hoon."
                ),
                1
            )

            Clock.schedule_once(
                lambda dt: self.listen(),
                3
            )

        except Exception as e:

            self.set_status(
                "Setup Error:\n" + str(e)
            )

    # ========================================================
    # TEXT TO SPEECH
    # ========================================================

    def speak(self, text):

        try:
            self.tts.speak(
                text,
                TextToSpeech.QUEUE_FLUSH,
                None
            )

        except Exception:
            pass

    # ========================================================
    # START LISTENING
    # ========================================================

    def listen(self):

        try:

            self.set_status(
                "Sun raha hoon..."
            )

            self.speech_recognizer.startListening(
                self.recognizer_intent
            )

        except Exception:

            Clock.schedule_once(
                lambda dt: self.listen_again(),
                0.5
            )

    # ========================================================
    # LISTEN AGAIN
    # ========================================================

    def listen_again(self):

        try:

            self.speech_recognizer.cancel()

        except Exception:
            pass

        Clock.schedule_once(
            lambda dt: self.listen(),
            0.3
        )

    # ========================================================
    # STOP LISTENING
    # ========================================================

    def stop_listening(self):

        try:
            self.speech_recognizer.stopListening()
        except Exception:
            pass

    # ========================================================
    # SPEECH ERROR
    # ========================================================

    def handle_speech_error(self, error):

        # Error 5 is handled silently above.
        # Baaki errors ke liye short status.

        if error == 7:
            self.set_status(
                "Dobara boliye..."
            )

        elif error == 6:
            self.set_status(
                "Dobara boliye..."
            )

        elif error == 8:
            self.set_status(
                "Listening restart ho raha hai..."
            )

        else:
            self.set_status(
                "Listening restart ho raha hai..."
            )

        Clock.schedule_once(
            lambda dt: self.listen(),
            1
        )

    # ========================================================
    # ANDROID MAIN THREAD
    # ========================================================

    def run_on_android_thread(self, callback):

        try:

            runnable = MainThreadRunnable(
                callback
            )

            self.activity.runOnUiThread(
                runnable
            )

        except Exception:
            try:
                callback()
            except Exception:
                pass

    # ========================================================
    # OPEN INTENT
    # ========================================================

    def open_intent(self, intent):

        def action():

            try:

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                Clock.schedule_once(
                    lambda dt: self.set_status(
                        "Open nahi ho saka."
                    ),
                    0
                )

        self.run_on_android_thread(
            action
        )

    # ========================================================
    # YOUTUBE
    # ========================================================

    def open_youtube(self):

        self.set_status(
            "YouTube khol raha hoon..."
        )

        self.speak(
            "YouTube khol raha hoon."
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(
                "https://www.youtube.com"
            )
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # CALCULATOR
    # ========================================================

    def open_calculator(self):

        self.set_status(
            "Calculator khol raha hoon..."
        )

        self.speak(
            "Calculator khol raha hoon."
        )

        try:

            intent = Intent(
                Intent.ACTION_MAIN
            )

            intent.addCategory(
                "android.intent.category.APP_CALCULATOR"
            )

            self.open_intent(
                intent
            )

        except Exception:

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(
                    "https://www.google.com/search?q=calculator"
                )
            )

            self.open_intent(
                intent
            )

    # ========================================================
    # CAMERA
    # ========================================================

    def open_camera(self):

        self.set_status(
            "Camera khol raha hoon..."
        )

        self.speak(
            "Camera khol raha hoon."
        )

        intent = Intent(
            "android.media.action.IMAGE_CAPTURE"
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # CHROME
    # ========================================================

    def open_chrome(self):

        self.set_status(
            "Chrome khol raha hoon..."
        )

        self.speak(
            "Chrome khol raha hoon."
        )

        try:

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(
                    "https://www.google.com"
                )
            )

            intent.setPackage(
                "com.android.chrome"
            )

            self.open_intent(
                intent
            )

        except Exception:

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(
                    "https://www.google.com"
                )
            )

            self.open_intent(
                intent
            )

    # ========================================================
    # WHATSAPP
    # ========================================================

    def open_whatsapp(self):

        self.set_status(
            "WhatsApp khol raha hoon..."
        )

        self.speak(
            "WhatsApp khol raha hoon."
        )

        try:

            intent = Intent(
                Intent.ACTION_MAIN
            )

            intent.addCategory(
                Intent.CATEGORY_LAUNCHER
            )

            intent.setPackage(
                "com.whatsapp"
            )

            self.open_intent(
                intent
            )

        except Exception:

            self.set_status(
                "WhatsApp nahi mila."
            )

    # ========================================================
    # MAIN SETTINGS
    # ========================================================

    def open_main_settings(self):

        self.set_status(
            "Settings khol raha hoon..."
        )

        self.speak(
            "Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # WIFI SETTINGS
    # ========================================================

    def open_wifi_settings(self):

        self.set_status(
            "Wi-Fi Settings khol raha hoon..."
        )

        self.speak(
            "Wi-Fi Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_WIFI_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # BLUETOOTH SETTINGS
    # ========================================================

    def open_bluetooth_settings(self):

        self.set_status(
            "Bluetooth Settings khol raha hoon..."
        )

        self.speak(
            "Bluetooth Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_BLUETOOTH_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # DISPLAY SETTINGS
    # ========================================================

    def open_display_settings(self):

        self.set_status(
            "Display Settings khol raha hoon..."
        )

        self.speak(
            "Display Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_DISPLAY_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # BATTERY SETTINGS
    # ========================================================

    def open_battery_settings(self):

        self.set_status(
            "Battery Settings khol raha hoon..."
        )

        self.speak(
            "Battery Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_BATTERY_SAVER_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # LOCATION SETTINGS
    # ========================================================

    def open_location_settings(self):

        self.set_status(
            "Location Settings khol raha hoon..."
        )

        self.speak(
            "Location Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_LOCATION_SOURCE_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # SECURITY SETTINGS
    # ========================================================

    def open_security_settings(self):

        self.set_status(
            "Security Settings khol raha hoon..."
        )

        self.speak(
            "Security Settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_SECURITY_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # MOBILE NETWORK / DATA SETTINGS
    # ========================================================

    def open_mobile_network_settings(self):

        self.set_status(
            "Mobile Network Settings khol raha hoon..."
        )

        self.speak(
            "Mobile Network Settings khol raha hoon."
        )

        def action():

            actions = [
                "android.settings.MOBILE_NETWORK_SETTINGS",
                "android.settings.NETWORK_OPERATOR_SETTINGS",
                "android.settings.DATA_ROAMING_SETTINGS"
            ]

            for action_name in actions:

                try:

                    intent = Intent(
                        action_name
                    )

                    self.activity.startActivity(
                        intent
                    )

                    return

                except Exception:
                    continue

            self.set_status(
                "Mobile Network Settings open nahi ho saki."
            )

        self.run_on_android_thread(
            action
        )

    # ========================================================
    # INSTALLED APP LAUNCHER
    # ========================================================

    def open_installed_app(self, app_name):

        clean_name = app_name.strip()

        if clean_name == "":
            return False

        self.set_status(
            clean_name.title() +
            " khol raha hoon..."
        )

        self.speak(
            clean_name.title() +
            " khol raha hoon."
        )

        def action():

            try:

                pm = self.activity.getPackageManager()

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                apps = pm.queryIntentActivities(
                    intent,
                    0
                )

                search_name = clean_name.lower()

                exact_match = None
                partial_match = None
                package_match = None

                for i in range(apps.size()):

                    info = apps.get(i)

                    label = str(
                        info.loadLabel(pm)
                    )

                    package_name = str(
                        info.activityInfo.packageName
                    )

                    label_lower = label.lower()
                    package_lower = package_name.lower()

                    if label_lower == search_name:
                        exact_match = info
                        break

                    if search_name in label_lower:
                        if partial_match is None:
                            partial_match = info

                    if search_name in package_lower:
                        if package_match is None:
                            package_match = info

                selected = (
                    exact_match
                    or partial_match
                    or package_match
                )

                if selected is None:

                    Clock.schedule_once(
                        lambda dt: self.set_status(
                            clean_name.title() +
                            " nahi mila."
                        ),
                        0
                    )

                    return

                launch_intent = pm.getLaunchIntentForPackage(
                    str(
                        selected.activityInfo.packageName
                    )
                )

                if launch_intent is None:

                    Clock.schedule_once(
                        lambda dt: self.set_status(
                            clean_name.title() +
                            " launch nahi ho saka."
                        ),
                        0
                    )

                    return

                self.activity.startActivity(
                    launch_intent
                )

            except Exception:

                Clock.schedule_once(
                    lambda dt: self.set_status(
                        clean_name.title() +
                        " open nahi ho saka."
                    ),
                    0
                )

        self.run_on_android_thread(
            action
        )

        return True

    # ========================================================
    # APP COMMAND NAME EXTRACTOR
    # ========================================================

    def extract_app_name(self, command):

        text = command.lower().strip()

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

            if text.startswith(prefix):

                name = text[
                    len(prefix):
                ].strip()

                if name:
                    return name

        return None

    # ========================================================
    # NATURAL APP COMMAND
    # ========================================================

    def try_open_natural_app(self, command):

        text = command.lower().strip()

        suffixes = [
            " kholo",
            " khol",
            " open karo",
            " open kar",
            " ko kholo",
            " ko khol"
        ]

        for suffix in suffixes:

            if text.endswith(suffix):

                app_name = text[
                    :-len(suffix)
                ].strip()

                if not app_name:
                    continue

                blocked = [
                    "youtube",
                    "calculator",
                    "camera",
                    "chrome",
                    "whatsapp",
                    "settings",
                    "wifi",
                    "bluetooth",
                    "display",
                    "battery",
                    "location",
                    "security",
                    "mobile network",
                    "mobile networks",
                    "data settings",
                    "google"
                ]

                if app_name in blocked:
                    return False

                return self.open_installed_app(
                    app_name
                )

        return False

    # ========================================================
    # GOOGLE / WEB SEARCH — v0.19 NEW FEATURE
    # ========================================================

    def google_web_search(self, query):

        query = query.strip()

        if not query:
            self.set_status(
                "Kya search karna hai?"
            )
            self.speak(
                "Kya search karna hai?"
            )
            return

        self.set_status(
            "Google par " +
            query +
            " search kar raha hoon..."
        )

        self.speak(
            "Google par search kar raha hoon."
        )

        try:

            encoded_query = Uri.encode(
                query
            )

            url = (
                "https://www.google.com/search?q="
                + str(encoded_query)
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent
            )

        except Exception:

            self.set_status(
                "Google Search open nahi ho saka."
            )

    # ========================================================
    # SEARCH COMMAND EXTRACTOR
    # ========================================================

    def extract_search_query(self, command):

        text = command.lower().strip()

        # ----------------------------------------------
        # Google search commands
        # ----------------------------------------------

        prefixes = [
            "google pe ",
            "google par ",
            "google me ",
            "google mein ",
            "google search ",
            "google search karo ",
            "google par search karo ",
            "google pe search karo ",
            "google me search karo ",
            "google mein search karo ",
            "search karo ",
            "search kar ",
            "web search ",
            "web search karo ",
            "internet par ",
            "internet pe "
        ]

        for prefix in prefixes:

            if text.startswith(prefix):

                query = text[
                    len(prefix):
                ].strip()

                if query:

                    # Optional ending remove
                    endings = [
                        " search karo",
                        " search kar",
                        " google par",
                        " google pe"
                    ]

                    for ending in endings:

                        if query.endswith(ending):

                            query = query[
                                :-len(ending)
                            ].strip()

                    return query

        # ----------------------------------------------
        # "X search karo"
        # ----------------------------------------------

        endings = [
            " search karo",
            " search kar"
        ]

        for ending in endings:

            if text.endswith(ending):

                query = text[
                    :-len(ending)
                ].strip()

                if query:

                    blocked = [
                        "youtube",
                        "instagram",
                        "whatsapp",
                        "chrome"
                    ]

                    # Dedicated commands ko search na samjhein
                    if query not in blocked:
                        return query

        return None

    # ========================================================
    # COMMAND PROCESSOR
    # ========================================================

    def process_command(self, command):

        try:

            text = command.strip().lower()

            if not text:
                self.listen_again()
                return

            # IMPORTANT:
            # Yahan "Maine suna: ..." display nahi hoga.
            # Har known command apna direct status dikhayega.

            # =================================================
            # STOP
            # =================================================

            if (
                text == "stop"
                or text == "stop listening"
                or text == "jarvis stop"
                or text == "bas"
            ):

                self.stop_listening()

                self.set_status(
                    "Listening stopped."
                )

                self.speak(
                    "Okay."
                )

                return

            # =================================================
            # GREETING
            # =================================================

            if (
                "hello jarvis" in text
                or "hi jarvis" in text
                or "hey jarvis" in text
                or text == "hello"
                or text == "hi"
            ):

                self.set_status(
                    "Hello! Main Jarvis hoon."
                )

                self.speak(
                    "Hello! Main Jarvis hoon."
                )

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    2
                )

                return

            # =================================================
            # NAME
            # =================================================

            if (
                "what is your name" in text
                or "what's your name" in text
                or "tumhara naam kya hai" in text
                or "aapka naam kya hai" in text
                or "apna naam batao" in text
            ):

                self.set_status(
                    "Mera naam Jarvis hai."
                )

                self.speak(
                    "Mera naam Jarvis hai."
                )

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    2
                )

                return

            # =================================================
            # WHO ARE YOU
            # =================================================

            if (
                "who are you" in text
                or "tum kaun ho" in text
                or "aap kaun ho" in text
            ):

                self.set_status(
                    "Main tumhara voice assistant Jarvis hoon."
                )

                self.speak(
                    "Main tumhara voice assistant Jarvis hoon."
                )

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    2
                )

                return

            # =================================================
            # GOOGLE / WEB SEARCH
            # NEW v0.19
            # =================================================

            search_query = self.extract_search_query(
                text
            )

            if search_query:

                self.google_web_search(
                    search_query
                )

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # YOUTUBE
            # =================================================

            if (
                "youtube" in text
                and (
                    "khol" in text
                    or "open" in text
                )
            ):

                self.open_youtube()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # CALCULATOR
            # =================================================

            if (
                "calculator" in text
                or "calculate" in text
            ) and (
                "khol" in text
                or "open" in text
            ):

                self.open_calculator()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # CAMERA
            # =================================================

            if (
                "camera" in text
                and (
                    "khol" in text
                    or "open" in text
                )
            ):

                self.open_camera()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # CHROME
            # =================================================

            if (
                "chrome" in text
                and (
                    "khol" in text
                    or "open" in text
                )
            ):

                self.open_chrome()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # WHATSAPP
            # =================================================

            if (
                "whatsapp" in text
                and (
                    "khol" in text
                    or "open" in text
                )
            ):

                self.open_whatsapp()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # MAIN SETTINGS
            # =================================================

            if (
                "settings kholo" in text
                or "settings khol" in text
                or "settings open karo" in text
                or "settings open kar" in text
                or "main settings" in text
                or "main setting" in text
            ):

                self.open_main_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # WIFI
            # =================================================

            if (
                "wifi" in text
                or "wi fi" in text
                or "wi-fi" in text
            ) and (
                "khol" in text
                or "open" in text
                or "setting" in text
            ):

                self.open_wifi_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # BLUETOOTH
            # =================================================

            if (
                "bluetooth" in text
            ) and (
                "khol" in text
                or "open" in text
                or "setting" in text
            ):

                self.open_bluetooth_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # DISPLAY
            # =================================================

            if (
                "display" in text
            ) and (
                "khol" in text
                or "open" in text
                or "setting" in text
            ):

                self.open_display_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # BATTERY
            # =================================================

            if (
                "battery" in text
            ) and (
                "khol" in text
                or "open" in text
                or "setting" in text
            ):

                self.open_battery_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # LOCATION
            # =================================================

            if (
                "location" in text
            ) and (
                "khol" in text
                or "open" in text
                or "setting" in text
            ):

                self.open_location_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # SECURITY
            # =================================================

            if (
                "security" in text
            ) and (
                "khol" in text
                or "open" in text
                or "setting" in text
            ):

                self.open_security_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # MOBILE NETWORK / DATA
            # =================================================

            mobile_network_words = [
                "mobile network",
                "mobile networks",
                "mobile data",
                "data settings",
                "network settings",
                "sim settings"
            ]

            is_mobile_network = False

            for word in mobile_network_words:

                if word in text:
                    is_mobile_network = True
                    break

            if is_mobile_network:

                self.open_mobile_network_settings()

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # GENERIC APP PREFIX
            # =================================================

            app_name = self.extract_app_name(
                text
            )

            if app_name:

                self.open_installed_app(
                    app_name
                )

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # NATURAL APP COMMAND
            # =================================================

            if self.try_open_natural_app(
                text
            ):

                Clock.schedule_once(
                    lambda dt: self.listen(),
                    3
                )

                return

            # =================================================
            # UNKNOWN COMMAND
            # =================================================

            self.set_status(
                "Command samajh nahi aaya."
            )

            self.speak(
                "Command samajh nahi aaya."
            )

            Clock.schedule_once(
                lambda dt: self.listen(),
                2
            )

        except Exception:

            self.set_status(
                "Command process nahi ho saka."
            )

            Clock.schedule_once(
                lambda dt: self.listen(),
                1
            )

    # ========================================================
    # APP STOP
    # ========================================================

    def on_stop(self):

        try:
            if self.speech_recognizer:
                self.speech_recognizer.destroy()
        except Exception:
            pass

        try:
            if self.tts:
                self.tts.stop()
                self.tts.shutdown()
        except Exception:
            pass


# ============================================================
# RUN JARVIS
# ============================================================

VoiceAssistant().run()   
