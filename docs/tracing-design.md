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

## Current State

### What We Have

1. **Call graph in `relationships.jsonl`**
   - `{"type": "calls", "from_func": "TableCommand.execute", "to_func": "validate_table", ...}`
   - We know who calls whom

2. **Static tracing (`PathTracer`)**
   - Can trace DOWN from a function to its callees
   - Saves traces as markdown files
   - Used when user manually creates traces

3. **Trace storage in `context/paths/`**
   - Pre-created traces saved as markdown
   - Searched during context retrieval

### What's Missing

1. **No decorator tracking**
   - Parser doesn't extract `@app.command`, `@app.route`, etc.
   - Can't automatically identify entry points

2. **No upward tracing**
   - Can trace from function → callees (down)
   - Cannot trace from function → callers (up) to find entry points

3. **No dynamic trace generation**
   - Traces must be pre-created manually
   - Context queries only search existing traces

4. **No entry point detection**
   - No way to identify CLI commands, API endpoints, public interfaces
   - User must manually specify entry points

---

## Implementation Plan

### Phase 1: Parser Enhancement

**Add decorator extraction to `parser.py`**

```python
class ManifestFunctionRecord(BaseModel):
    # ... existing fields ...
    decorators: list[str] = Field(default_factory=list)  # NEW
```

Extract decorators during AST parsing:
```python
for decorator in node.decorator_list:
    if isinstance(decorator, ast.Name):
        decorators.append(decorator.id)
    elif isinstance(decorator, ast.Call):
        decorators.append(ast.unparse(decorator.func))
```

### Phase 2: Bidirectional Call Graph

**Add `get_callers()` to `PathTracer`**

Currently we have:
```python
def get_callees(self, file: str, function: str) -> list[str]:
    """Get functions that a function calls."""
```

Add:
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

### Phase 3: Entry Point Detection

**Identify entry points automatically**

Entry point heuristics:
1. **Decorated functions** - `@app.command`, `@app.route`, `@click.command`, `@pytest.fixture`
2. **No callers** - Functions at the top of the call graph
3. **Public class methods** - Methods without underscore prefix on key classes
4. **Test functions** - `test_*` functions (entry points for test execution)

```python
def find_entry_points(self) -> list[dict]:
    """Find likely entry points in the codebase."""
    entry_points = []

    # 1. Functions with entry point decorators
    for record in self._load_manifest():
        if record["type"] == "function":
            decorators = record.get("decorators", [])
            if any(d in ENTRY_POINT_DECORATORS for d in decorators):
                entry_points.append(record)

    # 2. Functions with no callers
    all_callees = set()
    for rel in self._load_relationships():
        if rel["type"] == "calls":
            all_callees.add(rel["to_func"])

    for record in self._load_manifest():
        if record["type"] == "function":
            func_name = record["name"]
            if func_name not in all_callees:
                entry_points.append(record)

    return entry_points
```

### Phase 4: Upward Tracing

**Trace from a function UP to its entry point**

```python
def trace_to_entry_point(self, function_name: str, max_depth: int = 10) -> list[str]:
    """Trace upward from a function to find its entry point(s)."""
    visited = set()
    path = [function_name]
    current = function_name

    while len(path) < max_depth:
        callers = self.get_callers(current)
        if not callers:
            # No callers = this is an entry point
            break

        # Follow the first caller (could be smarter about this)
        caller = callers[0]["function"]
        if caller in visited:
            break  # Cycle detected

        visited.add(caller)
        path.insert(0, caller)
        current = caller

    return path
```

### Phase 5: Dynamic Trace Generation

**Generate traces at query time**

```python
def generate_dynamic_trace(self, target_functions: list[str]) -> ExecutionPath:
    """Generate an execution path dynamically from target functions."""

    # 1. Find entry points by tracing UP from targets
    entry_points = set()
    for func in target_functions:
        path_to_entry = self.trace_to_entry_point(func)
        if path_to_entry:
            entry_points.add(path_to_entry[0])

    # 2. For each entry point, trace DOWN through targets
    all_steps = []
    for entry in entry_points:
        steps = self.trace_from_function(entry, max_depth=10)
        # Filter to only include steps relevant to our targets
        relevant_steps = [s for s in steps if s.function in target_functions
                         or any(t in s.calls_to for t in target_functions)]
        all_steps.extend(relevant_steps)

    # 3. Build execution path
    return ExecutionPath(
        name="dynamic",
        description=f"Execution path through {', '.join(target_functions)}",
        entry_point=list(entry_points)[0] if entry_points else target_functions[0],
        steps=all_steps,
        related_files=list(set(s.file for s in all_steps))
    )
```

### Phase 6: Integration with Context Retrieval

**Update `build_context_for_query()` to use dynamic tracing**

```python
def build_context_for_query(brief_path, query, search_func, base_path):
    # ... existing search logic ...

    # Get target functions from search results
    target_functions = [r["name"] for r in results if r["type"] == "function"]

    # Generate dynamic trace instead of searching pre-made traces
    tracer = PathTracer(brief_path, base_path)
    if target_functions:
        dynamic_path = tracer.generate_dynamic_trace(target_functions)
        package.execution_paths = [{
            "name": "Relevant Execution Flow",
            "flow": dynamic_path.to_flow()
        }]

    return package
```

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

## Pre-Created vs Dynamic Traces

Both have value:

| Pre-Created Traces | Dynamic Traces |
|-------------------|----------------|
| Named, documented paths | Generated on-demand |
| "workspace-creation", "auth-flow" | Based on query targets |
| Curated with descriptions | Automatic, no curation |
| For known important flows | For any query |

**Recommendation**: Keep both. Pre-created traces for important documented flows, dynamic traces for everything else.

---

## Entry Point Decorator Patterns

Common decorators that indicate entry points:

```python
ENTRY_POINT_DECORATORS = [
    # CLI frameworks
    "app.command",
    "click.command",
    "typer.command",

    # Web frameworks
    "app.route",
    "app.get", "app.post", "app.put", "app.delete",
    "router.get", "router.post",

    # Testing
    "pytest.fixture",
    "pytest.mark",

    # Async
    "asyncio.coroutine",

    # Class decorators
    "dataclass",
    "app.middleware",
]
```

---

## Success Criteria

After implementation:

1. `brief context get "table validation"` returns execution flow automatically
2. No manual trace creation required for basic queries
3. Entry points detected from decorators and call graph
4. Agent sees full pipeline context, not just isolated files
5. Reduces missed dependencies and broken changes
