# Brief System Gap Analysis

**Date**: 2026-01-21
**Purpose**: Document the delta between intended design and actual implementation

---

## Part 1: What Was Actually Intended

Reading across all design documents and between the lines, the core intent is:

### The Real Problem

**AI coding agents fail to produce correct code over extended sessions.** This happens because:

1. **Context loss**: After compaction, agents forget what they were doing
2. **Convergence failure**: Even with context, agents drift from intent - producing code that "works" but doesn't match what was actually wanted
3. **Missing institutional knowledge**: Agents don't know conventions, patterns, or architectural decisions
4. **No task continuity**: Can't give an agent a task, pause, resume, and have it finish correctly

### The Desired Solution

A **context infrastructure** that enables:

- **Task-level usage**: Give agent a task → agent gets exactly the context needed → agent produces correct implementation
- **Planning usage**: Decompose feature into subtasks → agent executes continuously → coherent result
- **Maximal usage**: Context sufficient for someone to reproduce entire codebase

The key insight: **"convergence"** - the code should converge toward the intended design, not drift. This requires the agent to understand not just *what* exists, but *why* it exists that way and *how* it's supposed to work.

---

## Part 2: How the Design Documents Reflect This

### Original Plan (`docs/plans/brief-context-system-plan.md`)

The design document captures intent reasonably well:

**Correct Understanding**:
- "Complete, reproducible understanding" ✓
- "Solve the convergence problem" ✓
- "Precisely scoped context for each task" ✓
- Example `brief context "refactoring the table command"` shows exactly what's wanted

**Key Schema in Design**:
```json
{"type": "imports", "from_file": "...", "to_file": "...", "imports": ["Registry"]}
{"type": "calls", "from_func": "Acme.execute", "to_func": "Dispatcher.execute_command", ...}
{"type": "manages", "manager": "WorkspaceManager", "entity": "Workspace", "operations": [...]}
```

This shows **three relationship types** were intended:
- `imports` - what files import what
- `calls` - what functions call what
- `manages` - what components own what

**Design Gaps**:
1. Overemphasis on checkpoints for surviving compaction; the deeper issue is context *quality*, not persistence
2. LLM descriptions underspecified - just "generate descriptions" without specifying depth
3. No explicit "convergence mechanism" - tasks + context assumed to solve convergence without verification

---

### Checkpoint Plans (`brief/docs/dev-plan/`)

The checkpoint plans show **progressive narrowing** from intent:

| Phase | Design Intent | Checkpoint Scope |
|-------|---------------|------------------|
| 1 | "Build dependency graph (what imports/calls what)" | "RelationshipExtractor finds **import** relationships" |
| 3 | "Generate semantic descriptions of code units" | "Falls back to placeholder descriptions" |
| 7 | "Call graph following" | "Static call graph may be incomplete - depends on relationships.jsonl" |
| 9 | "Generate descriptions for core modules" | "PARTIAL (manual descriptions not needed for basic bootstrap)" |

**Critical Deviations in Checkpoints**:

1. **Phase 1 narrows "relationships" to just imports**:
   - Design: `imports + calls + manages`
   - Checkpoint: `imports` only
   - Impact: Execution tracing impossible without call relationships

2. **Phase 7 acknowledges the gap but doesn't fix it**:
   - Notes "depends on relationships.jsonl quality"
   - But Phase 1 already limited relationships to imports
   - Result: Traces can't follow call chains

3. **Phase 9 marks things "PARTIAL" and moves on**:
   - "Manual descriptions not needed for basic bootstrap"
   - "Semantic search requires embedding generation (optional enhancement)"
   - This punts the hard problems

---

### README (`brief/README.md`)

The README documents **what exists**, not what was intended:

**Accurate Documentation**:
- Three tiers (local, LLM, embeddings) - correct
- Commands work as documented - correct
- Data structures match - correct

**Misleading Claims**:
- "Context Retrieval - Get relevant files, patterns, and contracts for any task"
  - Reality: Returns keyword-matched files, not semantically relevant ones
- "Execution path tracing"
  - Reality: Shows entry point only, can't follow call chain

---

## Part 3: Delta Analysis

### Concept → Design Document

| Concept | Design Document | Gap |
|---------|-----------------|-----|
| "Complete reproducible understanding" | 7 analysis phases + descriptions | ✓ Captured |
| "Convergence" - code matches intent | Tasks + context assumed to solve | ⚠️ Mechanism unclear |
| Call graph for execution flow | `calls` relationship type | ✓ Captured |
| Component ownership | `manages` relationship type | ✓ Captured |
| Semantic code understanding | LLM descriptions | ⚠️ Underspecified depth |

**Design captured intent reasonably well**, but underspecified:
- How deep descriptions need to be
- How to verify context is sufficient
- What makes context "focused" vs "everything"

### Design Document → Checkpoint Plans

| Design | Checkpoint | Gap |
|--------|------------|-----|
| Extract imports + calls + manages | Extract imports only (Phase 1) | ❌ Major |
| Deep semantic descriptions | Placeholder fallback acceptable (Phase 3) | ⚠️ |
| Trace execution paths via call graph | Static analysis from manifest (Phase 7) | ❌ Blocked by Phase 1 |
| Full bootstrap with descriptions | Marked "PARTIAL" (Phase 9) | ⚠️ Deferred |

**Checkpoints narrowed scope significantly**, especially:
- Relationship extraction reduced to imports only
- Description depth became optional
- Tracing became non-functional due to missing calls

### Checkpoint Plans → Implementation

| Checkpoint | Implementation | Gap |
|------------|----------------|-----|
| Import relationships | ✓ Works | None |
| Call relationships | Model exists, never populated | ❌ |
| Manages relationships | Model exists, never populated | ❌ |
| Tracer follows callees | Looks for calls in relationships.jsonl | ❌ No calls exist |
| Semantic search | Keyword matching or shallow embeddings | ⚠️ |

**Implementation matches checkpoints** but checkpoints were already reduced from design.

### Overall: Concept → Implementation

| Layer | Intended | Actual | Status |
|-------|----------|--------|--------|
| **Structural Inventory** | Files, classes, functions | ✓ Works | ✅ |
| **Import Graph** | Who imports what | ✓ Works | ✅ |
| **Call Graph** | Who calls what | Model exists, empty | ❌ |
| **Ownership Graph** | Who manages what | Model exists, empty | ❌ |
| **Behavioral Understanding** | What code does and how | Shallow summaries | ⚠️ |
| **Execution Paths** | Full call chains | Entry point only | ❌ |
| **Contracts** | Naming + invariants | Naming patterns only | ⚠️ |
| **Task Context** | Sufficient for correct implementation | Keyword-matched files | ❌ |

---

## Part 4: Root Cause Analysis

### Why Did This Happen?

1. **Phase 1 made a critical scoping decision**: "Import relationships" instead of "all relationships". This propagated through everything.

2. **"It works" vs "It achieves the goal"**: Each phase passed its tests, but tests verified features exist, not that they solve the convergence problem.

3. **Optional became never**: LLM descriptions, semantic search, deep analysis were all marked "optional" and deferred. They're the hard parts.

4. **No end-to-end validation**: Phase 9 "bootstrap" verified commands work, not that context enables convergence.

### The Fundamental Gap

**A codebase index was built. A codebase understanding system was needed.**

| Index | Understanding |
|-------|---------------|
| What files exist | What files *do* |
| Who imports whom | Who calls whom and why |
| Naming conventions | Architectural invariants |
| Keyword search | Semantic comprehension |

An index can tell you: "Here are files with 'command' in the name."

Understanding can tell you: "Command dispatch works like this: CLI parses → Registry resolves → Dispatcher executes → Events yield. To add a command, create a class in definitions/, extend MetaCommand, implement execute() generator."

---

## Part 5: What Would Fix It

To achieve the actual goal:

### Priority 1: Extract Call Relationships

The models already exist (`CallRelationship` in models.py). The relationship extractor needs to populate them.

```python
# In analysis/relationships.py
# Currently: only ImportRelationship
# Needed: also CallRelationship
{"type": "calls", "from_func": "TaskManager.create_task", "to_func": "generate_task_id", ...}
```

This unblocks execution tracing.

### Priority 2: Deepen Descriptions

Current descriptions answer: "What is this file?"

Needed descriptions answer: "How does this work? Why is it designed this way? What would break if I changed it?"

### Priority 3: Context Retrieval That Understands

Current: keyword matching on file paths

Needed: semantic matching on *meaning* with relationship traversal

Query: "How do commands get executed?"
Should return: `dispatch.py`, `registry.py`, the call chain between them, the relevant contracts, the patterns

### Priority 4: Validate Convergence

Add a way to verify: "Given this context, could an agent correctly implement X?"

---

## Part 6: Summary

### What Was Wanted
A context system where AI agents can:
1. Receive a task
2. Get sufficient context
3. Produce code that converges to correct implementation

### What Was Built
A file index with:
- Structural inventory (good)
- Import tracking (good)
- Keyword search (inadequate)
- Shallow descriptions (inadequate)
- Non-functional execution tracing (broken)

### The Gap
**Inventory ≠ Understanding**

The system knows *what* exists but not *how it works* or *why it's designed that way*. An agent using Brief gets a list of possibly-related files, not the architectural knowledge needed to implement correctly.

### Path Forward
1. Extract call relationships (enables tracing)
2. Deepen descriptions (enables understanding)
3. Improve retrieval (enables focused context)
4. Validate with real tasks (proves convergence)

The building blocks are solid. The integration that makes "telescoping context" and "convergence" work needs to be completed.
