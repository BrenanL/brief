"""Project and module overview generation."""
from pathlib import Path
from collections import defaultdict
from typing import Any
from ..storage import read_jsonl
from ..config import get_brief_path, MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR


def get_module_structure(brief_path: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Build module structure from manifest."""
    modules: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"files": [], "classes": [], "functions": []}
    )

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            module = record.get("module", "root")
            modules[module]["files"].append(record)
        elif record["type"] == "class":
            # Extract module from file path
            parts = record["file"].replace("/", ".").replace("\\", ".")
            if parts.endswith(".py"):
                parts = parts[:-3]
            module = parts.rsplit(".", 1)[0] if "." in parts else "root"
            modules[module]["classes"].append(record)
        elif record["type"] == "function":
            parts = record["file"].replace("/", ".").replace("\\", ".")
            if parts.endswith(".py"):
                parts = parts[:-3]
            module = parts.rsplit(".", 1)[0] if "." in parts else "root"
            modules[module]["functions"].append(record)

    return dict(modules)


def generate_project_overview(brief_path: Path) -> str:
    """Generate project-level overview text."""
    modules = get_module_structure(brief_path)

    # Count totals
    total_files = sum(len(m["files"]) for m in modules.values())
    total_classes = sum(len(m["classes"]) for m in modules.values())
    total_functions = sum(len(m["functions"]) for m in modules.values())

    # Count relationships
    relationships = list(read_jsonl(brief_path / RELATIONSHIPS_FILE))
    import_count = len([r for r in relationships if r.get("type") == "imports"])

    # Check for context files
    context_path = brief_path / CONTEXT_DIR
    has_project_context = (context_path / "project.md").exists()
    module_contexts = len(list((context_path / "modules").glob("*.md"))) if (context_path / "modules").exists() else 0
    file_contexts = len(list((context_path / "files").glob("*.md"))) if (context_path / "files").exists() else 0

    lines = [
        "=" * 60,
        "PROJECT OVERVIEW",
        "=" * 60,
        "",
        f"Total Files Analyzed: {total_files}",
        f"Total Classes: {total_classes}",
        f"Total Functions: {total_functions}",
        f"Import Relationships: {import_count}",
        "",
        "Context Coverage:",
        f"  Project description: {'Yes' if has_project_context else 'No'}",
        f"  Module descriptions: {module_contexts}",
        f"  File descriptions: {file_contexts}",
        "",
        "=" * 60,
        "MODULES",
        "=" * 60,
    ]

    # Sort modules for consistent output
    for module_name in sorted(modules.keys()):
        data = modules[module_name]
        lines.append("")
        lines.append(f"  {module_name}/")
        lines.append(f"    Files: {len(data['files'])}")
        lines.append(f"    Classes: {len(data['classes'])}")
        lines.append(f"    Functions: {len(data['functions'])}")

        # List top-level classes
        if data['classes']:
            class_names = [c['name'] for c in data['classes'][:5]]
            more = len(data['classes']) - 5
            class_str = ", ".join(class_names)
            if more > 0:
                class_str += f", +{more} more"
            lines.append(f"    Classes: {class_str}")

    return "\n".join(lines)


def generate_module_overview(brief_path: Path, module_name: str) -> str:
    """Generate overview for a specific module."""
    modules = get_module_structure(brief_path)

    if module_name not in modules:
        return f"Module '{module_name}' not found in manifest."

    data = modules[module_name]

    lines = [
        "=" * 60,
        f"MODULE: {module_name}",
        "=" * 60,
        "",
        f"Files: {len(data['files'])}",
        f"Classes: {len(data['classes'])}",
        f"Functions: {len(data['functions'])}",
        "",
    ]

    # List files
    if data['files']:
        lines.append("Files:")
        for f in data['files']:
            analyzed = f.get('analyzed_at', 'unknown')
            lines.append(f"  - {f['path']} (analyzed: {analyzed})")

    # List classes with methods
    if data['classes']:
        lines.append("")
        lines.append("Classes:")
        for c in data['classes']:
            lines.append(f"  {c['name']} (line {c['line']})")
            if c.get('docstring'):
                doc_preview = c['docstring'].split('\n')[0][:60]
                lines.append(f"    {doc_preview}")
            if c.get('methods'):
                lines.append(f"    Methods: {', '.join(c['methods'][:5])}")
                if len(c['methods']) > 5:
                    lines.append(f"             +{len(c['methods']) - 5} more")

    # List module-level functions
    module_funcs = [f for f in data['functions'] if not f.get('class_name')]
    if module_funcs:
        lines.append("")
        lines.append("Functions:")
        for f in module_funcs:
            sig = f['name']
            if f.get('params'):
                param_str = ", ".join(p['name'] for p in f['params'][:3])
                if len(f['params']) > 3:
                    param_str += ", ..."
                sig += f"({param_str})"
            if f.get('returns'):
                sig += f" -> {f['returns']}"
            lines.append(f"  {sig}")

    return "\n".join(lines)
