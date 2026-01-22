"""Dependency visualization."""
from pathlib import Path
from collections import defaultdict
from typing import Any
from ..storage import read_jsonl
from ..config import RELATIONSHIPS_FILE


def get_dependencies(brief_path: Path, file_path: str) -> dict[str, list[dict[str, Any]]]:
    """Get dependencies for a file."""
    imports: list[dict[str, Any]] = []  # Files this file imports
    imported_by: list[dict[str, Any]] = []  # Files that import this file

    for record in read_jsonl(brief_path / RELATIONSHIPS_FILE):
        if record.get("type") == "imports":
            if record["from_file"] == file_path:
                imports.append({
                    "file": record["to_file"],
                    "names": record.get("imports", [])
                })
            elif record["to_file"] == file_path:
                imported_by.append({
                    "file": record["from_file"],
                    "names": record.get("imports", [])
                })

    return {"imports": imports, "imported_by": imported_by}


def format_dependencies(file_path: str, deps: dict[str, list[dict[str, Any]]], reverse: bool = False) -> str:
    """Format dependency info as text."""
    lines = [f"Dependencies for: {file_path}", ""]

    if not reverse:
        lines.append("IMPORTS (this file depends on):")
        if deps["imports"]:
            for imp in deps["imports"]:
                names = ", ".join(imp["names"][:3])
                if len(imp["names"]) > 3:
                    names += f", +{len(imp['names']) - 3} more"
                lines.append(f"  ├── {imp['file']}")
                lines.append(f"  │   └── imports: {names}")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("IMPORTED BY (files that depend on this):")
        if deps["imported_by"]:
            for imp in deps["imported_by"]:
                lines.append(f"  ├── {imp['file']}")
        else:
            lines.append("  (none)")
    else:
        # Reverse mode - only show what depends on this
        lines.append("FILES THAT DEPEND ON THIS:")
        if deps["imported_by"]:
            for imp in deps["imported_by"]:
                names = ", ".join(imp["names"][:3])
                lines.append(f"  ├── {imp['file']}")
                lines.append(f"  │   └── uses: {names}")
        else:
            lines.append("  (none)")

    return "\n".join(lines)


def generate_dependency_graph(brief_path: Path) -> str:
    """Generate full dependency graph summary."""
    relationships = list(read_jsonl(brief_path / RELATIONSHIPS_FILE))
    imports = [r for r in relationships if r.get("type") == "imports"]

    # Count incoming/outgoing edges per file
    outgoing: dict[str, int] = defaultdict(int)
    incoming: dict[str, int] = defaultdict(int)

    for imp in imports:
        outgoing[imp["from_file"]] += 1
        incoming[imp["to_file"]] += 1

    all_files = set(outgoing.keys()) | set(incoming.keys())

    lines = [
        "Dependency Graph Summary",
        "=" * 40,
        f"Total files with dependencies: {len(all_files)}",
        f"Total import relationships: {len(imports)}",
        "",
        "Most dependencies (imports most other files):",
    ]

    top_importers = sorted(outgoing.items(), key=lambda x: -x[1])[:5]
    for file, count in top_importers:
        lines.append(f"  {file}: {count} imports")

    lines.append("")
    lines.append("Most depended on (imported by most files):")

    top_imported = sorted(incoming.items(), key=lambda x: -x[1])[:5]
    for file, count in top_imported:
        lines.append(f"  {file}: imported by {count} files")

    return "\n".join(lines)
