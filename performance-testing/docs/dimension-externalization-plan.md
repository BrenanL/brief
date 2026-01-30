# Dimension Externalization Plan

**Created**: 2026-01-30
**Status**: Design notes for future implementation

---

## Problem

Test dimensions are currently defined inline in `run_test.py` as Python dataclasses with no analysis metadata. The analysis script (`analyze.py`) has no way to know which dimensions are valid for which analysis categories — filtering is done manually via ad-hoc scripts.

As the system grows to hundreds of tests and becomes a general-purpose agent testing framework (not Brief-specific), we need structured definitions with metadata that analysis tools can consume automatically.

---

## Proposed Structure

### Per-dimension YAML files

```
performance-testing/
  dimensions/
    feature-addition.yaml
    feature-extension.yaml
    bug-investigation.yaml
    cross-cutting.yaml
    integration.yaml
    pattern-following.yaml
    documentation.yaml
    multi-task.yaml
    resume.yaml
```

### Schema

```yaml
# dimensions/feature-addition.yaml
id: feature-addition
name: "Feature Addition (Greenfield)"
description: "Task where agent must figure out WHERE to add code"

prompt: |
  Add a 'brief logs archive' command that moves old log entries
  to an archive file. It should take a --days flag to specify how
  many days of logs to keep active (default 30). The archived logs
  should go to .brief-logs/archive/ with a timestamp in the filename.

# Optional setup for dimensions that need pre-configured state
setup:
  type: none                # "none", "multi-task", "resume", or custom
  # tasks: [...]            # Only for multi-task/resume types

# Analysis metadata — consumed by analyze.py for automatic filtering
analysis:
  # Which analysis categories this dimension is valid for
  categories:
    q1_efficiency: true       # "Does the tool help?" — fair A/B comparison
    q2_config_tuning: true    # "Which config works best?" — brief ratio
    q3_workflow_adoption: false  # "Does the agent follow the workflow?"

  # Which metrics are meaningful for this dimension
  metrics:
    - speed
    - turns
    - tool_calls
    - exploration_pattern

  # Free-form tags for ad-hoc grouping and filtering
  tags:
    - coding
    - greenfield
    - exploration-heavy

  # Why certain categories are excluded (documentation for reviewers)
  exclusion_notes: ""
```

Resume example (Q1-excluded):

```yaml
id: resume
name: "Resume Behavior"
description: "Set up partial state, prompt with 'resume'"
prompt: "resume"

setup:
  type: resume
  tasks:
    - title: "Add input validation to brief task create"
      desc: "Add validation to ensure task titles are not empty and descriptions are under 1000 characters"
      status: in_progress

analysis:
  categories:
    q1_efficiency: false
    q2_config_tuning: true
    q3_workflow_adoption: true
  metrics:
    - compliance
  tags:
    - workflow-adoption
    - brief-specific
  exclusion_notes: >
    Q1 excluded: The null CLAUDE.md has no concept of "resume" in
    the Brief task sense. Null agents complete in ~27s by not engaging,
    making duration comparisons meaningless.
```

---

## Changes to run_test.py

1. Add a `load_dimensions(path)` function that reads YAML files from a directory
2. Extend `TestDimension` dataclass with an `analysis` field (dict or sub-dataclass)
3. Attach analysis metadata to each job's `metadata` dict so it's preserved in the manifest
4. Add `--dimensions-dir` flag (default: `performance-testing/dimensions/`)
5. Keep backward compat: if no YAML files found, fall back to inline DIMENSIONS dict during transition

The `make_jobs()` function would include the analysis metadata in each job's manifest entry, so analyze.py can filter without needing to re-read dimension files.

---

## Changes to analyze.py

1. Read analysis metadata from manifest entries (attached at job creation time)
2. Add filtering flags:
   - `--category q1` / `--category q2` — filter by analysis category
   - `--tags coding,exploration-heavy` — filter by tags
   - `--exclude-dimensions resume,multi-task` — explicit exclusion (override)
3. Aggregation should always average trials per config+dimension cell first, then average across cells (see "Aggregation correctness" below)

---

## Aggregation Correctness

When multiple trials exist for the same config+dimension pair, the analysis must:

1. Average all trials for each (config, dimension) cell into a single data point
2. Use those cell-level averages for cross-dimension aggregates

This prevents over-weighting dimensions that happen to have more repeat runs.

Example: if feature-addition has 3 trials and bug-investigation has 1, the overall config average should weight both dimensions equally, not give feature-addition 3x the influence.

---

## Generalization Notes (Beyond Brief)

The system is intended to become a general-purpose agent testing framework. To support that:

- Dimension files should not assume Brief-specific signals. The `analysis.metrics` field should be extensible — Brief tests measure `context_get` calls, but other tools would measure different things.
- Consider a `signals` section in the dimension file that declares what to look for in output (e.g., "count bash commands matching pattern X"). This replaces the hardcoded `brief context get` detection in `parse_claude_output()`.
- Configs are similarly Brief-specific today (CLAUDE.md variants, hook variants). A generic config system would define arbitrary environment setups.
- The orchestrator (`orchestrator.py`) is already tool-agnostic — it just runs Claude Code with parameters. The Brief-specific parts are isolated to `run_test.py` and `analyze.py`.

---

## Implementation Priority

1. **Immediate**: Add `--exclude-dimensions` flag to analyze.py and fix aggregation to average per-cell first
2. **Short-term**: Create YAML dimension files alongside inline definitions (dual-source during transition)
3. **Medium-term**: run_test.py loads from YAML, inline definitions removed
4. **Later**: Generalize signal detection, config system, and metric definitions
