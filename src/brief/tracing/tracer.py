"""Execution path tracing - combining static analysis for call chains."""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from ..storage import read_jsonl, write_jsonl, append_jsonl
from ..config import MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR
from ..models import TraceDefinition


# Decorators that indicate entry points
ENTRY_POINT_DECORATORS = [
    # CLI frameworks
    "app.command", "click.command", "typer.command",
    # Web frameworks
    "app.route", "app.get", "app.post", "app.put", "app.delete", "app.patch",
    "router.get", "router.post", "router.put", "router.delete", "router.patch",
    "api_router.get", "api_router.post",
    "blueprint.route",
    # FastAPI
    "APIRouter",
    # Common patterns
    "main",
]

TRACES_FILE = "traces.jsonl"


@dataclass
class PathStep:
    """A single step in an execution path."""
    function: str  # "ClassName.method" or "function"
    file: str
    line: int
    description: str
    code_snippet: Optional[str] = None
    calls_to: list[str] = field(default_factory=list)
    depth: int = 0  # Nesting depth in call tree


@dataclass
class ExecutionPath:
    """A traced execution path."""
    name: str
    description: str
    entry_point: str
    steps: list[PathStep] = field(default_factory=list)
    data_flow: str = ""
    related_files: list[str] = field(default_factory=list)

    def to_markdown(self, include_code: bool = True) -> str:
        """Convert to markdown documentation."""
        lines = [
            f"# Path: {self.name}",
            "",
            self.description,
            "",
            "## Entry Point",
            f"`{self.entry_point}`",
            "",
            "## Steps",
        ]

        for i, step in enumerate(self.steps, 1):
            lines.append(f"\n### {i}. {step.function}")
            lines.append(f"**File**: `{step.file}:{step.line}`")
            lines.append("")
            lines.append(step.description)

            if include_code and step.code_snippet:
                lines.append("")
                lines.append("```python")
                lines.append(step.code_snippet)
                lines.append("```")

            if step.calls_to:
                lines.append("")
                lines.append(f"**Calls**: {', '.join(step.calls_to)}")

        if self.data_flow:
            lines.extend([
                "",
                "## Data Flow",
                self.data_flow
            ])

        if self.related_files:
            lines.extend([
                "",
                "## Related Files",
            ])
            for f in self.related_files:
                lines.append(f"- `{f}`")

        return "\n".join(lines)

    def to_flow(self) -> str:
        """Convert to compact flow diagram for context packages."""
        if not self.steps:
            return f"### {self.name}\n(no steps traced)"

        lines = [f"### {self.name}"]

        # Entry file for comparison
        entry_file = self.steps[0].file if self.steps else ""

        # First step is entry
        first = self.steps[0]
        first_desc = first.description.split('\n')[0][:60] if first.description else ""
        lines.append(f"Entry: `{first.function}` ({first.file})")
        if first_desc and first_desc != "No documentation":
            lines.append(f"  {first_desc}")

        # Remaining steps as indented tree based on depth
        for step in self.steps[1:]:
            # Truncate description to first line, max 60 chars
            desc = step.description.split('\n')[0][:50] if step.description else ""
            if desc == "No documentation":
                desc = ""

            # Indent based on depth (2 spaces per level)
            indent = "  " * step.depth

            # Only show file if different from entry
            if step.file != entry_file:
                func_part = f"`{step.function}` ({step.file})"
            else:
                func_part = f"`{step.function}`"

            if desc:
                lines.append(f"{indent}→ {func_part} - {desc}")
            else:
                lines.append(f"{indent}→ {func_part}")

        # List all files at the bottom
        if len(self.related_files) > 1:
            lines.append(f"Files: {', '.join(self.related_files)}")

        return "\n".join(lines)


def categorize_decorator(decorator: str) -> str:
    """Categorize a decorator into entry point type."""
    dec_lower = decorator.lower()
    if any(cli in dec_lower for cli in ["command", "typer", "click"]):
        return "cli"
    if any(web in dec_lower for web in ["route", "get", "post", "put", "delete", "patch", "router"]):
        return "api"
    if "test" in dec_lower or "fixture" in dec_lower:
        return "test"
    return "other"


class PathTracer:
    """Trace execution paths through the codebase."""

    def __init__(self, brief_path: Path, base_path: Path):
        self.brief_path = brief_path
        self.base_path = base_path
        self._manifest: Optional[list[dict[str, Any]]] = None
        self._relationships: Optional[list[dict[str, Any]]] = None

    def _load_manifest(self) -> list[dict[str, Any]]:
        """Load manifest lazily."""
        if self._manifest is None:
            self._manifest = list(read_jsonl(self.brief_path / MANIFEST_FILE))
        return self._manifest

    def _load_relationships(self) -> list[dict[str, Any]]:
        """Load relationships lazily."""
        if self._relationships is None:
            self._relationships = list(read_jsonl(self.brief_path / RELATIONSHIPS_FILE))
        return self._relationships

    def find_function(self, name: str, strict: bool = False) -> Optional[dict[str, Any]]:
        """Find a function in the manifest.

        Args:
            name: Function name to find
            strict: If True, only exact matches. If False, allows partial matching.
        """
        manifest = self._load_manifest()

        # Try exact match first
        for record in manifest:
            if record["type"] == "function":
                class_name = record.get("class_name") or ""
                full_name = f"{class_name}.{record['name']}" if class_name else record['name']
                if full_name == name or record['name'] == name:
                    return record

        if strict:
            return None

        # Try partial match (only for user-facing searches, not internal resolution)
        for record in manifest:
            if record["type"] == "function" and name in record['name']:
                return record

        return None

    def get_callees(self, file: str, function: str) -> list[str]:
        """Get functions that a function calls (from relationships)."""
        relationships = self._load_relationships()
        callees: list[str] = []

        for rel in relationships:
            if rel.get("type") == "calls":
                from_func = rel.get("from_func", "")
                if from_func.endswith(function) or from_func == function:
                    callees.append(rel["to_func"])

        return callees

    def get_callers(self, function: str) -> list[dict[str, Any]]:
        """Get functions that call this function (trace UP the call graph)."""
        relationships = self._load_relationships()
        callers: list[dict[str, Any]] = []

        for rel in relationships:
            if rel.get("type") == "calls":
                to_func = rel.get("to_func", "")
                # Match if to_func equals function or ends with it (for Class.method matching)
                if to_func == function or to_func.endswith(f".{function}"):
                    callers.append({
                        "function": rel["from_func"],
                        "file": rel["file"],
                        "line": rel["line"]
                    })

        return callers

    def trace_to_entry_point(self, function_name: str, max_depth: int = 15) -> list[str]:
        """Trace upward from a function to find its entry point.

        Returns the path from entry point to the target function.
        """
        path = [function_name]
        current = function_name
        visited = set()

        while len(path) < max_depth:
            if current in visited:
                break  # Cycle detected
            visited.add(current)

            callers = self.get_callers(current)
            if not callers:
                break  # No callers = this is an entry point

            # Use first caller (could be smarter - pick the one with most context)
            caller = callers[0]["function"]
            path.insert(0, caller)
            current = caller

        return path

    def get_code_snippet(
        self,
        file: str,
        start_line: int,
        end_line: Optional[int] = None
    ) -> str:
        """Extract code snippet from file."""
        file_path = self.base_path / file
        if not file_path.exists():
            return ""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return ""

        end = end_line or start_line + 10
        start = max(0, start_line - 1)
        end = min(len(lines), end)

        return ''.join(lines[start:end]).strip()

    def trace_from_function(
        self,
        function_name: str,
        max_depth: int = 5,
        visited: Optional[set[str]] = None,
        current_depth: int = 0
    ) -> list[PathStep]:
        """Trace execution from a function (downward through callees)."""
        if visited is None:
            visited = set()

        if function_name in visited or current_depth >= max_depth:
            return []

        visited.add(function_name)

        func_record = self.find_function(function_name)
        if not func_record:
            return []

        step = PathStep(
            function=function_name,
            file=func_record["file"],
            line=func_record["line"],
            description=func_record.get("docstring", "") or "No documentation",
            code_snippet=self.get_code_snippet(
                func_record["file"],
                func_record["line"],
                func_record.get("end_line")
            ),
            depth=current_depth
        )

        # Get what this function calls
        callees = self.get_callees(func_record["file"], function_name)
        step.calls_to = callees

        steps = [step]

        # Filter to callees that exist in our codebase (not external libraries)
        # Use strict matching to avoid false positives like "len" -> "test_..._len..."
        resolvable_callees = [c for c in callees if self.find_function(c, strict=True) is not None]

        # Recursively trace resolvable callees (limit to prevent explosion)
        for callee in resolvable_callees[:5]:
            steps.extend(self.trace_from_function(callee, max_depth, visited.copy(), current_depth + 1))

        return steps

    def find_entry_points(self, include_tests: bool = False) -> list[dict[str, Any]]:
        """Find likely entry points in the codebase.

        Entry points are functions with entry point decorators (like @app.command)
        or functions that have no callers in the call graph.
        """
        manifest = self._load_manifest()
        entry_points = []
        seen_functions = set()

        # 1. Find functions with entry point decorators
        for record in manifest:
            if record["type"] != "function":
                continue

            decorators = record.get("decorators", [])
            func_name = record["name"]
            class_name = record.get("class_name")
            full_name = f"{class_name}.{func_name}" if class_name else func_name

            # Skip test functions unless requested
            if not include_tests and func_name.startswith("test_"):
                continue

            # Check for entry point decorators
            for dec in decorators:
                if any(pattern in dec for pattern in ENTRY_POINT_DECORATORS):
                    entry_points.append({
                        "function": full_name,
                        "file": record["file"],
                        "line": record["line"],
                        "decorator": dec,
                        "category": categorize_decorator(dec),
                        "docstring": record.get("docstring", "")
                    })
                    seen_functions.add(full_name)
                    break

        return entry_points

    def generate_dynamic_trace(
        self,
        target_functions: list[str],
        max_depth: int = 10
    ) -> ExecutionPath:
        """Generate an execution path dynamically from target functions.

        1. Traces UP from targets to find entry points
        2. Traces DOWN from entry points through the call graph
        """
        # Find entry points by tracing UP from each target
        entry_points: list[str] = []
        for func in target_functions:
            path = self.trace_to_entry_point(func)
            if path:
                entry_points.append(path[0])

        # Remove duplicates while preserving order
        entry_points = list(dict.fromkeys(entry_points))

        # Trace DOWN from entry points
        all_steps: list[PathStep] = []
        if entry_points:
            entry = entry_points[0]  # Use first found entry point
            all_steps = self.trace_from_function(entry, max_depth=max_depth)
        else:
            # No entry point found, trace from targets directly
            for func in target_functions[:3]:
                all_steps.extend(self.trace_from_function(func, max_depth=5))

        # Collect related files
        related_files = list(dict.fromkeys(step.file for step in all_steps))

        return ExecutionPath(
            name="dynamic",
            description=f"Execution path through {', '.join(target_functions[:3])}",
            entry_point=entry_points[0] if entry_points else (target_functions[0] if target_functions else "unknown"),
            steps=all_steps,
            related_files=related_files
        )

    # === Trace Definition Storage (metadata only) ===

    def _get_traces_file(self) -> Path:
        """Get path to traces definition file."""
        return self.brief_path / CONTEXT_DIR / TRACES_FILE

    def save_trace_definition(self, definition: TraceDefinition) -> None:
        """Save a trace definition (metadata only)."""
        traces_file = self._get_traces_file()
        traces_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if trace with this name already exists
        existing = list(self.list_trace_definitions())
        for trace in existing:
            if trace.name == definition.name:
                # Update existing
                self._update_trace_definition(definition)
                return

        # Append new
        append_jsonl(traces_file, definition.model_dump())

    def _update_trace_definition(self, definition: TraceDefinition) -> None:
        """Update an existing trace definition."""
        traces_file = self._get_traces_file()
        traces = list(self.list_trace_definitions())

        updated = []
        for trace in traces:
            if trace.name == definition.name:
                updated.append(definition.model_dump())
            else:
                updated.append(trace.model_dump())

        write_jsonl(traces_file, updated)

    def list_trace_definitions(self) -> list[TraceDefinition]:
        """List all saved trace definitions."""
        traces_file = self._get_traces_file()
        if not traces_file.exists():
            return []

        traces = []
        for record in read_jsonl(traces_file):
            try:
                traces.append(TraceDefinition.model_validate(record))
            except Exception:
                pass  # Skip invalid records

        return traces

    def get_trace_definition(self, name: str) -> Optional[TraceDefinition]:
        """Get a trace definition by name."""
        for trace in self.list_trace_definitions():
            if trace.name == name:
                return trace
        return None

    def delete_trace_definition(self, name: str) -> bool:
        """Delete a trace definition by name."""
        traces_file = self._get_traces_file()
        if not traces_file.exists():
            return False

        traces = list(self.list_trace_definitions())
        original_count = len(traces)

        traces = [t for t in traces if t.name != name]

        if len(traces) < original_count:
            write_jsonl(traces_file, [t.model_dump() for t in traces])
            return True

        return False

    def check_entry_point_exists(self, entry_point: str) -> bool:
        """Check if an entry point function still exists in the codebase."""
        return self.find_function(entry_point) is not None

    def generate_trace_from_definition(
        self,
        definition: TraceDefinition,
        max_depth: int = 10
    ) -> Optional[ExecutionPath]:
        """Generate a trace from a saved definition (dynamic regeneration)."""
        if not self.check_entry_point_exists(definition.entry_point):
            return None

        steps = self.trace_from_function(definition.entry_point, max_depth=max_depth)
        related_files = list(dict.fromkeys(step.file for step in steps))

        return ExecutionPath(
            name=definition.name,
            description=definition.description,
            entry_point=definition.entry_point,
            steps=steps,
            related_files=related_files
        )

    def auto_create_trace_definitions(self, include_tests: bool = False) -> list[TraceDefinition]:
        """Auto-create trace definitions for detected entry points.

        Returns list of newly created definitions.
        """
        entry_points = self.find_entry_points(include_tests=include_tests)
        existing = {t.name for t in self.list_trace_definitions()}
        created: list[TraceDefinition] = []

        for ep in entry_points:
            # Generate a name from the function
            func_name = ep["function"]
            category = ep["category"]

            # Create a readable name
            if category == "cli":
                name = f"cli-{func_name.replace('.', '-').replace('_', '-')}"
            elif category == "api":
                name = f"api-{func_name.replace('.', '-').replace('_', '-')}"
            else:
                name = func_name.replace(".", "-").replace("_", "-")

            name = name.lower()

            if name in existing:
                continue

            # Get description from docstring
            description = ep.get("docstring", "")
            if not description:
                description = f"Entry point: {func_name}"
            else:
                # Use first line of docstring
                description = description.split("\n")[0].strip()

            definition = TraceDefinition(
                name=name,
                entry_point=func_name,
                description=description,
                category=category,
                created=datetime.now()
            )

            self.save_trace_definition(definition)
            created.append(definition)
            existing.add(name)

        return created

    # === Legacy methods for backward compatibility ===

    def create_path(
        self,
        name: str,
        entry_point: str,
        description: str = ""
    ) -> ExecutionPath:
        """Create an execution path starting from entry point."""
        steps = self.trace_from_function(entry_point)
        related_files = list(set(step.file for step in steps))

        path = ExecutionPath(
            name=name,
            description=description or f"Execution path from {entry_point}",
            entry_point=entry_point,
            steps=steps,
            related_files=related_files
        )

        return path

    def list_paths(self) -> list[str]:
        """List all saved trace definitions (by name)."""
        return [t.name for t in self.list_trace_definitions()]

    def load_path(self, name: str) -> Optional[str]:
        """Load and regenerate a trace, return as markdown."""
        definition = self.get_trace_definition(name)
        if not definition:
            return None

        path = self.generate_trace_from_definition(definition)
        if not path:
            return f"# {name}\n\nEntry point `{definition.entry_point}` not found."

        return path.to_markdown()

    def load_path_as_object(self, name: str) -> Optional[ExecutionPath]:
        """Load and regenerate a trace, return as ExecutionPath object."""
        definition = self.get_trace_definition(name)
        if not definition:
            return None

        return self.generate_trace_from_definition(definition)

    def save_path(self, path: ExecutionPath) -> Path:
        """Save a trace definition (not the full markdown anymore)."""
        definition = TraceDefinition(
            name=path.name,
            entry_point=path.entry_point,
            description=path.description,
            category="other",
            created=datetime.now()
        )
        self.save_trace_definition(definition)
        return self._get_traces_file()

    def delete_path(self, name: str) -> bool:
        """Delete a trace definition."""
        return self.delete_trace_definition(name)
