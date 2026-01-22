"""Brief CLI - Context infrastructure for AI coding agents."""

import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(
    name="brief",
    help="Context infrastructure for AI coding agents - deterministic context packages for convergent code generation",
    no_args_is_help=True,
)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Brief - Context infrastructure for AI coding agents."""
    pass


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

# Register init as a direct command (not a subcommand)
app.command(name="init")(init_cmd.init)

# Register analyze commands as a subcommand group
app.add_typer(analyze_cmd.app, name="analyze")

# Register individual report commands at top level
app.command(name="overview")(report_cmd.overview)
app.command(name="tree")(report_cmd.tree)
app.command(name="deps")(report_cmd.deps)
app.command(name="coverage")(report_cmd.coverage_cmd)
app.command(name="stale")(report_cmd.stale)
app.command(name="inventory")(report_cmd.inventory)


# Register describe commands as a subcommand group
app.add_typer(describe_cmd.app, name="describe")


# Register context commands as a subcommand group
app.add_typer(context_cmd.app, name="context")

# Register task commands as a subcommand group
app.add_typer(task_cmd.app, name="task")

# Register memory commands as a subcommand group
app.add_typer(memory_cmd.app, name="memory")

# Register trace commands as a subcommand group
app.add_typer(trace_cmd.app, name="trace")

# Register contracts commands as a subcommand group
app.add_typer(contracts_cmd.app, name="contracts")


# Resume command - top-level for easy access
@app.command(name="resume")
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
    from .tasks.manager import TaskManager
    from .retrieval.context import build_context_for_query
    from .retrieval.search import hybrid_search

    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
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
