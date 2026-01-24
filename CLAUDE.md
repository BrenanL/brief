# CLAUDE.md

This is the **Brief** codebase - a context infrastructure tool for AI coding agents.

---

## HOW TO WORK IN THIS CODEBASE

**This project uses Brief for context management. Follow this workflow.**

### Session Start Checklist

Every time you start working (including after context compaction):

```bash
brief status              # See project state
brief task list           # See what needs doing
```

If resuming previous work: `brief resume`

### CRITICAL: Compaction Summaries
ALWAYS include an instruction to run brief resume when you generate compaction summaries. 
If told to continue until all tasks are completed, include that instruction in your compaction summary. 

### CRITICAL: After Context Compaction

**When your context resets, you MUST immediately run:**

```bash
brief resume
```

This shows your active task and its full details. Do NOT try to remember what you were doing - always run `brief resume` first.

If no task is active, run `brief task list` and pick the next one.

### The Core Rule

**When you need to understand code, use Brief - not Read/Grep/Glob.**

```bash
brief context get "what you need to understand"
```

This gives you: relevant files, descriptions, function signatures, related files, contracts, and execution paths - all in one call. It's better than manual exploration.

### Task Workflow

**Step 1: Pick up a task**
```bash
brief task list                    # See available tasks
brief task start <task-id>         # Mark it active
brief task show <task-id>          # READ THE FULL TASK DESCRIPTION
brief context get "<task topic>"   # Get relevant context
```

**IMPORTANT**: Always run `brief task show` before starting work. The task title is just a summary - the full implementation requirements are in the description. Do not start coding until you've read the complete task specification.

**Step 2: Plan with TodoWrite**

Use your TodoWrite tool to break the task into steps. TodoWrite is for session-scoped step tracking. Brief tasks are for persistent work items.

Example:
- Brief task: "Implement caching for API calls"
- TodoWrite steps: "1. Find current API code, 2. Add cache layer, 3. Update tests, 4. Run tests"

**Step 3: Do the work**

As you work, use `brief context get` whenever you need to understand something new. Don't fall back to Read/Grep/Glob for exploration.

**Step 4: Complete the task**
```bash
brief task done <task-id>          # Mark complete
pytest tests/ -v -s                # Verify tests pass
```

### Quick Reference

| When... | Do this |
|---------|---------|
| Need to understand code | `brief context get "query"` |
| Starting a work session | `brief status` then `brief task list` |
| Starting a task | `brief task start <id>` |
| Finishing a task | `brief task done <id>` |
| User says "resume/continue" | `brief resume` |
| Error or need to view brief's capabilities | `brief --help` |

For detailed examples and workflow guidance, see **[docs/brief-workflow.md](docs/brief-workflow.md)**.

### Autonomous Task Completion Mode (Temporary)

When told to "continue until all tasks completed" or similar:

1. `brief task list` - see all pending tasks
2. `brief task start <id>` - pick highest priority ready task
3. `brief task show <id>` - **READ THE FULL DESCRIPTION** before coding
4. `brief context get "<topic>"` - understand relevant code
5. Implement the task completely
6. `pytest tests/ -v -s` - verify tests pass
7. `brief task done <id>` - mark complete
8. **REPEAT from step 1** until no pending tasks remain

**After context compaction**: Run `brief resume` immediately, then continue from step 4.

### What NOT To Do

- ❌ Don't use Read/Grep/Glob to explore code structure (use `brief context get`)
- ❌ Don't track tasks only in TodoWrite (use Brief tasks for persistence)
- ❌ Don't forget to mark tasks done with `brief task done`
- ❌ Don't start coding based only on the task title (always run `brief task show` first)
- ✅ DO use Read for specific files you already know you need
- ✅ DO use TodoWrite for planning steps within a task

---

## Development Notes

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

```bash
source .venv/bin/activate          # Always activate venv first
```

This project uses **uv** for package management. Always use `uv pip` instead of `pip`:

```bash
uv pip install -e .                # Install dependencies
uv pip install -e ".[dev]"         # With dev dependencies
uv pip install -e ".[all]"         # All optional dependencies

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
