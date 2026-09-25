from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

from jnius import autoclass, PythonJavaClass, java_method


# Android Main Thread ke liye Runnable
class MainThreadRunnable(PythonJavaClass):

    __javainterfaces__ = ['java/lang/Runnable']
    __javacontext__ = 'app'

    def __init__(self, function):
        super().__init__()
        self.function = function

    @java_method('()V')
    def run(self):
        self.function()


# Speech Recognition Listener
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
        self.app.label.text = "🎤 Sun raha hoon..."

    @java_method('(F)V')
    def onRmsChanged(self, rmsdB):
        pass

    @java_method('([B)V')
    def onBufferReceived(self, buffer):
        pass

    @java_method('()V')
    def onEndOfSpeech(self):
        self.app.label.text = "⏳ Samajh raha hoon..."

    @java_method('(ILjava/lang/String;)V')
    def onError(self, error):
        self.app.label.text = "❌ Speech Error: " + str(error)

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
        else:
            self.app.label.text = (
                "Kuch samajh nahi aaya."
            )


class VoiceAssistant(App):

    def build(self):

        self.label = Label(
            text="🎤 Voice Assistant\n\nStarting...",
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

        # Listener ko reference me rakhna zaroori hai
        self.listener = RecognitionListener(self)

        # Runnable ko reference me rakhna
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

            activity = self.PythonActivity.mActivity

            # Android Main Thread par setup
            activity.runOnUiThread(
                self.setup_runnable
            )

        except Exception as e:

            self.label.text = (
                "Thread Error:\n" + str(e)
            )


    def setup_speech(self):

        try:

            activity = self.PythonActivity.mActivity

            # SpeechRecognizer Main Thread par create hoga
            self.recognizer = (
                self.SpeechRecognizer
                .createSpeechRecognizer(
                    activity
                )
            )

            # Listener set karna
            self.recognizer.setRecognitionListener(
                self.listener
            )

            # Voice recognition intent
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
                "🎤 Voice Assistant\n\n"
                "2 second baad boliye..."
            )

            # Listening bhi Main Thread par
            self.listen_runnable = MainThreadRunnable(
                self.start_listening
            )

            Clock.schedule_once(
                self.start_listening_request,
                2
            )

        except Exception as e:

            self.label.text = (
                "Speech Setup Error:\n" + str(e)
            )


    def start_listening_request(self, dt):

        try:

            activity = self.PythonActivity.mActivity

            activity.runOnUiThread(
                self.listen_runnable
            )

        except Exception as e:

            self.label.text = (
                "Listening Thread Error:\n"
                + str(e)
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
                "Start Error:\n" + str(e)
            )


VoiceAssistant().run()
