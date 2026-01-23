#!/bin/bash
# Brief Hook Warning Script
# Shows a warning in Claude Code UI when Read/Grep/Glob is used on source files.
# Note: This warning is visible to the USER but not injected into Claude's context.
# The UserPromptSubmit hook in .claude/settings.json handles Claude-visible reminders.

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
