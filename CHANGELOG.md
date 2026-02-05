# Changelog

All notable changes to Brief will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Fixed
- Lite descriptions now include `<!-- lite -->` marker so they can be distinguished from LLM descriptions
- `brief describe batch` no longer says "No files to describe" on fresh install — lite descriptions are treated as candidates for LLM upgrade
- Lazy-load in `get_file_description` now upgrades lite descriptions to LLM descriptions when BAML is available

---

## [0.1.0] - 2026-02-05

Initial public release of Brief.

### Added

**Setup & Integration**
- `brief setup -d` — single command that initializes Brief, analyzes codebase, generates lite descriptions, creates embeddings (if `OPENAI_API_KEY` set), adds `.brief/` to `.gitignore`, writes Brief workflow to CLAUDE.md, installs Claude Code hooks, and configures permissions
- `brief setup` interactive wizard with `--default/-d` flag for non-interactive mode
- `brief setup --tasks` to opt into task management (off by default)
- Claude Code hooks: SessionStart, PreCompact, UserPromptSubmit, PreToolUse — auto-installed to `.brief/hooks/` and configured in `.claude/settings.json`
- Claude Code permissions: `Bash(brief:*)` auto-added to `.claude/settings.local.json`

**Context & Search**
- Core analysis system — AST parsing, manifest building, relationship extraction, call graphs
- `brief context get "query"` / `brief ctx` / `brief q` — hybrid keyword + semantic search returning structured context packages with file descriptions, function signatures, relationships, execution paths, and conventions
- Lite description generator — structured markdown from AST data (no LLM calls). Near-identical search ranking quality to full LLM descriptions
- `brief describe batch` — generate richer LLM-powered descriptions (requires API key)
- Embedding-based semantic search via OpenAI `text-embedding-3-small`
- Automated staleness detection — manifest auto-updated before every query; full re-analysis on session start via hook
- `analyze refresh` generates lite descriptions for new files and re-embeds automatically
- `--tokens` flag for token count estimates; `--compact/-c` mode for quick summaries
- `--show-signatures/-s` flag; `-G/--no-auto-generate` to disable on-demand generation

**Task Management** (opt-in via `--tasks`)
- Task system with dependencies, priorities, and step tracking
- `brief resume` for context recovery after compaction (falls back to `brief status` when tasks disabled)
- Task archiving: `brief task archive` with `--name`, `--link`, `--clear`
- Task clearing: `brief task clear` with `--done-only`

**Multi-Model LLM Support**
- `brief model list / set / show / clear / test` — runtime model switching
- Providers: OpenAI, Anthropic, Google (Gemini)
- Default model: `gpt-5-mini`

**Reports & Dashboard**
- `brief status` — project dashboard
- `brief overview` — rich table formatting
- `brief coverage --detailed` — per-directory description coverage
- `brief config show` — display current configuration

**Other Features**
- Memory/pattern storage and recall (`brief remember`, `brief recall`)
- Execution path tracing with dynamic regeneration and entry point auto-detection
- Contract detection for codebase conventions
- `brief reset` with `--dry-run`, `--include-embeddings`, `--full`, `--include-user-data`
- Command logging to `.brief-logs/`
- "Did you mean?" suggestions for mistyped subcommands
- `brief --help` organized into command panels

**Documentation**
- `docs/commands.md` — full command reference
- `docs/embeddings-architecture.md` — embeddings vs descriptions explained
- `docs/context-package-rules.md` — context package generation rules
- `docs/brief-workflow.md` — agent workflow guide

**Performance Testing** (development tooling, in `performance-testing/`)
- Automated test system: 63 runs across 7 configurations x 9 task dimensions
- Results: Brief-guided agents complete tasks 30% faster, generate 45% fewer output tokens, reduce tool-model costs by 78%
- Search quality benchmarks on LangChain (1,665 files): 100% hit rate on implementation queries, 87% on interface queries
- Full methodology: `performance-testing/docs/performance-test-findings-v1.md`
