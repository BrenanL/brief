"""Analyze command for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path
from ..analysis.manifest import ManifestBuilder, get_changed_files
from ..analysis.relationships import RelationshipExtractor
from ..models import ImportRelationship, CallRelationship
from ..storage import read_json

app = typer.Typer()


@app.command("file")
def analyze_file(
    file_path: Path = typer.Argument(..., help="Python file to analyze"),
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="Base path for module resolution"),
) -> None:
    """Analyze a single Python file."""
    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    base_path = base or Path.cwd()
    brief_path = get_brief_path(base_path)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    builder = ManifestBuilder(base_path)
    records = builder.analyze_file(file_path)

    typer.echo(f"Analyzed {file_path}")
    typer.echo(f"  Found: {len([r for r in records if r.type == 'class'])} classes, "
               f"{len([r for r in records if r.type == 'function'])} functions")


@app.command("dir")
def analyze_directory(
    directory: Path = typer.Argument(Path("."), help="Directory to analyze"),
    all_files: bool = typer.Option(False, "--all", "-a", help="Analyze all files (ignore previous analysis)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path where .brief is located"),
) -> None:
    """Analyze Python files in a directory."""
    if not directory.exists():
        typer.echo(f"Error: Directory not found: {directory}", err=True)
        raise typer.Exit(1)

    # brief_path is where .brief directory lives (project root)
    brief_path = get_brief_path(base)

    # target_path is what we're analyzing (can be a subdirectory)
    target_path = directory if directory.is_absolute() else Path.cwd() / directory

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    # Load config for exclude patterns
    config = read_json(brief_path / "config.json")
    exclude_patterns = config.get("exclude_patterns", [])

    # Build manifest
    typer.echo(f"Analyzing {directory}...")
    builder = ManifestBuilder(target_path, exclude_patterns)
    builder.analyze_directory()
    builder.save_manifest(brief_path)

    # Extract relationships
    typer.echo("Extracting relationships...")
    extractor = RelationshipExtractor(target_path, exclude_patterns)
    extractor.extract_all()
    extractor.save_relationships(brief_path)

    stats = builder.get_stats()
    import_count = sum(1 for r in extractor.relationships if isinstance(r, ImportRelationship))
    call_count = sum(1 for r in extractor.relationships if isinstance(r, CallRelationship))

    typer.echo(f"\nAnalysis complete:")
    typer.echo(f"  Files: {stats['files']}")
    typer.echo(f"  Classes: {stats['classes']}")
    typer.echo(f"  Functions: {stats['module_functions']} module-level, {stats['methods']} methods")
    typer.echo(f"  Relationships: {import_count} imports, {call_count} calls")


@app.command("all")
def analyze_all(
    base: Path = typer.Argument(Path("."), help="Base path to analyze"),
) -> None:
    """Analyze entire repository."""
    analyze_directory(directory=base, all_files=True, base=base)


@app.command("refresh")
def refresh(
    base: Path = typer.Argument(Path("."), help="Base path"),
) -> None:
    """Re-analyze only changed files."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    config = read_json(brief_path / "config.json")
    exclude_patterns = config.get("exclude_patterns", [])

    new_files, changed_files, deleted_files = get_changed_files(
        base, brief_path, exclude_patterns
    )

    if not new_files and not changed_files and not deleted_files:
        typer.echo("No changes detected.")
        return

    typer.echo(f"Changes detected:")
    typer.echo(f"  New: {len(new_files)}")
    typer.echo(f"  Changed: {len(changed_files)}")
    typer.echo(f"  Deleted: {len(deleted_files)}")

    # For now, do a full re-analyze
    typer.echo("\nRe-analyzing...")
    analyze_directory(directory=base, all_files=True, base=base)
