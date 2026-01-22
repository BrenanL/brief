# Phase 2: Reporting & Visualization Checkpoint

## Prerequisites
- [x] Phase 1 completed (all steps marked done in phase-1.md)
- [x] `brief analyze dir acme/` produces manifest.jsonl with records
- [x] relationships.jsonl contains import relationships

## Current Status
- [x] Step 2.1: Implement `brief overview` command - COMPLETED
- [x] Step 2.2: Implement `brief tree` command - COMPLETED
- [x] Step 2.3: Implement `brief deps` command - COMPLETED
- [x] Step 2.4: Implement `brief coverage` command - COMPLETED
- [x] Step 2.5: Implement `brief stale` command - COMPLETED
- [x] Step 2.6: Implement `brief inventory` command - COMPLETED
- [x] Step 2.7: Write tests for reporting - COMPLETED

## Phase 2 Complete
All Phase 2 tasks completed successfully on 2026-01-20.
- All 10 new tests pass (49 total brief tests)
- CLI reporting commands working: overview, tree, deps, coverage, stale, inventory
- Ready for Phase 3

## Files Created
- src/brief/reporting/__init__.py
- src/brief/reporting/overview.py
- src/brief/reporting/tree.py
- src/brief/reporting/deps.py
- src/brief/reporting/coverage.py
- src/brief/commands/report.py
- tests/brief/test_reporting.py

## CLI Commands Added
- `brief overview [module]` - Show project or module overview
- `brief tree [path]` - Show project structure as tree with status
- `brief deps [file]` - Show dependencies for a file or graph summary
- `brief coverage` - Show analysis coverage statistics
- `brief stale` - Show files that changed since last analysis
- `brief inventory` - List all manifest records with filtering

---

## Implementation Notes

### overview.py
- get_module_structure() builds module breakdown from manifest
- generate_project_overview() shows totals and module list
- generate_module_overview() shows details for specific module

### tree.py
- build_tree_structure() creates nested dict from manifest
- format_tree() renders as ASCII tree with [ANALYZED]/[DESCRIBED] markers
- Supports filtering by path

### deps.py
- get_dependencies() returns imports and imported_by for a file
- generate_dependency_graph() shows most connected files
- Supports reverse mode to show what depends on a file

### coverage.py
- calculate_coverage() compares files to manifest
- find_stale_files() detects content changes via hash comparison
