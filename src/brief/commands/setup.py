"""Setup wizard for Brief."""

import os
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

from ..config import get_brief_path
from ..storage import write_json, read_json
from ..models import BriefConfig


def _detect_api_keys() -> dict[str, bool]:
    """Detect which LLM API keys are available."""
    return {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "google": bool(os.environ.get("GOOGLE_API_KEY")),
    }


def _check_dotenv(base_path: Path) -> bool:
    """Check if a .env file exists."""
    return (base_path / ".env").exists()


def setup(
    path: Path = typer.Argument(
        Path("."),
        help="Path to set up Brief in"
    ),
    non_interactive: bool = typer.Option(
        False,
        "--default",
        "-d",
        help="Accept all defaults (non-interactive)"
    ),
) -> None:
    """Interactive setup wizard for Brief.

    Guides you through:
    - Initializing Brief in your repository
    - Configuring LLM providers
    - Setting up auto-generation preferences
    - Running initial analysis

    Example:
        brief setup              # Interactive setup
        brief setup --default    # Accept all defaults
    """
    console = Console()
    brief_path = get_brief_path(path)

    # Welcome banner
    console.print()
    console.print(Panel(
        "[bold cyan]Brief Setup Wizard[/bold cyan]\n"
        "Context infrastructure for AI coding agents",
        box=box.ROUNDED,
        padding=(1, 2)
    ))
    console.print()

    # Check if already initialized
    already_initialized = brief_path.exists()
    if already_initialized:
        console.print("[yellow]Brief is already initialized in this directory.[/yellow]")
        if not non_interactive:
            reconfigure = Confirm.ask("Do you want to reconfigure?", default=False)
            if not reconfigure:
                console.print("Setup cancelled.")
                raise typer.Exit(0)
        console.print()

    # Detect API keys
    api_keys = _detect_api_keys()
    has_any_key = any(api_keys.values())
    has_dotenv = _check_dotenv(path)

    console.print("[bold]Step 1: LLM Provider Configuration[/bold]")
    console.print()

    if has_any_key:
        console.print("[green]Detected API keys:[/green]")
        if api_keys["openai"]:
            console.print("  [green]✓[/green] OpenAI (OPENAI_API_KEY)")
        if api_keys["anthropic"]:
            console.print("  [green]✓[/green] Anthropic (ANTHROPIC_API_KEY)")
        if api_keys["google"]:
            console.print("  [green]✓[/green] Google (GOOGLE_API_KEY)")
    else:
        console.print("[yellow]No LLM API keys detected.[/yellow]")
        if has_dotenv:
            console.print("[dim]Found .env file - keys may be loaded at runtime.[/dim]")
        else:
            console.print()
            console.print("Brief can generate file descriptions using LLMs.")
            console.print("To enable this, set one of these environment variables:")
            console.print("  OPENAI_API_KEY    - For GPT models")
            console.print("  ANTHROPIC_API_KEY - For Claude models")
            console.print("  GOOGLE_API_KEY    - For Gemini models")
            console.print()
            console.print("[dim]You can add these to a .env file in your project root.[/dim]")

    console.print()

    # Auto-generation setting
    console.print("[bold]Step 2: Description Generation[/bold]")
    console.print()
    console.print("Brief can automatically generate natural language descriptions")
    console.print("of your code when you query for context. This requires an LLM API key.")
    console.print()

    if non_interactive:
        auto_generate = True
    else:
        default_auto = has_any_key or has_dotenv
        auto_generate = Confirm.ask(
            "Enable auto-generation of descriptions?",
            default=default_auto
        )

    console.print()

    # Gitignore integration
    console.print("[bold]Step 3: File Filtering[/bold]")
    console.print()
    console.print("Brief can use your .gitignore patterns to exclude files from analysis.")
    console.print()

    if non_interactive:
        use_gitignore = True
    else:
        use_gitignore = Confirm.ask(
            "Use .gitignore patterns for filtering?",
            default=True
        )

    console.print()

    # Command logging
    console.print("[bold]Step 4: Development Logging[/bold]")
    console.print()
    console.print("Brief can log command invocations to .brief-logs/ for debugging.")
    console.print()

    if non_interactive:
        command_logging = True
    else:
        command_logging = Confirm.ask(
            "Enable command logging?",
            default=True
        )

    console.print()

    # Initialize Brief
    console.print("[bold]Setting up Brief...[/bold]")
    console.print()

    if not already_initialized:
        # Create directory structure
        from ..config import (
            MANIFEST_FILE,
            RELATIONSHIPS_FILE,
            TASKS_FILE,
            MEMORY_FILE,
            CONTEXT_DIR,
        )
        from ..storage import write_jsonl

        brief_path.mkdir(parents=True, exist_ok=True)
        (brief_path / CONTEXT_DIR).mkdir(exist_ok=True)
        (brief_path / CONTEXT_DIR / "modules").mkdir(exist_ok=True)
        (brief_path / CONTEXT_DIR / "files").mkdir(exist_ok=True)
        (brief_path / CONTEXT_DIR / "paths").mkdir(exist_ok=True)

        write_jsonl(brief_path / MANIFEST_FILE, [])
        write_jsonl(brief_path / RELATIONSHIPS_FILE, [])
        write_jsonl(brief_path / TASKS_FILE, [])
        write_jsonl(brief_path / MEMORY_FILE, [])

        console.print("  [green]✓[/green] Created .brief directory structure")

    # Create/update config
    config = BriefConfig(
        use_gitignore=use_gitignore,
        command_logging=command_logging,
        auto_generate_descriptions=auto_generate,
    )
    write_json(brief_path / "config.json", config.model_dump())
    console.print("  [green]✓[/green] Saved configuration")

    console.print()

    # Offer to run analysis
    console.print("[bold]Step 5: Initial Analysis[/bold]")
    console.print()
    console.print("Brief works best after analyzing your codebase.")
    console.print()

    if non_interactive:
        run_analysis = True
    else:
        run_analysis = Confirm.ask(
            "Run initial analysis now?",
            default=True
        )

    if run_analysis:
        console.print()
        console.print("[dim]Running analysis...[/dim]")

        from ..analysis.manifest import ManifestBuilder
        from ..analysis.relationships import RelationshipExtractor
        from ..config import load_exclude_patterns

        current_config = read_json(brief_path / "config.json")
        exclude_patterns = load_exclude_patterns(path, current_config)

        builder = ManifestBuilder(path, exclude_patterns)
        builder.analyze_directory()
        builder.save_manifest(brief_path)

        extractor = RelationshipExtractor(path, exclude_patterns)
        extractor.extract_all()
        extractor.save_relationships(brief_path)

        stats = builder.get_stats()

        console.print(f"  [green]✓[/green] Analyzed {stats['python_files']} Python files")
        console.print(f"  [green]✓[/green] Found {stats['classes']} classes, {stats['module_functions'] + stats['methods']} functions")

    console.print()

    # Summary
    console.print(Panel(
        "[bold green]Setup Complete![/bold green]\n\n"
        f"Auto-generate descriptions: {'[green]enabled[/green]' if auto_generate else '[yellow]disabled[/yellow]'}\n"
        f"Gitignore filtering: {'[green]enabled[/green]' if use_gitignore else '[yellow]disabled[/yellow]'}\n"
        f"Command logging: {'[green]enabled[/green]' if command_logging else '[yellow]disabled[/yellow]'}",
        box=box.ROUNDED,
        title="Configuration"
    ))

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print()
    console.print("  [cyan]brief status[/cyan]         - See project overview")
    console.print("  [cyan]brief q \"query\"[/cyan]      - Get context for a query")
    console.print("  [cyan]brief describe batch[/cyan] - Generate descriptions (if LLM available)")
    console.print("  [cyan]brief task list[/cyan]      - Manage tasks")
    console.print()
    console.print("[dim]Run 'brief --help' for all available commands.[/dim]")
