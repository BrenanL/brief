#!/bin/bash
# Brief PreToolUse hook - contextual reminder when using Read/Grep/Glob
# Does NOT block - just adds context to help agent make better choices

# Read stdin into variable
INPUT=$(cat)

# Use Python for reliable JSON parsing, passing input via stdin
echo "$INPUT" | python3 -c '
import sys
import json

try:
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    pattern = tool_input.get("pattern", "")

    # Skip vendor/external directories
    skip_dirs = ["/node_modules/", "/.venv/", "/__pycache__/", "/.git/", "/site-packages/"]
    if any(d in file_path for d in skip_dirs):
        sys.exit(0)

    # Skip config/meta files (agent legitimately needs to read these directly)
    skip_files = ["CLAUDE.md", "settings.json", "config.json", ".env", "pyproject.toml", "package.json"]
    if any(f in file_path for f in skip_files):
        sys.exit(0)

    # Skip if already in .brief directory (using Brief data)
    if "/.brief/" in file_path or "/.brief-logs/" in file_path:
        sys.exit(0)

    # For code files being explored, add a gentle reminder
    code_extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".cpp", ".c", ".h"]
    is_code = any(file_path.endswith(ext) for ext in code_extensions)

    if is_code:
        # Get just the filename for the message
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
