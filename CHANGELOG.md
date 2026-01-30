# Changelog

All notable changes to Brief will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- Performance testing system (`performance-testing/`) for measuring Brief's effectiveness at guiding AI agents
  - `orchestrator.py` - general-purpose Claude Code headless run orchestrator with worker pool, git clone isolation, process group management, and JSONL manifest tracking
  - `run_test.py` - Brief-specific test matrix: 7 configs x 9 dimensions covering hook combinations, CLAUDE.md variants, and task types (feature addition, bug investigation, resume, multi-task, etc.)
  - `analyze.py` - post-run analysis with per-config/per-dimension breakdowns, full matrix view, job detail, and manifest annotation (void, flag, note)
  - Automatic rate limit detection and recovery — parses reset time from Claude output, sleeps until reset, re-queues affected jobs
  - Per-clone venv isolation so test agents run in their own environment
  - Phase 1 results: Brief+Hooks agents are 30% faster, generate 45% fewer output tokens, and reduce tool-model costs by 78% across 5 validated test dimensions. Full report: `performance-testing/docs/performance-test-findings-v1.md`
  - Per-model cost analysis in `analyze.py` — config comparison now shows main model vs tool model cost split instead of misleading blended token counts
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
  - Default model changed from gpt-5-mini to gemini-2.5-flash

### Fixed
- Model configuration now actually controls which LLM is used (previously was display-only)
- BAML Gemini clients now use correct `generationConfig` syntax for temperature
- Fixed gpt-5-mini which doesn't support temperature parameter

---

## [0.2.0] - 2026-01-23

Major feature release with 23 new features and improvements.

***This changelog was generated at the close of a single-shot brief task run based on [docs/plans/TASK_PLAN_01.md](docs/plans/TASK_PLAN_01.md)***
### Added

**Infrastructure**
- `brief reset` command with granular cache clearing options
  - `--dry-run` to preview what would be cleared
  - `--include-embeddings` to also clear embeddings.db
  - `--full` to clear LLM-generated content (with confirmation)
  - `--include-user-data` to clear tasks/memory/config
- Command logging to `.brief-logs/` for development debugging
- `command_logging` config option (default: true)

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

**Documentation**
- `docs/embeddings-architecture.md` - explains embeddings vs descriptions
- `docs/context-package-rules.md` - defines context package generation rules
- Improved `brief context embed` help and UX
- `--embed` flag on `brief describe batch` to generate embeddings after descriptions

### Fixed

- `coverage --detailed` showing raw ANSI escape codes instead of colors
- Empty manifest returning no results silently (now shows helpful error with quick start guide)
- Demo script had Windows line endings (CRLF), converted to Unix (LF)

### Changed

- Setup wizard flag changed from `--yes/-y` to `--default/-d`
- Memory subcommands renamed for clarity (`remember` → `add`, `recall` → `get`)

---

## [0.1.0] - 2026-01-22

Initial standalone release of Brief.

### Added

- Core analysis system (manifest, relationships, call graphs)
- File description generation via LLM (BAML integration)
- Context package building with hybrid search
- Task management system with dependencies and priorities
- Memory/pattern storage and recall
- Execution path tracing
- Contract detection for codebase conventions
- Embedding-based semantic search
- Rich CLI with status dashboard, tree view, coverage reports
- Claude Code integration with hooks and CLAUDE.md workflow

### Fixed

- Import relationship extraction for relative imports
- `describe batch` parameter passing
- `coverage` computation for described files
- BAML client import paths

---

## Version History

- **0.2.0** - Feature burst release (23 tasks + fixes)
- **0.1.0** - Initial standalone release
