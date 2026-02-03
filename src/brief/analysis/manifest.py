"""Manifest building from analyzed files - Python, docs, and other tracked files."""
from pathlib import Path
from typing import Generator, Any
from datetime import datetime
import fnmatch
from .parser import PythonFileParser, compute_file_hash
from .markdown import MarkdownParser, is_dated_filename
from ..models import (
    ManifestFileRecord, ManifestClassRecord, ManifestFunctionRecord,
    ManifestDocRecord
)
from ..storage import read_jsonl, write_jsonl
from ..config import (
    get_brief_path, MANIFEST_FILE,
    DEFAULT_EXCLUDE_PATTERNS, DEFAULT_DOC_INCLUDE, DEFAULT_DOC_EXCLUDE,
    PARSED_EXTENSIONS, TRACKED_EXTENSIONS
)

# Type alias for manifest records
ManifestRecord = ManifestFileRecord | ManifestClassRecord | ManifestFunctionRecord | ManifestDocRecord


def should_exclude(path: Path, patterns: list[str]) -> bool:
    """Check if path matches any exclude pattern.

    Matches patterns against individual path components to avoid substring
    false positives (e.g. gitignore 'lib/' should not exclude 'libs/').
    """
    for pattern in patterns:
        # Special handling for dot-prefixed directory pattern
        if pattern == ".*":
            for part in path.parts:
                if part.startswith('.') and part != '.':
                    return True
            continue

        # Check if pattern contains glob characters
        if any(c in pattern for c in '*?['):
            # Glob pattern: match against each path component
            for part in path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        else:
            # Plain name: exact match against path components
            if pattern in path.parts:
                return True
    return False


def matches_pattern(path: Path, patterns: list[str], base_path: Path) -> bool:
    """Check if path matches any of the glob patterns."""
    rel_path = str(path.relative_to(base_path))
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if fnmatch.fnmatch(path.name, pattern):
            return True
    return False


def should_include_doc(
    path: Path,
    base_path: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None
) -> bool:
    """Determine if a markdown file should be included as documentation.

    Uses sensible defaults - includes standard doc locations, excludes
    archive/status/dated files.
    """
    include = include_patterns if include_patterns is not None else DEFAULT_DOC_INCLUDE
    exclude = exclude_patterns if exclude_patterns is not None else DEFAULT_DOC_EXCLUDE

    # Check exclude patterns first
    if matches_pattern(path, exclude, base_path):
        return False

    # Check if filename has date pattern
    if is_dated_filename(path.name):
        return False

    # Check include patterns
    return matches_pattern(path, include, base_path)


def find_python_files(
    directory: Path,
    exclude_patterns: list[str]
) -> Generator[Path, None, None]:
    """Find all Python files in directory, respecting exclude patterns."""
    for path in directory.rglob("*.py"):
        if not should_exclude(path, exclude_patterns):
            yield path


def find_doc_files(
    directory: Path,
    exclude_patterns: list[str],
    doc_include: list[str] | None = None,
    doc_exclude: list[str] | None = None
) -> Generator[Path, None, None]:
    """Find all documentation files in directory."""
    for path in directory.rglob("*.md"):
        if should_exclude(path, exclude_patterns):
            continue
        if should_include_doc(path, directory, doc_include, doc_exclude):
            yield path


def find_other_files(
    directory: Path,
    exclude_patterns: list[str]
) -> Generator[Path, None, None]:
    """Find other tracked files (not Python or docs)."""
    for path in directory.rglob("*"):
        if path.is_dir():
            continue
        if should_exclude(path, exclude_patterns):
            continue

        ext = path.suffix.lower()
        # Skip Python and markdown (handled separately)
        if ext in [".py", ".md"]:
            continue
        # Only yield if extension is in our tracked list
        if ext in TRACKED_EXTENSIONS:
            yield path


def find_all_files(
    directory: Path,
    exclude_patterns: list[str]
) -> Generator[tuple[Path, str], None, None]:
    """Find all project files, categorized by type.

    Yields: (path, category) where category is 'python', 'doc', or 'other'
    """
    for path in directory.rglob("*"):
        if path.is_dir():
            continue
        if should_exclude(path, exclude_patterns):
            continue

        ext = path.suffix.lower()
        if ext == ".py":
            yield (path, "python")
        elif ext == ".md":
            if should_include_doc(path, directory):
                yield (path, "doc")
        elif ext in TRACKED_EXTENSIONS:
            yield (path, "other")


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
        if record.get("type") in ("file", "doc"):
            existing[record["path"]] = record.get("file_hash")

    new_files: list[Path] = []
    changed_files: list[Path] = []
    current_paths: set[str] = set()

    # Check all file types
    for file_path, _ in find_all_files(base_path, exclude_patterns):
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


def ensure_manifest_current(brief_path: Path, base_path: Path) -> dict[str, int]:
    """Fast manifest sync — add new files, re-parse stale files, remove deleted.

    Lightweight check (~100ms) suitable for running before every context query.
    Handles new, changed, and deleted Python files. Does NOT rebuild
    relationships, descriptions, or embeddings — those are handled by
    'analyze refresh' via the SessionStart hook.

    Returns dict with counts: {"added": N, "updated": N, "removed": N}.
    """
    config_file = brief_path / "config.json"
    if not config_file.exists():
        return {"added": 0, "updated": 0, "removed": 0}

    from ..storage import read_json
    from ..config import load_exclude_patterns

    config = read_json(config_file)
    exclude = load_exclude_patterns(base_path, config)

    # Get Python files on disk
    disk_files = {str(f.relative_to(base_path)) for f in find_python_files(base_path, exclude)}

    # Load manifest and build lookup
    manifest_path = brief_path / MANIFEST_FILE
    manifest_records = list(read_jsonl(manifest_path))
    manifest_file_hashes: dict[str, str] = {}
    for r in manifest_records:
        if r.get('type') == 'file' and r.get('file_hash'):
            manifest_file_hashes[r['path']] = r['file_hash']

    manifest_paths = set(manifest_file_hashes.keys())

    # Detect changes
    new_files = disk_files - manifest_paths
    deleted_files = manifest_paths - disk_files
    stale_files: set[str] = set()
    for fpath in disk_files & manifest_paths:
        full_path = base_path / fpath
        if full_path.exists():
            current_hash = compute_file_hash(full_path)
            if current_hash != manifest_file_hashes.get(fpath):
                stale_files.add(fpath)

    if not new_files and not stale_files and not deleted_files:
        return {"added": 0, "updated": 0, "removed": 0}

    changed = False
    builder = ManifestBuilder(base_path, exclude)

    # Remove records for deleted and stale files (stale will be re-added)
    paths_to_remove = deleted_files | stale_files
    if paths_to_remove:
        manifest_records = [
            r for r in manifest_records
            if r.get('path') not in paths_to_remove  # file/doc records
            and r.get('file') not in paths_to_remove  # class/function records
        ]
        changed = True

    # Parse new and stale files
    files_to_parse = new_files | stale_files
    for fpath in sorted(files_to_parse):
        full_path = base_path / fpath
        if full_path.exists():
            try:
                records = builder.analyze_python_file(full_path)
                for record in records:
                    manifest_records.append(
                        record.model_dump() if hasattr(record, 'model_dump') else record
                    )
                changed = True
            except Exception:
                continue

    if changed:
        write_jsonl(manifest_path, manifest_records)

        # Regenerate lite descriptions for new/stale files
        from ..generation.lite import generate_and_save_lite_description
        for fpath in sorted(files_to_parse):
            try:
                generate_and_save_lite_description(brief_path, fpath)
            except Exception:
                continue

    return {
        "added": len(new_files),
        "updated": len(stale_files),
        "removed": len(deleted_files),
    }


class ManifestBuilder:
    """Build manifest from Python files, docs, and other tracked files."""

    def __init__(
        self,
        base_path: Path,
        exclude_patterns: list[str] | None = None,
        doc_include: list[str] | None = None,
        doc_exclude: list[str] | None = None
    ):
        self.base_path = base_path
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
        self.doc_include = doc_include  # None means use defaults
        self.doc_exclude = doc_exclude  # None means use defaults
        self.records: list[ManifestRecord] = []

    def analyze_python_file(self, file_path: Path) -> list[ManifestRecord]:
        """Analyze a single Python file and return its records."""
        parser = PythonFileParser(file_path, self.base_path)
        if not parser.parse():
            return []

        records: list[ManifestRecord] = []
        file_record = parser.get_file_record()
        # Add extension field
        file_record.extension = file_path.suffix.lower()
        records.append(file_record)
        records.extend(parser.get_classes())
        records.extend(parser.get_functions())
        return records

    def analyze_doc_file(self, file_path: Path) -> ManifestDocRecord | None:
        """Analyze a markdown file and return its record."""
        parser = MarkdownParser(file_path, self.base_path)
        if not parser.parse():
            return None

        md_record = parser.get_record()

        return ManifestDocRecord(
            path=md_record.path,
            extension=".md",
            title=md_record.title or file_path.stem,
            headings=md_record.headings,
            first_paragraph=md_record.first_paragraph,
            file_hash=md_record.file_hash,
            analyzed_at=datetime.now()
        )

    def analyze_other_file(self, file_path: Path) -> ManifestFileRecord:
        """Create a basic record for an unparsed file."""
        rel_path = str(file_path.relative_to(self.base_path))

        return ManifestFileRecord(
            type="file",
            path=rel_path,
            module=rel_path.replace("/", ".").replace("\\", "."),
            extension=file_path.suffix.lower(),
            file_hash=compute_file_hash(file_path),
            analyzed_at=datetime.now(),
            parsed=False  # Mark as not fully parsed
        )

    def analyze_directory(self, directory: Path | None = None) -> list[ManifestRecord]:
        """Analyze all files in directory - Python, docs, and other."""
        if directory is None:
            directory = self.base_path

        self.records = []

        # Analyze Python files (full parsing)
        for file_path in find_python_files(directory, self.exclude_patterns):
            self.records.extend(self.analyze_python_file(file_path))

        # Analyze documentation files (heading extraction)
        for file_path in find_doc_files(
            directory, self.exclude_patterns,
            self.doc_include, self.doc_exclude
        ):
            doc_record = self.analyze_doc_file(file_path)
            if doc_record:
                self.records.append(doc_record)

        # Track other files (basic record only)
        for file_path in find_other_files(directory, self.exclude_patterns):
            self.records.append(self.analyze_other_file(file_path))

        return self.records

    def save_manifest(self, brief_path: Path | None = None) -> None:
        """Save manifest to JSONL file."""
        if brief_path is None:
            brief_path = get_brief_path(self.base_path)

        write_jsonl(brief_path / MANIFEST_FILE, self.records)

    def get_stats(self) -> dict[str, int]:
        """Get statistics about analyzed code."""
        files = [r for r in self.records if isinstance(r, ManifestFileRecord)]
        # Python files: extension is .py OR parsed is True (default) OR no extension set (old records)
        python_files = [
            f for f in files
            if (f.extension == ".py") or (f.extension is None) or (f.parsed is True and f.extension in (None, ".py"))
        ]
        other_files = [f for f in files if f.parsed is False]
        docs = [r for r in self.records if isinstance(r, ManifestDocRecord)]
        classes = [r for r in self.records if isinstance(r, ManifestClassRecord)]
        functions = [r for r in self.records if isinstance(r, ManifestFunctionRecord)]

        return {
            "python_files": len(python_files),
            "doc_files": len(docs),
            "other_files": len(other_files),
            "classes": len(classes),
            "functions": len(functions),
            "methods": len([f for f in functions if isinstance(f, ManifestFunctionRecord) and f.class_name]),
            "module_functions": len([f for f in functions if isinstance(f, ManifestFunctionRecord) and not f.class_name]),
            # Legacy field for backwards compatibility
            "files": len(python_files),
        }
