# Brief: Context Infrastructure for AI Coding Agents

## Bottom Line

**Brief is a context system that enables AI coding agents to produce correct code.**

When an agent receives a task, Brief provides the exact context needed - architecture, conventions, patterns, execution flows - so the agent's output converges to the intended design rather than drifting from it.

Instead of an indeterminate result from an agent querying and guessing what information it needs to know, the agent calls brief to create a deterministic context package for a given task.

---

## The Problem

AI coding agents fail in predictable ways:

1. **Convergence failure**: The agent produces code that "works" but doesn't match the intended design. Over a long session, implementations drift further from what was wanted.

2. **Context loss**: After context compaction, agents forget what they were doing. Work must be re-explained or starts from scratch.

3. **Missing knowledge**: Agents don't know project conventions, architectural decisions, or implicit rules. They reinvent patterns incorrectly.

4. **No continuity**: A task can't be paused and resumed. Each session starts cold.

The root cause is the same: **agents lack sufficient understanding of the codebase to make correct decisions**.

---

## The Solution

Brief captures and retrieves codebase understanding at the level needed for correct implementation.

**Task-level workflow**:
```
Human: "Add a logout button to the header"
Agent: brief context get "add logout button to header"
→ Returns: relevant components, auth patterns, event conventions, related code
Agent: implements correctly because it understands the system
```

**Planning workflow**:
```
Human: "Implement user authentication"
Agent: decomposes into subtasks, each with focused context
Agent: executes subtasks continuously
→ Coherent implementation that fits the architecture
```

**Maximal test**:
Given Brief's captured context, could someone reproduce the entire codebase? If yes, the understanding is complete.

---

## Elements of Code Understanding

To enable correct implementation, Brief must capture these layers:

### 1. Structural Inventory

**What exists in the codebase.**

- Every file, class, function, method
- Signatures (parameters, types, returns)
- Location (file paths, line numbers)
- Basic relationships (imports, inheritance)

This is mechanical. AST parsing plus some crawling.

### 2. Behavioral Semantics

**What the code actually does.**

Not just "this is a function called `execute`" but:
- What does it accomplish?
- What are its side effects? (writes to DB, mutates state, yields events)
- What are the error conditions and how are they handled?
- What's the happy path vs edge cases?

This requires understanding code, not just parsing it.

### 3. Execution Flows

**How code flows from entry to exit.**

Starting from entry points, trace what happens:
```
User calls Acme().execute("table list", {}, workspace_id)
  → Dispatcher looks up command in Registry
  → TableCommand.execute() called with context
  → WorkspaceManager.get_active_workspace() retrieves workspace
  → Workspace.list_tables() queries DuckDB
  → Results yielded as AcmeEvent objects
```

Each traced path becomes a "scenario" that is reproducible and can be traced through the code.

### 4. Contracts and Invariants

**The rules that must be followed.**

These are implicit constraints that aren't in any single place:
- "All command outputs must be AcmeEvent dataclasses"
- "System tables start with `__acme_` prefix"
- "Commands are auto-discovered from `definitions/` subdirectories"
- "Workspace IDs are UUIDs"

Violating these breaks the system in subtle ways.

### 5. Component Relationships

**How pieces connect and depend on each other.**

Beyond imports:
- **Calls**: What functions invoke what other functions
- **Manages**: What components own and control what entities
- **Uses**: What services or resources are consumed

This enables understanding impact: "If I change X, what breaks?"

### 6. State Model

**What persists and where.**

- Where is state stored? (DuckDB files, config JSONs, in-memory caches)
- What's the lifecycle? (created when, updated how, deleted when)
- What's the schema? (table structures, file formats, data shapes)

### 7. Configuration Surface

**The knobs and settings.**

- Environment variables and their effects
- Config file structure and precedence
- Defaults and how they're overridden
- Feature flags and their implications

### 8. Intent and Rationale

**Why things are designed the way they are.**

- Why is the registry separate from the dispatcher?
- Why do commands yield events instead of returning results?
- What problem does the workspace abstraction solve?
- What alternatives were considered and rejected?

This is the hardest to capture because it's rarely in code.

---

## Indexing and Building Context

```
Phase 1: Map Entry Points
├── What can users do? (CLI commands, Acme methods, API endpoints)
├── For each entry point, what's the signature?
└── What's the expected outcome?

Phase 2: Trace Execution Paths
├── For each major capability, follow the code
├── Document: entry → dispatch → managers → storage → response
└── Capture decision points and branches

Phase 3: Inventory Components
├── For each file: what classes/functions exist?
├── For each class: what's its responsibility?
├── For each function: what does it do, what does it need, what does it return?
└── Build the dependency graph

Phase 4: Extract Contracts
├── What patterns repeat?
├── What assumptions are made?
├── What would break if violated?
└── Document as explicit rules

Phase 5: Synthesize Spec
├── Roll up into coherent architecture description
├── Test: can I explain the whole system from this?
└── Test: could an agent rebuild each component from this description?
```

---

## How Brief Works

### Data Model

Brief stores understanding in `.brief/`:

```
.brief/
├── manifest.jsonl          # Structural inventory
├── relationships.jsonl     # Dependency graph, call graph
├── memory.jsonl            # Nudge-style learned patterns
├── tasks.jsonl             # Beads-style task tracking
├── context/
│   ├── files/              # Per-file understanding
│   ├── modules/            # Per-module understanding
│   ├── paths/              # Execution flow documentation
│   └── contracts.md        # System invariants
```

**manifest.jsonl** - What exists:
```json
{"type": "file", "path": "core/dispatch.py", "hash": "abc123"}
{"type": "class", "name": "Dispatcher", "file": "core/dispatch.py", "line": 42}
{"type": "function", "name": "execute", "class": "Dispatcher", "file": "core/dispatch.py", "line": 87}
```

**relationships.jsonl** - How things connect:
```json
{"type": "imports", "from_file": "core/acme.py", "to_file": "core/dispatch.py"}
{"type": "calls", "from_func": "Acme.execute", "to_func": "Dispatcher.execute_command"}
{"type": "manages", "manager": "WorkspaceManager", "entity": "Workspace"}
```

**memory.jsonl** - Learned patterns:
```json
{"key": "api/workspace", "value": "Use get_active_workspace() not get_current_workspace()"}
{"key": "convention/events", "value": "All outputs must be AcmeEvent dataclasses"}
```

### Context Retrieval

When an agent queries Brief:

```bash
brief context get "add a new command for data export"
```

Brief returns a **context package**:
- **Primary files**: Most relevant to the task (command base class, registry, similar commands)
- **Execution flows**: How commands are discovered, registered, executed
- **Contracts**: Rules commands must follow
- **Patterns**: Conventions for command implementation
- **Related files**: Dependencies and dependents

The context package contains what the agent needs to implement correctly - not everything, and not guesswork.

### Task Management

Brief tracks work to enable continuity:

```bash
brief task create "Implement export command"
brief task start ag-1234 --steps "design,implement,test"
# Work happens...
brief task step-done step-1 --notes "Design: ExportCommand yields RowBatch events"
# Context compacts...
brief resume
# Returns: current task, progress, notes, relevant context
```

Tasks survive context loss. The agent can resume exactly where it stopped.

### Pattern Memory

Brief learns from work:

```bash
brief memory remember "errors/commands" "Wrap execution in try/except, yield ErrorEvent on failure"
brief memory recall --tags "commands"
```

Patterns are surfaced in context when relevant. Institutional knowledge accumulates.

---

## Principles

### 1. Understanding Over Inventory

An inventory tells you what exists. Understanding tells you how it works and why.

**Inventory**: "Here are files with 'command' in the name."

**Understanding**: "Commands are classes in `definitions/` that extend `MetaCommand` and implement `execute()` as a generator yielding `AcmeEvent` objects. They're auto-discovered by the Registry at startup."

### 2. Focused Over Exhaustive

Context should be precisely what's needed - not everything, not a guess.

Too little: Agent makes wrong assumptions.
Too much: Agent drowns in irrelevant detail.
Just right: Agent has exactly what it needs to implement correctly.

### 3. Explicit Over Implicit

Conventions, contracts, and patterns must be captured explicitly. "Everyone knows" is not a context retrieval strategy.

### 4. Verifiable Convergence

The test: Given Brief's context for a task, does the agent produce correct code?

If not, the context is insufficient. Improve it.

---

## Usage

### For Agents

```bash
# Starting work
brief resume                    # What was I doing?
brief context get "my task"     # What do I need to know?

# During work
brief memory remember "key" "pattern"   # I learned something
brief task note ag-1234 "status"        # Save progress

# Completing work
brief task step-done step-1             # Mark progress
brief task done ag-1234                 # Task complete
```

### For Humans

```bash
# Understanding the codebase
brief overview                  # What is this project?
brief tree src/                 # What's the structure?
brief deps core/acme.py       # What does this depend on?

# Directing agents
brief task create "Feature X"   # Define work
brief context get --task ag-1234  # Get context to provide

# Capturing knowledge
brief memory remember "convention/X" "Rule about X"
brief contracts add "invariant" "Must always be true"
```

---

## Success Criteria

Brief succeeds when:

1. **Agents converge**: Given a task and Brief context, agents produce implementations that match intended design.

2. **Work continues**: After context compaction or session restart, agents resume correctly without re-explanation.

3. **Knowledge accumulates**: Patterns learned in one session improve context in future sessions.

4. **Humans can verify**: The captured understanding is readable and auditable.

5. **Maximal test passes**: Given all Brief context, someone could reproduce the codebase architecture.
