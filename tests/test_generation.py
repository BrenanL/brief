"""Tests for description generation."""
import pytest
from pathlib import Path
import tempfile
from brief.generation.generator import (
    extract_function_code,
    format_function_description,
    format_file_description,
    format_class_description,
    format_module_description,
    is_baml_available,
)
from brief.generation.types import (
    FunctionDescription,
    ClassDescription,
    FileDescription,
    ModuleDescription,
)
from brief.generation.synthesis import synthesize_spec, get_spec_stats
from brief.storage import write_jsonl


SAMPLE_CODE = '''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

def goodbye():
    pass
'''


class TestCodeExtraction:
    """Tests for code extraction utilities."""

    def test_extract_function_code(self) -> None:
        """Test extracting function code from a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(SAMPLE_CODE)

            code = extract_function_code(file_path, 2, 4)
            assert "def hello" in code
            assert "return" in code

    def test_extract_function_code_no_end_line(self) -> None:
        """Test extracting code when end_line is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(SAMPLE_CODE)

            code = extract_function_code(file_path, 2, None)
            assert "def hello" in code


class TestDescriptionTypes:
    """Tests for description type creation."""

    def test_function_description(self) -> None:
        """Test FunctionDescription dataclass."""
        desc = FunctionDescription(
            purpose="Greets a user by name",
            behavior="Constructs and returns a greeting string",
            inputs="name (str): The name to greet",
            outputs="A greeting string",
            side_effects=None
        )

        assert desc.purpose == "Greets a user by name"
        assert desc.side_effects is None

    def test_class_description(self) -> None:
        """Test ClassDescription dataclass."""
        desc = ClassDescription(
            purpose="Manages user data",
            responsibility="User data storage and retrieval",
            key_methods="get_user, save_user",
            state="Stores user dictionary",
            relationships=None
        )

        assert desc.purpose == "Manages user data"

    def test_file_description(self) -> None:
        """Test FileDescription dataclass."""
        desc = FileDescription(
            purpose="Provides user management utilities",
            contents="UserManager class, helper functions",
            role="Core user functionality",
            dependencies="Uses database module",
            exports="UserManager"
        )

        assert desc.purpose == "Provides user management utilities"

    def test_module_description(self) -> None:
        """Test ModuleDescription dataclass."""
        desc = ModuleDescription(
            purpose="Core module for the application",
            components="acme.py, registry.py, dispatch.py",
            architecture="Event-driven command dispatch",
            public_api="Acme class"
        )

        assert desc.purpose == "Core module for the application"


class TestFormatting:
    """Tests for description formatting."""

    def test_format_function_description(self) -> None:
        """Test formatting function description as markdown."""
        desc = FunctionDescription(
            purpose="Greets a user by name",
            behavior="Constructs and returns a greeting string",
            inputs="name (str): The name to greet",
            outputs="A greeting string",
            side_effects=None
        )

        markdown = format_function_description(desc)
        assert "**Purpose**:" in markdown
        assert "Greets a user" in markdown
        assert "**Behavior**:" in markdown

    def test_format_function_description_with_side_effects(self) -> None:
        """Test formatting function description with side effects."""
        desc = FunctionDescription(
            purpose="Writes to file",
            behavior="Opens file and writes content",
            inputs="path, content",
            outputs="None",
            side_effects="Creates or overwrites file"
        )

        markdown = format_function_description(desc)
        assert "**Side Effects**:" in markdown

    def test_format_class_description(self) -> None:
        """Test formatting class description as markdown."""
        desc = ClassDescription(
            purpose="Manages users",
            responsibility="User CRUD operations",
            key_methods="create, read, update, delete",
            state="User dictionary",
            relationships="Inherits from BaseManager"
        )

        markdown = format_class_description(desc)
        assert "**Purpose**:" in markdown
        assert "**Responsibility**:" in markdown
        assert "**Relationships**:" in markdown

    def test_format_file_description(self) -> None:
        """Test formatting file description as markdown."""
        desc = FileDescription(
            purpose="Main entry point",
            contents="main() function",
            role="Application startup",
            dependencies="config, utils",
            exports="main"
        )

        markdown = format_file_description(desc)
        assert "**Purpose**:" in markdown
        assert "**Contents**:" in markdown

    def test_format_module_description(self) -> None:
        """Test formatting module description as markdown."""
        desc = ModuleDescription(
            purpose="Core functionality",
            components="Several core files",
            architecture="Layered design",
            public_api="Acme class"
        )

        markdown = format_module_description(desc)
        assert "**Purpose**:" in markdown
        assert "**Architecture**:" in markdown


class TestSynthesis:
    """Tests for specification synthesis."""

    @pytest.fixture
    def mock_brief_with_context(self):
        """Create mock .brief directory with context files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / ".brief"
            brief_path.mkdir()
            context_path = brief_path / "context"
            context_path.mkdir()
            (context_path / "modules").mkdir()
            (context_path / "files").mkdir()

            # Create project description
            (context_path / "project.md").write_text("# Project Description\n\nA test project.")

            # Create module description
            (context_path / "modules" / "core.md").write_text("# Module: core\n\n**Purpose**: Core functionality")

            # Create file description
            (context_path / "files" / "main.py.md").write_text("# main.py\n\n**Purpose**: Main entry point")

            # Create manifest
            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "file", "path": "main.py", "module": "root"}
            ])

            yield brief_path, Path(tmpdir)

    def test_synthesize_spec(self, mock_brief_with_context) -> None:
        """Test synthesizing specification from context files."""
        brief_path, base_path = mock_brief_with_context
        spec = synthesize_spec(brief_path, base_path)

        assert "Project Description" in spec
        assert "Module: core" in spec
        assert "main.py" in spec

    def test_get_spec_stats(self, mock_brief_with_context) -> None:
        """Test getting spec statistics."""
        brief_path, base_path = mock_brief_with_context
        stats = get_spec_stats(brief_path)

        assert stats["has_project_description"] is True
        assert stats["module_descriptions"] == 1
        assert stats["file_descriptions"] == 1


class TestBamlAvailability:
    """Tests for BAML availability check."""

    def test_is_baml_available(self) -> None:
        """Test checking BAML availability."""
        # This should return False in test environment without BAML
        available = is_baml_available()
        assert isinstance(available, bool)
