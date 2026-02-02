"""Lite description generator — structured text from AST data only, no LLM calls.

Produces markdown descriptions in the same format as LLM-generated descriptions,
using only data available from the manifest (class names, function signatures,
docstrings, decorators, import relationships). These can be embedded for semantic
search without requiring LLM-generated descriptions first.
"""

from pathlib import Path
from ..storage import read_jsonl
from ..config import MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR


def generate_lite_description(brief_path: Path, file_path: str) -> str:
    """Generate a structured text description from manifest data only.

    Reads manifest records for the file and assembles purpose, contents,
    role, dependencies, and exports from AST-parsed data (class names,
    function signatures, docstrings, decorators, import relationships).

    Args:
        brief_path: Path to .brief directory
        file_path: Relative path to the file

    Returns:
        Markdown-formatted description string, or empty string if file not found.
    """
    # Collect manifest data for this file
    file_record = None
    classes: list[dict] = []
    functions: list[dict] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file" and record["path"] == file_path:
            file_record = record
        elif record.get("file") == file_path:
            if record["type"] == "class":
                classes.append(record)
            elif record["type"] == "function":
                functions.append(record)

    if not file_record:
        return ""

    # Collect import relationships
    imports_to: list[str] = []  # files this file imports
    imported_by: list[str] = []  # files that import this file

    for rel in read_jsonl(brief_path / RELATIONSHIPS_FILE):
        if rel.get("type") == "imports":
            if rel["from_file"] == file_path:
                imports_to.append(rel["to_file"])
            elif rel["to_file"] == file_path:
                imported_by.append(rel["from_file"])

    # Separate module-level functions from methods
    module_functions = [f for f in functions if not f.get("class_name")]
    methods = [f for f in functions if f.get("class_name")]

    # Build each section
    purpose = _build_purpose(file_record, classes, module_functions)
    contents = _build_contents(classes, module_functions, methods)
    role = _build_role(file_record, classes, module_functions)
    dependencies = _build_dependencies(imports_to)
    exports = _build_exports(classes, module_functions, imported_by)

    return f"""**Purpose**: {purpose}

**Contents**: {contents}

**Role**: {role}

**Dependencies**: {dependencies}

**Exports**: {exports}
"""


def _build_purpose(
    file_record: dict,
    classes: list[dict],
    module_functions: list[dict]
) -> str:
    """Build purpose string from available docstrings and names."""
    module_name = file_record.get("module", "")

    # Best case: use the first class docstring's first line
    for cls in classes:
        docstring = cls.get("docstring")
        if docstring:
            first_line = docstring.strip().split("\n")[0].rstrip(".")
            if len(classes) == 1:
                return f"{first_line}."
            return f"{first_line}; plus {len(classes) - 1} additional class{'es' if len(classes) > 2 else ''}."

    # Next: use a function docstring if available
    for func in module_functions:
        docstring = func.get("docstring")
        if docstring:
            first_line = docstring.strip().split("\n")[0].rstrip(".")
            other_count = len(module_functions) - 1
            if other_count > 0:
                return f"{first_line}; plus {other_count} additional function{'s' if other_count > 1 else ''}."
            return f"{first_line}."

    # Fallback: infer from names
    if classes and module_functions:
        return f"Provides {len(classes)} class{'es' if len(classes) > 1 else ''} and {len(module_functions)} function{'s' if len(module_functions) > 1 else ''} for {module_name} functionality."
    elif classes:
        class_names = ", ".join(c["name"] for c in classes[:3])
        return f"Defines {class_names} for {module_name}."
    elif module_functions:
        func_names = ", ".join(f["name"] for f in module_functions[:3])
        return f"Provides functions {func_names} for {module_name}."
    else:
        return f"Part of the {module_name} module."


def _format_signature(func: dict) -> str:
    """Format a function signature from manifest data."""
    prefix = "async def " if func.get("is_async") else "def "
    name = func.get("name", "?")

    params = []
    for p in func.get("params", []):
        if isinstance(p, dict):
            s = p.get("name", "?")
            if p.get("type_hint"):
                s += f": {p['type_hint']}"
            if p.get("default"):
                s += f" = {p['default']}"
        else:
            s = str(p)
        params.append(s)

    returns = func.get("returns")
    ret_str = f" -> {returns}" if returns else ""

    if func.get("is_generator"):
        ret_str = f" -> Generator[{returns}]" if returns else " -> Generator"

    return f"{prefix}{name}({', '.join(params)}){ret_str}"


def _build_contents(
    classes: list[dict],
    module_functions: list[dict],
    methods: list[dict]
) -> str:
    """Build contents section with full structural detail."""
    parts: list[str] = []

    for cls in classes:
        name = cls["name"]
        bases = cls.get("bases", [])
        base_str = f"({', '.join(bases)})" if bases else ""
        docstring = cls.get("docstring", "")
        first_line = docstring.strip().split("\n")[0] if docstring else ""

        cls_desc = f"class {name}{base_str}"
        if first_line:
            cls_desc += f" — {first_line}"

        # Add methods for this class
        cls_methods = [m for m in methods if m.get("class_name") == name]
        method_names = cls.get("methods", [])
        if method_names:
            cls_desc += f". Methods: {', '.join(method_names)}"

        # Add method docstrings for key methods (non-dunder, with docstrings)
        key_method_docs = []
        for m in cls_methods:
            if m["name"].startswith("_") and not m["name"] == "__init__":
                continue
            m_doc = m.get("docstring", "")
            if m_doc:
                first = m_doc.strip().split("\n")[0]
                sig = _format_signature(m)
                key_method_docs.append(f"{sig} — {first}")

        if key_method_docs:
            cls_desc += ". Key method signatures: " + "; ".join(key_method_docs[:5])

        parts.append(cls_desc)

    for func in module_functions:
        sig = _format_signature(func)
        docstring = func.get("docstring", "")
        first_line = docstring.strip().split("\n")[0] if docstring else ""

        decorators = func.get("decorators", [])
        dec_str = ""
        if decorators:
            dec_str = f" [{', '.join('@' + d for d in decorators)}]"

        if first_line:
            parts.append(f"{sig}{dec_str} — {first_line}")
        else:
            parts.append(f"{sig}{dec_str}")

    if not parts:
        return "This file contains implementation code."

    return "; ".join(parts) + "."


def _build_role(
    file_record: dict,
    classes: list[dict],
    module_functions: list[dict]
) -> str:
    """Infer role from decorators, path position, and structure."""
    module_name = file_record.get("module", "")
    path = file_record.get("path", "")

    # Check for CLI/route decorators
    all_decorators: list[str] = []
    for func in module_functions:
        all_decorators.extend(func.get("decorators", []))

    if any("command" in d or "route" in d for d in all_decorators):
        return f"CLI/API entry point in {module_name}."
    if any("test" in d.lower() or "fixture" in d.lower() for d in all_decorators):
        return f"Test module for {module_name}."

    # Check path patterns
    if "commands/" in path or "cli" in path:
        return f"Command implementation in {module_name}."
    if "test" in path:
        return f"Test module for {module_name}."
    if "__init__" in path:
        return f"Package initializer for {module_name}."
    if "models" in path:
        return f"Data model definitions for {module_name}."
    if "config" in path:
        return f"Configuration and constants for {module_name}."

    if classes:
        return f"Core component in {module_name} providing {len(classes)} class{'es' if len(classes) > 1 else ''}."
    return f"Utility module in {module_name}."


def _build_dependencies(imports_to: list[str]) -> str:
    """Build dependencies string from import relationships."""
    if not imports_to:
        return "No internal dependencies detected."

    # Simplify paths for readability
    deps = [Path(p).name for p in imports_to[:10]]
    result = f"Imports from: {', '.join(deps)}"
    if len(imports_to) > 10:
        result += f" (+{len(imports_to) - 10} more)"
    return result + "."


def _build_exports(
    classes: list[dict],
    module_functions: list[dict],
    imported_by: list[str]
) -> str:
    """Build exports string from public symbols and importers."""
    # Public symbols (no leading underscore)
    public_classes = [c["name"] for c in classes if not c["name"].startswith("_")]
    public_funcs = [f["name"] for f in module_functions if not f["name"].startswith("_")]
    symbols = public_classes + public_funcs

    parts: list[str] = []
    if symbols:
        parts.append(f"Public symbols: {', '.join(symbols[:10])}")
        if len(symbols) > 10:
            parts[-1] += f" (+{len(symbols) - 10} more)"

    if imported_by:
        importers = [Path(p).name for p in imported_by[:5]]
        parts.append(f"Used by: {', '.join(importers)}")
        if len(imported_by) > 5:
            parts[-1] += f" (+{len(imported_by) - 5} more)"

    return "; ".join(parts) + "." if parts else "No public exports detected."


def generate_and_save_lite_description(brief_path: Path, file_path: str) -> str | None:
    """Generate lite description and save to .brief/context/files/*.md.

    Args:
        brief_path: Path to .brief directory
        file_path: Relative path to the file

    Returns:
        The full markdown content (with header), or None if file not found.
    """
    description = generate_lite_description(brief_path, file_path)
    if not description:
        return None

    context_file = brief_path / CONTEXT_DIR / "files" / (
        file_path.replace("/", "__").replace("\\", "__") + ".md"
    )
    context_file.parent.mkdir(parents=True, exist_ok=True)

    header = f"# {file_path}\n\n"
    full_content = header + description
    context_file.write_text(full_content)

    return full_content


def generate_all_lite_descriptions(brief_path: Path) -> int:
    """Generate lite descriptions for all Python files in manifest.

    Args:
        brief_path: Path to .brief directory

    Returns:
        Count of descriptions generated.
    """
    count = 0
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file" and record.get("path", "").endswith(".py"):
            result = generate_and_save_lite_description(brief_path, record["path"])
            if result:
                count += 1
    return count
