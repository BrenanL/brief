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
from ..storage import write_json, write_jsonl, read_json


def _ensure_gitignore(base_path: Path) -> bool:
    """Add .brief/ and .brief-logs/ to .gitignore if not already present.

    Returns True if the file was modified.
    """
    gitignore = base_path / ".gitignore"
    entries_needed = [".brief/", ".brief-logs/"]

    existing_lines = []
    if gitignore.exists():
        existing_lines = gitignore.read_text().splitlines()

    # Check which entries are missing
    missing = [e for e in entries_needed if e not in existing_lines]
    if not missing:
        return False

    # Append missing entries
    with open(gitignore, "a") as f:
        # Add a newline separator if file doesn't end with one
        if existing_lines and existing_lines[-1].strip():
            f.write("\n")
        if not existing_lines:
            f.write("# Brief context data (local, not committed)\n")
        for entry in missing:
            f.write(f"{entry}\n")

    return True


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
    """Initialize Brief and analyze codebase.

    Creates .brief/ directory, analyzes all Python files, and
    adds .brief/ to .gitignore.

    Example:
        brief init              # Initialize and analyze
        brief init --force      # Reinitialize from scratch
    """
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
    from ..models import BriefConfig
    config = BriefConfig()
    write_json(brief_path / "config.json", config.model_dump())

    typer.echo(f"Initialized Brief at {brief_path}")

    # Add to .gitignore
    if _ensure_gitignore(path):
        typer.echo("  Added .brief/ and .brief-logs/ to .gitignore")

    # Run analysis
    typer.echo("Analyzing codebase...")

    from ..analysis.manifest import ManifestBuilder
    from ..analysis.relationships import RelationshipExtractor
    from ..config import load_exclude_patterns

    current_config = read_json(brief_path / "config.json")
    exclude_patterns = load_exclude_patterns(path, current_config)

    builder = ManifestBuilder(path, exclude_patterns)
    builder.analyze_directory()
    builder.save_manifest(brief_path)

    extractor = RelationshipExtractor(path, exclude_patterns)
    extractor.extract_all()
    extractor.save_relationships(brief_path)

    stats = builder.get_stats()
    typer.echo(f"  Analyzed {stats['python_files']} Python files")
    typer.echo(f"  Found {stats['classes']} classes, {stats['module_functions'] + stats['methods']} functions")
    typer.echo()
    typer.echo("Next: run 'brief setup -d' for full configuration, or 'brief context get \"query\"' to start.")
