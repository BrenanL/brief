"""Description generation commands for Brief."""
import os
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path, MANIFEST_FILE, CONTEXT_DIR, RELATIONSHIPS_FILE
from ..storage import read_jsonl, write_jsonl
from ..models import ManifestFileRecord, ManifestClassRecord, ManifestFunctionRecord

app = typer.Typer()


def set_baml_log_level(verbose: bool) -> None:
    """Set BAML log level based on verbose flag.

    When not verbose, suppress BAML's detailed output.
    """
    if not verbose:
        os.environ["BAML_LOG"] = "error"
    else:
        # Remove the env var to allow full logging
        os.environ.pop("BAML_LOG", None)


def update_manifest_context_ref(
    brief_path: Path,
    file_path: str,
    context_ref: str,
    description_hash: str | None = None
) -> None:
    """Update manifest with context reference and description hash.

    Args:
        brief_path: Path to .brief directory
        file_path: Relative path to the file
        context_ref: Path to the description file
        description_hash: Hash of the file at time of description generation
    """
    from datetime import datetime

    records = list(read_jsonl(brief_path / MANIFEST_FILE))

    for record in records:
        if record["type"] == "file" and record["path"] == file_path:
            record["context_ref"] = context_ref
            record["described_at"] = datetime.now().isoformat()
            if description_hash:
                record["description_hash"] = description_hash
            break

    write_jsonl(brief_path / MANIFEST_FILE, records)


@app.command("file")
def describe_file_cmd(
    file_path: str = typer.Argument(..., help="File to describe"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path where .brief is"),
    source: Optional[Path] = typer.Option(None, "--source", "-s", help="Source directory where files are located"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing description"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed BAML output"),
) -> None:
    """Generate description for a file.

    If files were analyzed with 'brief analyze dir <subdir>', use --source to
    specify that directory so the file can be found.

    Example:
        brief analyze dir src/
        brief describe file utils.py --source src/
    """
    from ..generation.generator import describe_file, format_file_description, is_baml_available

    set_baml_log_level(verbose)

    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    # Source path is where the actual source files are
    source_path = source if source else base

    # Find file record in manifest
    file_record = None
    class_names: list[str] = []
    function_names: list[str] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file" and record["path"] == file_path:
            file_record = ManifestFileRecord.model_validate(record)
        elif record.get("file") == file_path:
            if record["type"] == "class":
                class_names.append(record["name"])
            elif record["type"] == "function" and not record.get("class_name"):
                function_names.append(record["name"])

    if not file_record:
        typer.echo(f"Error: File '{file_path}' not found in manifest. Run 'brief analyze' first.", err=True)
        raise typer.Exit(1)

    # Check for existing description
    context_file = brief_path / CONTEXT_DIR / "files" / (file_path.replace("/", "__").replace("\\", "__") + ".md")
    if context_file.exists() and not force:
        typer.echo(f"Description already exists at {context_file}")
        typer.echo("Use --force to overwrite.")
        return

    if not is_baml_available():
        typer.echo("Note: BAML client not available. Using placeholder descriptions.")
        typer.echo("Run 'baml-cli generate' in brief to enable LLM descriptions.")

    typer.echo(f"Generating description for {file_path}...")

    # Get imports from relationships
    imports: list[str] = []
    for rel in read_jsonl(brief_path / RELATIONSHIPS_FILE):
        if rel.get("type") == "imports" and rel["from_file"] == file_path:
            imports.extend(rel.get("imports", []))

    try:
        desc = describe_file(file_record, source_path, class_names, function_names, imports)
        markdown = format_file_description(desc)

        # Write to context file
        context_file.parent.mkdir(parents=True, exist_ok=True)
        header = f"# {file_path}\n\n"
        context_file.write_text(header + markdown)

        # Compute file hash for freshness tracking
        from ..analysis.parser import compute_file_hash
        actual_file_path = source_path / file_path
        current_hash = compute_file_hash(actual_file_path) if actual_file_path.exists() else None

        # Update manifest with context_ref and description hash
        update_manifest_context_ref(
            brief_path, file_path,
            str(context_file.relative_to(brief_path)),
            description_hash=current_hash
        )

        typer.echo(f"Description saved to {context_file}")
        typer.echo("")
        typer.echo(markdown)

    except Exception as e:
        typer.echo(f"Error generating description: {e}", err=True)
        raise typer.Exit(1)


@app.command("module")
def describe_module_cmd(
    module_name: str = typer.Argument(..., help="Module to describe"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed BAML output"),
) -> None:
    """Generate description for a module (directory)."""
    from ..generation.generator import describe_module, format_module_description, is_baml_available
    from ..reporting.overview import get_module_structure

    set_baml_log_level(verbose)

    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    modules = get_module_structure(brief_path)
    if module_name not in modules:
        typer.echo(f"Error: Module '{module_name}' not found.", err=True)
        raise typer.Exit(1)

    data = modules[module_name]

    # Build file summaries
    file_summaries: list[str] = []
    for f in data["files"]:
        summary = f["path"]
        # Check for existing description
        context_ref = f.get("context_ref")
        if context_ref:
            context_file = brief_path / context_ref
            if context_file.exists():
                # Extract first line of purpose
                content = context_file.read_text()
                for line in content.split("\n"):
                    if line.startswith("**Purpose**:"):
                        summary += f" - {line.replace('**Purpose**:', '').strip()}"
                        break
        file_summaries.append(summary)

    if not is_baml_available():
        typer.echo("Note: BAML client not available. Using placeholder descriptions.")

    typer.echo(f"Generating description for module {module_name}...")

    try:
        desc = describe_module(
            module_name,
            file_summaries,
            len(data["classes"]),
            len(data["functions"])
        )
        markdown = format_module_description(desc)

        # Write to context file
        context_file = brief_path / CONTEXT_DIR / "modules" / f"{module_name.replace('.', '_')}.md"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        header = f"# Module: {module_name}\n\n"
        context_file.write_text(header + markdown)

        typer.echo(f"Description saved to {context_file}")
        typer.echo("")
        typer.echo(markdown)

    except Exception as e:
        typer.echo(f"Error generating description: {e}", err=True)
        raise typer.Exit(1)


def _file_priority(file_path: str) -> tuple[int, str]:
    """Get priority for a file path (lower = higher priority).

    Prioritizes source directories over test directories.

    Args:
        file_path: The file path to get priority for

    Returns:
        Tuple of (priority_level, file_path) for sorting
    """
    # Priority levels (lower = higher priority)
    # 0: Main source directories
    # 1: Other source-like directories
    # 2: Root-level files
    # 3: Test directories
    # 4: Everything else

    path_lower = file_path.lower()

    # High priority: main source directories
    if path_lower.startswith(("src/", "lib/", "app/", "core/")):
        return (0, file_path)

    # Medium-high priority: common source patterns
    if any(path_lower.startswith(p) for p in ("api/", "services/", "models/", "utils/", "common/")):
        return (1, file_path)

    # Medium priority: root-level Python files (often important)
    if "/" not in file_path and file_path.endswith(".py"):
        return (2, file_path)

    # Low priority: test directories
    if path_lower.startswith(("tests/", "test/", "testing/")) or "/tests/" in path_lower:
        return (3, file_path)

    # Default priority
    return (4, file_path)


@app.command("batch")
def describe_batch(
    path_filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter files by path pattern"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max files to describe"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--include-existing", help="Skip already described files"),
    include_other: bool = typer.Option(False, "--include-other", "-a", help="Include non-Python files (scripts, configs, etc.)"),
    embed: bool = typer.Option(False, "--embed", "-e", help="Generate embeddings after descriptions (enables semantic search)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed BAML output"),
) -> None:
    """Generate descriptions for multiple files.

    By default, only describes Python files. Use --include-other to also
    describe scripts, configs, and other tracked files.

    Files are processed in priority order: source directories (src/, lib/, app/)
    are processed before test directories.

    Use --embed to automatically generate embeddings for semantic search
    after descriptions are generated (requires OPENAI_API_KEY).

    Example:
        brief describe batch                    # Describe up to 10 files
        brief describe batch --limit 50         # Describe up to 50 files
        brief describe batch --embed            # Describe and embed
    """
    set_baml_log_level(verbose)

    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    # Collect files to describe
    candidate_files: list[str] = []
    context_files_dir = brief_path / CONTEXT_DIR / "files"

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] != "file":
            continue

        # Filter by file type
        is_python = record.get("extension") == ".py" or record.get("parsed", True)
        if not is_python and not include_other:
            continue

        if path_filter and path_filter not in record["path"]:
            continue

        # Check if description already exists (either in manifest or as actual file)
        if skip_existing:
            if record.get("context_ref"):
                continue
            # Also check if description file exists on disk
            desc_filename = record["path"].replace("/", "__").replace("\\", "__") + ".md"
            if (context_files_dir / desc_filename).exists():
                continue

        candidate_files.append(record["path"])

    # Sort by priority (source files first, test files last)
    candidate_files.sort(key=_file_priority)

    # Apply limit after sorting
    files_to_describe = candidate_files[:limit]

    if not files_to_describe:
        typer.echo("No files to describe.")
        return

    typer.echo(f"Describing {len(files_to_describe)} files...")

    for i, fp in enumerate(files_to_describe):
        typer.echo(f"[{i+1}/{len(files_to_describe)}] {fp}")
        try:
            describe_file_cmd(fp, base=base, source=None, model=None, force=True, verbose=verbose)
        except Exception as e:
            typer.echo(f"  Error: {e}")

    typer.echo("Done.")

    # Generate embeddings if requested
    if embed:
        from ..retrieval.embeddings import is_embedding_api_available, embed_all_descriptions

        typer.echo("")
        if not is_embedding_api_available():
            typer.echo("Skipping embeddings: OPENAI_API_KEY not set in .env")
            typer.echo("To enable semantic search later, set the key and run:")
            typer.echo("  brief context embed")
        else:
            typer.echo("Generating embeddings...")
            count = embed_all_descriptions(brief_path)
            typer.echo(f"Embedded {count} descriptions. Semantic search is now available.")


@app.command("spec")
def spec_cmd(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Generate full specification from all descriptions."""
    from ..generation.synthesis import synthesize_spec, get_spec_stats

    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    spec = synthesize_spec(brief_path, base)

    if output:
        output.write_text(spec)
        typer.echo(f"Specification written to {output}")
    else:
        spec_file = brief_path / "spec.md"
        spec_file.write_text(spec)
        typer.echo(f"Specification written to {spec_file}")

    # Show summary
    stats = get_spec_stats(brief_path)
    lines = spec.count("\n")
    typer.echo(f"Generated {lines} lines of documentation.")
    typer.echo(f"  Module descriptions: {stats['module_descriptions']}")
    typer.echo(f"  File descriptions: {stats['file_descriptions']}")
