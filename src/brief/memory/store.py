"""Memory store - Nudge-style pattern storage for Brief."""
from pathlib import Path
from datetime import datetime
from typing import Optional
import fnmatch
from ..models import MemoryRecord
from ..storage import read_jsonl, write_jsonl
from ..config import MEMORY_FILE


def match_scope(pattern_scope: str, current_path: str) -> bool:
    """Check if a pattern scope matches a path."""
    if not pattern_scope:
        return True  # No scope means global

    # Support glob patterns
    return fnmatch.fnmatch(current_path, pattern_scope)


class MemoryStore:
    """Store and retrieve patterns and conventions."""

    def __init__(self, brief_path: Path):
        self.brief_path = brief_path
        self.memory_file = brief_path / MEMORY_FILE

    def _load_all(self) -> list[MemoryRecord]:
        """Load all memory records."""
        records: list[MemoryRecord] = []
        for data in read_jsonl(self.memory_file):
            records.append(MemoryRecord.model_validate(data))
        return records

    def _save_all(self, records: list[MemoryRecord]) -> None:
        """Save all memory records."""
        write_jsonl(self.memory_file, records)

    def remember(
        self,
        key: str,
        value: str,
        tags: Optional[list[str]] = None,
        confidence: float = 1.0,
        source: str = "manual",
        scope: Optional[str] = None
    ) -> MemoryRecord:
        """Store a pattern in memory."""
        records = self._load_all()

        # Check if key exists (update) or new (create)
        existing_idx: Optional[int] = None
        for i, r in enumerate(records):
            if r.key == key:
                existing_idx = i
                break

        record = MemoryRecord(
            key=key,
            value=value,
            tags=tags or [],
            confidence=confidence,
            source=source,
            scope=scope,
            created=datetime.now()
        )

        if existing_idx is not None:
            records[existing_idx] = record
        else:
            records.append(record)

        self._save_all(records)
        return record

    def recall(
        self,
        query: Optional[str] = None,
        tags: Optional[list[str]] = None,
        scope: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> list[MemoryRecord]:
        """Recall patterns matching criteria."""
        records = self._load_all()
        results: list[MemoryRecord] = []

        for record in records:
            # Filter by confidence
            if record.confidence < min_confidence:
                continue

            # Filter by scope
            if scope and record.scope and record.scope not in scope:
                continue

            # Filter by tags
            if tags:
                if not any(t in record.tags for t in tags):
                    continue

            # Filter by query (key or value contains query)
            if query:
                query_lower = query.lower()
                if (query_lower not in record.key.lower() and
                    query_lower not in record.value.lower() and
                    not any(query_lower in t.lower() for t in record.tags)):
                    continue

            results.append(record)

        # Sort by use_count (most used first), then by confidence
        results.sort(key=lambda r: (-r.use_count, -r.confidence))

        return results

    def get(self, key: str) -> Optional[MemoryRecord]:
        """Get a specific memory by key."""
        for record in self._load_all():
            if record.key == key:
                return record
        return None

    def forget(self, key: str) -> bool:
        """Remove a pattern from memory."""
        records = self._load_all()
        original_len = len(records)

        records = [r for r in records if r.key != key]

        if len(records) < original_len:
            self._save_all(records)
            return True

        return False

    def bump(self, key: str) -> Optional[MemoryRecord]:
        """Increment use count for a pattern (reinforcement)."""
        records = self._load_all()

        for i, record in enumerate(records):
            if record.key == key:
                # Create updated record with incremented use_count
                updated = MemoryRecord(
                    key=record.key,
                    value=record.value,
                    tags=record.tags,
                    confidence=record.confidence,
                    source=record.source,
                    scope=record.scope,
                    created=record.created,
                    use_count=record.use_count + 1,
                    last_used=datetime.now()
                )
                records[i] = updated
                self._save_all(records)
                return updated

        return None

    def list_keys(self, prefix: Optional[str] = None) -> list[str]:
        """List all memory keys."""
        records = self._load_all()
        keys = [r.key for r in records]

        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]

        return sorted(keys)

    def get_by_tags(self, tags: list[str]) -> list[MemoryRecord]:
        """Get all patterns with any of the specified tags."""
        return self.recall(tags=tags)

    def recall_for_file(self, file_path: str) -> list[MemoryRecord]:
        """Get patterns relevant to a specific file."""
        records = self._load_all()
        results: list[MemoryRecord] = []

        file_parts = file_path.lower().split("/")

        for record in records:
            # Check scope match
            if record.scope and not match_scope(record.scope, file_path):
                continue

            # Check if key/tags relate to file path parts
            key_parts = record.key.lower().split("/")
            tag_match = any(
                part in record.tags or part in key_parts
                for part in file_parts
            )

            if tag_match or not record.tags:  # Include global patterns
                results.append(record)

        return results

    def recall_for_context(self, context_keywords: list[str]) -> list[MemoryRecord]:
        """Get patterns relevant to a context (list of keywords)."""
        records = self._load_all()
        scored_results: list[tuple[MemoryRecord, int]] = []

        for record in records:
            score = 0

            for keyword in context_keywords:
                keyword_lower = keyword.lower()

                # Check key
                if keyword_lower in record.key.lower():
                    score += 2

                # Check value
                if keyword_lower in record.value.lower():
                    score += 1

                # Check tags
                if any(keyword_lower in t.lower() for t in record.tags):
                    score += 2

            if score > 0:
                scored_results.append((record, score))

        # Sort by score, then by use_count
        scored_results.sort(key=lambda x: (-x[1], -x[0].use_count))

        return [r for r, _ in scored_results]
