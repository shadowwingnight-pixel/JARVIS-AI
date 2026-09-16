"""Local, explicit memory storage for JARVIS."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_MEMORY_PATH = Path(__file__).parent / "data" / "memories.json"


class MemoryStorageError(Exception):
    """Raised when a memory change cannot be safely saved."""


class MemoryStore:
    """Store small user memories in a local JSON file."""

    def __init__(self, path=DEFAULT_MEMORY_PATH):
        self.path = Path(path)
        self.last_error = ""

    def retrieve_memories(self):
        """Return all saved memories, or an empty list when none are available."""
        return self._load_memories()

    def add_memory(self, content):
        """Save one explicitly requested memory and return its record."""
        content = content.strip()
        if not content:
            raise ValueError("A memory cannot be empty.")

        memories = self._load_memories()
        if self.last_error:
            raise MemoryStorageError(self.last_error)

        memory = {
            "id": uuid4().hex[:8],
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        memories.append(memory)
        self._save_memories(memories)
        return memory

    def search_memories(self, query, limit=3):
        """Return memories with words or phrases relevant to *query*."""
        query = query.strip().lower()
        if not query:
            return []

        query_words = set(re.findall(r"\b\w+\b", query))
        matches = []
        for memory in self._load_memories():
            content = memory["content"].lower()
            content_words = set(re.findall(r"\b\w+\b", content))
            score = len(query_words.intersection(content_words))
            if query in content:
                score += len(query_words) + 1
            if score:
                matches.append((score, memory))

        matches.sort(key=lambda item: item[0], reverse=True)
        return [memory for _, memory in matches[:limit]]

    def delete_memory(self, memory_id):
        """Delete the memory with *memory_id* and report whether it existed."""
        memories = self._load_memories()
        if self.last_error:
            raise MemoryStorageError(self.last_error)

        kept_memories = [memory for memory in memories if memory["id"] != memory_id]
        if len(kept_memories) == len(memories):
            return False

        self._save_memories(kept_memories)
        return True

    def _load_memories(self):
        self.last_error = ""
        if not self.path.exists():
            return []

        try:
            with self.path.open("r", encoding="utf-8") as memory_file:
                memories = json.load(memory_file)
        except (OSError, json.JSONDecodeError) as error:
            self.last_error = f"Could not read local memory storage: {error}"
            return []

        if not isinstance(memories, list) or not all(
            isinstance(memory, dict)
            and isinstance(memory.get("id"), str)
            and isinstance(memory.get("content"), str)
            for memory in memories
        ):
            self.last_error = "Local memory storage has an unexpected format."
            return []
        return memories

    def _save_memories(self, memories):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(".json.tmp")
            with temporary_path.open("w", encoding="utf-8") as memory_file:
                json.dump(memories, memory_file, indent=2, ensure_ascii=False)
                memory_file.write("\n")
            temporary_path.replace(self.path)
        except OSError as error:
            raise MemoryStorageError(f"Could not save local memory storage: {error}") from error
