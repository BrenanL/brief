# CLAUDE.md

This is the **Brief** codebase - a context infrastructure tool for AI coding agents.

## READ FIRST: Development Notes

**Always read `docs/DEV_NOTES.md` before starting work.** It contains:
- Current known issues and their status
- Ideas under consideration
- Recent changes that may affect your work

**When you make changes:**
- If you encounter a new issue, add it to DEV_NOTES.md
- If you fix an issue, move it to the ARCHIVE section with a date
- If you have ideas while working, add them to the IDEAS section
- **Never delete items** - always archive completed/resolved items

---

## Environment Setup

Always activate the virtual environment before running commands:

```bash
source .venv/bin/activate
```

This project uses **uv** for package management. Always use `uv pip` instead of `pip`:

```bash
# Install dependencies
uv pip install -e .

# Install with optional dependencies
uv pip install -e ".[dev]"
uv pip install -e ".[llm]"
uv pip install -e ".[all]"

# Install a new package
uv pip install <package-name>
```

## Running Tests

```bash
pytest tests/ -v -s
```

## Project Structure

```
brief/
├── src/brief/           # Main package source
│   ├── cli.py           # Typer CLI entry point
│   ├── config.py        # Configuration and paths
│   ├── models.py        # Pydantic data models
│   ├── storage.py       # JSONL/JSON utilities
│   ├── analysis/        # AST parsing and code analysis
│   ├── commands/        # CLI command implementations
│   ├── contracts/       # Convention detection
│   ├── generation/      # LLM-powered descriptions
│   ├── memory/          # Pattern storage and recall
│   ├── retrieval/       # Context building and search
│   ├── tasks/           # Task management
│   └── tracing/         # Execution path tracing
├── tests/               # Test files
├── docs/                # Documentation
└── baml_src/            # BAML client definitions (for LLM)
```

## Key Files

- `src/brief/cli.py` - Main CLI entry point, registers all commands
- `src/brief/config.py` - `BRIEF_DIR`, `get_brief_path()`, path constants
- `src/brief/models.py` - All Pydantic models (`BriefConfig`, `TaskRecord`, etc.)
- `src/brief/retrieval/context.py` - `build_context_for_query()`, `ContextPackage`
- `src/brief/commands/*.py` - Individual command implementations

## Development Commands

```bash
# Run the CLI
brief --help

# Test specific functionality
brief init
brief analyze dir src/brief/
brief overview
brief context get "task management"

# Run specific test file
pytest tests/test_tasks.py -v -s
pytest tests/test_retrieval.py -v -s
```

## Code Style

- Use type hints for all function signatures
- Follow existing patterns in the codebase
- Pydantic models for data structures
- JSONL for persistent storage
- Typer for CLI commands

## Important Conventions

1. **Path handling**: Use `get_brief_path(base)` to get the `.brief/` directory path
2. **Storage**: Use `read_jsonl()` / `write_jsonl()` from `storage.py`
3. **Models**: All data structures are Pydantic models in `models.py`
4. **Commands**: Each command module has an `app = typer.Typer()` that gets registered in `cli.py`
5. **Error handling**: Use `typer.echo("Error: ...", err=True)` and `raise typer.Exit(1)`

---

## Using Brief in This Project

This project uses **Brief** for context management.

### Resuming Previous Work

If the user asks you to **resume**, **continue**, or **pick up where you left off**:

```bash
brief resume
```

This shows the active task with its context. Continue working on that task.

If you're unsure whether there's relevant existing work:
```bash
brief task list
```

### How to Get Information

**Do NOT search the codebase yourself.** Instead, use:

```bash
brief context get "what you need to understand"
```

This replaces grep, glob, find, and exploratory file reading. Brief knows the codebase structure and will give you exactly what's relevant - including related files, contracts you must follow, and execution paths.

**Examples:**
- Need to understand a feature? → `brief context get "how does context retrieval work"`
- Need to modify something? → `brief context get "modifying the search system"`
- Confused about relationships? → `brief context get "what calls build_context_for_query"`
- Starting a task? → `brief context get "adding timing to context retrieval"`

Use this command **repeatedly** as you work - not just once at the start.

### Workflow

#### Starting Work

When the user gives you a specific task:

```bash
# 1. Get context for what you're doing
brief context get "what you're working on"

# 2. For larger work, create a task to track it
brief task create "title" --desc "details" --tags "tags"
brief task start <task-id>
```

Task creation is optional for quick fixes, but recommended for anything that might be interrupted or handed off.

#### During Work

```bash
# Get more context as needed (use this liberally)
brief context get "the specific thing you need to understand"
```

#### Completing Work

```bash
# Mark the task done (if you created one)
brief task done <task-id>

# Run tests
pytest tests/ -v -s
```

### Key Commands

| Command | Use When |
|---------|----------|
| `brief context get "query"` | You need to understand something |
| `brief resume` | User asks to continue previous work |
| `brief task list` | See all tasks |
| `brief task create "title"` | Starting trackable work |
| `brief task done <id>` | Finishing tracked work |
| `brief contracts show` | You need to see all codebase rules |
| `brief trace show <name>` | You want to see an execution flow |

### Important

1. **Always use `brief context get` before implementing** - it shows you the right files, patterns, and contracts
2. **Use `brief resume` when asked to continue previous work** - not for new tasks
3. **Follow the contracts** - they're rules that keep the codebase consistent
4. **Don't search manually** - trust Brief to give you relevant context
