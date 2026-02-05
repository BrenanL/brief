# DEV_NOTES.md

**Live development notes for Brief** — read this first when starting work.

---

## How Documentation Works

### File Purposes
- **DEV_NOTES.md** (this file): Working document - current issues, open questions, ideas, active plans
- **CHANGELOG.md**: Historical record - what was shipped, organized by version
- **docs/plans/**: Sprint/task plans that get linked from changelog entries

### Workflow Rules

**When doing work:**
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
- When you encounter a new issue, add it to the appropriate section
- When you fix an issue, mark it `[DONE date]` and add to CHANGELOG

---

## Current Issues
- for now, put a quick list of the "main" files pulled by context get at the top. That way, I can see at a glance which files got pulled. 
- `[DONE 2026-02-05]` Lazy load of llm descriptions doesnt seem to work?
- claude code auto using explore agents may prevent brief from being used (and plan mode)

### Bugs

- `[DONE 2026-02-05]` On fresh install, running `brief describe batch` after setup says "No files to describe." — Fixed: lite descriptions now carry a `<!-- lite -->` marker, and both `describe batch` and lazy-load check for it.

- `[DONE 2026-02-05]` **LLM description lazy-load doesn't upgrade or refresh** — Fixed: `get_file_description` now checks for `<!-- lite -->` marker and upgrades to LLM description when BAML is available. `describe batch` also treats lite descriptions as candidates for LLM upgrade. Note: existing installs need `brief setup -d` to regenerate lite descriptions with the marker.
- **README typo** line 60: missing space before backtick in `in a\`.env\``.

### UX / Polish

- `brief setup -d` re-generates all embeddings even when they already exist — should only regenerate stale (delta-only embedding).
- `brief status` when no task is active but tasks exist — should show message saying to use `brief task list`.
- `--help` output: "Task Management" panel shows `resume` and `task` always, even when tasks are disabled.
- Agent checks task system on explicit instructions — Brief-guided agents run `brief status` + `brief task list` even on direct coding instructions, adding ~15-30s overhead. The CLAUDE.md "Session Start Checklist" triggers unconditionally. Possible: conditional checklist, lighter startup, or hook-based prompt detection.
- Should detect other agent tools (Beads, etc.) during `brief setup` and adapt accordingly.

### Search Quality

- **Tests showing up in query results** — test files rank at the top of search results. Need to trace how default config handles test file descriptions/embeddings and whether search ranking should penalize test files.
- **Conceptual query weakness** — agent-realistic benchmark showed conceptual/indirect queries have only 20% hit rate vs 100% for implementation queries. Real agent queries are mostly technical so real-world impact is lower, but this is a known gap.
- **Semantic attractor problem** — on large codebases, central hub files pull many unrelated queries toward them. Potential mitigations: chunked embeddings, file-size penalty, or a re-ranker.

### Open Questions

- How will lite descriptions work on codebases without good docstrings? Should we detect that? Generate docstrings via LLM?
- The CLAUDE.md setup we ship is technically untested (different from what performance testing used). Consider a global injection hook for Brief in Claude Code with a minimal CLAUDE.md.
- Performance tests should be re-run with tasks disabled to see true time/token differences.
- `[DEFERRED]` Conditional description generation tiers — configure what files get LLM descriptions vs just analysis.

---

## Ideas

### Near-term
- **`brief refresh` unified command** — single command that runs manifest sync + lite descriptions + embeddings. Replaces multi-step `analyze refresh` + `context embed`.
- **Chunked embeddings** at function/class level — per-file embeddings lose granularity for large files. More precise but more storage.
- **Embed raw code alongside descriptions** — richer semantic signal per file.
- **Abstract/conceptual query handling** — query expansion, concept extraction, or hybrid approaches to bridge natural language concepts and code structure.

### Deferred
- **Quick-consult tool**: `brief consult <prompt>` — send context package to an LLM for second opinion
- **Interactive browser**: `brief ls` or `brief browse` — file browser with analysis status
- **Plans attached to tasks**: richer task documents for agent convergence
- **Local embeddings**: replace OpenAI dependency with local models (`onnxruntime`, `fastembed`). Add as `brief[local]` extra. Benchmark vs OpenAI `text-embedding-3-small`.
- **Spec analyzer**: derive abstract understandings of code, snapshot format for "code at this moment"

### Performance Architecture
- **Rewrite core in Rust or Go** — Python startup (~200-400ms) is a fundamental ceiling. A compiled binary would be <50ms. Major effort.
- **Daemon mode** — long-running process, CLI communicates over Unix socket. Eliminates startup cost. Trade-offs: process management, stale state, memory.

### Someday/Maybe
- Support for languages other than Python
- VS Code extension
- Web UI for browsing context
- Branching model for per-task branches and agents
- Sub-agent dispatching and orchestration

---

## Next Version(s) Plans

### v0.2 - Context Quality (COMPLETED 2026-01-23)
See CHANGELOG.md for details. Task archive: `.brief/archives/tasks/2026-01-27_*_sprint-01-task-plan.*`

### v0.3 - Better Search `[DEFERRED]`
- Improved semantic search ranking
- Search result explanations (why this file matched)
- Filter by file type/directory

---

## Technical Notes

**Performance Testing Findings (2026-01-30)**
- Claude Code agents inherit the launching shell's exact environment (PATH, VIRTUAL_ENV, etc.)
- The orchestrator auto-detects `.venv/bin` in clones and sets subprocess env accordingly
- Sonnet stayed under Claude Max rate limits for 63 tests (~$0.38 each)

**Execution Path Tracing Limitations**
1. Cannot trace through class instantiation (`ManifestBuilder()` → `__init__`)
2. Cannot resolve variable-based method calls (`builder.analyze_directory()`)
3. Entry point detection is decorator-based only (no `if __name__ == "__main__"`)

**Import Resolution (2026-01-22)**
Relative imports resolved using `(module, level, names)` tuple from parser.
