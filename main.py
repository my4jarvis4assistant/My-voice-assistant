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

Uri = autoclass(
    "android.net.Uri"
)

RecognizerIntent = autoclass(
    "android.speech.RecognizerIntent"
)

SpeechRecognizer = autoclass(
    "android.speech.SpeechRecognizer"
)

Bundle = autoclass(
    "android.os.Bundle"
)

Locale = autoclass(
    "java.util.Locale"
)

TextToSpeech = autoclass(
    "android.speech.tts.TextToSpeech"
)

Settings = autoclass(
    "android.provider.Settings"
)

PackageManager = autoclass(
    "android.content.pm.PackageManager"
)


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

        try:
            self.callback()

        except Exception as e:
            print(
                "Main thread error:",
                e
            )


# ============================================================
# SPEECH RECOGNITION LISTENER
# ============================================================

class RecognitionListener(PythonJavaClass):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):

        self.app.set_status(
            "Listening..."
        )

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

        print(
            "Speech error:",
            error
        )

        # Error 5:
        # recognizer/client state issue.
        # Isko silently retry karenge.
        if error == 5:

            Clock.schedule_once(
                lambda dt:
                self.app.listen_again(),
                0.5
            )

            return

        # Temporary recognition errors.
        if error in (
            6,
            7,
            8,
            9
        ):

            Clock.schedule_once(
                lambda dt:
                self.app.listen_again(),
                0.8
            )

            return

        self.app.set_status(
            "Dobara boliye..."
        )

        Clock.schedule_once(
            lambda dt:
            self.app.listen_again(),
            1.0
        )

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):

        try:

            matches = (
                results.getStringArrayList(
                    SpeechRecognizer.RESULTS_RECOGNITION
                )
            )

            if (
                matches is not None
                and matches.size() > 0
            ):

                text = str(
                    matches.get(0)
                )

                print(
                    "Recognized:",
                    text
                )

                self.app.process_command(
                    text
                )

        except Exception as e:

            print(
                "Result error:",
                e
            )

    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, results):

        pass

    @java_method("(ILandroid/os/Bundle;)V")
    def onEvent(
        self,
        eventType,
        params
    ):

        pass


# ============================================================
# VOICE ASSISTANT
# ============================================================

class VoiceAssistant(App):

    def build(self):

        self.activity = (
            PythonActivity.mActivity
        )

        self.speech_recognizer = None

        self.listener = None

        self.recognizer_intent = None

        self.tts = None

        self.permission_requested = False

        self.setup_done = False

        self.status_label = Label(
            text="JARVIS starting...",
            font_size="20sp"
        )

        Clock.schedule_once(
            self.start_setup,
            1
        )

        return self.status_label

    # ========================================================
    # STATUS
    # ========================================================

    def set_status(self, text):

        try:

            Clock.schedule_once(
                lambda dt:
                setattr(
                    self.status_label,
                    "text",
                    text
                ),
                0
            )

        except Exception:
            pass

    # ========================================================
    # ANDROID MAIN THREAD
    # ========================================================

    def run_on_android_thread(
        self,
        callback
    ):

        try:

            runnable = MainThreadRunnable(
                callback
            )

            self.activity.runOnUiThread(
                runnable
            )

        except Exception as e:

            print(
                "run_on_android_thread error:",
                e
            )

    # ========================================================
    # MICROPHONE PERMISSION
    # ========================================================

    def check_microphone_permission(self):

        try:

            from android.permissions import (
                Permission,
                check_permission,
                request_permissions
            )

            granted = check_permission(
                Permission.RECORD_AUDIO
            )

            if granted:

                return True

            self.set_status(
                "Microphone permission required..."
            )

            if not self.permission_requested:

                self.permission_requested = True

                def permission_callback(
                    permissions,
                    grants
                ):

                    print(
                        "Permission result:",
                        permissions,
                        grants
                    )

                    self.permission_requested = False

                    Clock.schedule_once(
                        lambda dt:
                        self.start_setup(),
                        0.8
                    )

                request_permissions(
                    [
                        Permission.RECORD_AUDIO
                    ],
                    permission_callback
                )

            return False

        except Exception as e:

            print(
                "Permission check error:",
                e
            )

            # If the android permission helper
            # is unavailable, setup can still continue.
            return True

    # ========================================================
    # TTS
    # ========================================================

    def speak(self, text):

        try:

            if self.tts is None:

                return

            def speak_main():

                try:

                    self.tts.speak(
                        text,
                        TextToSpeech.QUEUE_FLUSH,
                        None
                    )

                except Exception as e:

                    print(
                        "TTS error:",
                        e
                    )

            self.run_on_android_thread(
                speak_main
            )

        except Exception as e:

            print(
                "Speak error:",
                e
            )

    # ========================================================
    # START SETUP
    # ========================================================

    def start_setup(self, dt=None):

        # ----------------------------------------------------
        # FIRST: MICROPHONE PERMISSION
        # ----------------------------------------------------

        if not self.check_microphone_permission():

            return

        # ----------------------------------------------------
        # ANDROID SETUP
        # ----------------------------------------------------

        def setup_android():

            try:

                # --------------------------------------------
                # TTS
                # --------------------------------------------

                if self.tts is None:

                    self.tts = TextToSpeech(
                        self.activity,
                        None
                    )

                    self.tts.setLanguage(
                        Locale.US
                    )

                # --------------------------------------------
                # SPEECH RECOGNIZER
                # --------------------------------------------

                if (
                    self.speech_recognizer
                    is None
                ):

                    self.speech_recognizer = (
                        SpeechRecognizer
                        .createSpeechRecognizer(
                            self.activity
                        )
                    )

                # --------------------------------------------
                # LISTENER
                # --------------------------------------------

                if self.listener is None:

                    self.listener = (
                        RecognitionListener(
                            self
                        )
                    )

                    self.speech_recognizer.setRecognitionListener(
                        self.listener
                    )

                # --------------------------------------------
                # RECOGNIZER INTENT
                # --------------------------------------------

                if (
                    self.recognizer_intent
                    is None
                ):

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
                        RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE,
                        "en-IN"
                    )

                    self.recognizer_intent.putExtra(
                        RecognizerIntent.EXTRA_MAX_RESULTS,
                        1
                    )

                self.setup_done = True

                self.set_status(
                    "JARVIS ready..."
                )

                self.speak(
                    "Hello! Main Jarvis hoon."
                )

                Clock.schedule_once(
                    lambda dt:
                    self.listen(),
                    2
                )

            except Exception as e:

                print(
                    "Setup Error:",
                    e
                )

                self.set_status(
                    "Setup Error: " +
                    str(e)
                )

        self.run_on_android_thread(
            setup_android
        )

    # ========================================================
    # LISTEN
    # ========================================================

    def listen(self):

        if (
            self.speech_recognizer
            is None
        ):

            return

        if (
            self.recognizer_intent
            is None
        ):

            return

        def start_listening():

            try:

                self.set_status(
                    "Listening..."
                )

                self.speech_recognizer.startListening(
                    self.recognizer_intent
                )

            except Exception as e:

                print(
                    "Start listening error:",
                    e
                )

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    1
                )

        self.run_on_android_thread(
            start_listening
        )

    # ========================================================
    # LISTEN AGAIN
    # ========================================================

    def listen_again(self):

        if (
            self.speech_recognizer
            is None
        ):

            return

        def restart():

            try:

                self.speech_recognizer.cancel()

            except Exception:
                pass

            try:

                self.speech_recognizer.startListening(
                    self.recognizer_intent
                )

                self.set_status(
                    "Listening..."
                )

            except Exception as e:

                print(
                    "Listen again error:",
                    e
                )

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    1
                )

        self.run_on_android_thread(
            restart
        )

    # ========================================================
    # STOP LISTENING
    # ========================================================

    def stop_listening(self):

        if (
            self.speech_recognizer
            is None
        ):

            return

        def stop():

            try:

                self.speech_recognizer.stopListening()

            except Exception:
                pass

        self.run_on_android_thread(
            stop
        )

    # ========================================================
    # OPEN INTENT
    # ========================================================

    def open_intent(self, intent):

        def open_main():

            try:

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Intent error:",
                    e
                )

        self.run_on_android_thread(
            open_main
        )

    # ========================================================
    # GENERIC URL
    # ========================================================

    def open_url(self, url):

        try:

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent
            )

            return True

        except Exception as e:

            print(
                "URL error:",
                e
            )

            return False

    # ========================================================
    # GOOGLE / WEB SEARCH
    # ========================================================

    def google_web_search(
        self,
        query
    ):

        query = query.strip()

        if not query:

            self.set_status(
                "Kya search karna hai?"
            )

            self.speak(
                "Kya search karna hai?"
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
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

        except Exception as e:

            print(
                "Google search error:",
                e
            )

            self.set_status(
                "Google Search open nahi ho saka."
            )

    # ========================================================
    # YOUTUBE SEARCH
    # ========================================================

    def youtube_search(
        self,
        query
    ):

        query = query.strip()

        if not query:

            self.set_status(
                "YouTube par kya search karna hai?"
            )

            self.speak(
                "YouTube par kya search karna hai?"
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

        self.set_status(
            "YouTube par " +
            query +
            " search kar raha hoon..."
        )

        self.speak(
            "YouTube par search kar raha hoon."
        )

        try:

            encoded_query = Uri.encode(
                query
            )

            url = (
                "https://www.youtube.com/results?search_query="
                + str(encoded_query)
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent
            )

        except Exception as e:

            print(
                "YouTube search error:",
                e
            )

            self.set_status(
                "YouTube Search open nahi ho saka."
            )

    # ========================================================
    # MUSIC SEARCH
    # ========================================================

    def music_search(
        self,
        query
    ):

        query = query.strip()

        if not query:

            self.set_status(
                "Music me kya search karna hai?"
            )

            self.speak(
                "Music me kya search karna hai?"
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

        self.set_status(
            "Music search kar raha hoon..."
        )

        self.speak(
            "Music search kar raha hoon."
        )

        try:

            encoded_query = Uri.encode(
                query
            )

            url = (
                "https://music.youtube.com/search?q="
                + str(encoded_query)
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            self.open_intent(
                intent
            )

        except Exception as e:

            print(
                "Music search error:",
                e
            )

            self.set_status(
                "Music Search open nahi ho saka."
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

        def launch():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                intent = (
                    pm.getLaunchIntentForPackage(
                        "com.whatsapp"
                    )
                )

                if intent is None:

                    intent = (
                        pm.getLaunchIntentForPackage(
                            "com.whatsapp.w4b"
                        )
                    )

                if intent is None:

                    self.set_status(
                        "WhatsApp installed nahi mila."
                    )

                    self.speak(
                        "WhatsApp installed nahi mila."
                    )

                    return

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "WhatsApp error:",
                    e
                )

                self.set_status(
                    "WhatsApp open nahi ho saka."
                )

        self.run_on_android_thread(
            launch
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

        def launch_calculator():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                packages = [
                    "com.miui.calculator",
                    "com.google.android.calculator",
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

                            intent.addFlags(
                                Intent.FLAG_ACTIVITY_NEW_TASK
                            )

                            self.activity.startActivity(
                                intent
                            )

                            return

                    except Exception as e:

                        print(
                            "Calculator package error:",
                            package_name,
                            e
                        )

                try:

                    calc_intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    calc_intent.addCategory(
                        Intent.CATEGORY_APP_CALCULATOR
                    )

                    self.activity.startActivity(
                        calc_intent
                    )

                    return

                except Exception:
                    pass

                self.set_status(
                    "Calculator open nahi ho saka."
                )

                self.speak(
                    "Calculator open nahi ho saka."
                )

            except Exception as e:

                print(
                    "Calculator error:",
                    e
                )

                self.set_status(
                    "Calculator open nahi ho saka."
                )

        self.run_on_android_thread(
            launch_calculator
        )

    # ========================================================
    # TIME
    # ========================================================

    def tell_time(self):

        try:

            from datetime import datetime

            time_text = datetime.now().strftime(
                "%I:%M %p"
            )

            self.set_status(
                "Abhi time hai " +
                time_text
            )

            self.speak(
                "Abhi time hai " +
                time_text
            )

        except Exception as e:

            print(
                "Time error:",
                e
            )

            self.set_status(
                "Time nahi bata saka."
            )

    # ========================================================
    # DATE
    # ========================================================

    def tell_date(self):

        try:

            from datetime import datetime

            date_text = datetime.now().strftime(
                "%d %B %Y"
            )

            self.set_status(
                "Aaj ki date hai " +
                date_text
            )

            self.speak(
                "Aaj ki date hai " +
                date_text
            )

        except Exception as e:

            print(
                "Date error:",
                e
            )

            self.set_status(
                "Date nahi bata saka."
                )
    # ========================================================
    # INSTALLED APP LAUNCHER
    # ========================================================

    def open_installed_app(
        self,
        app_name
    ):

        app_name = app_name.strip()

        self.set_status(
            app_name.capitalize() +
            " khol raha hoon..."
        )

        self.speak(
            app_name.capitalize() +
            " khol raha hoon."
        )

        def launch():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                packages = (
                    pm.getInstalledPackages(0)
                )

                for i in range(
                    packages.size()
                ):

                    info = packages.get(i)

                    label = str(
                        info.applicationInfo
                        .loadLabel(pm)
                    )

                    if (
                        label.lower()
                        == app_name.lower()
                    ):

                        package_name = str(
                            info.packageName
                        )

                        intent = (
                            pm.getLaunchIntentForPackage(
                                package_name
                            )
                        )

                        if intent is not None:

                            intent.addFlags(
                                Intent.FLAG_ACTIVITY_NEW_TASK
                            )

                            self.activity.startActivity(
                                intent
                            )

                            return

                self.set_status(
                    app_name.capitalize() +
                    " installed app nahi mila."
                )

                self.speak(
                    app_name.capitalize() +
                    " installed app nahi mila."
                )

            except Exception as e:

                print(
                    "Installed app error:",
                    e
                )

                self.set_status(
                    app_name.capitalize() +
                    " open nahi ho saka."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # PHONE / DIALER - v0.21
    # ========================================================

    def open_phone(self):

        self.set_status(
            "Phone khol raha hoon..."
        )

        self.speak(
            "Phone khol raha hoon."
        )

        def launch_phone():

            try:

                intent = Intent(
                    Intent.ACTION_DIAL
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Phone error:",
                    e
                )

                self.set_status(
                    "Phone open nahi ho saka."
                )

        self.run_on_android_thread(
            launch_phone
        )

    # ========================================================
    # DIAL NUMBER - v0.21
    # ========================================================

    def dial_number(
        self,
        number
    ):

        number = number.strip()

        if not number:

            self.set_status(
                "Number nahi mila."
            )

            self.speak(
                "Number nahi mila."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

        self.set_status(
            "Dialer me number khol raha hoon..."
        )

        self.speak(
            "Dialer me number khol raha hoon."
        )

        def launch_dialer():

            try:

                clean_number = ""

                for char in number:

                    if (
                        char.isdigit()
                        or char == "+"
                    ):

                        clean_number += char

                if not clean_number:

                    self.set_status(
                        "Valid number nahi mila."
                    )

                    self.speak(
                        "Valid number nahi mila."
                    )

                    return

                uri = Uri.parse(
                    "tel:" + clean_number
                )

                intent = Intent(
                    Intent.ACTION_DIAL,
                    uri
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Dial number error:",
                    e
                )

                self.set_status(
                    "Number Dialer me open nahi ho saka."
                )

        self.run_on_android_thread(
            launch_dialer
        )

    # ========================================================
    # CONTACTS - v0.21 FIXED
    # ========================================================

    def open_contacts(self):

        self.set_status(
            "Contacts khol raha hoon..."
        )

        self.speak(
            "Contacts khol raha hoon."
        )

        def launch_contacts():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                # ------------------------------------------------
                # METHOD 1:
                # Xiaomi/MIUI Contacts app
                # ------------------------------------------------

                contacts_packages = [
                    "com.android.contacts",
                    "com.google.android.contacts"
                ]

                for package_name in contacts_packages:

                    try:

                        intent = (
                            pm.getLaunchIntentForPackage(
                                package_name
                            )
                        )

                        if intent is not None:

                            intent.addFlags(
                                Intent.FLAG_ACTIVITY_NEW_TASK
                            )

                            self.activity.startActivity(
                                intent
                            )

                            return

                    except Exception as e:

                        print(
                            "Contacts package error:",
                            package_name,
                            e
                        )

                # ------------------------------------------------
                # METHOD 2:
                # Android Contacts category
                # ------------------------------------------------

                try:

                    intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    intent.addCategory(
                        "android.intent.category.APP_CONTACTS"
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    self.activity.startActivity(
                        intent
                    )

                    return

                except Exception as e:

                    print(
                        "Contacts category error:",
                        e
                    )

                # ------------------------------------------------
                # METHOD 3:
                # ContactsContract URI
                # ------------------------------------------------

                try:

                    ContactsContract = autoclass(
                        "android.provider.ContactsContract"
                    )

                    contacts_uri = (
                        ContactsContract
                        .Contacts
                        .CONTENT_URI
                    )

                    intent = Intent(
                        Intent.ACTION_VIEW,
                        contacts_uri
                    )

                    intent.addFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                    )

                    self.activity.startActivity(
                        intent
                    )

                    return

                except Exception as e:

                    print(
                        "Contacts URI error:",
                        e
                    )

                # ------------------------------------------------
                # NOTHING WORKED
                # ------------------------------------------------

                self.set_status(
                    "Contacts app nahi mili."
                )

                self.speak(
                    "Contacts app nahi mili."
                )

            except Exception as e:

                print(
                    "Contacts launch error:",
                    e
                )

                self.set_status(
                    "Contacts open nahi ho saka."
                )

                self.speak(
                    "Contacts open nahi ho saka."
                )

        self.run_on_android_thread(
            launch_contacts
        )


    # ========================================================
    # SETTINGS / ANDROID ACTIONS
    # ========================================================

    def open_settings(
        self,
        setting_type
    ):

        try:

            if setting_type == "main":

                intent = Intent(
                    Settings.ACTION_SETTINGS
                )

                self.set_status(
                    "Settings khol raha hoon..."
                )

                self.speak(
                    "Settings khol raha hoon."
                )

            elif setting_type == "wifi":

                # IMPORTANT:
                # Direct Wi-Fi Settings.
                intent = Intent(
                    Settings.ACTION_WIFI_SETTINGS
                )

                self.set_status(
                    "Wi-Fi Settings khol raha hoon..."
                )

                self.speak(
                    "Wi-Fi Settings khol raha hoon."
                )

            elif setting_type == "bluetooth":

                intent = Intent(
                    Settings.ACTION_BLUETOOTH_SETTINGS
                )

                self.set_status(
                    "Bluetooth Settings khol raha hoon..."
                )

                self.speak(
                    "Bluetooth Settings khol raha hoon."
                )

            elif setting_type == "display":

                intent = Intent(
                    Settings.ACTION_DISPLAY_SETTINGS
                )

                self.set_status(
                    "Display Settings khol raha hoon..."
                )

                self.speak(
                    "Display Settings khol raha hoon."
                )

            elif setting_type == "battery":

                intent = Intent(
                    Settings.ACTION_BATTERY_SAVER_SETTINGS
                )

                self.set_status(
                    "Battery Settings khol raha hoon..."
                )

                self.speak(
                    "Battery Settings khol raha hoon."
                )

            elif setting_type == "location":

                intent = Intent(
                    Settings.ACTION_LOCATION_SOURCE_SETTINGS
                )

                self.set_status(
                    "Location Settings khol raha hoon..."
                )

                self.speak(
                    "Location Settings khol raha hoon."
                )

            elif setting_type == "security":

                intent = Intent(
                    Settings.ACTION_SECURITY_SETTINGS
                )

                self.set_status(
                    "Security Settings khol raha hoon..."
                )

                self.speak(
                    "Security Settings khol raha hoon."
                )

            elif setting_type == "mobile":

                intent = Intent(
                    Settings.ACTION_NETWORK_OPERATOR_SETTINGS
                )

                self.set_status(
                    "Mobile Network Settings khol raha hoon..."
                )

                self.speak(
                    "Mobile Network Settings khol raha hoon."
                )

            else:

                intent = Intent(
                    Settings.ACTION_SETTINGS
                )

                self.set_status(
                    "Settings khol raha hoon..."
                )

                self.speak(
                    "Settings khol raha hoon."
                )

            self.open_intent(
                intent
            )

        except Exception as e:

            print(
                "Settings error:",
                e
            )

            self.set_status(
                "Settings open nahi ho saka."
            )

    # ========================================================
    # CAMERA
    # ========================================================

    def open_camera(self):

        try:

            intent = Intent(
                "android.media.action.IMAGE_CAPTURE"
            )

            self.set_status(
                "Camera khol raha hoon..."
            )

            self.speak(
                "Camera khol raha hoon."
            )

            self.open_intent(
                intent
            )

        except Exception as e:

            print(
                "Camera error:",
                e
            )

            self.set_status(
                "Camera open nahi ho saka."
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

        def launch():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                intent = (
                    pm.getLaunchIntentForPackage(
                        "com.android.chrome"
                    )
                )

                if intent is None:

                    intent = Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse(
                            "https://www.google.com"
                        )
                    )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Chrome error:",
                    e
                )

                self.set_status(
                    "Chrome open nahi ho saka."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # YOUTUBE APP
    # ========================================================

    def open_youtube(self):

        self.set_status(
            "YouTube khol raha hoon..."
        )

        self.speak(
            "YouTube khol raha hoon."
        )

        def launch():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                intent = (
                    pm.getLaunchIntentForPackage(
                        "com.google.android.youtube"
                    )
                )

                if intent is None:

                    intent = Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse(
                            "https://www.youtube.com"
                        )
                    )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "YouTube error:",
                    e
                )

                self.set_status(
                    "YouTube open nahi ho saka."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # COMMAND PROCESSOR
    # ========================================================

    def process_command(
        self,
        command
    ):

        command = command.lower().strip()

        print(
            "Processing command:",
            command
        )

        # ----------------------------------------------------
        # GREETING
        # ----------------------------------------------------

        if (
            command == "hello"
            or command == "hi"
            or command == "hey"
            or "hello jarvis" in command
            or "hi jarvis" in command
            or "hey jarvis" in command
        ):

            self.set_status(
                "Hello! Main Jarvis hoon."
            )

            self.speak(
                "Hello! Main Jarvis hoon."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if (
            "what is your name" in command
            or "your name" in command
            or "tumhara naam" in command
            or "aapka naam" in command
        ):

            self.set_status(
                "Mera naam Jarvis hai."
            )

            self.speak(
                "Mera naam Jarvis hai."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        if (
            "what time" in command
            or "time kya" in command
            or "time batao" in command
            or "time bata" in command
            or command == "time"
            or "current time" in command
        ):

            self.tell_time()

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                3
            )

            return

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        if (
            "what is the date" in command
            or "what date" in command
            or "date kya" in command
            or "date batao" in command
            or "date bata" in command
            or command == "date"
            or "today date" in command
            or "today's date" in command
        ):

            self.tell_date()

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                3
            )

            return

        # ----------------------------------------------------
        # GOOGLE SEARCH
        # ----------------------------------------------------

        google_prefixes = [
            "google pe search karo ",
            "google par search karo ",
            "google me search karo ",
            "google mein search karo ",
            "google search karo ",
            "google pe ",
            "google par ",
            "google me ",
            "google mein ",
            "google search ",
            "search karo ",
            "search kar ",
            "web search karo ",
            "web search ",
            "internet par ",
            "internet pe "
        ]

        for prefix in google_prefixes:

            if command.startswith(prefix):

                query = command[
                    len(prefix):
                ].strip()

                self.google_web_search(
                    query
                )

                return

        # ----------------------------------------------------
        # YOUTUBE SEARCH
        # ----------------------------------------------------

        youtube_prefixes = [
            "youtube pe search karo ",
            "youtube par search karo ",
            "youtube me search karo ",
            "youtube mein search karo ",
            "youtube search karo ",
            "youtube pe ",
            "youtube par ",
            "youtube me ",
            "youtube mein ",
            "youtube search "
        ]

        for prefix in youtube_prefixes:

            if command.startswith(prefix):

                query = command[
                    len(prefix):
                ].strip()

                self.youtube_search(
                    query
                )

                return

        # ----------------------------------------------------
        # MUSIC SEARCH
        # ----------------------------------------------------

        music_prefixes = [
            "music pe search karo ",
            "music par search karo ",
            "music me search karo ",
            "music mein search karo ",
            "music search karo ",
            "music search ",
            "song search karo ",
            "song search ",
            "gaana search karo ",
            "gana search karo "
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

        # ----------------------------------------------------
        # WHATSAPP
        # ----------------------------------------------------

        if (
            "open whatsapp" in command
            or "whatsapp kholo" in command
            or "whatsapp khol" in command
            or command == "whatsapp"
        ):

            self.open_whatsapp()

            return

        # ----------------------------------------------------
        # CALCULATOR
        # ----------------------------------------------------

        if (
            "open calculator" in command
            or "calculator kholo" in command
            or "calculator khol" in command
            or command == "calculator"
        ):

            self.open_calculator()

            return

        # ----------------------------------------------------
        # CAMERA
        # ----------------------------------------------------

        if (
            "open camera" in command
            or "camera kholo" in command
            or "camera khol" in command
            or command == "camera"
        ):

            self.open_camera()

            return

        # ----------------------------------------------------
        # CHROME
        # ----------------------------------------------------

        if (
            "open chrome" in command
            or "chrome kholo" in command
            or "chrome khol" in command
            or command == "chrome"
        ):

            self.open_chrome()

            return

        # ----------------------------------------------------
        # YOUTUBE
        # ----------------------------------------------------

        if (
            "open youtube" in command
            or "youtube kholo" in command
            or "youtube khol" in command
            or command == "youtube"
        ):

            self.open_youtube()

            return
        # ----------------------------------------------------
        # PHONE / DIALER - v0.21
        # ----------------------------------------------------

        if (
            "open phone" in command
            or "phone kholo" in command
            or "phone khol" in command
            or "open dialer" in command
            or "dialer kholo" in command
            or "dialer khol" in command
            or command == "phone"
            or command == "dialer"
        ):

            self.open_phone()

            return

        # ----------------------------------------------------
        # DIAL NUMBER - v0.21
        # ----------------------------------------------------

        number_prefixes = [
            "dial ",
            "dial number ",
            "number dial ",
            "call ",
            "phone number "
        ]

        for prefix in number_prefixes:

            if command.startswith(prefix):

                number = command[
                    len(prefix):
                ].strip()

                # Only open the Dialer.
                # Direct call intentionally not used.
                self.dial_number(
                    number
                )

                return

        # ----------------------------------------------------
        # CONTACTS - v0.21
        # ----------------------------------------------------

        if (
            "open contacts" in command
            or "contacts kholo" in command
            or "contacts khol" in command
            or "contact kholo" in command
            or "contact khol" in command
            or command == "contacts"
            or command == "contact"
        ):

            self.open_contacts()

            return

        # ----------------------------------------------------
        # MAIN SETTINGS
        # ----------------------------------------------------

        if (
            "open settings" in command
            or "settings kholo" in command
            or "settings khol" in command
            or command == "settings"
        ):

            self.open_settings(
                "main"
            )

            return

        # ----------------------------------------------------
        # WIFI - FIXED / ROBUST
        # ----------------------------------------------------

        if (
            "open wifi" in command
            or "open wi fi" in command
            or "open wi-fi" in command
            or "wifi kholo" in command
            or "wi fi kholo" in command
            or "wi-fi kholo" in command
            or "wifi khol" in command
            or "wi fi khol" in command
            or "wi-fi khol" in command
            or "wifi settings" in command
            or "wi fi settings" in command
            or "wi-fi settings" in command
            or command == "wifi"
            or command == "wi fi"
            or command == "wi-fi"
        ):

            self.open_settings(
                "wifi"
            )

            return

        # ----------------------------------------------------
        # BLUETOOTH
        # ----------------------------------------------------

        if (
            "open bluetooth" in command
            or "bluetooth kholo" in command
            or "bluetooth khol" in command
            or "bluetooth settings" in command
            or command == "bluetooth"
        ):

            self.open_settings(
                "bluetooth"
            )

            return

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        if (
            "open display" in command
            or "display kholo" in command
            or "display khol" in command
            or "display settings" in command
        ):

            self.open_settings(
                "display"
            )

            return

        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        if (
            "open battery" in command
            or "battery kholo" in command
            or "battery khol" in command
            or "battery settings" in command
        ):

            self.open_settings(
                "battery"
            )

            return

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        if (
            "open location" in command
            or "location kholo" in command
            or "location khol" in command
            or "location settings" in command
        ):

            self.open_settings(
                "location"
            )

            return

        # ----------------------------------------------------
        # SECURITY
        # ----------------------------------------------------

        if (
            "open security" in command
            or "security kholo" in command
            or "security khol" in command
            or "security settings" in command
        ):

            self.open_settings(
                "security"
            )

            return

        # ----------------------------------------------------
        # MOBILE NETWORK
        # ----------------------------------------------------

        if (
            "mobile network" in command
            or "mobile networks" in command
            or "mobile data" in command
            or "data settings" in command
            or "mobile setting" in command
        ):

            self.open_settings(
                "mobile"
            )

            return

        # ----------------------------------------------------
        # INSTALLED APP
        # ----------------------------------------------------

        app_prefixes = [
            "open app ",
            "app kholo ",
            "app khol "
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

        # ----------------------------------------------------
        # COMMON INSTALLED APPS
        # ----------------------------------------------------

        common_apps = [
            "instagram",
            "facebook",
            "telegram",
            "spotify",
            "gmail",
            "maps",
            "google maps"
        ]

        for app_name in common_apps:

            if (
                command == app_name
                or "open " + app_name in command
                or app_name + " kholo" in command
                or app_name + " khol" in command
            ):

                self.open_installed_app(
                    app_name
                )

                return

        # ----------------------------------------------------
        # UNKNOWN COMMAND
        # ----------------------------------------------------

        self.set_status(
            "Command samajh nahi aaya."
        )

        self.speak(
            "Command samajh nahi aaya."
        )

        Clock.schedule_once(
            lambda dt:
            self.listen(),
            2
        )

    # ========================================================
    # APP STOP / CLEANUP
    # ========================================================

    def on_stop(self):

        def cleanup():

            try:

                if (
                    self.speech_recognizer
                    is not None
                ):

                    self.speech_recognizer.stopListening()

            except Exception:
                pass

            try:

                if (
                    self.speech_recognizer
                    is not None
                ):

                    self.speech_recognizer.cancel()

            except Exception:
                pass

            try:

                if (
                    self.speech_recognizer
                    is not None
                ):

                    self.speech_recognizer.destroy()

            except Exception:
                pass

            try:

                if self.tts is not None:

                    self.tts.stop()

                    self.tts.shutdown()

            except Exception:
                pass

        try:

            self.run_on_android_thread(
                cleanup
            )

        except Exception:
            pass


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    VoiceAssistant().run()
