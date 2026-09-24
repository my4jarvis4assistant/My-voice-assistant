from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock

from jnius import autoclass, PythonJavaClass, java_method


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
        self.app.label.text = "❌ Speech error: " + str(error)

    @java_method('(Landroid/os/Bundle;)V')
    def onResults(self, results):
        matches = results.getStringArrayList(
            "results_recognition"
        )

        if matches and matches.size() > 0:
            text = matches.get(0)
            self.app.label.text = "Aapne kaha:\n" + text
        else:
            self.app.label.text = "Kuch samajh nahi aaya."


class VoiceAssistant(App):

    def build(self):
        self.label = Label(
            text="🎤 Voice Assistant\n\n2 second baad boliye...",
            font_size="22sp"
        )

        self.SpeechRecognizer = autoclass(
            "android.speech.SpeechRecognizer"
        )
        self.RecognizerIntent = autoclass(
            "android.content.Intent"
        )
        self.PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )

        self.listener = RecognitionListener(self)

        self.recognizer = self.SpeechRecognizer(
            self.PythonActivity.mActivity,
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

        Clock.schedule_once(self.start_listening, 2)

        return self.label

    def start_listening(self, dt):
        self.label.text = "🎤 Bolna shuru kijiye..."
        self.recognizer.startListening(self.intent)


VoiceAssistant().run()
