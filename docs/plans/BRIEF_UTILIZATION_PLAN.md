# Brief Utilization Improvement Plan

**Created**: 2026-01-27
**Purpose**: Improve agent adoption of `brief context get` based on task-plan-01 analysis

---

## Executive Summary

Analysis of the one-shot task run (23 tasks in 44 minutes) revealed:
- **8 `brief context get` queries** vs **62 Read/Grep/Glob calls**
- **Ratio**: 1:7.75 (one Brief call per ~8 direct file accesses)
- **Root cause**: PreToolUse hook uses `systemMessage` which only shows to UI, not agent context

---

## Phase 1: Fix Hook System

### 1.1 Fix PreToolUse Hook (CRITICAL)

**Problem**: Current hook uses `systemMessage` which is UI-only.

**Solution**: Use `additionalContext` in JSON output to inject into agent context.

```python
#!/usr/bin/env python3
"""Brief PreToolUse hook - injects reminder into agent context."""
import json
import sys

try:
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    pattern = tool_input.get("pattern", "")

    # Skip vendor/external files
    skip_patterns = ["/node_modules/", "/.venv/", "/__pycache__/", "/.git/"]
    if any(p in file_path for p in skip_patterns):
        sys.exit(0)

    # Skip if reading CLAUDE.md or config files (meta-operations)
    meta_files = ["CLAUDE.md", "settings.json", "config.json", ".env"]
    if any(m in file_path for m in meta_files):
        sys.exit(0)

    # For any code file read, remind about Brief
    code_extensions = [".py", ".js", ".ts", ".go", ".rs", ".java", ".rb"]
    is_code = any(file_path.endswith(ext) for ext in code_extensions)
    is_exploration = tool_name in ("Read", "Grep", "Glob")

    if is_code and is_exploration:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[Brief Reminder] You're using {tool_name} on {file_path.split('/')[-1]}. Consider: would `brief context get \"<topic>\"` give you better context? Brief returns file descriptions, signatures, relationships, and related files in one call."
            }
        }
        print(json.dumps(output))

except Exception:
    pass

sys.exit(0)
```

**Key changes**:
- Use `additionalContext` instead of `systemMessage`
- Expand to all code files, not just `/src/`
- Skip vendor directories and meta files

### 1.2 Add SessionStart Hook

**Purpose**: Prime the agent at session start and after compaction/resume.

```json
{
  "SessionStart": [
    {
      "matcher": "startup|resume|compact",
      "hooks": [
        {
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/scripts/brief-session-start.sh"
        }
      ]
    }
  ]
}
```

**Script** (`scripts/brief-session-start.sh`):
```bash
#!/bin/bash
cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "SESSION PROTOCOL: This project uses Brief for context management.\n\n1. BEFORE exploring code with Read/Grep/Glob, first run: brief context get \"<what you need>\"\n2. Brief returns: file descriptions, function signatures, related files, and contracts\n3. Only use Read for files you already know you need to edit\n\nStart with: brief status && brief task list"
  }
}
EOF
```

### 1.3 Add PreCompact Hook

**Purpose**: Ensure compaction summaries include Brief workflow instructions.

```json
{
  "PreCompact": [
    {
      "matcher": "auto|manual",
      "hooks": [
        {
          "type": "command",
          "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PreCompact\",\"additionalContext\":\"COMPACTION NOTE: Include in your summary: After resuming, run `brief resume` immediately, then use `brief context get` before exploring code.\"}}'"
        }
      ]
    }
  ]
}
```

### 1.4 Simplify UserPromptSubmit Hook

**Current**: Generic banner on every prompt.

**Improved**: More actionable, less noisy.

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "echo 'Brief project: Use `brief context get \"<topic>\"` for code exploration.'"
        }
      ]
    }
  ]
}
```

---

## Phase 2: Improve Logging for Analysis

### 2.1 Add Session Markers

**Problem**: Hard to identify session boundaries in commands.log.

**Solution**: Log session start/end events.

Add to `src/brief/logging.py`:
```python
def log_session_event(event: str, metadata: dict = None):
    """Log a session lifecycle event.

    Args:
        event: Event type (session_start, session_end, compaction, etc.)
        metadata: Optional metadata dict
    """
    if not is_logging_enabled():
        return

    logs_path = get_logs_path()
    log_file = logs_path / COMMAND_LOG_FILE
    logs_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    meta_str = json.dumps(metadata) if metadata else "{}"
    entry = f"{timestamp} | SESSION:{event} | {meta_str}\n"

    with log_file.open("a") as f:
        f.write(entry)
```

Create SessionStart hook to call:
```bash
source .venv/bin/activate && python -c "from brief.logging import log_session_event; log_session_event('start', {'source': '$1'})"
```

### 2.2 Add Analysis Command

Create `brief analyze-logs` command:
```python
@app.command("analyze-logs")
def analyze_logs(
    session: str = typer.Option(None, help="Analyze specific session or 'latest'"),
    output: str = typer.Option("summary", help="Output format: summary, json, csv")
):
    """Analyze Brief command usage from logs.

    Shows:
    - Total commands by type
    - brief context get vs Read/Grep/Glob ratio
    - Session timeline
    - Task completion correlation
    """
```

**Metrics to track**:
- `context_get_count`: Number of `brief context get` calls
- `read_count`, `grep_count`, `glob_count`: Direct exploration calls
- `ratio`: context_get / (read + grep + glob)
- `task_commands`: Task workflow commands
- `session_duration`: Time from first to last command
- `compaction_count`: Number of compaction events

---

## Phase 3: Streamline CLAUDE.md

Move hook-enforced behaviors OUT of CLAUDE.md to reduce cognitive load.

### Current CLAUDE.md Issues
- 192 lines, lots of repetition
- "The Core Rule" + "What NOT To Do" + workflow steps all say the same thing
- Task workflow is solid, Brief usage instructions are verbose

### Proposed Slimmed CLAUDE.md

```markdown
# CLAUDE.md

This is the **Brief** codebase - a context infrastructure tool for AI coding agents.

## Quick Start

```bash
brief status              # See project state
brief task list           # See what needs doing
brief context get "<topic>" # Understand code (use this BEFORE Read/Grep/Glob)
```

## Task Workflow

1. `brief task start <id>` - Claim a task
2. `brief task show <id>` - Read full description (required!)
3. `brief context get "<topic>"` - Get relevant context
4. Implement the task
5. `pytest tests/ -v -s` - Verify
6. `brief task done <id>` - Complete

**After compaction**: Run `brief resume` immediately.

## Environment

```bash
source .venv/bin/activate
pytest tests/ -v -s
```

## Code Style

- Type hints for all signatures
- Pydantic models for data structures
- JSONL for persistent storage

---

See `docs/DEV_NOTES.md` for current issues and ideas.


**Rationale**: Hooks now handle:
- Reminding about Brief on every prompt (UserPromptSubmit)
- Reminding when using Read/Grep/Glob (PreToolUse)
- Priming on session start (SessionStart)
- Guiding compaction summaries (PreCompact)

CLAUDE.md can be minimal reference.

---

## Phase 4: A/B Testing Framework

### 4.1 Test Harness Design

**Goal**: Automatically run agents with different configurations and compare Brief utilization.

**Approach**:
1. Create standardized test tasks
2. Run claude in non-interactive mode with `--print`
3. Parse session logs programmatically
4. Compare metrics across configurations

### 4.2 Test Script (`scripts/ab-test-brief.py`)

```python
#!/usr/bin/env python3
"""A/B test Brief utilization across hook configurations."""

import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass

@dataclass
class TestConfig:
    name: str
    hooks_settings: dict
    claude_md: str  # Path to CLAUDE.md variant

@dataclass
class TestResult:
    config_name: str
    context_get_count: int
    read_count: int
    grep_count: int
    glob_count: int
    ratio: float
    task_completed: bool
    duration_seconds: float

# Test configurations
CONFIGS = [
    TestConfig(
        name="baseline",
        hooks_settings={},  # No hooks
        claude_md="performance-testing/test-files/claude-md-baseline.md"
    ),
    TestConfig(
        name="hooks-v1",
        hooks_settings={...},  # Current hooks
        claude_md="performance-testing/test-files/claude-md-verbose.md"
    ),
    TestConfig(
        name="hooks-v2",
        hooks_settings={...},  # New hooks with additionalContext
        claude_md="__current__"  # Uses current CLAUDE.md
    ),
]

# Test tasks (simple, well-defined)
TEST_TASKS = [
    "Add a --verbose flag to the `brief status` command that shows additional debug info",
    "Find where file descriptions are stored and add a timestamp field",
    "Add input validation to the task create command",
]

def run_test(config: TestConfig, task: str) -> TestResult:
    """Run a single test with given config."""
    # 1. Set up isolated test environment
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy project
        test_dir = Path(tmpdir) / "brief"
        shutil.copytree(".", test_dir, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))

        # Apply hooks config
        settings_path = test_dir / ".claude" / "settings.json"
        settings_path.write_text(json.dumps(config.hooks_settings))

        # Apply CLAUDE.md variant
        shutil.copy(config.claude_md, test_dir / "CLAUDE.md")

        # 2. Run claude with task (would need --print or similar non-interactive mode)
        # This is the tricky part - need to investigate Claude Code's headless options

        # 3. Parse logs
        # 4. Return metrics

def main():
    results = []
    for config in CONFIGS:
        for task in TEST_TASKS:
            result = run_test(config, task)
            results.append(result)

    # Generate comparison report
    ...
```

### 4.3 Headless Execution (CONFIRMED FEASIBLE)

Claude Code supports non-interactive print mode with these key flags:

```bash
claude -p "task description" \
  --settings ./test-configs/hooks-v2.json \  # Load custom hook config
  --output-format json \                      # Structured output
  --max-turns 30 \                            # Limit iterations
  --max-budget-usd 2.00 \                     # Cost cap
  --dangerously-skip-permissions \            # Auto-approve for testing
  --verbose \                                 # Full turn-by-turn output
  --no-session-persistence                    # Clean test runs
```

**Output parsing**: The JSON output includes all tool calls, so we can count:
- Read/Grep/Glob tool invocations
- Bash commands containing `brief context get`

**Test execution flow**:
1. Copy project to temp directory
2. Apply test configuration (hooks, CLAUDE.md)
3. Run `claude -p` with test task
4. Parse JSON output for metrics
5. Clean up and repeat with next config

### 4.4 Manual A/B Protocol (Fallback)

If headless testing isn't feasible:

1. Create two project copies: `brief-a/` and `brief-b/`
2. Apply different hook configs to each
3. Run same task in both simultaneously
4. Use `brief analyze-logs` to compare results

**Test matrix**:
| Config | Hooks | CLAUDE.md | Expected |
|--------|-------|-----------|----------|
| A: Baseline | None | Current | Poor Brief usage |
| B: Hooks-v1 | Current | Current | Moderate improvement |
| C: Hooks-v2 | Fixed PreToolUse + SessionStart | Slim | Best Brief usage |

---

## Implementation Order

### Immediate (This Session)
1. [ ] Create new PreToolUse hook script with `additionalContext`
2. [ ] Create SessionStart hook script
3. [ ] Update `.claude/settings.json` with all hooks
4. [ ] Test hooks work by running a brief session

### Short Term (Next Session)
5. [ ] Add session markers to logging
6. [ ] Create `brief analyze-logs` command
7. [ ] Create slim CLAUDE.md variant for testing

### Medium Term
8. [ ] Research headless Claude Code execution
9. [ ] Build A/B test harness
10. [ ] Run comparison tests
11. [ ] Document findings and iterate

---

## Success Metrics

**Target ratio**: 1 `brief context get` : 2 Read/Grep/Glob calls (vs current 1:8)

**Measurement**:
- Parse `.brief-logs/commands.log` for command counts
- Parse Claude Code session logs for tool usage
- Compare task completion time (if measurable)

**Definition of done**:
- Hooks inject into agent context (verified in session logs)
- Brief:Read ratio improves by 50%+ in testing
- Agent uses Brief FIRST for exploration, Read SECOND for implementation
