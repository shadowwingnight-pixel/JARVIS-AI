"""Tests for JARVIS's explicit command router."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from command_router import CommandRouter
from memory_store import MemoryStore
from system_control import SystemControlError
from web_search import WebSearchError, WebSearchResult


class CommandRouterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        path = Path(self.temporary_directory.name) / "memories.json"
        self.store = MemoryStore(path)
        self.web_search_client = MagicMock()
        self.system_controller = MagicMock()
        self.system_controller.get_cpu_usage.return_value = "CPU usage is 20.0% across all processors."
        self.system_controller.get_ram_usage.return_value = "RAM usage is 4.0 GB of 8.0 GB (50%)."
        self.system_controller.get_disk_usage.return_value = "Disk usage is 100.0 GB of 200.0 GB (50.0%)."
        self.system_controller.get_operating_system.return_value = "You are running Windows 11."
        self.system_controller.open_chrome.return_value = "Opening Google Chrome."
        self.system_controller.open_vs_code.return_value = "Opening VS Code."
        self.system_controller.open_downloads_folder.return_value = "Opening your Downloads folder."
        self.system_controller.open_url.return_value = "Opening that URL."
        self.system_controller.take_screenshot.return_value = "Screenshot saved locally."
        self.router = CommandRouter(
            self.store, self.web_search_client, self.system_controller
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_normal_conversation_is_not_handled_as_a_command(self):
        self.assertIsNone(self.router.handle("Tell me a joke about robots."))

    @patch("command_router.datetime")
    def test_date_and_time_command(self, mock_datetime):
        fixed_time = datetime(2026, 9, 14, 9, 30).astimezone()
        mock_datetime.now.return_value.astimezone.return_value = fixed_time

        result = self.router.handle("What time is it")

        self.assertIn("Monday, September 14, 2026", result.message)
        self.assertIn("09:30 AM", result.message)

    def test_allowlisted_app_commands(self):
        chrome_result = self.router.handle("open chrome")
        code_result = self.router.handle("open VS Code")

        self.assertEqual(chrome_result.message, "Opening Google Chrome.")
        self.assertEqual(code_result.message, "Opening VS Code.")
        self.system_controller.open_chrome.assert_called_once()
        self.system_controller.open_vs_code.assert_called_once()

    def test_explicit_http_url_opens_in_browser(self):
        result = self.router.handle("open https://example.com/help")

        self.assertEqual(result.message, "Opening that URL.")
        self.system_controller.open_url.assert_called_once_with("https://example.com/help")

    def test_unsafe_open_input_is_not_executed(self):
        self.system_controller.open_url.side_effect = SystemControlError(
            "Please provide a complete http or https URL."
        )
        result = self.router.handle("open chrome && delete everything")

        self.assertIn("complete http", result.message)
        self.system_controller.open_url.assert_called_once_with("chrome && delete everything")

    def test_system_status_and_screenshot_commands(self):
        self.assertIn("CPU", self.router.handle("get CPU usage").message)
        self.assertIn("RAM", self.router.handle("get RAM usage").message)
        self.assertIn("Disk", self.router.handle("get disk usage").message)
        self.assertIn("Windows", self.router.handle("report the current operating system").message)
        self.assertIn("Screenshot", self.router.handle("take a screenshot").message)
        self.system_controller.get_cpu_usage.assert_called_once()
        self.system_controller.get_ram_usage.assert_called_once()
        self.system_controller.get_disk_usage.assert_called_once()
        self.system_controller.get_operating_system.assert_called_once()
        self.system_controller.take_screenshot.assert_called_once()

    def test_memory_commands_and_natural_retrieval(self):
        saved = self.router.handle("remember that I prefer concise answers.")
        memory_id = saved.message.split("ID: ")[1].rstrip(").")

        remembered = self.router.handle("what do you remember about me")
        search_result = self.router.handle("search memories concise")
        deleted = self.router.handle(f"forget {memory_id}")

        self.assertIn("I prefer concise answers.", remembered.message)
        self.assertIn("I prefer concise answers.", search_result.message)
        self.assertEqual(deleted.message, "I deleted that memory.")
        self.assertEqual(self.store.retrieve_memories(), [])

    def test_exit_command_requests_a_safe_exit(self):
        result = self.router.handle("exit")

        self.assertTrue(result.should_exit)
        self.assertEqual(result.message, "Goodbye!")

    def test_explicit_web_search_returns_context_for_ollama(self):
        self.web_search_client.search.return_value = [
            WebSearchResult("Current result", "https://example.com", "Current details.")
        ]

        result = self.router.handle("search the web for current Python release")

        self.assertIn("current web results", result.message)
        self.assertIn("Current result", result.web_context)
        self.web_search_client.search.assert_called_once_with("current Python release")

    def test_current_information_request_uses_web_search(self):
        self.web_search_client.search.return_value = []

        result = self.router.handle("latest space news")

        self.assertEqual(result.message, "I found no current web results for that search.")
        self.web_search_client.search.assert_called_once_with("latest space news")

    def test_web_search_failure_is_returned_without_ollama_context(self):
        self.web_search_client.search.side_effect = WebSearchError("Web search is unavailable.")

        result = self.router.handle("web search current weather")

        self.assertEqual(result.message, "Web search is unavailable.")
        self.assertIsNone(result.web_context)


if __name__ == "__main__":
    unittest.main()
