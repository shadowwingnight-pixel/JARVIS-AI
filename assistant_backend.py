"""GUI-friendly adapter around JARVIS's existing command and Ollama backend."""

from dataclasses import dataclass, field

import ollama

from command_router import CommandRouter
from memory_store import MemoryStore
from system_control import SystemController


MODEL_NAME = "qwen2.5:3b-instruct"
ASSISTANT_INSTRUCTIONS = (
    "You are JARVIS, a friendly, calm, and helpful assistant. "
    "Give clear beginner-friendly answers and keep responses concise."
)


@dataclass
class AssistantReply:
    """One backend response for the terminal or desktop interface."""

    message: str
    should_exit: bool = False
    notices: list[str] = field(default_factory=list)


def build_messages(conversation_history, user_input, memory_store, web_context=None):
    """Build Ollama messages with relevant local memory and optional web context."""
    relevant_memories = memory_store.search_memories(user_input)
    instructions = ASSISTANT_INSTRUCTIONS
    if relevant_memories:
        memory_text = "\n".join(f"- {memory['content']}" for memory in relevant_memories)
        instructions += (
            "\n\nRelevant memories the user explicitly asked you to save:\n"
            f"{memory_text}\nUse these only when they help answer the current request."
        )
    if web_context:
        instructions += f"\n\n{web_context}"
    return [{"role": "system", "content": instructions}, *conversation_history]


class AssistantBackend:
    """Process one user message without depending on a particular user interface."""

    def __init__(
        self,
        memory_store=None,
        command_router=None,
        ollama_client=ollama,
        model_name=MODEL_NAME,
        system_controller=None,
    ):
        self.memory_store = memory_store or MemoryStore()
        self.command_router = command_router or CommandRouter(self.memory_store)
        self.ollama_client = ollama_client
        self.model_name = model_name
        self.system_controller = system_controller or SystemController()
        self.conversation_history = []

    def process(self, user_input):
        """Route a command or ask Ollama, returning a UI-neutral reply."""
        user_input = user_input.strip()
        if not user_input:
            return AssistantReply("Please enter a message.")

        command_result = self.command_router.handle(user_input)
        if command_result and not command_result.web_context:
            return AssistantReply(command_result.message, command_result.should_exit)

        web_context = command_result.web_context if command_result else None
        notices = [command_result.message] if command_result else []
        self.conversation_history.append({"role": "user", "content": user_input})
        try:
            messages = build_messages(
                self.conversation_history, user_input, self.memory_store, web_context
            )
            response = self.ollama_client.chat(model=self.model_name, messages=messages)
            assistant_message = response.message.content
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )
            return AssistantReply(assistant_message, notices=notices)
        except ollama.ResponseError as error:
            self.conversation_history.pop()
            if error.status_code == 404:
                return AssistantReply(
                    f"The Ollama model '{self.model_name}' is unavailable. "
                    f"Run: ollama pull {self.model_name}"
                )
            return AssistantReply(f"Ollama returned an error: {error}")
        except Exception as error:
            self.conversation_history.pop()
            return AssistantReply(
                "I could not connect to Ollama. Make sure Ollama is running "
                f"and try again. Details: {error}"
            )

    def clear_conversation(self):
        """Clear only in-memory chat history, never saved local memories."""
        self.conversation_history.clear()

    def check_online(self):
        """Return whether the local Ollama service responds."""
        try:
            self.ollama_client.list()
        except Exception:
            return False
        return True

    def get_system_information(self):
        """Collect the small status summary displayed by the GUI."""
        getters = {
            "CPU": self.system_controller.get_cpu_usage,
            "RAM": self.system_controller.get_ram_usage,
            "Disk": self.system_controller.get_disk_usage,
        }
        information = {}
        for label, getter in getters.items():
            try:
                information[label] = getter()
            except Exception as error:
                information[label] = f"{label} unavailable: {error}"
        return information
