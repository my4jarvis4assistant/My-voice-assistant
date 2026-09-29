# ============================================================
# MY VOICE ASSISTANT
# VERSION 0.21.2
# BASE: v0.20
# NEW: PHONE / CONTACTS ACTIONS
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
Settings = autoclass("android.provider.Settings")
Uri = autoclass("android.net.Uri")

SpeechRecognizer = autoclass(
    "android.speech.SpeechRecognizer"
)

RecognitionListener = autoclass(
    "android.speech.RecognitionListener"
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
# GLOBAL VARIABLES
# ============================================================

speech_recognizer = None
tts = None
assistant_app = None

is_listening = False
is_destroyed = False


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
            print("Main thread error:", e)


def run_on_android_thread(callback):
    try:
        activity = PythonActivity.mActivity

        runnable = MainThreadRunnable(callback)

        activity.runOnUiThread(runnable)

    except Exception as e:
        print("run_on_android_thread error:", e)


# ============================================================
# SPEECH RECOGNITION LISTENER
# ============================================================

class VoiceRecognitionListener(
    PythonJavaClass
):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    @java_method("()V")
    def onReadyForSpeech(self, params):
        print("Ready for speech")

    @java_method("()V")
    def onBeginningOfSpeech(self):
        print("Listening...")

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("(F)V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("()V")
    def onEndOfSpeech(self):
        print("End of speech")

    @java_method("(Landroid/os/Bundle;)V")
    def onResults(self, results):

        global is_listening

        is_listening = False

        try:

            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )

            if matches is not None and matches.size() > 0:

                text = str(matches.get(0))

                print("Heard:", text)

                if assistant_app:
                    assistant_app.handle_command(text)

            else:
                restart_listening()

        except Exception as e:

            print("Results error:", e)

            restart_listening()


    @java_method("(Landroid/os/Bundle;)V")
    def onPartialResults(self, partialResults):
        pass


    @java_method("(ILandroid/os/Bundle;)V")
    def onError(self, error):

        global is_listening

        is_listening = False

        print("Speech error:", error)

        # Error 5 = client side error.
        # Do not speak/display an error.
        if error == 5:
            restart_listening()
            return

        # Common temporary errors
        if error in [6, 7, 8, 9, 10, 11, 12, 13]:

            restart_listening()

            return

        restart_listening()


# ============================================================
# LISTENER OBJECT
# ============================================================

voice_listener = VoiceRecognitionListener()


# ============================================================
# TTS INITIALIZATION
# ============================================================

class TTSInitListener(
    PythonJavaClass
):

    __javainterfaces__ = [
        "android/speech/tts/UtteranceProgressListener"
    ]


def initialize_tts():

    global tts

    try:

        activity = PythonActivity.mActivity

        tts = TextToSpeech(
            activity,
            None
        )

        tts.setLanguage(
            Locale.US
        )

        print("TTS initialized")

    except Exception as e:

        print("TTS initialization error:", e)

        tts = None


# ============================================================
# SPEAK
# ============================================================

def speak(text):

    global tts

    print("Assistant:", text)

    try:

        if assistant_app:
            assistant_app.set_status(text)

        def speak_on_main():

            global tts

            try:

                if tts is None:
                    initialize_tts()

                if tts is not None:

                    tts.setLanguage(
                        Locale.US
                    )

                    tts.speak(
                        str(text),
                        TextToSpeech.QUEUE_FLUSH,
                        None,
                        "assistant"
                    )

            except Exception as e:

                print("Speak error:", e)

        run_on_android_thread(
            speak_on_main
        )

    except Exception as e:

        print("speak wrapper error:", e)


# ============================================================
# START LISTENING
# ============================================================

def start_listening():

    global speech_recognizer
    global is_listening
    global is_destroyed

    if is_destroyed:
        return

    def start_on_main():

        global speech_recognizer
        global is_listening

        try:

            activity = PythonActivity.mActivity

            # Create recognizer ONLY on Android main thread
            if speech_recognizer is None:

                speech_recognizer = (
                    SpeechRecognizer.createSpeechRecognizer(
                        activity
                    )
                )

                speech_recognizer.setRecognitionListener(
                    voice_listener
                )

                print("SpeechRecognizer created")

            intent = RecognizerIntent()

            intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
            )

            intent.putExtra(
                RecognizerIntent.EXTRA_LANGUAGE,
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

            is_listening = True

            speech_recognizer.startListening(
                intent
            )

            if assistant_app:
                assistant_app.set_status(
                    "Listening..."
                )

            print("Started listening")

        except Exception as e:

            is_listening = False

            print(
                "Start listening error:",
                e
            )

            restart_listening()


    run_on_android_thread(
        start_on_main
    )


# ============================================================
# RESTART LISTENING
# ============================================================

def restart_listening():

    global is_listening

    is_listening = False

    def restart():

        try:

            if assistant_app:
                assistant_app.set_status(
                    "Listening..."
                )

            start_listening()

        except Exception as e:

            print(
                "Restart listening error:",
                e
            )

    Clock.schedule_once(
        lambda dt: restart(),
        1.0
    )


# ============================================================
# STOP LISTENING
# ============================================================

def stop_listening():

    global is_listening

    is_listening = False

    def stop_on_main():

        global speech_recognizer

        try:

            if speech_recognizer is not None:

                speech_recognizer.stopListening()

                print("Stopped listening")

        except Exception as e:

            print(
                "Stop listening error:",
                e
            )

    run_on_android_thread(
        stop_on_main
    )


# ============================================================
# OPEN INTENT
# ============================================================

def open_intent(intent):

    def open_on_main():

        try:

            activity = PythonActivity.mActivity

            activity.startActivity(intent)

            print("Intent opened")

        except Exception as e:

            print(
                "Open intent error:",
                e
            )

    run_on_android_thread(
        open_on_main
    )


# ============================================================
# OPEN SETTINGS
# ============================================================

def open_settings(action):

    try:

        intent = Intent(action)

        open_intent(intent)

    except Exception as e:

        print(
            "Settings error:",
            e
        )


# ============================================================
# GOOGLE SEARCH
# ============================================================

def google_search(query):

    try:

        encoded = Uri.encode(
            str(query)
        )

        url = (
            "https://www.google.com/search?q="
            + encoded
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(url)
        )

        open_intent(intent)

    except Exception as e:

        print(
            "Google search error:",
            e
        )


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def youtube_search(query):

    try:

        encoded = Uri.encode(
            str(query)
        )

        url = (
            "https://www.youtube.com/results?search_query="
            + encoded
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(url)
        )

        open_intent(intent)

    except Exception as e:

        print(
            "YouTube search error:",
            e
        )


# ============================================================
# MUSIC SEARCH
# ============================================================

def music_search(query):

    try:

        encoded = Uri.encode(
            str(query)
        )

        url = (
            "https://music.youtube.com/search?q="
            + encoded
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(url)
        )

        open_intent(intent)

    except Exception as e:

        print(
            "Music search error:",
            e
)

# ============================================================
# PHONE / DIALER
# ============================================================

def open_phone():

    try:

        intent = Intent(
            Intent.ACTION_DIAL
        )

        open_intent(intent)

    except Exception as e:

        print(
            "Phone error:",
            e
        )


# ============================================================
# DIAL NUMBER
# ============================================================

def dial_number(number):

    try:

        number = str(number).strip()

        if not number:
            speak("Number nahi mila.")
            return

        # Remove spaces and common symbols
        number = number.replace(
            " ",
            ""
        )

        number = number.replace(
            "-",
            ""
        )

        uri = Uri.parse(
            "tel:" + number
        )

        intent = Intent(
            Intent.ACTION_DIAL,
            uri
        )

        open_intent(intent)

        speak(
            "Dialer khol raha hoon."
        )

    except Exception as e:

        print(
            "Dial number error:",
            e
        )

        speak(
            "Number dial nahi ho saka."
        )


# ============================================================
# CONTACTS
# ============================================================

def open_contacts():

    try:

        # IMPORTANT:
        # ContactsContract is loaded only when the
        # Contacts command is actually used.
        ContactsContract = autoclass(
            "android.provider.ContactsContract"
        )

        intent = Intent(
            Intent.ACTION_VIEW
        )

        intent.setData(
            ContactsContract.Contacts.CONTENT_URI
        )

        open_intent(intent)

    except Exception as e:

        print(
            "Contacts error:",
            e
        )

        # Fallback to generic contacts app
        try:

            intent = Intent(
                Intent.ACTION_VIEW
            )

            intent.setType(
                "vnd.android.cursor.dir/contact"
            )

            open_intent(intent)

        except Exception as e2:

            print(
                "Contacts fallback error:",
                e2
            )


# ============================================================
# INSTALLED APP OPEN
# ============================================================

def open_installed_app(app_name):

    try:

        PackageManager = autoclass(
            "android.content.pm.PackageManager"
        )

        activity = PythonActivity.mActivity

        pm = activity.getPackageManager()

        packages = pm.getInstalledApplications(
            PackageManager.GET_META_DATA
        )

        target = str(
            app_name
        ).strip().lower()

        found_package = None

        for i in range(packages.size()):

            info = packages.get(i)

            try:

                label = str(
                    pm.getApplicationLabel(
                        info
                    )
                )

                package_name = str(
                    info.packageName
                )

                if target in label.lower():

                    found_package = package_name

                    break

                if target in package_name.lower():

                    found_package = package_name

                    break

            except Exception:
                continue

        if found_package:

            launch_intent = (
                pm.getLaunchIntentForPackage(
                    found_package
                )
            )

            if launch_intent is not None:

                open_intent(
                    launch_intent
                )

                speak(
                    str(app_name)
                    + " khol raha hoon."
                )

                return True

        speak(
            str(app_name)
            + " installed nahi mila."
        )

        return False

    except Exception as e:

        print(
            "Installed app error:",
            e
        )

        speak(
            "App open nahi ho saka."
        )

        return False


# ============================================================
# WHATSAPP
# ============================================================

def open_whatsapp():

    try:

        PackageManager = autoclass(
            "android.content.pm.PackageManager"
        )

        activity = PythonActivity.mActivity

        pm = activity.getPackageManager()

        packages = [
            "com.whatsapp",
            "com.whatsapp.w4b"
        ]

        for package_name in packages:

            try:

                intent = (
                    pm.getLaunchIntentForPackage(
                        package_name
                    )
                )

                if intent is not None:

                    open_intent(intent)

                    speak(
                        "WhatsApp khol raha hoon."
                    )

                    return

            except Exception:
                continue

        speak(
            "WhatsApp installed nahi mila."
        )

    except Exception as e:

        print(
            "WhatsApp error:",
            e
        )


# ============================================================
# CALCULATOR
# ============================================================

def open_calculator():

    try:

        PackageManager = autoclass(
            "android.content.pm.PackageManager"
        )

        activity = PythonActivity.mActivity

        pm = activity.getPackageManager()

        calculator_packages = [
            "com.miui.calculator",
            "com.google.android.calculator",
            "com.android.calculator2"
        ]

        for package_name in calculator_packages:

            try:

                intent = (
                    pm.getLaunchIntentForPackage(
                        package_name
                    )
                )

                if intent is not None:

                    open_intent(intent)

                    speak(
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

            open_intent(intent)

            speak(
                "Calculator khol raha hoon."
            )

        except Exception:

            speak(
                "Calculator nahi mila."
            )

    except Exception as e:

        print(
            "Calculator error:",
            e
        )


# ============================================================
# CAMERA
# ============================================================

def open_camera():

    try:

        intent = Intent(
            "android.media.action.IMAGE_CAPTURE"
        )

        open_intent(intent)

        speak(
            "Camera khol raha hoon."
        )

    except Exception as e:

        print(
            "Camera error:",
            e
        )


# ============================================================
# CHROME
# ============================================================

def open_chrome():

    try:

        PackageManager = autoclass(
            "android.content.pm.PackageManager"
        )

        activity = PythonActivity.mActivity

        pm = activity.getPackageManager()

        intent = (
            pm.getLaunchIntentForPackage(
                "com.android.chrome"
            )
        )

        if intent is not None:

            open_intent(intent)

            speak(
                "Chrome khol raha hoon."
            )

            return

        intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(
                "https://www.google.com"
            )
        )

        open_intent(intent)

        speak(
            "Browser khol raha hoon."
        )

    except Exception as e:

        print(
            "Chrome error:",
            e
        )


# ============================================================
# YOUTUBE APP
# ============================================================

def open_youtube():

    try:

        PackageManager = autoclass(
            "android.content.pm.PackageManager"
        )

        activity = PythonActivity.mActivity

        pm = activity.getPackageManager()

        intent = (
            pm.getLaunchIntentForPackage(
                "com.google.android.youtube"
            )
        )

        if intent is not None:

            open_intent(intent)

            speak(
                "YouTube khol raha hoon."
            )

            return

        intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse(
                "https://www.youtube.com"
            )
        )

        open_intent(intent)

        speak(
            "YouTube khol raha hoon."
        )

    except Exception as e:

        print(
            "YouTube error:",
            e
        )


# ============================================================
# TIME
# ============================================================

def tell_time():

    from datetime import datetime

    current_time = datetime.now().strftime(
        "%I:%M %p"
    )

    speak(
        "Abhi time hai "
        + current_time
    )


# ============================================================
# DATE
# ============================================================

def tell_date():

    from datetime import datetime

    current_date = datetime.now().strftime(
        "%d %B %Y"
    )

    speak(
        "Aaj ki date hai "
        + current_date
    )


# ============================================================
# COMMON SETTINGS
# ============================================================

def wifi_settings():

    try:

        open_settings(
            Settings.ACTION_WIFI_SETTINGS
        )

        speak(
            "Wi-Fi settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Wi-Fi error:",
            e
        )


def bluetooth_settings():

    try:

        open_settings(
            Settings.ACTION_BLUETOOTH_SETTINGS
        )

        speak(
            "Bluetooth settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Bluetooth error:",
            e
        )


def display_settings():

    try:

        open_settings(
            Settings.ACTION_DISPLAY_SETTINGS
        )

        speak(
            "Display settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Display settings error:",
            e
        )


def battery_settings():

    try:

        open_settings(
            Settings.ACTION_BATTERY_SAVER_SETTINGS
        )

        speak(
            "Battery settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Battery settings error:",
            e
        )


def location_settings():

    try:

        open_settings(
            Settings.ACTION_LOCATION_SOURCE_SETTINGS
        )

        speak(
            "Location settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Location settings error:",
            e
        )


def security_settings():

    try:

        open_settings(
            Settings.ACTION_SECURITY_SETTINGS
        )

        speak(
            "Security settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Security settings error:",
            e
        )


def mobile_network_settings():

    try:

        open_settings(
            Settings.ACTION_NETWORK_OPERATOR_SETTINGS
        )

        speak(
            "Mobile network settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Mobile network error:",
            e
        )


# ============================================================
# MAIN APP CLASS
# ============================================================

class MyVoiceAssistant(App):

    def build(self):

        global assistant_app

        assistant_app = self

        self.label = Label(
            text=(
                "My Voice Assistant\n\n"
                "Starting..."
            ),
            halign="center",
            valign="middle"
        )

        self.label.bind(
            size=self.label.setter(
                "text_size"
            )
        )

        return self.label


    def set_status(self, text):

        try:

            self.label.text = (
                "My Voice Assistant\n\n"
                + str(text)
            )

        except Exception as e:

            print(
                "Status error:",
                e
            )


    def on_start(self):

        print(
            "Application started"
        )

        # TTS and SpeechRecognizer setup
        # happen after Kivy/Android activity is ready.
        Clock.schedule_once(
            self.initialize_android,
            1.0
        )


    def initialize_android(self, dt):

        global is_destroyed

        is_destroyed = False

        self.set_status(
            "Starting..."
        )

        def setup():

            try:

                initialize_tts()

                print(
                    "Android voice system ready"
                )

            except Exception as e:

                print(
                    "Android setup error:",
                    e
                )

            Clock.schedule_once(
                lambda x: start_listening(),
                1.5
            )

        run_on_android_thread(
            setup
            )

# ============================================================
# COMMAND PROCESSOR
# ============================================================

    def handle_command(self, command):

        command = str(
            command
        ).strip()

        if not command:
            restart_listening()
            return

        print(
            "COMMAND:",
            command
        )

        text = command.lower().strip()


        # ====================================================
        # GREETINGS
        # ====================================================

        if (
            text in ["hello", "hi", "hey"]
            or "hello jarvis" in text
            or "hi jarvis" in text
            or "hello assistant" in text
        ):

            speak(
                "Hello! Main aapka voice assistant hoon."
            )

            return


        # ====================================================
        # NAME
        # ====================================================

        if (
            "tumhara naam" in text
            or "your name" in text
            or "what is your name" in text
            or "who are you" in text
            or "tum kaun ho" in text
        ):

            speak(
                "Main My Voice Assistant hoon."
            )

            return


        # ====================================================
        # TIME
        # ====================================================

        if (
            "time batao" in text
            or "time kya hai" in text
            or "what time" in text
            or text == "time"
        ):

            tell_time()

            return


        # ====================================================
        # DATE
        # ====================================================

        if (
            "date batao" in text
            or "aaj ki date" in text
            or "today date" in text
            or "what is the date" in text
        ):

            tell_date()

            return


        # ====================================================
        # PHONE APP
        # ====================================================

        if (
            text == "phone"
            or "phone kholo" in text
            or "phone open karo" in text
            or "dialer kholo" in text
            or "dialer open karo" in text
            or "calling app kholo" in text
            or "call app kholo" in text
        ):

            speak(
                "Phone khol raha hoon."
            )

            open_phone()

            return


        # ====================================================
        # CONTACTS
        # ====================================================

        if (
            "contacts kholo" in text
            or "contacts open karo" in text
            or "contact kholo" in text
            or "contact open karo" in text
            or "contacts app kholo" in text
            or "contact app kholo" in text
        ):

            speak(
                "Contacts khol raha hoon."
            )

            open_contacts()

            return


        # ====================================================
        # NUMBER DIAL
        # ====================================================

        if (
            text.startswith("call ")
            or text.startswith("dial ")
            or text.startswith("number ")
        ):

            words = text.split()

            number_parts = []

            for word in words[1:]:

                clean = (
                    word.replace(
                        "-",
                        ""
                    )
                    .replace(
                        " ",
                        ""
                    )
                )

                if (
                    clean.isdigit()
                    or clean.startswith("+")
                ):

                    number_parts.append(
                        clean
                    )

            if number_parts:

                number = "".join(
                    number_parts
                )

                dial_number(
                    number
                )

                return


        # ====================================================
        # WIFI
        # ====================================================

        if (
            "wifi" in text
            or "wi fi" in text
            or "wi-fi" in text
        ):

            wifi_settings()

            return


        # ====================================================
        # BLUETOOTH
        # ====================================================

        if (
            "bluetooth" in text
            or "blue tooth" in text
        ):

            bluetooth_settings()

            return


        # ====================================================
        # DISPLAY
        # ====================================================

        if (
            "display settings" in text
            or "screen settings" in text
            or "display kholo" in text
            or "screen kholo" in text
        ):

            display_settings()

            return


        # ====================================================
        # BATTERY
        # ====================================================

        if (
            "battery settings" in text
            or "battery kholo" in text
            or "battery setting kholo" in text
        ):

            battery_settings()

            return


        # ====================================================
        # LOCATION
        # ====================================================

        if (
            "location settings" in text
            or "location kholo" in text
            or "gps settings" in text
        ):

            location_settings()

            return


        # ====================================================
        # SECURITY
        # ====================================================

        if (
            "security settings" in text
            or "security kholo" in text
            or "security setting kholo" in text
        ):

            security_settings()

            return


        # ====================================================
        # MOBILE NETWORK
        # ====================================================

        if (
            "mobile network" in text
            or "mobile data settings" in text
            or "data settings" in text
            or "network settings" in text
            or "sim settings" in text
        ):

            mobile_network_settings()

            return


        # ====================================================
        # GOOGLE SEARCH
        # ====================================================

        if (
            "google search" in text
            or "google par search" in text
            or "google pe search" in text
            or "web search" in text
        ):

            query = text

            prefixes = [
                "google search",
                "google par search",
                "google pe search",
                "web search"
            ]

            for prefix in prefixes:

                query = query.replace(
                    prefix,
                    "",
                    1
                )

            query = query.strip()

            if query:

                speak(
                    "Google par search kar raha hoon."
                )

                google_search(
                    query
                )

            else:

                speak(
                    "Kya search karna hai?"
                )

            return


        # ====================================================
        # YOUTUBE SEARCH
        # ====================================================

        if (
            "youtube pe" in text
            and "search" in text
        ) or (
            "youtube par" in text
            and "search" in text
        ):

            query = text

            query = query.replace(
                "youtube pe",
                "",
                1
            )

            query = query.replace(
                "youtube par",
                "",
                1
            )

            query = query.replace(
                "search karo",
                "",
                1
            )

            query = query.replace(
                "search",
                "",
                1
            )

            query = query.strip()

            if query:

                speak(
                    "YouTube par search kar raha hoon."
                )

                youtube_search(
                    query
                )

            else:

                speak(
                    "YouTube par kya search karna hai?"
                )

            return


        # ====================================================
        # MUSIC SEARCH
        # ====================================================

        if (
            "music search" in text
            or "music search karo" in text
            or "song search" in text
            or "gaana search" in text
        ):

            query = text

            prefixes = [
                "music search karo",
                "music search",
                "song search",
                "gaana search"
            ]

            for prefix in prefixes:

                query = query.replace(
                    prefix,
                    "",
                    1
                )

            query = query.strip()

            if query:

                speak(
                    "Music search kar raha hoon."
                )

                music_search(
                    query
                )

            else:

                speak(
                    "Kaunsa music search karna hai?"
                )

            return


        # ====================================================
        # WHATSAPP
        # ====================================================

        if (
            "whatsapp kholo" in text
            or "whatsapp open karo" in text
            or "whatsapp open" in text
            or text == "whatsapp"
        ):

            open_whatsapp()

            return


        # ====================================================
        # CALCULATOR
        # ====================================================

        if (
            "calculator kholo" in text
            or "calculator open karo" in text
            or "calculator open" in text
            or text == "calculator"
        ):

            open_calculator()

            return


        # ====================================================
        # CAMERA
        # ====================================================

        if (
            "camera kholo" in text
            or "camera open karo" in text
            or "camera open" in text
            or text == "camera"
        ):

            open_camera()

            return


        # ====================================================
        # CHROME
        # ====================================================

        if (
            "chrome kholo" in text
            or "chrome open karo" in text
            or "chrome open" in text
            or text == "chrome"
        ):

            open_chrome()

            return


        # ====================================================
        # YOUTUBE APP
        # ====================================================

        if (
            text == "youtube"
            or "youtube kholo" in text
            or "youtube open karo" in text
            or "youtube open" in text
        ):

            open_youtube()

            return


        # ====================================================
        # INSTALLED APPS
        # ====================================================

        known_apps = {

            "instagram": [
                "instagram",
                "instagram kholo",
                "instagram open karo"
            ],

            "facebook": [
                "facebook",
                "facebook kholo",
                "facebook open karo"
            ],

            "settings": [
                "settings",
                "settings kholo",
                "settings open karo"
            ],

            "gallery": [
                "gallery",
                "gallery kholo",
                "gallery open karo"
            ],

            "play store": [
                "play store",
                "play store kholo",
                "play store open karo"
            ]
        }


        for app_name, commands in known_apps.items():

            matched = False

            for phrase in commands:

                if text == phrase:

                    matched = True
                    break

                if (
                    phrase + " " in text
                ):

                    matched = True
                    break

            if matched:

                if app_name == "settings":

                    try:

                        open_settings(
                            Settings.ACTION_SETTINGS
                        )

                        speak(
                            "Settings khol raha hoon."
                        )

                    except Exception as e:

                        print(
                            "Settings error:",
                            e
                        )

                else:

                    open_installed_app(
                        app_name
                    )

                return


        # ====================================================
        # GENERIC INSTALLED APP COMMAND
        # ====================================================

        app_prefixes = [
            "open ",
            "open app ",
            "khol ",
            "khol do ",
            "kholna ",
            "app kholo ",
            "app open karo ",
            "app khol do "
        ]

        for prefix in app_prefixes:

            if text.startswith(prefix):

                app_name = text[
                    len(prefix):
                ].strip()

                if app_name:

                    open_installed_app(
                        app_name
                    )

                    return


        # ====================================================
        # UNKNOWN COMMAND
        # ====================================================

        speak(
            "Command samajh nahi aaya."
        )


# ============================================================
# CLEANUP
# ============================================================

    def on_stop(self):

        global speech_recognizer
        global tts
        global is_destroyed
        global is_listening

        is_destroyed = True
        is_listening = False

        def cleanup_on_main():

            global speech_recognizer
            global tts

            try:

                if speech_recognizer is not None:

                    try:
                        speech_recognizer.stopListening()
                    except Exception:
                        pass

                    try:
                        speech_recognizer.cancel()
                    except Exception:
                        pass

                    try:
                        speech_recognizer.destroy()
                    except Exception:
                        pass

                    speech_recognizer = None

                print(
                    "SpeechRecognizer destroyed"
                )

            except Exception as e:

                print(
                    "Speech cleanup error:",
                    e
                )


            try:

                if tts is not None:

                    try:
                        tts.stop()
                    except Exception:
                        pass

                    try:
                        tts.shutdown()
                    except Exception:
                        pass

                    tts = None

                print(
                    "TTS destroyed"
                )

            except Exception as e:

                print(
                    "TTS cleanup error:",
                    e
                )


        run_on_android_thread(
            cleanup_on_main
        )


# ============================================================
# APP START
# ============================================================

if __name__ == "__main__":

    MyVoiceAssistant().run()
