"""Tests for storage utilities."""

import pytest
from pathlib import Path
import tempfile
from brief.storage import (
    read_jsonl,
    write_jsonl,
    append_jsonl,
    read_json,
    write_json,
    read_jsonl_typed,
    update_jsonl_record,
)
from brief.models import ManifestFileRecord


class TestJSONLOperations:
    """Tests for JSONL read/write operations."""

    def test_write_read_jsonl(self) -> None:
        """Test basic JSONL write and read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            records = [{"a": 1}, {"b": 2}]

            write_jsonl(path, records)
            result = list(read_jsonl(path))

            assert result == records

    def test_read_nonexistent_file(self) -> None:
        """Test reading a nonexistent file returns empty generator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.jsonl"

            result = list(read_jsonl(path))

            assert result == []

    def test_append_jsonl(self) -> None:
        """Test appending to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"

            write_jsonl(path, [{"a": 1}])
            append_jsonl(path, {"b": 2})
            result = list(read_jsonl(path))

            assert result == [{"a": 1}, {"b": 2}]

    def test_pydantic_model_serialization(self) -> None:
        """Test writing Pydantic models to JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            record = ManifestFileRecord(path="test.py", module="test")

            write_jsonl(path, [record])
            result = list(read_jsonl(path))

            assert result[0]["path"] == "test.py"
            assert result[0]["type"] == "file"

    def test_read_jsonl_typed(self) -> None:
        """Test reading JSONL into typed Pydantic models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            record = ManifestFileRecord(path="test.py", module="test")

            write_jsonl(path, [record])
            results = list(read_jsonl_typed(path, ManifestFileRecord))

            assert len(results) == 1
            assert isinstance(results[0], ManifestFileRecord)
            assert results[0].path == "test.py"

    def test_update_jsonl_record(self) -> None:
        """Test updating a record in JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            records = [
                {"id": "1", "name": "first"},
                {"id": "2", "name": "second"},
            ]

            write_jsonl(path, records)
            updated = update_jsonl_record(path, "id", "1", {"name": "updated"})

            assert updated is True
            result = list(read_jsonl(path))
            assert result[0]["name"] == "updated"
            assert result[1]["name"] == "second"


class TestJSONOperations:
    """Tests for JSON read/write operations."""

    def test_write_read_json(self) -> None:
        """Test basic JSON write and read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            data = {"key": "value", "nested": {"a": 1}}

            write_json(path, data)
            result = read_json(path)

            assert result == data

    def test_creates_parent_directories(self) -> None:
        """Test that write operations create parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "test.json"
            data = {"key": "value"}

            write_json(path, data)

            assert path.exists()
            assert read_json(path) == data
