# Testing Brief Utilization

This document describes how to test and optimize agent adoption of the `brief context get` command.

## Overview

The goal is to measure and improve how often AI agents use `brief context get` instead of raw Read/Grep/Glob when exploring code. Higher Brief usage means:
- More structured context for the agent
- Better understanding of file relationships
- Fewer wasted tokens on irrelevant code

## Key Metrics

### Brief Ratio

```
Brief Ratio = context_get_calls / (Read + Grep + Glob calls)
```

| Ratio | Interpretation |
|-------|----------------|
| > 0.5 | Excellent - Agent prefers Brief |
| 0.3 - 0.5 | Good - Balanced usage |
| 0.1 - 0.3 | Moderate - Room for improvement |
| < 0.1 | Poor - Agent ignoring Brief |

### What We're Measuring

1. **`brief context get` calls** - Direct usage of Brief's context command
2. **`brief q` calls** - Shortcut for context get
3. **Read tool calls** - Direct file reading
4. **Grep tool calls** - Pattern searching
5. **Glob tool calls** - File discovery

## Quick Commands

### View Current Metrics

```bash
# See metrics from existing logs
brief logs metrics

# Show recent log entries
brief logs show -n 20

# Export for analysis
brief logs export logs.json
```

### Clear and Start Fresh

```bash
# Clear logs before a test run
brief logs clear -f
```

## A/B Testing Framework

### Running Tests

```bash
cd /home/user/dev/brief

# Single test with specific config
python performance-testing/run_test.py --config hooks-v2 --task "Explain the task system"

# Compare two configurations
python performance-testing/run_test.py --compare baseline hooks-v2 --task "Find where files are indexed"

# Run all standard test tasks
python performance-testing/run_test.py --compare baseline hooks-v2 --task all --output results.json

# Keep test environment to review agent changes
python performance-testing/run_test.py --config hooks-v2 --task "Add a feature" --keep-env
```

### Environment Isolation

Each test runs in an **isolated copy** of the project:
- Project is copied to `.brief-logs/test-runs/<run-id>/env/`
- Agent changes don't affect the main repo
- Use `--keep-env` to preserve the environment for review
- Without `--keep-env`, the environment is cleaned up after the test

### Available Configurations

| Config | Hooks | CLAUDE.md | Purpose |
|--------|-------|-----------|---------|
| `baseline` | None | Minimal | Control group |
| `hooks-v1` | UserPromptSubmit only | Minimal | Test single hook |
| `hooks-v2` | Full suite | Streamlined | Current production |
| `hooks-v2-verbose-md` | Full suite | Verbose | Test CLAUDE.md impact |

### Standard Test Tasks

These tasks are designed to require code exploration:

1. "Explain how the task management system works"
2. "Find where file descriptions are stored and generated"
3. "Understand the context retrieval system"
4. "Add a --verbose flag to brief status command"
5. "Find all places where JSONL files are written"

### Interpreting Results

```
============================================================
COMPARISON RESULTS
============================================================
Config          context get  Read/Grep/Glob  Ratio      Duration
------------------------------------------------------------
baseline        1            15              6.67%      45.2s
hooks-v2        5            8               62.50%     38.1s
============================================================
```

**What to look for:**
- Higher Brief Ratio = better
- Fewer total Read/Grep/Glob calls = more efficient
- Similar or lower duration = no performance penalty

## Hook Tuning Guide

### Current Hook Setup

Located in `.claude/settings.json`:

1. **SessionStart** - Primes agent with Brief workflow
2. **UserPromptSubmit** - Reminds to use Brief first
3. **PreToolUse** - Contextual tip when reading code files
4. **PreCompact** - Ensures resume instructions in compaction

### Tuning the Hooks

#### If Brief Ratio is too low:

1. **Strengthen UserPromptSubmit message** - Make it more directive:
   ```bash
   # In scripts/hooks/user-prompt.sh
   echo '[Brief] FIRST run: brief context get "<topic>" - THEN use Read for specific files.'
   ```

2. **Make PreToolUse more prominent**:
   ```python
   # In scripts/hooks/pre-tool-use.sh
   # Change the message to be more actionable
   additionalContext = f"[Action Required] Before reading {filename}, run `brief context get` to understand its role."
   ```

3. **Add to SessionStart** - Include example usage:
   ```
   Example: brief context get "task management" returns 5 relevant files with descriptions
   ```

#### If agents seem confused:

1. **Simplify messages** - Too much instruction can be ignored
2. **Focus on the "why"** - Explain benefit, not just command
3. **Reduce redundancy** - Don't repeat same message in multiple hooks

### Hook Message Guidelines

**DO:**
- Keep messages short (1-2 sentences)
- Be specific about what Brief provides
- Use actionable language ("run X" not "consider X")

**DON'T:**
- Block or deny tool usage (frustrates agents)
- Repeat the same message multiple times per turn
- Use warning/error language (creates anxiety)

## Manual Testing Protocol

When automated testing isn't enough:

### Single Session Test

1. Clear logs: `brief logs clear -f`
2. Start fresh session: `claude`
3. Give exploration task: "Understand how the context system works"
4. Let agent work for 5-10 minutes
5. Check metrics: `brief logs metrics`

### What to Observe

- Does the agent use `brief context get` at the start?
- After the first Read, does it switch to Brief?
- Does the PreToolUse hook message appear?
- Does the agent acknowledge the Brief suggestions?

### Recording Observations

Note in `docs/DEV_NOTES.md`:
- Date and configuration tested
- Brief Ratio achieved
- Qualitative observations
- Ideas for improvement

## Analyzing Claude Code Logs

For deeper analysis, parse the Claude Code session logs:

```bash
# Find session files
ls -la ~/.claude/projects/-home-user-dev-brief/

# Parse with Python (see scripts in earlier analysis)
python3 << 'EOF'
import json
# ... analysis code from BRIEF_UTILIZATION_PLAN.md
EOF
```

## Success Criteria

### Minimum Viable

- Brief Ratio > 0.2 (1 context get per 5 Read/Grep/Glob)
- Agent uses Brief at least once per task

### Target

- Brief Ratio > 0.4 (1 context get per 2.5 Read/Grep/Glob)
- Agent uses Brief FIRST for exploration
- Agent uses Read only for files it intends to edit

### Stretch Goal

- Brief Ratio > 0.6
- Agent explains why it chose Brief or Read
- Agent builds on Brief's context in its reasoning

## Iteration Cycle

1. **Measure** - Run `brief logs metrics` or A/B test
2. **Analyze** - Identify where Brief wasn't used but should have been
3. **Adjust** - Tune hook messages or CLAUDE.md
4. **Test** - Run another test with new configuration
5. **Compare** - Did Brief Ratio improve?
6. **Document** - Record what worked in DEV_NOTES.md

## Reviewing Test Results

### Test Output Location

All test outputs are saved in `.brief-logs/test-runs/`:

```
.brief-logs/test-runs/
├── hooks-v2_20260127-143022/
│   ├── metadata.json      # Test config, metrics, timing
│   ├── claude_output.json # Raw Claude response
│   └── env/               # Test environment (if --keep-env)
│       ├── src/
│       ├── CLAUDE.md
│       └── ... (agent's changes are here)
```

### Reviewing Agent Changes

When using `--keep-env`:

```bash
# See what files the agent modified
ls -la .brief-logs/test-runs/<run-id>/env/

# Diff against original
diff -r src/ .brief-logs/test-runs/<run-id>/env/src/

# Or use git if you init'd the test env
cd .brief-logs/test-runs/<run-id>/env/
git init && git add -A && git status
```

### Parsing Raw Output

The `claude_output.json` contains the full conversation:

```python
import json

with open(".brief-logs/test-runs/<run-id>/claude_output.json") as f:
    for line in f:
        event = json.loads(line)
        if event.get("type") == "assistant":
            # Agent's messages and tool calls
            print(event)
```

## Files Reference

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Hook configuration |
| `scripts/hooks/*.sh` | Hook scripts |
| `CLAUDE.md` | Agent instructions |
| `.brief-logs/commands.log` | Command log |
| `performance-testing/run_test.py` | A/B test runner |
| `performance-testing/test-files/` | CLAUDE.md variants for testing |
| `performance-testing/configs/` | Configuration documentation |
