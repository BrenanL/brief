"""Reporting commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path, MANIFEST_FILE, load_exclude_patterns
from ..reporting.overview import generate_project_overview, generate_project_overview_rich, generate_module_overview
from ..reporting.tree import generate_tree
from ..reporting.deps import get_dependencies, format_dependencies, generate_dependency_graph
from ..reporting.coverage import calculate_coverage, format_coverage, find_stale_files, format_stale, format_coverage_detailed
from ..storage import read_json, read_jsonl

app = typer.Typer()


@app.command()
def overview(
    module: Optional[str] = typer.Argument(None, help="Module name for detailed overview"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    plain: bool = typer.Option(False, "--plain", "-p", help="Plain text output (no colors)"),
) -> None:
    """Show project architecture overview.

    Displays packages with their file counts, class counts, and key classes.
    Use for a quick understanding of codebase structure.

    Example:
        brief overview           # Show all packages
        brief overview src.brief # Show specific module details
    """
    from rich.console import Console

    brief_path = get_brief_path(base)
    console = Console(force_terminal=not plain, no_color=plain)

    if not brief_path.exists():
        console.print("[red]Error:[/red] Brief not initialized. Run 'brief init' first.")
        raise typer.Exit(1)

    if module:
        output = generate_module_overview(brief_path, module)
        typer.echo(output)
    else:
        if plain:
            output = generate_project_overview(brief_path, use_rich=False)
            typer.echo(output)
        else:
            generate_project_overview_rich(brief_path)


@app.command()
def tree(
    path: Optional[str] = typer.Argument(None, help="Path to show tree for"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    no_status: bool = typer.Option(False, "--no-status", help="Hide analysis status"),
    plain: bool = typer.Option(False, "--plain", "-p", help="Plain text output (no colors)"),
) -> None:
    """Show project structure as tree.

    Status markers:
      ✓ = Has description (green)
      ○ = Analyzed only (yellow)
      ✗ = Not analyzed (red)
    """
    from rich.console import Console

    brief_path = get_brief_path(base)
    console = Console(force_terminal=not plain, no_color=plain)

    if not brief_path.exists():
        console.print("[red]Error:[/red] Brief not initialized.")
        raise typer.Exit(1)

    output = generate_tree(brief_path, base, path, show_status=not no_status, use_color=not plain)

    if plain:
        typer.echo(output)
    else:
        console.print(output)


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
    unparsed: bool = typer.Option(False, "--unparsed", "-u", help="List all unparsed files"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show coverage by directory"),
) -> None:
    """Show analysis coverage statistics.

    Shows counts for:
    - Python files (analyzed/described)
    - Documentation files
    - Other tracked files (unparsed)

    Use --detailed to see breakdown by directory.
    Use --unparsed to see the full list of unparsed files.

    Example:
        brief coverage
        brief coverage --detailed
    """
    from rich.console import Console

    brief_path = get_brief_path(base)
    console = Console()

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    config = read_json(brief_path / "config.json")
    exclude_patterns = load_exclude_patterns(base, config)

    if detailed:
        format_coverage_detailed(brief_path, base, exclude_patterns, console)
    else:
        cov = calculate_coverage(brief_path, base, exclude_patterns)
        typer.echo(format_coverage(cov, show_unparsed=unparsed))


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
    record_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type (file/class/function/doc)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max records to show"),
) -> None:
    """List all items in the manifest.

    Types: file (Python), doc (markdown), class, function
    """
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
            parsed = record.get("parsed", True)
            ext = record.get("extension", ".py")
            tag = "FILE" if parsed else "OTHER"
            typer.echo(f"[{tag}] {record['path']}")
        elif rtype == "doc":
            title = record.get("title", "")
            typer.echo(f"[DOC] {record['path']}")
            if title:
                typer.echo(f"      Title: {title}")
        elif rtype == "class":
            typer.echo(f"[CLASS] {record['name']} in {record['file']}:{record['line']}")
        elif rtype == "function":
            prefix = f"{record['class_name']}." if record.get('class_name') else ""
            typer.echo(f"[FUNC] {prefix}{record['name']} in {record['file']}:{record['line']}")

    if len(records) == limit:
        typer.echo(f"\n(showing first {limit} records, use --limit to see more)")


@app.command()
def status(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    plain: bool = typer.Option(False, "--plain", "-p", help="Plain text output (no colors)"),
) -> None:
    """Show project status dashboard with key metrics."""
    from ..reporting.status import StatusReporter

    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    reporter = StatusReporter(brief_path, base)
    reporter.gather()

    if plain:
        typer.echo(reporter.format_plain())
    else:
        reporter.format_rich()
