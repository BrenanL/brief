"""Configuration and environment loading for Brief."""

from pathlib import Path
from typing import Optional
import os

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def load_env() -> bool:
    """Load environment variables from .env file.

    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    if not HAS_DOTENV:
        return False

    # Try repo root first (relative to this file)
    repo_root = Path(__file__).parent.parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        return True

    # Try current directory
    if Path(".env").exists():
        load_dotenv()
        return True

    return False


# Brief configuration constants
BRIEF_DIR = ".brief"
MANIFEST_FILE = "manifest.jsonl"
RELATIONSHIPS_FILE = "relationships.jsonl"
TASKS_FILE = "tasks.jsonl"
ACTIVE_TASK_FILE = "active_task"
MEMORY_FILE = "memory.jsonl"
EMBEDDINGS_DB = "embeddings.db"
CONTEXT_DIR = "context"


def get_brief_path(base_path: Optional[Path] = None) -> Path:
    """Get the .brief directory path.

    Args:
        base_path: Base path to look for .brief directory.
                   If None, uses current working directory.

    Returns:
        Path to the .brief directory.
    """
    if base_path is None:
        base_path = Path.cwd()
    return base_path / BRIEF_DIR


def find_brief_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the root directory containing .brief by walking up.

    Args:
        start_path: Starting path for search. Defaults to cwd.

    Returns:
        Path to directory containing .brief, or None if not found.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        if (current / BRIEF_DIR).exists():
            return current
        current = current.parent

    # Check root
    if (current / BRIEF_DIR).exists():
        return current

    return None
