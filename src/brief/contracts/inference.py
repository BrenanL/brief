"""LLM-assisted contract inference."""
from pathlib import Path
from typing import Optional
from .detector import Contract
from ..config import load_env, CONTEXT_DIR, MANIFEST_FILE
from ..storage import read_jsonl

load_env()


def infer_contracts_with_llm(
    brief_path: Path,
    base_path: Path,
    existing_contracts: list[Contract]
) -> list[Contract]:
    """Use LLM to infer additional contracts.

    Args:
        brief_path: Path to .brief directory
        base_path: Project base path
        existing_contracts: Already detected contracts

    Returns:
        List of inferred contracts from LLM
    """
    try:
        from ..baml_client.sync_client import b
    except ImportError:
        print("BAML client not available. Run 'baml-cli generate' first.")
        return []

    # Gather code samples
    code_samples = []
    manifest = list(read_jsonl(brief_path / MANIFEST_FILE))

    # Sample some files with interesting patterns
    files = [r for r in manifest if r.get("type") == "file"][:5]
    for f in files:
        file_path = base_path / f.get("path", "")
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")[:2000]  # Truncate
                code_samples.append(f"# {f.get('path', '')}\n{content}")
            except Exception:
                continue

    # Gather file descriptions
    file_descriptions = []
    files_dir = brief_path / CONTEXT_DIR / "files"
    if files_dir.exists():
        for md_file in list(files_dir.glob("*.md"))[:10]:
            try:
                content = md_file.read_text(encoding="utf-8")
                # Extract first paragraph
                para = content.split("\n\n")[0] if "\n\n" in content else content[:200]
                file_descriptions.append(para)
            except Exception:
                continue

    # Format existing contracts
    existing = [f"{c.name}: {c.rule}" for c in existing_contracts]

    try:
        result = b.InferContracts(
            code_samples=code_samples,
            file_descriptions=file_descriptions,
            existing_contracts=existing
        )

        new_contracts = []
        for item in result.contracts:
            new_contracts.append(Contract(
                name=item.name,
                rule=item.rule,
                category=item.category,
                confidence=item.confidence,
                source="LLM inference"
            ))

        return new_contracts

    except Exception as e:
        print(f"LLM inference failed: {e}")
        return []
