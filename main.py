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

    def open_intent(
        self,
        intent
    ):

        def launch():

            try:

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Intent launch error:",
                    e
                )

                self.set_status(
                    "Open nahi ho saka."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # GOOGLE SEARCH
    # ========================================================

    def google_search(
        self,
        query
    ):

        query = query.strip()

        if not query:
            self.set_status(
                "Search query nahi mili."
            )
            return

        self.set_status(
            "Google search kar raha hoon..."
        )

        self.speak(
            "Google par search kar raha hoon."
        )

        uri = Uri.parse(
            "https://www.google.com/search?q=" +
            query.replace(
                " ",
                "+"
            )
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            uri
        )

        self.open_intent(
            intent
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
                "YouTube search query nahi mili."
            )
            return

        self.set_status(
            "YouTube search kar raha hoon..."
        )

        self.speak(
            "YouTube par search kar raha hoon."
        )

        uri = Uri.parse(
            "https://www.youtube.com/results?search_query=" +
            query.replace(
                " ",
                "+"
            )
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            uri
        )

        self.open_intent(
            intent
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
                "Music search query nahi mili."
            )
            return

        self.set_status(
            "Music search kar raha hoon..."
        )

        self.speak(
            "Music search kar raha hoon."
        )

        uri = Uri.parse(
            "https://www.youtube.com/results?search_query=" +
            (
                query +
                " music"
            ).replace(
                " ",
                "+"
            )
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            uri
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

        def launch():

            try:

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                intent = (
                    package_manager
                    .getLaunchIntentForPackage(
                        "com.whatsapp"
                    )
                )

                if intent is None:

                    intent = (
                        package_manager
                        .getLaunchIntentForPackage(
                            "com.whatsapp.w4b"
                        )
                    )

                if intent is None:

                    raise Exception(
                        "WhatsApp not found"
                    )

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
                    "WhatsApp nahi mila."
                )

                self.speak(
                    "WhatsApp nahi mila."
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

        def launch():

            try:

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                calculator_packages = [
                    "com.google.android.calculator",
                    "com.android.calculator2",
                    "com.miui.calculator"
                ]

                for package_name in calculator_packages:

                    try:

                        intent = (
                            package_manager
                            .getLaunchIntentForPackage(
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

                    except Exception:
                        pass

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    "android.intent.category.APP_CALCULATOR"
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Calculator error:",
                    e
                )

                self.set_status(
                    "Calculator nahi mila."
                )

                self.speak(
                    "Calculator nahi mila."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # TIME
    # ========================================================

    def tell_time(self):

        from datetime import datetime

        now = datetime.now()

        current_time = now.strftime(
            "%I:%M %p"
        )

        self.set_status(
            "Time: " +
            current_time
        )

        self.speak(
            "Abhi time hai " +
            current_time
        )

    # ========================================================
    # DATE
    # ========================================================

    def tell_date(self):

        from datetime import datetime

        now = datetime.now()

        current_date = now.strftime(
            "%d %B %Y"
        )

        self.set_status(
            "Date: " +
            current_date
        )

        self.speak(
            "Aaj ki date hai " +
            current_date
        )

    # ========================================================
    # NORMALIZE APP NAME
    # ========================================================

    def normalize_app_name(
        self,
        name
    ):

        name = name.lower().strip()

        replacements = {
            "instagram": "instagram",
            "insta": "instagram",
            "youtube": "youtube",
            "you tube": "youtube",
            "whatsapp": "whatsapp",
            "what's app": "whatsapp",
            "facebook": "facebook",
            "chrome": "chrome",
            "google chrome": "chrome",
            "calculator": "calculator",
            "calc": "calculator",
            "settings": "settings",
            "setting": "settings",
            "camera": "camera",
            "gallery": "gallery",
            "photos": "photos",
            "google photos": "photos",
            "contacts": "contacts",
            "contact": "contacts",
            "messages": "messages",
            "message": "messages",
            "sms": "messages"
        }

        return replacements.get(
            name,
            name
        )

    # ========================================================
    # OPEN INSTALLED APP
    # ========================================================

    def open_installed_app(
        self,
        app_name
    ):

        app_name = self.normalize_app_name(
            app_name
        )

        if not app_name:
            self.set_status(
                "App name nahi mila."
            )
            self.speak(
                "App name nahi mila."
            )
            return

        self.set_status(
            app_name +
            " khol raha hoon..."
        )

        self.speak(
            app_name +
            " khol raha hoon."
        )

        def launch():

            try:

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                main_intent = Intent(
                    Intent.ACTION_MAIN
                )

                main_intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                activities = (
                    package_manager
                    .queryIntentActivities(
                        main_intent,
                        0
                    )
                )

                target_info = None

                app_name_lower = (
                    app_name.lower()
                )

                # Exact match first
                for info in activities:

                    try:

                        label = str(
                            info.loadLabel(
                                package_manager
                            )
                        ).strip()

                        if (
                            label.lower() ==
                            app_name_lower
                        ):
                            target_info = info
                            break

                    except Exception:
                        pass

                # Starts-with match
                if target_info is None:

                    for info in activities:

                        try:

                            label = str(
                                info.loadLabel(
                                    package_manager
                                )
                            ).strip()

                            if label.lower().startswith(
                                app_name_lower
                            ):
                                target_info = info
                                break

                        except Exception:
                            pass

                # Contains match
                if target_info is None:

                    for info in activities:

                        try:

                            label = str(
                                info.loadLabel(
                                    package_manager
                                )
                            ).strip()

                            if app_name_lower in label.lower():
                                target_info = info
                                break

                        except Exception:
                            pass

                if target_info is None:

                    raise Exception(
                        "App not found"
                    )

                package_name = (
                    target_info.activityInfo
                    .packageName
                )

                class_name = (
                    target_info.activityInfo
                    .name
                )

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    Intent.CATEGORY_LAUNCHER
                )

                intent.setClassName(
                    package_name,
                    class_name
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "Open app error:",
                    e
                )

                self.set_status(
                    app_name +
                    " nahi mila."
                )

                self.speak(
                    app_name +
                    " nahi mila."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # PHONE / DIALER
    # ========================================================

    def open_phone(
        self,
        number=None
    ):

        if number:

            number = number.strip()

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

            self.set_status(
                "Dialer khol raha hoon..."
            )

            self.speak(
                "Number dial kar raha hoon."
            )

            uri = Uri.parse(
                "tel:" +
                clean_number
            )

            intent = Intent(
                Intent.ACTION_DIAL,
                uri
            )

            self.open_intent(
                intent
            )

            return

        self.set_status(
            "Phone khol raha hoon..."
        )

        self.speak(
            "Phone khol raha hoon."
        )

        intent = Intent(
            Intent.ACTION_DIAL
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # CONTACTS
    # ========================================================

    def open_contacts(self):

        self.set_status(
            "Contacts khol raha hoon..."
        )

        self.speak(
            "Contacts khol raha hoon."
        )

        def launch():

            try:

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                packages = [
                    "com.google.android.contacts",
                    "com.android.contacts"
                ]

                for package_name in packages:

                    try:

                        intent = (
                            package_manager
                            .getLaunchIntentForPackage(
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

                    except Exception:
                        pass

                intent = Intent(
                    Intent.ACTION_MAIN
                )

                intent.addCategory(
                    "android.intent.category.APP_CONTACTS"
                )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                try:

                    self.activity.startActivity(
                        intent
                    )

                    return

                except Exception:
                    pass

                contacts_uri = Uri.parse(
                    "content://contacts/contacts"
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

            except Exception as e:

                print(
                    "Contacts error:",
                    e
                )

                self.set_status(
                    "Contacts nahi khul saka."
                )

                self.speak(
                    "Contacts nahi khul saka."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # MESSAGES
    # ========================================================

    def open_messages(self):

        self.set_status(
            "Messages khol raha hoon..."
        )

        self.speak(
            "Messages khol raha hoon."
        )

        def launch():

            try:

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                packages = [
                    "com.google.android.apps.messaging",
                    "com.android.mms",
                    "com.android.messaging",
                    "com.google.android.messaging"
                ]

                for package_name in packages:

                    try:

                        intent = (
                            package_manager
                            .getLaunchIntentForPackage(
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

                    except Exception:
                        pass

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

            except Exception as e:

                print(
                    "Messages error:",
                    e
                )

                self.set_status(
                    "Messages nahi mila."
                )

                self.speak(
                    "Messages nahi mila."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # SMS COMPOSE
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

            if char.isdigit() or char == "+":
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

                # Pre-fill message for Android Messages and other SMS apps.
                intent.putExtra(
                    "sms_body",
                    message
                )

                intent.putExtra(
                    Intent.EXTRA_TEXT,
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
    # SETTINGS
    # ========================================================

    def open_settings(self):

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
            "Wi-Fi settings khol raha hoon..."
        )

        self.speak(
            "Wi-Fi settings khol raha hoon."
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
            "Bluetooth settings khol raha hoon..."
        )

        self.speak(
            "Bluetooth settings khol raha hoon."
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
            "Display settings khol raha hoon..."
        )

        self.speak(
            "Display settings khol raha hoon."
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
            "Battery settings khol raha hoon..."
        )

        self.speak(
            "Battery settings khol raha hoon."
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
            "Location settings khol raha hoon..."
        )

        self.speak(
            "Location settings khol raha hoon."
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
            "Security settings khol raha hoon..."
        )

        self.speak(
            "Security settings khol raha hoon."
        )

        intent = Intent(
            Settings.ACTION_SECURITY_SETTINGS
        )

        self.open_intent(
            intent
        )

    # ========================================================
    # MOBILE NETWORK SETTINGS
    # ========================================================

    def open_mobile_network_settings(self):

        self.set_status(
            "Mobile network settings khol raha hoon..."
        )

        self.speak(
            "Mobile network settings khol raha hoon."
        )

        def launch():

            try:

                intents = [
                    Settings.ACTION_NETWORK_OPERATOR_SETTINGS,
                    Settings.ACTION_DATA_ROAMING_SETTINGS,
                    Settings.ACTION_WIRELESS_SETTINGS
                ]

                for action in intents:

                    try:

                        intent = Intent(
                            action
                        )

                        intent.addFlags(
                            Intent.FLAG_ACTIVITY_NEW_TASK
                        )

                        self.activity.startActivity(
                            intent
                        )

                        return

                    except Exception:
                        pass

                raise Exception(
                    "Mobile network settings unavailable"
                )

            except Exception as e:

                print(
                    "Mobile network settings error:",
                    e
                )

                self.set_status(
                    "Mobile network settings nahi khul saka."
                )

                self.speak(
                    "Mobile network settings nahi khul saka."
                )

        self.run_on_android_thread(
            launch
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

        def launch():

            try:

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                intent = (
                    package_manager
                    .getLaunchIntentForPackage(
                        "com.android.chrome"
                    )
                )

                if intent is None:
                    raise Exception(
                        "Chrome not found"
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
                    "Chrome nahi mila."
                )

                self.speak(
                    "Chrome nahi mila."
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

                package_manager = (
                    self.activity
                    .getPackageManager()
                )

                intent = (
                    package_manager
                    .getLaunchIntentForPackage(
                        "com.google.android.youtube"
                    )
                )

                if intent is None:
                    raise Exception(
                        "YouTube not found"
                    )

                intent.addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK
                )

                self.activity.startActivity(
                    intent
                )

            except Exception as e:

                print(
                    "YouTube app error:",
                    e
                )

                self.set_status(
                    "YouTube nahi mila."
                )

                self.speak(
                    "YouTube nahi mila."
                )

        self.run_on_android_thread(
            launch
        )

    # ========================================================
    # COMMAND PROCESSOR
    # ========================================================

    def process_command(self,
        command
    ):

        try:

            command = str(
                command
            ).strip()

            if not command:
                self.listen_again()
                return

            print(
                "Command:",
                command
            )

            lower = command.lower()

            # ------------------------------------------------
            # STOP
            # ------------------------------------------------

            if lower in [
                "stop",
                "stop listening",
                "shut up",
                "quiet"
            ]:

                self.stop_listening()

                self.set_status(
                    "Stopped."
                )

                self.speak(
                    "Okay."
                )

                return

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            if (
                lower == "time"
                or "what time" in lower
                or "current time" in lower
                or "time kya hai" in lower
            ):

                self.tell_time()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    1.5
                )

                return

            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            if (
                lower == "date"
                or "what date" in lower
                or "today's date" in lower
                or "aaj ki date" in lower
                or "date kya hai" in lower
            ):

                self.tell_date()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    1.5
                )

                return

            # ------------------------------------------------
            # WHATSAPP
            # ------------------------------------------------

            if (
                "open whatsapp" in lower
                or "whatsapp kholo" in lower
                or "whatsapp khol" in lower
            ):

                self.open_whatsapp()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # CALCULATOR
            # ------------------------------------------------

            if (
                "open calculator" in lower
                or "calculator kholo" in lower
                or "calculator khol" in lower
                or lower == "calculator"
            ):

                self.open_calculator()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # CAMERA
            # ------------------------------------------------

            if (
                "open camera" in lower
                or "camera kholo" in lower
                or "camera khol" in lower
                or lower == "camera"
            ):

                self.open_camera()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # CHROME
            # ------------------------------------------------

            if (
                "open chrome" in lower
                or "chrome kholo" in lower
                or "chrome khol" in lower
                or lower == "chrome"
            ):

                self.open_chrome()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # YOUTUBE APP
            # ------------------------------------------------

            if (
                lower == "youtube"
                or "open youtube" in lower
                or "youtube kholo" in lower
                or "youtube khol" in lower
            ):

                self.open_youtube()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # OPEN MESSAGES
            # ------------------------------------------------

            if (
                lower == "messages"
                or lower == "message"
                or lower == "sms"
                or "open messages" in lower
                or "messages kholo" in lower
                or "messages khol" in lower
                or "message kholo" in lower
                or "message khol" in lower
                or "open sms" in lower
                or "sms kholo" in lower
                or "sms khol" in lower
            ):

                self.open_messages()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # SMS COMPOSE
            # ------------------------------------------------

            sms_prefixes = [
                "send sms to ",
                "send message to ",
                "sms to ",
                "message to ",
                "text to "
            ]

            matched_sms_prefix = None

            for prefix in sms_prefixes:

                if lower.startswith(prefix):

                    matched_sms_prefix = prefix
                    break

            if matched_sms_prefix is not None:

                sms_data = command[
                    len(
                        matched_sms_prefix
                    ):
                ].strip()

                number = ""
                message = ""

                markers = [
                    " message ",
                    " sms ",
                    " saying ",
                    " bolo "
                ]

                marker_found = False

                for marker in markers:

                    marker_index = (
                        sms_data.lower().find(
                            marker
                        )
                    )

                    if marker_index != -1:

                        number = sms_data[
                            :marker_index
                        ].strip()

                        message = sms_data[
                            marker_index +
                            len(marker):
                        ].strip()

                        marker_found = True
                        break

                if not marker_found:

                    parts = sms_data.split(
                        " ",
                        1
                    )

                    if len(parts) == 2:

                        number = parts[0].strip()
                        message = parts[1].strip()

                self.send_sms(
                    number,
                    message
                )

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # PHONE
            # ------------------------------------------------

            if (
                lower == "phone"
                or lower == "open phone"
                or lower == "phone kholo"
                or lower == "phone khol"
            ):

                self.open_phone()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # DIAL NUMBER
            # ------------------------------------------------

            if (
                lower.startswith(
                    "call "
                )
                or lower.startswith(
                    "dial "
                )
                or lower.startswith(
                    "number "
                )
            ):

                if lower.startswith("call "):
                    number = command[5:].strip()

                elif lower.startswith("dial "):
                    number = command[5:].strip()

                else:
                    number = command[7:].strip()

                self.open_phone(
                    number
                )

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # CONTACTS
            # ------------------------------------------------

            if (
                lower == "contacts"
                or lower == "contact"
                or "open contacts" in lower
                or "contacts kholo" in lower
                or "contacts khol" in lower
                or "contact kholo" in lower
                or "contact khol" in lower
            ):

                self.open_contacts()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # SETTINGS
            # ------------------------------------------------

            if (
                lower == "settings"
                or lower == "setting"
                or "open settings" in lower
                or "settings kholo" in lower
                or "settings khol" in lower
                or "setting kholo" in lower
                or "setting khol" in lower
            ):

                self.open_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # WIFI
            # ------------------------------------------------

            if (
                "wifi settings" in lower
                or "wi-fi settings" in lower
                or "wifi kholo" in lower
                or "wifi khol" in lower
                or "wi-fi kholo" in lower
                or "wi-fi khol" in lower
            ):

                self.open_wifi_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # BLUETOOTH
            # ------------------------------------------------

            if (
                "bluetooth settings" in lower
                or "bluetooth kholo" in lower
                or "bluetooth khol" in lower
            ):

                self.open_bluetooth_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            if (
                "display settings" in lower
                or "display kholo" in lower
                or "display khol" in lower
            ):

                self.open_display_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # BATTERY
            # ------------------------------------------------

            if (
                "battery settings" in lower
                or "battery kholo" in lower
                or "battery khol" in lower
            ):

                self.open_battery_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # LOCATION
            # ------------------------------------------------

            if (
                "location settings" in lower
                or "location kholo" in lower
                or "location khol" in lower
            ):

                self.open_location_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # SECURITY
            # ------------------------------------------------

            if (
                "security settings" in lower
                or "security kholo" in lower
                or "security khol" in lower
            ):

                self.open_security_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # MOBILE NETWORK
            # ------------------------------------------------

            if (
                "mobile network" in lower
                or "mobile data" in lower
                or "data settings" in lower
                or "network settings" in lower
            ):

                self.open_mobile_network_settings()

                Clock.schedule_once(
                    lambda dt:
                    self.listen_again(),
                    2
                )

                return

            # ------------------------------------------------
            # GOOGLE SEARCH
            # ------------------------------------------------

            google_prefixes = [
                "google search ",
                "search google ",
                "search for ",
                "search "
            ]

            for prefix in google_prefixes:

                if lower.startswith(prefix):

                    query = command[
                        len(prefix):
                    ].strip()

                    self.google_search(
                        query
                    )

                    Clock.schedule_once(
                        lambda dt:
                        self.listen_again(),
                        2
                    )

                    return

            # ------------------------------------------------
            # YOUTUBE SEARCH
            # ------------------------------------------------

            youtube_prefixes = [
                "youtube search ",
                "search youtube ",
                "search on youtube "
            ]

            for prefix in youtube_prefixes:

                if lower.startswith(prefix):

                    query = command[
                        len(prefix):
                    ].strip()

                    self.youtube_search(
                        query
                    )

                    Clock.schedule_once(
                        lambda dt:
                        self.listen_again(),
                        2
                    )

                    return

            # ------------------------------------------------
            # MUSIC SEARCH
            # ------------------------------------------------

            music_prefixes = [
                "play music ",
                "music search ",
                "search music ",
                "play "
            ]

            for prefix in music_prefixes:

                if lower.startswith(prefix):

                    query = command[
                        len(prefix):
                    ].strip()

                    if query:

                        self.music_search(
                            query
                        )

                        Clock.schedule_once(
                            lambda dt:
                            self.listen_again(),
                            2
                        )

                        return

            # ------------------------------------------------
            # INSTALLED APP
            # ------------------------------------------------

            app_prefixes = [
                "open app ",
                "open application ",
                "launch app ",
                "launch application ",
                "app kholo ",
                "app khol ",
                "application kholo ",
                "application khol "
            ]

            for prefix in app_prefixes:

                if lower.startswith(prefix):

                    app_name = command[
                        len(prefix):
                    ].strip()

                    self.open_installed_app(
                        app_name
                    )

                    Clock.schedule_once(
                        lambda dt:
                        self.listen_again(),
                        2
                    )

                    return

            # ------------------------------------------------
            # FALLBACK
            # ------------------------------------------------

            self.set_status(
                "Command samajh nahi aaya."
            )

            self.speak(
                "Sorry, command samajh nahi aaya."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen_again(),
                2
            )

        except Exception as e:

            print(
                "Command processing error:",
                e
            )

            self.set_status(
                "Command error."
            )

            Clock.schedule_once(
                lambda dt:
                self.listen_again(),
                2
            )

    # ========================================================
    # CLEANUP
    # ========================================================

    def on_stop(self):

        try:

            if self.speech_recognizer is not None:

                def cleanup():

                    try:
                        self.speech_recognizer.destroy()
                    except Exception:
                        pass

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
    
        
