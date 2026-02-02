"""Brief CLI - Context infrastructure for AI coding agents."""

import sys
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(
    name="brief",
    help="Context infrastructure for AI coding agents - deterministic context packages for convergent code generation",
    no_args_is_help=True,
    rich_markup_mode="rich",
    epilog="[dim]Quick start: brief setup -d  |  Try: brief ctx \"your query\"  |  Docs: brief --help[/dim]",
)


# --- "Did you mean?" suggestion system ---
# Maps subcommand group names to their most common subcommand suggestions.
_SUBCOMMAND_SUGGESTIONS: dict[str, list[str]] = {
    "task": ["list", "create", "show", "start", "done"],
    "context": ["get", "search", "embed"],
    "analyze": ["all", "file", "dir", "refresh"],
    "describe": ["file", "batch", "module"],
    "memory": ["remember", "recall", "list"],
    "trace": ["list", "show", "define"],
    "contracts": ["detect", "show", "list"],
    "config": ["show", "set"],
    "model": ["list", "set"],
    "logs": ["show", "tail"],
}


def _make_suggestion_callback(group_name: str):
    """Create a callback that shows suggestions when a subcommand group is invoked bare."""
    def callback(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            suggestions = _SUBCOMMAND_SUGGESTIONS.get(group_name, [])
            typer.echo(f"Missing command for 'brief {group_name}'.", err=True)
            typer.echo("", err=True)
            if suggestions:
                typer.echo("Did you mean one of these?", err=True)
                for s in suggestions:
                    typer.echo(f"  brief {group_name} {s}", err=True)
                typer.echo("", err=True)
            typer.echo(f"Use 'brief {group_name} --help' for all available commands.", err=True)
            raise typer.Exit(1)
    return callback


@app.callback()
def main(ctx: typer.Context) -> None:
    """Brief - Context infrastructure for AI coding agents."""
    # Log command invocation for development tracking
    from .logging import log_from_cli
    try:
        log_from_cli()
    except Exception:
        # Don't let logging failures break the CLI
        pass


def _run_quick_query(query: str, base: Path) -> None:
    """Run a quick context query."""
    from .config import get_brief_path, MANIFEST_FILE
    from .retrieval.context import build_context_for_query
    from .retrieval.search import hybrid_search
    from .commands.context import _get_auto_generate_default, _check_manifest_has_files

    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    if not _check_manifest_has_files(brief_path):
        typer.echo("Error: No files in manifest. Run 'brief analyze all' first.", err=True)
        raise typer.Exit(1)

    should_auto_generate = _get_auto_generate_default(brief_path)

    def search_func(q: str):
        return hybrid_search(brief_path, q)

    package = build_context_for_query(
        brief_path,
        query,
        search_func,
        base_path=base,
        include_contracts=True,
        include_paths=True,
        include_patterns=True,
        auto_generate_descriptions=should_auto_generate
    )

    typer.echo(package.to_markdown())


# Quick context query command
@app.command(name="q", rich_help_panel="Context Queries")
def query_shortcut(
    query: str = typer.Argument(..., help="Query for context"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Quick context lookup (shortcut for 'context get').

    Example:
        brief q "add logging to tracing"
        brief q "error handling patterns"
    """
    _run_quick_query(query, base)


# Context query alias (brief ctx "query")
@app.command(name="ctx", rich_help_panel="Context Queries")
def ctx_shortcut(
    query: str = typer.Argument(..., help="Query for context"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Quick context lookup (alias for 'context get').

    Example:
        brief ctx "authentication flow"
        brief ctx "how does search work"
    """
    _run_quick_query(query, base)


# Import and register command modules
from .commands import init as init_cmd
from .commands import analyze as analyze_cmd
from .commands import report as report_cmd
from .commands import describe as describe_cmd
from .commands import context as context_cmd
from .commands import task as task_cmd
from .commands import memory as memory_cmd
from .commands import trace as trace_cmd
from .commands import contracts as contracts_cmd
from .commands import config_cmd
from .commands import reset as reset_cmd
from .commands import setup as setup_cmd
from .commands import model as model_cmd
from .commands import logs as logs_cmd

# Register init as a direct command (not a subcommand)
app.command(name="init", rich_help_panel="Getting Started")(init_cmd.init)

# Register setup wizard as a direct command
app.command(name="setup", rich_help_panel="Getting Started")(setup_cmd.setup)

# Register reset as a direct command
app.command(name="reset", rich_help_panel="Advanced")(reset_cmd.reset)

# Register subcommand groups with "did you mean?" callbacks and help panels
_subcommand_groups = {
    "context": (context_cmd.app, "Context Queries"),
    "analyze": (analyze_cmd.app, "Analysis"),
    "describe": (describe_cmd.app, "Analysis"),
    "task": (task_cmd.app, "Task Management"),
    "memory": (memory_cmd.app, "Context Queries"),
    "trace": (trace_cmd.app, "Analysis"),
    "contracts": (contracts_cmd.app, "Analysis"),
    "config": (config_cmd.app, "Advanced"),
    "model": (model_cmd.app, "Advanced"),
    "logs": (logs_cmd.app, "Advanced"),
}

for group_name, (group_app, panel) in _subcommand_groups.items():
    group_app.info.invoke_without_command = True
    group_app.registered_callback = None  # Clear any existing
    group_app.callback()(_make_suggestion_callback(group_name))
    app.add_typer(group_app, name=group_name, rich_help_panel=panel)

# Register individual report commands at top level
app.command(name="status", rich_help_panel="Getting Started")(report_cmd.status)
app.command(name="overview", rich_help_panel="Reports")(report_cmd.overview)
app.command(name="tree", rich_help_panel="Reports")(report_cmd.tree)
app.command(name="deps", rich_help_panel="Reports")(report_cmd.deps)
app.command(name="coverage", rich_help_panel="Reports")(report_cmd.coverage_cmd)
app.command(name="stale", rich_help_panel="Reports")(report_cmd.stale)
app.command(name="inventory", rich_help_panel="Reports")(report_cmd.inventory)

# Register top-level aliases for common memory commands
app.command(name="remember", rich_help_panel="Context Queries")(memory_cmd.memory_add)
app.command(name="recall", rich_help_panel="Context Queries")(memory_cmd.memory_get)


# Resume command - top-level for easy access
@app.command(name="resume", rich_help_panel="Task Management")
def resume(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output to file"),
) -> None:
    """Get context for resuming work on the active task.

    Shows:
    - Current active task status
    - Steps and progress (if any)
    - Notes you've left
    - Relevant files, patterns, and contracts

    Example:
        brief resume
        brief resume --output resume-context.md
    """
    from .config import get_brief_path
    from .storage import read_json
    from .tasks.manager import TaskManager
    from .retrieval.context import build_context_for_query
    from .retrieval.search import hybrid_search

    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    # Check if tasks are enabled
    config = read_json(brief_path / "config.json")
    if not config.get("enable_tasks", False):
        typer.echo("Task system is not enabled.", err=True)
        typer.echo("To enable: brief config set enable_tasks true", err=True)
        typer.echo("Or re-run setup with: brief setup --tasks", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)
    task = manager.get_active_task()

    if not task:
        typer.echo("No active task.")
        typer.echo("")
        typer.echo("To start working on a task:")
        typer.echo("  brief task start <task-id>")
        typer.echo("")
        typer.echo("Or create and start a new task:")
        typer.echo("  brief task create \"Task title\"")
        typer.echo("  brief task start <task-id>")
        return

    # Build resumption context
    lines = [
        "# Resume Context",
        "",
        f"**Active Task**: {task.id} - {task.title}",
        f"**Status**: {task.status.value}",
        ""
    ]

    if task.description:
        lines.extend([
            "## Description",
            task.description,
            ""
        ])

    # Steps progress
    if task.steps:
        summary = manager.get_step_summary(task.id)
        lines.extend([
            "## Progress",
            "",
            f"{summary['completed']}/{summary['total_steps']} steps complete ({summary['progress_percent']:.0f}%)",
            ""
        ])

        if summary['current_step']:
            lines.append(f"**Current step**: {summary['current_step']} - {summary['current_step_name']}")
            lines.append("")

        lines.append("### Steps")
        lines.append("")
        for step in task.steps:
            icon = {
                "pending": "[ ]",
                "in_progress": "[~]",
                "complete": "[x]",
                "skipped": "[-]"
            }.get(step.status.value, "[?]")
            lines.append(f"- {icon} {step.name}")
            if step.notes:
                lines.append(f"  - Note: {step.notes}")
        lines.append("")

    # Notes
    if task.notes:
        lines.extend([
            "## Notes",
            ""
        ])
        for note in task.notes:
            lines.append(f"- {note}")
        lines.append("")

    # Get relevant context
    query = task.title
    if task.description:
        query = f"{task.title}: {task.description}"

    def search_func(q: str):
        return hybrid_search(brief_path, q)

    context_package = build_context_for_query(
        brief_path,
        query,
        search_func,
        base_path=base
    )

    if context_package.primary_files:
        lines.extend([
            "## Relevant Files",
            ""
        ])
        for f in context_package.primary_files[:5]:
            lines.append(f"- `{f['path']}`")
        lines.append("")

    if context_package.patterns:
        lines.extend([
            "## Relevant Patterns",
            ""
        ])
        for p in context_package.patterns[:5]:
            lines.append(f"- **{p['key']}**: {p['value']}")
        lines.append("")

    if context_package.contracts:
        lines.extend([
            "## Relevant Contracts",
            ""
        ])
        for c in context_package.contracts[:5]:
            lines.append(f"- {c}")
        lines.append("")

    markdown = "\n".join(lines)

    if output:
        output.write_text(markdown)
        typer.echo(f"Resumption context written to {output}")
    else:
        typer.echo(markdown)


if __name__ == "__main__":
    app()
