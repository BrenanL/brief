"""Reset Brief cache and analysis data."""

import typer
from pathlib import Path
from ..config import (
    get_brief_path,
    MANIFEST_FILE,
    RELATIONSHIPS_FILE,
    EMBEDDINGS_DB,
    CONTEXT_DIR,
)
from ..storage import write_jsonl

app = typer.Typer(help="Reset Brief cache data")


def reset(
    base: Path = typer.Option(
        Path("."),
        "--base", "-b",
        help="Base path for Brief project"
    ),
    include_embeddings: bool = typer.Option(
        False,
        "--include-embeddings",
        help="Also clear embeddings database (takes time to regenerate)"
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Clear everything including LLM-generated content (costs money to regenerate)"
    ),
    include_user_data: bool = typer.Option(
        False,
        "--include-user-data",
        help="Also clear tasks, memory, and config (destructive!)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be cleared without actually clearing"
    ),
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompts"
    ),
) -> None:
    """Clear Brief analysis cache while preserving expensive LLM content.

    By default, clears:
      - manifest.jsonl (code structure cache)
      - relationships.jsonl (dependency graph cache)

    Preserves by default:
      - context/files/ (LLM-generated descriptions - costs $ to regenerate)
      - context/modules/ (LLM-generated module summaries)
      - context/paths/ (saved execution paths)
      - context/traces.jsonl (trace definitions)
      - tasks.jsonl, memory.jsonl, config.json (user data)
      - embeddings.db (takes time to regenerate)

    Use --include-embeddings to also clear the embeddings database.
    Use --full to clear everything except user data (tasks, memory, config).
    Use --include-user-data to also clear tasks, memory, and config.
    Use --dry-run to preview what would be cleared.

    Examples:
        brief reset                  # Clear analysis cache only
        brief reset --dry-run        # Preview what would be cleared
        brief reset --include-embeddings  # Also clear embeddings
        brief reset --full           # Clear all including LLM content
        brief reset --include-user-data   # Also clear tasks/memory/config
        brief reset --full -y        # Full reset without confirmation
    """
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    from ..config import TASKS_FILE, MEMORY_FILE, ACTIVE_TASK_FILE

    # Define what to clear
    analysis_files = [
        (brief_path / MANIFEST_FILE, "manifest.jsonl (code structure)"),
        (brief_path / RELATIONSHIPS_FILE, "relationships.jsonl (dependencies)"),
    ]

    embeddings_file = brief_path / EMBEDDINGS_DB

    # LLM-generated content directories
    context_path = brief_path / CONTEXT_DIR
    llm_content = [
        (context_path / "files", "context/files/ (file descriptions)"),
        (context_path / "modules", "context/modules/ (module summaries)"),
    ]

    # User data files
    user_data_files = [
        (brief_path / TASKS_FILE, "tasks.jsonl (task data)"),
        (brief_path / MEMORY_FILE, "memory.jsonl (remembered patterns)"),
        (brief_path / ACTIVE_TASK_FILE, "active_task"),
        (brief_path / "config.json", "config.json (settings)"),
    ]

    # Build list of items to clear
    to_clear = list(analysis_files)

    if include_embeddings or full:
        if embeddings_file.exists():
            to_clear.append((embeddings_file, "embeddings.db"))

    if full:
        to_clear.extend(llm_content)

    if include_user_data:
        to_clear.extend(user_data_files)

    # Show what will be cleared
    action_word = "Would clear" if dry_run else "Will clear"
    typer.echo(f"{action_word}:")
    for path, desc in to_clear:
        if path.exists():
            if path.is_dir():
                # Count files in directory
                file_count = len(list(path.glob("*")))
                typer.echo(f"  - {desc} ({file_count} files)")
            else:
                typer.echo(f"  - {desc}")
        else:
            typer.echo(f"  - {desc} (not present)")

    # Show what will be preserved
    typer.echo("")
    preserve_word = "Would preserve" if dry_run else "Will preserve"
    typer.echo(f"{preserve_word}:")
    preserved = []
    if not include_user_data:
        preserved.extend(["tasks.jsonl", "memory.jsonl", "config.json", "active_task"])
    if not (include_embeddings or full):
        preserved.append("embeddings.db")
    if not full:
        preserved.extend(["context/files/", "context/modules/", "context/paths/", "context/traces.jsonl"])
    for item in preserved:
        typer.echo(f"  - {item}")

    # Exit if dry run
    if dry_run:
        typer.echo("")
        typer.echo("(Dry run - no changes made)")
        return

    # Confirm if destructive operation
    needs_confirm = (full or include_user_data) and not yes
    if needs_confirm:
        typer.echo("")
        if include_user_data:
            typer.echo("WARNING: --include-user-data will delete your tasks, memory, and config!")
        if full:
            typer.echo("WARNING: --full will delete LLM-generated content that costs money to regenerate.")
        confirm = typer.confirm("Are you sure you want to proceed?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    # Perform the reset
    typer.echo("")
    cleared_count = 0

    for path, desc in to_clear:
        if path.exists():
            if path.is_dir():
                # Clear directory contents but keep the directory
                for file in path.glob("*"):
                    if file.is_file():
                        file.unlink()
                        cleared_count += 1
                typer.echo(f"  Cleared {desc}")
            else:
                if path.suffix == ".jsonl":
                    # Reset JSONL files to empty array
                    write_jsonl(path, [])
                    typer.echo(f"  Reset {desc}")
                else:
                    # Delete other files
                    path.unlink()
                    typer.echo(f"  Deleted {desc}")
                cleared_count += 1

    typer.echo("")
    typer.echo(f"Reset complete. Run 'brief analyze full' to rebuild analysis cache.")
