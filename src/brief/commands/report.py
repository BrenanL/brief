"""Reporting commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path, MANIFEST_FILE
from ..reporting.overview import generate_project_overview, generate_module_overview
from ..reporting.tree import generate_tree
from ..reporting.deps import get_dependencies, format_dependencies, generate_dependency_graph
from ..reporting.coverage import calculate_coverage, format_coverage, find_stale_files, format_stale
from ..storage import read_json, read_jsonl

app = typer.Typer()


@app.command()
def overview(
    module: Optional[str] = typer.Argument(None, help="Module name for detailed overview"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show project or module overview."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    if module:
        output = generate_module_overview(brief_path, module)
    else:
        output = generate_project_overview(brief_path)

    typer.echo(output)


@app.command()
def tree(
    path: Optional[str] = typer.Argument(None, help="Path to show tree for"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    no_status: bool = typer.Option(False, "--no-status", help="Hide analysis status"),
) -> None:
    """Show project structure as tree."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    output = generate_tree(brief_path, base, path, show_status=not no_status)
    typer.echo(output)


@app.command()
def deps(
    file_path: Optional[str] = typer.Argument(None, help="File to show dependencies for"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Show only reverse dependencies"),
) -> None:
    """Show dependencies for a file or project summary."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    if file_path:
        deps_data = get_dependencies(brief_path, file_path)
        output = format_dependencies(file_path, deps_data, reverse)
    else:
        output = generate_dependency_graph(brief_path)

    typer.echo(output)


@app.command("coverage")
def coverage_cmd(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show analysis coverage statistics."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    config = read_json(brief_path / "config.json")
    exclude_patterns = config.get("exclude_patterns", [])

    cov = calculate_coverage(brief_path, base, exclude_patterns)
    typer.echo(format_coverage(cov))


@app.command()
def stale(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show files that changed since last analysis."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    stale_files = find_stale_files(brief_path, base)
    typer.echo(format_stale(stale_files))


@app.command()
def inventory(
    filter_path: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by path pattern"),
    record_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type (file/class/function)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max records to show"),
) -> None:
    """List all items in the manifest."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    records = []
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        # Apply filters
        if record_type and record.get("type") != record_type:
            continue

        if filter_path:
            path = record.get("path") or record.get("file", "")
            if filter_path not in path:
                continue

        records.append(record)

        if len(records) >= limit:
            break

    if not records:
        typer.echo("No matching records found.")
        return

    typer.echo(f"Inventory ({len(records)} records):")
    typer.echo("-" * 60)

    for record in records:
        rtype = record.get("type", "?")
        if rtype == "file":
            typer.echo(f"[FILE] {record['path']}")
        elif rtype == "class":
            typer.echo(f"[CLASS] {record['name']} in {record['file']}:{record['line']}")
        elif rtype == "function":
            prefix = f"{record['class_name']}." if record.get('class_name') else ""
            typer.echo(f"[FUNC] {prefix}{record['name']} in {record['file']}:{record['line']}")

    if len(records) == limit:
        typer.echo(f"\n(showing first {limit} records, use --limit to see more)")
