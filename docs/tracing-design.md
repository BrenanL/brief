# Execution Path Tracing Design

## The Problem

Without Brief, agents try to predict what files contain the code they need to modify. They search, find some matches, and work with those files. But this approach has critical flaws:

1. **Most found code is irrelevant** - A search for "validation" returns every file mentioning validation, not just the ones in the execution path being modified.

2. **Missing pipeline context** - What agents really need isn't a few code files, but all the code snippets throughout the execution path they're modifying.

3. **Broken changes** - Without seeing the full flow, agents miss upstream callers or downstream dependencies and make changes that break the pipeline.

## The Solution: Dynamic Execution Path Tracing

Brief determines which execution path the agent is likely working on and returns the complete flow - all files, classes, functions, and how data flows through the pipeline.

### Example

Agent asks: "working on table validation"

**Without Brief:**
- Search finds `validate_table.py`
- Agent modifies it
- Breaks because they didn't know `TableCommand` expected a specific return format

**With Brief:**
```
## Execution Flow

Entry: Acme.execute()
  → Dispatcher.execute_command()
    → TableCommand.execute()
      → validate_table() ← YOUR TARGET
        → check_schema()
        → check_constraints()

## Files in this path
- acme/core/acme.py
- acme/dispatch/dispatcher.py
- acme/commands/table.py ← YOUR TARGET
- acme/validation/table.py
```

Now the agent sees:
- Where `validate_table()` fits in the bigger picture
- What calls it (`TableCommand.execute()`)
- What it calls (`check_schema()`, `check_constraints()`)
- The full pipeline from entry point to target

## The Chicken-and-Egg Problem

There's an apparent paradox:
- You need to know the trace to find the right files
- You need to know the files to find the right trace

**Solution: Trace in BOTH directions at query time.**

1. **Search** - Find functions matching the query
2. **Trace UP** - Follow callers to find the entry point (root of the call tree)
3. **Trace DOWN** - From entry point, trace through the relevant functions
4. **Return** - The execution flow showing where query targets fit in the bigger picture

This means traces are **dynamic** - computed at query time from the call graph, not pre-saved.

---

## Design: Hybrid Approach

### Core Insight: Store What to Trace, Not the Trace Itself

Instead of storing complete trace content that can become stale, we store **trace definitions** (metadata) and **regenerate content dynamically**.

**Trace definition** (stored in `.brief/context/traces.jsonl`):
```json
{"name": "cli-analyze", "entry_point": "analyze_directory", "description": "Analyze codebase", "category": "cli", "created": "2024-01-22"}
```

**Trace content** (generated on demand):
```
Entry: analyze_directory (src/brief/commands/analyze.py)
  → ManifestBuilder.analyze_directory
    → find_python_files
    → find_doc_files
```

### Why This Works

1. **Never stale** - Content always regenerated from current call graph
2. **Curated library** - You still have named, documented traces
3. **Discoverable** - Can browse all traces, see what flows exist
4. **Lightweight** - Just storing metadata, not full traces
5. **Simple staleness** - Only check: does entry point still exist?

### Why File Hashes Aren't Enough

Even if no individual file changes, the **call graph can change**:

```python
# Before: validate() calls check_schema() only
def validate():
    check_schema()

# After: validate() now also calls check_permissions()
def validate():
    check_schema()
    check_permissions()  # NEW CALL
```

With stored traces + hash checking, you'd need to track hashes of ALL files in the trace AND detect new relationships. With dynamic regeneration, this just works.

---

## How Dynamic Tracing Works

### The Algorithm

```
INPUT: Query "table validation"

STEP 1: SEARCH
  Search manifest for "table validation"
  → Finds: validate_table(), check_schema(), TableValidator.validate()

STEP 2: TRACE UP (find entry points)
  For each found function, follow callers:

  validate_table()
    ↑ called by TableCommand.execute()
      ↑ called by Dispatcher.execute_command()
        ↑ called by Acme.execute()
          ↑ no callers → ENTRY POINT FOUND

STEP 3: TRACE DOWN (build execution flow)
  From Acme.execute(), trace through call graph:

  Acme.execute()
    → Dispatcher.execute_command()
      → TableCommand.execute()
        → validate_table() ← TARGET
          → check_schema()
          → check_constraints()

STEP 4: FILTER & FORMAT
  Keep only the path through our targets
  Format as execution flow diagram

OUTPUT:
  Entry: Acme.execute()
    → Dispatcher.execute_command()
      → TableCommand.execute()
        → validate_table() ← YOUR TARGET
          → check_schema()
          → check_constraints()
```

### Visual Representation

```
                    SEARCH
                      │
                      ▼
            ┌─────────────────┐
            │ validate_table  │ ← Found by search
            │ check_schema    │
            └─────────────────┘
                      │
              TRACE UP│(find entry)
                      ▼
            ┌─────────────────┐
            │ Acme.execute()  │ ← Entry point (no callers)
            └─────────────────┘
                      │
            TRACE DOWN│(build flow)
                      ▼
            ┌─────────────────┐
            │ Full execution  │
            │ path with all   │
            │ context         │
            └─────────────────┘
```

---

## Real-World Use Cases

### Use Case 1: Initial Setup

```bash
brief init
brief analyze all
```

**What happens:**
1. Parse all code → manifest.jsonl
2. Extract calls → relationships.jsonl
3. Detect entry points (decorated functions, CLI commands)
4. Auto-create trace definitions:

```
Analysis complete:
  Python files: 58
  Functions: 147
  Relationships: 2205 calls

Entry points detected: 23
  CLI commands: 15 (auto-traced)
  Test functions: 204 (skipped - use --include-tests)

Trace definitions created: 15
  cli-init           init_command
  cli-analyze        analyze_directory
  cli-context-get    context_get
  ...
```

User immediately has a seeded trace library covering main workflows.

### Use Case 2: Querying Context

```bash
brief context get "file analysis"
```

**What happens:**
1. Search finds `analyze_file()`, `PythonFileParser.parse()`
2. Check saved traces: "cli-analyze" matches (description mentions "analyze")
3. Dynamic trace: trace UP from `analyze_file()` → finds entry point
4. Return both the saved trace and dynamic trace through specific functions

### Use Case 3: Browsing All Traces

```bash
brief trace list
```

```
Trace Definitions (15):

  CLI Commands:
    ✓ cli-init           init_command              Initialize Brief
    ✓ cli-analyze        analyze_directory         Analyze codebase
    ✓ cli-context-get    context_get               Get context for query

  Other:
    ✗ old-export         ExportManager.export      (entry point not found)

  ✓ = entry point exists, ✗ = entry point missing
```

### Use Case 4: Viewing a Trace

```bash
brief trace show cli-analyze
```

**What happens:**
1. Load metadata: `entry_point = "analyze_directory"`
2. Regenerate trace from current call graph
3. Display flow diagram (default):

```
# cli-analyze: Analyze codebase

Entry: analyze_directory (src/brief/commands/analyze.py)
  → ManifestBuilder.__init__
  → ManifestBuilder.analyze_directory
    → find_python_files
    → find_doc_files
    → analyze_python_file
      → PythonFileParser.parse
```

With `-v` flag, shows full code snippets for each step.

### Use Case 5: Code Changes Mid-Session

Developer adds a new call in `analyze_directory()`:

```python
def analyze_directory():
    # ... existing code ...
    validate_config()  # NEW
```

Next `brief trace show cli-analyze` automatically includes `validate_config()`. No staleness detection needed - dynamic regeneration just works.

### Use Case 6: Refactoring

Developer renames `ManifestBuilder` to `CodeAnalyzer`.

The trace still works because:
- Entry point `analyze_directory` still exists
- Dynamic regeneration follows current calls
- Now shows `CodeAnalyzer` instead of `ManifestBuilder`

If the entry point itself is renamed/deleted:
```bash
brief trace list
  ✗ cli-analyze    old_analyze_func    (entry point not found)
```

User can update: `brief trace update cli-analyze --entry new_analyze_func`

### Use Case 7: New Feature Added

Developer adds `@app.command("export")`.

```bash
brief analyze all   # or brief analyze refresh
```

```
Found 1 new entry point:
  export_data (@app.command)

Auto-created trace definition: cli-export
```

Trace library grows as codebase grows.

---

## Entry Point Detection

### Entry Point Decorator Patterns

```python
ENTRY_POINT_DECORATORS = [
    # CLI frameworks
    "app.command", "click.command", "typer.command",

    # Web frameworks
    "app.route", "app.get", "app.post", "app.put", "app.delete",
    "router.get", "router.post", "router.put", "router.delete",

    # FastAPI
    "api_router.get", "api_router.post",

    # Flask
    "blueprint.route",

    # Django (detected by pattern, not decorator)
    # Views in urls.py
]
```

### Entry Point Categories

| Category | Detection Method | Auto-trace? |
|----------|-----------------|-------------|
| CLI commands | `@app.command`, `@click.command` | Yes |
| API routes | `@app.route`, `@router.get` | Yes |
| Main functions | `if __name__ == "__main__"` | Yes |
| Test functions | `test_*` prefix | No (use `--include-tests`) |
| Public methods | No `_` prefix on key classes | Configurable |

---

## CLI Commands

```bash
# List all trace definitions
brief trace list

# Show a trace (regenerated dynamically)
brief trace show <name>           # Flow diagram
brief trace show <name> -v        # With code snippets

# Define a new trace manually
brief trace define <name> <entry_point> [-d description]

# Update a trace definition
brief trace update <name> [--entry new_entry] [--description new_desc]

# Delete a trace definition
brief trace delete <name>

# Auto-discover entry points and create traces
brief trace discover              # Interactive
brief trace discover --auto       # Auto-create all
```

---

## Storage Format

### Trace Definitions (`.brief/context/traces.jsonl`)

```json
{"name": "cli-init", "entry_point": "init_command", "description": "Initialize Brief in a directory", "category": "cli", "created": "2024-01-22T10:30:00"}
{"name": "cli-analyze", "entry_point": "analyze_directory", "description": "Analyze Python files in a directory", "category": "cli", "created": "2024-01-22T10:30:00"}
{"name": "cli-context-get", "entry_point": "context_get", "description": "Get context for a query", "category": "cli", "created": "2024-01-22T10:30:00"}
```

### No More `.brief/context/paths/*.md`

The old approach stored full markdown traces. These are replaced by:
- Trace definitions in `traces.jsonl`
- Dynamic regeneration when viewing

---

## Implementation Components

### 1. Parser Enhancement: Decorator Extraction

Add to `ManifestFunctionRecord`:
```python
decorators: list[str] = Field(default_factory=list)
```

Extract during AST parsing:
```python
for decorator in node.decorator_list:
    if isinstance(decorator, ast.Name):
        decorators.append(decorator.id)
    elif isinstance(decorator, ast.Call):
        decorators.append(ast.unparse(decorator.func))
    elif isinstance(decorator, ast.Attribute):
        decorators.append(ast.unparse(decorator))
```

### 2. Bidirectional Call Graph

Add to `PathTracer`:
```python
def get_callers(self, function: str) -> list[dict]:
    """Get functions that call this function."""
    callers = []
    for rel in self._load_relationships():
        if rel.get("type") == "calls" and rel["to_func"] == function:
            callers.append({
                "function": rel["from_func"],
                "file": rel["file"],
                "line": rel["line"]
            })
    return callers
```

### 3. Upward Tracing

```python
def trace_to_entry_point(self, function_name: str, max_depth: int = 10) -> list[str]:
    """Trace upward from a function to find its entry point."""
    path = [function_name]
    current = function_name
    visited = set()

    while len(path) < max_depth:
        if current in visited:
            break
        visited.add(current)

        callers = self.get_callers(current)
        if not callers:
            break  # No callers = entry point

        caller = callers[0]["function"]
        path.insert(0, caller)
        current = caller

    return path
```

### 4. Entry Point Detection

```python
def find_entry_points(self) -> list[dict]:
    """Find likely entry points in the codebase."""
    entry_points = []

    for record in self._load_manifest():
        if record["type"] != "function":
            continue

        decorators = record.get("decorators", [])

        # Check for entry point decorators
        for dec in decorators:
            if any(pattern in dec for pattern in ENTRY_POINT_DECORATORS):
                entry_points.append({
                    "function": record["name"],
                    "file": record["file"],
                    "decorator": dec,
                    "category": categorize_decorator(dec)
                })
                break

    return entry_points
```

### 5. Dynamic Trace Generation

```python
def generate_dynamic_trace(self, target_functions: list[str]) -> ExecutionPath:
    """Generate execution path dynamically from target functions."""

    # Find entry points by tracing UP
    entry_points = []
    for func in target_functions:
        path = self.trace_to_entry_point(func)
        if path:
            entry_points.append(path[0])

    # Trace DOWN from entry points
    if entry_points:
        entry = entry_points[0]  # Use first found
        steps = self.trace_from_function(entry, max_depth=10)
    else:
        # No entry point found, trace from targets directly
        steps = []
        for func in target_functions:
            steps.extend(self.trace_from_function(func, max_depth=5))

    return ExecutionPath(
        name="dynamic",
        entry_point=entry_points[0] if entry_points else target_functions[0],
        steps=steps,
        related_files=list(set(s.file for s in steps))
    )
```

---

## Success Criteria

After implementation:

1. `brief analyze all` auto-detects entry points and creates trace definitions
2. `brief trace list` shows all defined traces with validity status
3. `brief trace show <name>` regenerates and displays current trace
4. `brief context get "query"` includes dynamic execution flows
5. No manual trace creation required for basic queries
6. Traces are never stale - always reflect current code
7. Agent sees full pipeline context, reducing missed dependencies
