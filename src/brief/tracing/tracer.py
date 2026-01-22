"""Execution path tracing - combining static analysis for call chains."""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any
from ..storage import read_jsonl
from ..config import MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR


@dataclass
class PathStep:
    """A single step in an execution path."""
    function: str  # "ClassName.method" or "function"
    file: str
    line: int
    description: str
    code_snippet: Optional[str] = None
    calls_to: list[str] = field(default_factory=list)


@dataclass
class ExecutionPath:
    """A traced execution path."""
    name: str
    description: str
    entry_point: str
    steps: list[PathStep] = field(default_factory=list)
    data_flow: str = ""
    related_files: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
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

            if step.code_snippet:
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

        # Remaining steps as tree
        for step in self.steps[1:]:
            # Truncate description to first line, max 60 chars
            desc = step.description.split('\n')[0][:60] if step.description else ""
            if desc == "No documentation":
                desc = ""

            # Only show file if different from entry
            if step.file != entry_file:
                func_part = f"`{step.function}` ({step.file})"
            else:
                func_part = f"`{step.function}`"

            if desc:
                lines.append(f"  → {func_part} - {desc}")
            else:
                lines.append(f"  → {func_part}")

        # List all files at the bottom
        if len(self.related_files) > 1:
            lines.append(f"  Files: {', '.join(self.related_files)}")

        return "\n".join(lines)


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

    def find_function(self, name: str) -> Optional[dict[str, Any]]:
        """Find a function in the manifest."""
        manifest = self._load_manifest()

        # Try exact match first
        for record in manifest:
            if record["type"] == "function":
                class_name = record.get("class_name") or ""
                full_name = f"{class_name}.{record['name']}" if class_name else record['name']
                if full_name == name or record['name'] == name:
                    return record

        # Try partial match
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
        visited: Optional[set[str]] = None
    ) -> list[PathStep]:
        """Trace execution from a function."""
        if visited is None:
            visited = set()

        if function_name in visited or len(visited) >= max_depth:
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
            )
        )

        # Get what this function calls
        callees = self.get_callees(func_record["file"], function_name)
        step.calls_to = callees

        steps = [step]

        # Recursively trace callees
        for callee in callees[:3]:  # Limit to prevent explosion
            steps.extend(self.trace_from_function(callee, max_depth, visited.copy()))

        return steps

    def create_path(
        self,
        name: str,
        entry_point: str,
        description: str = ""
    ) -> ExecutionPath:
        """Create an execution path starting from entry point."""
        steps = self.trace_from_function(entry_point)

        # Collect related files
        related_files = list(set(step.file for step in steps))

        path = ExecutionPath(
            name=name,
            description=description or f"Execution path from {entry_point}",
            entry_point=entry_point,
            steps=steps,
            related_files=related_files
        )

        return path

    def save_path(self, path: ExecutionPath) -> Path:
        """Save a traced path to the context directory."""
        paths_dir = self.brief_path / CONTEXT_DIR / "paths"
        paths_dir.mkdir(parents=True, exist_ok=True)

        filename = path.name.lower().replace(" ", "-") + ".md"
        file_path = paths_dir / filename

        file_path.write_text(path.to_markdown())
        return file_path

    def list_paths(self) -> list[str]:
        """List all saved execution paths."""
        paths_dir = self.brief_path / CONTEXT_DIR / "paths"
        if not paths_dir.exists():
            return []

        return [f.stem for f in paths_dir.glob("*.md")]

    def load_path(self, name: str) -> Optional[str]:
        """Load a saved path by name."""
        paths_dir = self.brief_path / CONTEXT_DIR / "paths"
        filename = name.lower().replace(" ", "-") + ".md"
        file_path = paths_dir / filename

        if file_path.exists():
            return file_path.read_text()

        return None

    def load_path_as_object(self, name: str) -> Optional[ExecutionPath]:
        """Load a saved path and reconstruct as ExecutionPath object."""
        paths_dir = self.brief_path / CONTEXT_DIR / "paths"
        filename = name.lower().replace(" ", "-") + ".md"
        file_path = paths_dir / filename

        if not file_path.exists():
            return None

        # Parse the markdown back into an ExecutionPath
        content = file_path.read_text()
        steps: list[PathStep] = []
        related_files: list[str] = []
        entry_point = ""
        description = ""

        current_func = ""
        current_file = ""
        current_desc = ""
        in_related_files = False

        for line in content.split('\n'):
            if line.startswith('# Path: '):
                pass  # name already known
            elif line.startswith('`') and not entry_point:
                entry_point = line.strip('`')
            elif line.startswith('## Related Files'):
                in_related_files = True
            elif line.startswith('## ') and in_related_files:
                in_related_files = False
            elif in_related_files and line.startswith('- `'):
                related_files.append(line.strip('- `').rstrip('`'))
            elif line.startswith('### ') and '. ' in line:
                # Save previous step if exists
                if current_func:
                    steps.append(PathStep(
                        function=current_func,
                        file=current_file,
                        line=0,  # Not needed for flow format
                        description=current_desc
                    ))
                # Parse new step: "### 1. function_name"
                parts = line.split('. ', 1)
                current_func = parts[1] if len(parts) > 1 else ""
                current_desc = ""
                current_file = ""
            elif line.startswith('**File**: '):
                # Parse "**File**: `path:line`"
                file_part = line.replace('**File**: ', '').strip('`')
                current_file = file_part.split(':')[0] if ':' in file_part else file_part
            elif current_func and not line.startswith('**') and not line.startswith('```') and line.strip():
                if not current_desc and line.strip():
                    current_desc = line.strip()

        # Don't forget last step
        if current_func:
            steps.append(PathStep(
                function=current_func,
                file=current_file,
                line=0,
                description=current_desc
            ))

        return ExecutionPath(
            name=name,
            description=description or f"Execution path from {entry_point}",
            entry_point=entry_point,
            steps=steps,
            related_files=related_files or list(set(s.file for s in steps if s.file))
        )

    def delete_path(self, name: str) -> bool:
        """Delete a saved path."""
        paths_dir = self.brief_path / CONTEXT_DIR / "paths"
        filename = name.lower().replace(" ", "-") + ".md"
        file_path = paths_dir / filename

        if file_path.exists():
            file_path.unlink()
            return True

        return False
