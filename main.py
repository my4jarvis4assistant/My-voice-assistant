from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method
from datetime import datetime


class MainThreadRunnable(PythonJavaClass):
    __javainterfaces__ = ['java/lang/Runnable']
    __javacontext__ = 'app'

    def __init__(self, function):
        super().__init__()
        self.function = function

    @java_method('()V')
    def run(self):
        self.function()


class RecognitionListener(PythonJavaClass):
    __javainterfaces__ = ['android/speech/RecognitionListener']
    __javacontext__ = 'app'

    def __init__(self, app):
        super().__init__()
        self.app = app

    @java_method('(Landroid/os/Bundle;)V')
    def onReadyForSpeech(self, params):
        self.app.label.text = "🎤 Bolna shuru kijiye..."

    @java_method('()V')
    def onBeginningOfSpeech(self):
        self.app.label.text = "👂 Sun raha hoon..."

    @java_method('(F)V')
    def onRmsChanged(self, rmsdB):
        pass

    @java_method('([B)V')
    def onBufferReceived(self, buffer):
        pass

    @java_method('()V')
    def onEndOfSpeech(self):
        self.app.label.text = "🧠 Samajh raha hoon..."

    @java_method('(ILjava/lang/String;)V')
    def onError(self, error):
        self.app.label.text = "❌ Speech Error: " + str(error)

        # Error ke baad dobara listening
        Clock.schedule_once(self.app.listen_again, 1)

    @java_method('(Landroid/os/Bundle;)V')
    def onResults(self, results):
        matches = results.getStringArrayList(
            "results_recognition"
        )

        if matches and matches.size() > 0:
            text = matches.get(0)

            self.app.label.text = (
                "Aapne kaha:\n" + text
            )

            self.app.process_command(text)

        else:
            self.app.label.text = "Kuch samajh nahi aaya."

            Clock.schedule_once(
                self.app.listen_again, 1
            )


class VoiceAssistant(App):

    def build(self):

        self.label = Label(
            text="🤖 JARVIS\n\nStarting...",
            font_size="22sp"
        )

        self.PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )

        self.SpeechRecognizer = autoclass(
            "android.speech.SpeechRecognizer"
        )

        self.RecognizerIntent = autoclass(
            "android.content.Intent"
        )

        self.TextToSpeech = autoclass(
            "android.speech.tts.TextToSpeech"
        )

        self.Locale = autoclass(
            "java.util.Locale"
        )

        self.activity = self.PythonActivity.mActivity

        # TTS
        self.tts = self.TextToSpeech(
            self.activity,
            None
        )

        self.tts.setLanguage(
            self.Locale.US
        )

        # Speech listener
        self.listener = RecognitionListener(self)

        # Main-thread setup
        self.setup_runnable = MainThreadRunnable(
            self.setup_speech
        )

        Clock.schedule_once(
            self.start_setup,
            0.5
        )

        return self.label

    def start_setup(self, dt):

        try:
            self.activity.runOnUiThread(
                self.setup_runnable
            )

        except Exception as e:

            self.label.text = (
                "Thread Error:\n" + str(e)
            )

    def setup_speech(self):

        try:

            self.recognizer = (
                self.SpeechRecognizer
                .createSpeechRecognizer(
                    self.activity
                )
            )

            self.recognizer.setRecognitionListener(
                self.listener
            )

            self.intent = self.RecognizerIntent(
                "android.speech.action.RECOGNIZE_SPEECH"
            )

            self.intent.putExtra(
                "android.speech.extra.LANGUAGE_MODEL",
                "free_form"
            )

            self.intent.putExtra(
                "android.speech.extra.LANGUAGE",
                "hi-IN"
            )

            self.label.text = (
                "🤖 JARVIS\n\n"
                "2 second baad boliye..."
            )

            self.listen_runnable = MainThreadRunnable(
                self.start_listening
            )

            Clock.schedule_once(
                self.start_listening_request,
                2
            )

        except Exception as e:

            self.label.text = (
                "Speech Setup Error:\n" +
                str(e)
            )

    def start_listening_request(self, dt):

        try:

            self.activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Listening Thread Error:\n" +
                str(e)
            )

    def start_listening(self):

        try:

            self.label.text = (
                "🎤 Bolna shuru kijiye..."
            )

            self.recognizer.startListening(
                self.intent
            )

        except Exception as e:

            self.label.text = (
                "Start Error:\n" +
                str(e)
            )

    def listen_again(self, dt):

        try:

            self.activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Restart Error:\n" +
                str(e)
            )

    def process_command(self, text):

        command = text.lower().strip()

        # 1. Hello
        if (
            "hello jarvis" in command
            or "hello jarvis" == command
        ):

            self.speak(
                "Hello! Main ready hoon."
            )

        # 2. Name
        elif (
            "tumhara naam kya hai" in command
            or "what is your name" in command
            or "your name" in command
        ):

            self.speak(
                "Mera naam JARVIS hai."
            )

        # 3. Time
        elif (
            "time kya hai" in command
            or "what time is it" in command
            or "time" == command
        ):

            current_time = datetime.now().strftime(
                "%I:%M %p"
            )

            self.speak(
                "Abhi time hai " +
                current_time
            )

        # Unknown command
        else:

            self.speak(
                "Maine suna: " + text
            )

    def speak(self, text):

        try:

            self.label.text = (
                "🔊 JARVIS:\n" + text
            )

            self.tts.speak(
                text,
                self.TextToSpeech.QUEUE_FLUSH,
                None
            )

            # Answer ke baad dobara sunna
            Clock.schedule_once(
                self.listen_again,
                3
            )

        except Exception as e:

            self.label.text = (
                "TTS Error:\n" + str(e)
            )


VoiceAssistant().run()
