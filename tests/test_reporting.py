"""Tests for reporting functionality."""
import pytest
from pathlib import Path
import tempfile
from brief.reporting.overview import get_module_structure, generate_project_overview
from brief.reporting.tree import build_tree_structure, format_tree
from brief.reporting.deps import get_dependencies, generate_dependency_graph
from brief.reporting.coverage import calculate_coverage, find_stale_files
from brief.storage import write_jsonl, write_json


class TestOverview:
    """Tests for overview reporting."""

    @pytest.fixture
    def mock_brief(self):
        """Create mock .brief directory with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / ".brief"
            brief_path.mkdir()
            (brief_path / "context").mkdir()
            (brief_path / "context" / "modules").mkdir()
            (brief_path / "context" / "files").mkdir()

            # Create manifest
            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "file", "path": "core/main.py", "module": "core", "file_hash": "abc"},
                {"type": "file", "path": "core/utils.py", "module": "core", "file_hash": "def"},
                {"type": "class", "name": "MainClass", "file": "core/main.py", "line": 10, "methods": ["run"]},
                {"type": "function", "name": "helper", "file": "core/utils.py", "line": 5, "class_name": None},
            ])

            # Create relationships
            write_jsonl(brief_path / "relationships.jsonl", [
                {"type": "imports", "from_file": "core/main.py", "to_file": "core/utils.py", "imports": ["helper"]},
            ])

            # Create config
            write_json(brief_path / "config.json", {"exclude_patterns": []})

            yield brief_path, Path(tmpdir)

    def test_get_module_structure(self, mock_brief) -> None:
        """Test extracting module structure from manifest."""
        brief_path, base_path = mock_brief
        modules = get_module_structure(brief_path)

        assert "core" in modules
        assert len(modules["core"]["files"]) == 2
        assert len(modules["core"]["classes"]) == 1

    def test_generate_project_overview(self, mock_brief) -> None:
        """Test generating project overview."""
        brief_path, base_path = mock_brief
        # Use plain text mode for testing
        output = generate_project_overview(brief_path, use_rich=False)

        # Check for package structure in plain text output
        assert "Project Architecture" in output
        assert "core" in output


class TestTree:
    """Tests for tree visualization."""

    @pytest.fixture
    def mock_brief(self):
        """Create mock .brief directory with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / ".brief"
            brief_path.mkdir()

            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "file", "path": "core/main.py", "file_hash": "abc"},
                {"type": "file", "path": "core/utils.py", "file_hash": "def"},
                {"type": "file", "path": "utils/helpers.py", "file_hash": "ghi"},
            ])

            yield brief_path, Path(tmpdir)

    def test_build_tree_structure(self, mock_brief) -> None:
        """Test building tree structure from manifest."""
        brief_path, base_path = mock_brief
        tree = build_tree_structure(brief_path, base_path)

        assert "core" in tree
        assert "main.py" in tree["core"]
        assert "utils" in tree

    def test_format_tree(self, mock_brief) -> None:
        """Test formatting tree as text."""
        brief_path, base_path = mock_brief
        tree = build_tree_structure(brief_path, base_path)
        lines = format_tree(tree)

        # Should have directory and file entries
        assert any("core/" in line for line in lines)
        assert any("main.py" in line for line in lines)


class TestDependencies:
    """Tests for dependency reporting."""

    @pytest.fixture
    def mock_brief(self):
        """Create mock .brief directory with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / ".brief"
            brief_path.mkdir()

            write_jsonl(brief_path / "relationships.jsonl", [
                {"type": "imports", "from_file": "a.py", "to_file": "b.py", "imports": ["foo"]},
                {"type": "imports", "from_file": "c.py", "to_file": "b.py", "imports": ["bar"]},
                {"type": "imports", "from_file": "a.py", "to_file": "d.py", "imports": ["baz"]},
            ])

            yield brief_path, Path(tmpdir)

    def test_get_dependencies(self, mock_brief) -> None:
        """Test getting dependencies for a file."""
        brief_path, base_path = mock_brief
        deps = get_dependencies(brief_path, "a.py")

        assert len(deps["imports"]) == 2
        assert deps["imports"][0]["file"] == "b.py"

    def test_get_reverse_dependencies(self, mock_brief) -> None:
        """Test getting reverse dependencies."""
        brief_path, base_path = mock_brief
        deps = get_dependencies(brief_path, "b.py")

        assert len(deps["imported_by"]) == 2
        assert "a.py" in [d["file"] for d in deps["imported_by"]]
        assert "c.py" in [d["file"] for d in deps["imported_by"]]

    def test_generate_dependency_graph(self, mock_brief) -> None:
        """Test generating dependency graph summary."""
        brief_path, base_path = mock_brief
        output = generate_dependency_graph(brief_path)

        assert "Total import relationships: 3" in output
        assert "b.py" in output  # Most depended on


class TestCoverage:
    """Tests for coverage reporting."""

    @pytest.fixture
    def mock_project(self):
        """Create mock project with .brief directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            brief_path = base_path / ".brief"
            brief_path.mkdir()
            (brief_path / "context").mkdir()
            (brief_path / "context" / "files").mkdir()

            # Create actual Python files
            (base_path / "analyzed.py").write_text("# analyzed file")
            (base_path / "not_analyzed.py").write_text("# not analyzed")

            # Create manifest with only one file analyzed
            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "file", "path": "analyzed.py", "file_hash": "abc"},
            ])

            write_json(brief_path / "config.json", {"exclude_patterns": ["__pycache__"]})

            yield brief_path, base_path

    def test_calculate_coverage(self, mock_project) -> None:
        """Test calculating coverage statistics."""
        brief_path, base_path = mock_project
        cov = calculate_coverage(brief_path, base_path, ["__pycache__"])

        assert cov["total_files"] == 2
        assert cov["analyzed_files"] == 1
        assert "not_analyzed.py" in cov["not_analyzed"]


class TestStaleFiles:
    """Tests for stale file detection."""

    @pytest.fixture
    def mock_project(self):
        """Create mock project with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            brief_path = base_path / ".brief"
            brief_path.mkdir()

            # Create a file
            test_file = base_path / "test.py"
            test_file.write_text("original content")

            # Analyze it (capture hash)
            from brief.analysis.parser import compute_file_hash
            original_hash = compute_file_hash(test_file)

            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "file", "path": "test.py", "file_hash": original_hash, "analyzed_at": "2024-01-01"},
            ])

            yield brief_path, base_path, test_file

    def test_find_stale_files_none(self, mock_project) -> None:
        """Test no stale files when content unchanged."""
        brief_path, base_path, test_file = mock_project
        stale = find_stale_files(brief_path, base_path)

        assert len(stale) == 0

    def test_find_stale_files_changed(self, mock_project) -> None:
        """Test stale file detection when content changed."""
        brief_path, base_path, test_file = mock_project

        # Modify the file
        test_file.write_text("modified content")

        stale = find_stale_files(brief_path, base_path)

        assert len(stale) == 1
        assert stale[0]["path"] == "test.py"
