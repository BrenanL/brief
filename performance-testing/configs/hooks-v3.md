# Hooks V3 Configuration

This configuration combines the **best of both worlds**: the full hook suite from hooks-v2 with the verbose CLAUDE.md from hooks-v1.

## Hooks

Full hook suite (same as hooks-v2):

### .claude/settings.json

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|compact",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/session-start.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "auto|manual",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/pre-compact.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/user-prompt.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/pre-tool-use.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## CLAUDE.md

Verbose instructions (same as hooks-v1, ~108 lines):

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

### CRITICAL: After Context Compaction

**When your context resets, you MUST immediately run:**

```bash
brief resume
```

This shows your active task and its full details. Do NOT try to remember what you were doing - always run `brief resume` first.

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

**Step 2: Do the work**

As you work, use `brief context get` whenever you need to understand something new. Don't fall back to Read/Grep/Glob for exploration.

**Step 3: Complete the task**
```bash
brief task done <task-id>          # Mark complete
pytest tests/ -v -s                # Verify tests pass
```

### What NOT To Do

- Don't use Read/Grep/Glob to explore code structure (use `brief context get`)
- Don't forget to mark tasks done with `brief task done`
- DO use Read for specific files you already know you need

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
│   ├── commands/        # CLI command implementations
│   ├── retrieval/       # Context building and search
│   └── tasks/           # Task management
├── tests/               # Test files
└── docs/                # Documentation
```

## Code Style

- Use type hints for all function signatures
- Pydantic models for data structures
- JSONL for persistent storage
- Typer for CLI commands

---

See `docs/DEV_NOTES.md` for current issues and ideas.
```

## Purpose

This configuration tests the hypothesis that **combining detailed documentation with active hooks** produces the best results:

- Verbose CLAUDE.md provides comprehensive upfront guidance
- SessionStart hook reinforces on session start/resume
- UserPromptSubmit provides per-prompt reminders
- PreToolUse gives contextual tips when reading code
- PreCompact ensures instructions survive compaction

## Comparison to Other Configs

| Aspect | hooks-v1 | hooks-v2 | hooks-v3 |
|--------|----------|----------|----------|
| Hooks | 1 (UserPromptSubmit) | 4 (full suite) | 4 (full suite) |
| CLAUDE.md | Verbose | Streamlined | Verbose |
| Upfront guidance | Strong | Moderate | Strong |
| Real-time reinforcement | Weak | Strong | Strong |

## Expected Behavior

- Agent receives detailed Brief workflow from CLAUDE.md
- SessionStart reinforces the workflow
- Every prompt includes a reminder
- When reading code files, agent gets contextual tips
- Compaction summaries include resume instructions
- Maximum redundancy = maximum compliance
