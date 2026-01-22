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

    # Get analyzed files from manifest
    analyzed: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(brief_path / MANIFEST_FILE):
        if record["type"] == "file":
            analyzed[record["path"]] = record

    # Check for descriptions
    context_path = brief_path / CONTEXT_DIR
    described_files: set[str] = set()
    if (context_path / "files").exists():
        for md_file in (context_path / "files").glob("*.md"):
            # Convert filename back to path
            described_files.add(md_file.stem.replace("__", "/") + ".py")

    # Categorize files
    analyzed_paths = set(analyzed.keys())
    all_paths = set(str(f.relative_to(base_path)) for f in all_files)

    return {
        "total_files": len(all_paths),
        "analyzed_files": len(analyzed_paths & all_paths),
        "described_files": len(described_files & all_paths),
        "not_analyzed": sorted(all_paths - analyzed_paths),
        "analyzed_not_described": sorted(analyzed_paths - described_files),
    }


def format_coverage(coverage: dict[str, Any]) -> str:
    """Format coverage statistics."""
    total = coverage["total_files"]
    analyzed = coverage["analyzed_files"]
    described = coverage["described_files"]

    analysis_pct = (analyzed / total * 100) if total > 0 else 0
    description_pct = (described / total * 100) if total > 0 else 0

    lines = [
        "Analysis Coverage Report",
        "=" * 40,
        "",
        f"Total Python files: {total}",
        f"Analyzed (structure): {analyzed} ({analysis_pct:.1f}%)",
        f"Described (LLM):     {described} ({description_pct:.1f}%)",
        "",
    ]

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
