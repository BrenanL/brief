"""Manifest building from parsed Python files."""
from pathlib import Path
from typing import Generator
import fnmatch
from .parser import PythonFileParser, compute_file_hash
from ..models import ManifestFileRecord, ManifestClassRecord, ManifestFunctionRecord
from ..storage import read_jsonl, write_jsonl
from ..config import get_brief_path, MANIFEST_FILE

# Type alias for manifest records
ManifestRecord = ManifestFileRecord | ManifestClassRecord | ManifestFunctionRecord


def should_exclude(path: Path, patterns: list[str]) -> bool:
    """Check if path matches any exclude pattern."""
    path_str = str(path)
    for pattern in patterns:
        if fnmatch.fnmatch(path_str, f"*{pattern}*"):
            return True
        if fnmatch.fnmatch(path.name, pattern):
            return True
    return False


def find_python_files(
    directory: Path,
    exclude_patterns: list[str]
) -> Generator[Path, None, None]:
    """Find all Python files in directory, respecting exclude patterns."""
    for path in directory.rglob("*.py"):
        if not should_exclude(path, exclude_patterns):
            yield path


def get_changed_files(
    base_path: Path,
    brief_path: Path,
    exclude_patterns: list[str]
) -> tuple[list[Path], list[Path], list[Path]]:
    """
    Compare current files to manifest and return (new, changed, deleted).

    Returns:
        new: Files that exist but aren't in manifest
        changed: Files that exist but hash differs
        deleted: Files in manifest but don't exist
    """
    # Load existing manifest
    existing: dict[str, str | None] = {}
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record.get("type") == "file":
            existing[record["path"]] = record.get("file_hash")

    new_files: list[Path] = []
    changed_files: list[Path] = []
    current_paths: set[str] = set()

    for file_path in find_python_files(base_path, exclude_patterns):
        rel_path = str(file_path.relative_to(base_path))
        current_paths.add(rel_path)

        if rel_path not in existing:
            new_files.append(file_path)
        elif existing[rel_path] != compute_file_hash(file_path):
            changed_files.append(file_path)

    deleted_files = [
        base_path / path for path in existing.keys()
        if path not in current_paths
    ]

    return new_files, changed_files, deleted_files


class ManifestBuilder:
    """Build manifest from Python files."""

    def __init__(self, base_path: Path, exclude_patterns: list[str] | None = None):
        self.base_path = base_path
        self.exclude_patterns = exclude_patterns or [
            "__pycache__", "*.pyc", ".git", ".venv",
            "node_modules", "baml_client"
        ]
        self.records: list[ManifestRecord] = []

    def analyze_file(self, file_path: Path) -> list[ManifestRecord]:
        """Analyze a single file and return its records."""
        parser = PythonFileParser(file_path, self.base_path)
        if not parser.parse():
            return []

        records: list[ManifestRecord] = []
        records.append(parser.get_file_record())
        records.extend(parser.get_classes())
        records.extend(parser.get_functions())
        return records

    def analyze_directory(self, directory: Path | None = None) -> list[ManifestRecord]:
        """Analyze all Python files in directory."""
        if directory is None:
            directory = self.base_path

        self.records = []
        for file_path in find_python_files(directory, self.exclude_patterns):
            self.records.extend(self.analyze_file(file_path))

        return self.records

    def save_manifest(self, brief_path: Path | None = None) -> None:
        """Save manifest to JSONL file."""
        if brief_path is None:
            brief_path = get_brief_path(self.base_path)

        write_jsonl(brief_path / MANIFEST_FILE, self.records)

    def get_stats(self) -> dict[str, int]:
        """Get statistics about analyzed code."""
        files = [r for r in self.records if r.type == "file"]
        classes = [r for r in self.records if r.type == "class"]
        functions = [r for r in self.records if r.type == "function"]

        return {
            "files": len(files),
            "classes": len(classes),
            "functions": len(functions),
            "methods": len([f for f in functions if isinstance(f, ManifestFunctionRecord) and f.class_name]),
            "module_functions": len([f for f in functions if isinstance(f, ManifestFunctionRecord) and not f.class_name])
        }
