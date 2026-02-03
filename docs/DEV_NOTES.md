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
## Release Prep
***Temp section — delete for release***

- hooks and other things mention brief resume - is that intended? or rather, are we only doing that properly when tasks are enabled? we need a pass on full behaviors (that is all hook setups and claude.md, as well as commands being enabled disabled) based on tasks being active or not. Also, cant have task commands in help message if they are disabled
- when running `brief setup -d --tasks` we need a confirmation that indicates we installed with tasks. Right now, no indication that this was done. 

### Testing
- `[DONE 2026-02-02]` Final first-time user deployment test — `brief setup -d` produces a working system from a clean project with no `.claude/` or `CLAUDE.md`. All 4 hook types confirmed working: SessionStart, PreCompact, PreToolUse, UserPromptSubmit. Note: UserPromptSubmit hook execution is NOT logged in the JSONL transcript — only in `~/.claude/debug/{session-id}.txt`. The JSONL only records `hook_progress` events for SessionStart and PreToolUse. To verify UserPromptSubmit hooks, check the debug log or observe the `<system-reminder>` tags injected into the model's context. Also discovered: the hookify plugin (from `anthropics/claude-plugins-official` marketplace) registers a global UserPromptSubmit hook that runs on every prompt — outputs `{}` when no `.local.md` rules are configured.

### Decisions Made
- **Task system defaults OFF** — `brief setup -d` does NOT enable tasks. Users opt in with `brief setup --tasks` or `brief config set enable_tasks true`. Rationale: many potential Brief users also use Beads for task management. Having two task systems creates confusion and risks the impression that Brief duplicates Beads. Brief's value proposition is context querying — that should be the first impression, not tasks.
- **Hook script location** — `[DONE]` Scripts now live in `.brief/hooks/`, settings.json references them via `$CLAUDE_PROJECT_DIR/.brief/hooks/`. Single location, no fallback needed.

### Remaining Work
- `[DONE 2026-02-02]` **Task system disable enforcement** — `enable_tasks` defaults to `False` in BriefConfig and config.get(). All task commands have guard check. `resume` command checks too. CLAUDE.md snippet and SessionStart hook no longer reference tasks. `brief setup --tasks` flag opts in. Tasks section appended to CLAUDE.md only when enabled.
- `[DONE 2026-02-02]` **`brief --help` restructure** — Commands grouped into panels: Getting Started, Context Queries, Reports, Analysis, Task Management, Advanced. Epilog shows quick-start commands. Subcommand help unchanged.
- `[DONE 2026-02-02]` **Shell tab completion** — Works via Typer (`brief --install-completion`). Tested — functional but clunky: slow (Python process per tab press), completions show above the line rather than inline. Moved instruction to epilog at bottom of `--help` output, labeled as "Typer tab completions" to avoid confusion. May disable or hide in future if it creates more confusion than value.
- `[DONE 2026-02-02]` **Dev repo hook location** — Not a mismatch, intentional. Dev repo uses `scripts/hooks/` (committed) because `.brief/` is gitignored. Setup command generates into `.brief/hooks/` for user projects.
- `[DONE 2026-02-02]` **System env var / .env loading** — `setup()` now loads the user's project `.env` file directly (`load_dotenv(path / ".env")`) before `_detect_api_keys()`, so `.env`-only keys are detected and embeddings run. Does NOT use the global `load_env()` function (see known issue below). Previously, `.env` keys were never loaded before the `has_openai` gate, so fresh `setup -d` with keys only in `.env` would skip embeddings entirely. Live-tested: confirmed working. Note: `load_dotenv()` uses `override=False` (env vars win over `.env`). Consider whether `.env` presence should signal intent to override — against dotenv convention but matches some user expectations. Defer for now.
- `[DONE 2026-02-02]` **Remove sentence-transformers remnants** — No code references remain. Clean.
- need to verify that when we install with the task system, that the hooks and claude.md are setup correctly
- `[DONE 2026-02-02]` `[BUG]` **PreCompact hook format is invalid** — Fixed: both `scripts/hooks/pre-compact.sh` and `_HOOK_PRE_COMPACT` in `setup.py` now use `systemMessage` top-level field instead of `hookSpecificOutput` (which is only valid for PreToolUse, UserPromptSubmit, PostToolUse).
- `[DONE 2026-02-02]` **README says `GEMINI_API_KEY`, code uses `GOOGLE_API_KEY`** — Fixed: README now says `GOOGLE_API_KEY` to match setup.py and BAML clients.
- `[DONE 2026-02-02]` **README typo** — Fixed stray `>` character.
- `[DONE 2026-02-02]` **Re-analyze stale files** — 7 files re-analyzed. All up to date.
- `[DONE 2026-02-02]` **CLI performance — lazy imports** — Deferred heavy imports (openai, pydantic, rich) into function bodies. Removed eager `from .cli import app` in `__init__.py`. Deferred retrieval/search/embeddings in `commands/context.py`, BriefConfig in `commands/init.py`, Rich in `commands/setup.py`. Results: import time 1743ms→303ms (83% reduction), CLI startup 1.2s→0.49s (59% faster). Remaining ~170ms is typer + config/dotenv chain (near Python floor).
- `[DONE 2026-02-02]` **Gitignore exclude pattern matching** — `should_exclude` now matches patterns against individual path components instead of substring-wrapping with `*pattern*`. Plain names match exact components (`lib` matches `lib/` but not `libs/`), glob patterns match against each component (`*.egg-info` matches `foo.egg-info/`). Regression test added.
- `[DONE 2026-02-02]` **Automated staleness detection** — Two-layer approach: (1) `ensure_manifest_current()` runs before every `context get` / `brief ctx` / `brief q` — fast (~100ms) check that adds new files, re-parses stale files, and removes deleted files from the manifest. No relationship/embedding rebuild. (2) SessionStart hook now runs `brief analyze refresh` (full re-analysis including relationships) on session start, resume, and post-compaction. Hook timeout increased to 15s. Users never need to know `analyze refresh` exists.

### Dependencies (Resolved)
- `[DONE]` `pydantic` was missing from core deps — crashes on import. Fixed.
- `[DONE]` `python-dotenv` and `openai` moved to core deps — needed for default `brief setup -d` experience (embeddings). Without them, setup creates embeddings that can't be queried.
- `[DONE]` `sentence-transformers` removed from optional deps — was never used (switched to OpenAI embeddings long ago). It pulls PyTorch (~2GB), which we don't want. Local embeddings is a future feature; when added, it should be its own install extra (`brief[local]` or similar).
- `[DONE]` Optional dep groups simplified — `llm` is now just `baml-py` for LLM descriptions. No more `embeddings` group. Core install gets everything needed for the default experience.
- `[DONE]` `.env` file loading — `python-dotenv` is now a core dep and `config.py` loads `.env` files automatically. Embeddings will work whether the key is in env vars or `.env`.

## CURRENT ISSUES

*Between-sprint work is tracked in CHANGELOG.md under `[Unreleased]`.*

- `[DONE 2026-01-27]` Task archiving system - `brief task archive` and `brief task clear` commands
- `[DONE 2026-02-01]` Figure out claude permissions file format to allow all brief commands — `brief setup -d` now writes `Bash(brief:*)` to `.claude/settings.local.json` and hooks to `.claude/settings.json`. Merges with existing settings.
- `[DONE 2026-01-27]` Multi-model LLM support - `brief model` command, runtime model switching, fixed model configuration
- `[DEFERRED]` Conditional description generation tiers - configure what files get LLM descriptions vs just analysis
- `[DONE 2026-01-30]` Review `.brief-logs/` from TASK_PLAN_01 run to assess brief efficacy and look for improvements — led to performance testing system
- `[DONE 2026-01-30]` Performance testing Phase 1 complete — 63 tests (7 configs x 9 dimensions), results report at `performance-testing/docs/performance-test-findings-v1.md`. Headline: Brief+Hooks is 30% faster, 45% fewer output tokens, 78% tool-model cost reduction across 5 valid Q1 dimensions. Per-model cost analysis added to `analyze.py`.
- `[DONE 2026-01-30]` Orchestrator process orphan bug — `_handle_completion` didn't kill process groups on normal completion, leaving orphaned Claude subprocesses (MCP servers, subagents) consuming CPU. Fixed with `_cleanup_job()` method called on all completions.
- `[DONE 2026-01-30]` Test clone venv isolation — test agents had no `.venv` in clones, causing 6/63 agents to escape to main repo when following CLAUDE.md `source .venv/bin/activate` instruction. Fixed: per-clone venv creation with `uv` (~1.5s) + orchestrator auto-detects and activates clone venv via subprocess env.
- `[DONE 2026-01-30]` Rogue system-wide brief install — test agent (`feature-extension`) ran `pip install -e .` without venv, installing to `~/.local/`. Removed; prevented by per-clone venv isolation.
- `[DONE 2026-02-01]` Change `brief q <>` shorthand to `brief ctx <>` — added `brief ctx` alias (kept `brief q` too for backwards compat)
- Spec analyzer concept - derive abstract understandings of code, snapshot format for "code at this moment"
- `[NO TASK]` Analysis aggregation should average per-cell first — when multiple trials exist for a (config, dimension) pair, the analysis must average those trials into a single data point before computing cross-dimension aggregates. Otherwise dimensions with more repeat runs get over-weighted. Currently no duplicates exist, but this will matter as soon as we add repeat runs for validation. Affects `analyze.py` report functions.
- `[NO TASK]` Agent checks task system on explicit instructions — performance testing revealed that Brief-guided agents run `brief status` + `brief task list` even when given a direct, specific coding instruction (e.g. "extend the describe command to support --format"). This adds ~15-30s of administrative overhead per task. The CLAUDE.md "Session Start Checklist" triggers unconditionally. Needs exploration and testing before attempting a fix — the checklist is valuable for ambiguous/resume scenarios but wasteful for direct prompts. Possible approaches: conditional checklist based on prompt type, lighter-weight startup, or hook-based detection of prompt specificity.
- `[DONE 2026-02-01]` Review user first time setup workflow — `brief setup -d` now does everything: init, analyze, lite descriptions, embeddings, gitignore, CLAUDE.md. README updated with concise quick-start.
- `[DONE 2026-02-01]` for .env and api key stuff — Brief now presents env vars as primary, .env as fallback. Messaging updated in setup wizard and README.
- `[DONE 2026-02-01]` for the "reach out to help" parts of the readme — Added "Get Involved" section with GitHub issues and discussions links.
- `[DONE 2026-02-01]` The readme overall is too long — Restructured. Concise README with quick-start, stats, key commands. Command reference moved to `docs/commands.md`.
- `[DONE 2026-02-01]` When you run `brief task` instead of just an error — Added "did you mean?" suggestions for all subcommand groups (task, context, analyze, describe, memory, trace, contracts, config, model, logs). Also suggests `--help`.
- `[DONE 2026-02-01]` We need to probably modify the claude settings file to add permissions for all brief commands. I always run in skip permissions mode, but most people probably dont — `brief setup` now writes `Bash(brief:*)` to `.claude/settings.local.json`.
- we should detect some other tools that impact our configs. For example, if during `brief setup`, we can detect if beads is installed, and not install the brief task system.
- `[DEFERRED]` add local embeddings capability — detailed plan in Ideas section
- `[DONE 2026-02-02]` **CLI performance — lazy imports** — Deferred heavy imports (openai 516ms, pydantic 200ms, rich 1100ms) into function bodies. CLI startup 1.2s→0.49s. See release prep for details.
- assess models used, particularly on defaults. Defaulting to gemini for descriptions and openai for embeddings is better functionality wise, but many users may think having two providers at start rather than one is worse.
- `[NO TASK]` Research abstract/conceptual query handling — current search (keyword and semantic) works well for queries that map to code terms (class names, function names, docstrings) but struggles with abstract queries like "how does the app prevent agents from forgetting context" or "why does convergence fail". These require a semantic bridge between natural language concepts and code structure that neither keyword matching nor code-level embeddings provide well. Needs research into: query expansion, concept extraction, hierarchical summarization, or hybrid approaches that combine structural understanding with semantic search. Not critical for early users (most practical queries use code terms) but important for Brief's long-term value proposition.
- `[NO TASK]` Chunked embeddings at function/class level — currently embeddings are per-file, which loses granularity for large files where only one function is relevant. Embedding individual functions and classes would produce more precise context packages. Trade-off: more embeddings to store and search, but significantly better precision for targeted queries. Related: could embed raw code alongside structured summaries for richer signal.
- `[DONE 2026-02-01]` Lite descriptions from AST data — Implemented at `src/brief/generation/lite.py`. See item below for details.
- `[NO TASK]` Embedding raw code alongside descriptions — embed both structured summaries AND key code snippets (function bodies, class definitions) for richer semantic signal per file. More tokens per embedding but captures patterns that summaries miss.
- `[NO TASK]` Semantic attractor problem — on large codebases (tested on LangChain, 1665 files), certain large central files (e.g. `runnables/base.py`, `callbacks/manager.py`) act as "semantic attractors" that pull many unrelated queries toward them because they touch every concept. These files rank high for conceptual queries even when a more specific file is the correct answer. This is a fundamental limitation of per-file embeddings on hub files. Potential mitigations: chunked embeddings (per-function/class), file-size penalty in ranking, or a re-ranker that boosts specificity. Documented in `performance-testing/search-quality/results/langchain-agent_2026-02-01_analysis.md`.
- `[NO TASK]` Conceptual query tier failure — agent-realistic benchmark on LangChain (65 queries) showed conceptual/indirect queries ("let the model call external functions", "only keep the last few messages") have only 20% hit rate even with lite embeddings. Implementation-location queries hit 100%, interface-pattern 87%, feature-modification 100%. The gap is extreme. Real agent queries are mostly technical (implementation/feature), so real-world impact is lower than the 20% suggests, but this tier remains a known weakness. Not blocking for early users — agents use code vocabulary, not abstract language.
- `[BUG]` LLM description lazy-load doesn't upgrade or refresh — `get_file_description` in `retrieval/context.py` returns early if any description file exists (line 518), so lite descriptions are never upgraded to LLM descriptions even when `auto_generate_descriptions` is on and an LLM key is available. Also, stored `description_hash` (set in `generator.py` line 369) is never checked during retrieval, so stale descriptions aren't refreshed on access. Fix needed: (1) when auto-generate is on and BAML is available, check if existing description is lite (header/marker?) and upgrade it, (2) compare `description_hash` to current file hash and regenerate if stale. The staleness infrastructure exists (`reporting/coverage.py`), just needs to be wired into the retrieval path.
- `[DONE 2026-02-02]` `[BUG]` Gitignore exclude pattern matching too greedy — Fixed: `should_exclude` now uses per-component matching instead of `fnmatch(path, "*pattern*")`. See release prep for details.
- `[DONE 2026-02-01]` `[BUG]` AST parser missing positional-only and keyword-only args — Fixed. Added `posonlyargs` and `kwonlyargs` handling to `_make_function_record`. 6 regression tests added to `tests/test_analysis.py`. All 236 tests pass.
- `[DONE 2026-02-01]` should probably add .brief and .brief-logs to the gitignore programmatically on `brief setup` and init commands — Both `brief init` and `brief setup` now auto-add `.brief/` and `.brief-logs/` to .gitignore.
- `[DONE 2026-02-01]` concept of 'lite' descriptions — Implemented at `src/brief/generation/lite.py`. Generates structured markdown from AST data (docstrings, signatures, decorators, imports) without LLM calls. Search quality benchmarks confirm lite descriptions achieve near-identical MRR to full LLM descriptions for search ranking (+0.002 difference on Brief corpus). Lite is now the default in `brief setup -d`.
- `[BUG]` **`load_env()` resolves path relative to Brief's install location** — `config.py:load_env()` computes `Path(__file__).parent.parent.parent` to find `.env`, which points to Brief's source tree, not the user's project. On editable installs (`uv pip install -e`), this always loads the dev repo's `.env` regardless of CWD. Setup.py was fixed to load directly from the user's project path, but other callers (`retrieval/embeddings.py`, `generation/generator.py`, `llm.py`, `contracts/inference.py`, `commands/model.py`) still use `load_env()`. Not currently breaking (they just need an API key from somewhere) but conceptually wrong. Fix: `load_env()` should accept a `base_path` parameter and default to CWD, not package location.
- `[DONE 2026-02-02]` `[BUG]` **PreCompact hook references `brief resume` unconditionally** — Hook stays as `brief resume`. Fix: `brief resume` now gracefully falls back to showing `brief status` output when tasks are disabled, instead of erroring. Hook works correctly in both cases.
- `brief setup -d` re-generates all embeddings, even when embeddings already exist. we should only regenerate stale embeddings. 
- and staleness on embeddings - are we regenerating embeddings in a meaningful way?
- `brief status` when no task is active, but there are tasks, then show message saying to use brief task list to see all tasks. 
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
- **Plans attached to tasks** `[DEFERRED]`: Richer task documents for agent convergence
- **Local embeddings** `[DEFERRED]`: Replace OpenAI embedding dependency with local models so Brief works fully offline with zero API cost. Removed `sentence-transformers` from current release because it was unused and pulls PyTorch (~2GB). When revisiting: (a) evaluate lighter alternatives — `onnxruntime` with ONNX-exported models, `fastembed`, or similar libs that don't require PyTorch, (b) add as its own install extra (`brief[local]`) so default install stays light, (c) benchmark local embedding quality vs OpenAI `text-embedding-3-small` on our search quality suite, (d) consider making local the default if quality is close enough — removes the OpenAI key requirement entirely from the default experience.

### Performance Architecture `[DEFERRED]`
- **Rewrite core in Rust or Go** — Python startup cost (~200-400ms per invocation) is a fundamental ceiling. Tools like `ruff` and `uv` are fast because they're compiled binaries. A compiled `brief` binary handling search, status, manifest reads, and AST parsing natively would feel instant (<50ms). Python would remain for LLM/embedding API calls (or be eliminated entirely). Rust has good Python AST parsing crates; Go has faster compile times and simpler FFI. Either would eliminate the import-chain problem permanently. Major effort but transforms the UX — especially for tab completion and hook scripts that spawn `brief` processes.
- **Daemon mode** — Keep a long-running `brief` process in the background, CLI sends commands over a Unix socket or localhost port. Eliminates startup cost entirely since the process is already warm with all imports loaded and manifest cached in memory. Similar to how `gradle --daemon` and `flutter daemon` work. Trade-offs: process management complexity (start/stop/crash recovery), stale state if files change (need file-watcher or invalidation), memory usage for idle daemon. Could be opt-in: `brief daemon start` launches it, CLI auto-detects and routes through daemon when available, falls back to direct execution otherwise. Would make tab completion near-instant too.

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

**Performance Testing Findings (2026-01-30)**
- Claude Code agents inherit the launching shell's exact environment (PATH, VIRTUAL_ENV, etc.)
- If you activate a venv before launching `claude`, agents are "in" that venv. If not, they use system PATH.
- The orchestrator now auto-detects `.venv/bin` in clones and sets subprocess env accordingly, so agents start inside the clone's venv regardless of the orchestrator's own env.
- Sonnet model stayed under Claude Max rate limits for 63 tests (~$0.38 each). No retries triggered.
- Manifest annotation system added: void development tests, flag compromised tests, without deleting data.

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
