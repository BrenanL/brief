# DEV_NOTES.md

**Live development notes for Brief**

This file tracks issues, ideas, and plans. Read this first when starting work.

> **For AI agents**: Do NOT delete items. Move completed/resolved items to the `## ARCHIVE` section at the bottom with a date stamp.

---

## CURRENT ISSUES

- need to do more robust testing on when and how the agents are actually using brief. I'm not convinced the prompting and hooks are sufficient right now to constrain/encourage usage. The pre-tool call hook may not actually be going to the agent, and instead just to the ui of claude code
- context.py, the autogenerate descriptions thing, can have a flag to force doing this, but should also be a config behavior. I want default to be yes, generate. It is unreasonable to have to remember to type in flags each time if you want fresh context. 
- how are embeddings actually generated, like what command does it, how do we make this feel better or be easier to use. 
- need a pass on our rulesets for context package generation. Ideally, we will make this configurable at some point, so users can decide what a good context package looks like. For now, we need to define things like: how many files to return? should we limit the number, or should the number inherently be different based on what you're looking for? what proximity for embedding search is relevant? Should we refine search terms before embedding search (as in, generate multiple sentences to cover different solution spaces around the query, and vector search for each)? how to verify what execution pipelines we return? what exactly are we returning, is it important/necessary, are we not returning something we should? how much of what could go in a context package is not yet implemented in brief? can we better BLUF the context packages (gen an llm summary of the package to put at top, list an index of what is in the context package, etc)?
- in doc exclude config, what about date/time formats other than YYYY-MM-DD?
- define a default behavior for using brief. I like the default to be getting a context package. So running `brief "add logging to execution tracing"` would just give me the context package. Essentially, set it up as a shortcut for `brief context get`, we can set the shortcut to do something else in the future if we want
- Let's add google gemini as a provider for our llm work. Then we can run some side-by-side tests for descriptions from a couple openai models, a couple gemini models, and claude to pick a default. Then we can also make this an optional override in the config file.
- need a test pass on prompting for description generation. should we have conditionals, as in by filetype, etc for what prompt we should use? what provides the best BLUF and agent steering in a description, how do our prompts achieve that?
- the relationship between embeddings.db and our context/files/ and when they are used is not fully clear to me. We need an analysis of how they are both currently used, how they are used together, and how we should best use them both. 
- how should we handle tests? if there is a test/ directory, do we want to brief index them the same way as other code? or instead give overviews of what is in the test dir? what benefit comes from indexing tests, and what drawbacks come from not indexing them?
- consider some mode for disabline the task stuff, to use an alternative like beads and not have confusion with the two systems. 
- `brief overview` is pretty bad, very unreadable and not good looking. Not sure what it is trying to communicate either, what should this actually do?
- how can we set this up to automate the documentation generated, or lazy load, etc. From the perspective of first time use, you init, you analyze, then you `brief context get`. Any time I use it, I want there to be descriptions with those files. Right now, the user has no idea of 1. the concept of file descriptions and how they would be used by brief or by agents and 2. if the context package will have descriptions. Particularly difficult when it is just an agent doing the calling, and the user never runs `context get`. 
- a setup wizard, so give me a few questions and it will run the commands/setup needed. An example is to just ask "do you want to generate file descriptions automatically?" and if yes, then any time a file is either used as context for the first time, or if stale, it will auto-gen the llm description for it. 
- no indication on llm not available. Also, what are the placeholders? Placeholders would hurt context. It's one thing to give all of the function names rather than a description, another if it is "insert description here"
```
# 12. Generate descriptions (uses placeholder without BAML/LLM)
  brief describe batch --limit 5
```
- `brief memory remember <key> <value>` and `brief memory recall <key>` are very cumbersome. instead we want `brief memory add <> <>` and `brief memory get <>`. I like the idea of aliasing these two as well, so you can optionally do `brief remember <key> <value>` and `brief recall <key>`.
- need a method of clearing and re-generating all of the brief 'cache' files without damaging the descriptions, summaries, etc. The analyzed etc files are 'free' and the llm-generated ones cost money (and more time). So clearing and re-analyzing should be easy. this is also nice for dev and for rolling out updates when we change how the files work etc.
- Not sure how it works right now, but for file context in the context package, I like the idea of returning the signatures if no description/summary, but not returning both the description and signatures. Too much if we do that.
- the help messages from the `brief trace` branch of commands are now great. Let's go through every other command in here and get them all up to the same quality.
- running `brief describe batch` is always generating descriptions for test files first. Maybe it has to do with the ordering, but it feels weird becasue no one cares about descriptions for test files. I actually want the default behavior to be not to describe test files, and something you can put an optional param config in to have it do. 
- figure out a good format for the claude permissions file to permit all brief commands. I'm not sure on syntax to just allow them all. 
- what models are actually being used? i see usage on gpt-4o, not gpt-5-mini in my console. 
---
## Notes / Open Questions

### Execution Path Tracing - Known Limitations
The tracing system works well for functions that call other functions directly, but has these limitations:

1. **Cannot trace through class instantiation**: When code does `builder = ManifestBuilder()`, we can't follow calls to `ManifestBuilder.__init__` or trace what the constructor does. Would need to detect class instantiation and map to `__init__` methods.

2. **Cannot resolve variable-based method calls**: When code does `builder.analyze_directory()`, we see the call as `builder.analyze_directory` but can't resolve that `builder` is a `ManifestBuilder` instance. Would need type inference or runtime analysis.

3. **Entry point detection is decorator-based only**: Currently detects `@app.command`, `@app.route`, etc. Does not yet detect:
   - `if __name__ == "__main__"` blocks
   - Public API functions (non-underscore functions in `__init__.py`)

These limitations mean some traces are shorter than ideal when most calls are to class methods or external libraries. The core path through module-level functions traces well.

### Pre-Release testing
What tests do we need to run, and how will we design/create them to ensure that brief actually makes a difference to performance and is semi-stable for claude code usage? Lets quantify and/or qualify performance gains, and ensure that it is working in production-analagous environments before publishing fully. 

### Release prep
what do we need to do before release? i.e. include a license file and attributions, clean up documentation and prune old docs, ensure security, no keys committed, .env.example, how to install, ease of install so you can just use instead of install as a developer, remove any developer personal information, should we squash commits to remove initial dev history to ensure no unsafe data becomes accessible, etc. 
---

## IDEAS

- quick-consult tool. When claude code gets stuck on something, I like to switch to gemini to approach it. This involves loading up the right context (figuring out what files to copy-paste or otherwise send over) and explaining what the problem is and what todo. Instead, we have claude code call a consultant tool within brief to provide the right context package and have a conversation with gemini to figure it out. I mean, I could potentially standalone this as it's own little thing because people would find this interesting. `brief consult <prompt> <context package or keywords, etc>`

### Logging for development
I would like to see when the agent calls `brief context get` and other commands to check if they are being used. Helpful for debugging our prompting and rules and if the agent is obeying them

### Better Dashboard / Status Overview (Partially Done)
**Added**: 2026-01-22

**DONE**:
- [x] `brief status` dashboard with tables and color-coded metrics
- [x] `brief tree --status` with ✓/○/✗ markers for description status
- [x] Color-coded coverage percentages and freshness indicators

**Remaining ideas**:
- `brief ls` or `brief browse` - interactive file browser with analysis status
- `brief coverage --detailed` - breakdown by directory
- Compact summary mode for `context get` (just file list + stats, not full descriptions)
- `brief config show` - display current configuration clearly
- Collapsible sections or pagination for large outputs
- token counting for context packages. Token counter utility to use anywhere, but include token counts with context get calls.
- attaching plans to tasks. Some way of more robust documents etc alongside them to improve convergence. 
- can we get autocomplete in the cli? for example, when human typing in task ids, it is a pain, being able to arrow key through them or something would be nice. Low priority, particularly if agents are touching this more than humans

---

## FUTURE PLANS

### v0.2 - Context Quality
- [x] Fix import relationship extraction (DONE 2026-01-22)
- [x] Add function signatures to context output (DONE 2026-01-22)
- [x] Lazy description generation (DONE 2026-01-22)
- [x] Freshness tracking for descriptions (DONE 2026-01-22)

### v0.3 - Better Search
- [ ] Improved semantic search ranking
- [ ] Search result explanations (why this file matched)
- [ ] Filter by file type/directory

### Someday/Maybe
- Support for languages other than Python
- VS Code extension
- Web UI for browsing context
- Branching model for per-task branches and agents, storing patch files/diffs as context for a work item
- Sub-agent dispatching and orchestration

---

## RECENT CHANGES

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
  - Modified `parser.get_imports()` to return `(module, level, names)` tuple
  - Modified `resolve_import_to_file()` to resolve paths relative to importing file
  - Import relationships: 0 → 105 (now working)
- **Added function signatures to context output**: Context packages now show signatures
  - Added `format_function_signature()` and `format_class_signature()` helper functions
  - Signatures include: params with types/defaults, return types, async/generator indicators
  - Class signatures show base classes and methods list
- **Implemented lazy description generation**: Descriptions can now be generated on-demand
  - Added `generate_and_save_file_description()` helper in generator module
  - Modified `get_file_description()` to accept `auto_generate` parameter
  - Updated `build_context_for_query()` and `build_context_for_file()` to support it
  - Added `--auto-generate` (`-g`) option to `brief context get` command
- **Implemented freshness tracking for descriptions**: Can now detect stale descriptions
  - Added `described_at` and `description_hash` fields to manifest records
  - Added `find_stale_descriptions()` function in coverage module
  - Updated `calculate_coverage()` to include stale description count
  - Updated `format_coverage()` to show stale descriptions with refresh hints
- **Implemented `brief status` dashboard command**: Comprehensive project status at a glance
  - Shows codebase stats: files, classes, functions, import/call relationships
  - Shows context coverage: file descriptions, module summaries, execution paths, memory patterns
  - Shows freshness: stale files, stale descriptions
  - Shows tasks: pending, in progress, done counts plus active task
  - Shows configuration: version, default model, exclude patterns
  - Provides helpful hints for next actions
- **Improved output formatting with rich tables and colors**:
  - `brief status` now uses rich Tables for structured data display
  - Color-coded coverage percentages (green=100%, yellow>=50%, red<50%)
  - Color-coded freshness indicators (green=current, yellow=stale)
  - Color-coded task counts
  - `brief tree` now uses colored status markers:
    - ✓ green = has description
    - ○ yellow = analyzed only
    - ✗ red = not analyzed
  - Both commands support `--plain` flag for CI/pipe-friendly output
- **Implemented smarter call graph expansion**: Now only follows internal functions
  - `expand_with_call_graph()` builds lookup of internal functions from manifest
  - Only follows calls to functions that exist in the codebase
  - Skips stdlib/external library calls (typer.Option, Path.exists, etc.)
  - Returns the file where callee is defined, not just the call site
- **Restructured CLAUDE.md for better Brief workflow adoption**:
  - Moved Brief workflow instructions to the very top
  - Added explicit "Session Start Checklist"
  - Defined clear Task Workflow with numbered steps
  - Clarified TodoWrite vs Brief task roles (TodoWrite = session steps, Brief = persistent tasks)
  - Added "What NOT To Do" section with clear guidance
- **Added Claude Code hooks for Brief reminders**:
  - Created `scripts/brief-hook-warn.sh` to warn when Read/Grep/Glob used on src/ files
  - Added `.claude/settings.json` with PreToolUse hook configuration
  - Created `docs/hooks-setup.md` with full documentation
  - Hook warns but doesn't block - encourages `brief context get` usage
  - test_analysis.py: Tests parser extraction, manifest building, relationship extraction, call graphs, file hashing
  - test_cli.py: Tests init command behavior, help output
  - test_storage.py: Tests JSONL/JSON operations, Pydantic serialization
  - test_models.py: Tests model creation and defaults (appropriate for data models)
  - test_tasks.py: Tests full task workflow, dependencies, priorities, notes
  - test_memory.py: Tests pattern storage, recall, scope matching, scoring
  - test_retrieval.py: Tests context building, embeddings, search functions
  - test_tracing.py: Tests execution path tracing, storage, loading
  - test_contracts.py: Tests contract detection, edge cases, categories
  - test_generation.py: Tests description formatting, code extraction
  - test_reporting.py: Tests overview, tree, deps, coverage, stale files
  - **Conclusion**: No tests need deprecation - all align with the vision

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
