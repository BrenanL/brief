"""Setup wizard for Brief."""
from __future__ import annotations

import os
import json
import stat
import typer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

from ..config import get_brief_path
from ..storage import write_json, read_json


def _detect_api_keys() -> dict[str, bool]:
    """Detect which LLM API keys are available in environment."""
    return {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "google": bool(os.environ.get("GOOGLE_API_KEY")),
    }


def _check_dotenv(base_path: Path) -> bool:
    """Check if a .env file exists."""
    return (base_path / ".env").exists()


def _ensure_gitignore(base_path: Path) -> bool:
    """Add .brief/ and .brief-logs/ to .gitignore if not already present."""
    gitignore = base_path / ".gitignore"
    entries_needed = [".brief/", ".brief-logs/"]

    existing_lines = []
    if gitignore.exists():
        existing_lines = gitignore.read_text().splitlines()

    missing = [e for e in entries_needed if e not in existing_lines]
    if not missing:
        return False

    with open(gitignore, "a") as f:
        if existing_lines and existing_lines[-1].strip():
            f.write("\n")
        if not existing_lines:
            f.write("# Brief context data (local, not committed)\n")
        for entry in missing:
            f.write(f"{entry}\n")

    return True


CLAUDE_MD_BRIEF_SECTION = '''
## Context Management (Brief)

This project uses **Brief** for context management. Brief provides structured context packages
that replace manual file exploration.

### When you need to understand code
```bash
brief context get "what you need to understand"
```

This returns: relevant files, descriptions, function signatures, relationships, and execution paths — all in one call. Use this instead of Read/Grep/Glob for exploration.

### Session Start
```bash
brief status              # See project state
```

### After context compaction
Always run `brief status` first when your context resets.
'''

CLAUDE_MD_TASKS_SECTION = '''
### Task Management
```bash
brief task list           # See what needs doing
brief task start <id>     # Start working on a task
brief task done <id>      # Mark complete
brief resume              # Resume active task with full context
```

After context compaction, run `brief resume` to restore your active task context.
'''


def _write_claude_md_tasks_snippet(base_path: Path, console: Console) -> bool:
    """Append Brief tasks section to CLAUDE.md if not already present."""
    claude_md = base_path / "CLAUDE.md"
    marker = "### Task Management"

    if not claude_md.exists():
        return False

    content = claude_md.read_text()
    if marker in content:
        return False

    with open(claude_md, "a") as f:
        f.write(CLAUDE_MD_TASKS_SECTION)
    console.print("  [green]✓[/green] Added task management section to CLAUDE.md")
    return True


def _write_claude_md_snippet(base_path: Path, console: Console) -> bool:
    """Append Brief section to CLAUDE.md (or create it).

    Returns True if the file was modified.
    """
    claude_md = base_path / "CLAUDE.md"
    marker = "## Context Management (Brief)"

    if claude_md.exists():
        content = claude_md.read_text()
        if marker in content:
            console.print("  [dim]CLAUDE.md already has Brief section — skipped[/dim]")
            return False
        # Append
        with open(claude_md, "a") as f:
            f.write("\n" + CLAUDE_MD_BRIEF_SECTION)
        console.print("  [green]✓[/green] Appended Brief section to CLAUDE.md")
        return True
    else:
        # Create new
        claude_md.write_text(f"# CLAUDE.md\n{CLAUDE_MD_BRIEF_SECTION}")
        console.print("  [green]✓[/green] Created CLAUDE.md with Brief workflow")
        return True


# --- Hook script contents (written to .brief/hooks/) ---

_HOOK_SESSION_START = r'''#!/bin/bash
# Brief SessionStart hook - refresh analysis and prime agent with workflow
cat > /dev/null
# Refresh analysis to catch any files changed since last session
brief analyze refresh > /dev/null 2>&1
cat << 'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[Brief Workflow] This project uses Brief for context management.\n\nWHEN YOU NEED TO UNDERSTAND CODE:\n1. FIRST run: brief context get \"<what you need to understand>\"\n2. Brief returns: file descriptions, signatures, relationships, and related files\n3. THEN use Read only for specific files you need to edit\n\nStart with: brief status"}}
EOF
exit 0
'''

_HOOK_PRE_COMPACT = r'''#!/bin/bash
# Brief PreCompact hook - ensure compaction summary includes resume instructions
cat > /dev/null
cat << 'EOF'
{"systemMessage":"[Compaction Note] Include in your summary: After resuming, run `brief resume` first, then use `brief context get` before exploring code with Read/Grep/Glob."}
EOF
exit 0
'''

_HOOK_USER_PROMPT = r'''#!/bin/bash
# Brief UserPromptSubmit hook - remind agent to use context get first
cat > /dev/null
echo '[Brief] Before exploring code, run: brief context get "<topic>" to get structured context.'
exit 0
'''

_HOOK_PRE_TOOL_USE = r'''#!/bin/bash
# Brief PreToolUse hook - contextual reminder when using Read/Grep/Glob
INPUT=$(cat)
echo "$INPUT" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    skip_dirs = ["/node_modules/", "/.venv/", "/__pycache__/", "/.git/", "/site-packages/"]
    if any(d in file_path for d in skip_dirs):
        sys.exit(0)
    skip_files = ["CLAUDE.md", "settings.json", "config.json", ".env", "pyproject.toml", "package.json"]
    if any(f in file_path for f in skip_files):
        sys.exit(0)
    if "/.brief/" in file_path or "/.brief-logs/" in file_path:
        sys.exit(0)
    code_extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".cpp", ".c", ".h"]
    if any(file_path.endswith(ext) for ext in code_extensions):
        filename = file_path.split("/")[-1] if "/" in file_path else file_path
        output = {"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":f"[Brief Tip] If you are trying to understand how {filename} works or fits into the codebase, consider running `brief context get` first - it provides descriptions, signatures, and related files in one call."}}
        print(json.dumps(output))
except Exception:
    pass
sys.exit(0)
'
exit 0
'''

_HOOK_SCRIPTS = {
    "session-start.sh": _HOOK_SESSION_START,
    "pre-compact.sh": _HOOK_PRE_COMPACT,
    "user-prompt.sh": _HOOK_USER_PROMPT,
    "pre-tool-use.sh": _HOOK_PRE_TOOL_USE,
}

# The hooks config that references .brief/hooks/ via $CLAUDE_PROJECT_DIR
_BRIEF_HOOKS_CONFIG = {
    "SessionStart": [
        {
            "matcher": "startup|resume|compact",
            "hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.brief/hooks/session-start.sh", "timeout": 15}]
        }
    ],
    "PreCompact": [
        {
            "matcher": "auto|manual",
            "hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.brief/hooks/pre-compact.sh", "timeout": 5}]
        }
    ],
    "UserPromptSubmit": [
        {
            "matcher": "",
            "hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.brief/hooks/user-prompt.sh", "timeout": 5}]
        }
    ],
    "PreToolUse": [
        {
            "matcher": "Read|Grep|Glob",
            "hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.brief/hooks/pre-tool-use.sh", "timeout": 5}]
        }
    ],
}

# Permission patterns that allow all brief commands without prompting
_BRIEF_PERMISSIONS = [
    "Bash(brief:*)",
]


def _install_hooks(brief_path: Path) -> int:
    """Write hook scripts to .brief/hooks/. Returns count of scripts written."""
    hooks_dir = brief_path / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    count = 0
    for filename, content in _HOOK_SCRIPTS.items():
        script_path = hooks_dir / filename
        script_path.write_text(content.lstrip("\n"))
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        count += 1
    return count


def _configure_claude_settings(base_path: Path, console: Console) -> None:
    """Write/merge hooks into .claude/settings.json and permissions into settings.local.json."""
    claude_dir = base_path / ".claude"
    claude_dir.mkdir(exist_ok=True)

    # --- settings.json: hooks ---
    settings_path = claude_dir / "settings.json"
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}

    existing_hooks = settings.get("hooks", {})

    # Check if Brief hooks are already installed (look for .brief/hooks/ in any command)
    already_has_brief_hooks = any(
        ".brief/hooks/" in str(hook_entry)
        for event_list in existing_hooks.values()
        for hook_entry in event_list
    )

    if already_has_brief_hooks:
        console.print("  [dim]Hooks already configured in .claude/settings.json — skipped[/dim]")
    else:
        # Merge: for each event type, append Brief's hooks to any existing ones
        for event_name, brief_entries in _BRIEF_HOOKS_CONFIG.items():
            if event_name in existing_hooks:
                existing_hooks[event_name].extend(brief_entries)
            else:
                existing_hooks[event_name] = brief_entries

        settings["hooks"] = existing_hooks
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        console.print("  [green]✓[/green] Configured hooks in .claude/settings.json")

    # --- settings.local.json: permissions ---
    local_path = claude_dir / "settings.local.json"
    local_settings = {}
    if local_path.exists():
        try:
            local_settings = json.loads(local_path.read_text())
        except (json.JSONDecodeError, OSError):
            local_settings = {}

    existing_perms = local_settings.get("permissions", {}).get("allow", [])

    # Check if Brief permissions already present
    brief_perms_present = any("brief" in p for p in existing_perms)

    if brief_perms_present:
        console.print("  [dim]Permissions already configured in .claude/settings.local.json — skipped[/dim]")
    else:
        for perm in _BRIEF_PERMISSIONS:
            if perm not in existing_perms:
                existing_perms.append(perm)

        if "permissions" not in local_settings:
            local_settings["permissions"] = {}
        local_settings["permissions"]["allow"] = existing_perms
        local_path.write_text(json.dumps(local_settings, indent=2) + "\n")
        console.print("  [green]✓[/green] Added brief command permissions to .claude/settings.local.json")


def setup(
    path: Path = typer.Argument(
        Path("."),
        help="Path to set up Brief in"
    ),
    non_interactive: bool = typer.Option(
        False,
        "--default",
        "-d",
        help="Accept all defaults — full automated setup"
    ),
    enable_tasks: bool = typer.Option(
        False,
        "--tasks",
        help="Enable built-in task management (off by default — use if you don't have Beads or similar)"
    ),
) -> None:
    """Interactive setup wizard for Brief.

    Guides you through configuring Brief in your repository.
    With --default (-d), runs full automated setup:
    init, analyze, generate lite descriptions, generate embeddings,
    configure CLAUDE.md, and update .gitignore.

    Example:
        brief setup              # Interactive setup
        brief setup -d           # Full automated setup
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import box
    from ..models import BriefConfig

    console = Console()
    brief_path = get_brief_path(path)

    # Welcome banner
    console.print()
    console.print(Panel(
        "[bold cyan]Brief Setup[/bold cyan]\n"
        "Context infrastructure for AI coding agents",
        box=box.ROUNDED,
        padding=(1, 2)
    ))
    console.print()

    # Check if already initialized
    already_initialized = brief_path.exists()
    if already_initialized:
        console.print("[yellow]Brief is already initialized in this directory.[/yellow]")
        if not non_interactive:
            reconfigure = Confirm.ask("Do you want to reconfigure?", default=False)
            if not reconfigure:
                console.print("Setup cancelled.")
                raise typer.Exit(0)
        console.print()

    # Load the user's project .env (if present) before detecting keys
    env_file = path / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass

    # Detect API keys
    api_keys = _detect_api_keys()
    has_openai = api_keys["openai"]
    has_any_key = any(api_keys.values())
    has_dotenv = _check_dotenv(path)

    # --- Step 1: API Key Detection ---
    console.print("[bold]Step 1: API Keys[/bold]")
    console.print()

    if has_any_key:
        console.print("[green]Detected API keys in your environment:[/green]")
        if api_keys["openai"]:
            console.print("  [green]✓[/green] OpenAI (OPENAI_API_KEY)")
        if api_keys["anthropic"]:
            console.print("  [green]✓[/green] Anthropic (ANTHROPIC_API_KEY)")
        if api_keys["google"]:
            console.print("  [green]✓[/green] Google (GOOGLE_API_KEY)")
    else:
        console.print("[yellow]No API keys detected in environment.[/yellow]")
        if has_dotenv:
            console.print("[dim]Found .env file — keys may be loaded at runtime.[/dim]")
        else:
            console.print()
            console.print("Brief works without API keys (keyword search, AST analysis).")
            console.print("For semantic search, set OPENAI_API_KEY in your environment.")
            console.print("[dim]Brief checks environment variables first, then .env files.[/dim]")

    console.print()

    # --- Step 2: Configuration ---
    console.print("[bold]Step 2: Configuration[/bold]")
    console.print()

    if non_interactive:
        auto_generate = True
        use_gitignore = True
        command_logging = True
    else:
        console.print("Brief can auto-generate descriptions when querying context.")
        console.print("This requires an LLM API key.")
        console.print()
        default_auto = has_any_key or has_dotenv
        auto_generate = Confirm.ask(
            "Enable auto-generation of descriptions?",
            default=default_auto
        )

        console.print()
        use_gitignore = Confirm.ask(
            "Use .gitignore patterns for filtering?",
            default=True
        )

        console.print()
        command_logging = Confirm.ask(
            "Enable command logging to .brief-logs/?",
            default=True
        )

    console.print()

    # --- Step 3: Initialize ---
    console.print("[bold]Step 3: Setting up Brief...[/bold]")
    console.print()

    if not already_initialized:
        from ..config import (
            MANIFEST_FILE,
            RELATIONSHIPS_FILE,
            TASKS_FILE,
            MEMORY_FILE,
            CONTEXT_DIR,
        )
        from ..storage import write_jsonl

        brief_path.mkdir(parents=True, exist_ok=True)
        (brief_path / CONTEXT_DIR).mkdir(exist_ok=True)
        (brief_path / CONTEXT_DIR / "modules").mkdir(exist_ok=True)
        (brief_path / CONTEXT_DIR / "files").mkdir(exist_ok=True)
        (brief_path / CONTEXT_DIR / "paths").mkdir(exist_ok=True)

        write_jsonl(brief_path / MANIFEST_FILE, [])
        write_jsonl(brief_path / RELATIONSHIPS_FILE, [])
        if enable_tasks:
            write_jsonl(brief_path / TASKS_FILE, [])
        write_jsonl(brief_path / MEMORY_FILE, [])

        console.print("  [green]✓[/green] Created .brief/ directory")

    # Save config
    config = BriefConfig(
        use_gitignore=use_gitignore,
        command_logging=command_logging,
        auto_generate_descriptions=auto_generate,
        enable_tasks=enable_tasks,
    )
    write_json(brief_path / "config.json", config.model_dump())
    console.print("  [green]✓[/green] Saved configuration")

    # Gitignore
    if _ensure_gitignore(path):
        console.print("  [green]✓[/green] Added .brief/ and .brief-logs/ to .gitignore")

    # --- Step 4: Analysis ---
    console.print()
    console.print("[bold]Step 4: Analyzing codebase...[/bold]")
    console.print()

    if non_interactive:
        run_analysis = True
    else:
        run_analysis = Confirm.ask(
            "Run codebase analysis now?",
            default=True
        )

    if run_analysis:
        from ..analysis.manifest import ManifestBuilder
        from ..analysis.relationships import RelationshipExtractor
        from ..config import load_exclude_patterns

        current_config = read_json(brief_path / "config.json")
        exclude_patterns = load_exclude_patterns(path, current_config)

        builder = ManifestBuilder(path, exclude_patterns)
        builder.analyze_directory()
        builder.save_manifest(brief_path)

        extractor = RelationshipExtractor(path, exclude_patterns)
        extractor.extract_all()
        extractor.save_relationships(brief_path)

        stats = builder.get_stats()
        file_count = stats['python_files']
        console.print(f"  [green]✓[/green] Analyzed {file_count} Python files")
        console.print(f"  [green]✓[/green] Found {stats['classes']} classes, {stats['module_functions'] + stats['methods']} functions")
    else:
        file_count = 0

    embed_count = 0
    # --- Step 5: Lite Descriptions + Embeddings ---
    if run_analysis and file_count > 0:
        console.print()
        console.print("[bold]Step 5: Generating search index...[/bold]")
        console.print()

        # Always generate lite descriptions (free, fast, no API key)
        from ..generation.lite import generate_all_lite_descriptions

        desc_count = generate_all_lite_descriptions(brief_path)
        console.print(f"  [green]✓[/green] Generated lite descriptions for {desc_count} files")

        # Generate embeddings if OpenAI key available
        embed_count = 0
        if has_openai:
            try:
                from ..retrieval.embeddings import embed_all_descriptions, is_embedding_api_available

                if is_embedding_api_available():
                    console.print("  [dim]Generating embeddings (OpenAI)...[/dim]")
                    embed_count = embed_all_descriptions(brief_path)
                    if embed_count > 0:
                        console.print(f"  [green]✓[/green] Embedded {embed_count} files — semantic search enabled")
                    else:
                        console.print("  [yellow]![/yellow] No files were embedded — keyword search only")
                        console.print("  [dim]Run 'brief context embed' later to retry[/dim]")
                else:
                    console.print("  [yellow]![/yellow] OpenAI API not available — skipping embeddings")
                    console.print("  [dim]Run 'brief context embed' later to enable semantic search[/dim]")
            except Exception as e:
                console.print(f"  [yellow]![/yellow] Embedding failed: {e}")
                console.print("  [dim]Run 'brief context embed' later to retry[/dim]")
        else:
            console.print("  [dim]No OPENAI_API_KEY — skipping embeddings (keyword search still works)[/dim]")
            console.print("  [dim]Set OPENAI_API_KEY and run 'brief context embed' for semantic search[/dim]")

    # --- Step 6: CLAUDE.md ---
    console.print()
    console.print("[bold]Step 6: Agent configuration...[/bold]")
    console.print()

    if non_interactive:
        write_claude = True
    else:
        write_claude = Confirm.ask(
            "Add Brief workflow to CLAUDE.md?",
            default=True
        )

    if write_claude:
        _write_claude_md_snippet(path, console)
        if enable_tasks:
            _write_claude_md_tasks_snippet(path, console)

    # Install hooks and configure permissions
    hook_count = _install_hooks(brief_path)
    console.print(f"  [green]✓[/green] Installed {hook_count} hook scripts to .brief/hooks/")
    _configure_claude_settings(path, console)

    # --- Summary ---
    console.print()

    has_embeddings = run_analysis and file_count > 0 and embed_count > 0
    search_mode = "[green]semantic + keyword[/green]" if has_embeddings else "[yellow]keyword only[/yellow]"

    console.print(Panel(
        "[bold green]Setup Complete![/bold green]\n\n"
        f"Files analyzed: {file_count}\n"
        f"Search mode: {search_mode}\n"
        f"Auto-generate descriptions: {'[green]enabled[/green]' if auto_generate else '[yellow]disabled[/yellow]'}\n"
        f"Command logging: {'[green]enabled[/green]' if command_logging else '[yellow]disabled[/yellow]'}\n"
        f"Task management: {'[green]enabled[/green]' if enable_tasks else '[dim]disabled[/dim] (enable with brief setup --tasks)'}",
        box=box.ROUNDED,
        title="Brief"
    ))

    console.print()
    console.print("[bold]Try it now:[/bold]")
    console.print()
    console.print('  [cyan]brief context get "your query here"[/cyan]')
    console.print()
    console.print("  See what Brief returns for a topic in your codebase.")
    console.print("  This is what your AI agent receives instead of searching files manually.")
    console.print()
    if not has_embeddings:
        console.print("[dim]To enable semantic search: set OPENAI_API_KEY, then run 'brief context embed'[/dim]")
        console.print()
    console.print("[dim]All commands: 'brief --help' | Workflow guide: docs/brief-workflow.md[/dim]")
