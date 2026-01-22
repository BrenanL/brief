"""Task management commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path
from ..tasks.manager import TaskManager
from ..models import TaskStatus, TaskStepStatus

app = typer.Typer()


@app.command("list")
def task_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """List all tasks."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            typer.echo(f"Invalid status: {status}", err=True)
            raise typer.Exit(1)

    tasks = manager.list_tasks(status=status_filter, tag=tag)

    if not tasks:
        typer.echo("No tasks found.")
        return

    # Get active task for marking
    active_task = manager.get_active_task()
    active_id = active_task.id if active_task else None

    typer.echo(f"Tasks ({len(tasks)}):")
    typer.echo("-" * 60)

    for task in tasks:
        status_icon = {
            TaskStatus.PENDING: "○",
            TaskStatus.READY: "◐",
            TaskStatus.IN_PROGRESS: "●",
            TaskStatus.DONE: "✓",
            TaskStatus.BLOCKED: "⊘"
        }.get(task.status, "?")

        priority_str = f"[P{task.priority}]" if task.priority > 0 else ""
        deps_str = f"(depends: {', '.join(task.depends)})" if task.depends else ""
        active_marker = " *" if task.id == active_id else ""

        typer.echo(f"{status_icon} {task.id}: {task.title} {priority_str} {deps_str}{active_marker}")


@app.command("ready")
def task_ready(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show tasks ready to work on (no blockers)."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)
    ready = manager.get_ready_tasks()

    if not ready:
        typer.echo("No ready tasks. All tasks are either blocked, in progress, or done.")
        return

    typer.echo(f"Ready tasks ({len(ready)}):")
    typer.echo("-" * 60)

    for task in ready:
        priority_str = f"[P{task.priority}]" if task.priority > 0 else ""
        typer.echo(f"○ {task.id}: {task.title} {priority_str}")


@app.command("create")
def task_create(
    title: str = typer.Argument(..., help="Task title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    priority: int = typer.Option(0, "--priority", "-p", help="Priority (higher = more important)"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    depends: Optional[str] = typer.Option(None, "--depends", help="Comma-separated dependency IDs"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Create a new task."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    dep_list = [d.strip() for d in depends.split(",")] if depends else []

    try:
        task = manager.create_task(
            title=title,
            description=description,
            priority=priority,
            tags=tag_list,
            depends=dep_list
        )
        typer.echo(f"Created task: {task.id}")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("start")
def task_start(
    task_id: str = typer.Argument(..., help="Task ID to start"),
    steps: Optional[str] = typer.Option(None, "--steps", "-s", help="Comma-separated step names"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Mark a task as in progress and set as active.

    Example:
        brief task start ag-1234
        brief task start ag-1234 --steps "design,implement,test"
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    task = manager.start_task(task_id)
    if not task:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Started: {task.id} - {task.title}")
    typer.echo(f"  (Now the active task)")

    # Set steps if provided
    if steps:
        step_names = [s.strip() for s in steps.split(",")]
        task = manager.set_steps(task_id, step_names)
        if task:
            typer.echo(f"  Steps: {len(task.steps)}")
            for step in task.steps:
                typer.echo(f"    - {step.id}: {step.name}")


@app.command("done")
def task_done(
    task_id: str = typer.Argument(..., help="Task ID to complete"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Mark a task as complete."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    task = manager.complete_task(task_id)
    if task:
        typer.echo(f"Completed: {task.id} - {task.title}")
    else:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)


@app.command("note")
def task_note(
    task_id: str = typer.Argument(..., help="Task ID"),
    note: str = typer.Argument(..., help="Note to add"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Add a note to a task."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    task = manager.add_note(task_id, note)
    if task:
        typer.echo(f"Note added to {task_id}")
    else:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)


@app.command("show")
def task_show(
    task_id: str = typer.Argument(..., help="Task ID to show"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show details of a specific task."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    task = manager.get_task(task_id)
    if not task:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    # Check if this is the active task
    active_task = manager.get_active_task()
    is_active = active_task and active_task.id == task_id

    typer.echo(f"Task: {task.id}" + (" (ACTIVE)" if is_active else ""))
    typer.echo(f"Title: {task.title}")
    typer.echo(f"Status: {task.status.value}")
    typer.echo(f"Priority: {task.priority}")
    typer.echo(f"Created: {task.created}")

    if task.description:
        typer.echo(f"Description: {task.description}")

    if task.tags:
        typer.echo(f"Tags: {', '.join(task.tags)}")

    if task.depends:
        typer.echo(f"Depends on: {', '.join(task.depends)}")

    if task.started:
        typer.echo(f"Started: {task.started}")

    if task.completed:
        typer.echo(f"Completed: {task.completed}")

    # Show steps if present
    if task.steps:
        summary = manager.get_step_summary(task_id)
        typer.echo("")
        typer.echo(f"Steps: {summary['completed']}/{summary['total_steps']} complete ({summary['progress_percent']:.0f}%)")
        if summary['current_step']:
            typer.echo(f"Current: {summary['current_step']} - {summary['current_step_name']}")
        typer.echo("")
        for step in task.steps:
            icon = {
                "pending": "○",
                "in_progress": "◐",
                "complete": "●",
                "skipped": "⊘"
            }.get(step.status.value, "?")
            typer.echo(f"  {icon} {step.id}: {step.name}")
            if step.notes:
                typer.echo(f"      Note: {step.notes}")

    if task.notes:
        typer.echo("")
        typer.echo("Notes:")
        for note in task.notes:
            typer.echo(f"  - {note}")


@app.command("delete")
def task_delete(
    task_id: str = typer.Argument(..., help="Task ID to delete"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    task = manager.get_task(task_id)
    if not task:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete task '{task.title}'?")
        if not confirm:
            typer.echo("Cancelled.")
            return

    if manager.delete_task(task_id):
        typer.echo(f"Deleted: {task_id}")
    else:
        typer.echo(f"Failed to delete: {task_id}", err=True)


@app.command("blocked")
def task_blocked(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show tasks that are blocked by dependencies."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)
    blocked = manager.get_blocked_tasks()

    if not blocked:
        typer.echo("No blocked tasks.")
        return

    typer.echo(f"Blocked tasks ({len(blocked)}):")
    typer.echo("-" * 60)

    for task, blockers in blocked:
        typer.echo(f"⊘ {task.id}: {task.title}")
        typer.echo(f"  Blocked by: {', '.join(blockers)}")


@app.command("steps")
def task_steps(
    steps: str = typer.Argument(..., help="Comma-separated step names"),
    task_id: Optional[str] = typer.Option(None, "--task", "-t", help="Task ID (uses active task if not provided)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Set steps for a task.

    Example:
        brief task steps "design,implement,test"
        brief task steps "investigate,fix,verify" --task ag-1234
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    # Use active task if no task_id provided
    if not task_id:
        active = manager.get_active_task()
        if not active:
            typer.echo("No active task. Specify --task or start a task first.", err=True)
            raise typer.Exit(1)
        task_id = active.id

    step_names = [s.strip() for s in steps.split(",")]
    task = manager.set_steps(task_id, step_names)

    if not task:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Set {len(task.steps)} steps for {task_id}:")
    for step in task.steps:
        typer.echo(f"  - {step.id}: {step.name}")


@app.command("step-done")
def task_step_done(
    step_id: str = typer.Argument(..., help="Step ID to mark complete"),
    task_id: Optional[str] = typer.Option(None, "--task", "-t", help="Task ID (uses active task if not provided)"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Notes for this step"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Mark a step as complete.

    Example:
        brief task step-done step-1
        brief task step-done step-2 --notes "Implemented with edge case handling"
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)

    # Use active task if no task_id provided
    if not task_id:
        active = manager.get_active_task()
        if not active:
            typer.echo("No active task. Specify --task or start a task first.", err=True)
            raise typer.Exit(1)
        task_id = active.id

    task = manager.update_step(task_id, step_id, TaskStepStatus.COMPLETE, notes)

    if not task:
        typer.echo(f"Step '{step_id}' not found in task '{task_id}'", err=True)
        raise typer.Exit(1)

    typer.echo(f"Completed: {step_id}")
    if notes:
        typer.echo(f"  Notes: {notes}")

    # Show progress
    summary = manager.get_step_summary(task_id)
    if summary:
        typer.echo(f"Progress: {summary['completed']}/{summary['total_steps']} ({summary['progress_percent']:.0f}%)")
        if summary['current_step']:
            typer.echo(f"Next: {summary['current_step']} - {summary['current_step_name']}")
        elif summary['is_complete']:
            typer.echo("All steps complete!")


@app.command("active")
def task_active(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show the currently active task."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    manager = TaskManager(brief_path)
    task = manager.get_active_task()

    if not task:
        typer.echo("No active task. Start one with 'brief task start <id>'")
        return

    typer.echo(f"Active task: {task.id} - {task.title}")
    typer.echo(f"Status: {task.status.value}")

    if task.steps:
        summary = manager.get_step_summary(task.id)
        typer.echo(f"Progress: {summary['completed']}/{summary['total_steps']} steps ({summary['progress_percent']:.0f}%)")
        if summary['current_step']:
            typer.echo(f"Current step: {summary['current_step']} - {summary['current_step_name']}")

    if task.notes:
        typer.echo(f"Latest note: {task.notes[-1]}")
