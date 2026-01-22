"""LLM client wrapper for Brief using BAML."""

from typing import Optional
from .config import load_env

# Load environment before any BAML imports
load_env()

# Available model aliases
MODELS = {
    "gpt-5-mini": "GPT5Mini",
    "gpt-4o": "GPT4o",
    "claude-sonnet": "ClaudeSonnet",
    "claude-haiku": "ClaudeHaiku",
    "gemini-flash": "GeminiFlash",
    "default": "Default",
}

DEFAULT_MODEL = "gpt-5-mini"


def get_available_models() -> list[str]:
    """Return list of available model aliases."""
    return list(MODELS.keys())


def get_model_client_name(alias: str) -> Optional[str]:
    """Get the BAML client name for a model alias.

    Args:
        alias: Model alias (e.g., "gpt-5-mini", "claude-sonnet")

    Returns:
        BAML client name, or None if alias not found.
    """
    return MODELS.get(alias)


# Note: Actual BAML client usage will be added in Phase 3
# when we define the LLM functions for description generation.
#
# Example usage (after Phase 3):
#
#     from ..baml_client.sync_client import b
#     from ..baml_client.types import FunctionDescription
#
#     result = b.DescribeFunction(
#         function_name="my_func",
#         function_code="def my_func(): pass",
#         file_context="test.py",
#         docstring=None
#     )
