# DEV_NOTES.md

**Live development notes for Brief**

This file tracks issues, ideas, and plans. Read this first when starting work.

> **For AI agents**: Do NOT delete items. Move completed/resolved items to the `## ARCHIVE` section at the bottom with a date stamp.

> **Task Plan**: See `docs/plans/TASK_PLAN_01.md` for prioritized, detailed implementation plans for these issues. Created 2025-01-23.

---

## CURRENT ISSUES

*All P0-P4 tasks from the 2026-01-23 sprint have been completed. See ARCHIVE section and CHANGELOG.md for details.*

- `[NO TASK]` figure out a good format for the claude permissions file to permit all brief commands. I'm not sure on syntax to just allow them all. *(Quick investigation, not a full task)*
- `[NO TASK]` what models are actually being used? i see usage on gpt-4o, not gpt-5-mini in my console. *(Quick investigation, not a full task)*
- `[DEFERRED]` Conditional description generation tiers - configure what files get LLM descriptions vs just analysis (e.g., skip test files by default)
- Review the .brief-logs for the latest run that executed TASK_PLAN_01.md to assess brief efficacy and look for improvements.
---

## Notes / Open Questions

### Setup Wizard - Future Enhancement
**Added**: 2026-01-23

The setup wizard (`brief setup`) could be enhanced to automatically modify the user's `CLAUDE.md` or `agent.md` file to include Brief workflow instructions. This would ensure that AI agents immediately know to use Brief for context retrieval.

**Considerations**:
- Should prompt user before modifying any file
- Should backup existing file before modifying
- Should add Brief-specific section without disturbing user's existing content
- Could offer to create the file if it doesn't exist
- Need to detect which file format the user prefers (CLAUDE.md, agent.md, etc.)

**Status**: Deferred for future implementation.

### Embeddings vs Descriptions - Clarification Needed
**Added**: 2026-01-23

The relationship between embeddings (`embeddings.db`) and descriptions (`context/files/*.md`) is not clearly documented for users. Questions that need answering:

1. **When are embeddings used vs descriptions?**
   - Descriptions are the LLM-generated human-readable file summaries
   - Embeddings are vector representations for semantic similarity search
   - Both can exist independently, but embeddings require descriptions to embed

2. **What's the value proposition of each?**
   - Descriptions: Better context for agents, human-readable summaries
   - Embeddings: Enable semantic search ("find files about authentication" vs keyword match)

3. **When should users generate each?**
   - Descriptions: Always valuable, should be auto-generated
   - Embeddings: Only needed if using semantic search mode

4. **How should we communicate this to users?**
   - Better help text on `brief context embed`
   - Clearer separation in setup wizard
   - Documentation on search modes (keyword vs semantic vs hybrid)

**Status**: Discussion item - needs UX design work before implementation.


### Execution Path Tracing - Known Limitations
The tracing system works well for functions that call other functions directly, but has these limitations:

1. **Cannot trace through class instantiation**: When code does `builder = ManifestBuilder()`, we can't follow calls to `ManifestBuilder.__init__` or trace what the constructor does. Would need to detect class instantiation and map to `__init__` methods.

2. **Cannot resolve variable-based method calls**: When code does `builder.analyze_directory()`, we see the call as `builder.analyze_directory` but can't resolve that `builder` is a `ManifestBuilder` instance. Would need type inference or runtime analysis.

3. **Entry point detection is decorator-based only**: Currently detects `@app.command`, `@app.route`, etc. Does not yet detect:
   - `if __name__ == "__main__"` blocks
   - Public API functions (non-underscore functions in `__init__.py`)

These limitations mean some traces are shorter than ideal when most calls are to class methods or external libraries. The core path through module-level functions traces well.

### Pre-Release testing `[DEFERRED]`
What tests do we need to run, and how will we design/create them to ensure that brief actually makes a difference to performance and is semi-stable for claude code usage? Lets quantify and/or qualify performance gains, and ensure that it is working in production-analagous environments before publishing fully.

### Release prep `[DEFERRED]`
what do we need to do before release? i.e. include a license file and attributions, clean up documentation and prune old docs, ensure security, no keys committed, .env.example, how to install, ease of install so you can just use instead of install as a developer, remove any developer personal information, should we squash commits to remove initial dev history to ensure no unsafe data becomes accessible, etc.

---

## IDEAS

- `[DEFERRED]` quick-consult tool. When claude code gets stuck on something, I like to switch to gemini to approach it. This involves loading up the right context (figuring out what files to copy-paste or otherwise send over) and explaining what the problem is and what todo. Instead, we have claude code call a consultant tool within brief to provide the right context package and have a conversation with gemini to figure it out. I mean, I could potentially standalone this as it's own little thing because people would find this interesting. `brief consult <prompt> <context package or keywords, etc>`

### Better Dashboard / Status Overview (Completed)
**Added**: 2026-01-22
**Completed**: 2026-01-23

**DONE**:
- [x] `brief status` dashboard with tables and color-coded metrics
- [x] `brief tree --status` with ✓/○/✗ markers for description status
- [x] Color-coded coverage percentages and freshness indicators
- [x] `brief coverage --detailed` - breakdown by directory
- [x] Compact summary mode for `context get` (`--compact` flag)
- [x] `brief config show` - display current configuration clearly
- [x] Token counting for context packages (`--tokens` flag)

**Remaining ideas (DEFERRED)**:
- `brief ls` or `brief browse` - interactive file browser with analysis status
- Collapsible sections or pagination for large outputs
- Attaching plans to tasks for better convergence
- CLI autocomplete for task IDs

---

## FUTURE PLANS

### v0.2 - Context Quality (COMPLETED 2026-01-23)
- [x] Fix import relationship extraction (DONE 2026-01-22)
- [x] Add function signatures to context output (DONE 2026-01-22)
- [x] Lazy description generation (DONE 2026-01-22)
- [x] Freshness tracking for descriptions (DONE 2026-01-22)
- [x] Auto-generate descriptions by default (DONE 2026-01-23)
- [x] Cache reset command (DONE 2026-01-23)
- [x] Setup wizard (DONE 2026-01-23)
- [x] Token counting (DONE 2026-01-23)
- [x] Compact mode (DONE 2026-01-23)

### v0.3 - Better Search `[DEFERRED]`
- [ ] Improved semantic search ranking
- [ ] Search result explanations (why this file matched)
- [ ] Filter by file type/directory

### Someday/Maybe `[DEFERRED]`
- Support for languages other than Python
- VS Code extension
- Web UI for browsing context
- Branching model for per-task branches and agents, storing patch files/diffs as context for a work item
- Sub-agent dispatching and orchestration

---

## RECENT CHANGES

### 2026-01-23 - Feature Burst (v0.2.0)

Completed 23 tasks across P0-P4 priorities plus 9 additional fixes. See CHANGELOG.md for full details.

**Infrastructure (P0)**
- Added `brief reset` with `--dry-run`, `--full`, `--include-embeddings`, `--include-user-data`
- Added command logging to `.brief-logs/`
- Verified hook and prompting effectiveness

**Core (P1)**
- Auto-generate descriptions now default (config: `auto_generate_descriptions`)
- Added `-G` flag to disable auto-generation
- LLM unavailable warning with signature fallback
- `describe batch` prioritizes src/ over tests/
- Signatures hidden when description exists (`--show-signatures` to force)
- Memory commands renamed: `remember`→`add`, `recall`→`get`
- Added `brief q "query"` shortcut
- Added top-level `brief remember`/`brief recall` aliases

**Polish (P2)**
- Improved help messages across all commands
- Redesigned `brief overview` with rich tables
- Added `brief setup` wizard (`--default` for non-interactive)
- Extended date format exclusions (ISO, American, European, etc.)
- Added `enable_tasks` config option
- Added `llm_provider` config option
- Optimized description prompts for BLUF

**Research/Docs (P3)**
- Created `docs/embeddings-architecture.md`
- Created `docs/context-package-rules.md`
- Improved embeddings UX and help text

**Dashboard (P4)**
- Added `brief config show`
- Added `--tokens` flag for token estimates
- Added `--compact` mode
- Added `brief coverage --detailed`

**Additional Fixes**
- Fixed `coverage --detailed` ANSI escape codes
- Fixed empty manifest silent failure
- Fixed demo script line endings
- Changed setup wizard flag to `--default/-d`

### 2026-01-22 - Bug Fixes and Development
- Fixed `describe batch` command (was passing OptionInfo instead of Path for `source` parameter)
  - Same root cause as the `analyze all` fix - direct CLI function calls need explicit parameter passing
- Fixed `brief coverage` command (was incorrectly computing described files count as 0)
  - Bug 1: Appending `.py` to stems that already ended in `.py` (double extension)
  - Bug 2: Simple `__` → `/` replacement broke dunder filenames like `__init__.py`
  - Fix: Use regex to properly handle dunder patterns (`____name__` → `/__name__`)
- Generated LLM descriptions for all 54 source files (100% coverage)
- **Test Harness Review**: All 186 tests pass and properly test functionality, not just existence
- **Fixed import relationship extraction**: Now properly handles relative imports
- **Added function signatures to context output**: Context packages now show signatures
- **Implemented lazy description generation**: Descriptions can now be generated on-demand
- **Implemented freshness tracking for descriptions**: Can now detect stale descriptions
- **Implemented `brief status` dashboard command**: Comprehensive project status at a glance
- **Improved output formatting with rich tables and colors**
- **Implemented smarter call graph expansion**: Now only follows internal functions
- **Restructured CLAUDE.md for better Brief workflow adoption**
- **Added Claude Code hooks for Brief reminders**

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

### [RESOLVED 2026-01-23] P0-P4 Task Sprint

All 23 tasks from the task plan have been completed:

**P0 - Infrastructure**
- P0-1: Cache Reset Command - `brief reset` with granular options
- P0-2: Development Logging - `.brief-logs/` with `command_logging` config
- P0-3: Hook Verification - Confirmed hooks work, documented in hooks-setup.md

**P1 - Core**
- P1-1: Auto-Generate Config - `auto_generate_descriptions` default true
- P1-2: LLM Unavailable Handling - Warning message, signature fallback
- P1-3: Batch Source Priority - src/ before tests/
- P1-4: Signature vs Description - Show one or the other, not both
- P1-5: Memory Rename - `add`/`get` with top-level aliases
- P1-6: Quick Shortcut - `brief q "query"` (note: `brief "query"` not feasible with Typer)

**P2 - Polish**
- P2-1: Help Quality Pass - All commands have examples
- P2-2: Overview Fix - Rich table with packages/classes
- P2-3: Setup Wizard - Interactive with `--default` flag
- P2-4: Date Formats - Multiple formats supported
- P2-5: Task Disable - `enable_tasks` config
- P2-6: Gemini Provider - `llm_provider` config, BAML docs
- P2-7: Prompt Optimization - BLUF-focused prompts

**P3 - Research**
- P3-1: Embeddings Docs - `docs/embeddings-architecture.md`
- P3-2: Embeddings UX - Improved help, `--embed` flag
- P3-3: Context Ruleset - `docs/context-package-rules.md`

**P4 - Dashboard**
- P4-1: Config Show - `brief config show`
- P4-2: Token Counting - `--tokens` flag
- P4-3: Compact Mode - `--compact` flag
- P4-4: Coverage Detailed - `--detailed` flag

### [RESOLVED 2026-01-22] Lazy Context Generation
**Original Idea**: Generate descriptions on-demand during `brief context get` instead of requiring manual `brief describe` commands.

**Resolution**: Implemented `--auto-generate` (`-g`) flag for `brief context get`. Added `generate_and_save_file_description()` helper in generator module. Descriptions are now generated lazily when needed.

### [RESOLVED 2026-01-22] Function Signatures in Context
**Original Idea**: Include function signatures (params, return types) in context packages.

**Resolution**: Added `format_function_signature()` and `format_class_signature()` helper functions. `ContextPackage.to_markdown()` now includes signatures with params, types, defaults, async/generator indicators.

### [RESOLVED 2026-01-22] Smarter Call Graph Expansion
**Original Idea**: Filter call graph expansion to only follow functions that exist in the manifest.

**Resolution**: Modified `expand_with_call_graph()` to build lookup of internal functions from manifest. Only follows calls to functions in our codebase, skipping stdlib/external calls (typer.Option, Path.exists, etc.). Returns the file where callee is defined, not just the call site.

### [RESOLVED 2026-01-22] Import Relationship Extraction Not Working
**Original Problem**: `brief analyze` extracted 0 import relationships because `resolve_import_to_file()` didn't handle relative imports (e.g., `from ..models import X`).

**Resolution**:
- Updated `parser.get_imports()` to return `(module, level, names)` tuple including the relative import level
- Updated `resolve_import_to_file()` to accept `importing_file` and `level` parameters
- For relative imports, the function now resolves paths relative to the importing file's location
- Import relationships now work: 105 imports extracted from Brief codebase (was 0)

### [RESOLVED 2026-01-22] Reporter Classes for Commands
**Original Problem**: Command files like `report.py` were doing too much work - fetching data, building visualizations, and formatting output. Commands should be thin access points; modules should be workers.

**Resolution**:
- Created `StatusReporter` class in `src/brief/reporting/status.py`
- `StatusData` dataclass holds all gathered data
- `StatusReporter.gather()` collects data from manifest, relationships, memory, tasks, freshness
- `StatusReporter.format_plain()` and `format_rich()` handle output formatting
- `status` command in `report.py` now only ~15 lines instead of ~200

### [RESOLVED 2026-01-22] Task Dependencies System Documentation
**Original Question**: How are dependencies actually working? There's a priority system, but what about when task C requires tasks A and B to be completed?

**Resolution**: The task system already has full dependency support:
- **`task.depends`**: List of task IDs that must be completed before this task
- **`get_ready_tasks()`**: Returns pending tasks with NO incomplete dependencies, sorted by priority
- **`get_blocked_tasks()`**: Returns tasks that ARE blocked and what's blocking them
- **`add_dependency(task_id, depends_on)`**: Add dependency to existing task
- **Validation**: When creating a task with `--depends`, validates all dependency IDs exist
- **CLI**: `brief task ready` shows ready tasks, `brief task blocked` shows blocked tasks
- **Active task shown**: `brief task list` marks active task with `*`

### [RESOLVED 2026-01-22] Execution Path Tracing Overhaul
**Original Problems**:
- Traces were manually created with `brief trace create`, no automation
- No way to auto-detect entry points
- Traces could become stale when code changed
- `brief trace show` showed all code fragments instead of flow diagrams
- `brief analyze all` didn't include tracing
- Help messages were confusing

**Resolution**: Complete overhaul of the tracing system:
- **Auto-detection**: Entry points detected via decorators (`@app.command`, `@app.route`, etc.)
- **Auto-creation**: `brief analyze all` now auto-creates trace definitions for all entry points
- **Dynamic regeneration**: Traces stored as metadata only; content regenerated on demand (never stale)
- **Compact flow view**: `brief trace show` displays indented call tree; `-v` for full code
- **New commands**: `list`, `show`, `define`, `update`, `delete`, `discover`
- **Depth tracking**: Call hierarchy shown with proper indentation
- **Context integration**: Traces appear in `brief context get` output under "Execution Flows"
- **Strict matching**: Prevents false positives when resolving function calls

**Known limitations** (documented in Notes section):
- Cannot trace through class instantiation
- Cannot resolve variable-based method calls
- Entry point detection is decorator-based only
