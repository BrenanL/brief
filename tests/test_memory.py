"""Tests for memory/pattern system."""
import pytest
from pathlib import Path
import tempfile
import shutil
from brief.memory.store import MemoryStore, match_scope
from brief.storage import write_jsonl


@pytest.fixture
def brief_path():
    """Create mock .brief directory."""
    tmp = tempfile.mkdtemp()
    brief_dir = Path(tmp) / ".brief"
    brief_dir.mkdir()
    write_jsonl(brief_dir / "memory.jsonl", [])

    yield brief_dir

    # Cleanup
    shutil.rmtree(tmp)


class TestMatchScope:
    """Tests for scope matching."""

    def test_match_scope_no_pattern(self):
        """Test empty scope matches everything."""
        assert match_scope(None, "any/path.py") is True
        assert match_scope("", "any/path.py") is True

    def test_match_scope_glob(self):
        """Test glob pattern matching."""
        assert match_scope("acme/*.py", "acme/core.py") is True
        assert match_scope("acme/*.py", "acme/api.py") is True
        assert match_scope("acme/*.py", "other/core.py") is False

    def test_match_scope_exact(self):
        """Test exact path matching."""
        assert match_scope("acme/core.py", "acme/core.py") is True
        assert match_scope("acme/core.py", "acme/api.py") is False


class TestRememberAndRecall:
    """Tests for basic remember and recall operations."""

    def test_remember_basic(self, brief_path):
        """Test storing a basic pattern."""
        store = MemoryStore(brief_path)

        record = store.remember(
            key="api/workspace",
            value="Use get_active_workspace() not get_current_workspace()"
        )

        assert record.key == "api/workspace"
        assert record.use_count == 0
        assert record.confidence == 1.0

    def test_remember_with_tags(self, brief_path):
        """Test storing a pattern with tags."""
        store = MemoryStore(brief_path)

        record = store.remember(
            key="api/workspace",
            value="Use get_active_workspace()",
            tags=["api", "workspace", "important"]
        )

        assert record.tags == ["api", "workspace", "important"]

    def test_remember_with_scope(self, brief_path):
        """Test storing a pattern with scope."""
        store = MemoryStore(brief_path)

        record = store.remember(
            key="core/pattern",
            value="Core patterns only",
            scope="acme/core/*.py"
        )

        assert record.scope == "acme/core/*.py"

    def test_recall_by_query(self, brief_path):
        """Test recalling patterns by query."""
        store = MemoryStore(brief_path)

        store.remember("api/workspace", "Workspace API pattern")
        store.remember("api/auth", "Auth pattern")
        store.remember("db/query", "Query pattern")

        results = store.recall("workspace")
        assert len(results) == 1
        assert results[0].key == "api/workspace"

    def test_recall_all(self, brief_path):
        """Test recalling all patterns."""
        store = MemoryStore(brief_path)

        store.remember("pattern1", "Value 1")
        store.remember("pattern2", "Value 2")
        store.remember("pattern3", "Value 3")

        results = store.recall()
        assert len(results) == 3

    def test_recall_by_tags(self, brief_path):
        """Test recalling patterns by tags."""
        store = MemoryStore(brief_path)

        store.remember("api/auth", "Auth pattern", tags=["api", "auth"])
        store.remember("api/workspace", "Workspace pattern", tags=["api", "workspace"])
        store.remember("db/query", "Query pattern", tags=["db"])

        results = store.recall(tags=["api"])
        assert len(results) == 2

        results = store.recall(tags=["auth"])
        assert len(results) == 1
        assert results[0].key == "api/auth"

    def test_recall_by_confidence(self, brief_path):
        """Test recalling patterns by minimum confidence."""
        store = MemoryStore(brief_path)

        store.remember("high", "High confidence", confidence=0.9)
        store.remember("medium", "Medium confidence", confidence=0.5)
        store.remember("low", "Low confidence", confidence=0.2)

        results = store.recall(min_confidence=0.5)
        assert len(results) == 2

        results = store.recall(min_confidence=0.8)
        assert len(results) == 1
        assert results[0].key == "high"


class TestGet:
    """Tests for getting specific patterns."""

    def test_get_existing(self, brief_path):
        """Test getting an existing pattern."""
        store = MemoryStore(brief_path)

        store.remember("test/key", "Test value")

        record = store.get("test/key")
        assert record is not None
        assert record.value == "Test value"

    def test_get_nonexistent(self, brief_path):
        """Test getting a non-existent pattern."""
        store = MemoryStore(brief_path)

        record = store.get("fake/key")
        assert record is None


class TestForget:
    """Tests for forgetting patterns."""

    def test_forget_existing(self, brief_path):
        """Test forgetting an existing pattern."""
        store = MemoryStore(brief_path)

        store.remember("temp/pattern", "Temporary")

        assert store.forget("temp/pattern") is True
        assert store.get("temp/pattern") is None

    def test_forget_nonexistent(self, brief_path):
        """Test forgetting a non-existent pattern."""
        store = MemoryStore(brief_path)

        assert store.forget("fake/pattern") is False


class TestBump:
    """Tests for bumping (reinforcing) patterns."""

    def test_bump_increments_count(self, brief_path):
        """Test that bump increments use count."""
        store = MemoryStore(brief_path)

        store.remember("test/pattern", "Test")

        record = store.bump("test/pattern")
        assert record.use_count == 1

        record = store.bump("test/pattern")
        assert record.use_count == 2

        record = store.bump("test/pattern")
        assert record.use_count == 3

    def test_bump_sets_last_used(self, brief_path):
        """Test that bump sets last_used timestamp."""
        store = MemoryStore(brief_path)

        store.remember("test/pattern", "Test")

        record = store.bump("test/pattern")
        assert record.last_used is not None

    def test_bump_nonexistent(self, brief_path):
        """Test bumping a non-existent pattern."""
        store = MemoryStore(brief_path)

        record = store.bump("fake/pattern")
        assert record is None


class TestListKeys:
    """Tests for listing pattern keys."""

    def test_list_all_keys(self, brief_path):
        """Test listing all keys."""
        store = MemoryStore(brief_path)

        store.remember("api/auth", "Auth")
        store.remember("api/workspace", "Workspace")
        store.remember("db/query", "Query")

        keys = store.list_keys()
        assert len(keys) == 3
        assert "api/auth" in keys
        assert "api/workspace" in keys
        assert "db/query" in keys

    def test_list_keys_with_prefix(self, brief_path):
        """Test listing keys with prefix filter."""
        store = MemoryStore(brief_path)

        store.remember("api/auth", "Auth")
        store.remember("api/workspace", "Workspace")
        store.remember("db/query", "Query")

        keys = store.list_keys(prefix="api/")
        assert len(keys) == 2
        assert "api/auth" in keys
        assert "api/workspace" in keys


class TestRecallForFile:
    """Tests for file-specific recall."""

    def test_recall_for_file_by_tags(self, brief_path):
        """Test recalling patterns relevant to a file by tags."""
        store = MemoryStore(brief_path)

        store.remember("core/workspace", "Workspace pattern", tags=["core", "workspace"])
        store.remember("api/routes", "API pattern", tags=["api"])
        store.remember("db/models", "DB pattern", tags=["db"])

        results = store.recall_for_file("acme/core/workspace.py")

        # Should match because "core" and "workspace" are in both path and tags
        assert any(r.key == "core/workspace" for r in results)

    def test_recall_for_file_with_scope(self, brief_path):
        """Test scoped patterns are filtered by file path."""
        store = MemoryStore(brief_path)

        store.remember("core/only", "Core only", scope="acme/core/*.py")
        store.remember("api/only", "API only", scope="acme/api/*.py")

        core_results = store.recall_for_file("acme/core/workspace.py")
        api_results = store.recall_for_file("acme/api/routes.py")

        # Core pattern should match core files
        assert any(r.key == "core/only" for r in core_results)
        assert not any(r.key == "api/only" for r in core_results)

        # API pattern should match API files
        assert any(r.key == "api/only" for r in api_results)
        assert not any(r.key == "core/only" for r in api_results)


class TestRecallForContext:
    """Tests for context-based recall."""

    def test_recall_for_context_by_keywords(self, brief_path):
        """Test recalling patterns by context keywords."""
        store = MemoryStore(brief_path)

        store.remember("workspace/api", "Workspace API pattern", tags=["workspace"])
        store.remember("auth/pattern", "Authentication pattern", tags=["auth"])
        store.remember("db/query", "Database query pattern", tags=["database"])

        results = store.recall_for_context(["workspace", "api"])

        assert len(results) > 0
        # The workspace pattern should score highest
        assert results[0].key == "workspace/api"

    def test_recall_for_context_scoring(self, brief_path):
        """Test that context recall uses scoring."""
        store = MemoryStore(brief_path)

        # This has "test" in key and tags
        store.remember("test/pattern", "Test pattern", tags=["test", "sample"])
        # This only has "test" in value
        store.remember("other/pattern", "A test value", tags=["other"])

        results = store.recall_for_context(["test"])

        # test/pattern should score higher (key match = 2, tag match = 2)
        # other/pattern should score lower (value match = 1)
        assert results[0].key == "test/pattern"


class TestUpdateExisting:
    """Tests for updating existing patterns."""

    def test_update_existing_pattern(self, brief_path):
        """Test that remembering same key updates the pattern."""
        store = MemoryStore(brief_path)

        store.remember("test/key", "Original value")
        store.remember("test/key", "Updated value")

        record = store.get("test/key")
        assert record.value == "Updated value"

        # Should only have one record
        all_records = store._load_all()
        assert sum(1 for r in all_records if r.key == "test/key") == 1

    def test_update_preserves_single_entry(self, brief_path):
        """Test multiple updates don't create duplicates."""
        store = MemoryStore(brief_path)

        store.remember("test/key", "Value 1")
        store.remember("test/key", "Value 2")
        store.remember("test/key", "Value 3")
        store.remember("test/key", "Value 4")

        all_records = store._load_all()
        assert len(all_records) == 1
        assert all_records[0].value == "Value 4"


class TestSorting:
    """Tests for result sorting."""

    def test_sort_by_use_count(self, brief_path):
        """Test that results are sorted by use count."""
        store = MemoryStore(brief_path)

        store.remember("pattern1", "Pattern 1")
        store.remember("pattern2", "Pattern 2")
        store.remember("pattern3", "Pattern 3")

        # Bump pattern2 twice, pattern3 once
        store.bump("pattern2")
        store.bump("pattern2")
        store.bump("pattern3")

        results = store.recall()

        assert results[0].key == "pattern2"  # Most used
        assert results[1].key == "pattern3"  # Second most used
        assert results[2].key == "pattern1"  # Least used
