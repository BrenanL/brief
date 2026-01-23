"""Directory tree visualization with analysis status."""
from pathlib import Path
from typing import Any
from ..storage import read_jsonl
from ..config import MANIFEST_FILE, CONTEXT_DIR


def build_tree_structure(brief_path: Path, base_path: Path) -> dict[str, Any]:
    """Build nested tree structure from manifest."""
    import re

    # Load all tracked files (code, docs, and other)
    analyzed_files: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            analyzed_files[record["path"]] = {
                "hash": record.get("file_hash"),
                "analyzed_at": record.get("analyzed_at"),
                "context_ref": record.get("context_ref"),
                "file_type": "code",
                "parsed": record.get("parsed", True),
            }
        elif record["type"] == "doc":
            # Doc files - they have built-in summaries (title, first_paragraph)
            analyzed_files[record["path"]] = {
                "hash": record.get("file_hash"),
                "analyzed_at": record.get("analyzed_at"),
                "context_ref": record.get("context_ref"),
                "file_type": "doc",
                "title": record.get("title"),
                # Docs are considered "described" if they have a title/first_paragraph
                "has_description": bool(record.get("title") or record.get("first_paragraph")),
            }

    # Also check for description files on disk
    files_dir = brief_path / CONTEXT_DIR / "files"
    if files_dir.exists():
        for md_file in files_dir.glob("*.md"):
            # Convert filename back to path
            stem = md_file.stem
            # Remove extension suffix if present
            for ext in [".py", ".sh", ".json", ".toml", ".txt", ".yaml", ".yml"]:
                if stem.endswith(ext):
                    stem = stem[:-len(ext)]
                    break
            # Handle dunder patterns
            stem = re.sub(r'____(\w+)__', r'/@@\1@@', stem)
            path = stem.replace("__", "/")
            path = path.replace("@@", "__")
            # Try to find matching file in manifest
            for ext in [".py", ".sh", ".json", ".toml", ".txt", ".yaml", ".yml", ""]:
                test_path = path + ext
                if test_path in analyzed_files:
                    analyzed_files[test_path]["has_description"] = True
                    break

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
    descriptions: dict[str, str] | None = None,
    use_color: bool = False
) -> list[str]:
    """Format tree structure as text lines."""
    lines: list[str] = []
    items = sorted(tree.items())

    for i, (name, value) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "

        if isinstance(value, dict) and "hash" not in value:
            # Directory
            if use_color:
                lines.append(f"{prefix}{connector}[bold blue]{name}/[/bold blue]")
            else:
                lines.append(f"{prefix}{connector}{name}/")
            extension = "    " if is_last else "│   "
            lines.extend(format_tree(value, prefix + extension, show_status, descriptions, use_color))
        else:
            # File
            status = ""
            if show_status:
                has_desc = value.get("context_ref") or value.get("has_description")
                file_type = value.get("file_type", "code")
                is_parsed = value.get("parsed", True)

                if has_desc:
                    if use_color:
                        status = " [green]✓[/green]"
                    else:
                        status = " ✓"
                elif value.get("hash"):
                    if use_color:
                        status = " [yellow]○[/yellow]"
                    else:
                        status = " ○"
                else:
                    if use_color:
                        status = " [red]✗[/red]"
                    else:
                        status = " ✗"

                # Add file type indicator for non-code files
                if file_type == "doc":
                    if use_color:
                        status += " [cyan][doc][/cyan]"
                    else:
                        status += " [doc]"
                elif not is_parsed:
                    if use_color:
                        status += " [dim][other][/dim]"
                    else:
                        status += " [other]"

            desc = ""
            if descriptions and name in descriptions:
                desc = f" - {descriptions[name][:40]}..."

            lines.append(f"{prefix}{connector}{name}{status}{desc}")

    return lines


def generate_tree(
    brief_path: Path,
    base_path: Path,
    path_filter: str | None = None,
    show_status: bool = True,
    use_color: bool = False
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

    if use_color:
        lines = ["[bold]Project Structure:[/bold]"]
    else:
        lines = ["Project Structure:"]
    lines.extend(format_tree(tree, show_status=show_status, use_color=use_color))
    return "\n".join(lines)
