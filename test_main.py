"""Tests for JARVIS message construction and application flow."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from command_router import CommandResult
from memory_store import MemoryStore


class MainMemoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        path = Path(self.temporary_directory.name) / "memories.json"
        self.store = MemoryStore(path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_relevant_memory_is_added_to_ollama_system_message(self):
        self.store.add_memory("My favorite color is blue.")

        messages = main.build_messages(
            [{"role": "user", "content": "What is my favorite color?"}],
            "What is my favorite color?",
            self.store,
        )

        self.assertIn("My favorite color is blue.", messages[0]["content"])
        self.assertEqual(messages[1]["content"], "What is my favorite color?")

    def test_web_context_is_added_to_ollama_system_message(self):
        web_context = "Current web search results for: current Python release"

        messages = main.build_messages(
            [{"role": "user", "content": "search the web for current Python release"}],
            "search the web for current Python release",
            self.store,
            web_context,
        )

        self.assertIn(web_context, messages[0]["content"])

    def test_text_mode_sends_a_message_and_exits(self):
        response = type(
            "Response", (), {"message": type("Message", (), {"content": "Hello!"})()}
        )()
        with (
            patch("main.pyttsx3.init"),
            patch("main.sr.Recognizer"),
            patch("main.sr.Microphone"),
            patch("main.speak"),
            patch("main.ollama.chat", return_value=response) as chat,
            patch("builtins.input", side_effect=["text", "Hello JARVIS", "exit"]),
        ):
            main.main()

        self.assertEqual(chat.call_count, 1)
        self.assertEqual(chat.call_args.kwargs["model"], main.MODEL_NAME)
        self.assertEqual(chat.call_args.kwargs["messages"][1]["content"], "Hello JARVIS")

    def test_web_search_context_reaches_ollama_in_the_application_loop(self):
        response = type(
            "Response", (), {"message": type("Message", (), {"content": "Web summary."})()}
        )()
        web_context = "Current web search results for: latest space news"
        router = unittest.mock.MagicMock()
        router.handle.side_effect = [
            CommandResult("I found current web results.", web_context=web_context),
            CommandResult("Goodbye!", should_exit=True),
        ]
        with (
            patch("main.CommandRouter", return_value=router),
            patch("main.pyttsx3.init"),
            patch("main.sr.Recognizer"),
            patch("main.sr.Microphone"),
            patch("main.speak"),
            patch("main.ollama.chat", return_value=response) as chat,
            patch("builtins.input", side_effect=["text", "latest space news", "exit"]),
        ):
            main.main()

        self.assertEqual(chat.call_count, 1)
        self.assertIn(web_context, chat.call_args.kwargs["messages"][0]["content"])

    def test_listen_for_input_returns_recognized_voice_text(self):
        class FakeMicrophone:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        class FakeRecognizer:
            def listen(self, *_args, **_kwargs):
                return "audio"

            def recognize_google(self, audio, language):
                self.audio = audio
                self.language = language
                return "  Hello JARVIS  "

        recognizer = FakeRecognizer()
        with patch("builtins.print"):
            result = main.listen_for_input(recognizer, FakeMicrophone())

        self.assertEqual(result, "Hello JARVIS")
        self.assertEqual(recognizer.language, "en-IN")


if __name__ == "__main__":
    unittest.main()
