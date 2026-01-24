"""Development logging for Brief commands."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Log file location (outside .brief/ so it survives resets)
BRIEF_LOGS_DIR = ".brief-logs"
COMMAND_LOG_FILE = "commands.log"
MAX_LOG_SIZE_MB = 10


def get_logs_path(base_path: Optional[Path] = None) -> Path:
    """Get the .brief-logs directory path.

    Args:
        base_path: Base path for logs. Defaults to cwd.

    Returns:
        Path to .brief-logs directory.
    """
    if base_path is None:
        base_path = Path.cwd()
    return base_path / BRIEF_LOGS_DIR


def is_logging_enabled(base_path: Optional[Path] = None) -> bool:
    """Check if command logging is enabled via config.

    Args:
        base_path: Base path. Defaults to cwd.

    Returns:
        True if logging is enabled, False otherwise.
    """
    from .storage import read_json
    from .config import get_brief_path

    if base_path is None:
        base_path = Path.cwd()

    brief_path = get_brief_path(base_path)
    config_file = brief_path / "config.json"

    if not config_file.exists():
        # Default to enabled during development
        return True

    try:
        config = read_json(config_file)
        return config.get("command_logging", True)
    except Exception:
        return True


def log_command(command: str, args: list[str], base_path: Optional[Path] = None) -> None:
    """Log a command invocation.

    Args:
        command: The command name (e.g., "context get").
        args: Command arguments.
        base_path: Base path. Defaults to cwd.
    """
    if not is_logging_enabled(base_path):
        return

    logs_path = get_logs_path(base_path)
    log_file = logs_path / COMMAND_LOG_FILE

    # Create directory on first write
    logs_path.mkdir(parents=True, exist_ok=True)

    # Check log rotation (simple size-based)
    if log_file.exists():
        size_mb = log_file.stat().st_size / (1024 * 1024)
        if size_mb > MAX_LOG_SIZE_MB:
            # Rotate: keep .1 backup
            backup = logs_path / f"{COMMAND_LOG_FILE}.1"
            if backup.exists():
                backup.unlink()
            log_file.rename(backup)

    # Format log entry
    timestamp = datetime.now().isoformat()
    args_str = " ".join(f'"{a}"' if " " in a else a for a in args)
    entry = f"{timestamp} | {command} | {args_str}\n"

    # Append to log
    with log_file.open("a") as f:
        f.write(entry)


def log_from_cli() -> None:
    """Log the current CLI invocation.

    Call this from the CLI callback to capture all brief commands.
    """
    if len(sys.argv) < 2:
        return

    # Extract command and args from sys.argv
    # sys.argv[0] is "brief", rest are command and args
    args = sys.argv[1:]

    # Find the command name (first non-option arg)
    command_parts = []
    remaining_args = []
    in_command = True

    for arg in args:
        if in_command:
            if arg.startswith("-"):
                # Options after command name belong to args
                in_command = False
                remaining_args.append(arg)
            else:
                command_parts.append(arg)
                # Some commands are two words (e.g., "context get")
                if len(command_parts) == 2:
                    in_command = False
        else:
            remaining_args.append(arg)

    command = " ".join(command_parts) if command_parts else "unknown"
    log_command(command, remaining_args)
