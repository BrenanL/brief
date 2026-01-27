# Changelog

All notable changes to Brief will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
