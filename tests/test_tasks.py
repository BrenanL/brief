"""Tests for task management."""
import pytest
from pathlib import Path
import tempfile
import shutil
from brief.tasks.manager import TaskManager, generate_task_id
from brief.models import TaskStatus
from brief.storage import write_jsonl


@pytest.fixture
def brief_path():
    """Create mock .brief directory."""
    tmp = tempfile.mkdtemp()
    brief_dir = Path(tmp) / ".brief"
    brief_dir.mkdir()
    write_jsonl(brief_dir / "tasks.jsonl", [])

    yield brief_dir

    # Cleanup
    shutil.rmtree(tmp)


class TestTaskIdGeneration:
    """Tests for task ID generation."""

    def test_generate_task_id_format(self):
        """Test task ID has correct format."""
        task_id = generate_task_id()
        assert task_id.startswith("ag-")
        assert len(task_id) == 7  # "ag-" + 4 hex chars

    def test_generate_task_id_uniqueness(self):
        """Test task IDs are unique."""
        ids = [generate_task_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique


class TestTaskCreation:
    """Tests for task creation."""

    def test_create_task_basic(self, brief_path):
        """Test creating a basic task."""
        manager = TaskManager(brief_path)

        task = manager.create_task("Test task")

        assert task.id.startswith("ag-")
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == 0

    def test_create_task_with_options(self, brief_path):
        """Test creating a task with all options."""
        manager = TaskManager(brief_path)

        task = manager.create_task(
            title="Full task",
            description="A detailed description",
            priority=5,
            tags=["important", "urgent"]
        )

        assert task.title == "Full task"
        assert task.description == "A detailed description"
        assert task.priority == 5
        assert "important" in task.tags
        assert "urgent" in task.tags

    def test_create_task_with_valid_dependency(self, brief_path):
        """Test creating a task with valid dependency."""
        manager = TaskManager(brief_path)

        parent = manager.create_task("Parent task")
        child = manager.create_task("Child task", depends=[parent.id])

        assert parent.id in child.depends

    def test_create_task_with_invalid_dependency(self, brief_path):
        """Test creating a task with invalid dependency fails."""
        manager = TaskManager(brief_path)

        with pytest.raises(ValueError, match="does not exist"):
            manager.create_task("Child task", depends=["ag-fake"])


class TestTaskQueries:
    """Tests for task queries."""

    def test_get_task(self, brief_path):
        """Test getting a task by ID."""
        manager = TaskManager(brief_path)
        task = manager.create_task("Test task")

        retrieved = manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.title == "Test task"

    def test_get_task_not_found(self, brief_path):
        """Test getting a non-existent task."""
        manager = TaskManager(brief_path)
        retrieved = manager.get_task("ag-fake")
        assert retrieved is None

    def test_list_tasks(self, brief_path):
        """Test listing all tasks."""
        manager = TaskManager(brief_path)

        manager.create_task("Task 1")
        manager.create_task("Task 2")
        manager.create_task("Task 3")

        tasks = manager.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_by_status(self, brief_path):
        """Test filtering tasks by status."""
        manager = TaskManager(brief_path)

        task1 = manager.create_task("Task 1")
        manager.create_task("Task 2")
        manager.start_task(task1.id)

        pending = manager.list_tasks(status=TaskStatus.PENDING)
        in_progress = manager.list_tasks(status=TaskStatus.IN_PROGRESS)

        assert len(pending) == 1
        assert len(in_progress) == 1

    def test_list_tasks_by_tag(self, brief_path):
        """Test filtering tasks by tag."""
        manager = TaskManager(brief_path)

        manager.create_task("Task 1", tags=["important"])
        manager.create_task("Task 2", tags=["important", "urgent"])
        manager.create_task("Task 3", tags=["normal"])

        important = manager.list_tasks(tag="important")
        urgent = manager.list_tasks(tag="urgent")

        assert len(important) == 2
        assert len(urgent) == 1


class TestTaskWorkflow:
    """Tests for task status workflow."""

    def test_start_task(self, brief_path):
        """Test starting a task."""
        manager = TaskManager(brief_path)

        task = manager.create_task("Test workflow")
        assert task.status == TaskStatus.PENDING

        task = manager.start_task(task.id)
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started is not None

    def test_complete_task(self, brief_path):
        """Test completing a task."""
        manager = TaskManager(brief_path)

        task = manager.create_task("Test workflow")
        task = manager.start_task(task.id)
        task = manager.complete_task(task.id)

        assert task.status == TaskStatus.DONE
        assert task.completed is not None

    def test_full_workflow(self, brief_path):
        """Test full task workflow: create -> start -> complete."""
        manager = TaskManager(brief_path)

        # Create
        task = manager.create_task("Full workflow test")
        assert task.status == TaskStatus.PENDING
        assert task.started is None
        assert task.completed is None

        # Start
        task = manager.start_task(task.id)
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started is not None
        assert task.completed is None

        # Complete
        task = manager.complete_task(task.id)
        assert task.status == TaskStatus.DONE
        assert task.started is not None
        assert task.completed is not None


class TestTaskDependencies:
    """Tests for task dependencies."""

    def test_get_ready_tasks_no_deps(self, brief_path):
        """Test tasks without dependencies are ready."""
        manager = TaskManager(brief_path)

        task1 = manager.create_task("Task 1")
        task2 = manager.create_task("Task 2")

        ready = manager.get_ready_tasks()
        ready_ids = [t.id for t in ready]

        assert task1.id in ready_ids
        assert task2.id in ready_ids

    def test_get_ready_tasks_with_deps(self, brief_path):
        """Test tasks with incomplete dependencies are not ready."""
        manager = TaskManager(brief_path)

        parent = manager.create_task("Parent task")
        child = manager.create_task("Child task", depends=[parent.id])

        ready = manager.get_ready_tasks()
        ready_ids = [t.id for t in ready]

        assert parent.id in ready_ids
        assert child.id not in ready_ids

    def test_get_ready_tasks_after_dep_complete(self, brief_path):
        """Test task becomes ready after dependency completes."""
        manager = TaskManager(brief_path)

        parent = manager.create_task("Parent task")
        child = manager.create_task("Child task", depends=[parent.id])

        # Before completing parent
        ready = manager.get_ready_tasks()
        assert child.id not in [t.id for t in ready]

        # Complete parent
        manager.complete_task(parent.id)

        # After completing parent
        ready = manager.get_ready_tasks()
        assert child.id in [t.id for t in ready]

    def test_get_blocked_tasks(self, brief_path):
        """Test getting blocked tasks."""
        manager = TaskManager(brief_path)

        parent = manager.create_task("Parent task")
        child = manager.create_task("Child task", depends=[parent.id])

        blocked = manager.get_blocked_tasks()

        assert len(blocked) == 1
        blocked_task, blockers = blocked[0]
        assert blocked_task.id == child.id
        assert parent.id in blockers

    def test_add_dependency(self, brief_path):
        """Test adding a dependency to existing task."""
        manager = TaskManager(brief_path)

        task1 = manager.create_task("Task 1")
        task2 = manager.create_task("Task 2")

        task2 = manager.add_dependency(task2.id, task1.id)
        assert task1.id in task2.depends

    def test_priority_ordering(self, brief_path):
        """Test ready tasks are sorted by priority."""
        manager = TaskManager(brief_path)

        low = manager.create_task("Low priority", priority=1)
        high = manager.create_task("High priority", priority=10)
        medium = manager.create_task("Medium priority", priority=5)

        ready = manager.get_ready_tasks()

        assert ready[0].id == high.id
        assert ready[1].id == medium.id
        assert ready[2].id == low.id


class TestTaskNotes:
    """Tests for task notes."""

    def test_add_note(self, brief_path):
        """Test adding a note to a task."""
        manager = TaskManager(brief_path)

        task = manager.create_task("Test notes")
        task = manager.add_note(task.id, "First note")

        assert len(task.notes) == 1
        assert "First note" in task.notes[0]

    def test_add_multiple_notes(self, brief_path):
        """Test adding multiple notes."""
        manager = TaskManager(brief_path)

        task = manager.create_task("Test notes")
        task = manager.add_note(task.id, "First note")
        task = manager.add_note(task.id, "Second note")
        task = manager.add_note(task.id, "Third note")

        assert len(task.notes) == 3


class TestTaskDeletion:
    """Tests for task deletion."""

    def test_delete_task(self, brief_path):
        """Test deleting a task."""
        manager = TaskManager(brief_path)

        task = manager.create_task("To delete")
        task_id = task.id

        result = manager.delete_task(task_id)
        assert result is True
        assert manager.get_task(task_id) is None

    def test_delete_nonexistent_task(self, brief_path):
        """Test deleting a non-existent task."""
        manager = TaskManager(brief_path)

        result = manager.delete_task("ag-fake")
        assert result is False


class TestTaskTree:
    """Tests for task dependency tree."""

    def test_get_task_tree_single(self, brief_path):
        """Test getting tree for task with no deps."""
        manager = TaskManager(brief_path)

        task = manager.create_task("Single task")
        tree = manager.get_task_tree(task.id)

        assert tree["task"].id == task.id
        assert tree["dependencies"] == []

    def test_get_task_tree_with_deps(self, brief_path):
        """Test getting tree for task with dependencies."""
        manager = TaskManager(brief_path)

        grandparent = manager.create_task("Grandparent")
        parent = manager.create_task("Parent", depends=[grandparent.id])
        child = manager.create_task("Child", depends=[parent.id])

        tree = manager.get_task_tree(child.id)

        assert tree["task"].id == child.id
        assert len(tree["dependencies"]) == 1
        assert tree["dependencies"][0]["task"].id == parent.id
        assert tree["dependencies"][0]["dependencies"][0]["task"].id == grandparent.id

    def test_get_task_tree_nonexistent(self, brief_path):
        """Test getting tree for non-existent task."""
        manager = TaskManager(brief_path)

        tree = manager.get_task_tree("ag-fake")
        assert tree == {}
