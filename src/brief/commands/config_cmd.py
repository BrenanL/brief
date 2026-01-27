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
    plain: bool = typer.Option(False, "--plain", "-p", help="Plain text output"),
) -> None:
    """Show current configuration.

    Displays all configuration values and marks which are defaults vs custom.

    Example:
        brief config show
    """
    from rich.console import Console
    from rich.table import Table
    from rich import box

    brief_path = get_brief_path(base)
    console = Console(force_terminal=not plain, no_color=plain)

    if not brief_path.exists():
        console.print("[red]Error:[/red] Brief not initialized. Run 'brief init' first.")
        raise typer.Exit(1)

    config = read_json(brief_path / "config.json")
    defaults = BriefConfig()

    # Display config file location
    config_file = brief_path / "config.json"
    console.print(f"[dim]Config file: {config_file}[/dim]")
    console.print()

    # Create table for settings
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Status", justify="center")

    # Core settings
    settings = [
        ("version", config.get("version"), defaults.version),
        ("default_model", config.get("default_model"), defaults.default_model),
        ("auto_analyze", config.get("auto_analyze"), defaults.auto_analyze),
        ("use_gitignore", config.get("use_gitignore"), defaults.use_gitignore),
        ("command_logging", config.get("command_logging"), defaults.command_logging),
        ("auto_generate_descriptions", config.get("auto_generate_descriptions"), defaults.auto_generate_descriptions),
        ("enable_tasks", config.get("enable_tasks"), defaults.enable_tasks),
        ("llm_provider", config.get("llm_provider"), defaults.llm_provider),
    ]

    for name, value, default in settings:
        value_str = str(value) if value is not None else str(default)
        if value == default or value is None:
            status = "[dim]default[/dim]"
        else:
            status = "[green]custom[/green]"
        table.add_row(name, value_str, status)

    console.print(table)

    # Exclude patterns
    console.print()
    exclude = config.get("exclude_patterns", defaults.exclude_patterns)
    console.print(f"[bold]Exclude patterns[/bold] ({len(exclude)}):")
    for pattern in exclude[:8]:
        console.print(f"  [dim]-[/dim] {pattern}")
    if len(exclude) > 8:
        console.print(f"  [dim]... and {len(exclude) - 8} more[/dim]")

    # Show effective gitignore patterns if enabled
    if config.get("use_gitignore", defaults.use_gitignore):
        gitignore_patterns = load_gitignore_patterns(base)
        if gitignore_patterns:
            console.print()
            console.print(f"[bold]Gitignore patterns[/bold] ({len(gitignore_patterns)} from .gitignore):")
            for pattern in gitignore_patterns[:5]:
                console.print(f"  [dim]-[/dim] {pattern}")
            if len(gitignore_patterns) > 5:
                console.print(f"  [dim]... and {len(gitignore_patterns) - 5} more[/dim]")


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
