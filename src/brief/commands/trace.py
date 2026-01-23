"""Execution path tracing commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from datetime import datetime
from ..config import get_brief_path
from ..tracing.tracer import PathTracer
from ..models import TraceDefinition

app = typer.Typer()


@app.command("list")
def trace_list(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category (cli, api, test, other)"),
) -> None:
    """List all trace definitions.

    Shows saved trace definitions with their entry points and validity status.
    Traces are regenerated dynamically when viewed - this just shows metadata.
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)
    definitions = tracer.list_trace_definitions()

    if category:
        definitions = [d for d in definitions if d.category == category]

    if not definitions:
        typer.echo("No trace definitions found.")
        typer.echo("")
        typer.echo("To create traces automatically from entry points:")
        typer.echo("  brief trace discover --auto")
        typer.echo("")
        typer.echo("To define a trace manually:")
        typer.echo("  brief trace define <name> <entry_point>")
        return

    # Group by category
    by_category: dict[str, list[TraceDefinition]] = {}
    for d in definitions:
        cat = d.category or "other"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(d)

    typer.echo(f"Trace Definitions ({len(definitions)}):")
    typer.echo("")

    for cat in ["cli", "api", "other", "test"]:
        if cat not in by_category:
            continue

        cat_traces = by_category[cat]
        typer.echo(f"  {cat.upper()} ({len(cat_traces)}):")

        for d in cat_traces:
            # Check if entry point still exists
            exists = tracer.check_entry_point_exists(d.entry_point)
            status = "✓" if exists else "✗"

            # Truncate description
            desc = d.description[:40] + "..." if len(d.description) > 40 else d.description

            if exists:
                typer.echo(f"    {status} {d.name:<25} {d.entry_point:<30} {desc}")
            else:
                typer.echo(f"    {status} {d.name:<25} {d.entry_point:<30} (entry point not found)")

        typer.echo("")

    typer.echo("  ✓ = entry point exists, ✗ = entry point not found")


@app.command("show")
def trace_show(
    name: str = typer.Argument(..., help="Trace name to show"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full code snippets"),
) -> None:
    """Show a trace (regenerated dynamically from current code).

    By default shows a compact flow diagram. Use -v for full code snippets.
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)
    definition = tracer.get_trace_definition(name)

    if not definition:
        typer.echo(f"Trace not found: {name}", err=True)
        typer.echo("")
        typer.echo("Available traces:")
        for t in tracer.list_trace_definitions():
            typer.echo(f"  - {t.name}")
        raise typer.Exit(1)

    # Generate trace dynamically
    path = tracer.generate_trace_from_definition(definition)

    if not path:
        typer.echo(f"# {name}")
        typer.echo("")
        typer.echo(f"Entry point `{definition.entry_point}` not found in codebase.")
        typer.echo("The function may have been renamed or deleted.")
        typer.echo("")
        typer.echo("Update the trace definition:")
        typer.echo(f"  brief trace update {name} --entry <new_entry_point>")
        raise typer.Exit(1)

    if verbose:
        # Full markdown with code
        typer.echo(path.to_markdown(include_code=True))
    else:
        # Compact flow diagram
        typer.echo(f"# {definition.name}")
        typer.echo("")
        if definition.description:
            typer.echo(definition.description)
            typer.echo("")
        typer.echo(path.to_flow())


@app.command("define")
def trace_define(
    name: str = typer.Argument(..., help="Trace name (e.g., 'user-login')"),
    entry_point: str = typer.Argument(..., help="Entry function (e.g., 'AuthService.login')"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    category: str = typer.Option("other", "--category", "-c", help="Category (cli, api, test, other)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Define a new trace from an entry point.

    Saves trace metadata only - content is regenerated dynamically when viewed.

    Example:
        brief trace define user-login AuthService.login -d "User authentication flow"
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)

    # Check if entry point exists
    if not tracer.check_entry_point_exists(entry_point):
        typer.echo(f"Warning: Entry point '{entry_point}' not found in manifest.", err=True)
        typer.echo("The trace will be saved but may not work until the function exists.")

    # Check if name already exists
    existing = tracer.get_trace_definition(name)
    if existing:
        typer.echo(f"Trace '{name}' already exists. Updating...")

    definition = TraceDefinition(
        name=name,
        entry_point=entry_point,
        description=description or f"Trace from {entry_point}",
        category=category,
        created=datetime.now()
    )

    tracer.save_trace_definition(definition)
    typer.echo(f"Trace definition saved: {name}")
    typer.echo(f"  Entry point: {entry_point}")
    typer.echo(f"  Category: {category}")
    typer.echo("")
    typer.echo(f"View with: brief trace show {name}")


@app.command("update")
def trace_update(
    name: str = typer.Argument(..., help="Trace name to update"),
    entry: Optional[str] = typer.Option(None, "--entry", "-e", help="New entry point"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="New category"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Update a trace definition."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)
    definition = tracer.get_trace_definition(name)

    if not definition:
        typer.echo(f"Trace not found: {name}", err=True)
        raise typer.Exit(1)

    # Update fields
    if entry:
        definition.entry_point = entry
    if description:
        definition.description = description
    if category:
        definition.category = category

    tracer.save_trace_definition(definition)
    typer.echo(f"Updated trace: {name}")


@app.command("delete")
def trace_delete(
    name: str = typer.Argument(..., help="Trace name to delete"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a trace definition."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)

    if not tracer.get_trace_definition(name):
        typer.echo(f"Trace not found: {name}", err=True)
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete trace '{name}'?")
        if not confirm:
            typer.echo("Cancelled.")
            return

    if tracer.delete_trace_definition(name):
        typer.echo(f"Deleted: {name}")
    else:
        typer.echo(f"Failed to delete: {name}", err=True)
        raise typer.Exit(1)


@app.command("discover")
def trace_discover(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Auto-create all without prompting"),
    include_tests: bool = typer.Option(False, "--include-tests", "-t", help="Include test functions"),
) -> None:
    """Discover entry points and create trace definitions.

    Scans the codebase for functions with entry point decorators
    (like @app.command, @app.route) and creates trace definitions for them.

    Example:
        brief trace discover --auto
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)

    typer.echo("Scanning for entry points...")
    entry_points = tracer.find_entry_points(include_tests=include_tests)

    if not entry_points:
        typer.echo("No entry points found.")
        typer.echo("")
        typer.echo("Entry points are detected from decorators like:")
        typer.echo("  @app.command, @click.command (CLI)")
        typer.echo("  @app.route, @router.get (API)")
        typer.echo("")
        typer.echo("Make sure you've run 'brief analyze all' first.")
        return

    # Check existing definitions
    existing = {t.name for t in tracer.list_trace_definitions()}

    typer.echo(f"Found {len(entry_points)} entry points:")
    typer.echo("")

    # Group by category
    by_category: dict[str, list] = {}
    for ep in entry_points:
        cat = ep["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(ep)

    for cat, eps in by_category.items():
        typer.echo(f"  {cat.upper()}: {len(eps)}")
        for ep in eps[:5]:  # Show first 5 per category
            typer.echo(f"    - {ep['function']} ({ep['decorator']})")
        if len(eps) > 5:
            typer.echo(f"    ... and {len(eps) - 5} more")
        typer.echo("")

    if auto:
        created = tracer.auto_create_trace_definitions(include_tests=include_tests)
        typer.echo(f"Created {len(created)} trace definitions.")
        for d in created[:10]:
            typer.echo(f"  - {d.name}: {d.entry_point}")
        if len(created) > 10:
            typer.echo(f"  ... and {len(created) - 10} more")
    else:
        typer.echo("Run with --auto to create trace definitions for all entry points.")
        typer.echo("Or define individually with: brief trace define <name> <entry_point>")


# Backward compatibility alias
@app.command("create", hidden=True)
def trace_create(
    name: str = typer.Argument(..., help="Trace name"),
    entry_point: str = typer.Argument(..., help="Entry function"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    depth: int = typer.Option(5, "--depth", help="(Ignored - for backward compatibility)"),
) -> None:
    """(Deprecated) Use 'brief trace define' instead."""
    trace_define(name, entry_point, description, "other", base)
