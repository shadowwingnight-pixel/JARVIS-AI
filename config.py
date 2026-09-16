"""Small local configuration helpers for JARVIS."""

import os
from pathlib import Path


ENV_PATH = Path(__file__).parent / ".env"


def load_local_environment(path=ENV_PATH):
    """Load simple KEY=value entries without replacing real environment values."""
    path = Path(path)
    if not path.exists():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"\'')
        if key:
            os.environ.setdefault(key, value)


def get_brave_search_api_key():
    """Return the optional Brave Search API key without displaying it."""
    load_local_environment()
    return os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
