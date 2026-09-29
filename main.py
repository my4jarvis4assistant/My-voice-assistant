# ============================================================
# MY VOICE ASSISTANT
# VERSION: v0.21.3
# BASE: v0.20 SUCCESS
# NEW: PHONE / CONTACTS + MICROPHONE RUNTIME PERMISSION FIX
# ============================================================

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label

from jnius import autoclass, PythonJavaClass, java_method


# ============================================================
# ANDROID CLASSES
# ============================================================

PythonActivity = autoclass("org.kivy.android.PythonActivity")
activity = PythonActivity.mActivity

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

BuildVersion = autoclass(
    "android.os.Build$VERSION"
)

PackageManager = autoclass(
    "android.content.pm.PackageManager"
)


# ============================================================
# RUNTIME MICROPHONE PERMISSION
# ============================================================

try:
    from android.permissions import (
        Permission,
        request_permissions,
        check_permission
    )

    ANDROID_PERMISSION_API = True

except Exception:
    ANDROID_PERMISSION_API = False


# ============================================================
# MAIN THREAD RUNNER
# ============================================================

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
            print("MainThreadRunnable Error:", e)


def run_on_android_thread(function):

    try:
        runnable = MainThreadRunnable(function)
        activity.runOnUiThread(runnable)
        return True

    except Exception as e:
        print("run_on_android_thread Error:", e)
        return False


# ============================================================
# GLOBAL OBJECTS
# ============================================================

tts = None
speech_recognizer = None
recognition_listener = None

assistant_app = None

tts_ready = False
speech_ready = False
permission_requested = False
is_listening = False


# ============================================================
# RECOGNITION LISTENER
# ============================================================

class VoiceRecognitionListener(PythonJavaClass):

    __javainterfaces__ = [
        "android/speech/RecognitionListener"
    ]

    def __init__(self):
        super().__init__()

    @java_method("()V")
    def onReadyForSpeech(self, params):
        global is_listening

        is_listening = True

        if assistant_app:
            assistant_app.set_status("Listening...")

    @java_method("()V")
    def onBeginningOfSpeech(self):
        if assistant_app:
            assistant_app.set_status("Listening...")

    @java_method("()V")
    def onRmsChanged(self, rmsdB):
        pass

    @java_method("([B)V")
    def onBufferReceived(self, buffer):
        pass

    @java_method("()V")
    def onEndOfSpeech(self):
        global is_listening

        is_listening = False

        if assistant_app:
            assistant_app.set_status("Processing...")

    @java_method("(I)V")
    def onError(self, error):
        global is_listening

        is_listening = False

        print("Speech Error:", error)

        # Error 5 = ERROR_CLIENT
        # We silently restart it.

        if error == 5:

            if assistant_app:
                assistant_app.set_status(
                    "Listening..."
                )

            Clock.schedule_once(
                lambda dt: start_listening(),
                0.4
            )

            return

        # Common temporary speech errors

        if error in (6, 7, 8, 9):

            Clock.schedule_once(
                lambda dt: start_listening(),
                0.8
            )

            return

        if assistant_app:
            assistant_app.set_status(
                "Listening..."
            )

        Clock.schedule_once(
            lambda dt: start_listening(),
            1.0
        )

    @java_method("([Ljava/lang/String;)V")
    def onResults(self, results):

        global is_listening

        is_listening = False

        try:

            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )

            if matches is not None and matches.size() > 0:

                command = str(matches.get(0))

                print(
                    "Recognized:",
                    command
                )

                process_command(command)

            else:

                Clock.schedule_once(
                    lambda dt: start_listening(),
                    0.5
                )

        except Exception as e:

            print(
                "onResults Error:",
                e
            )

            Clock.schedule_once(
                lambda dt: start_listening(),
                0.8
            )

    @java_method("([Ljava/lang/String;)V")
    def onPartialResults(self, partial_results):
        pass

    @java_method("(Landroid/os/Bundle;)V")
    def onEvent(self, event_type, params):
        pass


# ============================================================
# TTS INITIALIZATION
# ============================================================

class TTSInitListener(PythonJavaClass):

    __javainterfaces__ = [
        "android/speech/tts/TextToSpeech$OnInitListener"
    ]

    def __init__(self):
        super().__init__()

    @java_method("(I)V")
    def onInit(self, status):

        global tts
        global tts_ready

        try:

            if status == TextToSpeech.SUCCESS:

                language_result = tts.setLanguage(
                    Locale("en", "IN")
                )

                if (
                    language_result
                    != TextToSpeech.LANG_MISSING_DATA
                    and
                    language_result
                    != TextToSpeech.LANG_NOT_SUPPORTED
                ):

                    tts_ready = True

                    print(
                        "TTS initialized"
                    )

                    if assistant_app:
                        assistant_app.set_status(
                            "Ready"
                        )

                else:

                    print(
                        "TTS language unavailable"
                    )

            else:

                print(
                    "TTS initialization failed"
                )

        except Exception as e:

            print(
                "TTS Init Error:",
                e
            )


def initialize_tts():

    global tts

    try:

        listener = TTSInitListener()

        tts = TextToSpeech(
            activity,
            listener
        )

        print(
            "TTS object created"
        )

    except Exception as e:

        print(
            "TTS Create Error:",
            e
        )


# ============================================================
# SPEAK
# ============================================================

def speak(text):

    global tts

    print(
        "Assistant:",
        text
    )

    if assistant_app:
        assistant_app.set_status(
            text
        )

    def speak_on_main():

        try:

            if tts is None:
                return

            if not tts_ready:
                return

            # Android API 21+

            tts.speak(
                str(text),
                TextToSpeech.QUEUE_FLUSH,
                None,
                "assistant_utterance"
            )

        except Exception as e:

            print(
                "Speak Error:",
                e
            )

    run_on_android_thread(
        speak_on_main
    )


# ============================================================
# MICROPHONE PERMISSION
# ============================================================

def has_microphone_permission():

    try:

        if not ANDROID_PERMISSION_API:

            # Fallback for packaged environments
            # where android.permissions isn't available.

            if int(BuildVersion.SDK_INT) < 23:
                return True

            result = activity.checkSelfPermission(
                "android.permission.RECORD_AUDIO"
            )

            return (
                result
                ==
                PackageManager.PERMISSION_GRANTED
            )

        return check_permission(
            Permission.RECORD_AUDIO
        )

    except Exception as e:

        print(
            "Permission Check Error:",
            e
        )

        return False


def request_microphone_permission():

    global permission_requested

    if permission_requested:
        return

    permission_requested = True

    print(
        "Requesting microphone permission..."
    )

    try:

        if ANDROID_PERMISSION_API:

            request_permissions(
                [Permission.RECORD_AUDIO],
                microphone_permission_callback
            )

        else:

            if int(BuildVersion.SDK_INT) >= 23:

                activity.requestPermissions(
                    ["android.permission.RECORD_AUDIO"],
                    1001
                )

                Clock.schedule_once(
                    lambda dt:
                    microphone_permission_callback(
                        ["android.permission.RECORD_AUDIO"],
                        [PackageManager.PERMISSION_GRANTED]
                    ),
                    1.5
                )

            else:

                microphone_permission_callback(
                    [],
                    []
                )

    except Exception as e:

        print(
            "Permission Request Error:",
            e
        )

        Clock.schedule_once(
            lambda dt: start_listening(),
            1.5
        )


def microphone_permission_callback(
    permissions,
    grants
):

    global permission_requested

    permission_requested = False

    try:

        if has_microphone_permission():

            print(
                "Microphone permission: GRANTED"
            )

            if assistant_app:
                assistant_app.set_status(
                    "Microphone Ready"
                )

            Clock.schedule_once(
                lambda dt:
                setup_speech_recognizer(),
                0.2
            )

        else:

            print(
                "Microphone permission: DENIED"
            )

            if assistant_app:
                assistant_app.set_status(
                    "Microphone Permission Required"
                )

            speak(
                "Microphone permission chahiye."
            )

    except Exception as e:

        print(
            "Permission Callback Error:",
            e
        )


# ============================================================
# SPEECH RECOGNIZER SETUP
# ============================================================

def setup_speech_recognizer():

    global speech_recognizer
    global recognition_listener
    global speech_ready

    def create_recognizer():

        global speech_recognizer
        global recognition_listener
        global speech_ready

        try:

            if not has_microphone_permission():

                request_microphone_permission()
                return

            available = (
                SpeechRecognizer
                .isRecognitionAvailable(activity)
            )

            if not available:

                print(
                    "Speech recognition unavailable"
                )

                if assistant_app:
                    assistant_app.set_status(
                        "Speech Recognition Unavailable"
                    )

                return

            recognition_listener = (
                VoiceRecognitionListener()
            )

            speech_recognizer = (
                SpeechRecognizer
                .createSpeechRecognizer(activity)
            )

            speech_recognizer.setRecognitionListener(
                recognition_listener
            )

            speech_ready = True

            print(
                "SpeechRecognizer created on main thread"
            )

            if assistant_app:
                assistant_app.set_status(
                    "Ready"
                )

            Clock.schedule_once(
                lambda dt:
                start_listening(),
                0.5
            )

        except Exception as e:

            print(
                "SpeechRecognizer Setup Error:",
                e
            )

            speech_ready = False

            if assistant_app:
                assistant_app.set_status(
                    "Speech Setup Error"
                )

    run_on_android_thread(
        create_recognizer
    )


# ============================================================
# RECOGNIZER INTENT
# ============================================================

def create_recognizer_intent():

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

    return intent


# ============================================================
# START LISTENING
# ============================================================

def start_listening():

    global speech_recognizer
    global speech_ready
    global is_listening

    def listen_on_main():

        global is_listening

        try:

            if not has_microphone_permission():

                request_microphone_permission()
                return

            if (
                speech_recognizer is None
                or
                not speech_ready
            ):

                setup_speech_recognizer()
                return

            if is_listening:
                return

            intent = (
                create_recognizer_intent()
            )

            speech_recognizer.startListening(
                intent
            )

            is_listening = True

            print(
                "startListening() called"
            )

            if assistant_app:
                assistant_app.set_status(
                    "Listening..."
                )

        except Exception as e:

            print(
                "Start Listening Error:",
                e
            )

            is_listening = False

            Clock.schedule_once(
                lambda dt:
                setup_speech_recognizer(),
                1.0
            )

    run_on_android_thread(
        listen_on_main
    )


# ============================================================
# RESTART LISTENING
# ============================================================

def restart_listening(delay=0.7):

    Clock.schedule_once(
        lambda dt:
        start_listening(),
        delay
    )


# ============================================================
# STOP LISTENING
# ============================================================

def stop_listening():

    global is_listening

    def stop_on_main():

        global is_listening

        try:

            if speech_recognizer is not None:

                speech_recognizer.stopListening()

            is_listening = False

        except Exception as e:

            print(
                "Stop Listening Error:",
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

            intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
            )

            activity.startActivity(
                intent
            )

        except Exception as e:

            print(
                "Intent Error:",
                e
            )

            if assistant_app:
                assistant_app.set_status(
                    "Open failed"
                )

    run_on_android_thread(
        open_on_main
    )


# ============================================================
# OPEN URL
# ============================================================

def open_url(url):

    intent = Intent(
        Intent.ACTION_VIEW
    )

    intent.setData(
        Uri.parse(url)
    )

    open_intent(intent)


# ============================================================
# PART 1 END
# ============================================================

# ============================================================
# PHONE / CONTACTS ACTIONS
# ============================================================

def open_phone():

    try:

        intent = Intent(
            Intent.ACTION_DIAL
        )

        open_intent(intent)

        speak(
            "Phone dialer khol raha hoon."
        )

    except Exception as e:

        print(
            "Phone Error:",
            e
        )


def dial_number(number):

    try:

        cleaned = ""

        for char in str(number):

            if char.isdigit() or char == "+":

                cleaned += char

        if not cleaned:

            speak(
                "Number samajh nahi aaya."
            )

            restart_listening()
            return

        uri = Uri.parse(
            "tel:" + cleaned
        )

        intent = Intent(
            Intent.ACTION_DIAL
        )

        intent.setData(
            uri
        )

        open_intent(intent)

        speak(
            "Dialer khol raha hoon."
        )

    except Exception as e:

        print(
            "Dial Number Error:",
            e
        )

        speak(
            "Number open nahi ho paya."
        )


def open_contacts():

    try:

        ContactsContract = autoclass(
            "android.provider.ContactsContract"
        )

        intent = Intent(
            Intent.ACTION_VIEW,
            ContactsContract.Contacts.CONTENT_URI
        )

        open_intent(intent)

        speak(
            "Contacts khol raha hoon."
        )

    except Exception as e:

        print(
            "Contacts Error:",
            e
        )

        speak(
            "Contacts open nahi ho paye."
        )


# ============================================================
# INSTALLED APP LAUNCHER
# ============================================================

def open_installed_app(app_name):

    try:

        PackageManagerClass = autoclass(
            "android.content.pm.PackageManager"
        )

        pm = activity.getPackageManager()

        packages = pm.getInstalledApplications(
            PackageManagerClass.GET_META_DATA
        )

        target = str(
            app_name
        ).lower().strip()

        for i in range(packages.size()):

            app_info = packages.get(i)

            try:

                label = str(
                    pm.getApplicationLabel(
                        app_info
                    )
                ).lower()

                package_name = str(
                    app_info.packageName
                )

                if target in label:

                    launch_intent = (
                        pm.getLaunchIntentForPackage(
                            package_name
                        )
                    )

                    if launch_intent is not None:

                        open_intent(
                            launch_intent
                        )

                        speak(
                            str(
                                pm.getApplicationLabel(
                                    app_info
                                )
                            )
                            + " khol raha hoon."
                        )

                        return

            except Exception:
                continue

        speak(
            "Ye app nahi mili."
        )

    except Exception as e:

        print(
            "Installed App Error:",
            e
        )

        speak(
            "App open nahi ho payi."
        )


# ============================================================
# WHATSAPP
# ============================================================

def open_whatsapp():

    try:

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

                    open_intent(
                        intent
                    )

                    speak(
                        "WhatsApp khol raha hoon."
                    )

                    return

            except Exception:
                continue

        speak(
            "WhatsApp installed nahi hai."
        )

    except Exception as e:

        print(
            "WhatsApp Error:",
            e
        )

        speak(
            "WhatsApp open nahi ho paya."
        )


# ============================================================
# CALCULATOR
# ============================================================

def open_calculator():

    try:

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

                    open_intent(
                        intent
                    )

                    speak(
                        "Calculator khol raha hoon."
                    )

                    return

            except Exception:
                continue

        try:

            intent = Intent(
                Intent.ACTION_MAIN
            )

            intent.addCategory(
                Intent.CATEGORY_APP_CALCULATOR
            )

            open_intent(
                intent
            )

            speak(
                "Calculator khol raha hoon."
            )

            return

        except Exception:
            pass

        speak(
            "Calculator nahi mila."
        )

    except Exception as e:

        print(
            "Calculator Error:",
            e
        )

        speak(
            "Calculator open nahi ho paya."
        )


# ============================================================
# CAMERA
# ============================================================

def open_camera():

    try:

        intent = Intent(
            "android.media.action.IMAGE_CAPTURE"
        )

        open_intent(
            intent
        )

        speak(
            "Camera khol raha hoon."
        )

    except Exception as e:

        print(
            "Camera Error:",
            e
        )


# ============================================================
# CHROME
# ============================================================

def open_chrome():

    try:

        pm = activity.getPackageManager()

        intent = (
            pm.getLaunchIntentForPackage(
                "com.android.chrome"
            )
        )

        if intent is not None:

            open_intent(
                intent
            )

            speak(
                "Chrome khol raha hoon."
            )

            return

        open_url(
            "https://www.google.com"
        )

        speak(
            "Browser khol raha hoon."
        )

    except Exception as e:

        print(
            "Chrome Error:",
            e
        )

        open_url(
            "https://www.google.com"
        )


# ============================================================
# YOUTUBE
# ============================================================

def open_youtube():

    try:

        pm = activity.getPackageManager()

        intent = (
            pm.getLaunchIntentForPackage(
                "com.google.android.youtube"
            )
        )

        if intent is not None:

            open_intent(
                intent
            )

            speak(
                "YouTube khol raha hoon."
            )

            return

        open_url(
            "https://www.youtube.com"
        )

        speak(
            "YouTube khol raha hoon."
        )

    except Exception as e:

        print(
            "YouTube Error:",
            e
        )

        open_url(
            "https://www.youtube.com"
        )


# ============================================================
# GOOGLE SEARCH
# ============================================================

def google_search(query):

    try:

        query = str(
            query
        ).strip()

        if not query:

            speak(
                "Kya search karna hai?"
            )

            restart_listening()
            return

        import urllib.parse

        encoded = urllib.parse.quote_plus(
            query
        )

        url = (
            "https://www.google.com/search?q="
            + encoded
        )

        open_url(
            url
        )

        speak(
            "Google par search kar raha hoon."
        )

    except Exception as e:

        print(
            "Google Search Error:",
            e
        )


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def youtube_search(query):

    try:

        query = str(
            query
        ).strip()

        if not query:

            speak(
                "YouTube par kya search karna hai?"
            )

            restart_listening()
            return

        import urllib.parse

        encoded = urllib.parse.quote_plus(
            query
        )

        url = (
            "https://www.youtube.com/results?search_query="
            + encoded
        )

        open_url(
            url
        )

        speak(
            "YouTube par search kar raha hoon."
        )

    except Exception as e:

        print(
            "YouTube Search Error:",
            e
        )


# ============================================================
# MUSIC SEARCH
# ============================================================

def music_search(query):

    try:

        query = str(
            query
        ).strip()

        if not query:

            speak(
                "Music me kya search karna hai?"
            )

            restart_listening()
            return

        import urllib.parse

        encoded = urllib.parse.quote_plus(
            query
        )

        url = (
            "https://music.youtube.com/search?q="
            + encoded
        )

        open_url(
            url
        )

        speak(
            "Music search kar raha hoon."
        )

    except Exception as e:

        print(
            "Music Search Error:",
            e
        )


# ============================================================
# SETTINGS
# ============================================================

def open_settings():

    try:

        intent = Intent(
            Settings.ACTION_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Settings Error:",
            e
        )


def open_wifi_settings():

    try:

        intent = Intent(
            Settings.ACTION_WIFI_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Wi-Fi settings khol raha hoon."
        )

    except Exception as e:

        print(
            "WiFi Error:",
            e
        )


def open_bluetooth_settings():

    try:

        intent = Intent(
            Settings.ACTION_BLUETOOTH_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Bluetooth settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Bluetooth Error:",
            e
        )


def open_display_settings():

    try:

        intent = Intent(
            Settings.ACTION_DISPLAY_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Display settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Display Error:",
            e
        )


def open_battery_settings():

    try:

        intent = Intent(
            Settings.ACTION_BATTERY_SAVER_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Battery settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Battery Error:",
            e
        )

        try:

            intent = Intent(
                Settings.ACTION_SETTINGS
            )

            open_intent(
                intent
            )

        except Exception:
            pass


def open_location_settings():

    try:

        intent = Intent(
            Settings.ACTION_LOCATION_SOURCE_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Location settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Location Error:",
            e
        )


def open_security_settings():

    try:

        intent = Intent(
            Settings.ACTION_SECURITY_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Security settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Security Error:",
            e
        )


def open_mobile_network_settings():

    try:

        intent = Intent(
            Settings.ACTION_NETWORK_OPERATOR_SETTINGS
        )

        open_intent(
            intent
        )

        speak(
            "Mobile network settings khol raha hoon."
        )

    except Exception as e:

        print(
            "Mobile Network Error:",
            e
        )


# ============================================================
# PART 2 END
# ============================================================

# ============================================================
# TIME / DATE
# ============================================================

def tell_time():

    try:

        from datetime import datetime

        current_time = datetime.now().strftime(
            "%I:%M %p"
        )

        speak(
            "Abhi time hai "
            + current_time
        )

    except Exception as e:

        print(
            "Time Error:",
            e
        )


def tell_date():

    try:

        from datetime import datetime

        current_date = datetime.now().strftime(
            "%d %B %Y"
        )

        speak(
            "Aaj ki date hai "
            + current_date
        )

    except Exception as e:

        print(
            "Date Error:",
            e
        )


# ============================================================
# COMMAND NORMALIZATION
# ============================================================

def normalize_command(command):

    command = str(
        command
    ).lower().strip()

    replacements = {
        "wi fi": "wifi",
        "wi-fi": "wifi",
        "you tube": "youtube",
        "what's app": "whatsapp",
        "whats app": "whatsapp",
        "calculator": "calculator",
        "calcu later": "calculator"
    }

    for old, new in replacements.items():

        command = command.replace(
            old,
            new
        )

    return command


# ============================================================
# COMMAND PROCESSOR
# ============================================================

def process_command(command):

    command = normalize_command(
        command
    )

    print(
        "Command:",
        command
    )

    if not command:

        restart_listening()
        return


    # --------------------------------------------------------
    # GREETING
    # --------------------------------------------------------

    if (
        command == "hello"
        or
        command == "hi"
        or
        command == "hey"
        or
        "hello jarvis" in command
        or
        "hi jarvis" in command
    ):

        speak(
            "Hello. Main tumhara voice assistant hoon."
        )

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    if (
        "your name" in command
        or
        "what is your name" in command
        or
        "who are you" in command
        or
        "tumhara naam" in command
        or
        "aapka naam" in command
    ):

        speak(
            "Mera naam My Voice Assistant hai."
        )

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    if (
        "time" in command
        or
        "kitne baje" in command
        or
        "samay" in command
    ):

        tell_time()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if (
        "date" in command
        or
        "today" in command
        or
        "aaj ki date" in command
        or
        "tarikh" in command
    ):

        tell_date()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    if (
        command == "phone"
        or
        "phone kholo" in command
        or
        "phone open" in command
        or
        "dialer kholo" in command
        or
        "dialer open" in command
        or
        "calling app kholo" in command
    ):

        open_phone()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # CONTACTS
    # --------------------------------------------------------

    if (
        "contacts" in command
        or
        "contact kholo" in command
        or
        "contacts kholo" in command
        or
        "contact open" in command
    ):

        open_contacts()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # WHATSAPP
    # --------------------------------------------------------

    if (
        "whatsapp" in command
        or
        "what's app" in command
    ):

        open_whatsapp()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # CALCULATOR
    # --------------------------------------------------------

    if (
        "calculator" in command
        or
        "calculate app kholo" in command
    ):

        open_calculator()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    if (
        "camera" in command
        or
        "camera kholo" in command
        or
        "camera open" in command
    ):

        open_camera()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # CHROME
    # --------------------------------------------------------

    if (
        "chrome" in command
        or
        "chrome kholo" in command
        or
        "browser kholo" in command
    ):

        open_chrome()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # YOUTUBE
    # --------------------------------------------------------

    if (
        command == "youtube"
        or
        "youtube kholo" in command
        or
        "youtube open" in command
    ):

        open_youtube()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # YOUTUBE SEARCH
    # --------------------------------------------------------

    if (
        "youtube par search" in command
        or
        "youtube pe search" in command
        or
        "youtube search" in command
        or
        "youtube mein search" in command
    ):

        query = command

        for phrase in [
            "youtube par search karo",
            "youtube par search",
            "youtube pe search karo",
            "youtube pe search",
            "youtube search karo",
            "youtube search"
        ]:

            query = query.replace(
                phrase,
                ""
            )

        youtube_search(
            query.strip()
        )

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # MUSIC SEARCH
    # --------------------------------------------------------

    if (
        "music search" in command
        or
        "music mein search" in command
        or
        "music me search" in command
    ):

        query = command

        for phrase in [
            "music search karo",
            "music search",
            "music mein search karo",
            "music mein search",
            "music me search karo",
            "music me search"
        ]:

            query = query.replace(
                phrase,
                ""
            )

        music_search(
            query.strip()
        )

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # GOOGLE SEARCH
    # --------------------------------------------------------

    if (
        "google par search" in command
        or
        "google pe search" in command
        or
        "google search" in command
        or
        "web search" in command
        or
        "search karo" in command
    ):

        query = command

        for phrase in [
            "google par search karo",
            "google par search",
            "google pe search karo",
            "google pe search",
            "google search karo",
            "google search",
            "web search karo",
            "web search",
            "search karo"
        ]:

            query = query.replace(
                phrase,
                ""
            )

        google_search(
            query.strip()
        )

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # WIFI
    # --------------------------------------------------------

    if (
        "wifi" in command
        or
        "wifi settings" in command
        or
        "wifi setting" in command
    ):

        open_wifi_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # BLUETOOTH
    # --------------------------------------------------------

    if (
        "bluetooth" in command
        or
        "bluetooth settings" in command
    ):

        open_bluetooth_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    if (
        "display settings" in command
        or
        "display setting" in command
        or
        "screen settings" in command
    ):

        open_display_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    if (
        "battery settings" in command
        or
        "battery setting" in command
    ):

        open_battery_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if (
        "location settings" in command
        or
        "location setting" in command
        or
        "gps settings" in command
    ):

        open_location_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    if (
        "security settings" in command
        or
        "security setting" in command
    ):

        open_security_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # MOBILE NETWORK
    # --------------------------------------------------------

    if (
        "mobile network" in command
        or
        "mobile network settings" in command
        or
        "data settings" in command
        or
        "mobile data" in command
    ):

        open_mobile_network_settings()

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # INSTALLED APP
    # --------------------------------------------------------

    app_phrases = [
        " kholo",
        " open"
    ]

    common_apps = [
        "instagram",
        "facebook",
        "telegram",
        "maps",
        "gmail",
        "gallery",
        "settings",
        "files",
        "file manager",
        "play store",
        "clock",
        "calendar",
        "calculator",
        "camera",
        "chrome",
        "youtube",
        "whatsapp"
    ]

    for app_name in common_apps:

        if (
            command == app_name
            or
            command == app_name + " kholo"
            or
            command == app_name + " open"
        ):

            if app_name == "whatsapp":
                open_whatsapp()

            elif app_name == "calculator":
                open_calculator()

            elif app_name == "camera":
                open_camera()

            elif app_name == "chrome":
                open_chrome()

            elif app_name == "youtube":
                open_youtube()

            else:
                open_installed_app(
                    app_name
                )

            restart_listening(
                1.5
            )

            return


    # --------------------------------------------------------
    # GENERIC INSTALLED APP COMMAND
    # --------------------------------------------------------

    if (
        "app kholo" in command
        or
        "app open" in command
    ):

        app_name = command

        app_name = app_name.replace(
            "app kholo",
            ""
        )

        app_name = app_name.replace(
            "app open",
            ""
        )

        app_name = app_name.strip()

        if app_name:

            open_installed_app(
                app_name
            )

        else:

            speak(
                "Kaunsa app kholna hai?"
            )

        restart_listening(
            1.5
        )

        return


    # --------------------------------------------------------
    # UNKNOWN COMMAND
    # --------------------------------------------------------

    speak(
        "Command samajh nahi aaya."
    )

    restart_listening(
        1.5
    )


# ============================================================
# MAIN KIVY APP
# ============================================================

class VoiceAssistantApp(App):

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
            size=self.update_text_size
        )

        return self.label


    def update_text_size(
        self,
        instance,
        value
    ):

        instance.text_size = value


    def set_status(self, text):

        try:

            self.label.text = (
                "My Voice Assistant\n\n"
                + str(text)
            )

        except Exception as e:

            print(
                "UI Status Error:",
                e
            )


    def on_start(self):

        print(
            "Application started"
        )

        self.set_status(
            "Starting..."
        )

        # Give Android activity time to initialize.

        Clock.schedule_once(
            lambda dt:
            self.start_voice_system(),
            1.5
        )


    def start_voice_system(self):

        print(
            "Starting voice system..."
        )

        self.set_status(
            "Checking Microphone..."
        )

        if not has_microphone_permission():

            self.set_status(
                "Microphone Permission Required"
            )

            request_microphone_permission()

            return

        self.set_status(
            "Starting Speech..."
        )

        # TTS and SpeechRecognizer are both
        # initialized through Android main thread.

        run_on_android_thread(
            initialize_tts
        )

        Clock.schedule_once(
            lambda dt:
            setup_speech_recognizer(),
            0.8
        )


    def on_stop(self):

        global speech_recognizer
        global tts
        global speech_ready
        global is_listening

        print(
            "Application stopping..."
        )

        def cleanup():

            global speech_recognizer
            global tts
            global speech_ready
            global is_listening

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

                speech_ready = False
                is_listening = False

            except Exception as e:

                print(
                    "Speech Cleanup Error:",
                    e
                )

            try:

                if tts is not None:

                    tts.stop()
                    tts.shutdown()
                    tts = None

            except Exception as e:

                print(
                    "TTS Cleanup Error:",
                    e
                )

        run_on_android_thread(
            cleanup
        )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    VoiceAssistantApp().run()
