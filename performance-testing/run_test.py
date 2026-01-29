#!/usr/bin/env python3
"""
Brief A/B Testing Framework v2

Runs Claude Code in headless mode with different configurations and measures
Brief utilization metrics. Tests run in isolated copies of the project.

See PERFORMANCE_TESTING_PLAN.md for full documentation.

Usage:
    # List available options
    python performance-testing/run_test.py --list-configs
    python performance-testing/run_test.py --list-dimensions

    # Single test
    python performance-testing/run_test.py --config baseline-pretool --dimension feature-addition

    # Compare configurations
    python performance-testing/run_test.py --compare null-no-hooks baseline-pretool --dimension feature-addition

    # Run all dimensions for a config
    python performance-testing/run_test.py --config baseline-full-hooks --dimension all

    # Run all configs for all dimensions (full test suite)
    python performance-testing/run_test.py --compare all --dimension all
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable

# Script location and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Test output directory
TEST_OUTPUT_DIR = PROJECT_ROOT / ".brief-logs" / "test-runs"
RESULTS_DIR = PROJECT_ROOT / "performance-testing" / "results"

# =============================================================================
# HOOK DEFINITIONS
# =============================================================================

# PreToolUse hook (fires before Read/Grep/Glob on code files)
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

# UserPromptSubmit hook (fires on every user prompt)
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

# SessionStart hook (fires on startup/resume/compact)
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

# PreCompact hook (fires before context compaction)
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

# Full hook suite (all 4 hooks)
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
    # Null CLAUDE.md variants (no Brief references)
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

    # Baseline CLAUDE.md variants (original Brief instructions)
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
        prompt="""Add a 'brief logs archive' command that moves old log entries to an archive file.
It should take a --days flag to specify how many days of logs to keep active (default 30).
The archived logs should go to .brief-logs/archive/ with a timestamp in the filename."""
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
        prompt="""Extend the brief describe command to support a --format flag that can output
descriptions as JSON instead of markdown. The JSON should include all the same fields
(purpose, contents, role, dependencies, exports)."""
    ),

    "bug-investigation": TestDimension(
        id="bug-investigation",
        name="Bug Investigation",
        description="Agent must trace through code to find root cause",
        prompt="""The brief context get command sometimes returns empty results even when relevant
files exist. Investigate why this might happen and identify potential root causes.
Don't fix it yet, just report your findings with specific file locations and code paths."""
    ),

    "cross-cutting": TestDimension(
        id="cross-cutting",
        name="Cross-Cutting Concern",
        description="Add X to all Y - requires finding all locations",
        prompt="""Add input validation to all Brief CLI commands that accept file paths as arguments.
Validate that: 1) paths exist, 2) paths are within the project directory (no path traversal),
3) paths point to files not directories (where appropriate). Use a shared validation function."""
    ),

    "integration": TestDimension(
        id="integration",
        name="Integration Task",
        description="Connect X to Y - requires understanding two systems",
        prompt="""Make the task system integrate with the logging system so that task state changes
(create, start, done, archive) are automatically recorded in the command log with timestamps.
The log entries should include the task ID, action, and relevant metadata."""
    ),

    "pattern-following": TestDimension(
        id="pattern-following",
        name="Pattern Following",
        description="Follow existing pattern when implementing Y",
        prompt="""Add a new 'brief contracts export' command following the same pattern used by
other export/output commands in the codebase. It should export all detected contracts
to a JSON file, with options for filtering by file or contract type."""
    ),

    "documentation": TestDimension(
        id="documentation",
        name="Documentation/Explanation",
        description="Document how X works",
        prompt="""Document how the context retrieval system works. Create a markdown file at
docs/CONTEXT_RETRIEVAL.md that explains the flow from a 'brief context get' call through
to the returned context package, including all intermediate steps and data transformations."""
    ),
}

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TestResult:
    """Results from a single test run."""
    config_name: str
    dimension_id: str
    dimension_name: str
    prompt: str
    timestamp: str
    duration_seconds: float
    exit_code: int
    tool_counts: dict = field(default_factory=dict)
    context_get_count: int = 0
    read_count: int = 0
    grep_count: int = 0
    glob_count: int = 0
    brief_ratio: float = 0.0
    test_env_path: Optional[str] = None
    raw_output_path: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def parse_claude_output(output: str) -> dict:
    """Parse Claude Code JSON output to extract tool usage."""
    tool_counts = {}
    context_get_count = 0

    try:
        # Try parsing as single JSON object
        data = json.loads(output)
        messages = data.get("messages", [])

        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "tool_use":
                            tool_name = block.get("name", "unknown")
                            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                            # Check for brief context get in Bash commands
                            if tool_name == "Bash":
                                cmd = block.get("input", {}).get("command", "")
                                if "brief context get" in cmd or "brief q " in cmd:
                                    context_get_count += 1

    except json.JSONDecodeError:
        # Try parsing as stream-json (newline-delimited)
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                # Handle streaming format
                if event.get("type") == "assistant" and "message" in event:
                    content = event["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if block.get("type") == "tool_use":
                                tool_name = block.get("name", "unknown")
                                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                                if tool_name == "Bash":
                                    cmd = block.get("input", {}).get("command", "")
                                    if "brief context get" in cmd or "brief q " in cmd:
                                        context_get_count += 1
            except json.JSONDecodeError:
                continue

    return {
        "tool_counts": tool_counts,
        "context_get_count": context_get_count,
        "read_count": tool_counts.get("Read", 0),
        "grep_count": tool_counts.get("Grep", 0),
        "glob_count": tool_counts.get("Glob", 0),
    }


# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

def create_test_environment(config_name: str, run_id: str, dimension: TestDimension) -> Path:
    """Create an isolated copy of the project for testing.

    Returns path to the test environment.
    """
    config = CONFIGS[config_name]

    # Create test directory
    test_dir = TEST_OUTPUT_DIR / run_id / "env"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Copy project (excluding heavy/unnecessary dirs)
    ignore_patterns = shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", "*.pyc", ".pytest_cache",
        "node_modules", ".brief-logs", "*.egg-info", "dist", "build",
        "embeddings.db"
    )

    # Copy source tree
    for item in PROJECT_ROOT.iterdir():
        if item.name in [".git", ".venv", "__pycache__", ".pytest_cache",
                         "node_modules", ".brief-logs", "dist", "build"]:
            continue
        dest = test_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=ignore_patterns)
        else:
            shutil.copy2(item, dest)

    # Copy .brief/ directory (for context data) but exclude tasks.jsonl
    brief_src = PROJECT_ROOT / ".brief"
    brief_dst = test_dir / ".brief"
    if brief_src.exists():
        if brief_dst.exists():
            shutil.rmtree(brief_dst)
        shutil.copytree(
            brief_src,
            brief_dst,
            ignore=shutil.ignore_patterns("tasks.jsonl", "*.db")
        )
        # Create empty tasks.jsonl
        (brief_dst / "tasks.jsonl").write_text("")

    # Apply configuration

    # 1. Set up hooks
    claude_dir = test_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)

    if config["hooks"]:
        # Write hooks config
        settings = {"hooks": config["hooks"]}
        (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

        # Copy hook scripts if needed
        hooks_src = PROJECT_ROOT / "scripts" / "hooks"
        hooks_dst = test_dir / "scripts" / "hooks"
        if hooks_src.exists() and not hooks_dst.exists():
            hooks_dst.mkdir(parents=True, exist_ok=True)
            for script in hooks_src.glob("*.sh"):
                shutil.copy2(script, hooks_dst / script.name)
    else:
        # No hooks - write empty settings
        (claude_dir / "settings.json").write_text(json.dumps({"hooks": {}}, indent=2))

    # 2. Set up CLAUDE.md
    if config["claude_md"]:
        claude_md_src = PROJECT_ROOT / config["claude_md"]
        if claude_md_src.exists():
            shutil.copy2(claude_md_src, test_dir / "CLAUDE.md")

    # 3. Run dimension-specific setup
    if dimension.setup_type == "multi-task":
        setup_multi_task(test_dir, dimension.setup_tasks)
    elif dimension.setup_type == "resume":
        setup_resume_scenario(test_dir, dimension.setup_tasks)

    return test_dir


def setup_multi_task(test_dir: Path, tasks: list):
    """Pre-create Brief tasks in the test environment."""
    tasks_file = test_dir / ".brief" / "tasks.jsonl"
    tasks_file.parent.mkdir(parents=True, exist_ok=True)

    with tasks_file.open("w") as f:
        for i, task in enumerate(tasks):
            task_data = {
                "id": f"test-{i+1:04d}",
                "title": task["title"],
                "description": task.get("desc", ""),
                "status": task.get("status", "pending"),
                "priority": task.get("priority", 50 - i),  # Higher priority for earlier tasks
                "created_at": datetime.now().isoformat(),
                "tags": [],
                "depends_on": [],
            }
            f.write(json.dumps(task_data) + "\n")


def setup_resume_scenario(test_dir: Path, tasks: list):
    """Set up a resume scenario with an active task."""
    tasks_file = test_dir / ".brief" / "tasks.jsonl"
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

    # Write active task file
    if active_task_id:
        active_file = test_dir / ".brief" / "active_task"
        active_file.write_text(active_task_id)


# =============================================================================
# TEST EXECUTION
# =============================================================================

def run_single_test(
    config_name: str,
    dimension_id: str,
    max_turns: int = 25,
    max_budget: float = 2.0,
    timeout: int = 600,
    keep_env: bool = False,
) -> TestResult:
    """Run a single test with the specified configuration and dimension."""

    if config_name not in CONFIGS:
        raise ValueError(f"Unknown config: {config_name}. Use --list-configs to see options.")
    if dimension_id not in DIMENSIONS:
        raise ValueError(f"Unknown dimension: {dimension_id}. Use --list-dimensions to see options.")

    dimension = DIMENSIONS[dimension_id]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{config_name}_{dimension_id}_{timestamp}"

    print(f"\n{'='*70}")
    print(f"Config: {config_name}")
    print(f"Dimension: {dimension.name}")
    print(f"{'='*70}")

    # Create isolated environment
    print("Creating isolated test environment...")
    test_dir = create_test_environment(config_name, run_id, dimension)
    print(f"Test environment: {test_dir}")

    start_time = datetime.now()

    # Build command
    cmd = [
        "claude",
        "-p", dimension.prompt,
        "--output-format", "stream-json",
        "--max-turns", str(max_turns),
        "--max-budget-usd", str(max_budget),
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--verbose",
    ]

    # Run the test
    try:
        print(f"Running Claude Code (max {max_turns} turns, ${max_budget} budget)...")
        print(f"Prompt: {dimension.prompt[:80]}...")
        result = subprocess.run(
            cmd,
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        exit_code = result.returncode
        error = result.stderr if result.returncode != 0 else None
    except subprocess.TimeoutExpired:
        output = ""
        exit_code = -1
        error = f"Test timed out after {timeout}s"
    except Exception as e:
        output = ""
        exit_code = -1
        error = str(e)

    duration = (datetime.now() - start_time).total_seconds()

    # Parse output
    metrics = parse_claude_output(output)

    # Calculate ratio
    exploration_tools = metrics["read_count"] + metrics["grep_count"] + metrics["glob_count"]
    total_exploration = metrics["context_get_count"] + exploration_tools
    if total_exploration > 0:
        brief_ratio = metrics["context_get_count"] / total_exploration
    else:
        brief_ratio = 0.0

    # Save raw output
    output_dir = TEST_OUTPUT_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "claude_output.json"
    output_file.write_text(output)

    # Save test metadata
    metadata = {
        "config": config_name,
        "dimension_id": dimension_id,
        "dimension_name": dimension.name,
        "prompt": dimension.prompt,
        "timestamp": timestamp,
        "duration": duration,
        "metrics": metrics,
        "brief_ratio": brief_ratio,
        "exit_code": exit_code,
        "error": error,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    # Print result
    print(f"\nResult: context_get={metrics['context_get_count']}, "
          f"Read/Grep/Glob={exploration_tools}, "
          f"ratio={brief_ratio:.1%}, "
          f"duration={duration:.1f}s")
    if error:
        print(f"Error: {error}")

    # Cleanup or keep environment
    if keep_env:
        print(f"\nTest environment preserved at: {test_dir}")
    else:
        shutil.rmtree(test_dir)
        test_dir = None

    return TestResult(
        config_name=config_name,
        dimension_id=dimension_id,
        dimension_name=dimension.name,
        prompt=dimension.prompt,
        timestamp=timestamp,
        duration_seconds=duration,
        exit_code=exit_code,
        tool_counts=metrics["tool_counts"],
        context_get_count=metrics["context_get_count"],
        read_count=metrics["read_count"],
        grep_count=metrics["grep_count"],
        glob_count=metrics["glob_count"],
        brief_ratio=brief_ratio,
        test_env_path=str(test_dir) if test_dir else None,
        raw_output_path=str(output_file),
        error=error,
    )


def run_comparison(
    configs: list[str],
    dimension_id: str,
    **kwargs
) -> list[TestResult]:
    """Run the same dimension with multiple configurations for comparison."""
    results = []
    for config_name in configs:
        result = run_single_test(config_name, dimension_id, **kwargs)
        results.append(result)

    return results


# =============================================================================
# REPORTING
# =============================================================================

def print_comparison_table(results: list[TestResult]):
    """Print a comparison table of results."""
    print("\n" + "="*90)
    print("COMPARISON RESULTS")
    print("="*90)
    print(f"{'Config':<22} {'context_get':<12} {'Read/Grep/Glob':<15} {'Brief Ratio':<12} {'Duration':<10}")
    print("-"*90)

    for r in results:
        exploration = r.read_count + r.grep_count + r.glob_count
        status = "" if r.exit_code == 0 else " [ERR]"
        print(f"{r.config_name:<22} {r.context_get_count:<12} {exploration:<15} "
              f"{r.brief_ratio:<12.1%} {r.duration_seconds:<10.1f}s{status}")

    print("="*90)

    # Summary
    if len(results) >= 2:
        best = max(results, key=lambda r: r.brief_ratio)
        worst = min(results, key=lambda r: r.brief_ratio)
        print(f"\nBest: {best.config_name} ({best.brief_ratio:.1%})")
        print(f"Worst: {worst.config_name} ({worst.brief_ratio:.1%})")


def save_results(results: list[TestResult], output_path: Path):
    """Save test results to a JSON file, appending to existing results."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results if file exists
    existing = []
    if output_path.exists():
        try:
            with output_path.open() as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            existing = []

    # Append new results
    new_data = [asdict(r) for r in results]
    all_data = existing + new_data

    with output_path.open("w") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path} ({len(new_data)} new, {len(all_data)} total)")


def generate_summary_report(results_path: Path):
    """Generate a summary report from accumulated results."""
    if not results_path.exists():
        print("No results file found.")
        return

    with results_path.open() as f:
        results = json.load(f)

    # Group by config
    by_config = {}
    for r in results:
        config = r["config_name"]
        if config not in by_config:
            by_config[config] = []
        by_config[config].append(r)

    # Group by dimension
    by_dimension = {}
    for r in results:
        dim = r["dimension_id"]
        if dim not in by_dimension:
            by_dimension[dim] = []
        by_dimension[dim].append(r)

    print("\n" + "="*90)
    print("SUMMARY REPORT")
    print("="*90)

    print("\n### By Configuration ###")
    print(f"{'Config':<22} {'Tests':<8} {'Avg Ratio':<12} {'Avg Duration':<12}")
    print("-"*60)
    for config, runs in sorted(by_config.items()):
        avg_ratio = sum(r["brief_ratio"] for r in runs) / len(runs)
        avg_duration = sum(r["duration_seconds"] for r in runs) / len(runs)
        print(f"{config:<22} {len(runs):<8} {avg_ratio:<12.1%} {avg_duration:<12.1f}s")

    print("\n### By Dimension ###")
    print(f"{'Dimension':<25} {'Tests':<8} {'Avg Ratio':<12}")
    print("-"*50)
    for dim, runs in sorted(by_dimension.items()):
        avg_ratio = sum(r["brief_ratio"] for r in runs) / len(runs)
        print(f"{dim:<25} {len(runs):<8} {avg_ratio:<12.1%}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Brief A/B Testing Framework v2 - Test agent Brief utilization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available options
  python performance-testing/run_test.py --list-configs
  python performance-testing/run_test.py --list-dimensions

  # Run single test
  python performance-testing/run_test.py --config baseline-pretool --dimension feature-addition

  # Compare configs on one dimension
  python performance-testing/run_test.py --compare null-no-hooks baseline-pretool --dimension feature-addition

  # Run all dimensions for one config
  python performance-testing/run_test.py --config baseline-full-hooks --dimension all

  # Run full test suite (all configs × all dimensions)
  python performance-testing/run_test.py --compare all --dimension all --output results.json

  # Generate summary from results
  python performance-testing/run_test.py --summary results.json
        """
    )
    parser.add_argument("--config", "-c", help="Single configuration to test")
    parser.add_argument("--compare", nargs="+", metavar="CONFIG", help="Compare configs (use 'all' for all)")
    parser.add_argument("--dimension", "-d", help="Dimension to test (or 'all')")
    parser.add_argument("--max-turns", type=int, default=25, help="Max agentic turns (default: 25)")
    parser.add_argument("--max-budget", type=float, default=2.0, help="Max budget in USD (default: 2.0)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds (default: 600)")
    parser.add_argument("--output", "-o", type=Path, help="Output file for results JSON")
    parser.add_argument("--keep-env", action="store_true", help="Keep test environment for review")
    parser.add_argument("--list-configs", action="store_true", help="List available configurations")
    parser.add_argument("--list-dimensions", action="store_true", help="List test dimensions")
    parser.add_argument("--summary", type=Path, help="Generate summary from results file")

    args = parser.parse_args()

    if args.list_configs:
        print("Available configurations:\n")
        for name, config in CONFIGS.items():
            hooks_count = len(config["hooks"]) if config["hooks"] else 0
            print(f"  {name}")
            print(f"    {config['description']}")
            print(f"    Hooks: {hooks_count}")
            print(f"    CLAUDE.md: {config['claude_md']}")
            print()
        return

    if args.list_dimensions:
        print("Test dimensions:\n")
        for dim_id, dim in DIMENSIONS.items():
            print(f"  {dim_id}")
            print(f"    {dim.name}")
            print(f"    {dim.description}")
            print(f"    Setup: {dim.setup_type}")
            print()
        return

    if args.summary:
        generate_summary_report(args.summary)
        return

    # Validation
    if not args.config and not args.compare:
        parser.print_help()
        print("\nError: Must specify --config or --compare")
        sys.exit(1)

    if not args.dimension:
        print("Error: --dimension required")
        sys.exit(1)

    # Determine configs and dimensions to run
    if args.compare:
        if args.compare == ["all"]:
            configs = list(CONFIGS.keys())
        else:
            configs = args.compare
    else:
        configs = [args.config]

    if args.dimension == "all":
        dimensions = list(DIMENSIONS.keys())
    else:
        dimensions = [args.dimension]

    # Set up output file
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESULTS_DIR / f"results_{timestamp}.json"

    all_results = []

    # Run tests
    total_tests = len(configs) * len(dimensions)
    current_test = 0

    for dimension_id in dimensions:
        print(f"\n{'#'*70}")
        print(f"# Dimension: {DIMENSIONS[dimension_id].name}")
        print(f"{'#'*70}")

        dimension_results = []
        for config_name in configs:
            current_test += 1
            print(f"\n[Test {current_test}/{total_tests}]")

            result = run_single_test(
                config_name,
                dimension_id,
                max_turns=args.max_turns,
                max_budget=args.max_budget,
                timeout=args.timeout,
                keep_env=args.keep_env,
            )
            dimension_results.append(result)
            all_results.append(result)

        if len(dimension_results) > 1:
            print_comparison_table(dimension_results)

    # Save results
    save_results(all_results, output_path)

    # Print overall summary
    if len(all_results) > 1:
        print(f"\n{'='*70}")
        print("OVERALL SUMMARY")
        print(f"{'='*70}")
        avg_ratio = sum(r.brief_ratio for r in all_results) / len(all_results)
        print(f"Tests run: {len(all_results)}")
        print(f"Average Brief Ratio: {avg_ratio:.1%}")

        # Best and worst configs
        by_config = {}
        for r in all_results:
            if r.config_name not in by_config:
                by_config[r.config_name] = []
            by_config[r.config_name].append(r.brief_ratio)

        config_avgs = {c: sum(ratios)/len(ratios) for c, ratios in by_config.items()}
        best_config = max(config_avgs.items(), key=lambda x: x[1])
        worst_config = min(config_avgs.items(), key=lambda x: x[1])

        print(f"Best config: {best_config[0]} ({best_config[1]:.1%})")
        print(f"Worst config: {worst_config[0]} ({worst_config[1]:.1%})")


if __name__ == "__main__":
    main()
