"""Directory tree visualization with analysis status."""
from pathlib import Path
from typing import Any
from ..storage import read_jsonl
from ..config import MANIFEST_FILE


def build_tree_structure(brief_path: Path, base_path: Path) -> dict[str, Any]:
    """Build nested tree structure from manifest."""
    # Load analyzed files
    analyzed_files: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            analyzed_files[record["path"]] = {
                "hash": record.get("file_hash"),
                "analyzed_at": record.get("analyzed_at"),
                "context_ref": record.get("context_ref")
            }

    # Build tree
    tree: dict[str, Any] = {}
    for file_path in analyzed_files:
        parts = Path(file_path).parts
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = analyzed_files[file_path]

    return tree


def format_tree(
    tree: dict[str, Any],
    prefix: str = "",
    show_status: bool = True,
    descriptions: dict[str, str] | None = None
) -> list[str]:
    """Format tree structure as text lines."""
    lines: list[str] = []
    items = sorted(tree.items())

    for i, (name, value) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "

        if isinstance(value, dict) and "hash" not in value:
            # Directory
            lines.append(f"{prefix}{connector}{name}/")
            extension = "    " if is_last else "│   "
            lines.extend(format_tree(value, prefix + extension, show_status, descriptions))
        else:
            # File
            status = ""
            if show_status:
                if value.get("context_ref"):
                    status = " [DESCRIBED]"
                elif value.get("hash"):
                    status = " [ANALYZED]"
                else:
                    status = " [PENDING]"

            desc = ""
            if descriptions and name in descriptions:
                desc = f" - {descriptions[name][:40]}..."

            lines.append(f"{prefix}{connector}{name}{status}{desc}")

    return lines


def generate_tree(
    brief_path: Path,
    base_path: Path,
    path_filter: str | None = None,
    show_status: bool = True
) -> str:
    """Generate tree visualization."""
    tree = build_tree_structure(brief_path, base_path)

    # Apply filter if provided
    if path_filter:
        parts = Path(path_filter).parts
        current = tree
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return f"Path '{path_filter}' not found in manifest."
        tree = {path_filter: current}

    lines = ["Project Structure:"]
    lines.extend(format_tree(tree, show_status=show_status))
    return "\n".join(lines)
