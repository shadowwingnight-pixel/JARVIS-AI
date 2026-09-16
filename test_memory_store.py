"""Tests for JARVIS's local memory storage."""

import tempfile
import unittest
from pathlib import Path

from memory_store import MemoryStorageError, MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "memories.json"
        self.store = MemoryStore(self.path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_add_retrieve_search_and_delete_memory(self):
        saved_memory = self.store.add_memory("My favorite color is blue.")
        self.store.add_memory("I prefer concise answers.")

        self.assertEqual(len(self.store.retrieve_memories()), 2)
        self.assertEqual(
            self.store.search_memories("What is my favorite color?")[0]["id"],
            saved_memory["id"],
        )
        self.assertTrue(self.store.delete_memory(saved_memory["id"]))
        self.assertFalse(self.store.delete_memory(saved_memory["id"]))

    def test_missing_storage_starts_empty(self):
        self.assertEqual(self.store.retrieve_memories(), [])
        self.assertEqual(self.store.last_error, "")

    def test_corrupted_storage_is_not_overwritten(self):
        self.path.write_text("not valid json", encoding="utf-8")

        self.assertEqual(self.store.retrieve_memories(), [])
        self.assertTrue(self.store.last_error)
        with self.assertRaises(MemoryStorageError):
            self.store.add_memory("Do not overwrite broken storage.")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "not valid json")


if __name__ == "__main__":
    unittest.main()
