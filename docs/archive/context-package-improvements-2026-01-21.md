# Context Package Improvements - Session Notes

**Date**: 2026-01-21
**Status**: Implemented core improvements, identified future work

---

## What We Set Out To Do

Test whether Brief's context packages result in **convergent code generation** - when an agent uses Brief context, does it produce code that fits the codebase correctly?

### The Original Vision (7 Layers of Understanding)

We defined what "complete reproducible understanding" would require:

1. **Structural Inventory** - files, classes, functions, signatures, imports, call sites
2. **Behavioral Semantics** - what functions actually do, side effects, error handling
3. **Execution Paths** - traced flows from entry to exit
4. **Contracts and Invariants** - implicit rules that must be followed
5. **State Model** - where state is stored, lifecycle, schema
6. **Configuration Surface** - env vars, config structure
7. **Intent and Rationale** - the "why" behind decisions

---

## What We Tested

### Simulation Setup

Created a test environment at `~/t/brief-test/` with:
- Brief codebase copy
- Local venv with brief installed
- CLAUDE.md with Brief usage instructions
- Initialized .brief with traces, contracts, memory patterns

### Test 1: "Add timing to context retrieval"

**Prompt**: "Add execution time tracking to context retrieval. When `brief context get` runs, it should show how long each step takes."

**Result**: ✅ SUCCESS
- Agent's first action was `brief context get "adding timing to context retrieval"`
- Found correct files (retrieval/context.py, commands/context.py)
- Implementation matched codebase style
- All tests passed

### Test 2: "Add --json flag to context get" (Task-driven)

**Prompt**: Created task first with `brief task create`, then told agent to "resume"

**Result**: ✅ SUCCESS
- Agent ran `brief task list` to discover the task
- Ran `brief context get` multiple times for different angles
- Implemented correctly with `to_dict()` method and `--json` flag
- Marked task done with `brief task done`

### Key Finding

**The context packages worked** - agents found the right files and produced convergent code. But we identified gaps between what we designed and what we delivered.

---

## Gaps Identified

### What We Collected vs What We Displayed

| Data | Collected? | Displayed? | Gap |
|------|------------|------------|-----|
| File paths | ✅ | ✅ | None |
| LLM descriptions | ✅ | ✅ | None |
| Classes list | ✅ | ❌ | Not rendered |
| Functions list | ✅ | ❌ | Not rendered |
| Import relationships | ✅ | ❌ | Not rendered |
| Execution paths | ✅ Names only | ❌ Content not shown | **Fixed** |
| Call relationships | ✅ | ❌ | Not rendered |

### The Execution Paths Problem

**Before**: Context showed just path names
```
## Execution Paths
- context-retrieval
- manifest-search
```

Agent would need to run `brief trace show context-retrieval` separately to see the actual flow.

**After** (implemented): Context shows inline flow diagrams
```
## Execution Flows

### full-context-retrieval
Entry: `build_context_for_query` (retrieval/context.py)
  Build a context package for a task description.
  → `search_manifest` - Search manifest entries by query terms.
  → `read_jsonl` (storage.py) - Read records from a JSONL file.
  → `recall_for_context` (memory/store.py) - Get memory patterns.
  → `detect_all` (contracts/detector.py) - Detect all contracts.
  Files: retrieval/context.py, storage.py, memory/store.py, contracts/detector.py
```

---

## Changes Implemented

### 1. `to_flow()` method on ExecutionPath (tracer.py)

Generates compact flow diagram:
- Entry point with file
- Call chain with arrows (→)
- File only shown when different from parent
- Brief descriptions inline
- Files list at bottom

### 2. `load_path_as_object()` method on PathTracer (tracer.py)

Parses saved markdown traces back into ExecutionPath objects so we can regenerate flow diagrams.

### 3. Updated `get_relevant_paths()` (context.py)

Changed return type from `list[str]` (just names) to `list[dict[str, str]]` with `{name, flow}` containing the flow diagram.

### 4. Updated `ContextPackage` (context.py)

- Changed `execution_paths` type to `list[dict[str, str]]`
- Updated `to_markdown()` to render flows inline
- Section renamed from "Execution Paths" to "Execution Flows"

### 5. Updated CLAUDE.md for agents

- Made `brief resume` conditional (only when user asks to continue)
- Made `brief context get` the primary action for new tasks
- Removed unused commands (memory recall/remember, task notes)
- Added "use repeatedly" encouragement

---

## Lazy Context Generation (Future Work)

### The Problem

Currently:
- LLM descriptions are generated manually with `brief describe file X.py`
- Traces are generated manually with `brief trace create`
- If files change, descriptions become stale
- Regenerating everything on every change is wasteful

### The Solution: Generate on Observation

When `brief context get` runs:

```
1. Find relevant files/traces/contracts
2. For each item:
   a. Does description/trace exist?
   b. If no → generate it (lazy creation)
   c. If yes → is it stale? (file modified since description created)
   d. If stale → regenerate it (lazy refresh)
3. Include fresh content in package
```

### Benefits

- First query for a topic is slower (generates what's needed)
- Subsequent queries are fast (cached)
- Descriptions stay fresh without wasteful regeneration
- No manual `brief describe` commands needed

### Implementation Notes

Need to track:
- `description_generated_at` timestamp for each file description
- `file_modified_at` from filesystem
- Compare: if `file_modified_at > description_generated_at` → stale

For traces:
- Track which functions are in each trace
- If any function's file changed → trace may be stale
- Could also track manifest hash to detect structural changes

---

## Other Future Improvements

### 1. Show Function Signatures in Context

Currently we collect class/function info but don't render it. Could add:

```
### retrieval/context.py
**Classes**: ContextPackage
**Functions**:
- `build_context_for_query(brief_path, query, ...) → ContextPackage`
- `search_manifest(brief_path, query, max_results) → list[tuple]`
```

### 2. Smarter Call Graph Expansion

Current tracer only follows first 3 callees, which often catches external deps like `typer.Option` instead of codebase functions.

Fix: Filter callees to only follow functions that exist in the manifest.

### 3. Task-Specific Contracts

Current contracts are generic (get_* naming, generator pattern). Could filter/rank by relevance to the specific files being modified.

### 4. Line Numbers

We deliberately excluded line numbers from flow diagrams because they go stale during editing. Could explore:
- Showing them but marking as "approximate"
- Looking them up fresh on each context get
- Using function names as stable anchors instead

---

## Files Changed

| File | Change |
|------|--------|
| `brief/tracing/tracer.py` | Added `to_flow()`, `load_path_as_object()` |
| `brief/retrieval/context.py` | Updated `get_relevant_paths()`, `ContextPackage`, `to_markdown()` |

---

## Testing Commands

```bash
# From the brief directory
source ../.venv/bin/activate

# Reinitialize (if needed)
rm -rf .brief
brief init
brief analyze dir . --base .
brief contracts detect

# Create comprehensive traces
python -c "
from pathlib import Path
from brief.tracing.tracer import PathTracer, ExecutionPath, PathStep
# ... (see session for full script)
"

# Test context get
brief context get "context package building flow"
brief context get "adding a new feature"

# Run tests
pytest tests/ -v -s
```

---

## Summary

**What worked**: Agents using `brief context get` found the right files and produced code that fit the codebase.

**What we fixed**: Execution paths now show inline flow diagrams instead of just names.

**What's next**: Lazy generation, function signatures, smarter call graph expansion.

The core hypothesis is validated: **Brief's context packages do lead to convergent code generation.**
