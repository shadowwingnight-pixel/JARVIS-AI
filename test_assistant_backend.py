"""Display-free integration tests for the GUI-facing JARVIS backend."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from assistant_backend import AssistantBackend
from command_router import CommandResult
from memory_store import MemoryStore


class AssistantBackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.memory_store = MemoryStore(Path(self.temporary_directory.name) / "memories.json")
        self.router = MagicMock()
        self.ollama_client = MagicMock()
        self.system_controller = MagicMock()
        self.backend = AssistantBackend(
            self.memory_store, self.router, self.ollama_client, "test-model", self.system_controller
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_normal_conversation_reaches_ollama(self):
        self.router.handle.return_value = None
        self.ollama_client.chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="Hello from Ollama.")
        )

        reply = self.backend.process("Hello JARVIS")

        self.assertEqual(reply.message, "Hello from Ollama.")
        self.assertEqual(self.ollama_client.chat.call_args.kwargs["model"], "test-model")
        self.assertEqual(len(self.backend.conversation_history), 2)

    def test_local_command_does_not_reach_ollama(self):
        self.router.handle.return_value = CommandResult("CPU usage is 20%.")

        reply = self.backend.process("get CPU usage")

        self.assertEqual(reply.message, "CPU usage is 20%.")
        self.ollama_client.chat.assert_not_called()

    def test_web_context_reaches_ollama_and_keeps_notice(self):
        self.router.handle.return_value = CommandResult(
            "I found current web results.", web_context="Current web search results for: Python"
        )
        self.ollama_client.chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="Here is a summary.")
        )

        reply = self.backend.process("search the web for Python")

        self.assertEqual(reply.notices, ["I found current web results."])
        self.assertIn(
            "Current web search results", self.ollama_client.chat.call_args.kwargs["messages"][0]["content"]
        )

    def test_clear_conversation_keeps_saved_memory(self):
        self.memory_store.add_memory("My preferred color is blue.")
        self.backend.conversation_history.append({"role": "user", "content": "Hello"})

        self.backend.clear_conversation()

        self.assertEqual(self.backend.conversation_history, [])
        self.assertEqual(len(self.memory_store.retrieve_memories()), 1)

    def test_system_information_handles_one_failed_metric(self):
        self.system_controller.get_cpu_usage.return_value = "CPU usage is 10%."
        self.system_controller.get_ram_usage.side_effect = RuntimeError("unavailable")
        self.system_controller.get_disk_usage.return_value = "Disk usage is 50%."

        information = self.backend.get_system_information()

        self.assertEqual(information["CPU"], "CPU usage is 10%.")
        self.assertIn("RAM unavailable", information["RAM"])
        self.assertEqual(information["Disk"], "Disk usage is 50%.")


if __name__ == "__main__":
    unittest.main()
