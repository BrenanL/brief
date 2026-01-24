"""Memory/pattern commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path
from ..memory.store import MemoryStore

app = typer.Typer()


@app.command("add")
def memory_add(
    key: str = typer.Argument(..., help="Pattern key (e.g., 'api/workspace')"),
    value: str = typer.Argument(..., help="Pattern value/description"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Path scope (glob pattern)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Store a pattern in memory.

    Example:
        brief memory add "error-handling" "Use typer.echo for errors"
        brief remember "api/auth" "Use JWT tokens" --tags auth,api
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    store = MemoryStore(brief_path)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    record = store.remember(
        key=key,
        value=value,
        tags=tag_list,
        scope=scope,
        source="cli"
    )

    typer.echo(f"Remembered: {record.key}")
    typer.echo(f"  Value: {record.value}")
    if tag_list:
        typer.echo(f"  Tags: {', '.join(tag_list)}")
    if scope:
        typer.echo(f"  Scope: {scope}")


@app.command("get")
def memory_get(
    query: Optional[str] = typer.Argument(None, help="Search query or key"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Filter by tags"),
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Filter by scope"),
    file_path: Optional[str] = typer.Option(None, "--file", "-f", help="Get patterns for file"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Get patterns from memory.

    Example:
        brief memory get                  # List all patterns
        brief memory get "error"          # Search for patterns
        brief recall --file src/api.py    # Get patterns for a file
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    store = MemoryStore(brief_path)

    if file_path:
        results = store.recall_for_file(file_path)
    else:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        results = store.recall(query=query, tags=tag_list, scope=scope)

    if not results:
        typer.echo("No patterns found.")
        return

    typer.echo(f"Patterns ({len(results)}):")
    typer.echo("-" * 60)

    for record in results:
        typer.echo(f"[{record.key}]")
        typer.echo(f"  {record.value}")
        if record.tags:
            typer.echo(f"  Tags: {', '.join(record.tags)}")
        if record.scope:
            typer.echo(f"  Scope: {record.scope}")
        typer.echo(f"  Used: {record.use_count} times | Confidence: {record.confidence}")
        typer.echo("")


@app.command("forget")
def memory_forget(
    key: str = typer.Argument(..., help="Pattern key to forget"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Remove a pattern from memory."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    store = MemoryStore(brief_path)

    if store.forget(key):
        typer.echo(f"Forgot: {key}")
    else:
        typer.echo(f"Pattern not found: {key}", err=True)
        raise typer.Exit(1)


@app.command("bump")
def memory_bump(
    key: str = typer.Argument(..., help="Pattern key to reinforce"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Reinforce a pattern (increment use count)."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    store = MemoryStore(brief_path)

    record = store.bump(key)
    if record:
        typer.echo(f"Reinforced: {key} (use count: {record.use_count})")
    else:
        typer.echo(f"Pattern not found: {key}", err=True)
        raise typer.Exit(1)


@app.command("list")
def memory_list(
    prefix: Optional[str] = typer.Argument(None, help="Key prefix filter"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """List all pattern keys."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    store = MemoryStore(brief_path)
    keys = store.list_keys(prefix)

    if not keys:
        typer.echo("No patterns stored.")
        return

    typer.echo(f"Pattern keys ({len(keys)}):")
    for key in keys:
        typer.echo(f"  {key}")


@app.command("show")
def memory_show(
    key: str = typer.Argument(..., help="Pattern key to show"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show details of a specific pattern."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    store = MemoryStore(brief_path)
    record = store.get(key)

    if not record:
        typer.echo(f"Pattern not found: {key}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Key: {record.key}")
    typer.echo(f"Value: {record.value}")
    typer.echo(f"Tags: {', '.join(record.tags) if record.tags else '(none)'}")
    typer.echo(f"Scope: {record.scope or '(global)'}")
    typer.echo(f"Source: {record.source}")
    typer.echo(f"Confidence: {record.confidence}")
    typer.echo(f"Use count: {record.use_count}")
    typer.echo(f"Created: {record.created}")
    if record.last_used:
        typer.echo(f"Last used: {record.last_used}")
