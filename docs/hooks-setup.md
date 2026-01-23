# Claude Code Hooks Setup for Brief

This document explains how to configure Claude Code hooks to encourage proper Brief usage.

## Overview

Claude Code supports hooks that run shell commands in response to events. Brief uses two hooks:

1. **UserPromptSubmit** - Injects a reminder into Claude's context on every user message
2. **PreToolUse** - Shows a warning in the UI when Read/Grep/Glob is used on src/ files

## Project-Level Configuration

The hooks are configured in `.claude/settings.json` at the project root:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/brief/scripts/brief-hook-warn.sh",
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
            "command": "echo '\\n════════════════════════════════════════════════════\\n  BRIEF PROJECT: Use `brief context get` for code\\n  exploration instead of Read/Grep/Glob. Returns\\n  descriptions, signatures, and related files.\\n════════════════════════════════════════════════════\\n'"
          }
        ]
      }
    ]
  }
}
```

## How Hook Output Works

Different hooks have different output visibility:

| Hook Event | stdout Visibility |
|------------|-------------------|
| `SessionStart` | **Added to Claude's context** |
| `UserPromptSubmit` | **Added to Claude's context** |
| `PreToolUse` | Shown in UI only (user sees, Claude doesn't) |
| `PostToolUse` | Shown in UI only |

This is why we use **UserPromptSubmit** for the main reminder - it's the only way to inject text into Claude's context on an ongoing basis (including after context compaction).

## The PreToolUse Hook Script

Located at `scripts/brief-hook-warn.sh`:

```bash
#!/bin/bash
INPUT=$(cat)

python3 -c '
import sys
import json

try:
    data = json.loads(sys.argv[1])
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    if "/src/" in file_path or file_path.startswith("src/"):
        response = {
            "systemMessage": f"[Brief] Consider using \"brief context get\" instead of {tool_name} for code exploration."
        }
        print(json.dumps(response))
except Exception:
    pass
' "$INPUT"

exit 0
```

The `systemMessage` JSON field shows a warning in the Claude Code UI (visible to the user but not to Claude).

## Hook Input Format

Hooks receive JSON via stdin:

```json
{
  "session_id": "abc123",
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": {
    "file_path": "/path/to/file.py"
  }
}
```

## Available Hook Events

| Event | When It Fires | stdout Goes To |
|-------|---------------|----------------|
| `SessionStart` | When session begins | Claude's context |
| `UserPromptSubmit` | When user sends a message | Claude's context |
| `PreToolUse` | Before tool execution | UI only |
| `PostToolUse` | After tool completes | UI only |
| `PreCompact` | Before context compaction | UI only |

## Important: Activating Hooks

After adding or changing hooks in `.claude/settings.json`:

1. **Restart Claude Code**, OR
2. **Use `/hooks` command** to review and enable new hooks

Hooks added during a session won't activate until approved.

## Customization

### Blocking Tools (Not Recommended)

To block instead of warn, use exit code 2:

```bash
echo '{"permissionDecision":"deny","permissionDecisionReason":"Use brief context get"}'
exit 2
```

### Different Path Patterns

Modify the path check in the script:

```python
if "/src/" in file_path or "/lib/" in file_path or "/app/" in file_path:
    # warn...
```

### Global vs Project Hooks

- **Project**: `.claude/settings.json` in project root (recommended)
- **Global**: `~/.claude/settings.json` (applies to all projects)

Project and global hooks **merge** - they don't replace each other.

## Troubleshooting

1. **Hook not firing**: Restart Claude Code or use `/hooks` to activate
2. **Script not found**: Use absolute path in settings.json
3. **Permission denied**: Run `chmod +x scripts/brief-hook-warn.sh`
4. **Claude doesn't see message**: Use UserPromptSubmit, not PreToolUse

## References

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
