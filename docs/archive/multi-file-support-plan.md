# Multi-File Support Implementation Plan

**Task**: ag-e49d - Add multi-file support (docs, scripts, all files)
**Status**: ✅ Complete
**Created**: 2026-01-22
**Completed**: 2026-01-22

## Overview

Extend Brief to discover and track ALL project files, not just Python. This enables searching documentation, scripts, and other files alongside code.

## Implementation Steps

### 1. MarkdownParser ✅ DONE
**File**: `src/brief/analysis/markdown.py`

- [x] Create `MarkdownParser` class
- [x] Extract title (first h1 heading)
- [x] Extract headings (h1-h4) with level and line number
- [x] Extract first paragraph for summary
- [x] Create `MarkdownFileRecord` dataclass
- [x] Add `is_dated_filename()` helper for excluding ephemeral files

### 2. Config Defaults ✅ DONE
**File**: `src/brief/config.py`

Add constants:
```python
DEFAULT_EXCLUDE = [
    ".*",              # All dot-folders
    "__pycache__",
    "node_modules",
    "*.pyc",
]

DEFAULT_DOC_INCLUDE = [
    "README.md", "CLAUDE.md", "CONTRIBUTING.md", "CHANGELOG.md",
    "docs/*.md",
    "src/**/*.md", "lib/**/*.md", "app/**/*.md",
]

DEFAULT_DOC_EXCLUDE = [
    "**/archive/**", "**/old/**", "**/deprecated/**",
    "**/status/**", "**/scratch/**", "**/draft/**",
    "**/*-session-*", "**/*-log-*",
]
```

### 3. Update Models ✅ DONE
**File**: `src/brief/models.py`

Added ManifestDocRecord model and updated ManifestFileRecord with extension/parsed fields.
```python
class ManifestDocRecord(BaseModel):
    type: Literal["doc"] = "doc"
    path: str
    extension: str
    title: str
    headings: list[str]
    file_hash: str
    first_paragraph: str | None = None
    context_ref: str | None = None  # Link to description file
    parsed: bool = True
```

Update `ManifestFileRecord`:
```python
class ManifestFileRecord(BaseModel):
    # ... existing fields ...
    extension: str  # NEW
    parsed: bool = True  # NEW - False for files we just discovered
```

### 4. Update Manifest Builder ✅ DONE
**File**: `src/brief/analysis/manifest.py`

Implemented:
- Rename `find_python_files()` → `find_files()`
- Add `find_doc_files()` for markdown with include/exclude logic
- Update `ManifestBuilder.analyze_directory()` to:
  1. Find all Python files → parse with PythonFileParser
  2. Find doc files → parse with MarkdownParser
  3. Find other files → create basic record (path, extension, hash, parsed=False)
- Add `should_include_doc()` function for doc filtering logic

### 5. Update Search/Context ✅ DONE
**File**: `src/brief/retrieval/context.py`

Implemented:
- [x] Search doc titles and headings in `search_manifest()`
- [x] Add `get_doc_context()` function for doc record retrieval
- [x] Update `build_context_for_query()` to handle doc records
- [x] Update `to_markdown()` to render docs differently (title/headings vs signatures)
- [x] Update `keyword_search()` to search doc fields

### 6. Update Coverage Command ✅ DONE
**File**: `src/brief/commands/report.py`

Implemented:
- [x] Count of doc files in output
- [x] Count of unparsed files by extension
- [x] `--unparsed` flag to list unparsed files

### 7. Tests ✅ DONE
**File**: `tests/test_markdown.py` (NEW)

Implemented 18 test cases:
- [x] Parse markdown with headings
- [x] Extract title from first h1
- [x] Handle files without h1 (use filename)
- [x] Skip h5/h6 headings
- [x] Extract first paragraph
- [x] Detect dated filenames (ISO and compact formats)
- [x] Handle empty files
- [x] Handle files with only code blocks
- [x] Additional edge cases (empty lines, headings as paragraphs, file hash)

## File Discovery Logic

```
find_all_project_files(base_path, exclude_patterns):
    for file in base_path.rglob("*"):
        if is_excluded(file, exclude_patterns):
            continue
        if file.is_dir():
            continue
        yield file

categorize_file(file_path):
    ext = file_path.suffix.lower()
    if ext == ".py":
        return "python"  # Full AST parsing
    elif ext == ".md":
        if matches_doc_include(file_path) and not matches_doc_exclude(file_path):
            return "doc"  # Heading extraction
        else:
            return "skip"  # Ephemeral doc, ignore
    elif ext in [".sh", ".bash"]:
        return "script"  # Basic parsing
    else:
        return "other"  # Just record existence
```

## Default Behavior Summary

| File Type | Default Behavior |
|-----------|------------------|
| `*.py` | Always analyze (unless excluded) |
| `README.md`, `CLAUDE.md`, etc. | Always include |
| `docs/*.md` (top-level) | Include |
| `docs/archive/**` | Exclude |
| `docs/status/**` | Exclude |
| `*-2024-01-15.md` (dated) | Exclude |
| `src/**/*.md` | Include (inline docs) |
| `.*/**` (dot folders) | Exclude |
| `.html`, `.css`, `.js`, etc. | Discover, don't parse, allow description |

## Testing the Implementation

After implementation:
```bash
# Re-analyze to pick up docs
brief analyze all

# Check coverage
brief coverage
# Should show: 54 Python, 12 docs, 8 other

# Search should find docs
brief context get "hooks configuration"
# Should return docs/hooks-setup.md

# See unparsed files
brief coverage --unparsed
```

## Notes

- Unified manifest - all file types in `manifest.jsonl`
- `type` field differentiates: "file", "class", "function", "doc"
- `parsed` field indicates if we extracted structure or just recorded existence
- Descriptions work for any file type via `brief describe file <path>`
