"""Context retrieval commands for Brief."""
import typer
from pathlib import Path
from typing import Optional
from ..config import get_brief_path, MANIFEST_FILE
from ..storage import read_json, read_jsonl
from ..retrieval.context import (
    build_context_for_file,
    build_context_for_query,
    get_file_context,
)
from ..retrieval.search import hybrid_search, keyword_search, semantic_search
from ..retrieval.embeddings import is_embedding_api_available
from ..tasks.manager import TaskManager

app = typer.Typer()


def _check_manifest_has_files(brief_path: Path) -> bool:
    """Check if the manifest has any file records.

    Args:
        brief_path: Path to .brief directory

    Returns:
        True if manifest has file records, False otherwise
    """
    manifest_file = brief_path / MANIFEST_FILE
    if not manifest_file.exists():
        return False

    for record in read_jsonl(manifest_file):
        if record.get("type") == "file":
            return True
    return False


def _get_auto_generate_default(brief_path: Path) -> bool:
    """Get the default auto-generate setting from config.

    Args:
        brief_path: Path to .brief directory

    Returns:
        True if auto-generation should be enabled by default
    """
    config_file = brief_path / "config.json"
    if config_file.exists():
        try:
            config = read_json(config_file)
            return config.get("auto_generate_descriptions", True)
        except Exception:
            pass
    return True  # Default to enabled


@app.command("get")
def context_get(
    query: Optional[str] = typer.Argument(None, help="Task description or file path"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Task ID to get context for"),
    file_mode: bool = typer.Option(False, "--file", "-f", help="Treat query as file path"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output to file"),
    patterns: bool = typer.Option(True, "--patterns/--no-patterns", help="Include memory patterns"),
    contracts: bool = typer.Option(True, "--contracts/--no-contracts", help="Include contracts"),
    paths: bool = typer.Option(True, "--paths/--no-paths", help="Include execution paths"),
    auto_generate: Optional[bool] = typer.Option(None, "--auto-generate", "-g", help="Generate descriptions on-demand (default: from config)"),
    no_auto_generate: bool = typer.Option(False, "--no-auto-generate", "-G", help="Disable auto-generation even if config enables it"),
    show_signatures: bool = typer.Option(False, "--show-signatures", "-s", help="Force showing signatures even when descriptions exist"),
    compact: bool = typer.Option(False, "--compact", "-c", help="Show compact summary (file list and stats only)"),
    tokens: bool = typer.Option(False, "--tokens", help="Show estimated token count"),
) -> None:
    """Get relevant context for a task or file.

    Returns a unified context package including:
    - Primary files matching your query
    - Related files (imports, imported-by)
    - Relevant memory patterns
    - Relevant contracts
    - Relevant execution paths

    Use --task to get context for a specific task ID:
        brief context get --task ag-1234

    Or provide a query directly:
        brief context get "refactoring the table command"

    Use --compact for a quick summary without full descriptions:
        brief context get "auth" --compact

    Auto-generation is enabled by default (configurable in config.json).
    Use -G/--no-auto-generate to disable:
        brief context get "task management" -G
    """
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    # Check if manifest has any files
    if not _check_manifest_has_files(brief_path):
        typer.echo("Error: No files in manifest. Run 'brief analyze all' first.", err=True)
        typer.echo("", err=True)
        typer.echo("Quick start:", err=True)
        typer.echo("  brief analyze all    # Analyze your codebase", err=True)
        typer.echo("  brief describe batch # Generate descriptions (optional)", err=True)
        typer.echo("  brief context get \"your query\"", err=True)
        raise typer.Exit(1)

    # Determine auto-generate setting
    # Priority: -G flag > -g flag > config > default (True)
    if no_auto_generate:
        should_auto_generate = False
    elif auto_generate is not None:
        should_auto_generate = auto_generate
    else:
        should_auto_generate = _get_auto_generate_default(brief_path)

    # Handle task-based context
    if task:
        task_manager = TaskManager(brief_path)
        task_record = task_manager.get_task(task)
        if not task_record:
            typer.echo(f"Error: Task '{task}' not found.", err=True)
            raise typer.Exit(1)

        # Build query from task title and description
        query = task_record.title
        if task_record.description:
            query = f"{task_record.title}: {task_record.description}"

        typer.echo(f"Getting context for task: {task_record.id} - {task_record.title}")
        typer.echo("")

    # Ensure we have a query
    if not query:
        typer.echo("Error: Must provide either a query or --task option.", err=True)
        raise typer.Exit(1)

    if file_mode or query.endswith(".py"):
        # File mode
        package = build_context_for_file(
            brief_path, query, base_path=base,
            auto_generate_descriptions=should_auto_generate
        )
    else:
        # Query mode with search
        def search_func(q: str):
            return hybrid_search(brief_path, q)

        package = build_context_for_query(
            brief_path,
            query,
            search_func,
            base_path=base,
            include_contracts=contracts,
            include_paths=paths,
            include_patterns=patterns,
            auto_generate_descriptions=should_auto_generate
        )

    markdown = package.to_markdown(force_signatures=show_signatures, compact=compact)

    if output:
        output.write_text(markdown)
        typer.echo(f"Context written to {output}")
    else:
        typer.echo(markdown)

    # Show token estimate if requested
    if tokens:
        estimates = package.estimate_tokens()
        typer.echo("")
        typer.echo("Token Estimates (approximate):")
        typer.echo(f"  Primary files:   ~{estimates['primary_files']:,}")
        typer.echo(f"  Related files:   ~{estimates['related_files']:,}")
        typer.echo(f"  Patterns:        ~{estimates['patterns']:,}")
        typer.echo(f"  Execution paths: ~{estimates['execution_paths']:,}")
        typer.echo(f"  Contracts:       ~{estimates['contracts']:,}")
        typer.echo(f"  ─────────────────────")
        typer.echo(f"  Content subtotal: ~{estimates['content_subtotal']:,}")
        typer.echo(f"  Formatted output: ~{estimates['formatted_output']:,}")
        typer.echo(f"  ─────────────────────")
        typer.echo(f"  Total (output):   ~{estimates['total']:,} tokens")


@app.command("related")
def context_related(
    file_path: str = typer.Argument(..., help="File to find related files for"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    depth: int = typer.Option(1, "--depth", "-d", help="Relationship depth to explore"),
) -> None:
    """Find files related to a given file."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    context = get_file_context(brief_path, file_path)

    typer.echo(f"Files related to: {file_path}")
    typer.echo("")

    if context["imports"]:
        typer.echo("IMPORTS (this file depends on):")
        for imp in context["imports"]:
            typer.echo(f"  - {imp}")
    else:
        typer.echo("IMPORTS: (none)")

    typer.echo("")

    if context["imported_by"]:
        typer.echo("IMPORTED BY (files that depend on this):")
        for imp in context["imported_by"]:
            typer.echo(f"  - {imp}")
    else:
        typer.echo("IMPORTED BY: (none)")

    # If depth > 1, expand
    if depth > 1:
        typer.echo("")
        typer.echo(f"EXTENDED RELATIONSHIPS (depth {depth}):")
        seen = {file_path}
        to_expand = list(context["imports"]) + list(context["imported_by"])

        for _ in range(depth - 1):
            next_expand: list[str] = []
            for path in to_expand:
                if path in seen:
                    continue
                seen.add(path)
                ctx = get_file_context(brief_path, path)
                for imp in ctx["imports"] + ctx["imported_by"]:
                    if imp not in seen:
                        next_expand.append(imp)
                        typer.echo(f"  {path} -> {imp}")
            to_expand = next_expand


@app.command("search")
def context_search(
    query: str = typer.Argument(..., help="Search query"),
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
    mode: str = typer.Option("hybrid", "--mode", "-m", help="Search mode: semantic, keyword, hybrid"),
) -> None:
    """Search the codebase semantically."""
    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized. Run 'brief init' first.", err=True)
        raise typer.Exit(1)

    if not _check_manifest_has_files(brief_path):
        typer.echo("Error: No files in manifest. Run 'brief analyze all' first.", err=True)
        raise typer.Exit(1)

    results: list[dict] = []

    if mode == "semantic":
        if not is_embedding_api_available():
            typer.echo("Error: Semantic search requires OPENAI_API_KEY in .env", err=True)
            raise typer.Exit(1)
        results = semantic_search(brief_path, query, limit)
    elif mode == "keyword":
        results = keyword_search(brief_path, query, limit)
    else:
        results = hybrid_search(brief_path, query, limit)

    typer.echo(f"Search results for: {query}")
    typer.echo(f"Mode: {mode}")
    typer.echo("-" * 40)

    if not results:
        typer.echo("No results found.")
        return

    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        typer.echo(f"{i}. {result['path']} (score: {score:.3f})")


@app.command("embed")
def context_embed(
    base: Path = typer.Option(Path("."), "--base", "-b", help="Base path"),
) -> None:
    """Generate embeddings for semantic search.

    Embeddings enable semantic similarity search over file descriptions.
    This converts your LLM-generated descriptions into vector embeddings
    that can be searched using natural language queries.

    Prerequisites:
    1. Run 'brief describe batch' first to generate descriptions
    2. Set OPENAI_API_KEY in .env (embeddings use OpenAI's API)

    After running this command, you can use:
        brief context search "query" --mode semantic
        brief context search "query" --mode hybrid

    Example:
        brief context embed    # Generate embeddings for all descriptions
    """
    from ..retrieval.embeddings import embed_all_descriptions
    from ..config import CONTEXT_DIR

    brief_path = get_brief_path(base)

    if not brief_path.exists():
        typer.echo("Error: Brief not initialized.", err=True)
        raise typer.Exit(1)

    # Check if descriptions exist
    files_dir = brief_path / CONTEXT_DIR / "files"
    if not files_dir.exists() or not any(files_dir.glob("*.md")):
        typer.echo("No descriptions found. Run 'brief describe batch' first.", err=True)
        raise typer.Exit(1)

    if not is_embedding_api_available():
        typer.echo("Error: Embedding requires OPENAI_API_KEY in .env", err=True)
        typer.echo("", err=True)
        typer.echo("To set up:", err=True)
        typer.echo("  1. Get an API key from platform.openai.com", err=True)
        typer.echo("  2. Add to .env: OPENAI_API_KEY=sk-...", err=True)
        raise typer.Exit(1)

    desc_count = len(list(files_dir.glob("*.md")))
    typer.echo(f"Generating embeddings for {desc_count} descriptions...")
    typer.echo("(This may take a moment)")

    count = embed_all_descriptions(brief_path)

    typer.echo("")
    typer.echo(f"Embedded {count} file descriptions.")
    typer.echo("")
    typer.echo("You can now use semantic search:")
    typer.echo("  brief context search \"your query\" --mode semantic")
