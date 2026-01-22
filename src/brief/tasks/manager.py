"""Task management - Beads-style task tracking for Brief."""
from pathlib import Path
from datetime import datetime
from typing import Optional
import hashlib
import random
from ..models import TaskRecord, TaskStatus, TaskStep, TaskStepStatus
from ..storage import read_jsonl, write_jsonl, append_jsonl
from ..config import TASKS_FILE, ACTIVE_TASK_FILE


def generate_task_id() -> str:
    """Generate a short unique task ID like 'ag-a3f8'."""
    random_part = hashlib.md5(
        f"{datetime.now().isoformat()}{random.random()}".encode()
    ).hexdigest()[:4]
    return f"ag-{random_part}"


class TaskManager:
    """Manage tasks in brief."""

    def __init__(self, brief_path: Path):
        self.brief_path = brief_path
        self.tasks_file = brief_path / TASKS_FILE
        self.active_task_file = brief_path / ACTIVE_TASK_FILE

    def get_active_task(self) -> Optional[TaskRecord]:
        """Get the currently active task."""
        if self.active_task_file.exists():
            task_id = self.active_task_file.read_text().strip()
            return self.get_task(task_id)
        return None

    def set_active_task(self, task_id: str) -> bool:
        """Set the active task."""
        task = self.get_task(task_id)
        if task:
            self.active_task_file.write_text(task_id)
            return True
        return False

    def clear_active_task(self) -> None:
        """Clear the active task."""
        if self.active_task_file.exists():
            self.active_task_file.unlink()

    def _load_tasks(self) -> list[TaskRecord]:
        """Load all tasks from file."""
        tasks: list[TaskRecord] = []
        for record in read_jsonl(self.tasks_file):
            tasks.append(TaskRecord.model_validate(record))
        return tasks

    def _save_tasks(self, tasks: list[TaskRecord]) -> None:
        """Save all tasks to file."""
        write_jsonl(self.tasks_file, tasks)

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get a task by ID."""
        for task in self._load_tasks():
            if task.id == task_id:
                return task
        return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        tag: Optional[str] = None
    ) -> list[TaskRecord]:
        """List tasks with optional filtering."""
        tasks = self._load_tasks()

        if status:
            tasks = [t for t in tasks if t.status == status]

        if tag:
            tasks = [t for t in tasks if tag in t.tags]

        return tasks

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: int = 0,
        tags: Optional[list[str]] = None,
        depends: Optional[list[str]] = None
    ) -> TaskRecord:
        """Create a new task."""
        task = TaskRecord(
            id=generate_task_id(),
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
            depends=depends or [],
            created=datetime.now()
        )

        # Check dependencies exist
        if task.depends:
            existing_ids = {t.id for t in self._load_tasks()}
            for dep_id in task.depends:
                if dep_id not in existing_ids:
                    raise ValueError(f"Dependency {dep_id} does not exist")

        append_jsonl(self.tasks_file, task)
        return task

    def update_task(self, task_id: str, **updates) -> Optional[TaskRecord]:
        """Update a task's fields."""
        tasks = self._load_tasks()

        for i, task in enumerate(tasks):
            if task.id == task_id:
                task_dict = task.model_dump()
                task_dict.update(updates)
                tasks[i] = TaskRecord.model_validate(task_dict)
                self._save_tasks(tasks)
                return tasks[i]

        return None

    def start_task(self, task_id: str) -> Optional[TaskRecord]:
        """Mark a task as in progress and set as active."""
        task = self.update_task(
            task_id,
            status=TaskStatus.IN_PROGRESS,
            started=datetime.now()
        )
        if task:
            self.set_active_task(task_id)
        return task

    def complete_task(self, task_id: str) -> Optional[TaskRecord]:
        """Mark a task as done and clear active if this was active."""
        task = self.update_task(
            task_id,
            status=TaskStatus.DONE,
            completed=datetime.now()
        )
        if task:
            # Clear active task if this was the active one
            active = self.get_active_task()
            if active and active.id == task_id:
                self.clear_active_task()
        return task

    def add_note(self, task_id: str, note: str) -> Optional[TaskRecord]:
        """Add a note to a task."""
        task = self.get_task(task_id)
        if not task:
            return None

        notes = list(task.notes)
        notes.append(f"[{datetime.now().isoformat()}] {note}")

        return self.update_task(task_id, notes=notes)

    def add_dependency(self, task_id: str, depends_on: str) -> Optional[TaskRecord]:
        """Add a dependency to a task."""
        task = self.get_task(task_id)
        if not task:
            return None

        # Verify dependency exists
        dep_task = self.get_task(depends_on)
        if not dep_task:
            raise ValueError(f"Dependency {depends_on} does not exist")

        depends = list(task.depends)
        if depends_on not in depends:
            depends.append(depends_on)

        return self.update_task(task_id, depends=depends)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        tasks = self._load_tasks()
        original_len = len(tasks)

        tasks = [t for t in tasks if t.id != task_id]

        if len(tasks) < original_len:
            self._save_tasks(tasks)
            return True

        return False

    def get_ready_tasks(self) -> list[TaskRecord]:
        """Get tasks that have no incomplete dependencies (ready to work on)."""
        tasks = self._load_tasks()

        # Build set of incomplete task IDs
        incomplete = {
            t.id for t in tasks
            if t.status not in (TaskStatus.DONE,)
        }

        ready: list[TaskRecord] = []
        for task in tasks:
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are complete
            blocking = [d for d in task.depends if d in incomplete]
            if not blocking:
                ready.append(task)

        # Sort by priority (higher first)
        ready.sort(key=lambda t: -t.priority)

        return ready

    def get_blocked_tasks(self) -> list[tuple[TaskRecord, list[str]]]:
        """Get tasks that are blocked and what's blocking them."""
        tasks = self._load_tasks()

        # Build set of incomplete task IDs
        incomplete = {
            t.id for t in tasks
            if t.status not in (TaskStatus.DONE,)
        }

        blocked: list[tuple[TaskRecord, list[str]]] = []
        for task in tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                continue

            # Find blocking dependencies
            blocking = [d for d in task.depends if d in incomplete]
            if blocking:
                blocked.append((task, blocking))

        return blocked

    def get_task_tree(self, task_id: str) -> dict:
        """Get a task and all its dependencies as a tree."""
        task = self.get_task(task_id)
        if not task:
            return {}

        tree = {
            "task": task,
            "dependencies": []
        }

        for dep_id in task.depends:
            dep_tree = self.get_task_tree(dep_id)
            if dep_tree:
                tree["dependencies"].append(dep_tree)

        return tree

    def set_steps(
        self,
        task_id: str,
        step_names: list[str]
    ) -> Optional[TaskRecord]:
        """Set steps for a task.

        Args:
            task_id: The task ID
            step_names: List of step names

        Returns:
            Updated task or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        steps = [
            TaskStep(id=f"step-{i+1}", name=name)
            for i, name in enumerate(step_names)
        ]

        return self.update_task(
            task_id,
            steps=steps,
            current_step_id=steps[0].id if steps else None
        )

    def update_step(
        self,
        task_id: str,
        step_id: str,
        status: TaskStepStatus,
        notes: Optional[str] = None
    ) -> Optional[TaskRecord]:
        """Update a step's status.

        Args:
            task_id: The task ID
            step_id: The step ID to update
            status: New status
            notes: Optional notes for the step

        Returns:
            Updated task or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # Find and update the step
        updated_steps = []
        step_found = False
        for step in task.steps:
            if step.id == step_id:
                step_found = True
                step.status = status
                if notes:
                    step.notes = notes
                if status == TaskStepStatus.COMPLETE:
                    step.completed_at = datetime.now()
            updated_steps.append(step)

        if not step_found:
            return None

        # Determine current step (first non-complete step)
        current_step_id = None
        for step in updated_steps:
            if step.status in (TaskStepStatus.PENDING, TaskStepStatus.IN_PROGRESS):
                current_step_id = step.id
                break

        return self.update_task(
            task_id,
            steps=updated_steps,
            current_step_id=current_step_id
        )

    def get_step_summary(self, task_id: str) -> Optional[dict]:
        """Get a summary of task step progress.

        Args:
            task_id: The task ID

        Returns:
            Dict with step summary or None if not found
        """
        task = self.get_task(task_id)
        if not task or not task.steps:
            return None

        total = len(task.steps)
        completed = sum(1 for s in task.steps if s.status == TaskStepStatus.COMPLETE)
        in_progress = sum(1 for s in task.steps if s.status == TaskStepStatus.IN_PROGRESS)
        pending = sum(1 for s in task.steps if s.status == TaskStepStatus.PENDING)
        skipped = sum(1 for s in task.steps if s.status == TaskStepStatus.SKIPPED)

        current_step = None
        current_step_name = None
        if task.current_step_id:
            for step in task.steps:
                if step.id == task.current_step_id:
                    current_step = step.id
                    current_step_name = step.name
                    break

        return {
            "total_steps": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "skipped": skipped,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "current_step": current_step,
            "current_step_name": current_step_name,
            "is_complete": completed == total and total > 0
        }
