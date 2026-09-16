"""Display-free smoke tests for the GUI and voice-service modules."""

import unittest
from unittest.mock import MagicMock, patch

import jarvis_gui
from voice_service import VoiceService


class GuiModuleTests(unittest.TestCase):
    def test_gui_module_exposes_a_desktop_application_without_creating_one(self):
        self.assertTrue(callable(jarvis_gui.JarvisGUI))
        self.assertTrue(callable(jarvis_gui.main))
        self.assertEqual(jarvis_gui.THEME["background"], "#070B14")

    def test_system_metric_value_is_compact_for_dashboard_cards(self):
        self.assertEqual(
            jarvis_gui.system_metric_value("CPU", "CPU usage is 24.5% across all processors."),
            "24.5% across all processors",
        )
        self.assertEqual(
            jarvis_gui.system_metric_value("RAM", "RAM unavailable: unavailable"),
            "RAM unavailable: unavailable",
        )

    def test_submit_uses_a_callback_keyword_for_backend_processing(self):
        gui = object.__new__(jarvis_gui.JarvisGUI)
        gui.input_box = MagicMock()
        gui.input_box.get.return_value = "get CPU usage"
        gui.backend = MagicMock()
        gui._append = MagicMock()
        gui._set_activity = MagicMock()
        gui._run_in_background = MagicMock()
        gui._handle_reply = MagicMock()

        gui.submit_text()

        gui.input_box.delete.assert_called_once_with(0, jarvis_gui.tk.END)
        gui._run_in_background.assert_called_once_with(
            gui.backend.process, "get CPU usage", callback=gui._handle_reply
        )

    @patch("voice_service.sr.Microphone")
    @patch("voice_service.sr.Recognizer")
    def test_voice_service_returns_recognized_text(self, mock_recognizer, mock_microphone):
        microphone = MagicMock()
        microphone.__enter__.return_value = microphone
        mock_microphone.return_value = microphone
        recognizer = mock_recognizer.return_value
        recognizer.recognize_google.return_value = "  Hello JARVIS  "

        result = VoiceService().listen()

        self.assertEqual(result.text, "Hello JARVIS")
        self.assertEqual(recognizer.recognize_google.call_args.kwargs["language"], "en-IN")

    @patch("voice_service.pyttsx3.init")
    def test_voice_service_speaks_through_pyttsx3(self, mock_init):
        speaker = mock_init.return_value

        VoiceService.speak("Hello")

        speaker.say.assert_called_once_with("Hello")
        speaker.runAndWait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
