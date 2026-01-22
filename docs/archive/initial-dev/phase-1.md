# Phase 1: Static Analysis Engine Checkpoint

## Prerequisites
- [x] Phase 0 completed (all steps marked done in phase-0.md)
- [x] Can run `poetry run brief init` successfully
- [x] Can run `poetry run brief --help`

## Current Status
- [x] Step 1.1: Implement AST parser for Python files - COMPLETED
- [x] Step 1.2: Implement manifest builder - COMPLETED
- [x] Step 1.3: Implement relationship extractor (imports) - COMPLETED
- [x] Step 1.4: Implement `brief analyze` command - COMPLETED
- [x] Step 1.5: Implement hash-based change detection - COMPLETED
- [x] Step 1.6: Implement `brief refresh` command - COMPLETED
- [x] Step 1.7: Write tests for analysis engine - COMPLETED

## Phase 1 Complete
All Phase 1 tasks completed successfully on 2026-01-20.
- All 14 new tests pass (39 total brief tests)
- CLI analyze commands working: analyze file, analyze dir, analyze all, analyze refresh
- Static analysis extracts classes, functions, imports, relationships
- Ready for Phase 2

## Files Created
- src/brief/analysis/__init__.py
- src/brief/analysis/parser.py
- src/brief/analysis/manifest.py
- src/brief/analysis/relationships.py
- src/brief/commands/analyze.py
- tests/brief/test_analysis.py

## CLI Commands Added
- `brief analyze file <path>` - Analyze single Python file
- `brief analyze dir <path>` - Analyze directory
- `brief analyze all <path>` - Analyze entire repository
- `brief analyze refresh <path>` - Re-analyze only changed files

---

## Implementation Notes

### parser.py
- Uses Python AST module for parsing
- Extracts: classes, functions (including methods), imports
- Computes MD5 file hashes for change detection
- Handles async functions and generators

### manifest.py
- ManifestBuilder collects all records from parsed files
- Respects exclude patterns (pycache, venv, etc.)
- Saves to JSONL format
- get_changed_files() for incremental analysis

### relationships.py
- RelationshipExtractor finds import relationships
- Resolves local imports to file paths
- Ignores stdlib and third-party imports
- Provides get_dependencies() and get_dependents() helpers
