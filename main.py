from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method

PythonActivity = autoclass("org.kivy.android.PythonActivity")
Intent = autoclass("android.content.Intent")
Uri = autoclass("android.net.Uri")
RecognizerIntent = autoclass("android.speech.RecognizerIntent")
SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
Bundle = autoclass("android.os.Bundle")
Locale = autoclass("java.util.Locale")
TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
Settings = autoclass("android.provider.Settings")
PackageManager = autoclass("android.content.pm.PackageManager")
AlarmClock = autoclass("android.provider.AlarmClock")


class MainThreadRunnable(PythonJavaClass):
    __javainterfaces__ = ["java/lang/Runnable"]

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method("()V")
    def run(self):
        try:
            self.callback()
        except Exception as e:
            print("Main thread error:", e)


class RecognitionListener(PythonJavaClass):
    __javainterfaces__ = ["android/speech/RecognitionListener"]

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method("(Landroid/os/Bundle;)V")
    def onReadyForSpeech(self, params):
        self.app.set_status("Listening...")

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
        print("Speech error:", error)

        if error == 5:
            Clock.schedule_once(
                lambda dt: self.app.listen_again(),
                0.5
            )
            return

        if error in (6, 7, 8, 9):
            Clock.schedule_once(
                lambda dt: self.app.listen_again(),
                0.8
            )
            return

        self.app.set_status("Dobara boliye...")

        Clock.schedule_once(
            lambda dt: self.app.listen_again(),
            1
        )

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):
        try:
            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )

            if (
                matches is not None
                and matches.size() > 0
            ):
                text = str(matches.get(0))

                print(
                    "Recognized:",
                    text
                )

                self.app.process_command(text)

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

            self.activity.runOnUiThread(
                MainThreadRunnable(
                    callback
                )
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

            if check_permission(
                Permission.RECORD_AUDIO
            ):
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

        if not self.check_microphone_permission():
            return

        def setup_android():

            try:

                if self.tts is None:

                    self.tts = TextToSpeech(
                        self.activity,
                        None
                    )

                    self.tts.setLanguage(
                        Locale.US
                    )

                if self.speech_recognizer is None:

                    self.speech_recognizer = (
                        SpeechRecognizer
                        .createSpeechRecognizer(
                            self.activity
                        )
                    )

                if self.listener is None:

                    self.listener = (
                        RecognitionListener(
                            self
                        )
                    )

                    self.speech_recognizer.setRecognitionListener(
                        self.listener
                    )

                if self.recognizer_intent is None:

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
            self.speech_recognizer is None
            or self.recognizer_intent is None
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

        if self.speech_recognizer is None:
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

        if self.speech_recognizer is None:
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

            self.open_intent(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(url)
                )
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

            url = (
                "https://www.google.com/search?q="
                + str(Uri.encode(query))
            )

            self.open_intent(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(url)
                )
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

            url = (
                "https://www.youtube.com/results?search_query="
                + str(Uri.encode(query))
            )

            self.open_intent(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(url)
                )
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

            url = (
                "https://music.youtube.com/search?q="
                + str(Uri.encode(query))
            )

            self.open_intent(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(url)
                )
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

                for package_name in [
                    "com.miui.calculator",
                    "com.google.android.calculator",
                    "com.android.calculator2"
                ]:

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
    # INSTALLED APP LAUNCHER - v0.22 FIXED
    # ========================================================

    def normalize_app_name(self, text):

        text = text.lower().strip()

        aliases = {
            "you tube": "youtube",
            "face book": "facebook",
            "insta gram": "instagram",
            "telegram": "telegram",
            "spot ify": "spotify",
            "g mail": "gmail",
            "google maps": "google maps"
        }

        return aliases.get(
            text,
            text
        )

    def open_installed_app(
        self,
        app_name
    ):

        app_name = self.normalize_app_name(
            app_name
        )

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

                # ------------------------------------------------
                # v0.22 FIX:
                # Launcher activities ko directly search karna.
                # Isse sirf hard-coded Instagram nahi chalega.
                # ------------------------------------------------

                launcher_intent = Intent(
                    Intent.ACTION_MAIN
                )

                launcher_intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                activities = (
                    pm.queryIntentActivities(
                        launcher_intent,
                        0
                    )
                )

                requested = (
                    app_name
                    .lower()
                    .strip()
                )

                exact = []
                prefix = []
                contains = []

                for i in range(
                    activities.size()
                ):

                    try:

                        item = activities.get(i)

                        info = item.activityInfo

                        label = str(
                            info.loadLabel(pm)
                        ).strip()

                        package_name = str(
                            info.packageName
                        ).strip()

                        label_lower = (
                            label.lower()
                        )

                        entry = (
                            label,
                            package_name,
                            info.name
                        )

                        if (
                            label_lower
                            ==
                            requested
                        ):

                            exact.append(
                                entry
                            )

                        elif (
                            label_lower.startswith(
                                requested
                            )
                        ):

                            prefix.append(
                                entry
                            )

                        elif (
                            requested
                            in label_lower
                        ):

                            contains.append(
                                entry
                            )

                    except Exception as e:

                        print(
                            "App scan error:",
                            e
                        )

                candidates = (
                    exact +
                    prefix +
                    contains
                )

                seen = set()

                for (
                    label,
                    package_name,
                    activity_name
                ) in candidates:

                    key = (
                        package_name +
                        "/" +
                        activity_name
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    try:

                        intent = Intent(
                            Intent.ACTION_MAIN
                        )

                        intent.addCategory(
                            Intent.CATEGORY_LAUNCHER
                        )

                        intent.setClassName(
                            package_name,
                            activity_name
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
                            "App launch error:",
                            label,
                            package_name,
                            e
                        )

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

                self.speak(
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

                intent = Intent(
                    Intent.ACTION_DIAL,
                    Uri.parse(
                        "tel:" +
                        clean_number
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

                try:

                    ContactsContract = autoclass(
                        "android.provider.ContactsContract"
                    )

                    intent = Intent(
                        Intent.ACTION_VIEW,
                        ContactsContract
                        .Contacts
                        .CONTENT_URI
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
    # SMS / MESSAGES - v0.22
    # ========================================================

    def open_messages(self):

        self.set_status(
            "Messages khol raha hoon..."
        )

        self.speak(
            "Messages khol raha hoon."
        )

        def launch_messages():

            try:

                pm = (
                    self.activity
                    .getPackageManager()
                )

                message_packages = [
                    "com.google.android.apps.messaging",
                    "com.android.mms",
                    "com.android.messaging",
                    "com.google.android.messaging"
                ]

                for package_name in message_packages:

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
                            "Messages package error:",
                            package_name,
                            e
                        )

                try:

                    intent = Intent(
                        Intent.ACTION_MAIN
                    )

                    intent.addCategory(
                        "android.intent.category.APP_MESSAGING"
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
                        "Messages category error:",
                        e
                    )

                self.set_status(
                    "Messages app nahi mili."
                )

                self.speak(
                    "Messages app nahi mili."
                )

            except Exception as e:

                print(
                    "Messages error:",
                    e
                )

                self.set_status(
                    "Messages open nahi ho saka."
                )

                self.speak(
                    "Messages open nahi ho saka."
                )

        self.run_on_android_thread(
            launch_messages
        )

    # ========================================================
    # SMS COMPOSER - v0.22
    # ========================================================

    def send_sms(
        self,
        number,
        message
    ):

        number = number.strip()
        message = message.strip()

        if not number:

            self.set_status(
                "SMS number nahi mila."
            )

            self.speak(
                "SMS number nahi mila."
            )

            return

        if not message:

            self.set_status(
                "SMS message nahi mila."
            )

            self.speak(
                "SMS message nahi mila."
            )

            return

        clean_number = ""

        for char in number:

            if (
                char.isdigit()
                or char == "+"
            ):

                clean_number += char

        if not clean_number:

            self.set_status(
                "Valid mobile number nahi mila."
            )

            self.speak(
                "Valid mobile number nahi mila."
            )

            return

        self.set_status(
            "SMS compose kar raha hoon..."
        )

        self.speak(
            "SMS message ready kar raha hoon."
        )

        def launch_sms():

            try:

                intent = Intent(
                    Intent.ACTION_SENDTO,
                    Uri.parse(
                        "smsto:" +
                        clean_number
                    )
                )

                intent.putExtra(
                    "sms_body",
                    message
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "SMS compose error:",
                    e
                )

                self.set_status(
                    "SMS compose open nahi ho saka."
                )

                self.speak(
                    "SMS compose open nahi ho saka."
                )

        self.run_on_android_thread(
            launch_sms
        )



    # ========================================================
    # SETTINGS / ANDROID ACTIONS
    # ========================================================

    def open_settings(
        self,
        setting_type
    ):

        try:

            actions = {

                "main": (
                    Settings.ACTION_SETTINGS,
                    "Settings"
                ),

                "wifi": (
                    Settings.ACTION_WIFI_SETTINGS,
                    "Wi-Fi Settings"
                ),

                "bluetooth": (
                    Settings.ACTION_BLUETOOTH_SETTINGS,
                    "Bluetooth Settings"
                ),

                "display": (
                    Settings.ACTION_DISPLAY_SETTINGS,
                    "Display Settings"
                ),

                "battery": (
                    Settings.ACTION_BATTERY_SAVER_SETTINGS,
                    "Battery Settings"
                ),

                "location": (
                    Settings.ACTION_LOCATION_SOURCE_SETTINGS,
                    "Location Settings"
                ),

                "security": (
                    Settings.ACTION_SECURITY_SETTINGS,
                    "Security Settings"
                ),

                "mobile": (
                    Settings.ACTION_NETWORK_OPERATOR_SETTINGS,
                    "Mobile Network Settings"
                )
            }

            action, title = actions.get(
                setting_type,
                (
                    Settings.ACTION_SETTINGS,
                    "Settings"
                )
            )

            self.set_status(
                title +
                " khol raha hoon..."
            )

            self.speak(
                title +
                " khol raha hoon."
            )

            self.open_intent(
                Intent(action)
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

            self.set_status(
                "Camera khol raha hoon..."
            )

            self.speak(
                "Camera khol raha hoon."
            )

            self.open_intent(
                Intent(
                    "android.media.action.IMAGE_CAPTURE"
                )
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

        command = (
            command
            .lower()
            .strip()
        )

        print(
            "Processing command:",
            command
        )

        # ----------------------------------------------------
        # GREETING
        # ----------------------------------------------------

        if (
            command in (                
                "hello",
                "hi",
                "hey"
            )
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
        # ALARM + TIMER - v0.23
        # ----------------------------------------------------

        if (
            "alarm" in command
            and (
                "laga" in command
                or "lagao" in command
                or "alarm" in command
            )
        ):

            alarm_command = command
            alarm_command = alarm_command.replace(
                "alarm", " "
            )
            alarm_command = alarm_command.replace(
                "laga do", " "
            )
            alarm_command = alarm_command.replace(
                "lagao", " "
            )
            alarm_command = alarm_command.replace(
                "laga", " "
            )
            alarm_command = alarm_command.replace(
                "ka", " "
            )
            alarm_command = alarm_command.replace(
                "baje", " "
            )
            alarm_command = alarm_command.replace(
                "subah", " subah "
            )
            alarm_command = alarm_command.replace(
                "raat", " raat "
            )
            alarm_command = alarm_command.replace(
                "shaam", " shaam "
            )
            alarm_command = alarm_command.replace(
                "dopahar", " dopahar "
            )

            tokens = alarm_command.split()
            hour = None
            minute = 0
            period = ""

            for token in tokens:

                if token in (
                    "am",
                    "pm"
                ):
                    period = token

            for token in tokens:

                if ":" in token:

                    time_parts = token.split(":")

                    if len(time_parts) >= 2:

                        try:
                            hour = int(time_parts[0])
                            minute = int(
                                time_parts[1]
                            )
                            break
                        except Exception:
                            pass

                elif token.isdigit():

                    try:
                        value = int(token)
                    except Exception:
                        continue

                    if hour is None:
                        hour = value

            if hour is not None:

                if hour < 0 or hour > 23:

                    hour = None

                if minute < 0 or minute > 59:

                    hour = None

            if hour is not None:

                if period == "pm" and hour < 12:
                    hour += 12

                elif period == "am" and hour == 12:
                    hour = 0

                elif "raat" in tokens and hour < 12:

                    hour += 12

                elif (
                    "subah" in tokens
                    and hour == 12
                ):
                    hour = 0

                def launch_alarm():

                    try:

                        intent = Intent(
                            AlarmClock.ACTION_SET_ALARM
                        )

                        intent.putExtra(
                            AlarmClock.EXTRA_HOUR,
                            hour
                        )

                        intent.putExtra(
                            AlarmClock.EXTRA_MINUTES,
                            minute
                        )

                        intent.putExtra(
                            AlarmClock.EXTRA_MESSAGE,
                            "Jarvis Alarm"
                        )

                        intent.addFlags(
                            Intent.FLAG_ACTIVITY_NEW_TASK
                        )

                        self.activity.startActivity(
                            intent
                        )

                        self.set_status(
                            "Alarm set ho raha hai."
                        )

                        self.speak(
                            "Alarm set kar raha hoon."
                        )

                    except Exception as e:

                        print(
                            "Alarm error:",
                            e
                        )

                        self.set_status(
                            "Alarm set nahi ho saka."
                        )

                        self.speak(
                            "Alarm set nahi ho saka."
                        )

                self.run_on_android_thread(
                    launch_alarm
                )

                return

            self.set_status(
                "Alarm ka sahi time boliye."
            )

            self.speak(
                "Alarm ka sahi time boliye."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

        if (
            "timer" in command
            and (
                "laga" in command
                or "lagao" in command
                or "timer" in command
            )
        ):

            timer_command = command
            timer_command = timer_command.replace(
                "timer", " "
            )
            timer_command = timer_command.replace(
                "laga do", " "
            )
            timer_command = timer_command.replace(
                "lagao", " "
            )
            timer_command = timer_command.replace(
                "laga", " "
            )
            timer_command = timer_command.replace(
                "ka", " "
            )

            tokens = timer_command.split()
            amount = None
            unit = ""

            for index, token in enumerate(tokens):

                if token.isdigit():

                    amount = int(token)

                    if index + 1 < len(tokens):
                        unit = tokens[index + 1]

                    break

            minute_units = (
                "minute",
                "minutes",
                "min"
            )

            second_units = (
                "second",
                "seconds",
                "sec",
                "secs"
            )

            hour_units = (
                "hour",
                "hours",
                "ghanta",
                "ghante",
                "ghanton"
            )

            seconds = None

            if amount is not None:

                if unit in minute_units:
                    seconds = amount * 60

                elif unit in second_units:
                    seconds = amount

                elif unit in hour_units:
                    seconds = amount * 3600

            if seconds is not None and seconds > 0:

                def launch_timer():

                    try:

                        intent = Intent(
                            AlarmClock.ACTION_SET_TIMER
                        )

                        intent.putExtra(
                            AlarmClock.EXTRA_LENGTH,
                            seconds
                        )

                        intent.putExtra(
                            AlarmClock.EXTRA_MESSAGE,
                            "Jarvis Timer"
                        )

                        intent.addFlags(
                            Intent.FLAG_ACTIVITY_NEW_TASK
                        )

                        self.activity.startActivity(
                            intent
                        )

                        self.set_status(
                            "Timer set ho raha hai."
                        )

                        self.speak(
                            "Timer set kar raha hoon."
                        )

                    except Exception as e:

                        print(
                            "Timer error:",
                            e
                        )

                        self.set_status(
                            "Timer set nahi ho saka."
                        )

                        self.speak(
                            "Timer set nahi ho saka."
                        )

                self.run_on_android_thread(
                    launch_timer
                )

                return

            self.set_status(
                "Timer ka sahi samay boliye."
            )

            self.speak(
                "Timer ka sahi samay boliye."
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

                self.google_web_search(
                    command[
                        len(prefix):
                    ].strip()
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

                self.youtube_search(
                    command[
                        len(prefix):
                    ].strip()
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

                    self.music_search(
                        command[
                            len(prefix):
                        ].strip()
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
                or command in (
                    "phone",
                    "dialer"
                )
            ):

                self.open_phone()

                return

            # ----------------------------------------------------
            # DIAL NUMBER - v0.21
            # ----------------------------------------------------

            for prefix in [
                "dial ",
                "dial number ",
                "number dial ",
                "call ",
                "phone number "
            ]:

                if command.startswith(prefix):

                    self.dial_number(
                        command[
                            len(prefix):
                        ].strip()
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
                or command in (
                    "contacts",
                    "contact"
                )
            ):

                self.open_contacts()

                return

            # ----------------------------------------------------
            # SMS / MESSAGES - v0.22
            # ----------------------------------------------------

            if (
                "open messages" in command
                or "messages kholo" in command
                or "messages khol" in command
                or "message kholo" in command
                or "message khol" in command
                or "open sms" in command
                or "sms kholo" in command
                or "sms khol" in command
                or command in (
                    "messages",
                    "message",
                    "sms"
                )
            ):

                self.open_messages()

                return

            # ----------------------------------------------------
            # SMS COMPOSE - v0.22
            # ----------------------------------------------------

            for prefix in [
                "send sms to ",
                "send message to ",
                "sms to ",
                "message to ",
                "text to "
            ]:

                if command.startswith(prefix):

                    remaining = command[
                        len(prefix):
                    ].strip()

                    number_part = ""
                    message_part = ""

                    markers = [
                        " message ",
                        " sms ",
                        " saying ",
                        " bolo "
                    ]

                    found = None

                    for marker in markers:

                        index = remaining.find(
                            marker
                        )

                        if (
                            index != -1
                            and (
                                found is None
                                or index < found[0]
                            )
                        ):

                            found = (
                                index,
                                marker
                            )

                    if found:

                        index, marker = found

                        number_part = (
                            remaining[
                                :index
                            ].strip()
                        )

                        message_part = (
                            remaining[
                                index +
                                len(marker):
                            ].strip()
                        )

                    else:

                        parts = remaining.split(
                            " ",
                            1
                        )

                        if len(parts) == 2:

                            number_part = (
                                parts[0].strip()
                            )

                            message_part = (
                                parts[1].strip()
                            )

                    if (
                        number_part
                        and message_part
                    ):

                        self.send_sms(
                            number_part,
                            message_part
                        )

                    else:

                        self.set_status(
                            "Number aur message dono boliye."
                        )

                        self.speak(
                            "Number aur message dono boliye."
                        )

                        Clock.schedule_once(
                            lambda dt:
                            self.listen(),
                            2
                        )

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
            # WIFI
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
                or command in (
                    "wifi",
                    "wi fi",
                    "wi-fi"
                )
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

            for prefix in [
                "open app ",
                "app kholo ",
                "app khol "
            ]:

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
        # GENERAL INSTALLED APP VOICE LAUNCH
        # v0.22 FIX
        # ----------------------------------------------------

        general_app_name = ""

        if command.startswith("open "):

            general_app_name = command[
                5:
            ].strip()

        elif command.startswith("khol "):

            general_app_name = command[
                5:
            ].strip()

        elif command.startswith("kholo "):

            general_app_name = command[
                6:
            ].strip()

        if general_app_name:

            blocked = [
                "settings",
                "wifi",
                "wi fi",
                "wi-fi",
                "bluetooth",
                "display",
                "battery",
                "location",
                "security",
                "mobile network",
                "mobile data",
                "phone",
                "dialer",
                "contacts",
                "contact",
                "messages",
                "message",
                "sms"
            ]

            if general_app_name not in blocked:

                self.open_installed_app(
                    general_app_name
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
