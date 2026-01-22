"""Execution path tracing commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path
from ..tracing.tracer import PathTracer

app = typer.Typer()


@app.command("create")
def trace_create(
    name: str = typer.Argument(..., help="Path name (e.g., 'workspace-creation')"),
    entry_point: str = typer.Argument(..., help="Entry function (e.g., 'Acme.create_workspace')"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Path description"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    depth: int = typer.Option(5, "--depth", help="Max trace depth"),
) -> None:
    """Trace and document an execution path."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)

    typer.echo(f"Tracing from: {entry_point}")
    path = tracer.create_path(name, entry_point, description or "")

    if not path.steps:
        typer.echo("Warning: No steps traced. Entry point may not be in manifest.")
        typer.echo("Make sure you've run 'brief analyze' first.")

    file_path = tracer.save_path(path)
    typer.echo(f"Path saved to: {file_path}")
    typer.echo("")
    typer.echo(f"Steps traced: {len(path.steps)}")
    typer.echo(f"Related files: {len(path.related_files)}")


@app.command("show")
def trace_show(
    name: str = typer.Argument(..., help="Path name to show"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show a saved execution path."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)
    content = tracer.load_path(name)

    if content:
        typer.echo(content)
    else:
        typer.echo(f"Path not found: {name}", err=True)
        raise typer.Exit(1)


@app.command("list")
def trace_list(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """List all traced execution paths."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)
    paths = tracer.list_paths()

    if not paths:
        typer.echo("No execution paths traced yet.")
        typer.echo("Use 'brieftrace create' to trace a path.")
        return

    typer.echo(f"Execution paths ({len(paths)}):")
    for path_name in paths:
        typer.echo(f"  - {path_name}")


@app.command("delete")
def trace_delete(
    name: str = typer.Argument(..., help="Path name to delete"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a traced execution path."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    tracer = PathTracer(brief_path, base)

    # Check if path exists
    if not tracer.load_path(name):
        typer.echo(f"Path not found: {name}", err=True)
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete path '{name}'?")
        if not confirm:
            typer.echo("Cancelled.")
            return

    if tracer.delete_path(name):
        typer.echo(f"Deleted: {name}")
    else:
        typer.echo(f"Failed to delete: {name}", err=True)
        raise typer.Exit(1)
