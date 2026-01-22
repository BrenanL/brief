## How I Would Capture Complete Reproducible Understanding

If I had to ensure another agent could reproduce Acme perfectly, I'd need to capture these layers:

### 1. Structural Inventory (the "what exists")

* Every file, class, function, method
* Signatures (parameters, return types)
* Import relationships
* Where things are instantiated/called from

This is mechanical. AST parsing plus some crawling.

### 2. Behavioral Semantics (the "what it does")

* What each function *actually accomplishes* (not just its name)
* Side effects (writes to DB, mutates state, yields events)
* Error conditions and how they're handled
* The "happy path" vs edge cases

This requires reading and understanding code.

### 3. Execution Paths (the "how it flows")

Starting from entry points, trace what happens:

* User calls `Acme().execute("table list", {}, workspace_id)`
* → Dispatcher looks up command in Registry
* → TableCommand.execute() is called with context
* → WorkspaceManager.get_active_workspace() retrieves workspace
* → Workspace.list_tables() queries DuckDB
* → Results yielded as AcmeEvent objects
* → Events returned to caller

Each traced path becomes a "scenario" that must be reproducible.

### 4. Contracts and Invariants (the "rules")

* "All events must be AcmeEvent dataclasses"
* "Workspace IDs are UUIDs"
* "System tables start with `__acme_`"
* "Commands are auto-discovered from `definitions/` subdirectories"

These are the implicit rules that aren't in any single place but must be followed everywhere.

### 5. State Model (the "what persists")

* Where is state stored? (DuckDB files, config JSONs, in-memory)
* What's the lifecycle? (created when, deleted when)
* What's the schema? (table structures, file formats)

### 6. Configuration Surface (the "knobs")

* Environment variables
* Config file structure
* Defaults and overrides

### 7. Intent and Rationale (the "why")

* Why is the registry designed this way?
* Why separate managers from commands?
* What problem does the event streaming solve?

This is the hardest to capture because it's often not in the code.

---

## The Process I'd Follow

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

## Proposed Tool Design: "Brief"

Let me propose a concrete design that combines your preferences:

### Storage Structure

```
.brief/
├── manifest.jsonl          # Structural inventory (files, classes, functions)
├── relationships.jsonl     # Dependency graph, call graph
├── tasks.jsonl             # Beads-style task tracking
├── memory.jsonl            # Nudge-style learned patterns
├── embeddings.db           # SQLite with vector embeddings (for search)
├── context/
│   ├── modules/
│   │   ├── core.acme.md
│   │   ├── core.registry.md
│   │   └── ...
│   ├── files/
│   │   ├── core_acme.py.md
│   │   └── ...
│   ├── paths/
│   │   ├── workspace-creation.md
│   │   ├── command-dispatch.md
│   │   └── ...
│   └── contracts.md
└── spec.md
```

### JSONL Record Types

**manifest.jsonl**

```json
{"type":"file","path":"acme/core/acme.py","module":"core","context_ref":"context/files/core_acme.py.md"}
{"type":"class","name":"Acme","file":"acme/core/acme.py","line":42,"methods":["execute","create_workspace"],"description":"Main embedded interface for AI agents"}
{"type":"function","name":"execute","class":"Acme","file":"acme/core/acme.py","line":87,"params":[],"returns":"Generator[AcmeEvent]","calls":["dispatch.execute_command"]}
```

**relationships.jsonl**

```json
{"type":"imports","from":"acme/core/acme.py","to":"acme/core/registry.py"}
{"type":"calls","from":"Acme.execute","to":"Dispatcher.execute_command","context":"command dispatch"}
{"type":"manages","manager":"WorkspaceManager","entity":"Workspace"}
```

**tasks.jsonl**

```json
{"id":"ag-001","status":"done","title":"Generate manifest for core module"}
{"id":"ag-002","status":"ready","title":"Trace workspace creation path"}
{"id":"ag-003","status":"blocked","title":"Describe registry internals","depends":["ag-001"]}
```

**memory.jsonl**

```json
{"key":"api/workspace_manager","pattern":"Use get_active_workspace() not get_current_workspace()","confidence":1.0}
{"key":"convention/events","pattern":"All command outputs must be AcmeEvent dataclasses","confidence":1.0}
```

### CLI / DSL Commands

```bash
brief init
brief analyze acme/core/
brief analyze acme/core/acme.py
brief trace "workspace creation"
brief describe acme/core/acme.py
brief contracts extract
brief spec generate

brief context "working on table commands"
brief related acme/core/registry.py
brief path "how does execute() work"

brief task list
brief task ready
brief task create "Refactor registry"
brief task done ag-001

brief remember "pattern" "description"
brief recall "workspace"

brief show manifest
brief show relationships
brief show spec
```

### Agent Instructions (CLAUDE.md)

```markdown
This project uses Brief for context management.

Before starting work:
1. brief context "<what you're working on>"
2. brief recall "<area>"
3. brief task list

When you learn something:
- brief remember "<category>" "<what you learned>"

When completing work:
- brief task done <task-id>
- brief describe <file>
```

### Vector Search Integration

* Embed markdown descriptions, functions, classes, and execution paths
* Query → vector search → relationship expansion → focused context

---

## Bootstrapping Plan

1. CLI skeleton + JSONL storage
2. Static analysis (AST)
3. LLM-powered descriptions
4. Relationship extraction
5. Context retrieval
6. Task management
7. Self-hosted dogfooding on Acme

---

## The Key Question

Does this design match your mental model?

1. JSONL + markdown split
2. CLI-first, human + agent usable
3. Query-based context retrieval
4. Beads-style task continuation

If this feels right, I can start building the skeleton. If not, let’s adjust before writing code.
