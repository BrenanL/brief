"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from brief.models import (
    ManifestFileRecord,
    ManifestClassRecord,
    ManifestFunctionRecord,
    ParamInfo,
    ImportRelationship,
    TaskRecord,
    TaskStatus,
    MemoryRecord,
    BriefConfig,
)


class TestManifestRecords:
    """Tests for manifest record models."""

    def test_manifest_file_record(self) -> None:
        """Test ManifestFileRecord creation and defaults."""
        record = ManifestFileRecord(
            path="acme/core/acme.py",
            module="core"
        )

        assert record.type == "file"
        assert record.path == "acme/core/acme.py"
        assert record.module == "core"
        assert record.context_ref is None
        assert record.analyzed_at is None

    def test_manifest_file_record_with_all_fields(self) -> None:
        """Test ManifestFileRecord with all fields populated."""
        now = datetime.now()
        record = ManifestFileRecord(
            path="test.py",
            module="test",
            context_ref="context/files/test.md",
            analyzed_at=now,
            file_hash="abc123"
        )

        assert record.context_ref == "context/files/test.md"
        assert record.analyzed_at == now
        assert record.file_hash == "abc123"

    def test_manifest_class_record(self) -> None:
        """Test ManifestClassRecord creation."""
        record = ManifestClassRecord(
            name="Acme",
            file="acme/core/acme.py",
            line=42,
            methods=["execute", "create_workspace"],
            bases=["object"],
        )

        assert record.type == "class"
        assert record.name == "Acme"
        assert len(record.methods) == 2
        assert "execute" in record.methods

    def test_manifest_function_record(self) -> None:
        """Test ManifestFunctionRecord creation."""
        record = ManifestFunctionRecord(
            name="execute",
            file="acme/core/acme.py",
            line=87,
            class_name="Acme",
            params=[
                ParamInfo(name="command", type_hint="str"),
                ParamInfo(name="kwargs", type_hint="dict", default="{}"),
            ],
            returns="Generator[AcmeEvent, None, None]",
            is_generator=True,
        )

        assert record.type == "function"
        assert record.name == "execute"
        assert record.class_name == "Acme"
        assert len(record.params) == 2
        assert record.is_generator is True
        assert record.is_async is False

    def test_param_info(self) -> None:
        """Test ParamInfo model."""
        param = ParamInfo(name="x", type_hint="int", default="0")

        assert param.name == "x"
        assert param.type_hint == "int"
        assert param.default == "0"


class TestRelationshipRecords:
    """Tests for relationship record models."""

    def test_import_relationship(self) -> None:
        """Test ImportRelationship creation."""
        record = ImportRelationship(
            from_file="acme/core/acme.py",
            to_file="acme/core/registry.py",
            imports=["Registry", "get_registry"],
        )

        assert record.type == "imports"
        assert record.from_file == "acme/core/acme.py"
        assert len(record.imports) == 2


class TestTaskRecord:
    """Tests for task management models."""

    def test_task_record_defaults(self) -> None:
        """Test TaskRecord with default values."""
        record = TaskRecord(id="ag-001", title="Test task")

        assert record.status == TaskStatus.PENDING
        assert record.priority == 0
        assert record.depends == []
        assert record.notes == []

    def test_task_record_full(self) -> None:
        """Test TaskRecord with all fields."""
        record = TaskRecord(
            id="ag-001",
            status=TaskStatus.IN_PROGRESS,
            title="Implement feature",
            description="Full description here",
            depends=["ag-000"],
            priority=2,
            tags=["feature", "core"],
        )

        assert record.status == TaskStatus.IN_PROGRESS
        assert record.priority == 2
        assert "feature" in record.tags


class TestMemoryRecord:
    """Tests for memory/pattern models."""

    def test_memory_record_defaults(self) -> None:
        """Test MemoryRecord with default values."""
        record = MemoryRecord(
            key="test/pattern",
            value="Use X instead of Y"
        )

        assert record.confidence == 1.0
        assert record.use_count == 0
        assert record.source == "manual"

    def test_memory_record_full(self) -> None:
        """Test MemoryRecord with all fields."""
        record = MemoryRecord(
            key="api/workspace",
            value="Use get_active_workspace()",
            tags=["api", "workspace"],
            confidence=0.9,
            source="discovered",
            scope="acme/core/*",
        )

        assert "api" in record.tags
        assert record.scope == "acme/core/*"


class TestBriefConfig:
    """Tests for configuration model."""

    def test_config_defaults(self) -> None:
        """Test BriefConfig default values."""
        config = BriefConfig()

        assert config.version == "0.1.0"
        assert config.default_model == "gpt-5-mini"
        assert config.auto_analyze is False
        assert "__pycache__" in config.exclude_patterns

    def test_config_serialization(self) -> None:
        """Test BriefConfig JSON serialization."""
        config = BriefConfig()
        json_str = config.model_dump_json()

        assert "gpt-5-mini" in json_str
        assert "exclude_patterns" in json_str
