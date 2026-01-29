#!/usr/bin/env python3
"""
Brief A/B Testing Framework v3

Uses the Claude Code orchestrator to run headless tests measuring Brief
utilization across different configurations and testing dimensions.

See PERFORMANCE_TESTING_PLAN.md for full documentation.
See ORCHESTRATOR_DESIGN.md for orchestrator architecture.

Usage:
    # List available options
    python performance-testing/run_test.py list-configs
    python performance-testing/run_test.py list-dimensions

    # Run all tests (7 configs x 9 dimensions = 63 tests)
    python performance-testing/run_test.py run --configs all --dimensions all

    # Run specific configs/dimensions
    python performance-testing/run_test.py run --configs baseline-pretool baseline-full-hooks --dimensions feature-addition

    # Run with custom parallelism
    python performance-testing/run_test.py run --configs all --dimensions all --workers 3
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

# Resolve imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from orchestrator import ClaudeOrchestrator, ClaudeJob

PROJECT_ROOT = SCRIPT_DIR.parent

# =============================================================================
# HOOK DEFINITIONS
# =============================================================================

PRETOOL_HOOK = {
    "PreToolUse": [{
        "matcher": "Read|Grep|Glob",
        "hooks": [{
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/pre-tool-use.sh",
            "timeout": 5
        }]
    }]
}

USERPROMPT_HOOK = {
    "UserPromptSubmit": [{
        "matcher": "",
        "hooks": [{
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/user-prompt.sh",
            "timeout": 5
        }]
    }]
}

SESSIONSTART_HOOK = {
    "SessionStart": [{
        "matcher": "startup|resume|compact",
        "hooks": [{
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/session-start.sh",
            "timeout": 5
        }]
    }]
}

PRECOMPACT_HOOK = {
    "PreCompact": [{
        "matcher": "auto|manual",
        "hooks": [{
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/pre-compact.sh",
            "timeout": 5
        }]
    }]
}

FULL_HOOKS = {
    **SESSIONSTART_HOOK,
    **USERPROMPT_HOOK,
    **PRETOOL_HOOK,
    **PRECOMPACT_HOOK,
}

# =============================================================================
# TEST CONFIGURATIONS (7 configs)
# =============================================================================

CONFIGS = {
    "null-no-hooks": {
        "description": "Null CLAUDE.md, no hooks (true control)",
        "hooks": {},
        "claude_md": "performance-testing/test-files/claude-md-null.md"
    },
    "null-pretool": {
        "description": "Null CLAUDE.md, PreToolUse hook only",
        "hooks": PRETOOL_HOOK,
        "claude_md": "performance-testing/test-files/claude-md-null.md"
    },
    "null-userprompt": {
        "description": "Null CLAUDE.md, UserPromptSubmit hook only",
        "hooks": USERPROMPT_HOOK,
        "claude_md": "performance-testing/test-files/claude-md-null.md"
    },
    "null-full-hooks": {
        "description": "Null CLAUDE.md, full hook suite (4 hooks)",
        "hooks": FULL_HOOKS,
        "claude_md": "performance-testing/test-files/claude-md-null.md"
    },
    "baseline-no-hooks": {
        "description": "Baseline CLAUDE.md, no hooks (isolate docs impact)",
        "hooks": {},
        "claude_md": "performance-testing/test-files/claude-md-baseline.md"
    },
    "baseline-pretool": {
        "description": "Baseline CLAUDE.md, PreToolUse hook only",
        "hooks": PRETOOL_HOOK,
        "claude_md": "performance-testing/test-files/claude-md-baseline.md"
    },
    "baseline-full-hooks": {
        "description": "Baseline CLAUDE.md, full hook suite (maximum guidance)",
        "hooks": FULL_HOOKS,
        "claude_md": "performance-testing/test-files/claude-md-baseline.md"
    },
}

# =============================================================================
# TEST DIMENSIONS (9 dimensions for Phase 1)
# =============================================================================

@dataclass
class TestDimension:
    """Defines a test dimension with its prompt and optional setup."""
    id: str
    name: str
    description: str
    prompt: str
    setup_type: str = "none"  # "none", "multi-task", "resume"
    setup_tasks: list = field(default_factory=list)


DIMENSIONS = {
    "feature-addition": TestDimension(
        id="feature-addition",
        name="Feature Addition (Greenfield)",
        description="Task where agent must figure out WHERE to add code",
        prompt=("Add a 'brief logs archive' command that moves old log entries to an archive file. "
                "It should take a --days flag to specify how many days of logs to keep active (default 30). "
                "The archived logs should go to .brief-logs/archive/ with a timestamp in the filename.")
    ),

    "multi-task": TestDimension(
        id="multi-task",
        name="Multi-Task Sequential",
        description="Queue 3 tasks, tell agent to complete all",
        prompt="You have Brief tasks queued. Run `brief task list` to see them, then complete all pending tasks in order.",
        setup_type="multi-task",
        setup_tasks=[
            {"title": "Add --json flag to brief status command", "desc": "Add a --json flag that outputs the status as JSON instead of the table format"},
            {"title": "Add brief task priority command", "desc": "Add a command to set task priorities: brief task priority <id> <priority>"},
            {"title": "Add brief context stats command", "desc": "Add a command that shows context coverage statistics: files described, relationships mapped, etc."},
        ]
    ),

    "resume": TestDimension(
        id="resume",
        name="Resume Behavior",
        description="Set up partial state, prompt with 'resume'",
        prompt="resume",
        setup_type="resume",
        setup_tasks=[
            {"title": "Add input validation to brief task create", "desc": "Add validation to ensure task titles are not empty and descriptions are under 1000 characters", "status": "in_progress"},
        ]
    ),

    "feature-extension": TestDimension(
        id="feature-extension",
        name="Feature Extension",
        description="Building on existing functionality",
        prompt=("Extend the brief describe command to support a --format flag that can output "
                "descriptions as JSON instead of markdown. The JSON should include all the same fields "
                "(purpose, contents, role, dependencies, exports).")
    ),

    "bug-investigation": TestDimension(
        id="bug-investigation",
        name="Bug Investigation",
        description="Agent must trace through code to find root cause",
        prompt=("The brief context get command sometimes returns empty results even when relevant "
                "files exist. Investigate why this might happen and identify potential root causes. "
                "Don't fix it yet, just report your findings with specific file locations and code paths.")
    ),

    "cross-cutting": TestDimension(
        id="cross-cutting",
        name="Cross-Cutting Concern",
        description="Add X to all Y - requires finding all locations",
        prompt=("Add input validation to all Brief CLI commands that accept file paths as arguments. "
                "Validate that: 1) paths exist, 2) paths are within the project directory (no path traversal), "
                "3) paths point to files not directories (where appropriate). Use a shared validation function.")
    ),

    "integration": TestDimension(
        id="integration",
        name="Integration Task",
        description="Connect X to Y - requires understanding two systems",
        prompt=("Make the task system integrate with the logging system so that task state changes "
                "(create, start, done, archive) are automatically recorded in the command log with timestamps. "
                "The log entries should include the task ID, action, and relevant metadata.")
    ),

    "pattern-following": TestDimension(
        id="pattern-following",
        name="Pattern Following",
        description="Follow existing pattern when implementing Y",
        prompt=("Add a new 'brief contracts export' command following the same pattern used by "
                "other export/output commands in the codebase. It should export all detected contracts "
                "to a JSON file, with options for filtering by file or contract type.")
    ),

    "documentation": TestDimension(
        id="documentation",
        name="Documentation/Explanation",
        description="Document how X works",
        prompt=("Document how the context retrieval system works. Create a markdown file at "
                "docs/CONTEXT_RETRIEVAL.md that explains the flow from a 'brief context get' call through "
                "to the returned context package, including all intermediate steps and data transformations.")
    ),
}

# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

def make_setup_fn(config_name: str, dimension: TestDimension):
    """Create a setup function for a specific config/dimension combo."""

    def setup(work_dir: Path):
        # Copy .brief/ context data (descriptions, analysis) but not tasks or embeddings
        brief_src = PROJECT_ROOT / ".brief"
        brief_dst = work_dir / ".brief"
        if brief_src.exists():
            if brief_dst.exists():
                shutil.rmtree(brief_dst)
            shutil.copytree(
                brief_src,
                brief_dst,
                ignore=shutil.ignore_patterns("tasks.jsonl", "*.db"),
            )
            # Create empty tasks.jsonl
            (brief_dst / "tasks.jsonl").write_text("")

        # Copy hook scripts if config uses hooks
        config = CONFIGS[config_name]
        if config["hooks"]:
            hooks_src = PROJECT_ROOT / "scripts" / "hooks"
            hooks_dst = work_dir / "scripts" / "hooks"
            if hooks_src.exists():
                hooks_dst.mkdir(parents=True, exist_ok=True)
                for script in hooks_src.glob("*.sh"):
                    shutil.copy2(script, hooks_dst / script.name)

        # Dimension-specific setup
        if dimension.setup_type == "multi-task":
            _write_tasks(work_dir, dimension.setup_tasks)
        elif dimension.setup_type == "resume":
            _write_resume_scenario(work_dir, dimension.setup_tasks)

    return setup


def _write_tasks(work_dir: Path, tasks: list):
    """Pre-create Brief tasks in the work directory."""
    tasks_file = work_dir / ".brief" / "tasks.jsonl"
    tasks_file.parent.mkdir(parents=True, exist_ok=True)

    with tasks_file.open("w") as f:
        for i, task in enumerate(tasks):
            task_data = {
                "id": f"test-{i+1:04d}",
                "title": task["title"],
                "description": task.get("desc", ""),
                "status": task.get("status", "pending"),
                "priority": task.get("priority", 50 - i),
                "created_at": datetime.now().isoformat(),
                "tags": [],
                "depends_on": [],
            }
            f.write(json.dumps(task_data) + "\n")


def _write_resume_scenario(work_dir: Path, tasks: list):
    """Set up a resume scenario with an active task."""
    tasks_file = work_dir / ".brief" / "tasks.jsonl"
    tasks_file.parent.mkdir(parents=True, exist_ok=True)

    active_task_id = None
    with tasks_file.open("w") as f:
        for i, task in enumerate(tasks):
            task_id = f"test-{i+1:04d}"
            task_data = {
                "id": task_id,
                "title": task["title"],
                "description": task.get("desc", ""),
                "status": task.get("status", "pending"),
                "priority": task.get("priority", 50),
                "created_at": datetime.now().isoformat(),
                "tags": [],
                "depends_on": [],
            }
            if task.get("status") == "in_progress":
                active_task_id = task_id
                task_data["started_at"] = datetime.now().isoformat()
            f.write(json.dumps(task_data) + "\n")

    if active_task_id:
        active_file = work_dir / ".brief" / "active_task"
        active_file.write_text(active_task_id)


# =============================================================================
# JOB GENERATION
# =============================================================================

def make_jobs(
    configs: list[str],
    dimensions: list[str],
    max_turns: int = 25,
    max_budget: float = 2.0,
    timeout: int = 600,
) -> list[ClaudeJob]:
    """Generate ClaudeJob instances for each config x dimension combo."""
    jobs = []
    for config_name in configs:
        config = CONFIGS[config_name]
        for dim_id in dimensions:
            dimension = DIMENSIONS[dim_id]

            job = ClaudeJob(
                job_id=f"{config_name}__{dim_id}",
                prompt=dimension.prompt,
                repo_path=str(PROJECT_ROOT),
                repo_ref="HEAD",
                max_turns=max_turns,
                max_budget=max_budget,
                timeout=timeout,
                claude_md_source=str(PROJECT_ROOT / config["claude_md"]),
                settings_json={"hooks": config["hooks"]},
                setup_fn=make_setup_fn(config_name, dimension),
                metadata={
                    "config_name": config_name,
                    "config_description": config["description"],
                    "dimension_id": dim_id,
                    "dimension_name": dimension.name,
                    "dimension_description": dimension.description,
                    "prompt": dimension.prompt,
                },
            )
            jobs.append(job)

    return jobs


# =============================================================================
# MAIN CLI
# =============================================================================

def load_config() -> dict:
    """Load orchestrator config from config.json."""
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with config_path.open() as f:
            return json.load(f)
    return {
        "temp_dir": "/home/user/tmp/brief-performance-testing",
        "manifest_path": "performance-testing/results/manifest.jsonl",
        "max_workers": 2,
        "defaults": {"max_turns": 25, "max_budget": 2.0, "timeout": 600},
    }


def resolve_configs(config_args: list[str]) -> list[str]:
    """Resolve config arguments to a list of config names."""
    if config_args == ["all"]:
        return list(CONFIGS.keys())
    for c in config_args:
        if c not in CONFIGS:
            print(f"Error: unknown config '{c}'", file=sys.stderr)
            print(f"Available: {', '.join(CONFIGS.keys())}", file=sys.stderr)
            sys.exit(1)
    return config_args


def resolve_dimensions(dim_args: list[str]) -> list[str]:
    """Resolve dimension arguments to a list of dimension IDs."""
    if dim_args == ["all"]:
        return list(DIMENSIONS.keys())
    for d in dim_args:
        if d not in DIMENSIONS:
            print(f"Error: unknown dimension '{d}'", file=sys.stderr)
            print(f"Available: {', '.join(DIMENSIONS.keys())}", file=sys.stderr)
            sys.exit(1)
    return dim_args


def cmd_list_configs():
    """List available test configurations."""
    print("Available configurations:\n")
    for name, config in CONFIGS.items():
        hooks_count = len(config["hooks"]) if config["hooks"] else 0
        print(f"  {name}")
        print(f"    {config['description']}")
        print(f"    Hooks: {hooks_count}")
        print(f"    CLAUDE.md: {config['claude_md']}")
        print()


def cmd_list_dimensions():
    """List test dimensions."""
    print("Test dimensions:\n")
    for dim_id, dim in DIMENSIONS.items():
        print(f"  {dim_id}")
        print(f"    {dim.name}")
        print(f"    {dim.description}")
        print(f"    Setup: {dim.setup_type}")
        print()


def cmd_run(args):
    """Run tests using the orchestrator."""
    config = load_config()
    defaults = config.get("defaults", {})

    configs = resolve_configs(args.configs)
    dimensions = resolve_dimensions(args.dimensions)

    jobs = make_jobs(
        configs=configs,
        dimensions=dimensions,
        max_turns=args.max_turns or defaults.get("max_turns", 25),
        max_budget=args.max_budget or defaults.get("max_budget", 2.0),
        timeout=args.timeout or defaults.get("timeout", 600),
    )

    print(f"Queuing {len(jobs)} tests ({len(configs)} configs x {len(dimensions)} dimensions)")
    print(f"Workers: {args.workers or config.get('max_workers', 2)}")
    print()

    manifest_path = PROJECT_ROOT / config["manifest_path"]
    orch = ClaudeOrchestrator(
        temp_dir=config["temp_dir"],
        manifest_path=manifest_path,
        max_workers=args.workers or config.get("max_workers", 2),
    )

    orch.add_jobs(jobs)
    entries = orch.run()

    # Print summary
    print(f"\n{'='*70}")
    print("RUN COMPLETE")
    print(f"{'='*70}")
    completed = [e for e in entries if e.status == "completed"]
    failed = [e for e in entries if e.status in ("failed", "killed", "error")]
    print(f"Completed: {len(completed)}")
    print(f"Failed: {len(failed)}")
    print(f"Manifest: {manifest_path}")
    print(f"\nRun analysis with: python performance-testing/analyze.py {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Brief A/B Testing Framework v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-configs
    subparsers.add_parser("list-configs", help="List available configurations")

    # list-dimensions
    subparsers.add_parser("list-dimensions", help="List test dimensions")

    # run
    run_parser = subparsers.add_parser("run", help="Run tests")
    run_parser.add_argument("--configs", nargs="+", default=["all"], help="Configs to test (or 'all')")
    run_parser.add_argument("--dimensions", nargs="+", default=["all"], help="Dimensions to test (or 'all')")
    run_parser.add_argument("--workers", type=int, help="Max parallel workers")
    run_parser.add_argument("--max-turns", type=int, help="Max agentic turns per test")
    run_parser.add_argument("--max-budget", type=float, help="Max budget in USD per test")
    run_parser.add_argument("--timeout", type=int, help="Timeout in seconds per test")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list-configs":
        cmd_list_configs()
    elif args.command == "list-dimensions":
        cmd_list_dimensions()
    elif args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
