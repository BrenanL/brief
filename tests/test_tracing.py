"""Tests for execution path tracing."""
import pytest
from pathlib import Path
import tempfile
import shutil
from brief.tracing.tracer import PathTracer, ExecutionPath, PathStep
from brief.storage import write_jsonl


@pytest.fixture
def brief_path():
    """Create mock .brief directory with test data."""
    tmp = tempfile.mkdtemp()
    base_path = Path(tmp)
    brief_dir = base_path / ".brief"
    brief_dir.mkdir()
    ( brief_dir / "context").mkdir()
    ( brief_dir / "context" / "paths").mkdir()

    # Create test manifest
    write_jsonl(brief_dir / "manifest.jsonl", [
        {
            "type": "file",
            "path": "test.py",
            "lines": 50
        },
        {
            "type": "function",
            "name": "main_func",
            "file": "test.py",
            "line": 10,
            "end_line": 15,
            "class_name": None,
            "docstring": "Main function that starts execution"
        },
        {
            "type": "function",
            "name": "helper_func",
            "file": "test.py",
            "line": 20,
            "end_line": 25,
            "class_name": None,
            "docstring": "Helper function for processing"
        },
        {
            "type": "function",
            "name": "utility",
            "file": "utils.py",
            "line": 5,
            "end_line": 10,
            "class_name": None,
            "docstring": "Utility function"
        },
        {
            "type": "function",
            "name": "process",
            "file": "processor.py",
            "line": 10,
            "class_name": "DataProcessor",
            "docstring": "Process data"
        }
    ])

    # Create test relationships
    write_jsonl(brief_dir / "relationships.jsonl", [
        {
            "type": "calls",
            "from_func": "main_func",
            "to_func": "helper_func",
            "file": "test.py",
            "line": 12
        },
        {
            "type": "calls",
            "from_func": "helper_func",
            "to_func": "utility",
            "file": "test.py",
            "line": 22
        }
    ])

    # Create test source file
    (base_path / "test.py").write_text('''"""Test module."""

def main_func():
    """Main function that starts execution"""
    result = helper_func()
    return result

def helper_func():
    """Helper function for processing"""
    data = utility()
    return data
''')

    yield brief_dir, base_path

    # Cleanup
    shutil.rmtree(tmp)


class TestPathStep:
    """Tests for PathStep dataclass."""

    def test_path_step_creation(self):
        """Test creating a path step."""
        step = PathStep(
            function="test_func",
            file="test.py",
            line=10,
            description="Test function"
        )

        assert step.function == "test_func"
        assert step.file == "test.py"
        assert step.line == 10
        assert step.calls_to == []

    def test_path_step_with_calls(self):
        """Test path step with calls list."""
        step = PathStep(
            function="main",
            file="main.py",
            line=1,
            description="Main",
            calls_to=["helper", "utility"]
        )

        assert len(step.calls_to) == 2


class TestExecutionPath:
    """Tests for ExecutionPath dataclass."""

    def test_execution_path_creation(self):
        """Test creating an execution path."""
        path = ExecutionPath(
            name="Test Path",
            description="A test execution path",
            entry_point="main_func"
        )

        assert path.name == "Test Path"
        assert path.entry_point == "main_func"
        assert path.steps == []

    def test_execution_path_to_markdown(self):
        """Test converting path to markdown."""
        path = ExecutionPath(
            name="Test Path",
            description="A test execution path",
            entry_point="test_func",
            steps=[
                PathStep(
                    function="test_func",
                    file="test.py",
                    line=10,
                    description="Does testing",
                    calls_to=["helper"]
                )
            ],
            related_files=["test.py", "helper.py"]
        )

        markdown = path.to_markdown()

        assert "# Path: Test Path" in markdown
        assert "A test execution path" in markdown
        assert "`test_func`" in markdown
        assert "test.py:10" in markdown
        assert "Does testing" in markdown
        assert "**Calls**: helper" in markdown
        assert "## Related Files" in markdown

    def test_execution_path_to_markdown_with_code_snippet(self):
        """Test markdown includes code snippet."""
        path = ExecutionPath(
            name="Code Path",
            description="Path with code",
            entry_point="func",
            steps=[
                PathStep(
                    function="func",
                    file="test.py",
                    line=1,
                    description="A function",
                    code_snippet="def func():\n    pass"
                )
            ]
        )

        markdown = path.to_markdown()

        assert "```python" in markdown
        assert "def func():" in markdown

    def test_execution_path_with_data_flow(self):
        """Test path with data flow section."""
        path = ExecutionPath(
            name="Data Path",
            description="Shows data flow",
            entry_point="process",
            data_flow="input -> transform -> output"
        )

        markdown = path.to_markdown()

        assert "## Data Flow" in markdown
        assert "input -> transform -> output" in markdown


class TestPathTracer:
    """Tests for PathTracer class."""

    def test_find_function(self, brief_path):
        """Test finding a function in manifest."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        func = tracer.find_function("main_func")
        assert func is not None
        assert func["name"] == "main_func"
        assert func["file"] == "test.py"

    def test_find_function_partial_match(self, brief_path):
        """Test finding function by partial name."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        func = tracer.find_function("helper")
        assert func is not None
        assert func["name"] == "helper_func"

    def test_find_function_not_found(self, brief_path):
        """Test finding non-existent function."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        func = tracer.find_function("nonexistent")
        assert func is None

    def test_find_function_with_class(self, brief_path):
        """Test finding class method."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        func = tracer.find_function("process")
        assert func is not None
        assert func["class_name"] == "DataProcessor"

    def test_get_callees(self, brief_path):
        """Test getting functions called by a function."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        callees = tracer.get_callees("test.py", "main_func")
        assert "helper_func" in callees

    def test_get_code_snippet(self, brief_path):
        """Test extracting code snippet."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        snippet = tracer.get_code_snippet("test.py", 3, 6)
        assert "def main_func" in snippet

    def test_get_code_snippet_missing_file(self, brief_path):
        """Test code snippet for missing file."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        snippet = tracer.get_code_snippet("nonexistent.py", 1, 5)
        assert snippet == ""


class TestTracing:
    """Tests for tracing execution paths."""

    def test_trace_from_function(self, brief_path):
        """Test tracing from a function."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        steps = tracer.trace_from_function("main_func")

        assert len(steps) >= 1
        assert steps[0].function == "main_func"
        assert steps[0].file == "test.py"

    def test_trace_follows_calls(self, brief_path):
        """Test tracing follows call relationships."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        steps = tracer.trace_from_function("main_func", max_depth=10)

        # Should include main_func and helper_func (and possibly utility)
        functions = [s.function for s in steps]
        assert "main_func" in functions
        # helper_func should be traced due to call relationship
        assert "helper_func" in functions or "helper_func" in steps[0].calls_to

    def test_trace_respects_max_depth(self, brief_path):
        """Test tracing respects max depth."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        steps = tracer.trace_from_function("main_func", max_depth=1)

        # With depth 1, should only get the entry function
        assert len(steps) == 1

    def test_create_path(self, brief_path):
        """Test creating an execution path."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        path = tracer.create_path(
            name="Test Execution",
            entry_point="main_func",
            description="Test path for main_func"
        )

        assert path.name == "Test Execution"
        assert path.entry_point == "main_func"
        assert len(path.steps) >= 1
        assert len(path.related_files) >= 1


class TestPathStorage:
    """Tests for saving and loading paths."""

    def test_save_path(self, brief_path):
        """Test saving a path."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        path = tracer.create_path("Test Path", "main_func")
        file_path = tracer.save_path(path)

        assert file_path.exists()
        assert file_path.name == "test-path.md"

        content = file_path.read_text()
        assert "# Path: Test Path" in content

    def test_list_paths(self, brief_path):
        """Test listing saved paths."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        # Save some paths
        path1 = tracer.create_path("Path One", "main_func")
        tracer.save_path(path1)

        path2 = tracer.create_path("Path Two", "helper_func")
        tracer.save_path(path2)

        paths = tracer.list_paths()

        assert len(paths) == 2
        assert "path-one" in paths
        assert "path-two" in paths

    def test_load_path(self, brief_path):
        """Test loading a saved path."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        # Save a path
        path = tracer.create_path("Load Test", "main_func")
        tracer.save_path(path)

        # Load it back
        content = tracer.load_path("load-test")

        assert content is not None
        assert "# Path: Load Test" in content

    def test_load_path_not_found(self, brief_path):
        """Test loading non-existent path."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        content = tracer.load_path("nonexistent")
        assert content is None

    def test_delete_path(self, brief_path):
        """Test deleting a path."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        # Save a path
        path = tracer.create_path("Delete Me", "main_func")
        tracer.save_path(path)

        # Verify it exists
        assert "delete-me" in tracer.list_paths()

        # Delete it
        result = tracer.delete_path("delete-me")
        assert result is True

        # Verify it's gone
        assert "delete-me" not in tracer.list_paths()

    def test_delete_path_not_found(self, brief_path):
        """Test deleting non-existent path."""
        brief_dir, base = brief_path
        tracer = PathTracer(brief_dir, base)

        result = tracer.delete_path("nonexistent")
        assert result is False
