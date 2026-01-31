# Hooks V2 Configuration

This configuration represents the full Brief hook suite with streamlined CLAUDE.md instructions.

## Hooks

Four hooks working together to guide agent behavior:

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

### Hook Scripts

#### scripts/hooks/session-start.sh
Primes agent with Brief workflow on session start/resume/compact:

```bash
#!/bin/bash
cat > /dev/null
cat << 'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[Brief Workflow] This project uses Brief for context management.\n\nWHEN YOU NEED TO UNDERSTAND CODE:\n1. FIRST run: brief context get \"<what you need to understand>\"\n2. Brief returns: file descriptions, signatures, relationships, and related files\n3. THEN use Read only for specific files you need to edit\n\nStart with: brief status && brief task list"}}
EOF
exit 0
```

#### scripts/hooks/user-prompt.sh
Reminds agent to use Brief first on every prompt:

```bash
#!/bin/bash
cat > /dev/null
echo '[Brief] Before exploring code, run: brief context get "<topic>" to get structured context.'
exit 0
```

#### scripts/hooks/pre-tool-use.sh
Contextual tip when agent uses Read/Grep/Glob on code files:

```bash
#!/bin/bash
INPUT=$(cat)
echo "$INPUT" | python3 -c '
import sys
import json

try:
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    # Skip vendor/config files
    skip_dirs = ["/node_modules/", "/.venv/", "/__pycache__/", "/.git/", "/site-packages/"]
    skip_files = ["CLAUDE.md", "settings.json", "config.json", ".env", "pyproject.toml", "package.json"]

    if any(d in file_path for d in skip_dirs):
        sys.exit(0)
    if any(f in file_path for f in skip_files):
        sys.exit(0)
    if "/.brief/" in file_path or "/.brief-logs/" in file_path:
        sys.exit(0)

    # Reminder for code files
    code_extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".cpp", ".c", ".h"]
    is_code = any(file_path.endswith(ext) for ext in code_extensions)

    if is_code:
        filename = file_path.split("/")[-1] if "/" in file_path else file_path
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[Brief Tip] If you are trying to understand how {filename} works or fits into the codebase, consider running `brief context get` first - it provides descriptions, signatures, and related files in one call."
            }
        }
        print(json.dumps(output))
except Exception:
    pass
sys.exit(0)
'
exit 0
```

#### scripts/hooks/pre-compact.sh
Ensures compaction summaries include Brief resume instructions:

```bash
#!/bin/bash
cat > /dev/null
cat << 'EOF'
{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"[Compaction Note] Include in your summary: After resuming, run `brief resume` first, then use `brief context get` before exploring code with Read/Grep/Glob."}}
EOF
exit 0
```

## CLAUDE.md

Streamlined instructions (hooks handle behavioral reminders):

```markdown
# CLAUDE.md

This is the **Brief** codebase - a context infrastructure tool for AI coding agents.

## Quick Start

```bash
brief status                      # Project state
brief task list                   # See tasks
brief context get "<topic>"       # Understand code (use BEFORE Read/Grep/Glob)
```

## The Core Rule

**Use `brief context get` FIRST when you need to understand code.**

It returns file descriptions, signatures, relationships, and related files in one call - better than manually exploring with Read/Grep/Glob.

## Task Workflow

1. `brief task start <id>` - Claim a task
2. `brief task show <id>` - Read full description (required before coding!)
3. `brief context get "<topic>"` - Get relevant context
4. Implement the task
5. `pytest tests/ -v -s` - Verify tests pass
6. `brief task done <id>` - Mark complete

**After compaction**: Run `brief resume` immediately.

## Environment

```bash
source .venv/bin/activate         # Always activate first
uv pip install -e ".[dev]"        # Install with dev deps
pytest tests/ -v -s               # Run tests
```

## Code Conventions

- Type hints for all function signatures
- Pydantic models for data structures (`models.py`)
- JSONL for persistent storage (`storage.py`)
- Typer for CLI commands (`commands/`)
- Path handling via `get_brief_path(base)`

## Key Directories

src/brief/
├── cli.py              # Entry point
├── config.py           # Paths and config
├── models.py           # Data models
├── commands/           # CLI commands
├── retrieval/          # Context building
├── tasks/              # Task management
└── analysis/           # Code parsing

---

See `docs/DEV_NOTES.md` for current issues and ideas.
```

## Purpose

This configuration represents the **optimized Brief setup** designed to guide agents toward using `brief context get` for code exploration.

## Expected Behavior

- Agent receives Brief workflow instructions on session start
- Every prompt includes a reminder to use Brief first
- When agent uses Read/Grep/Glob on code files, it receives a contextual tip
- Compaction summaries include instructions to use `brief resume`
