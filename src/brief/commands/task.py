"""Task management commands for Brief."""
import typer
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from ..config import get_brief_path, TASKS_FILE
from ..storage import read_json, read_jsonl, write_jsonl
from ..tasks.manager import TaskManager
from ..models import TaskStatus, TaskStepStatus

app = typer.Typer()

# Archive directory structure
ARCHIVES_DIR = "archives"
TASK_ARCHIVES_DIR = "archives/tasks"


def _check_tasks_enabled(brief_path: Path) -> bool:
    """Check if the task system is enabled in config.

    Returns True if enabled, False if disabled. Shows warning when disabled.
    """
    if not brief_path.exists():
        return True  # Let individual commands handle "not initialized" error

    config = read_json(brief_path / "config.json")
    if not config.get("enable_tasks", False):
        typer.echo("Task system is disabled in config.", err=True)
        typer.echo("To enable: brief config set enable_tasks true", err=True)
        typer.echo("", err=True)
        typer.echo("This allows using external task tools (e.g., beads) instead.", err=True)
        return False
    return True


@app.command("list")
def task_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """List all tasks.

    Shows task status, priority, and dependencies. Active task is marked with *.

    Example:
        brief task list
        brief task list --status pending
        brief task list --tag bug
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    if not _check_tasks_enabled(brief_path):
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
    """Show tasks ready to work on (no blockers).

    Lists pending tasks that have no unmet dependencies.
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    if not _check_tasks_enabled(brief_path):
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
    """Create a new task.

    Example:
        brief task create "Fix login bug"
        brief task create "Add caching" -d "Implement Redis caching" -p 80
        brief task create "Write tests" --depends ag-1234
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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

    if not _check_tasks_enabled(brief_path):
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


@app.command("clear")
def task_clear(
    done_only: bool = typer.Option(False, "--done-only", "-d", help="Only clear completed tasks"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Clear tasks from the task list.

    By default, clears ALL tasks. Use --done-only to keep pending/in-progress tasks.

    Example:
        brief task clear              # Clear all tasks (with confirmation)
        brief task clear --yes        # Clear all without confirmation
        brief task clear --done-only  # Only clear completed tasks
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    if not _check_tasks_enabled(brief_path):
        raise typer.Exit(1)

    manager = TaskManager(brief_path)
    tasks = manager.list_tasks()

    if not tasks:
        typer.echo("No tasks to clear.")
        return

    if done_only:
        tasks_to_clear = [t for t in tasks if t.status == TaskStatus.DONE]
        tasks_to_keep = [t for t in tasks if t.status != TaskStatus.DONE]
        action = f"Clear {len(tasks_to_clear)} completed tasks (keeping {len(tasks_to_keep)} active)?"
    else:
        tasks_to_clear = tasks
        tasks_to_keep = []
        action = f"Clear ALL {len(tasks_to_clear)} tasks?"

    if not tasks_to_clear:
        typer.echo("No tasks match the criteria to clear.")
        return

    if not yes:
        confirm = typer.confirm(action)
        if not confirm:
            typer.echo("Cancelled.")
            return

    # Write remaining tasks (or empty list)
    write_jsonl(brief_path / TASKS_FILE, tasks_to_keep)

    # Clear active task if we cleared all or if active task was cleared
    if not done_only:
        manager.clear_active_task()
    else:
        active = manager.get_active_task()
        if active and active.status == TaskStatus.DONE:
            manager.clear_active_task()

    typer.echo(f"Cleared {len(tasks_to_clear)} tasks.")
    if tasks_to_keep:
        typer.echo(f"Kept {len(tasks_to_keep)} tasks.")


# Archive subcommand group
archive_app = typer.Typer(help="Archive task management")
app.add_typer(archive_app, name="archive")


@archive_app.callback(invoke_without_command=True)
def archive_callback(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Archive name (default: timestamp)"),
    link: Optional[Path] = typer.Option(None, "--link", "-l", help="Link and copy a plan file to the archive"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear tasks after archiving"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation for --clear"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Archive current tasks to .brief/archives/tasks/.

    Creates a snapshot of the current tasks.jsonl file with optional metadata.
    Use --link to also copy a related plan file into the archive.

    Example:
        brief task archive                           # Archive with timestamp name
        brief task archive --name "sprint-01"        # Custom name
        brief task archive --link docs/TASK_PLAN.md  # Include plan file
        brief task archive --clear                   # Archive then clear tasks
        brief task archive list                      # List all archives
    """
    # If a subcommand was invoked, don't run the archive action
    if ctx.invoked_subcommand is not None:
        return

    # Run the archive action
    _do_archive(name=name, link=link, clear=clear, yes=yes, base=base)


def _do_archive(
    name: Optional[str],
    link: Optional[Path],
    clear: bool,
    yes: bool,
    base: Path,
) -> None:
    """Implementation of archive action."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    if not _check_tasks_enabled(brief_path):
        raise typer.Exit(1)

    manager = TaskManager(brief_path)
    tasks = manager.list_tasks()

    if not tasks:
        typer.echo("No tasks to archive.")
        return

    # Create archive directory
    archive_dir = brief_path / TASK_ARCHIVES_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Generate archive name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if name:
        archive_name = f"{timestamp}_{name}"
    else:
        archive_name = timestamp

    # Create archive files
    archive_tasks_file = archive_dir / f"{archive_name}.jsonl"
    archive_meta_file = archive_dir / f"{archive_name}.meta.json"

    # Check if archive already exists
    if archive_tasks_file.exists():
        typer.echo(f"Archive already exists: {archive_tasks_file.name}", err=True)
        raise typer.Exit(1)

    # Count task statuses
    status_counts = {
        "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
        "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
        "done": len([t for t in tasks if t.status == TaskStatus.DONE]),
        "blocked": len([t for t in tasks if t.status == TaskStatus.BLOCKED]),
    }

    # Copy tasks to archive
    shutil.copy(brief_path / TASKS_FILE, archive_tasks_file)
    typer.echo(f"Archived {len(tasks)} tasks to: {archive_tasks_file.relative_to(brief_path)}")

    # Handle linked plan file
    linked_plan_name = None
    if link:
        if not link.exists():
            typer.echo(f"Warning: Link file not found: {link}", err=True)
        else:
            # Copy plan file to archive directory with matching name
            plan_ext = link.suffix
            linked_plan_name = f"{archive_name}_plan{plan_ext}"
            archive_plan_file = archive_dir / linked_plan_name
            shutil.copy(link, archive_plan_file)
            typer.echo(f"Linked plan file: {archive_plan_file.relative_to(brief_path)}")

    # Write metadata
    import json
    meta = {
        "archived_at": datetime.now().isoformat(),
        "name": name or archive_name,
        "task_count": len(tasks),
        "status_counts": status_counts,
        "linked_plan": linked_plan_name,
        "original_plan_path": str(link) if link else None,
    }
    archive_meta_file.write_text(json.dumps(meta, indent=2))

    # Clear tasks if requested
    if clear:
        if not yes:
            confirm = typer.confirm(f"Clear all {len(tasks)} tasks after archiving?")
            if not confirm:
                typer.echo("Tasks archived but not cleared.")
                return

        write_jsonl(brief_path / TASKS_FILE, [])
        manager.clear_active_task()
        typer.echo(f"Cleared {len(tasks)} tasks.")


@archive_app.command("list")
def archive_list(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """List all task archives.

    Shows archived task snapshots with their metadata.

    Example:
        brief task archive list
    """
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    archive_dir = brief_path / TASK_ARCHIVES_DIR
    if not archive_dir.exists():
        typer.echo("No archives found.")
        return

    # Find all archive metadata files
    meta_files = sorted(archive_dir.glob("*.meta.json"))
    if not meta_files:
        typer.echo("No archives found.")
        return

    import json
    typer.echo(f"Task Archives ({len(meta_files)}):")
    typer.echo("-" * 60)

    for meta_file in meta_files:
        try:
            meta = json.loads(meta_file.read_text())
            name = meta.get("name", meta_file.stem.replace(".meta", ""))
            count = meta.get("task_count", "?")
            archived_at = meta.get("archived_at", "?")[:10]  # Just date
            status = meta.get("status_counts", {})
            done = status.get("done", 0)
            linked = meta.get("linked_plan")

            status_str = f"({done}/{count} done)"
            link_str = f" [linked: {linked}]" if linked else ""

            typer.echo(f"  {name} - {count} tasks {status_str} - {archived_at}{link_str}")
        except Exception:
            typer.echo(f"  {meta_file.stem} (error reading metadata)")
