#!/usr/bin/env python3
"""
Post-run analysis for Brief performance tests.

Reads the orchestrator manifest, parses Claude Code output from each
test run, and generates comparison reports.

Usage:
    python performance-testing/analyze.py                              # Use default manifest
    python performance-testing/analyze.py path/to/manifest.jsonl       # Specific manifest
    python performance-testing/analyze.py --detail job-id              # Detail for one job
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def read_manifest(manifest_path: Path) -> list[dict]:
    """Read manifest JSONL, return latest entry per job_id."""
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return []

    entries_by_id = {}
    with manifest_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries_by_id[entry["job_id"]] = entry
            except (json.JSONDecodeError, KeyError):
                continue

    return list(entries_by_id.values())


def parse_claude_output(stdout_path: str) -> dict:
    """Parse Claude Code stream-json output to extract tool usage metrics."""
    path = Path(stdout_path)
    if not path.exists():
        return {"tool_counts": {}, "context_get_count": 0,
                "read_count": 0, "grep_count": 0, "glob_count": 0,
                "brief_ratio": 0.0, "total_turns": 0, "parse_error": "stdout not found"}

    content = path.read_text().strip()
    if not content:
        return {"tool_counts": {}, "context_get_count": 0,
                "read_count": 0, "grep_count": 0, "glob_count": 0,
                "brief_ratio": 0.0, "total_turns": 0, "parse_error": "stdout empty"}

    tool_counts = {}
    context_get_count = 0
    total_turns = 0

    for line in content.split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)

            # Count turns
            if event.get("type") == "assistant":
                total_turns += 1

            # Extract tool usage from assistant messages
            message = event.get("message", event)
            content_blocks = message.get("content", [])
            if isinstance(content_blocks, list):
                for block in content_blocks:
                    if block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                        # Check for brief context get in Bash commands
                        if tool_name == "Bash":
                            cmd = block.get("input", {}).get("command", "")
                            if "brief context get" in cmd or "brief q " in cmd:
                                context_get_count += 1

        except json.JSONDecodeError:
            continue

    read_count = tool_counts.get("Read", 0)
    grep_count = tool_counts.get("Grep", 0)
    glob_count = tool_counts.get("Glob", 0)

    exploration = context_get_count + read_count + grep_count + glob_count
    brief_ratio = context_get_count / exploration if exploration > 0 else 0.0

    return {
        "tool_counts": tool_counts,
        "context_get_count": context_get_count,
        "read_count": read_count,
        "grep_count": grep_count,
        "glob_count": glob_count,
        "brief_ratio": brief_ratio,
        "total_turns": total_turns,
    }


def analyze_entries(entries: list[dict]) -> list[dict]:
    """Parse outputs for all completed entries, return enriched results."""
    results = []
    for entry in entries:
        if entry.get("status") != "completed":
            results.append({
                **entry,
                "metrics": None,
                "brief_ratio": 0.0,
            })
            continue

        stdout_path = entry.get("stdout_path", "")
        metrics = parse_claude_output(stdout_path)

        results.append({
            **entry,
            "metrics": metrics,
            "brief_ratio": metrics["brief_ratio"],
            "context_get_count": metrics["context_get_count"],
            "read_count": metrics["read_count"],
            "grep_count": metrics["grep_count"],
            "glob_count": metrics["glob_count"],
            "total_turns": metrics["total_turns"],
        })

    return results


# =============================================================================
# REPORTING
# =============================================================================

def print_config_comparison(results: list[dict]):
    """Print comparison table grouped by config."""
    by_config = defaultdict(list)
    for r in results:
        if r.get("status") != "completed":
            continue
        config = r.get("metadata", {}).get("config_name", "unknown")
        by_config[config].append(r)

    if not by_config:
        print("No completed results to analyze.")
        return

    print("\n" + "=" * 90)
    print("RESULTS BY CONFIGURATION")
    print("=" * 90)
    print(f"{'Config':<22} {'Tests':<7} {'ctx_get':<8} {'R/G/G':<7} {'Avg Ratio':<11} {'Avg Duration':<12}")
    print("-" * 90)

    rows = []
    for config in sorted(by_config.keys()):
        runs = by_config[config]
        total_ctx = sum(r.get("context_get_count", 0) for r in runs)
        total_rgg = sum(r.get("read_count", 0) + r.get("grep_count", 0) + r.get("glob_count", 0) for r in runs)
        avg_ratio = sum(r.get("brief_ratio", 0) for r in runs) / len(runs)
        avg_duration = sum(r.get("duration_seconds", 0) for r in runs) / len(runs)
        rows.append((config, len(runs), total_ctx, total_rgg, avg_ratio, avg_duration))
        print(f"{config:<22} {len(runs):<7} {total_ctx:<8} {total_rgg:<7} {avg_ratio:<11.1%} {avg_duration:<12.1f}s")

    print("=" * 90)

    # Best/worst
    if len(rows) >= 2:
        best = max(rows, key=lambda r: r[4])
        worst = min(rows, key=lambda r: r[4])
        print(f"\nBest:  {best[0]} ({best[4]:.1%})")
        print(f"Worst: {worst[0]} ({worst[4]:.1%})")


def print_dimension_comparison(results: list[dict]):
    """Print comparison table grouped by dimension."""
    by_dim = defaultdict(list)
    for r in results:
        if r.get("status") != "completed":
            continue
        dim = r.get("metadata", {}).get("dimension_id", "unknown")
        by_dim[dim].append(r)

    if not by_dim:
        return

    print("\n" + "=" * 90)
    print("RESULTS BY DIMENSION")
    print("=" * 90)
    print(f"{'Dimension':<25} {'Tests':<7} {'Avg Ratio':<11} {'Avg ctx_get':<12} {'Avg R/G/G':<10}")
    print("-" * 90)

    for dim in sorted(by_dim.keys()):
        runs = by_dim[dim]
        avg_ratio = sum(r.get("brief_ratio", 0) for r in runs) / len(runs)
        avg_ctx = sum(r.get("context_get_count", 0) for r in runs) / len(runs)
        avg_rgg = sum(r.get("read_count", 0) + r.get("grep_count", 0) + r.get("glob_count", 0) for r in runs) / len(runs)
        print(f"{dim:<25} {len(runs):<7} {avg_ratio:<11.1%} {avg_ctx:<12.1f} {avg_rgg:<10.1f}")

    print("=" * 90)


def print_isolation_analysis(results: list[dict]):
    """Compare configs to isolate variable impact."""
    by_config = defaultdict(list)
    for r in results:
        if r.get("status") != "completed":
            continue
        config = r.get("metadata", {}).get("config_name", "unknown")
        by_config[config].append(r)

    if not by_config:
        return

    def avg_ratio(config_name):
        runs = by_config.get(config_name, [])
        if not runs:
            return None
        return sum(r.get("brief_ratio", 0) for r in runs) / len(runs)

    print("\n" + "=" * 90)
    print("VARIABLE ISOLATION ANALYSIS")
    print("=" * 90)

    # CLAUDE.md impact (same hooks, different docs)
    print("\n### CLAUDE.md Impact (holding hooks constant) ###")
    hook_groups = [
        ("No hooks", "null-no-hooks", "baseline-no-hooks"),
        ("PreToolUse only", "null-pretool", "baseline-pretool"),
        ("Full hooks", "null-full-hooks", "baseline-full-hooks"),
    ]
    print(f"{'Hooks':<20} {'Null CLAUDE.md':<16} {'Baseline CLAUDE.md':<20} {'Delta':<10}")
    print("-" * 70)
    for label, null_cfg, baseline_cfg in hook_groups:
        null_r = avg_ratio(null_cfg)
        base_r = avg_ratio(baseline_cfg)
        if null_r is not None and base_r is not None:
            delta = base_r - null_r
            print(f"{label:<20} {null_r:<16.1%} {base_r:<20.1%} {delta:<+10.1%}")
        else:
            print(f"{label:<20} {'N/A':<16} {'N/A':<20} {'N/A':<10}")

    # Hook impact (same CLAUDE.md, different hooks)
    print("\n### Hook Impact (holding CLAUDE.md constant) ###")
    md_groups = [
        ("Null CLAUDE.md", [
            ("No hooks", "null-no-hooks"),
            ("PreToolUse", "null-pretool"),
            ("UserPrompt", "null-userprompt"),
            ("Full hooks", "null-full-hooks"),
        ]),
        ("Baseline CLAUDE.md", [
            ("No hooks", "baseline-no-hooks"),
            ("PreToolUse", "baseline-pretool"),
            ("Full hooks", "baseline-full-hooks"),
        ]),
    ]

    for md_label, configs in md_groups:
        print(f"\n  {md_label}:")
        print(f"  {'Hooks':<20} {'Avg Ratio':<12} {'Tests':<7}")
        print(f"  {'-'*45}")
        for hook_label, cfg_name in configs:
            r = avg_ratio(cfg_name)
            n = len(by_config.get(cfg_name, []))
            if r is not None:
                print(f"  {hook_label:<20} {r:<12.1%} {n:<7}")
            else:
                print(f"  {hook_label:<20} {'N/A':<12} {0:<7}")

    print()


def print_full_matrix(results: list[dict]):
    """Print the full config x dimension matrix."""
    by_config_dim = {}
    for r in results:
        if r.get("status") != "completed":
            continue
        config = r.get("metadata", {}).get("config_name", "unknown")
        dim = r.get("metadata", {}).get("dimension_id", "unknown")
        by_config_dim[(config, dim)] = r

    if not by_config_dim:
        return

    configs = sorted(set(c for c, _ in by_config_dim.keys()))
    dims = sorted(set(d for _, d in by_config_dim.keys()))

    print("\n" + "=" * 90)
    print("FULL MATRIX (Brief Ratio)")
    print("=" * 90)

    # Header
    header = f"{'Config':<22}"
    for dim in dims:
        short = dim[:8]
        header += f" {short:<9}"
    print(header)
    print("-" * (22 + 10 * len(dims)))

    for config in configs:
        row = f"{config:<22}"
        for dim in dims:
            r = by_config_dim.get((config, dim))
            if r:
                ratio = r.get("brief_ratio", 0)
                row += f" {ratio:<9.0%}"
            else:
                row += f" {'---':<9}"
        print(row)

    print("=" * (22 + 10 * len(dims)))


def print_detail(results: list[dict], job_id: str):
    """Print detailed results for a specific job."""
    entry = None
    for r in results:
        if r.get("job_id") == job_id:
            entry = r
            break

    if not entry:
        print(f"Job not found: {job_id}")
        return

    print(f"\nJob: {entry['job_id']}")
    print(f"Status: {entry.get('status', 'unknown')}")
    print(f"Config: {entry.get('metadata', {}).get('config_name', 'N/A')}")
    print(f"Dimension: {entry.get('metadata', {}).get('dimension_name', 'N/A')}")
    print(f"Duration: {entry.get('duration_seconds', 0):.1f}s")
    print(f"Exit code: {entry.get('exit_code', 'N/A')}")

    if entry.get("metrics"):
        m = entry["metrics"]
        print(f"\nTool counts:")
        for tool, count in sorted(m.get("tool_counts", {}).items()):
            print(f"  {tool}: {count}")
        print(f"\nBrief ratio: {m.get('brief_ratio', 0):.1%}")
        print(f"  context_get: {m.get('context_get_count', 0)}")
        print(f"  Read: {m.get('read_count', 0)}")
        print(f"  Grep: {m.get('grep_count', 0)}")
        print(f"  Glob: {m.get('glob_count', 0)}")

    if entry.get("error"):
        print(f"\nError: {entry['error']}")

    print(f"\nWork dir: {entry.get('work_dir', 'N/A')}")
    print(f"Stdout: {entry.get('stdout_path', 'N/A')}")
    print(f"Stderr: {entry.get('stderr_path', 'N/A')}")


def print_failures(results: list[dict]):
    """Print summary of failed jobs."""
    failed = [r for r in results if r.get("status") in ("failed", "killed", "error")]
    if not failed:
        return

    print(f"\n{'='*90}")
    print(f"FAILURES ({len(failed)})")
    print(f"{'='*90}")
    for r in failed:
        config = r.get("metadata", {}).get("config_name", "?")
        dim = r.get("metadata", {}).get("dimension_id", "?")
        status = r.get("status", "?")
        error = r.get("error", "")[:100]
        print(f"  {config}/{dim}: {status} - {error}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Brief performance test results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("manifest", nargs="?",
                        default="performance-testing/results/manifest.jsonl",
                        help="Path to manifest JSONL")
    parser.add_argument("--detail", help="Show detail for a specific job ID")
    parser.add_argument("--matrix", action="store_true", help="Show full config x dimension matrix")

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = PROJECT_ROOT / manifest_path

    entries = read_manifest(manifest_path)
    if not entries:
        print("No entries in manifest.")
        return

    results = analyze_entries(entries)

    completed = [r for r in results if r.get("status") == "completed"]
    total = len(results)
    print(f"Manifest: {manifest_path}")
    print(f"Total entries: {total} ({len(completed)} completed)")

    if args.detail:
        print_detail(results, args.detail)
        return

    print_config_comparison(results)
    print_dimension_comparison(results)
    print_isolation_analysis(results)

    if args.matrix:
        print_full_matrix(results)

    print_failures(results)


if __name__ == "__main__":
    main()
