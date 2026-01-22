"""Tests for contract extraction."""
import pytest
from pathlib import Path
import tempfile
import shutil
from brief.contracts.detector import ContractDetector, Contract
from brief.storage import write_jsonl


@pytest.fixture
def mock_brief():
    """Create mock .brief directory with test data."""
    tmp = tempfile.mkdtemp()
    base_path = Path(tmp)
    brief_path = base_path / ".brief"
    brief_path.mkdir()
    (brief_path / "context").mkdir()

    # Create manifest with various patterns
    write_jsonl(brief_path / "manifest.jsonl", [
        # Class naming patterns
        {"type": "class", "name": "TableCommand", "file": "commands/table.py", "line": 1, "bases": ["MetaCommand"]},
        {"type": "class", "name": "WorkspaceCommand", "file": "commands/workspace.py", "line": 1, "bases": ["MetaCommand"]},
        {"type": "class", "name": "ConfigCommand", "file": "commands/config.py", "line": 1, "bases": ["MetaCommand"]},
        {"type": "class", "name": "WorkspaceManager", "file": "managers/workspace.py", "line": 1, "bases": ["BaseManager"]},
        {"type": "class", "name": "ConfigManager", "file": "managers/config.py", "line": 1, "bases": ["BaseManager"]},
        {"type": "class", "name": "BaseManager", "file": "managers/base.py", "line": 1, "bases": []},
        {"type": "class", "name": "MetaCommand", "file": "commands/base.py", "line": 1, "bases": []},
        {"type": "class", "name": "ConnectionError", "file": "errors.py", "line": 10, "bases": ["Exception"]},
        {"type": "class", "name": "ValidationError", "file": "errors.py", "line": 20, "bases": ["Exception"]},

        # Function patterns
        {"type": "function", "name": "execute", "file": "commands/table.py", "line": 10, "is_generator": True},
        {"type": "function", "name": "execute", "file": "commands/workspace.py", "line": 10, "is_generator": True},
        {"type": "function", "name": "execute", "file": "commands/config.py", "line": 10, "is_generator": True},
        {"type": "function", "name": "get_workspace", "file": "managers/workspace.py", "line": 20},
        {"type": "function", "name": "get_config", "file": "managers/config.py", "line": 20},
        {"type": "function", "name": "test_table_command", "file": "tests/test_table.py", "line": 5},
        {"type": "function", "name": "test_workspace_command", "file": "tests/test_workspace.py", "line": 5},
        {"type": "function", "name": "test_config_command", "file": "tests/test_config.py", "line": 5},
        {"type": "function", "name": "test_create", "file": "tests/test_table.py", "line": 15},
        {"type": "function", "name": "test_delete", "file": "tests/test_table.py", "line": 25},
        {"type": "function", "name": "_private_helper", "file": "utils.py", "line": 10},
        {"type": "function", "name": "_internal_process", "file": "utils.py", "line": 20},
        {"type": "function", "name": "fetch_data", "file": "api.py", "line": 10, "is_async": True},
        {"type": "function", "name": "send_request", "file": "api.py", "line": 20, "is_async": True},

        # File organization patterns
        {"type": "file", "path": "commands/table.py", "lines": 50},
        {"type": "file", "path": "commands/workspace.py", "lines": 50},
        {"type": "file", "path": "commands/config.py", "lines": 50},
        {"type": "file", "path": "commands/definitions/table.py", "lines": 100},
        {"type": "file", "path": "managers/workspace.py", "lines": 80},
        {"type": "file", "path": "managers/config.py", "lines": 60},
        {"type": "file", "path": "managers/__init__.py", "lines": 5},
        {"type": "file", "path": "commands/__init__.py", "lines": 5},
        {"type": "file", "path": "tests/test_table.py", "lines": 40},
        {"type": "file", "path": "tests/test_workspace.py", "lines": 40},

        # Decorated functions
        {"type": "function", "name": "decorated_func1", "file": "decorators.py", "line": 10, "decorators": ["staticmethod"]},
        {"type": "function", "name": "decorated_func2", "file": "decorators.py", "line": 20, "decorators": ["staticmethod"]},
        {"type": "function", "name": "property_getter", "file": "models.py", "line": 10, "decorators": ["property"]},
        {"type": "function", "name": "another_property", "file": "models.py", "line": 20, "decorators": ["property"]},
    ])

    yield brief_path, base_path

    # Cleanup
    shutil.rmtree(tmp)


class TestContract:
    """Tests for Contract dataclass."""

    def test_contract_creation(self):
        """Test creating a contract."""
        contract = Contract(
            name="Test Contract",
            rule="Test rule",
            category="naming"
        )

        assert contract.name == "Test Contract"
        assert contract.rule == "Test rule"
        assert contract.category == "naming"
        assert contract.confidence == "medium"  # Default

    def test_contract_with_examples(self):
        """Test contract with examples."""
        contract = Contract(
            name="Command Suffix",
            rule="Commands must end with 'Command'",
            category="naming",
            examples_good=["TableCommand", "WorkspaceCommand"],
            examples_bad=["Table", "Workspace"],
            confidence="high"
        )

        assert len(contract.examples_good) == 2
        assert len(contract.examples_bad) == 2
        assert contract.confidence == "high"

    def test_contract_to_markdown(self):
        """Test converting contract to markdown."""
        contract = Contract(
            name="Test Contract",
            rule="Test rule description",
            category="naming",
            examples_good=["Good1", "Good2"],
            examples_bad=["Bad1"],
            verification="Check naming pattern",
            files_affected=["file1.py", "file2.py"],
            source="Pattern detection",
            confidence="high"
        )

        markdown = contract.to_markdown()

        assert "## Contract: Test Contract" in markdown
        assert "Test rule description" in markdown
        assert "✓ Good1" in markdown
        assert "✓ Good2" in markdown
        assert "✗ Bad1" in markdown
        assert "Check naming pattern" in markdown
        assert "`file1.py`" in markdown
        assert "Pattern detection" in markdown
        assert "**Confidence**: high" in markdown

    def test_contract_markdown_without_optional_fields(self):
        """Test markdown generation with minimal fields."""
        contract = Contract(
            name="Minimal Contract",
            rule="Simple rule",
            category="type"
        )

        markdown = contract.to_markdown()

        assert "## Contract: Minimal Contract" in markdown
        assert "Simple rule" in markdown
        assert "### Examples" not in markdown  # No examples
        assert "### Files Affected" not in markdown  # No files

    def test_contract_markdown_truncates_files(self):
        """Test that file list is truncated."""
        contract = Contract(
            name="Many Files",
            rule="Rule",
            category="organization",
            files_affected=[f"file{i}.py" for i in range(20)]
        )

        markdown = contract.to_markdown()

        assert "file0.py" in markdown
        assert "file9.py" in markdown
        # Should show truncation notice
        assert "10 more" in markdown


class TestContractDetector:
    """Tests for ContractDetector class."""

    def test_detector_creation(self, mock_brief):
        """Test creating a contract detector."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        assert detector.brief_path == brief_path
        assert detector.base_path == base_path

    def test_detect_naming_conventions(self, mock_brief):
        """Test detecting naming convention contracts."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_naming_conventions()

        # Should detect Command suffix pattern
        command_contracts = [c for c in contracts if "Command" in c.name]
        assert len(command_contracts) >= 1

        # Should detect Manager suffix pattern
        manager_contracts = [c for c in contracts if "Manager" in c.name]
        assert len(manager_contracts) >= 1

        # Should detect test_ prefix pattern
        test_contracts = [c for c in contracts if "test_" in c.name]
        assert len(test_contracts) >= 1

    def test_detect_file_organization(self, mock_brief):
        """Test detecting file organization contracts."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_file_organization()

        # Should detect commands directory pattern
        cmd_contracts = [c for c in contracts if "commands" in str(c.files_affected).lower() or "Commands" in c.name]
        assert len(cmd_contracts) >= 1

        # Should detect package structure (__init__.py)
        pkg_contracts = [c for c in contracts if "Package" in c.name]
        assert len(pkg_contracts) >= 1

    def test_detect_type_patterns(self, mock_brief):
        """Test detecting type-related contracts."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_type_patterns()

        # Should detect generator pattern
        generator_contracts = [c for c in contracts if "Generator" in c.name]
        assert len(generator_contracts) >= 1

        # Should detect async pattern
        async_contracts = [c for c in contracts if "Async" in c.name]
        assert len(async_contracts) >= 1

    def test_detect_inheritance_patterns(self, mock_brief):
        """Test detecting inheritance patterns."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_inheritance_patterns()

        # Should detect MetaCommand inheritance
        metacmd_contracts = [c for c in contracts if "MetaCommand" in c.name]
        assert len(metacmd_contracts) >= 1

        # Should detect BaseManager inheritance
        basemgr_contracts = [c for c in contracts if "BaseManager" in c.name]
        assert len(basemgr_contracts) >= 1

    def test_detect_decorator_patterns(self, mock_brief):
        """Test detecting decorator patterns."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_decorator_patterns()

        # Should detect @staticmethod pattern
        static_contracts = [c for c in contracts if "staticmethod" in c.name]
        assert len(static_contracts) >= 1

        # Should detect @property pattern
        prop_contracts = [c for c in contracts if "property" in c.name]
        assert len(prop_contracts) >= 1

    def test_detect_all(self, mock_brief):
        """Test running all detection methods."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_all()

        # Should find multiple contracts
        assert len(contracts) >= 5

        # Should have contracts from different categories
        categories = set(c.category for c in contracts)
        assert "naming" in categories
        assert "organization" in categories
        assert "type" in categories

    def test_empty_manifest(self):
        """Test handling empty manifest."""
        tmp = tempfile.mkdtemp()
        try:
            base_path = Path(tmp)
            brief_path = base_path / ".brief"
            brief_path.mkdir()

            write_jsonl(brief_path / "manifest.jsonl", [])

            detector = ContractDetector(brief_path, base_path)
            contracts = detector.detect_all()

            assert contracts == []
        finally:
            shutil.rmtree(tmp)

    def test_confidence_levels(self, mock_brief):
        """Test that confidence levels are assigned correctly."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_all()

        # Should have contracts with high confidence (3+ occurrences)
        high_confidence = [c for c in contracts if c.confidence == "high"]
        assert len(high_confidence) >= 1

        # All contracts should have valid confidence
        for contract in contracts:
            assert contract.confidence in ["low", "medium", "high"]


class TestContractCategories:
    """Test contract categories and filtering."""

    def test_naming_category(self, mock_brief):
        """Test naming category contracts."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_naming_conventions()

        for contract in contracts:
            assert contract.category == "naming"

    def test_organization_category(self, mock_brief):
        """Test organization category contracts."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_file_organization()

        for contract in contracts:
            assert contract.category == "organization"

    def test_type_category(self, mock_brief):
        """Test type category contracts."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_type_patterns()

        for contract in contracts:
            assert contract.category == "type"

    def test_behavioral_category(self, mock_brief):
        """Test behavioral category contracts (from decorators)."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_decorator_patterns()

        for contract in contracts:
            assert contract.category == "behavioral"


class TestContractSources:
    """Test contract source tracking."""

    def test_source_tracking(self, mock_brief):
        """Test that contracts track their source."""
        brief_path, base_path = mock_brief
        detector = ContractDetector(brief_path, base_path)

        contracts = detector.detect_all()

        for contract in contracts:
            assert contract.source != ""
            assert "Detected" in contract.source or "LLM" in contract.source or "manual" in contract.source


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_partial_manifest_records(self):
        """Test handling records with missing fields."""
        tmp = tempfile.mkdtemp()
        try:
            base_path = Path(tmp)
            brief_path = base_path / ".brief"
            brief_path.mkdir()

            # Records with missing optional fields
            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "class", "name": "TestClass", "file": "test.py", "line": 1},  # No bases
                {"type": "function", "name": "test_func", "file": "test.py", "line": 10},  # No is_generator
                {"type": "file", "path": "test.py"},  # Minimal file record
            ])

            detector = ContractDetector(brief_path, base_path)
            contracts = detector.detect_all()

            # Should not crash
            assert isinstance(contracts, list)
        finally:
            shutil.rmtree(tmp)

    def test_unicode_names(self):
        """Test handling unicode in names."""
        tmp = tempfile.mkdtemp()
        try:
            base_path = Path(tmp)
            brief_path = base_path / ".brief"
            brief_path.mkdir()

            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "class", "name": "UnicodeCommand", "file": "命令.py", "line": 1},
                {"type": "class", "name": "AnotherCommand", "file": "命令.py", "line": 10},
            ])

            detector = ContractDetector(brief_path, base_path)
            contracts = detector.detect_all()

            # Should handle unicode without error
            assert isinstance(contracts, list)
        finally:
            shutil.rmtree(tmp)

    def test_special_characters_in_paths(self):
        """Test handling special characters in file paths."""
        tmp = tempfile.mkdtemp()
        try:
            base_path = Path(tmp)
            brief_path = base_path / ".brief"
            brief_path.mkdir()

            write_jsonl(brief_path / "manifest.jsonl", [
                {"type": "file", "path": "path with spaces/file.py", "lines": 10},
                {"type": "file", "path": "path-with-dashes/file.py", "lines": 10},
            ])

            detector = ContractDetector(brief_path, base_path)
            contracts = detector.detect_all()

            assert isinstance(contracts, list)
        finally:
            shutil.rmtree(tmp)
