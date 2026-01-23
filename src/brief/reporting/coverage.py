"""Analysis coverage reporting."""
from pathlib import Path
from typing import Any
from ..storage import read_jsonl
from ..config import MANIFEST_FILE, CONTEXT_DIR
from ..analysis.manifest import find_python_files
from ..analysis.parser import compute_file_hash


def calculate_coverage(
    brief_path: Path,
    base_path: Path,
    exclude_patterns: list[str]
) -> dict[str, Any]:
    """Calculate analysis coverage statistics."""
    # Get all Python files
    all_files = list(find_python_files(base_path, exclude_patterns))

    # Get analyzed files from manifest and track all record types
    analyzed: dict[str, dict[str, Any]] = {}
    doc_files: list[dict[str, Any]] = []
    unparsed_files: list[dict[str, Any]] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            if record.get("parsed", True):
                analyzed[record["path"]] = record
            else:
                unparsed_files.append(record)
        elif record["type"] == "doc":
            doc_files.append(record)

    # Check for descriptions (any file type)
    import re
    context_path = brief_path / CONTEXT_DIR
    described_files: set[str] = set()
    if (context_path / "files").exists():
        for md_file in (context_path / "files").glob("*.md"):
            # Convert filename back to path
            # Filename pattern: src__brief__cli.py.md -> src/brief/cli.py
            # Also handles: scripts__demo.sh.md -> scripts/demo.sh
            stem = md_file.stem  # e.g., "src__brief__cli.py" or "scripts__demo.sh"

            # Remove known extensions from end
            original_ext = ""
            for ext in [".py", ".sh", ".bash", ".json", ".toml", ".yaml", ".yml", ".txt", ".js", ".ts"]:
                if stem.endswith(ext):
                    original_ext = ext
                    stem = stem[:-len(ext)]
                    break

            # Replace dunder patterns: ____name__ -> /@@name@@
            # This handles __init__, __main__, etc.
            stem = re.sub(r'____(\w+)__', r'/@@\1@@', stem)
            # Replace path separators
            path = stem.replace("__", "/")
            # Restore dunders
            path = path.replace("@@", "__")
            described_files.add(path + original_ext)

    # Categorize files
    analyzed_paths = set(analyzed.keys())
    all_paths = set(str(f.relative_to(base_path)) for f in all_files)

    # Find stale descriptions
    stale_descriptions = find_stale_descriptions(brief_path, base_path)

    # Group unparsed files by extension and track descriptions
    unparsed_by_ext: dict[str, int] = {}
    unparsed_described: list[str] = []
    unparsed_not_described: list[str] = []
    for f in unparsed_files:
        ext = f.get("extension", "unknown")
        unparsed_by_ext[ext] = unparsed_by_ext.get(ext, 0) + 1
        # Check if this unparsed file has a description
        if f["path"] in described_files or f.get("context_ref"):
            unparsed_described.append(f["path"])
        else:
            unparsed_not_described.append(f["path"])

    return {
        "total_files": len(all_paths),
        "analyzed_files": len(analyzed_paths & all_paths),
        "described_files": len(described_files & all_paths),
        "stale_descriptions": len(stale_descriptions),
        "stale_description_files": [f["path"] for f in stale_descriptions],
        "not_analyzed": sorted(all_paths - analyzed_paths),
        "analyzed_not_described": sorted(analyzed_paths - described_files),
        # New fields for multi-file support
        "doc_files": len(doc_files),
        "doc_file_list": [d["path"] for d in doc_files],
        "unparsed_files": len(unparsed_files),
        "unparsed_file_list": [f["path"] for f in unparsed_files],
        "unparsed_by_extension": unparsed_by_ext,
        "unparsed_described": len(unparsed_described),
        "unparsed_not_described": sorted(unparsed_not_described),
    }


def format_coverage(coverage: dict[str, Any], show_unparsed: bool = False) -> str:
    """Format coverage statistics.

    Args:
        coverage: Coverage data from calculate_coverage()
        show_unparsed: If True, list all unparsed files
    """
    total = coverage["total_files"]
    analyzed = coverage["analyzed_files"]
    described = coverage["described_files"]
    stale = coverage.get("stale_descriptions", 0)
    doc_count = coverage.get("doc_files", 0)
    unparsed_count = coverage.get("unparsed_files", 0)

    analysis_pct = (analyzed / total * 100) if total > 0 else 0
    description_pct = (described / total * 100) if total > 0 else 0

    # Calculate unparsed description stats
    unparsed_described = coverage.get("unparsed_described", 0)
    unparsed_not_described = coverage.get("unparsed_not_described", [])
    unparsed_desc_pct = (unparsed_described / unparsed_count * 100) if unparsed_count > 0 else 0

    lines = [
        "Analysis Coverage Report",
        "=" * 40,
        "",
        f"Python files:        {total}",
        f"  Analyzed:          {analyzed} ({analysis_pct:.1f}%)",
        f"  Described (LLM):   {described} ({description_pct:.1f}%)",
        "",
        f"Documentation files: {doc_count} (have built-in summaries)",
        f"Other tracked files: {unparsed_count}",
        f"  Described (LLM):   {unparsed_described} ({unparsed_desc_pct:.1f}%)",
    ]

    # Show unparsed files by extension
    unparsed_by_ext = coverage.get("unparsed_by_extension", {})
    if unparsed_by_ext:
        ext_summary = ", ".join(f"{ext}: {count}" for ext, count in sorted(unparsed_by_ext.items()))
        lines.append(f"  Types: {ext_summary}")

    lines.append("")

    # Show freshness info
    if stale > 0:
        lines.append(f"Stale descriptions:  {stale} (files changed since description)")
    else:
        lines.append(f"Stale descriptions:  0 (all descriptions up to date)")

    lines.append("")

    if coverage["not_analyzed"]:
        lines.append(f"Not yet analyzed ({len(coverage['not_analyzed'])}):")
        for path in coverage["not_analyzed"][:10]:
            lines.append(f"  - {path}")
        if len(coverage["not_analyzed"]) > 10:
            lines.append(f"  ... and {len(coverage['not_analyzed']) - 10} more")

    if coverage["analyzed_not_described"]:
        lines.append("")
        lines.append(f"Analyzed but not described ({len(coverage['analyzed_not_described'])}):")
        for path in coverage["analyzed_not_described"][:10]:
            lines.append(f"  - {path}")
        if len(coverage["analyzed_not_described"]) > 10:
            lines.append(f"  ... and {len(coverage['analyzed_not_described']) - 10} more")

    # Show stale description files
    stale_files = coverage.get("stale_description_files", [])
    if stale_files:
        lines.append("")
        lines.append(f"Stale descriptions ({len(stale_files)}):")
        for path in stale_files[:10]:
            lines.append(f"  - {path}")
        if len(stale_files) > 10:
            lines.append(f"  ... and {len(stale_files) - 10} more")
        lines.append("")
        lines.append("Run 'brief describe batch' to regenerate stale descriptions.")

    # Show other files without descriptions
    other_not_described = coverage.get("unparsed_not_described", [])
    if other_not_described:
        lines.append("")
        lines.append(f"Other files without descriptions ({len(other_not_described)}):")
        for path in other_not_described[:10]:
            lines.append(f"  - {path}")
        if len(other_not_described) > 10:
            lines.append(f"  ... and {len(other_not_described) - 10} more")
        lines.append("")
        lines.append("Run 'brief describe batch --include-other' to generate descriptions.")

    # Show unparsed files if requested
    if show_unparsed:
        unparsed_list = coverage.get("unparsed_file_list", [])
        if unparsed_list:
            lines.append("")
            lines.append(f"All other tracked files ({len(unparsed_list)}):")
            for path in unparsed_list:
                lines.append(f"  - {path}")

    return "\n".join(lines)


def find_stale_files(brief_path: Path, base_path: Path) -> list[dict[str, Any]]:
    """Find files that changed since last analysis."""
    stale: list[dict[str, Any]] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            file_path = base_path / record["path"]
            if file_path.exists():
                current_hash = compute_file_hash(file_path)
                if current_hash != record.get("file_hash"):
                    stale.append({
                        "path": record["path"],
                        "analyzed_at": record.get("analyzed_at"),
                        "old_hash": record.get("file_hash"),
                        "new_hash": current_hash
                    })

    return stale


def find_stale_descriptions(brief_path: Path, base_path: Path) -> list[dict[str, Any]]:
    """Find descriptions that are stale (file changed since description was generated)."""
    stale: list[dict[str, Any]] = []

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file" and record.get("context_ref"):
            # File has a description
            description_hash = record.get("description_hash")
            if description_hash:
                # Check if file changed since description was generated
                file_path = base_path / record["path"]
                if file_path.exists():
                    current_hash = compute_file_hash(file_path)
                    if current_hash != description_hash:
                        stale.append({
                            "path": record["path"],
                            "described_at": record.get("described_at"),
                            "description_hash": description_hash,
                            "current_hash": current_hash
                        })

    return stale


def format_stale_descriptions(stale_files: list[dict[str, Any]]) -> str:
    """Format stale descriptions report."""
    if not stale_files:
        return "No stale descriptions. All descriptions are up to date."

    lines = [
        f"Stale Descriptions ({len(stale_files)} files changed since description)",
        "=" * 55,
        ""
    ]

    for f in stale_files:
        lines.append(f"  {f['path']}")
        if f.get('described_at'):
            lines.append(f"    Described: {f['described_at']}")

    lines.append("")
    lines.append("Run 'brief describe batch' to regenerate stale descriptions.")

    return "\n".join(lines)


def format_stale(stale_files: list[dict[str, Any]]) -> str:
    """Format stale files report."""
    if not stale_files:
        return "No stale files detected. All analyzed files are up to date."

    lines = [
        f"Stale Files ({len(stale_files)} files changed since analysis)",
        "=" * 50,
        ""
    ]

    for f in stale_files:
        lines.append(f"  {f['path']}")
        lines.append(f"    Last analyzed: {f['analyzed_at']}")

    lines.append("")
    lines.append("Run 'brief analyze refresh' to re-analyze changed files.")

    return "\n".join(lines)
