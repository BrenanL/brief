"""Description generation commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path, MANIFEST_FILE, CONTEXT_DIR, RELATIONSHIPS_FILE
from ..storage import read_jsonl, write_jsonl
from ..models import ManifestFileRecord, ManifestClassRecord, ManifestFunctionRecord

app = typer.Typer()


def update_manifest_context_ref(brief_path: Path, file_path: str, context_ref: str) -> None:
    """Update manifest with context reference."""
    records = list(read_jsonl(brief_path / MANIFEST_FILE))

    for record in records:
        if record["type"] == "file" and record["path"] == file_path:
            record["context_ref"] = context_ref
            break

    write_jsonl(brief_path / MANIFEST_FILE, records)


@app.command("file")
def describe_file_cmd(
    file_path: str = typer.Argument(..., help="File to describe"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path where .brief is"),
    source: Optional[Path] = typer.Option(None, "--source", "-s", help="Source directory where files are located"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing description"),
) -> None:
    """Generate description for a file.

    If files were analyzed with 'brief analyze dir <subdir>', use --source to
    specify that directory so the file can be found.

    Example:
        brief analyze dir src/
        brief describe file utils.py --source src/
    """
    from ..generation.generator import describe_file, format_file_description, is_baml_available

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

        # Update manifest with context_ref
        update_manifest_context_ref(brief_path, file_path, str(context_file.relative_to(brief_path)))

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
) -> None:
    """Generate description for a module (directory)."""
    from ..generation.generator import describe_module, format_module_description, is_baml_available
    from ..reporting.overview import get_module_structure

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


@app.command("batch")
def describe_batch(
    path_filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter files by path pattern"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max files to describe"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--include-existing", help="Skip already described files"),
) -> None:
    """Generate descriptions for multiple files."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    # Collect files to describe
    files_to_describe: list[str] = []
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] != "file":
            continue

        if path_filter and path_filter not in record["path"]:
            continue

        if skip_existing and record.get("context_ref"):
            continue

        files_to_describe.append(record["path"])

        if len(files_to_describe) >= limit:
            break

    if not files_to_describe:
        typer.echo("No files to describe.")
        return

    typer.echo(f"Describing {len(files_to_describe)} files...")

    for i, fp in enumerate(files_to_describe):
        typer.echo(f"[{i+1}/{len(files_to_describe)}] {fp}")
        try:
            describe_file_cmd(fp, base, model=None, force=True)
        except Exception as e:
            typer.echo(f"  Error: {e}")

    typer.echo("Done.")


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
