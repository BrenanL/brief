# Changelog

All notable changes to Brief will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- **Lite description generator** (`src/brief/generation/lite.py`) — generates structured markdown descriptions from AST data only (no LLM calls). Includes purpose, contents, role, dependencies, and exports. Used as the default description source for embeddings in first-time setup.
- **`brief setup -d` full automated setup** — single command that initializes Brief, analyzes codebase, generates lite descriptions, creates embeddings (if OpenAI key available), adds .brief/ to .gitignore, and writes Brief workflow to CLAUDE.md. Replaces the previous multi-step setup.
- **`brief init` now runs analysis** — `brief init` creates the directory structure AND analyzes the codebase in one step. No reason to separate these.
- **`brief ctx` alias** — shortcut for `brief context get`, alongside existing `brief q`.
- **"Did you mean?" suggestions** — running `brief task`, `brief context`, etc. without a subcommand now suggests common subcommands instead of showing a generic error.
- **Automatic .gitignore management** — `brief init` and `brief setup` add `.brief/` and `.brief-logs/` to .gitignore if not already present.
- **CLAUDE.md auto-configuration** — `brief setup -d` appends a Brief workflow section to CLAUDE.md (or creates it).
- **Claude Code hooks auto-installation** — `brief setup -d` installs hook scripts to `.brief/hooks/` and configures `.claude/settings.json` with SessionStart, PreCompact, UserPromptSubmit, and PreToolUse hooks. Merges with existing settings.
- **Claude Code permissions** — `brief setup -d` adds `Bash(brief:*)` to `.claude/settings.local.json` so brief commands don't require permission prompts.
- **Search quality benchmark system** (`performance-testing/search-quality/`) — reusable tool for measuring search ranking quality across different configurations. Supports multiple corpora, tiered query sets, and permanent result archiving.
- **Agent-realistic benchmark** — 65 queries across 4 tiers (implementation location, interface pattern, feature modification, conceptual task) tested against LangChain (1,665 files). Lite embeddings achieve 100% hit rate on implementation/feature queries.
- **Parser test coverage** — 6 new tests for positional-only args, keyword-only args, and mixed parameter types.
- **Command reference doc** (`docs/commands.md`) — full command reference moved from README.

### Fixed
- **AST parser missing positional-only and keyword-only args** — `_make_function_record` now handles `posonlyargs` (before `/`), `kwonlyargs` (after `*`), and their defaults correctly. Previously caused `IndexError` on functions using these Python 3.8+ features.

### Changed
- **README restructured** — concise quick-start with `brief setup -d`, performance stats, and call to action. Detailed command reference moved to `docs/commands.md`.
- **API key messaging** — environment variables presented as primary method, `.env` files as fallback.
- **Search quality runner simplified** — queries source `.brief/` directly instead of creating temp directories. Descriptions and embeddings generated once, reused across runs.

---

## [0.1.0] - 2026-01-30

Initial public release of Brief.

### Added

**Performance Testing**
- Performance testing system (`performance-testing/`) for measuring Brief's effectiveness at guiding AI agents
  - `orchestrator.py` - general-purpose Claude Code headless run orchestrator with worker pool, git clone isolation, process group management, and JSONL manifest tracking
  - `run_test.py` - Brief-specific test matrix: 7 configs x 9 dimensions covering hook combinations, CLAUDE.md variants, and task types (feature addition, bug investigation, resume, multi-task, etc.)
  - `analyze.py` - post-run analysis with per-config/per-dimension breakdowns, full matrix view, job detail, and manifest annotation (void, flag, note)
  - Automatic rate limit detection and recovery — parses reset time from Claude output, sleeps until reset, re-queues affected jobs
  - Per-clone venv isolation so test agents run in their own environment
  - Phase 1 results: Brief+Hooks agents are 30% faster, generate 45% fewer output tokens, and reduce tool-model costs by 78% across 5 validated test dimensions. Full report: `performance-testing/docs/performance-test-findings-v1.md`
  - Per-model cost analysis in `analyze.py` — config comparison now shows main model vs tool model cost split instead of misleading blended token counts

**Infrastructure**
- `brief reset` command with granular cache clearing options
  - `--dry-run` to preview what would be cleared
  - `--include-embeddings` to also clear embeddings.db
  - `--full` to clear LLM-generated content (with confirmation)
  - `--include-user-data` to clear tasks/memory/config
- Command logging to `.brief-logs/` for development debugging
- `command_logging` config option (default: true)
- Task archiving system: `brief task archive` saves snapshots to `.brief/archives/tasks/`
  - `--name` for custom archive names
  - `--link` to copy and associate a plan file with the archive
  - `--clear` to clear tasks after archiving
  - `brief task archive list` to view all archives
- Task clearing: `brief task clear` with `--done-only` option to keep active tasks
- Multi-model LLM support with runtime model switching:
  - `brief model list` - show available models
  - `brief model set <model>` - set active model for session
  - `brief model show` - display currently active model and source
  - `brief model clear` - revert to config default
  - `brief model test [--all]` - test model connectivity
  - Available models: gpt-4o-mini, gpt-4o, gpt-5-mini, claude-sonnet, claude-haiku, gemini-2.0-flash, gemini-2.0-flash-lite, gemini-2.5-flash-lite, gemini-2.5-flash, gemini-3-flash-preview
  - Default model: gpt-5-mini

**Core Improvements**
- Auto-generation of descriptions now enabled by default
- `auto_generate_descriptions` config option
- `-G/--no-auto-generate` flag to disable on-demand generation
- Clear warning when LLM unavailable, with fallback to signatures
- `brief describe batch` now prioritizes src/ directories over tests/
- Signatures only shown when no description exists
- `--show-signatures/-s` flag to force showing signatures
- Renamed memory commands: `remember` → `add`, `recall` → `get`
- Top-level aliases: `brief remember`, `brief recall`
- `brief q "query"` shortcut for quick context lookup

**Quality of Life**
- `brief setup` interactive wizard for first-time configuration
  - `--default/-d` flag for non-interactive mode
- Redesigned `brief overview` with rich table formatting
- Improved help messages across all commands with examples
- Extended date format support in exclusions (ISO, compact, American, European)
- `enable_tasks` config option to disable task system
- `llm_provider` config option for multi-provider support (openai, anthropic, gemini)
- Optimized description prompts for BLUF (Bottom Line Up Front) output

**Dashboard**
- `brief config show` command to display current configuration
- `--tokens` flag on `context get` for token count estimates with breakdown
- `--compact/-c` mode for quick context summaries
- `brief coverage --detailed` for per-directory breakdown

**Context & Search**
- Core analysis system (manifest, relationships, call graphs)
- File description generation via LLM (BAML integration)
- Context package building with hybrid search
- Embedding-based semantic search

**Task Management**
- Task management system with dependencies and priorities
- Task steps with progress tracking
- `brief resume` for context recovery after compaction

**Memory & Patterns**
- Memory/pattern storage and recall

**Execution Tracing**
- Execution path tracing with dynamic regeneration
- Auto-detection of entry points from decorators

**Contracts**
- Contract detection for codebase conventions

**CLI**
- Rich CLI with status dashboard, tree view, coverage reports
- Claude Code integration with hooks and CLAUDE.md workflow

**Documentation**
- `docs/embeddings-architecture.md` - explains embeddings vs descriptions
- `docs/context-package-rules.md` - defines context package generation rules
- Improved `brief context embed` help and UX
- `--embed` flag on `brief describe batch` to generate embeddings after descriptions

### Fixed
- Model configuration now actually controls which LLM is used (previously was display-only)
- BAML Gemini clients now use correct `generationConfig` syntax for temperature
- Fixed gpt-5-mini which doesn't support temperature parameter
- `coverage --detailed` showing raw ANSI escape codes instead of colors
- Empty manifest returning no results silently (now shows helpful error with quick start guide)
- Import relationship extraction for relative imports
- `describe batch` parameter passing
- `coverage` computation for described files
- BAML client import paths

### Changed
- Setup wizard flag changed from `--yes/-y` to `--default/-d`
- Memory subcommands renamed for clarity (`remember` → `add`, `recall` → `get`)

---

## Version History

- **0.1.0** - Initial public release with full analysis pipeline, context retrieval, task management, multi-model LLM support, and performance testing
