from kivy.app import App
import re
import os
import json
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
AlarmManager = autoclass("android.app.AlarmManager")
PendingIntent = autoclass("android.app.PendingIntent")
Context = autoclass("android.content.Context")
Build = autoclass("android.os.Build")
BuildVersion = autoclass("android.os.Build$VERSION")
System = autoclass("java.lang.System")
SystemClock = autoclass("android.os.SystemClock")
Calendar = autoclass("java.util.Calendar")
JarvisAlarmReceiver = autoclass(
    "org.myassistant.myvoiceassistant.JarvisAlarmReceiver"
)


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
            except Exception as e:
                print("Stop listening error:", e)

        self.run_on_android_thread(stop)

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

                # Keep the smsto URI limited to the recipient. Several Android
                # messaging apps ignore a body embedded in the URI query, while
                # the standard sms_body extra is widely supported.
                sms_uri = Uri.parse("smsto:" + clean_number + "?body=" + Uri.encode(message))
                intent = Intent(Intent.ACTION_SENDTO, sms_uri)
                intent.putExtra("sms_body", message)
                intent.putExtra("body", message)
                intent.putExtra(Intent.EXTRA_TEXT, message)
                print("JARVIS SMS COMPOSE:", clean_number, repr(message))

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
    # ANDROID ALARM MANAGER - v0.23 FIX
    # ========================================================

    def _schedule_android_alarm(self, hour, minute):
        """Schedule an Android AlarmManager alarm through the bundled receiver."""
        def schedule():
            try:
                target_hour, target_minute = int(hour), int(minute)
                if not (0 <= target_hour <= 23 and 0 <= target_minute <= 59):
                    raise ValueError("Invalid alarm time")
                cal = Calendar.getInstance()
                cal.set(Calendar.HOUR_OF_DAY, target_hour)
                cal.set(Calendar.MINUTE, target_minute)
                cal.set(Calendar.SECOND, 0)
                cal.set(Calendar.MILLISECOND, 0)
                now_ms = int(System.currentTimeMillis())
                trigger_ms = int(cal.getTimeInMillis())
                if trigger_ms <= now_ms:
                    cal.add(Calendar.DAY_OF_YEAR, 1)
                    trigger_ms = int(cal.getTimeInMillis())
                manager = self.activity.getSystemService(Context.ALARM_SERVICE)
                alarm_intent = Intent(self.activity, JarvisAlarmReceiver)
                alarm_intent.putExtra("jarvis_type", "alarm")
                alarm_intent.putExtra("jarvis_message", "JARVIS alarm")
                flags = PendingIntent.FLAG_UPDATE_CURRENT
                if int(BuildVersion.SDK_INT) >= 23:
                    flags |= PendingIntent.FLAG_IMMUTABLE
                pending = PendingIntent.getBroadcast(self.activity, 9001, alarm_intent, flags)
                if int(BuildVersion.SDK_INT) >= 23:
                    manager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, trigger_ms, pending)
                else:
                    manager.setExact(AlarmManager.RTC_WAKEUP, trigger_ms, pending)
                from datetime import datetime
                shown = datetime.fromtimestamp(trigger_ms / 1000.0).strftime("%I:%M %p")
                self.set_status("JARVIS alarm schedule hua: " + shown)
                self.speak("JARVIS alarm schedule ho gaya " + shown)
                print("JARVIS ALARM SCHEDULED:", shown, trigger_ms)
            except Exception as e:
                print("JARVIS ALARM SCHEDULING ERROR:", repr(e))
                self.set_status("Alarm schedule nahi hua: " + str(e))
                self.speak("Alarm schedule nahi ho saka. Error screen par check karein.")
        self.run_on_android_thread(schedule)

    def _schedule_android_timer(self, seconds):
        """Schedule a wake-up timer through the bundled AlarmManager receiver."""
        def schedule():
            try:
                timer_seconds = int(seconds)
                if timer_seconds <= 0 or timer_seconds > 86400:
                    raise ValueError("Timer must be between 1 and 86400 seconds")
                manager = self.activity.getSystemService(Context.ALARM_SERVICE)
                timer_intent = Intent(self.activity, JarvisAlarmReceiver)
                timer_intent.putExtra("jarvis_type", "timer")
                timer_intent.putExtra("jarvis_message", "JARVIS timer complete")
                flags = PendingIntent.FLAG_UPDATE_CURRENT
                if int(BuildVersion.SDK_INT) >= 23:
                    flags |= PendingIntent.FLAG_IMMUTABLE
                pending = PendingIntent.getBroadcast(self.activity, 9002, timer_intent, flags)
                trigger_ms = int(SystemClock.elapsedRealtime()) + timer_seconds * 1000
                if int(BuildVersion.SDK_INT) >= 23:
                    manager.setExactAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, trigger_ms, pending)
                else:
                    manager.setExact(AlarmManager.ELAPSED_REALTIME_WAKEUP, trigger_ms, pending)
                self.set_status("JARVIS timer schedule hua: %d seconds" % timer_seconds)
                self.speak("JARVIS timer start ho gaya. %d seconds." % timer_seconds)
                print("JARVIS TIMER SCHEDULED:", timer_seconds, trigger_ms)
            except Exception as e:
                print("JARVIS TIMER SCHEDULING ERROR:", repr(e))
                self.set_status("Timer start nahi hua: " + str(e))
                self.speak("Timer start nahi ho saka. Error screen par check karein.")
        self.run_on_android_thread(schedule)

    # ========================================================
    # CALENDAR + REMINDERS - v0.24
    # Opens Android Calendar event editor so the user can review/save it.
    # ========================================================

    def open_calendar(self):
        def launch():
            try:
                calendar_intent = Intent(Intent.ACTION_MAIN)
                calendar_intent.addCategory("android.intent.category.APP_CALENDAR")
                calendar_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                self.activity.startActivity(calendar_intent)
                self.set_status("Calendar khol raha hoon...")
                self.speak("Calendar khol raha hoon.")
            except Exception as e:
                print("Calendar open error:", repr(e))
                try:
                    self.activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("content://com.android.calendar/time")))
                except Exception as inner:
                    print("Calendar fallback error:", repr(inner))
                    self.set_status("Calendar app nahi khul saka.")
                    self.speak("Calendar app nahi khul saka.")
        self.run_on_android_thread(launch)

    def create_calendar_reminder(self, command):
        """Create a prefilled event in Android Calendar; user confirms saving it."""
        try:
            import re
            from datetime import datetime, timedelta

            cleaned = command.strip()
            prefixes = [
                "jarvis remind me to ", "remind me to ", "remind me ",
                "jarvis reminder ", "reminder ", "yaad dilana ",
                "yaad dilao ", "mujhe yaad dilana ", "mujhe yaad dilao "
            ]
            title = cleaned
            for prefix in prefixes:
                if title.startswith(prefix):
                    title = title[len(prefix):].strip()
                    break

            # Strip the command phrase first, then remove date/time expressions.
            title = re.sub(r"^.*?\bremind me to\b", "", title, flags=re.IGNORECASE).strip()
            title = re.sub(r"\b(?:tomorrow|today|kal|aaj)\b", " ", title, flags=re.IGNORECASE)
            title = re.sub(r"\b(?:at|on|ko|subah|shaam|raat|baje)\b", " ", title, flags=re.IGNORECASE)
            title = re.sub(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", " ", title, flags=re.IGNORECASE)
            title = re.sub(r"\b\d{1,2}:\d{2}\b", " ", title)
            title = re.sub(r"\s+", " ", title).strip(" ,.-")
            if not title:
                title = "JARVIS Reminder"

            now = datetime.now()
            target = now + timedelta(hours=1)
            if "tomorrow" in command.lower() or "kal" in command.lower():
                target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            elif "today" in command.lower() or "aaj" in command.lower():
                target = now + timedelta(hours=1)

            match = re.search(
                r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|\b(\d{1,2}):(\d{2})\b",
                command,
                flags=re.IGNORECASE,
            )
            if match:
                if match.group(1) is not None:
                    hour = int(match.group(1))
                    minute = int(match.group(2) or 0)
                    period = (match.group(3) or "").lower()
                else:
                    hour = int(match.group(4))
                    minute = int(match.group(5) or 0)
                    period = ""
                if period == "pm" and hour < 12:
                    hour += 12
                elif period == "am" and hour == 12:
                    hour = 0
                elif period == "" and hour <= 12 and ("shaam" in command.lower() or "raat" in command.lower()):
                    if hour < 12:
                        hour += 12
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    day = now.date() + timedelta(days=1 if ("tomorrow" in command.lower() or "kal" in command.lower()) else 0)
                    target = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
                    if target <= now and not ("tomorrow" in command.lower() or "kal" in command.lower()):
                        target += timedelta(days=1)

            begin_ms = int(target.timestamp() * 1000)
            end_ms = begin_ms + 30 * 60 * 1000
            Events = autoclass("android.provider.CalendarContract$Events")
            CalendarContract = autoclass("android.provider.CalendarContract")
            intent = Intent(Intent.ACTION_INSERT)
            intent.setData(Events.CONTENT_URI)
            intent.putExtra(Events.TITLE, title)
            intent.putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, begin_ms)
            intent.putExtra(CalendarContract.EXTRA_EVENT_END_TIME, end_ms)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self.activity.startActivity(intent)
            self.set_status("Calendar mein reminder review karke Save karein: " + title)
            self.speak("Calendar khol diya hai. Reminder check karke save kar dijiye.")
            print("JARVIS CALENDAR REMINDER PREFILL:", title, target.isoformat())
        except Exception as e:
            print("Calendar reminder error:", repr(e))
            self.set_status("Reminder editor nahi khul saka: " + str(e))
            self.speak("Reminder editor nahi khul saka. Calendar mein manually reminder banaiye.")

    # ========================================================
    # VOICE NOTES - v0.25
    # Notes are stored locally inside the app's private data folder.
    # ========================================================

    def _voice_notes_path(self):
        app = App.get_running_app()
        return os.path.join(app.user_data_dir, "jarvis_voice_notes.json")

    def _load_voice_notes(self):
        path = self._voice_notes_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError, TypeError):
            return []

    def _save_voice_note(self, note_text):
        note_text = " ".join(str(note_text).split()).strip(" .,!?")
        if not note_text:
            self.set_status("Note ka text nahi mila.")
            self.speak("Kya note save karna hai? Note ke baad boliye.")
            return
        notes = self._load_voice_notes()
        notes.append(note_text)
        path = self._voice_notes_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            self.set_status("Voice note save ho gaya. Total notes: " + str(len(notes)))
            self.speak("Note save ho gaya.")
            print("JARVIS VOICE NOTE SAVED:", note_text)
        except Exception as e:
            print("JARVIS VOICE NOTE SAVE ERROR:", repr(e))
            self.set_status("Note save nahi ho saka: " + str(e))
            self.speak("Note save nahi ho saka.")

    def _show_voice_notes(self):
        notes = self._load_voice_notes()
        if not notes:
            self.set_status("Abhi koi voice note save nahi hai.")
            self.speak("Abhi koi voice note save nahi hai.")
            return
        recent = notes[-5:]
        spoken = "Aapke " + str(len(notes)) + " notes hain. "
        start_num = len(notes) - len(recent) + 1
        spoken += " ".join("Note " + str(start_num + i) + ": " + text for i, text in enumerate(recent))
        self.set_status("Saved voice notes: " + str(len(notes)) + ". Latest notes spoken aloud.")
        self.speak(spoken)
        print("JARVIS VOICE NOTES:", notes)

    def _delete_last_voice_note(self):
        notes = self._load_voice_notes()
        if not notes:
            self.set_status("Delete karne ke liye koi note nahi hai.")
            self.speak("Delete karne ke liye koi note nahi hai.")
            return
        removed = notes.pop()
        try:
            path = self._voice_notes_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            self.set_status("Aakhri voice note delete ho gaya.")
            self.speak("Aakhri note delete ho gaya.")
            print("JARVIS VOICE NOTE DELETED:", removed)
        except Exception as e:
            print("JARVIS VOICE NOTE DELETE ERROR:", repr(e))
            self.set_status("Note delete nahi ho saka: " + str(e))
            self.speak("Note delete nahi ho saka.")

    def _search_voice_notes(self, query):
        query = " ".join(str(query).lower().split()).strip(" .,!?:;")
        notes = self._load_voice_notes()
        if not query:
            self.set_status("Kis note ko dhoondhna hai, uska naam boliye.")
            self.speak("Kis note ko dhoondhna hai? Kuch shabd boliye.")
            return
        matches = [(i, n) for i, n in enumerate(notes) if query in n.lower()]
        if not matches:
            self.set_status("Is shabd se koi note nahi mila: " + query)
            self.speak("Is shabd se koi note nahi mila.")
            return
        spoken = " " .join("Note " + str(i + 1) + ": " + note for i, note in matches[:5])
        self.set_status(str(len(matches)) + " matching voice note(s) mile.")
        self.speak(str(len(matches)) + " matching notes mile. " + spoken)
        print("JARVIS VOICE NOTE SEARCH:", query, matches)

    def _delete_matching_voice_note(self, query):
        query = " ".join(str(query).lower().split()).strip(" .,!?:;")
        notes = self._load_voice_notes()
        if not query:
            self.set_status("Kaunsa note delete karna hai, uske kuch shabd boliye.")
            self.speak("Kaunsa note delete karna hai? Uske kuch shabd boliye.")
            return
        matches = [i for i, n in enumerate(notes) if query in n.lower()]
        if not matches:
            self.set_status("Delete karne ke liye matching note nahi mila.")
            self.speak("Matching note nahi mila, kuch aur shabd boliye.")
            return
        if len(matches) > 1:
            self.set_status(str(len(matches)) + " notes match hue. Aur specific shabd boliye.")
            self.speak(str(len(matches)) + " notes match hue. Galat note delete na ho, isliye aur specific shabd boliye.")
            return
        index = matches[0]
        removed = notes.pop(index)
        try:
            with open(self._voice_notes_path(), "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            self.set_status("Matching note delete ho gaya.")
            self.speak("Matching note delete ho gaya.")
            print("JARVIS VOICE NOTE DELETED BY SEARCH:", removed)
        except Exception as e:
            print("JARVIS VOICE NOTE DELETE ERROR:", repr(e))
            self.set_status("Note delete nahi ho saka: " + str(e))
            self.speak("Note delete nahi ho saka.")

    def _export_voice_notes(self):
        notes = self._load_voice_notes()
        if not notes:
            self.set_status("Export karne ke liye koi note nahi hai.")
            self.speak("Export karne ke liye koi note nahi hai.")
            return
        content = "JARVIS VOICE NOTES\n==================\n\n" + "\n\n".join(
            str(i + 1) + ". " + note for i, note in enumerate(notes)
        ) + "\n"
        try:
            export_path = os.path.join(App.get_running_app().user_data_dir, "JARVIS_Voice_Notes.txt")
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(content)
            # Share sheet lets the user send/save the readable text in a compatible app.
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_SUBJECT, "JARVIS Voice Notes")
            intent.putExtra(Intent.EXTRA_TEXT, content)
            chooser = Intent.createChooser(intent, "JARVIS Voice Notes - Share or Save")
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self.activity.startActivity(chooser)
            self.set_status("Notes ki TXT copy taiyar hai; share/save option khula hai.")
            self.speak("Aapke notes ki text copy taiyar hai. Ab share ya save kar sakte hain.")
            print("JARVIS VOICE NOTES EXPORTED:", export_path)
        except Exception as e:
            print("JARVIS VOICE NOTES EXPORT ERROR:", repr(e))
            self.set_status("TXT export nahi ho saka: " + str(e))
            self.speak("Text export nahi ho saka.")

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
        # VOICE NOTES - v0.25 (alarm/timer/reminder untouched)
        # ----------------------------------------------------
        note_export_phrases = (
            "export notes", "export my notes", "save notes as text",
            "notes export karo", "notes ki file banao", "notes share karo",
            "text file banao", "txt file banao"
        )
        if any(phrase in command for phrase in note_export_phrases):
            self._export_voice_notes()
            return

        # Specific search/delete is checked before general notes commands.
        for prefix in ("search note ", "find note ", "search my notes for ", "note dhoondo ", "note dhundo ", "notes mein dhoondo "):
            if command.startswith(prefix):
                self._search_voice_notes(command[len(prefix):])
                return
        for prefix in ("delete note ", "remove note ", "delete the note ", "note hatao ", "note delete karo "):
            if command.startswith(prefix):
                self._delete_matching_voice_note(command[len(prefix):])
                return

        note_show_phrases = (
            "show notes", "read notes", "my notes", "voice notes",
            "mere notes", "notes dikhao", "notes padho", "saved notes",
            "show my notes", "mere voice notes"
        )
        note_delete_phrases = (
            "delete last note", "delete my last note", "last note delete",
            "aakhri note delete", "akhri note delete", "last note hatao",
            "aakhri note hatao", "note delete karo"
        )
        if any(phrase in command for phrase in note_show_phrases):
            self._show_voice_notes()
            return
        if any(phrase in command for phrase in note_delete_phrases):
            self._delete_last_voice_note()
            return

        note_prefixes = (
            "take a note", "take note", "save a note", "save note",
            "write a note", "write note", "note down", "remember this",
            "voice note", "make a note", "note karo", "note kar lo",
            "likh lo", "likh lena", "yaad rakhna"
        )
        for prefix in note_prefixes:
            if command == prefix:
                self.set_status("Note boliye, main save kar dunga.")
                self.speak("Note boliye, main save kar dunga.")
                return
            if command.startswith(prefix + " "):
                note_text = command[len(prefix):].strip(" :,-")
                self._save_voice_note(note_text)
                return

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
        # CALENDAR + REMINDERS - v0.24
        # ----------------------------------------------------

        if command in ("calendar", "open calendar", "calendar kholo", "calendar khol", "calendar open karo", "calendar khol do"):
            self.open_calendar()
            return

        reminder_phrases = (
            "remind me", "reminder", "yaad dilana", "yaad dilao",
            "mujhe yaad dilana", "mujhe yaad dilao", "jarvis remind"
        )
        if any(phrase in command for phrase in reminder_phrases):
            self.create_calendar_reminder(command)
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

                self._schedule_android_alarm(hour, minute)

                return

            diagnostic_message = (
                "ALARM PARSE ERROR | command=" +
                command +
                " | tokens=" +
                str(tokens) +
                " | hour=" +
                str(hour) +
                " | minute=" +
                str(minute) +
                " | period=" +
                str(period)
            )

            print(diagnostic_message)

            self.set_status(
                diagnostic_message
            )

            self.speak(
                "Alarm command samajh nahi aaya. " +
                "Command screen par dekhiye."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen(),
                2
            )

            return

    # ----------------------------------------------------
        # TIMER - v0.24 REPAIR
        # ----------------------------------------------------

        timer_unit_words = (
            "minute", "minutes", "min", "mins",
            "minit", "minits", "mint", "mints",
            "second", "seconds", "sec", "secs",
            "sekand", "sekands",
            "hour", "hours",
            "ghanta", "ghante", "ghanton"
        )

        has_timer_word = (
            "timer" in command.split()
            or "countdown" in command.split()
        )

        has_duration_word = any(
            word in command.split()
            for word in timer_unit_words
        )

        if has_timer_word or (
            "countdown" in command and has_duration_word
        ):

            print(
                "JARVIS TIMER COMMAND RECEIVED:",
                repr(command)
            )

            number_words = {
                "one": 1, "ek": 1,
                "two": 2, "do": 2,
                "three": 3, "teen": 3,
                "four": 4, "char": 4,
                "five": 5, "paanch": 5, "panch": 5,
                "six": 6, "chhe": 6, "che": 6,
                "seven": 7, "saat": 7,
                "eight": 8, "aath": 8,
                "nine": 9, "nau": 9,
                "ten": 10, "das": 10,
                "eleven": 11, "gyarah": 11,
                "twelve": 12, "barah": 12,
                "fifteen": 15, "pandrah": 15,
                "twenty": 20, "bees": 20,
                "thirty": 30, "tees": 30,
                "forty": 40, "chalis": 40,
                "fifty": 50, "pachaas": 50
            }

            seconds = None

            match = re.search(
                r"\b(\d+)\s*"
                r"(seconds?|secs?|sekands?|"
                r"minutes?|mins?|minits?|mints?|"
                r"hours?|ghante|ghanton|ghanta)\b",
                command
            )

            if match:
                amount = int(match.group(1))
                unit = match.group(2)

                if unit in (
                    "second", "seconds", "sec", "secs",
                    "sekand", "sekands"
                ):
                    seconds = amount

                elif unit in (
                    "minute", "minutes", "min", "mins",
                    "minit", "minits", "mint", "mints"
                ):
                    seconds = amount * 60

                else:
                    seconds = amount * 3600

            else:
                tokens = command.split()

                for index, token in enumerate(tokens):
                    if token not in number_words:
                        continue

                    if index + 1 >= len(tokens):
                        continue

                    unit = tokens[index + 1]
                    amount = number_words[token]

                    if unit in (
                        "second", "seconds", "sec", "secs",
                        "sekand", "sekands"
                    ):
                        seconds = amount

                    elif unit in (
                        "minute", "minutes", "min", "mins",
                        "minit", "minits", "mint", "mints"
                    ):
                        seconds = amount * 60

                    elif unit in (
                        "hour", "hours", "ghanta",
                        "ghante", "ghanton"
                    ):
                        seconds = amount * 3600

                    if seconds is not None:
                        break

            if seconds is not None and 0 < seconds <= 86400:
                print(
                    "JARVIS TIMER PARSED:",
                    repr(command),
                    "seconds=",
                    seconds
                )

                self._schedule_android_timer(seconds)

            else:
                print(
                    "JARVIS TIMER PARSE FAILED:",
                    repr(command),
                    "seconds=",
                    seconds
                )

                self.set_status(
                    "Timer duration samajh nahi aayi: " + command
                )

                self.speak(
                    "Timer ka samay samajh nahi aaya. "
                    "Das seconds ka timer bolkar dekhiye."
                )

                Clock.schedule_once(
                    lambda dt: self.listen_again(),
                    2
                )

                return

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
            general_app_name = command[5:].strip()
        elif command.startswith("khol "):
            general_app_name = command[5:].strip()
        elif command.startswith("kholo "):
            general_app_name = command[6:].strip()

        if general_app_name:
            blocked = [
                "settings", "wifi", "wi fi", "wi-fi", "bluetooth",
                "display", "battery", "location", "security",
                "mobile network", "mobile data", "phone", "dialer",
                "contacts", "contact", "messages", "message", "sms"
            ]
            if general_app_name not in blocked:
                self.open_installed_app(general_app_name)
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
