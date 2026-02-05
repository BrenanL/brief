"""Context package building for focused task context."""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from ..storage import read_jsonl
from ..config import get_brief_path, MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR, MEMORY_FILE
from ..memory.store import MemoryStore
from ..contracts.detector import ContractDetector
from ..tracing.tracer import PathTracer
from ..models import CallRelationship


def format_function_signature(func: dict[str, Any]) -> str:
    """Format a function record into a readable signature string.

    Args:
        func: Function record from manifest containing name, params, returns, etc.

    Returns:
        Formatted signature like "async def foo(bar: str, baz: int = 5) -> bool"
    """
    # Build prefix (async/def)
    prefix = "async def " if func.get("is_async") else "def "

    # Build parameter string
    params = func.get("params", [])
    param_strs = []
    for p in params:
        if isinstance(p, dict):
            param_str = p.get("name", "?")
            if p.get("type_hint"):
                param_str += f": {p['type_hint']}"
            if p.get("default"):
                param_str += f" = {p['default']}"
        else:
            param_str = str(p)
        param_strs.append(param_str)

    params_str = ", ".join(param_strs)

    # Build return type
    returns = func.get("returns")
    returns_str = f" -> {returns}" if returns else ""

    # Add generator indicator
    if func.get("is_generator"):
        if returns:
            returns_str = f" -> Generator[{returns}]"
        else:
            returns_str = " -> Generator"

    # Build full name (with class if method)
    name = func.get("name", "?")
    class_name = func.get("class_name")
    full_name = f"{class_name}.{name}" if class_name else name

    return f"{prefix}{full_name}({params_str}){returns_str}"


def format_class_signature(cls: dict[str, Any]) -> str:
    """Format a class record into a readable signature string.

    Args:
        cls: Class record from manifest containing name, bases, methods.

    Returns:
        Formatted signature like "class Foo(BaseClass):" with method list
    """
    name = cls.get("name", "?")
    bases = cls.get("bases", [])
    bases_str = f"({', '.join(bases)})" if bases else ""

    methods = cls.get("methods", [])
    methods_str = f"  # methods: {', '.join(methods)}" if methods else ""

    return f"class {name}{bases_str}:{methods_str}"


@dataclass
class ContextPackage:
    """A focused context package for a task."""
    query: str
    primary_files: list[dict[str, Any]] = field(default_factory=list)
    related_files: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    execution_paths: list[dict[str, str]] = field(default_factory=list)  # {name, flow}
    contracts: list[str] = field(default_factory=list)

    def to_markdown(self, include_signatures: bool = True, force_signatures: bool = False, compact: bool = False) -> str:
        """Convert to markdown for display/consumption.

        Args:
            include_signatures: Whether to include function/class signatures when
                               no description exists (default True)
            force_signatures: Force showing signatures even when description exists
                             (default False)
            compact: Show compact summary (file list and stats only, no descriptions)

        Returns:
            Markdown-formatted string
        """
        if compact:
            return self._to_markdown_compact()

        lines = [
            f"# Context for: {self.query}",
            "",
        ]

        if self.primary_files:
            lines.append("## Primary Files")
            for f in self.primary_files:
                # Check if this is a doc record (has title) vs code file
                if f.get('record_type') == 'doc' or f.get('title'):
                    # Documentation file rendering
                    lines.append(f"### {f['path']}")
                    if f.get('title'):
                        lines.append(f"**Title:** {f['title']}")
                    if f.get('first_paragraph'):
                        lines.append(f"\n{f['first_paragraph']}")
                    if f.get('headings'):
                        lines.append("")
                        lines.append("**Sections:**")
                        for heading in f['headings'][:10]:  # Limit to top 10
                            lines.append(f"- {heading}")
                else:
                    # Code file rendering
                    lines.append(f"### {f['path']}")
                    has_description = bool(f.get('description'))

                    if has_description:
                        lines.append(f.get('description'))

                    # Show signatures if:
                    # - force_signatures is True, OR
                    # - no description exists AND include_signatures is True
                    should_show_signatures = force_signatures or (not has_description and include_signatures)

                    if should_show_signatures:
                        classes = f.get('classes', [])
                        functions = f.get('functions', [])

                        if classes or functions:
                            lines.append("")
                            lines.append("**Signatures:**")
                            lines.append("```python")

                            # Classes first
                            for cls in classes:
                                lines.append(format_class_signature(cls))

                            # Then functions
                            for func in functions:
                                lines.append(format_function_signature(func))

                            lines.append("```")

                lines.append("")

        if self.related_files:
            lines.append("## Related Files")
            for f in self.related_files:
                lines.append(f"- {f['path']}")
                if f.get('reason'):
                    lines.append(f"  *Reason: {f['reason']}*")
            lines.append("")

        if self.patterns:
            lines.append("## Relevant Patterns")
            for p in self.patterns:
                lines.append(f"- **{p['key']}**: {p['value']}")
            lines.append("")

        if self.execution_paths:
            lines.append("## Execution Flows")
            lines.append("")
            for path in self.execution_paths:
                if isinstance(path, dict):
                    lines.append(path.get("flow", path.get("name", str(path))))
                else:
                    lines.append(f"- {path}")  # Backwards compat
                lines.append("")

        if self.contracts:
            lines.append("## Contracts")
            for contract in self.contracts:
                lines.append(f"- {contract}")
            lines.append("")

        return "\n".join(lines)

    def _to_markdown_compact(self) -> str:
        """Generate compact summary format."""
        lines = [
            f"# Context for: {self.query}",
            "",
        ]

        # Stats summary
        total_classes = sum(len(f.get('classes', [])) for f in self.primary_files)
        total_functions = sum(len(f.get('functions', [])) for f in self.primary_files)

        lines.append(f"**Summary**: {len(self.primary_files)} primary files, {len(self.related_files)} related files")
        lines.append(f"**Contains**: {total_classes} classes, {total_functions} functions")
        lines.append("")

        # Primary files - just paths with one-line summary
        if self.primary_files:
            lines.append("## Primary Files")
            for f in self.primary_files:
                path = f['path']
                # Extract purpose from description if available
                desc = f.get('description', '')
                summary = None
                if desc:
                    # Look for **Purpose**: line
                    for line in desc.split('\n'):
                        if '**Purpose**:' in line:
                            summary = line.replace('**Purpose**:', '').strip()
                            break
                    # If no Purpose line, use first non-header line
                    if not summary:
                        for line in desc.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#') and not line.startswith('**'):
                                summary = line
                                break

                if summary:
                    # Truncate to 70 chars
                    if len(summary) > 70:
                        summary = summary[:67] + "..."
                    lines.append(f"- **{path}**: {summary}")
                else:
                    # Show class/function count
                    classes = len(f.get('classes', []))
                    functions = len(f.get('functions', []))
                    lines.append(f"- **{path}**: {classes} classes, {functions} functions")
            lines.append("")

        # Related files - just paths
        if self.related_files:
            lines.append("## Related Files")
            for f in self.related_files:
                lines.append(f"- {f['path']}")
            lines.append("")

        # Brief counts for other sections
        extras = []
        if self.patterns:
            extras.append(f"{len(self.patterns)} patterns")
        if self.execution_paths:
            extras.append(f"{len(self.execution_paths)} execution flows")
        if self.contracts:
            extras.append(f"{len(self.contracts)} contracts")

        if extras:
            lines.append(f"**Also includes**: {', '.join(extras)}")
            lines.append("")

        lines.append("*Use without --compact for full details.*")

        return "\n".join(lines)

    def estimate_tokens(self) -> dict[str, int]:
        """Estimate token count for the context package.

        Uses a simple character-based estimate (roughly 4 chars per token).
        For more accurate counts, use tiktoken.

        Returns:
            Dict with token estimates by section and total, including
            the formatted markdown output.
        """
        def chars_to_tokens(text: str) -> int:
            """Rough estimate: ~4 characters per token for English."""
            return len(text) // 4

        estimates: dict[str, int] = {}

        # Primary files content
        primary_text = ""
        for f in self.primary_files:
            primary_text += f.get('path', '') + "\n"
            primary_text += f.get('description', '') + "\n"
            for cls in f.get('classes', []):
                primary_text += str(cls) + "\n"
            for func in f.get('functions', []):
                primary_text += str(func) + "\n"
        estimates['primary_files'] = chars_to_tokens(primary_text)

        # Related files
        related_text = "\n".join(f.get('path', '') for f in self.related_files)
        estimates['related_files'] = chars_to_tokens(related_text)

        # Patterns
        patterns_text = "\n".join(f"{p.get('key', '')}: {p.get('value', '')}" for p in self.patterns)
        estimates['patterns'] = chars_to_tokens(patterns_text)

        # Execution paths
        paths_text = "\n".join(str(p) for p in self.execution_paths)
        estimates['execution_paths'] = chars_to_tokens(paths_text)

        # Contracts
        contracts_text = "\n".join(self.contracts)
        estimates['contracts'] = chars_to_tokens(contracts_text)

        # Subtotal of content
        content_total = sum(estimates.values())
        estimates['content_subtotal'] = content_total

        # Actual formatted output (includes markdown formatting overhead)
        markdown_output = self.to_markdown()
        estimates['formatted_output'] = chars_to_tokens(markdown_output)

        # Total is the formatted output (which includes all content + formatting)
        estimates['total'] = estimates['formatted_output']

        return estimates


def search_manifest(
    brief_path: Path,
    query: str,
    max_results: int = 10
) -> list[tuple[int, dict[str, Any]]]:
    """Search manifest entries by query terms.

    Searches across:
    - File paths
    - Class names
    - Function names
    - Docstrings
    - Doc titles and headings

    Returns:
        List of (score, record) tuples sorted by score descending.
    """
    import re
    # Strip punctuation from terms
    query_terms = [
        re.sub(r'[^\w_]', '', t.lower())
        for t in query.split()
    ]
    query_terms = [t for t in query_terms if len(t) > 2]
    scored_records: list[tuple[int, dict[str, Any]]] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        score = 0
        record_type = record.get("type", "")

        # Score based on name matches
        name = record.get("name", "").lower()
        path = record.get("path", "").lower()
        file_path = record.get("file", "").lower()
        docstring = (record.get("docstring") or "").lower()

        for term in query_terms:
            # Exact name match is very valuable
            if term == name:
                score += 10
            elif term in name:
                score += 5

            # Path match
            if term in path or term in file_path:
                score += 2

            # Docstring match
            if term in docstring:
                score += 3

            # Class method match (e.g., "create" matches "TaskManager.create_task")
            if record_type == "function":
                full_name = f"{record.get('class_name', '')}.{name}".lower()
                if term in full_name:
                    score += 4

            # Documentation file matches
            if record_type == "doc":
                title = (record.get("title") or "").lower()
                headings = record.get("headings", [])
                first_para = (record.get("first_paragraph") or "").lower()

                # Title match is very valuable
                if term == title:
                    score += 10
                elif term in title:
                    score += 6

                # Heading matches
                for heading in headings:
                    heading_lower = heading.lower()
                    if term == heading_lower:
                        score += 8
                    elif term in heading_lower:
                        score += 4

                # First paragraph match
                if term in first_para:
                    score += 3

        if score > 0:
            scored_records.append((score, record))

    # Sort by score descending
    scored_records.sort(key=lambda x: -x[0])
    return scored_records[:max_results]


def expand_with_call_graph(
    brief_path: Path,
    seed_files: list[str],
    seed_functions: list[str],
    max_related: int = 5
) -> list[dict[str, str]]:
    """Expand seed files/functions using call graph relationships.

    Only follows calls to functions that exist in the manifest (skips stdlib
    and external library calls like typer.Option, Path.exists, etc).

    Args:
        brief_path: Path to .brief directory
        seed_files: Initial file paths
        seed_functions: Initial function names (e.g., "TaskManager.create_task")
        max_related: Maximum related files to return

    Returns:
        List of {path, reason} dicts for related files
    """
    related: list[dict[str, str]] = []
    seen_files = set(seed_files)

    # Build a lookup of internal functions -> their files
    # This allows us to skip external/stdlib calls
    internal_funcs: dict[str, str] = {}  # func_name -> file_path
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "function":
            name = record["name"]
            class_name = record.get("class_name")
            file_path = record["file"]
            # Add both forms: "func_name" and "ClassName.func_name"
            internal_funcs[name] = file_path
            if class_name:
                internal_funcs[f"{class_name}.{name}"] = file_path

    # Load relationships
    calls: list[CallRelationship] = []
    for rel in read_jsonl(brief_path / RELATIONSHIPS_FILE):
        if rel.get("type") == "calls":
            calls.append(CallRelationship.model_validate(rel))

    # Find functions called by seed functions (only follow internal calls)
    for func_name in seed_functions:
        for call in calls:
            if call.from_func == func_name or call.from_func.endswith(f".{func_name}"):
                # Check if the callee is an internal function
                callee_name = call.to_func
                callee_file = None

                # Try exact match first
                if callee_name in internal_funcs:
                    callee_file = internal_funcs[callee_name]
                else:
                    # Try partial match (e.g., "create_task" matches "TaskManager.create_task")
                    for internal_name, internal_file in internal_funcs.items():
                        if internal_name.endswith(f".{callee_name}") or callee_name.endswith(f".{internal_name}"):
                            callee_file = internal_file
                            break

                if callee_file and callee_file not in seen_files:
                    seen_files.add(callee_file)
                    related.append({
                        "path": callee_file,
                        "reason": f"defines {callee_name} called by {func_name}"
                    })

    # Find functions that call seed functions
    for func_name in seed_functions:
        for call in calls:
            if call.to_func == func_name or call.to_func.endswith(f".{func_name}"):
                # Found a caller - add the file where the call is made
                if call.file not in seen_files:
                    seen_files.add(call.file)
                    related.append({
                        "path": call.file,
                        "reason": f"calls {func_name} from {call.from_func}"
                    })

    return related[:max_related]


_llm_warning_shown = False

def get_file_description(
    brief_path: Path,
    file_path: str,
    auto_generate: bool = False,
    base_path: Optional[Path] = None,
    show_progress: bool = True
) -> str | None:
    """Get the description for a file.

    Args:
        brief_path: Path to .brief directory
        file_path: Relative path to the file
        auto_generate: If True, generate description on-demand if missing
        base_path: Base path for the project (required if auto_generate is True)
        show_progress: If True, print progress message when generating (default True)

    Returns:
        The description content, or None if not found and auto_generate is False.
    """
    import sys
    global _llm_warning_shown

    context_file = brief_path / CONTEXT_DIR / "files" / (file_path.replace("/", "__").replace("\\", "__") + ".md")
    if context_file.exists():
        content = context_file.read_text()
        is_lite = "<!-- lite -->" in content

        # If it's a lite description and BAML is available, upgrade to LLM
        if is_lite and auto_generate and base_path:
            try:
                from ..generation.generator import generate_and_save_file_description, is_baml_available
                if is_baml_available():
                    if show_progress:
                        print(f"  Upgrading description for {file_path}...", file=sys.stderr)
                    upgraded = generate_and_save_file_description(brief_path, base_path, file_path)
                    if upgraded:
                        return upgraded
            except Exception:
                pass

        return content

    # Lazy generation if requested
    if auto_generate and base_path:
        try:
            from ..generation.generator import generate_and_save_file_description, is_baml_available

            # Show warning once if LLM is unavailable
            if not is_baml_available() and not _llm_warning_shown:
                _llm_warning_shown = True
                print(
                    "Note: LLM not configured - descriptions will show code structure only.\n"
                    "      To enable full descriptions, configure BAML with an API key.\n"
                    "      See: brief describe --help",
                    file=sys.stderr
                )

            if show_progress:
                if is_baml_available():
                    print(f"  Generating description for {file_path}...", file=sys.stderr)
                else:
                    print(f"  Creating signature summary for {file_path}...", file=sys.stderr)

            return generate_and_save_file_description(brief_path, base_path, file_path)
        except Exception:
            pass

    return None


def get_file_context(
    brief_path: Path,
    file_path: str,
    auto_generate_descriptions: bool = False,
    base_path: Optional[Path] = None
) -> dict[str, Any]:
    """Get full context for a specific file.

    Args:
        brief_path: Path to .brief directory
        file_path: Relative path to the file
        auto_generate_descriptions: If True, generate descriptions on-demand if missing
        base_path: Base path for the project (required if auto_generate_descriptions is True)

    Returns:
        Dict containing file context (record, classes, functions, imports, description, etc.)
    """
    # Get manifest record
    file_record = None
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file" and record["path"] == file_path:
            file_record = record
        elif record.get("file") == file_path:
            if record["type"] == "class":
                classes.append(record)
            elif record["type"] == "function":
                functions.append(record)

    # Get relationships
    imports: list[str] = []
    imported_by: list[str] = []
    for rel in read_jsonl(brief_path / RELATIONSHIPS_FILE):
        if rel.get("type") == "imports":
            if rel["from_file"] == file_path:
                imports.append(rel["to_file"])
            elif rel["to_file"] == file_path:
                imported_by.append(rel["from_file"])

    # Get description (with optional lazy generation)
    description = get_file_description(
        brief_path, file_path,
        auto_generate=auto_generate_descriptions,
        base_path=base_path
    )

    return {
        "path": file_path,
        "record": file_record,
        "classes": classes,
        "functions": functions,
        "imports": imports,
        "imported_by": imported_by,
        "description": description
    }


def get_doc_context(
    brief_path: Path,
    doc_path: str,
) -> dict[str, Any]:
    """Get context for a documentation file.

    Args:
        brief_path: Path to .brief directory
        doc_path: Relative path to the doc file

    Returns:
        Dict containing doc context (path, title, headings, first_paragraph, etc.)
    """
    # Find the doc record in manifest
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "doc" and record["path"] == doc_path:
            return {
                "path": doc_path,
                "record_type": "doc",
                "title": record.get("title"),
                "headings": record.get("headings", []),
                "first_paragraph": record.get("first_paragraph"),
            }

    # Not found - return minimal context
    return {
        "path": doc_path,
        "record_type": "doc",
        "title": Path(doc_path).stem,
        "headings": [],
        "first_paragraph": None,
    }


def get_relevant_contracts(
    brief_path: Path,
    base_path: Path,
    query: str,
    file_paths: Optional[list[str]] = None
) -> list[str]:
    """Get contracts relevant to a query or file paths.

    Args:
        brief_path: Path to .brief directory
        base_path: Base path for the project
        query: Query string to match against
        file_paths: Optional list of file paths to match contracts by affected files

    Returns:
        List of contract descriptions as strings
    """
    relevant = []
    query_terms = query.lower().split()

    # Try to detect contracts (faster than parsing markdown)
    try:
        detector = ContractDetector(brief_path, base_path)
        contracts = detector.detect_all()

        for contract in contracts:
            score = 0

            # Match against query terms
            name_lower = contract.name.lower()
            rule_lower = contract.rule.lower()
            for term in query_terms:
                if term in name_lower:
                    score += 2
                if term in rule_lower:
                    score += 1
                if term in contract.category.lower():
                    score += 1

            # Match against file paths
            if file_paths:
                for fp in file_paths:
                    if fp in contract.files_affected:
                        score += 3
                    # Also check if file is in the same directory as affected files
                    fp_dir = str(Path(fp).parent)
                    if any(fp_dir in str(Path(af).parent) for af in contract.files_affected):
                        score += 1

            if score > 0:
                relevant.append((score, f"[{contract.category}] {contract.name}: {contract.rule}"))

        # Sort by score and return top contracts
        relevant.sort(key=lambda x: -x[0])
        return [desc for _, desc in relevant[:10]]

    except Exception:
        # Fallback: parse contracts.md if detection fails
        contracts_file = brief_path / CONTEXT_DIR / "contracts.md"
        if contracts_file.exists():
            content = contracts_file.read_text()
            # Extract contract names and rules from markdown
            current_name = ""
            for line in content.split("\n"):
                if line.startswith("## Contract: "):
                    current_name = line.replace("## Contract: ", "")
                elif line.startswith("### Rule") and current_name:
                    # Next non-empty line is the rule
                    pass
                elif current_name and any(term in line.lower() for term in query_terms):
                    relevant.append(current_name)
                    current_name = ""

        return relevant[:10]


def get_relevant_paths(
    brief_path: Path,
    base_path: Path,
    query: str,
    file_paths: Optional[list[str]] = None
) -> list[dict[str, str]]:
    """Get execution paths relevant to a query or file paths.

    Args:
        brief_path: Path to .brief directory
        base_path: Base path for the project
        query: Query string to match against
        file_paths: Optional list of file paths to match paths by related files

    Returns:
        List of dicts with 'name' and 'flow' keys containing flow diagrams
    """
    relevant: list[tuple[int, dict[str, str]]] = []
    query_terms = query.lower().split()

    try:
        tracer = PathTracer(brief_path, base_path)
        path_names = tracer.list_paths()

        for path_name in path_names:
            score = 0

            # Match path name against query
            name_lower = path_name.lower()
            for term in query_terms:
                if term in name_lower:
                    score += 2

            # Load path as object to check content and generate flow
            path_obj = tracer.load_path_as_object(path_name)
            if path_obj:
                # Check if query terms appear in any step
                for step in path_obj.steps:
                    step_text = f"{step.function} {step.description}".lower()
                    for term in query_terms:
                        if term in step_text:
                            score += 1

                # Check if any of our file paths are in the path's files
                if file_paths:
                    for fp in file_paths:
                        if fp in path_obj.related_files:
                            score += 3

                if score > 0:
                    relevant.append((score, {
                        "name": path_name,
                        "flow": path_obj.to_flow()
                    }))

        # Sort by score and return top 3 (since flows are larger)
        relevant.sort(key=lambda x: -x[0])
        return [item for _, item in relevant[:3]]

    except Exception:
        return []


def build_context_for_file(
    brief_path: Path,
    file_path: str,
    base_path: Optional[Path] = None,
    auto_generate_descriptions: bool = False
) -> ContextPackage:
    """Build a context package for working on a specific file.

    Args:
        brief_path: Path to .brief directory
        file_path: Relative path to the file
        base_path: Base path for the project (defaults to brief_path.parent)
        auto_generate_descriptions: Whether to generate descriptions on-demand if missing
    """
    package = ContextPackage(query=f"file: {file_path}")

    if base_path is None:
        base_path = brief_path.parent

    # Get primary file context
    primary = get_file_context(
        brief_path, file_path,
        auto_generate_descriptions=auto_generate_descriptions,
        base_path=base_path
    )
    package.primary_files.append(primary)

    # Add imported files as related
    for imp_path in primary["imports"]:
        imp_context = get_file_context(
            brief_path, imp_path,
            auto_generate_descriptions=auto_generate_descriptions,
            base_path=base_path
        )
        imp_context["reason"] = "imported by primary file"
        package.related_files.append(imp_context)

    # Add files that import this as related
    for imp_path in primary["imported_by"][:5]:  # Limit
        imp_context = get_file_context(
            brief_path, imp_path,
            auto_generate_descriptions=auto_generate_descriptions,
            base_path=base_path
        )
        imp_context["reason"] = "imports primary file"
        package.related_files.append(imp_context)

    # Get relevant patterns from memory using MemoryStore
    try:
        memory_store = MemoryStore(brief_path)
        patterns = memory_store.recall_for_file(file_path)
        for pattern in patterns[:10]:
            package.patterns.append({
                "key": pattern.key,
                "value": pattern.value,
                "tags": pattern.tags,
                "confidence": pattern.confidence
            })
    except Exception:
        # Fallback to basic keyword matching
        memory_file = brief_path / MEMORY_FILE
        if memory_file.exists():
            for pattern in read_jsonl(memory_file):
                key_lower = pattern.get("key", "").lower()
                if any(word in key_lower for word in file_path.lower().split("/")):
                    package.patterns.append(pattern)

    # Get relevant contracts
    all_files = [file_path] + primary["imports"] + primary["imported_by"][:5]
    package.contracts = get_relevant_contracts(
        brief_path, base_path, file_path, all_files
    )

    # Get relevant execution paths
    package.execution_paths = get_relevant_paths(
        brief_path, base_path, file_path, all_files
    )

    return package


def build_context_for_query(
    brief_path: Path,
    query: str,
    search_func: Callable[[str], list[dict[str, Any]]] | None = None,
    base_path: Optional[Path] = None,
    include_contracts: bool = True,
    include_paths: bool = True,
    include_patterns: bool = True,
    auto_generate_descriptions: bool = False
) -> ContextPackage:
    """Build a context package for a task description.

    Args:
        brief_path: Path to .brief directory
        query: Task description or search query
        search_func: Optional search function for semantic search
        base_path: Base path for the project (defaults to brief_path.parent)
        include_contracts: Whether to include relevant contracts
        include_paths: Whether to include relevant execution paths
        include_patterns: Whether to include relevant memory patterns
        auto_generate_descriptions: Whether to generate descriptions on-demand if missing

    Returns:
        ContextPackage with files, patterns, contracts, and execution paths
    """
    package = ContextPackage(query=query)

    if base_path is None:
        base_path = brief_path.parent

    # Collect all file paths for matching
    all_file_paths: list[str] = []

    if search_func:
        # Use semantic search to find relevant files
        results = search_func(query)
        for result in results[:5]:  # Top 5
            result_path = result["path"]
            # Check if this is a doc file or code file
            if result_path.endswith(".md"):
                context = get_doc_context(brief_path, result_path)
            else:
                context = get_file_context(
                    brief_path, result_path,
                    auto_generate_descriptions=auto_generate_descriptions,
                    base_path=base_path
                )
            context["relevance"] = result.get("score", 0)
            package.primary_files.append(context)
            all_file_paths.append(result_path)

        # Add related files (only for code files, not docs)
        for primary in package.primary_files[:3]:
            if primary.get("record_type") == "doc":
                continue  # Docs don't have imports
            for imp_path in primary.get("imports", [])[:2]:
                imp_context = get_file_context(
                    brief_path, imp_path,
                    auto_generate_descriptions=auto_generate_descriptions,
                    base_path=base_path
                )
                imp_context["reason"] = f"imported by {primary['path']}"
                if imp_context not in package.related_files:
                    package.related_files.append(imp_context)
                    all_file_paths.append(imp_path)
    else:
        # Improved keyword search across manifest (classes, functions, docstrings, docs)
        scored_results = search_manifest(brief_path, query, max_results=20)

        # Group by file and collect matched functions
        file_scores: dict[str, int] = {}
        file_functions: dict[str, list[str]] = {}
        doc_scores: dict[str, int] = {}  # Separate tracking for doc files

        for score, record in scored_results:
            if record["type"] == "file":
                file_path = record["path"]
                file_scores[file_path] = file_scores.get(file_path, 0) + score
            elif record["type"] == "doc":
                # Documentation files tracked separately
                doc_path = record["path"]
                doc_scores[doc_path] = doc_scores.get(doc_path, 0) + score
            elif record["type"] in ("class", "function"):
                file_path = record["file"]
                file_scores[file_path] = file_scores.get(file_path, 0) + score
                # Track function names for call graph expansion
                func_name = record.get("name", "")
                class_name = record.get("class_name")
                if class_name:
                    func_name = f"{class_name}.{func_name}"
                if file_path not in file_functions:
                    file_functions[file_path] = []
                file_functions[file_path].append(func_name)

        # Sort code files by score and take top ones
        sorted_files = sorted(file_scores.items(), key=lambda x: -x[1])

        seed_functions: list[str] = []
        for file_path, score in sorted_files[:5]:
            context = get_file_context(
                brief_path, file_path,
                auto_generate_descriptions=auto_generate_descriptions,
                base_path=base_path
            )
            context["relevance"] = score
            package.primary_files.append(context)
            all_file_paths.append(file_path)
            # Collect functions for call graph expansion
            seed_functions.extend(file_functions.get(file_path, []))

        # Add matching documentation files
        sorted_docs = sorted(doc_scores.items(), key=lambda x: -x[1])
        for doc_path, score in sorted_docs[:3]:  # Top 3 docs
            context = get_doc_context(brief_path, doc_path)
            context["relevance"] = score
            package.primary_files.append(context)
            all_file_paths.append(doc_path)

        # Expand using call graph
        if seed_functions:
            call_related = expand_with_call_graph(
                brief_path, all_file_paths, seed_functions[:10], max_related=5
            )
            for rel in call_related:
                if rel["path"] not in all_file_paths:
                    context = get_file_context(
                        brief_path, rel["path"],
                        auto_generate_descriptions=auto_generate_descriptions,
                        base_path=base_path
                    )
                    context["reason"] = rel["reason"]
                    package.related_files.append(context)
                    all_file_paths.append(rel["path"])

    # Get relevant patterns from memory using MemoryStore
    if include_patterns:
        try:
            memory_store = MemoryStore(brief_path)
            # Use the context-aware recall
            query_keywords = query.split()
            patterns = memory_store.recall_for_context(query_keywords)
            for pattern in patterns[:10]:
                package.patterns.append({
                    "key": pattern.key,
                    "value": pattern.value,
                    "tags": pattern.tags,
                    "confidence": pattern.confidence
                })
        except Exception:
            # Fallback to basic keyword matching
            memory_file = brief_path / MEMORY_FILE
            if memory_file.exists():
                for pattern in read_jsonl(memory_file):
                    tags = pattern.get("tags", [])
                    key = pattern.get("key", "")
                    if any(term in key.lower() or term in str(tags).lower()
                           for term in query.lower().split()):
                        package.patterns.append(pattern)

    # Get relevant contracts
    if include_contracts:
        package.contracts = get_relevant_contracts(
            brief_path, base_path, query, all_file_paths
        )

    # Get relevant execution paths
    if include_paths:
        package.execution_paths = get_relevant_paths(
            brief_path, base_path, query, all_file_paths
        )

    return package
