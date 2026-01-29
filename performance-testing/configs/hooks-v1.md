# Hooks V1 Configuration

This configuration represents the **original Brief setup** with verbose CLAUDE.md instructions and a single UserPromptSubmit hook.

## Hooks

Single hook providing a brief reminder on each prompt:

### .claude/settings.json

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo '[Brief] Use brief context get for code exploration.'"
          }
        ]
      }
    ]
  }
}
```

## CLAUDE.md

Verbose instructions with full workflow documentation (~190 lines):

```markdown
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

**IMPORTANT**: Always run `brief task show` before starting work. The task title is just a summary - the full implementation requirements are in the description.

**Step 2: Plan with TodoWrite**

Use your TodoWrite tool to break the task into steps.

**Step 3: Do the work**

As you work, use `brief context get` whenever you need to understand something new.

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

### Autonomous Task Completion Mode

When told to "continue until all tasks completed":

1. `brief task list` - see all pending tasks
2. `brief task start <id>` - pick highest priority ready task
3. `brief task show <id>` - **READ THE FULL DESCRIPTION**
4. `brief context get "<topic>"` - understand relevant code
5. Implement the task completely
6. `pytest tests/ -v -s` - verify tests pass
7. `brief task done <id>` - mark complete
8. **REPEAT from step 1** until no pending tasks remain

**After context compaction**: Run `brief resume` immediately, then continue.

### What NOT To Do

- ❌ Don't use Read/Grep/Glob to explore code structure (use `brief context get`)
- ❌ Don't track tasks only in TodoWrite (use Brief tasks for persistence)
- ❌ Don't forget to mark tasks done with `brief task done`
- ❌ Don't start coding based only on the task title
- ✅ DO use Read for specific files you already know you need
- ✅ DO use TodoWrite for planning steps within a task

---

## Development Notes

**Always read `docs/DEV_NOTES.md` before starting work.**

---

## Environment Setup

```bash
source .venv/bin/activate          # Always activate venv first
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
└── baml_src/            # BAML client definitions
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
```

## Purpose

This configuration represents the **intermediate Brief setup** - relying primarily on verbose CLAUDE.md documentation to guide agent behavior, with minimal hook intervention.

## Key Differences from Other Configs

| Aspect | baseline | hooks-v1 | hooks-v2 |
|--------|----------|----------|----------|
| Hooks | None | 1 (UserPromptSubmit) | 4 (full suite) |
| CLAUDE.md | Minimal | Verbose (~190 lines) | Streamlined (~90 lines) |
| Behavioral guidance | None | Via documentation | Via hooks + docs |
| Contextual reminders | None | On prompt only | On every tool use |

## Expected Behavior

- Agent receives Brief workflow instructions via CLAUDE.md at session start
- Each prompt triggers a brief reminder to use `brief context get`
- No contextual reminders when agent uses Read/Grep/Glob on code files
- Compaction may lose the detailed CLAUDE.md context

## Hypothesis

The verbose CLAUDE.md approach is expected to be **less effective** than hooks-v2 because:
1. Long documents get skimmed/ignored by agents
2. No real-time reinforcement when agent reaches for Read/Grep/Glob
3. Instructions may be lost during context compaction
4. Single echo hook is easily overlooked
