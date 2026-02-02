# Agent Instructions — Brief Internals

**Read this when developing on the Brief codebase.** This document describes Brief's architecture, design principles, data structures, and how the pieces fit together. CLAUDE.md tells you the *workflow* — this tells you the *system*.

---

## Design Principles

These principles govern every implementation decision. Follow them when adding or modifying code.

1. **Deterministic Context** — Same query always returns the same context package. No randomness in the retrieval pipeline.
2. **Persistence Over Memory** — Everything is stored to disk, nothing relies on agent context window. Tasks, patterns, descriptions, traces — all survive compaction.
3. **Graceful Degradation** — Works without LLM APIs (uses docstrings/heuristics). Each feature layer is independent.
4. **Agent-First Design** — Optimized for AI assistant workflows, not human browsing. Output format is designed to be consumed by LLMs in their context window.
5. **Minimal Overhead** — Fast analysis, efficient storage. AST parsing completes in seconds. JSONL for append-friendly persistence.
6. **Composable Components** — Each piece works independently. Task management works without context retrieval. Search works without descriptions.

---

## How Brief Works

### Default Setup (`brief setup -d`)

One command does everything:

1. **AST parsing** — parses Python files, extracts classes, functions, imports, docstrings into a manifest
2. **Lite descriptions** — generates structured markdown for every file from AST data alone (no LLM, no cost). Uses docstrings, signatures, decorators, and import relationships.
3. **Embeddings** — embeds lite descriptions via OpenAI's embedding API (~$0.02 total) to enable semantic search

After setup, `brief context get "authentication"` finds relevant files using hybrid search — semantic similarity (70% weight) + keyword matching (30%). All local features also work: reports, contracts, traces, tasks, memory, keyword search.

### Optional: LLM Descriptions

When an LLM API key is configured (OpenAI, Anthropic, or Google), Brief can generate richer descriptions via BAML (`generation/generator.py`). These capture intent and purpose, not just structure.

LLM descriptions are **lazy-loaded**: when a file appears in a context package for the first time, Brief generates an LLM description on-demand and caches it. On subsequent retrievals, if the file has changed since the description was generated, Brief regenerates it automatically. This avoids the cost and wait of describing an entire codebase upfront — only files that are actually relevant to the agent's work get described, and descriptions stay fresh.

To disable auto-generation: `brief config set auto_generate_descriptions false`, or pass `-G` / `--no-auto-generate` on individual `context get` calls.

Search quality benchmarks show lite and LLM descriptions achieve near-identical ranking for file retrieval (+0.002 MRR difference). The value of LLM descriptions is in the richer context the agent receives when working with files, not in finding the right files.

### Graceful Degradation

Brief works at every level of API access:
- **No API keys** — AST analysis, keyword search, reports, tasks, traces, contracts, memory. All local.
- **OpenAI key only** — adds semantic search via embeddings (~$0.02). This is the default `brief setup -d` experience.
- **OpenAI + description LLM key** — adds lazy-loaded LLM descriptions for richer context packages.

---

## Analysis Pipeline

How Brief processes a codebase, step by step:

1. **Static Analysis** — Parse Python files with AST, extract classes/functions/imports. Captures structure without executing anything. (`analysis/parser.py`)
2. **Manifest Generation** — Store inventory in JSONL format with file hashes. The manifest is ground truth for what exists. (`analysis/manifest.py`)
3. **Relationship Extraction** — Track import dependencies and call graphs. Enables execution path tracing. (`analysis/manifest.py`)
4. **Contract Detection** — Find naming conventions, patterns, inheritance hierarchies. (`contracts/`)
5. **Lite Description Generation** — Generate structured descriptions from AST data (no LLM). Part of default setup. (`generation/lite.py`)
6. **Embedding Generation** — Embed descriptions for semantic search using OpenAI API (~$0.02). Part of default setup. (`retrieval/embeddings.py`)
7. **LLM Description Generation** — (Optional) Lazy-loaded on-demand when files appear in context packages. Richer than lite. (`generation/generator.py`)

---

## Context Retrieval — What Happens When You Query

When the agent calls `brief context get "add logout button to header"`:

1. `hybrid_search()` tries semantic search (if embeddings exist) + keyword search
2. Without embeddings → 100% keyword search on manifest (names, paths, docstrings)
3. Top 5 results become primary files, expanded via the call graph (what imports them, what they import)
4. Descriptions are loaded from cache (lite or LLM). If an LLM key is configured and auto-generation is enabled, stale or missing descriptions are regenerated on-demand.
5. Output includes: file descriptions or signatures, related files, patterns, contracts, execution paths

### The Context Package

What the agent receives is structured:

- **Primary files** — most relevant files for the query, ranked by semantic + keyword relevance
- **File descriptions** — what each file does, its purpose, key functions and classes
- **Function signatures** — the actual interface, not just the name
- **Relationships** — what imports what, what calls what, what depends on what
- **Execution paths** — how a request flows through the system, from entry point to implementation
- **Contracts** — detected naming conventions, patterns, and rules the code follows
- **Memory patterns** — stored knowledge about how things should work

The hybrid approach means search always works — keyword is the baseline, semantic is the upgrade. There's no cliff edge where "no API key = no search."

---

## Data Storage

### `.brief/` Directory Layout

```
.brief/
├── manifest.jsonl          # Code inventory (classes, functions, imports per file)
├── relationships.jsonl     # Import dependencies and call graph edges
├── memory.jsonl            # Pattern memory entries
├── tasks.jsonl             # Task records with steps and notes
├── active_task             # Currently active task ID (plain text)
├── active_model            # Currently active LLM model name (plain text)
├── config.json             # User configuration
├── embeddings.db           # SQLite database of vector embeddings
├── archives/
│   └── tasks/              # Task archive snapshots (JSONL + metadata)
├── hooks/                  # Claude Code hook scripts (created by brief setup -d)
│   ├── session-start.sh
│   ├── pre-compact.sh
│   ├── user-prompt.sh
│   └── pre-tool-use.sh
└── context/
    ├── files/              # Per-file descriptions (*.md) — lite or LLM-generated
    ├── modules/            # Per-module descriptions (*.md)
    ├── contracts.md        # Detected conventions and contracts
    └── traces.jsonl        # Trace definitions (content regenerated dynamically)
```

### Storage Format Rationale

- **JSONL** for append-friendly data: manifest, relationships, tasks, memory. These grow over time and JSONL makes it easy to append without rewriting.
- **SQLite** for embeddings: vector data needs indexed lookup, not sequential scan.
- **Markdown** for descriptions: human-readable, LLM-friendly, easily diffable.
- **JSON** for config: simple key-value, rarely changes.

The `.brief/` directory is self-contained. You can delete it and regenerate everything. It's a cache of understanding that can always be rebuilt from source code.

---

## Source Components

```
src/brief/
├── cli.py              # Typer CLI entry point. All command groups registered here.
├── config.py           # Configuration paths, get_brief_path(), defaults
├── models.py           # Pydantic data models (ManifestRecord, Task, ContextPackage, etc.)
├── storage.py          # JSONL/JSON read/write utilities
├── llm.py              # LLM abstraction layer (model routing, provider config)
├── logging.py          # Command logging to .brief-logs/
├── analysis/           # AST parsing (parser.py) and manifest building (manifest.py)
├── commands/           # CLI command implementations (one module per command group)
├── contracts/          # Convention detection and storage
├── generation/         # Description generators:
│   ├── lite.py         #   AST-derived descriptions (no LLM)
│   ├── generator.py    #   LLM-powered descriptions (BAML)
│   ├── synthesis.py    #   Module-level synthesis
│   └── types.py        #   Shared types
├── memory/             # Pattern storage and recall
├── reporting/          # Report generation (overview, tree, deps, inventory, coverage)
├── retrieval/          # Context building, keyword search, hybrid search, embeddings
├── tasks/              # Task management with steps, notes, archiving
└── tracing/            # Execution path tracing from entry points
```

### Key Conventions

1. **Path handling**: Use `get_brief_path(base)` from `config.py` to get the `.brief/` directory path
2. **Storage**: Use `read_jsonl()` / `write_jsonl()` from `storage.py` for all JSONL operations
3. **Models**: All data structures are Pydantic models in `models.py`
4. **Commands**: Each command module has `app = typer.Typer()` that gets registered in `cli.py`
5. **Error handling**: Use `typer.echo("Error: ...", err=True)` and `raise typer.Exit(1)`
6. **Type hints**: Required for all function signatures
7. **JSONL persistence**: Append-friendly, one record per line

---

## Configuration

### Environment Variables

```bash
# For LLM descriptions (optional — lite descriptions work without this)
OPENAI_API_KEY=sk-...           # OpenAI (also used for embeddings)
ANTHROPIC_API_KEY=sk-ant-...    # Anthropic (alternative for descriptions)
GOOGLE_API_KEY=...              # Google/Gemini (alternative for descriptions)
```

Environment variables are the primary method. `.env` files in the project root are a fallback (loaded via `python-dotenv`).

### BAML Clients

LLM clients for full descriptions are configured in `baml_src/clients.baml`. The active model can be switched at runtime with `brief model set <model>`.

### Claude Code Integration

`brief setup -d` configures three integration points:
- **CLAUDE.md** — appends Brief workflow instructions for the agent
- **`.claude/settings.json`** — installs hooks (SessionStart, PreCompact, UserPromptSubmit, PreToolUse)
- **`.claude/settings.local.json`** — adds `Bash(brief:*)` permission so Brief commands don't trigger permission prompts

---

## The Hook System

Hooks are advisory shell scripts that run at specific points in the Claude Code agent lifecycle:

- **Session start** — reminds the agent to use Brief when a session begins
- **Pre-tool-use** — when the agent reaches for Read/Grep/Glob, reminds it that `brief context get` exists
- **Pre-compaction** — ensures the compaction summary includes `brief resume` instructions
- **User prompt** — gentle reminder before each response

These are non-blocking. The agent can ignore them. In practice, CLAUDE.md instructions + hooks produces consistent Brief usage in ~80-90% of interactions.

---

## The Task System

The task system exists because agents lose their context. When Claude Code's context window fills and compacts, the agent loses everything. `brief resume` restores: active task, completed steps, notes, and relevant code context.

Workflow:
1. Create a task with description
2. Start it with defined steps
3. Work, marking steps done and leaving notes
4. When context compacts → `brief resume` brings everything back
5. Agent continues where it left off

This is persistence over memory — working state stored to disk, not trusted to the context window.

---

## Pattern Memory

The memory system stores project-specific knowledge that doesn't live in code:

- "All API endpoints must return AcmeEvent objects"
- "Test files use test_\<module\>.py format"
- "Never use print() — use the logger"

Memory patterns are surfaced in context packages when relevant, so the agent knows the rules before it starts writing code.
