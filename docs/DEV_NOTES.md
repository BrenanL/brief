# DEV_NOTES.md

**Live development notes for Brief** - Read this first when starting work.

---

## How Documentation Works

### File Purposes
- **DEV_NOTES.md** (this file): Working document - current issues, open questions, ideas, active plans
- **CHANGELOG.md**: Historical record - what was shipped, organized by version
- **docs/plans/**: Sprint/task plans that get linked from changelog entries

### Workflow Rules

**During a sprint:**
1. Work from a task plan (e.g., `docs/plans/TASK_PLAN_02.md`)
2. Track progress in Brief tasks (`brief task list`)
3. When sprint completes, archive tasks: `brief task archive --name "sprint-name" --link docs/plans/TASK_PLAN_XX.md --clear`
4. Add changelog entry for the version, link to the task plan

**Between sprints (small improvements, fixes):**
1. Do the work
2. Add bullet to CHANGELOG.md under `[Unreleased]` section
3. Mark item `[DONE date]` in DEV_NOTES CURRENT ISSUES (optional, for visibility)

**When releasing a version:**
1. Rename CHANGELOG `[Unreleased]` → `[0.x.x] - YYYY-MM-DD`
2. Add new empty `[Unreleased]` section at top
3. Remove `[DONE]` items from DEV_NOTES (they're now versioned in changelog)

**For AI agents:**
- Do NOT delete items from DEV_NOTES - mark them `[DONE]` or `[DEFERRED]`
- Always add completed work to CHANGELOG `[Unreleased]`
- Keep DEV_NOTES focused on current/future state, not history

---

## CURRENT ISSUES

*Between-sprint work is tracked in CHANGELOG.md under `[Unreleased]`.*

- `[DONE 2026-01-27]` Task archiving system - `brief task archive` and `brief task clear` commands
- `[NO TASK]` Figure out claude permissions file format to allow all brief commands
- `[DONE 2026-01-27]` Multi-model LLM support - `brief model` command, runtime model switching, fixed model configuration
- `[DEFERRED]` Conditional description generation tiers - configure what files get LLM descriptions vs just analysis
- Review `.brief-logs/` from TASK_PLAN_01 run to assess brief efficacy and look for improvements
- Change `brief q <>` shorthand to `brief ctx <>`
- Spec analyzer concept - derive abstract understandings of code, snapshot format for "code at this moment"

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

The relationship between embeddings (`embeddings.db`) and descriptions (`context/files/*.md`) is not clearly documented for users and needs refactoring. Questions that need answering:

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

**Status**: Discussion item - needs UX design work before implementation. See `docs/embeddings-architecture.md` for technical details.


### Execution Path Tracing Limitations
Known limitations documented here for reference:
1. **Cannot trace through class instantiation**: When code does `builder = ManifestBuilder()`, we can't follow calls to `ManifestBuilder.__init__` or trace what the constructor does. Would need to detect class instantiation and map to `__init__` methods.

2. **Cannot resolve variable-based method calls**: When code does `builder.analyze_directory()`, we see the call as `builder.analyze_directory` but can't resolve that `builder` is a `ManifestBuilder` instance. Would need type inference or runtime analysis.

3. **Entry point detection is decorator-based only**: Currently detects `@app.command`, `@app.route`, etc. Does not yet detect:
   - `if __name__ == "__main__"` blocks
   - Public API functions (non-underscore functions in `__init__.py`)

These limitations mean some traces are shorter than ideal when most calls are to class methods or external libraries. The core path through module-level functions traces well.

---

## Ideas

- **Quick-consult tool** `[DEFERRED]`: `brief consult <prompt>` - send context package to Gemini for second opinion
- **Interactive browser** `[DEFERRED]`: `brief ls` or `brief browse` - file browser with analysis status
- **CLI autocomplete** `[DEFERRED]`: Tab completion for task IDs, command names
- **Plans attached to tasks** `[DEFERRED]`: Richer task documents for agent convergence

### Someday/Maybe `[DEFERRED]`
- Support for languages other than Python
- VS Code extension
- Web UI for browsing context
- Branching model for per-task branches and agents, storing patch files/diffs as context for a work item
- Sub-agent dispatching and orchestration


---

## Version Plans

### v0.2 - Context Quality (COMPLETED 2026-01-23)
See CHANGELOG.md for details. Task archive: `.brief/archives/tasks/2026-01-27_*_sprint-01-task-plan.*`

### v0.3 - Better Search `[DEFERRED]`
- Improved semantic search ranking
- Search result explanations (why this file matched)
- Filter by file type/directory

### Pre-Release `[DEFERRED]`
- Quantify/qualify performance gains from Brief usage
- Test in production-analogous environments
- License, attributions, security audit, .env.example, install docs

**Pre-Release Testing** - What tests do we need to run, and how will we design/create them to ensure that brief actually makes a difference to performance and is semi-stable for claude code usage? Lets quantify and/or qualify performance gains, and ensure that it is working in production-analagous environments before publishing fully.

**Release prep** - what do we need to do before release? i.e. include a license file and attributions, clean up documentation and prune old docs, ensure security, no keys committed, .env.example, how to install, ease of install so you can just use instead of install as a developer, remove any developer personal information, should we squash commits to remove initial dev history to ensure no unsafe data becomes accessible, etc.


---

## Technical Notes

### Recent Architecture Decisions

**Task Archiving (2026-01-27)**
Archives stored in `.brief/archives/tasks/` with JSONL + metadata JSON + optional linked plan file. Enables sprint snapshots with full context preservation.

**Tracing Overhaul (2026-01-22)**
Traces stored as definitions only, regenerated on-demand. Entry points auto-detected from decorators. See CHANGELOG 0.2.0 for full details.

**Import Resolution Fix (2026-01-22)**
Relative imports now resolved correctly using `(module, level, names)` tuple from parser.

---

## Archive

*Detailed implementation notes for completed work are in CHANGELOG.md. Only significant reference items kept here.*

### Sprint 01 (2026-01-23) - v0.2.0
23 tasks completed across P0-P4 priorities. See:
- CHANGELOG.md [0.2.0] entry
- Task archive: `brief task archive list`
- Plan: `docs/plans/TASK_PLAN_01.md`
