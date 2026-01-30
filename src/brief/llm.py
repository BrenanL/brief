"""LLM client wrapper for Brief using BAML."""

from typing import Optional
from pathlib import Path
from .config import load_env, get_brief_path

# Load environment before any BAML imports
load_env()

# Model alias -> BAML client name mapping
# User-friendly names map to the BAML client definitions in clients.baml
MODELS = {
    # OpenAI
    "gpt-4o-mini": "GPT4oMini",
    "gpt-4o": "GPT4o",
    "gpt-5-mini": "GPT5Mini",
    # Anthropic
    "claude-sonnet": "ClaudeSonnet",
    "claude-haiku": "ClaudeHaiku",
    # Google Gemini
    "gemini-2.0-flash": "Gemini20Flash",
    "gemini-2.0-flash-lite": "Gemini20FlashLite",
    "gemini-2.5-flash-lite": "Gemini25FlashLite",
    "gemini-2.5-flash": "Gemini25Flash",
    "gemini-3-flash-preview": "Gemini3FlashPreview",
    # Default fallback
    "default": "Default",
}

DEFAULT_MODEL = "gemini-2.5-flash"

# File to store active model (session override)
ACTIVE_MODEL_FILE = "active_model"


def get_available_models() -> list[str]:
    """Return list of available model aliases."""
    return [m for m in MODELS.keys() if m != "default"]


def get_model_client_name(alias: str) -> Optional[str]:
    """Get the BAML client name for a model alias.

    Args:
        alias: Model alias (e.g., "gpt-5-mini", "gemini-2.5-flash")

    Returns:
        BAML client name, or None if alias not found.
    """
    return MODELS.get(alias)


def get_active_model(base: Path = Path(".")) -> str:
    """Get the currently active model.

    Priority:
    1. Session override (active_model file)
    2. Config default_model
    3. Hardcoded DEFAULT_MODEL

    Args:
        base: Base path for Brief project

    Returns:
        Model alias string
    """
    brief_path = get_brief_path(base)

    # Check session override first
    active_file = brief_path / ACTIVE_MODEL_FILE
    if active_file.exists():
        model = active_file.read_text().strip()
        if model and model in MODELS:
            return model

    # Check config default
    from .models import BriefConfig
    from .storage import read_json
    config_path = brief_path / "config.json"
    if config_path.exists():
        config = read_json(config_path)
        if config and "default_model" in config:
            model = config["default_model"]
            if model in MODELS:
                return model

    return DEFAULT_MODEL


def set_active_model(model: str, base: Path = Path(".")) -> bool:
    """Set the active model for this session.

    This creates/updates a session file, not the config.
    Use `brief config set default_model` to change the persistent default.

    Args:
        model: Model alias to set
        base: Base path for Brief project

    Returns:
        True if successful, False if model not found
    """
    if model not in MODELS:
        return False

    brief_path = get_brief_path(base)
    active_file = brief_path / ACTIVE_MODEL_FILE
    active_file.write_text(model)
    return True


def clear_active_model(base: Path = Path(".")) -> bool:
    """Clear the session model override, reverting to config default.

    Args:
        base: Base path for Brief project

    Returns:
        True if file was removed, False if it didn't exist
    """
    brief_path = get_brief_path(base)
    active_file = brief_path / ACTIVE_MODEL_FILE
    if active_file.exists():
        active_file.unlink()
        return True
    return False


def get_model_info(alias: str) -> dict:
    """Get information about a model.

    Args:
        alias: Model alias

    Returns:
        Dict with provider and client name, or empty dict if not found
    """
    client_name = MODELS.get(alias)
    if not client_name:
        return {}

    # Determine provider from alias
    if alias.startswith("gpt"):
        provider = "openai"
    elif alias.startswith("claude"):
        provider = "anthropic"
    elif alias.startswith("gemini"):
        provider = "google"
    else:
        provider = "unknown"

    return {
        "alias": alias,
        "client": client_name,
        "provider": provider,
    }
