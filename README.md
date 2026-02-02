# Brief

**Context infrastructure for AI coding agents.**

Brief gives AI coding agents deterministic context packages instead of having them search your codebase randomly. One call to `brief context get` replaces 5-25 file exploration calls with structured, relevant context.

Preliminary testing shows brief-guided agents complete coding tasks **30% faster**, generate **45% fewer output tokens**, and reduce tool-model costs by **78%**. Full methodology: [`performance-testing/docs/performance-test-findings-v1.md`](performance-testing/docs/performance-test-findings-v1.md)

## Quick Start

### Option A: Let Claude Code install it

Paste this into Claude Code (replace the path with where you want Brief installed):

```
Clone brief from https://github.com/BrenanL/brief into /home/user/brief/ and install it in this project. Then run `brief setup -d` to configure.
```

Restart Claude Code after setup completes.

### Option B: Manual install

```bash
# Install Brief
git clone https://github.com/BrenanL/brief.git
cd brief && python -m venv .venv && source .venv/bin/activate
pip install -e .

# Go to your project and set up
cd /path/to/your/project
brief setup -d  # use defaults
brief setup     # interactive setup wizard
```

That's it. `brief setup -d` initializes Brief, analyzes your codebase, generates search descriptions, creates embeddings (if `OPENAI_API_KEY` is set), and configures your CLAUDE.md.

### Try it

```bash
brief context get "authentication"
```

This is what your agent receives instead of searching 20 files. Structured context: relevant files, descriptions, function signatures, relationships, execution paths, and conventions.

## How It Works

Brief AST-parses your codebase and builds a manifest of every class, function, import, and relationship. It generates structured descriptions from this data and embeds them for semantic search.

When queried, Brief identifies the most relevant files, traces execution paths across the codebase, and returns a context package containing everything an agent needs to understand the code it's about to work on.

The agent gets this context package as the most recent entry in its context window, pre-biasing it with accurate understanding before it writes any code.

## What You Need

- **Python 3.10+**
- **No API keys required** for core functionality (analysis, keyword search, task management)
- **OPENAI_API_KEY** enables semantic search via embeddings (~$0.02 per codebase)
- **GEMINI_API_KEY** or **OPENAI_API_KEY** or **ANTHROPIC_API_KEY** enables richer LLM-generated descriptions (optional — lite descriptions work well for search)

Brief checks your environment variables automatically. Alternatively, set keys in a`.env` file at project root.

## Key Commands

```bash
brief setup -d                    # Full automated setup (do this first)
brief context get "your query>"         # Get context package for a topic
brief ctx "your query"                 # Shortcut for above
brief status                      # Project dashboard
brief task list                   # See tasks
brief resume                      # Resume after context compaction
brief analyze refresh             # Re-analyze changed files
brief context embed               # Regenerate embeddings
```

Full command reference: [`docs/commands.md`](docs/commands.md)

## Agent Integration

Brief integrates with Claude Code via:
- **CLAUDE.md** — Brief workflow instructions (auto-configured by `brief setup -d`)
- **Hooks** — Optional shell hooks that remind agents to use Brief (see [`docs/hooks-setup.md`](docs/hooks-setup.md))
- **Task system** — Persistent task tracking that survives context compaction

Agent workflow guide: [`docs/brief-workflow.md`](docs/brief-workflow.md)

## Performance

Tested with Claude Code across 63 automated test runs (7 configurations x 9 task dimensions):

| Metric | Without Brief | With Brief | Improvement |
|--------|--------------|------------|-------------|
| Task completion time | 260s | 182s | **30% faster** |
| Output tokens | 14,768 | 8,065 | **45% fewer** |
| Tool-model (Haiku) cost | $0.10 | $0.02 | **78% cheaper** |
| Read/Grep/Glob calls | 18 | 6 | **66% fewer** |

Search quality benchmarks on LangChain (1,665 files): lite embeddings achieve **100% hit rate** on implementation queries and **87%** on interface queries. Details: [`performance-testing/search-quality/`](performance-testing/search-quality/)

## Get Involved

Brief is in early development. If you try it, I want to hear what happens.

- **Issues & feedback**: [github.com/BrenanL/brief/issues](https://github.com/BrenanL/brief/issues)
- **Discussions**: [github.com/BrenanL/brief/discussions](https://github.com/BrenanL/brief/discussions)

If something doesn't work, if the agent ignores Brief, if the context package misses the right files — that's exactly the feedback that makes this better. Open an issue or start a discussion.

## License

MIT — see [LICENSE](LICENSE)
