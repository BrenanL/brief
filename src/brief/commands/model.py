"""Model selection commands for Brief."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage LLM model selection")
console = Console()


@app.command("list")
def model_list() -> None:
    """List available LLM models.

    Shows all configured models with their providers.

    Examples:
        brief model list
    """
    from ..llm import get_available_models, get_model_info, get_active_model

    active = get_active_model()
    models = get_available_models()

    table = Table(title="Available Models")
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Status", style="yellow")

    for model in models:
        info = get_model_info(model)
        status = "active" if model == active else ""
        table.add_row(model, info.get("provider", "unknown"), status)

    console.print(table)
    console.print(f"\nActive model: [bold cyan]{active}[/bold cyan]")
    console.print("\nUse 'brief model set <name>' to change the active model.")
    console.print("Use 'brief config set default_model <name>' to change the persistent default.")


@app.command("set")
def model_set(
    model: str = typer.Argument(
        ...,
        help="Model name to set as active (e.g., gemini-2.5-flash, gpt-5-mini)"
    ),
    base: Path = typer.Option(
        Path("."),
        "--base", "-b",
        help="Base path for Brief project"
    ),
) -> None:
    """Set the active model for this session.

    This sets a session override that takes precedence over the config default.
    The setting persists until cleared with 'brief model clear'.

    Examples:
        brief model set gemini-2.5-flash
        brief model set gpt-5-mini
        brief model set claude-sonnet
    """
    from ..llm import set_active_model, get_available_models

    available = get_available_models()

    if model not in available:
        typer.echo(f"Error: Unknown model '{model}'", err=True)
        typer.echo(f"Available models: {', '.join(available)}", err=True)
        raise typer.Exit(1)

    if set_active_model(model, base):
        typer.echo(f"Active model set to: {model}")
        typer.echo("This is a session override. Use 'brief model clear' to revert to config default.")
    else:
        typer.echo("Error: Failed to set active model", err=True)
        raise typer.Exit(1)


@app.command("show")
def model_show(
    base: Path = typer.Option(
        Path("."),
        "--base", "-b",
        help="Base path for Brief project"
    ),
) -> None:
    """Show the currently active model.

    Displays the active model and whether it's from a session override or config default.

    Examples:
        brief model show
    """
    from ..llm import get_active_model, get_model_info, ACTIVE_MODEL_FILE
    from ..config import get_brief_path

    brief_path = get_brief_path(base)
    active_file = brief_path / ACTIVE_MODEL_FILE

    model = get_active_model(base)
    info = get_model_info(model)

    source = "session override" if active_file.exists() else "config default"

    console.print(f"Active model: [bold cyan]{model}[/bold cyan]")
    console.print(f"Provider: [green]{info.get('provider', 'unknown')}[/green]")
    console.print(f"BAML client: {info.get('client', 'unknown')}")
    console.print(f"Source: {source}")


@app.command("clear")
def model_clear(
    base: Path = typer.Option(
        Path("."),
        "--base", "-b",
        help="Base path for Brief project"
    ),
) -> None:
    """Clear the session model override.

    Reverts to using the config default_model setting.

    Examples:
        brief model clear
    """
    from ..llm import clear_active_model, get_active_model

    if clear_active_model(base):
        new_model = get_active_model(base)
        typer.echo(f"Session override cleared. Now using config default: {new_model}")
    else:
        typer.echo("No session override was set.")


@app.command("test")
def model_test(
    model: str = typer.Argument(
        None,
        help="Model to test (default: active model)"
    ),
    base: Path = typer.Option(
        Path("."),
        "--base", "-b",
        help="Base path for Brief project"
    ),
    all_models: bool = typer.Option(
        False,
        "--all", "-a",
        help="Test all available models"
    ),
) -> None:
    """Test LLM model connectivity.

    Sends a simple test prompt to verify the model is working.

    Examples:
        brief model test                    # Test active model
        brief model test gemini-2.5-flash   # Test specific model
        brief model test --all              # Test all models
    """
    from ..config import load_env
    from ..llm import get_available_models, get_active_model, get_model_client_name

    # Load environment variables before BAML imports
    load_env()

    # Import BAML client
    try:
        import sys
        repo_root = Path(__file__).parent.parent.parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from baml_client.sync_client import b as baml_client
    except ImportError as e:
        typer.echo(f"Error: Could not import BAML client: {e}", err=True)
        typer.echo("Run 'baml-cli generate' first.", err=True)
        raise typer.Exit(1)

    models_to_test = []

    if all_models:
        models_to_test = get_available_models()
    elif model:
        if model not in get_available_models():
            typer.echo(f"Error: Unknown model '{model}'", err=True)
            raise typer.Exit(1)
        models_to_test = [model]
    else:
        models_to_test = [get_active_model(base)]

    # Simple test code
    test_code = '''def hello(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"
'''

    results = []

    for m in models_to_test:
        client_name = get_model_client_name(m)
        typer.echo(f"\nTesting {m} ({client_name})...")

        try:
            result = baml_client.DescribeFunction(
                function_name="hello",
                function_code=test_code,
                file_context="test.py",
                docstring="Greet someone by name.",
                baml_options={"client": client_name}
            )
            typer.echo(f"  [OK] Response: {result.purpose[:60]}...")
            results.append((m, True, None))
        except Exception as e:
            error_msg = str(e)[:100]
            typer.echo(f"  [FAIL] {error_msg}")
            results.append((m, False, error_msg))

    # Summary
    typer.echo("\n" + "=" * 50)
    typer.echo("Summary:")
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    typer.echo(f"  Passed: {passed}/{len(results)}")
    if failed > 0:
        typer.echo(f"  Failed: {failed}")
        for m, success, error in results:
            if not success:
                typer.echo(f"    - {m}: {error}")
