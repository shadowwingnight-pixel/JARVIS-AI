"""Background-friendly microphone input and speech output for JARVIS UIs."""

from dataclasses import dataclass

import pyttsx3
import speech_recognition as sr


@dataclass
class VoiceInputResult:
    text: str = ""
    error: str = ""


class VoiceService:
    """Use the project's existing SpeechRecognition and pyttsx3 dependencies."""

    def __init__(self, microphone_device_index=30):
        self.microphone_device_index = microphone_device_index

    def listen(self):
        """Capture one English (India) voice request for a UI worker thread."""
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(device_index=self.microphone_device_index)
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            return VoiceInputResult(
                text=recognizer.recognize_google(audio, language="en-IN").strip()
            )
        except sr.WaitTimeoutError:
            return VoiceInputResult(error="I did not hear anything.")
        except sr.UnknownValueError:
            return VoiceInputResult(error="I could not understand that.")
        except sr.RequestError as error:
            return VoiceInputResult(error=f"Speech recognition is unavailable: {error}")
        except OSError as error:
            return VoiceInputResult(error=f"Microphone is unavailable: {error}")

    @staticmethod
    def speak(text):
        """Speak one response; call this from a worker thread, not the GUI thread."""
        speaker = pyttsx3.init()
        speaker.say(text)
        speaker.runAndWait()
