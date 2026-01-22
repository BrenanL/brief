"""Initialize Brief in a repository."""

import typer
from pathlib import Path
from ..config import (
    get_brief_path,
    MANIFEST_FILE,
    RELATIONSHIPS_FILE,
    TASKS_FILE,
    MEMORY_FILE,
    CONTEXT_DIR,
)
from ..storage import write_json, write_jsonl
from ..models import BriefConfig


def init(
    path: Path = typer.Argument(
        Path("."),
        help="Path to initialize Brief in"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .brief directory"
    ),
) -> None:
    """Initialize Brief context system in a repository."""
    brief_path = get_brief_path(path)

    if brief_path.exists() and not force:
        typer.echo(f"Brief already initialized at {brief_path}")
        typer.echo("Use --force to reinitialize")
        raise typer.Exit(1)

    # Create directory structure
    brief_path.mkdir(parents=True, exist_ok=True)
    (brief_path / CONTEXT_DIR).mkdir(exist_ok=True)
    (brief_path / CONTEXT_DIR / "modules").mkdir(exist_ok=True)
    (brief_path / CONTEXT_DIR / "files").mkdir(exist_ok=True)
    (brief_path / CONTEXT_DIR / "paths").mkdir(exist_ok=True)

    # Create empty JSONL files
    write_jsonl(brief_path / MANIFEST_FILE, [])
    write_jsonl(brief_path / RELATIONSHIPS_FILE, [])
    write_jsonl(brief_path / TASKS_FILE, [])
    write_jsonl(brief_path / MEMORY_FILE, [])

    # Create config
    config = BriefConfig()
    write_json(brief_path / "config.json", config.model_dump())

    typer.echo(f"Initialized Brief at {brief_path}")
    typer.echo("Created:")
    typer.echo(f"  {MANIFEST_FILE} - Code structure inventory")
    typer.echo(f"  {RELATIONSHIPS_FILE} - Dependency graph")
    typer.echo(f"  {TASKS_FILE} - Task tracking")
    typer.echo(f"  {MEMORY_FILE} - Pattern memory")
    typer.echo(f"  {CONTEXT_DIR}/ - Context descriptions")
    typer.echo(f"  config.json - Configuration")
