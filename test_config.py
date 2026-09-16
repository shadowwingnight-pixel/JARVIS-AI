"""Tests for local environment configuration."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import load_local_environment


class ConfigTests(unittest.TestCase):
    def test_local_env_does_not_replace_a_real_environment_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("BRAVE_SEARCH_API_KEY=from-file\n", encoding="utf-8")
            with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "from-environment"}, clear=True):
                load_local_environment(path)
                self.assertEqual(os.environ["BRAVE_SEARCH_API_KEY"], "from-environment")

    def test_local_env_loads_a_missing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("BRAVE_SEARCH_API_KEY=from-file\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                load_local_environment(path)
                self.assertEqual(os.environ["BRAVE_SEARCH_API_KEY"], "from-file")


if __name__ == "__main__":
    unittest.main()
