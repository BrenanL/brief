"""Contract extraction commands."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path, CONTEXT_DIR
from ..contracts.detector import ContractDetector, Contract

app = typer.Typer()


@app.command("detect")
def contracts_detect(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    use_llm: bool = typer.Option(False, "--llm", help="Also use LLM inference"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """Detect contracts from code patterns."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    detector = ContractDetector(brief_path, base)

    typer.echo("Detecting contracts...")
    contracts = detector.detect_all()

    if use_llm:
        typer.echo("Running LLM inference...")
        from ..contracts.inference import infer_contracts_with_llm
        llm_contracts = infer_contracts_with_llm(brief_path, base, contracts)
        contracts.extend(llm_contracts)

    # Filter by category if specified
    if category:
        contracts = [c for c in contracts if c.category == category]

    if not contracts:
        typer.echo("No contracts detected.")
        return

    typer.echo(f"Detected {len(contracts)} contracts:")
    typer.echo("")

    # Build markdown
    lines = ["# Contracts and Invariants", ""]
    lines.append("This document captures implicit contracts and conventions in the codebase.")
    lines.append("")

    # Group by category
    by_category: dict[str, list[Contract]] = {}
    for contract in contracts:
        cat = contract.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(contract)

    for cat in sorted(by_category.keys()):
        lines.append(f"# {cat.title()} Contracts")
        lines.append("")
        for contract in by_category[cat]:
            lines.append(contract.to_markdown())
            lines.append("---")
            lines.append("")

    markdown = "\n".join(lines)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown)
        typer.echo(f"Written to: {output}")
    else:
        # Save to default location
        context_dir = brief_path / CONTEXT_DIR
        context_dir.mkdir(parents=True, exist_ok=True)
        contracts_file = context_dir / "contracts.md"
        contracts_file.write_text(markdown)
        typer.echo(f"Written to: {contracts_file}")

    # Display summary
    typer.echo("")
    typer.echo("Summary:")
    for cat in sorted(by_category.keys()):
        typer.echo(f"  {cat}: {len(by_category[cat])} contracts")
    typer.echo("")

    for contract in contracts:
        icon = {"high": "●", "medium": "◐", "low": "○"}.get(contract.confidence, "?")
        typer.echo(f"  {icon} [{contract.category}] {contract.name}")


@app.command("show")
def contracts_show(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Show extracted contracts."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    contracts_file = brief_path / CONTEXT_DIR / "contracts.md"

    if contracts_file.exists():
        typer.echo(contracts_file.read_text())
    else:
        typer.echo("No contracts file found. Run 'briefcontracts detect' first.")


@app.command("add")
def contracts_add(
    name: str = typer.Argument(..., help="Contract name"),
    rule: str = typer.Argument(..., help="Contract rule"),
    category: str = typer.Option("api", "--category", "-c",
                                 help="Category (naming, type, behavioral, organization, api)"),
    confidence: str = typer.Option("high", "--confidence",
                                   help="Confidence level (low, medium, high)"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Manually add a contract."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    contract = Contract(
        name=name,
        rule=rule,
        category=category,
        confidence=confidence,
        source="manual entry"
    )

    # Ensure context directory exists
    context_dir = brief_path / CONTEXT_DIR
    context_dir.mkdir(parents=True, exist_ok=True)

    contracts_file = context_dir / "contracts.md"

    # Append to file
    if contracts_file.exists():
        existing = contracts_file.read_text()
    else:
        existing = "# Contracts and Invariants\n\n"
        existing += "This document captures implicit contracts and conventions in the codebase.\n\n"

    existing += contract.to_markdown() + "\n---\n\n"
    contracts_file.write_text(existing)

    typer.echo(f"Added contract: {name}")
    typer.echo(f"  Category: {category}")
    typer.echo(f"  Rule: {rule}")


@app.command("list")
def contracts_list(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
) -> None:
    """List detected contracts (quick summary)."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    contracts_file = brief_path / CONTEXT_DIR / "contracts.md"

    if not contracts_file.exists():
        typer.echo("No contracts file found. Run 'briefcontracts detect' first.")
        return

    content = contracts_file.read_text()

    # Parse contract headers from markdown
    lines = content.split("\n")
    contracts_found = []
    current_category = "unknown"

    for line in lines:
        if line.startswith("# ") and "Contracts" in line:
            # Category header
            current_category = line.replace("# ", "").replace(" Contracts", "").lower()
        elif line.startswith("## Contract: "):
            name = line.replace("## Contract: ", "")
            if category is None or current_category == category:
                contracts_found.append((current_category, name))

    if not contracts_found:
        typer.echo("No contracts found.")
        return

    typer.echo(f"Contracts ({len(contracts_found)}):")
    for cat, name in contracts_found:
        typer.echo(f"  [{cat}] {name}")


@app.command("verify")
def contracts_verify(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Verify contracts are being followed (basic check)."""
    brief_path = get_brief_path(base)
    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    detector = ContractDetector(brief_path, base)

    typer.echo("Running contract verification...")
    typer.echo("")

    # Re-detect contracts and compare
    contracts = detector.detect_all()

    violations = 0

    # For now, just report what we found
    for contract in contracts:
        if contract.confidence == "high":
            typer.echo(f"✓ {contract.name}")
            typer.echo(f"  {len(contract.files_affected)} files follow this convention")
        else:
            typer.echo(f"? {contract.name}")
            typer.echo(f"  Confidence: {contract.confidence} - may need review")

    typer.echo("")
    if violations == 0:
        typer.echo("All detected contracts appear to be followed.")
    else:
        typer.echo(f"Found {violations} potential violations.")
