"""Specification synthesis from descriptions."""
from pathlib import Path
from ..config import get_brief_path, CONTEXT_DIR, MANIFEST_FILE
from ..storage import read_jsonl


def synthesize_spec(brief_path: Path, base_path: Path) -> str:
    """Synthesize full specification from all descriptions."""
    sections: list[str] = []

    # Project overview
    project_file = brief_path / CONTEXT_DIR / "project.md"
    if project_file.exists():
        sections.append(project_file.read_text())
    else:
        sections.append("# Project Specification\n\n*No project description available.*")

    # Module descriptions
    modules_dir = brief_path / CONTEXT_DIR / "modules"
    if modules_dir.exists():
        module_files = sorted(modules_dir.glob("*.md"))
        if module_files:
            sections.append("\n---\n\n## Modules\n")
            for mf in module_files:
                sections.append(mf.read_text())
                sections.append("\n---\n")

    # File descriptions (organized by module)
    files_dir = brief_path / CONTEXT_DIR / "files"
    if files_dir.exists():
        file_files = sorted(files_dir.glob("*.md"))
        if file_files:
            sections.append("\n---\n\n## File Details\n")
            for ff in file_files:
                sections.append(ff.read_text())
                sections.append("\n---\n")

    # Contracts
    contracts_file = brief_path / CONTEXT_DIR / "contracts.md"
    if contracts_file.exists():
        sections.append("\n---\n\n## Contracts and Invariants\n")
        sections.append(contracts_file.read_text())

    return "\n".join(sections)


def get_spec_stats(brief_path: Path) -> dict[str, int]:
    """Get statistics about the specification."""
    stats = {
        "module_descriptions": 0,
        "file_descriptions": 0,
        "has_project_description": False,
        "has_contracts": False,
    }

    if (brief_path / CONTEXT_DIR / "project.md").exists():
        stats["has_project_description"] = True

    modules_dir = brief_path / CONTEXT_DIR / "modules"
    if modules_dir.exists():
        stats["module_descriptions"] = len(list(modules_dir.glob("*.md")))

    files_dir = brief_path / CONTEXT_DIR / "files"
    if files_dir.exists():
        stats["file_descriptions"] = len(list(files_dir.glob("*.md")))

    if (brief_path / CONTEXT_DIR / "contracts.md").exists():
        stats["has_contracts"] = True

    return stats
