from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from jnius import autoclass


class MyAssistant(App):

    def build(self):

        TextToSpeech = autoclass(
            "android.speech.tts.TextToSpeech"
        )

        PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )

        Locale = autoclass(
            "java.util.Locale"
        )

        self.TextToSpeech = TextToSpeech

        self.tts = TextToSpeech(
            PythonActivity.mActivity,
            None
        )

        self.tts.setLanguage(Locale.US)

        Clock.schedule_once(self.speak_test, 2)

        return Label(
            text="My Voice Assistant APK"
        )

    def speak_test(self, dt):

        self.tts.speak(
            "Hello! Main tumhara voice assistant hoon.",
            self.TextToSpeech.QUEUE_FLUSH,
            None
        )


MyAssistant().run()
