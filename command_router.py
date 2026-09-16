"""Explicit, safe commands that do not need an Ollama response."""

from dataclasses import dataclass
from datetime import datetime
from memory_store import MemoryStorageError
from system_control import SystemControlError, SystemController
from web_search import WebSearchClient, WebSearchError, format_results_for_assistant


@dataclass
class CommandResult:
    """The response returned when a command was handled."""

    message: str
    should_exit: bool = False
    web_context: str | None = None


class CommandRouter:
    """Route explicitly phrased commands without executing arbitrary input."""

    def __init__(self, memory_store, web_search_client=None, system_controller=None):
        self.memory_store = memory_store
        self.web_search_client = web_search_client or WebSearchClient()
        self.system_controller = system_controller or SystemController()

    def handle(self, user_input):
        """Return a result for a command, or None for normal conversation."""
        command = user_input.strip()
        normalized = command.lower()

        if normalized in ("exit", "quit", "bye"):
            return CommandResult("Goodbye!", should_exit=True)

        if normalized == "command help":
            return CommandResult(
                "Try 'what time is it', 'open chrome', 'open VS Code', "
                "'open https://example.com', 'remember <fact>', 'memories', "
                "'search memories <words>', 'search the web for <topic>', "
                "'forget <id>', or 'exit'."
            )

        if self._is_date_time_command(normalized):
            now = datetime.now().astimezone()
            return CommandResult(now.strftime("It is %A, %B %d, %Y at %I:%M %p %Z."))

        if normalized.startswith("open "):
            return self._open_target(command[5:].strip())

        system_result = self._handle_system_command(normalized)
        if system_result:
            return system_result

        web_result = self._handle_web_search_command(command, normalized)
        if web_result:
            return web_result

        memory_result = self._handle_memory_command(command, normalized)
        if memory_result:
            return memory_result
        return None

    def _handle_web_search_command(self, command, normalized):
        prefixes = (
            "search the web for ",
            "search web for ",
            "web search ",
        )
        query = next(
            (command[len(prefix):].strip() for prefix in prefixes if normalized.startswith(prefix)),
            None,
        )
        if query is None and self._requests_current_information(normalized):
            query = command
        if query is None:
            return None
        if not query:
            return CommandResult("Please say what you want me to search the web for.")

        try:
            results = self.web_search_client.search(query)
        except WebSearchError as error:
            return CommandResult(str(error))

        context = format_results_for_assistant(query, results)
        if not results:
            return CommandResult("I found no current web results for that search.")
        return CommandResult(
            "I found current web results. I will summarize them separately from my local knowledge.",
            web_context=context,
        )

    @staticmethod
    def _requests_current_information(command):
        return command.startswith(
            (
                "latest ",
                "what is the latest ",
                "current ",
                "what is the current ",
                "today's ",
                "todays ",
            )
        )

    @staticmethod
    def _is_date_time_command(command):
        return command in {
            "what time is it",
            "what's the time",
            "tell me the time",
            "what is the date",
            "what's the date",
            "what date is it",
            "tell me the date",
            "what is the current date and time",
            "tell me the current date and time",
        }

    def _open_target(self, target):
        """Open only an allowlisted app or an explicit safe URL."""
        actions = {
            "chrome": self.system_controller.open_chrome,
            "google chrome": self.system_controller.open_chrome,
            "vs code": self.system_controller.open_vs_code,
            "visual studio code": self.system_controller.open_vs_code,
            "downloads": self.system_controller.open_downloads_folder,
            "downloads folder": self.system_controller.open_downloads_folder,
        }
        action = actions.get(target.lower())
        try:
            if action:
                return CommandResult(action())
            return CommandResult(self.system_controller.open_url(target))
        except SystemControlError as error:
            return CommandResult(str(error))

    def _handle_system_command(self, command):
        actions = {
            "cpu usage": self.system_controller.get_cpu_usage,
            "get cpu usage": self.system_controller.get_cpu_usage,
            "what is cpu usage": self.system_controller.get_cpu_usage,
            "ram usage": self.system_controller.get_ram_usage,
            "get ram usage": self.system_controller.get_ram_usage,
            "what is ram usage": self.system_controller.get_ram_usage,
            "memory usage": self.system_controller.get_ram_usage,
            "disk usage": self.system_controller.get_disk_usage,
            "get disk usage": self.system_controller.get_disk_usage,
            "storage usage": self.system_controller.get_disk_usage,
            "what operating system am i using": self.system_controller.get_operating_system,
            "what os am i using": self.system_controller.get_operating_system,
            "current operating system": self.system_controller.get_operating_system,
            "report the current operating system": self.system_controller.get_operating_system,
            "take a screenshot": self.system_controller.take_screenshot,
            "take screenshot": self.system_controller.take_screenshot,
        }
        action = actions.get(command)
        if not action:
            return None
        try:
            return CommandResult(action())
        except SystemControlError as error:
            return CommandResult(str(error))

    def _handle_memory_command(self, command, normalized):
        if normalized == "memory help":
            return CommandResult(
                "Use 'remember <fact>', 'memories', 'search memories <words>', "
                "or 'forget <id>'."
            )

        if normalized.startswith("remember "):
            content = command[len("remember "):].strip()
            if content.lower().startswith("that "):
                content = content[5:].strip()
            try:
                memory = self.memory_store.add_memory(content)
            except (ValueError, MemoryStorageError) as error:
                return CommandResult(f"I could not save that memory: {error}")
            return CommandResult(f"I saved that memory (ID: {memory['id']}).")

        if normalized in {
            "memories",
            "what do you remember",
            "what do you remember about me",
            "what does jarvis remember",
        }:
            memories = self.memory_store.retrieve_memories()
            if self.memory_store.last_error:
                return CommandResult(self.memory_store.last_error)
            if not memories:
                return CommandResult("You have no saved memories.")
            return CommandResult(self._format_memories("Saved memories:", memories))

        if normalized.startswith("search memories "):
            query = command[len("search memories "):].strip()
            memories = self.memory_store.search_memories(query)
            if self.memory_store.last_error:
                return CommandResult(self.memory_store.last_error)
            if not memories:
                return CommandResult("I found no matching memories.")
            return CommandResult(self._format_memories("Matching memories:", memories))

        if normalized.startswith("forget "):
            memory_id = command[len("forget "):].strip()
            try:
                deleted = self.memory_store.delete_memory(memory_id)
            except MemoryStorageError as error:
                return CommandResult(f"I could not delete that memory: {error}")
            if deleted:
                return CommandResult("I deleted that memory.")
            return CommandResult("I could not find a memory with that ID.")

        return None

    @staticmethod
    def _format_memories(heading, memories):
        lines = [heading]
        lines.extend(f"- {memory['id']}: {memory['content']}" for memory in memories)
        return "\n".join(lines)
