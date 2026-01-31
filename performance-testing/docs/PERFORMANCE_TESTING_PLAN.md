# Performance Testing Plan v2

**Created**: 2026-01-28
**Purpose**: Comprehensive A/B testing to determine optimal configuration for Brief utilization

---

## Executive Summary

This plan defines a rigorous testing framework to answer the core question:
**"Can we convince the model to prefer using Brief over its default file exploration patterns?"**

We test 7 configurations across 9 testing dimensions, measuring Brief utilization ratios and patterns.

---

## Naming Conventions

| Name | Description |
|------|-------------|
| **null** | CLAUDE.md with NO Brief references (true control) |
| **baseline** | Original manually-crafted CLAUDE.md with Brief workflow instructions |

---

## Configuration Matrix (7 Configs)

| Config ID | CLAUDE.md | Hooks | Purpose |
|-----------|-----------|-------|---------|
| `null-no-hooks` | Null | None | True control - no Brief guidance |
| `null-pretool` | Null | PreToolUse only | Isolate PreToolUse hook impact |
| `null-userprompt` | Null | UserPromptSubmit only | Isolate UserPromptSubmit hook impact |
| `null-full-hooks` | Null | Full suite (4 hooks) | Hooks without documentation |
| `baseline-no-hooks` | Baseline | None | Isolate documentation impact |
| `baseline-pretool` | Baseline | PreToolUse only | Original "base case" setup |
| `baseline-full-hooks` | Baseline | Full suite (4 hooks) | Maximum guidance |

### Hook Definitions

**Full suite** includes:
- SessionStart: Fires on startup/resume/compact
- UserPromptSubmit: Fires on every user prompt
- PreToolUse: Fires before Read/Grep/Glob on code files
- PreCompact: Fires before context compaction

---

## Testing Dimensions (Phase 1: 9 Dimensions)

### 1. Feature Addition (Greenfield)
- **What**: Task where agent must figure out WHERE to add code
- **Why**: Requires understanding project structure, patterns, conventions
- **Signal**: Does agent use Brief to understand architecture before writing?
- **Example prompts**: "Add X feature to the system"

### 2. Multi-Task Sequential
- **What**: Queue 3-5 Brief tasks, tell agent to complete all
- **Why**: Tests Brief usage persistence over longer session
- **Signal**: Does Brief ratio decline with task number? Does agent lose track?
- **Setup**: Pre-create tasks in Brief before running test

### 3. Resume Behavior
- **What**: Set up partial state, prompt with "resume" or "continue"
- **Why**: Tests if agent follows `brief resume` pattern
- **Signal**: Does agent run `brief resume`? Does it find active task?
- **Setup**: Pre-create tasks, mark one as active

### 4. Feature Extension
- **What**: Building on existing functionality
- **Why**: Agent must understand current implementation before extending
- **Signal**: Does agent Brief-first or Read-first when exploring existing code?

### 5. Bug Investigation
- **What**: Agent must trace through code to find root cause
- **Why**: Pure exploration, no implementation
- **Signal**: Exploration pattern - Brief vs grep/read chains

### 6. Cross-Cutting Concern
- **What**: "Add X to all Y" (e.g., "add validation to all commands")
- **Why**: Requires finding all relevant locations
- **Signal**: Discovery method - Brief context vs grep patterns

### 7. Integration Task
- **What**: "Connect X to Y" or "Make X work with Y"
- **Why**: Requires understanding two separate systems
- **Signal**: Does agent Brief both areas or just one?

### 8. Pattern Following
- **What**: "Follow the existing pattern for X when implementing Y"
- **Why**: Agent must identify and understand existing patterns
- **Signal**: Does agent ask Brief for related implementations?

### 9. Documentation/Explanation
- **What**: "Document how X works" or "Explain X"
- **Why**: Requires comprehensive understanding
- **Signal**: Does agent use Brief's descriptions or generate from scratch?

---

## Postponed Dimensions (Phase 2+)

| Dimension | Reason for Postponement |
|-----------|------------------------|
| Unfamiliar Codebase Simulation | Assumes Brief is already set up |
| Refactoring | Often driven by IDE/tool support |
| Context Pressure | Hard to control experimentally |
| Iterative Refinement | Noisy signal from conversation dynamics |

---

## Test Implementation

### Architecture

Tests use a general-purpose **Claude Code Orchestrator** (`orchestrator.py`) that manages:
- Git clone-based repo isolation (each test gets its own clone)
- Worker pool with configurable parallelism
- Append-only JSONL manifest for tracking
- Process group cleanup on interrupt

See `ORCHESTRATOR_DESIGN.md` for full architecture.

### File Structure

```
performance-testing/
├── orchestrator.py               # General-purpose Claude Code orchestrator
├── run_test.py                   # Brief test definitions + job generation
├── analyze.py                    # Post-run analysis and reporting
├── config.json                   # Orchestrator configuration
├── test_orchestrator.py          # Orchestrator tests
├── PERFORMANCE_TESTING_PLAN.md   # This document
├── ORCHESTRATOR_DESIGN.md        # Orchestrator architecture
├── TESTING_GUIDE.md              # How to run tests
├── results/
│   └── manifest.jsonl            # Test run tracking (append-only)
├── configs/                      # Config documentation (historical)
└── test-files/
    ├── claude-md-null.md         # No Brief references (control)
    └── claude-md-baseline.md     # Original Brief instructions
```

### Environment Setup

Before running tests:
1. Run `brief analyze refresh` to update analysis
2. Run `brief describe batch --limit 100 --include-other` to generate descriptions
3. Commit changes: tests clone from HEAD
4. Ensure temp dir exists: `mkdir -p /home/user/tmp/brief-performance-testing`

### Results Collection

Results are tracked via JSONL manifest. Analysis is done post-run by parsing
the manifest and Claude output files from each test's work directory.

See `TESTING_GUIDE.md` for usage.

---

## Test Prompts by Dimension

### Dimension 1: Feature Addition (Greenfield)
```
"Add a 'brief logs archive' command that moves old log entries to an archive file.
It should take a --days flag to specify how many days of logs to keep active."
```

### Dimension 2: Multi-Task Sequential
**Setup**: Pre-create 3 tasks:
1. "Add --json flag to brief status command"
2. "Add brief task priority command to set task priorities"
3. "Add brief context stats command to show context coverage statistics"

**Prompt**: "You have Brief tasks queued. Run `brief task list` to see them, then complete all pending tasks in order."

### Dimension 3: Resume Behavior
**Setup**: Create task and mark as in_progress:
- Task: "Add input validation to the brief task create command"
- Status: in_progress

**Prompt**: "resume"

### Dimension 4: Feature Extension
```
"Extend the brief describe command to support a --format flag that can output
descriptions as JSON instead of markdown."
```

### Dimension 5: Bug Investigation
```
"The brief context get command sometimes returns empty results even when relevant
files exist. Investigate why this might happen and identify the root cause.
Don't fix it yet, just report your findings."
```

### Dimension 6: Cross-Cutting Concern
```
"Add input validation to all Brief CLI commands that accept file paths.
Validate that paths exist and are within the project directory."
```

### Dimension 7: Integration Task
```
"Make the task system integrate with the logging system so that task state
changes (create, start, done) are recorded in the command log."
```

### Dimension 8: Pattern Following
```
"Add a new 'brief contracts export' command following the same pattern used
by other export/output commands in the codebase."
```

### Dimension 9: Documentation/Explanation
```
"Document how the context retrieval system works. Explain the flow from
a 'brief context get' call through to the returned context package."
```

---

## Additional Variables for Future Testing

### Model Variation
- `--model sonnet` vs `--model opus`
- Hypothesis: More capable models might ignore instructions more?

### System Prompt Injection
- `--append-system-prompt "Always use brief context get before exploring code"`
- Could be more direct than hooks

### Tool Restrictions
- `--allowed-tools "Bash Read Edit Write"` (remove Grep/Glob)
- Force different exploration patterns

### Turn Limits
- 15 turns vs 30 turns vs 50 turns
- Test if Brief usage degrades with session length

### Hook Message Variations
- Different wording in hook messages
- Different levels of directiveness

---

## Success Metrics

### Primary Metric: Brief Ratio
```
Brief Ratio = context_get_calls / (context_get_calls + Read + Grep + Glob calls)
```

| Ratio | Interpretation |
|-------|----------------|
| > 0.5 | Excellent - Agent prefers Brief |
| 0.3 - 0.5 | Good - Balanced usage |
| 0.1 - 0.3 | Moderate - Room for improvement |
| < 0.1 | Poor - Agent ignoring Brief |

### Secondary Metrics
- First exploration action (Brief vs Read/Grep)
- Brief usage in first 5 turns vs last 5 turns
- Task completion rate
- Total exploration calls

---

## Execution Plan

### Phase 1 Tasks

1. Rename files: baseline → null, verbose → baseline
2. Create null CLAUDE.md file (no Brief references)
3. Update run_test.py with all 7 configurations
4. Update test environment setup to copy .brief/ (excluding tasks.jsonl)
5. Implement multi-task setup functionality
6. Implement resume scenario setup
7. Run all 7 configs × 9 dimensions = 63 tests
8. Analyze and report results

### Run Order

Tests will be run config-by-config to minimize setup overhead:
1. null-no-hooks (all 9 dimensions)
2. null-pretool (all 9 dimensions)
3. null-userprompt (all 9 dimensions)
4. null-full-hooks (all 9 dimensions)
5. baseline-no-hooks (all 9 dimensions)
6. baseline-pretool (all 9 dimensions)
7. baseline-full-hooks (all 9 dimensions)

---

## Results Analysis

After all tests complete:
1. Generate aggregate Brief ratios per config
2. Compare configs within same CLAUDE.md (isolate hook impact)
3. Compare configs within same hooks (isolate docs impact)
4. Identify dimension-specific patterns
5. Statistical significance assessment
6. Recommendations for production configuration

---

## Appendix: Historical Context

Previous testing (2026-01-27) showed:
- hooks-v1 (verbose CLAUDE.md + UserPromptSubmit): 83.3% avg Brief ratio
- hooks-v2 (streamlined CLAUDE.md + full hooks): 38.9% avg Brief ratio
- hooks-v3 (verbose CLAUDE.md + full hooks): 44.4% avg Brief ratio

Key finding: Verbose documentation appeared more impactful than hook complexity.

This plan expands testing to isolate variables and increase sample size.
