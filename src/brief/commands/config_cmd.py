"""Configuration management commands for Brief."""
import typer
from pathlib import Path
from ..config import get_brief_path
from ..storage import write_json, read_json
from ..models import BriefConfig

app = typer.Typer()


def load_gitignore_patterns(base_path: Path) -> list[str]:
    """Load patterns from .gitignore file."""
    gitignore = base_path / ".gitignore"
    if not gitignore.exists():
        return []

    patterns = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        # Skip negation patterns (we don't support those)
        if line.startswith("!"):
            continue
        # Strip trailing slash (gitignore convention for directories)
        pattern = line.rstrip("/")
        if pattern:
            patterns.append(pattern)

    return patterns


@app.command("show")
def config_show(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show current configuration."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    config = read_json(brief_path / "config.json")

    typer.echo("Brief Configuration:")
    typer.echo("=" * 40)
    typer.echo(f"Version: {config.get('version', 'unknown')}")
    typer.echo(f"Default model: {config.get('default_model', 'not set')}")
    typer.echo(f"Auto analyze: {config.get('auto_analyze', False)}")
    typer.echo(f"Use gitignore: {config.get('use_gitignore', False)}")
    typer.echo("")
    typer.echo("Exclude patterns:")
    for pattern in config.get("exclude_patterns", []):
        typer.echo(f"  - {pattern}")

    # Show effective gitignore patterns if enabled
    if config.get("use_gitignore", False):
        gitignore_patterns = load_gitignore_patterns(base)
        if gitignore_patterns:
            typer.echo("")
            typer.echo(f"Gitignore patterns ({len(gitignore_patterns)} from .gitignore):")
            for pattern in gitignore_patterns[:10]:
                typer.echo(f"  - {pattern}")
            if len(gitignore_patterns) > 10:
                typer.echo(f"  ... and {len(gitignore_patterns) - 10} more")


@app.command("reset")
def config_reset(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    use_gitignore: bool = typer.Option(True, "--gitignore/--no-gitignore", help="Include .gitignore patterns"),
) -> None:
    """Reset configuration to defaults.

    This regenerates config.json with the latest default values.
    Use --no-gitignore to disable .gitignore integration.
    """
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    # Create fresh config with defaults
    config = BriefConfig(use_gitignore=use_gitignore)
    write_json(brief_path / "config.json", config.model_dump())

    typer.echo("Configuration reset to defaults.")
    typer.echo(f"  Use gitignore: {use_gitignore}")
    typer.echo(f"  Exclude patterns: {len(config.exclude_patterns)}")

    if use_gitignore:
        gitignore_patterns = load_gitignore_patterns(base)
        if gitignore_patterns:
            typer.echo(f"  Gitignore patterns: {len(gitignore_patterns)} (from .gitignore)")
        else:
            typer.echo("  Gitignore patterns: 0 (no .gitignore found)")


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key to set"),
    value: str = typer.Argument(..., help="Value to set"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Set a configuration value.

    Examples:
        brief config set use_gitignore true
        brief config set default_model gpt-4
    """
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    config = read_json(brief_path / "config.json")

    # Parse value
    if value.lower() == "true":
        parsed_value = True
    elif value.lower() == "false":
        parsed_value = False
    else:
        parsed_value = value

    if key not in config:
        typer.echo(f"Warning: '{key}' is not a standard config key.", err=True)

    config[key] = parsed_value
    write_json(brief_path / "config.json", config)

    typer.echo(f"Set {key} = {parsed_value}")
