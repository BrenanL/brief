# DEV_NOTES.md

**Live development notes for Brief**

This file tracks issues, ideas, and plans. Read this first when starting work.

> **For AI agents**: Do NOT delete items. Move completed/resolved items to the `## ARCHIVE` section at the bottom with a date stamp.

---

## CURRENT ISSUES

### Import Relationship Extraction Not Working
**Added**: 2026-01-22
**Status**: Open
**Severity**: Low (call relationships work, which is more important)

**Problem**: The `brief analyze` command extracts 0 import relationships. Call relationships work fine (1904+ tracked).

**Root Cause**: The `resolve_import_to_file()` function in `src/brief/analysis/relationships.py` doesn't handle relative imports (e.g., `from ..models import X`). It expects absolute module paths like `brief.models`.

**Impact**:
- Import graph is empty
- `brief deps` shows no dependencies
- Context retrieval still works via call graph

**Potential Fix**: Update `resolve_import_to_file()` to:
1. Detect relative imports (starting with `.`)
2. Resolve them relative to the importing file's location
3. Convert to absolute paths before checking if file exists

**Files**: `src/brief/analysis/relationships.py:13-40`

---

## IDEAS

### Better Dashboard / Status Overview
**Added**: 2026-01-22

Current `brief overview` and `brief context get` output is an ugly wall of text. Need better ways to get a quick sense of the project state.

**Dashboard command** (`brief status` or `brief dashboard`):
- Quick stats: files analyzed, classes, functions, call relationships
- Coverage: X/Y files have LLM descriptions, X/Y modules described
- Execution paths: N paths traced, list their names
- Memory: N patterns stored
- Config: current settings (default model, exclude patterns)
- Freshness: files changed since last analysis

**Better browsing/visualization**:
- `brief ls` or `brief browse` - interactive file browser with analysis status
- `brief tree --status` - show which files have descriptions (✓/✗ markers)
- `brief coverage --detailed` - breakdown by directory
- Compact summary mode for `context get` (just file list + stats, not full descriptions)
- `brief config show` - display current configuration clearly

**Output formatting**:
- Use tables for structured data (rich library already installed)
- Color coding for status (green=described, yellow=stale, red=missing)
- Collapsible sections or pagination for large outputs

### Lazy Context Generation
Generate descriptions on-demand during `brief context get` instead of requiring manual `brief describe` commands. Track freshness via file modification timestamps.

### Function Signatures in Context
Include function signatures (params, return types) in context packages - we collect this data but don't display it.

### Smarter Call Graph Expansion
Filter call graph expansion to only follow functions that exist in the manifest (skip stdlib/external calls like `typer.Option`).

---

## FUTURE PLANS

### v0.2 - Context Quality
- [ ] Fix import relationship extraction
- [ ] Add function signatures to context output
- [ ] Lazy description generation
- [ ] Freshness tracking for descriptions

### v0.3 - Better Search
- [ ] Improved semantic search ranking
- [ ] Search result explanations (why this file matched)
- [ ] Filter by file type/directory

### Someday/Maybe
- Support for languages other than Python
- VS Code extension
- Web UI for browsing context

---

## RECENT CHANGES

### 2026-01-22 - Initial Standalone Release
- Migrated from FlowDB/agenda to standalone `brief` package
- Renamed all references: agenda → brief, FlowDB → Acme
- Fixed `analyze all` command (was passing OptionInfo instead of Path)
- Fixed BAML client import path (now finds repo-root baml_client/)
- All 186 tests passing
- LLM descriptions working with OpenAI

---

## ARCHIVE

*Move completed items here with a date stamp*

<!-- Example:
### [RESOLVED 2026-01-22] Some issue title
Original issue description...
**Resolution**: How it was fixed
-->
