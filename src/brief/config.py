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

# Default exclusion patterns (applies to all file discovery)
DEFAULT_EXCLUDE_PATTERNS = [
    ".*",              # All dot-prefixed folders (.git, .venv, .claude, etc.)
    "__pycache__",
    "node_modules",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    "dist",
    "build",
]

# Default patterns for documentation files to include
DEFAULT_DOC_INCLUDE = [
    "README.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE.md",
    "docs/*.md",           # Top-level docs only
    "src/**/*.md",         # Inline docs in source
    "lib/**/*.md",
    "app/**/*.md",
]

# Default patterns for documentation files to exclude
DEFAULT_DOC_EXCLUDE = [
    "**/archive/**",
    "**/old/**",
    "**/deprecated/**",
    "**/status/**",
    "**/scratch/**",
    "**/draft/**",
    "**/wip/**",
    "**/*-session-*",
    "**/*-log-*",
    # Dated files - various formats typically used for logs/status reports
    # YYYY-MM-DD (ISO format)
    "*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*",
    # YYYY_MM_DD (underscore variant)
    "*[0-9][0-9][0-9][0-9]_[0-9][0-9]_[0-9][0-9]*",
    # YYYY.MM.DD (dot variant)
    "*[0-9][0-9][0-9][0-9].[0-9][0-9].[0-9][0-9]*",
    # YYYYMMDD (compact)
    "*[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]*",
]

# File extensions we fully parse (extract structure)
PARSED_EXTENSIONS = {
    ".py": "python",    # Full AST parsing
    ".md": "markdown",  # Heading extraction
}

# File extensions we track but don't parse (just record existence)
TRACKED_EXTENSIONS = {
    # Code files
    ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".rb", ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp",
    ".cs", ".php", ".swift",
    # Web files
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    # Config files
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".xml", ".env.example",
    # Scripts
    ".sh", ".bash", ".zsh", ".fish",
    ".ps1", ".bat", ".cmd",
    # Data/docs
    ".txt", ".rst", ".csv",
    # Other
    ".sql", ".graphql", ".proto",
}


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


def load_exclude_patterns(base_path: Path, config: dict) -> list[str]:
    """Load all effective exclude patterns from config and gitignore.

    Args:
        base_path: Project root directory
        config: Loaded config dict from config.json

    Returns:
        Combined list of exclude patterns
    """
    patterns = list(config.get("exclude_patterns", DEFAULT_EXCLUDE_PATTERNS))

    # Add gitignore patterns if enabled
    if config.get("use_gitignore", False):
        gitignore = base_path / ".gitignore"
        if gitignore.exists():
            for line in gitignore.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("!"):
                    # Strip trailing slash (gitignore convention for directories)
                    pattern = line.rstrip("/")
                    if pattern and pattern not in patterns:
                        patterns.append(pattern)

    return patterns


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
