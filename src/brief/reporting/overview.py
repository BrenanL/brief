"""Project and module overview generation."""
from pathlib import Path
from collections import defaultdict
from typing import Any
from ..storage import read_jsonl
from ..config import get_brief_path, MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR


def get_module_structure(brief_path: Path) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Build module structure from manifest.

    Groups records by Python package (directory with __init__.py or containing .py files).
    Only includes actual Python modules, not scripts or config files.
    """
    modules: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"files": [], "classes": [], "functions": []}
    )

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            # Only include Python files
            if not record.get("path", "").endswith(".py"):
                continue

            module = record.get("module", "")
            if not module:
                # Extract module from path for Python files
                path = record.get("path", "")
                if "/" in path or "\\" in path:
                    # Get directory part
                    parts = path.replace("\\", "/").split("/")
                    # Remove filename
                    parts = parts[:-1]
                    module = ".".join(parts) if parts else "root"
                else:
                    module = "root"

            modules[module]["files"].append(record)

        elif record["type"] == "class":
            # Extract module from file path
            file_path = record.get("file", "")
            if not file_path.endswith(".py"):
                continue

            parts = file_path.replace("\\", "/").split("/")
            parts = parts[:-1]  # Remove filename
            module = ".".join(parts) if parts else "root"
            modules[module]["classes"].append(record)

        elif record["type"] == "function":
            file_path = record.get("file", "")
            if not file_path.endswith(".py"):
                continue

            parts = file_path.replace("\\", "/").split("/")
            parts = parts[:-1]
            module = ".".join(parts) if parts else "root"
            modules[module]["functions"].append(record)

    return dict(modules)


def generate_project_overview_rich(brief_path: Path) -> None:
    """Generate project-level overview with rich formatting (prints directly)."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    modules = get_module_structure(brief_path)
    console = Console()

    if not modules:
        console.print("No Python modules found. Run 'brief analyze all' first.")
        return

    # Sort modules: src modules first, then others
    def module_sort_key(name: str) -> tuple[int, str]:
        if name.startswith("src"):
            return (0, name)
        elif name == "root":
            return (2, name)
        elif name.startswith("tests"):
            return (3, name)
        return (1, name)

    sorted_modules = sorted(modules.keys(), key=module_sort_key)

    console.print("[bold]Project Architecture[/bold]")
    console.print()

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Package", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Classes", justify="right")
    table.add_column("Functions", justify="right")
    table.add_column("Key Classes", max_width=40)

    for module_name in sorted_modules:
        data = modules[module_name]
        file_count = len(data['files'])
        class_count = len(data['classes'])
        func_count = len(data['functions'])

        # Get top class names
        class_names = [c['name'] for c in data['classes'][:3]]
        if len(data['classes']) > 3:
            class_names.append(f"+{len(data['classes']) - 3}")
        class_str = ", ".join(class_names) if class_names else "-"

        # Format module name for display
        display_name = module_name if module_name else "(root)"
        if display_name.startswith("src.brief"):
            display_name = display_name.replace("src.brief", "brief")

        table.add_row(
            display_name,
            str(file_count),
            str(class_count),
            str(func_count),
            class_str
        )

    console.print(table)

    # Summary
    total_files = sum(len(m["files"]) for m in modules.values())
    total_classes = sum(len(m["classes"]) for m in modules.values())
    total_functions = sum(len(m["functions"]) for m in modules.values())

    console.print()
    console.print(f"[dim]Total: {len(modules)} packages, {total_files} files, {total_classes} classes, {total_functions} functions[/dim]")


def generate_project_overview(brief_path: Path, use_rich: bool = True) -> str:
    """Generate project-level overview text.

    Shows the high-level architecture: main packages and their key components.
    """
    modules = get_module_structure(brief_path)

    if not modules:
        return "No Python modules found. Run 'brief analyze all' first."

    # Sort modules: src modules first, then others
    def module_sort_key(name: str) -> tuple[int, str]:
        if name.startswith("src"):
            return (0, name)
        elif name == "root":
            return (2, name)
        elif name.startswith("tests"):
            return (3, name)
        return (1, name)

    sorted_modules = sorted(modules.keys(), key=module_sort_key)

    if use_rich:
        generate_project_overview_rich(brief_path)
        return ""  # Rich output is printed directly
    else:
        # Plain text fallback
        lines = ["Project Architecture", "=" * 50, ""]

        for module_name in sorted_modules:
            data = modules[module_name]
            class_names = [c['name'] for c in data['classes'][:3]]
            class_str = ", ".join(class_names) if class_names else "(none)"

            lines.append(f"{module_name or '(root)'}")
            lines.append(f"  Files: {len(data['files'])}  Classes: {len(data['classes'])}  Functions: {len(data['functions'])}")
            lines.append(f"  Key: {class_str}")
            lines.append("")

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
