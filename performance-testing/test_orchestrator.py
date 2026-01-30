#!/usr/bin/env python3
"""
Basic tests for the Claude Code orchestrator.

Tests repo isolation, manifest tracking, and simple runs.
Run with: python performance-testing/test_orchestrator.py
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add parent to path so we can import orchestrator
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import ClaudeOrchestrator, ClaudeJob, ManifestEntry

PROJECT_ROOT = Path(__file__).parent.parent
TEST_TEMP = Path("/home/user/tmp/brief-performance-testing/test-runs")


def cleanup():
    """Remove test artifacts."""
    if TEST_TEMP.exists():
        shutil.rmtree(TEST_TEMP)
    manifest = PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl"
    if manifest.exists():
        manifest.unlink()


def test_repo_isolation():
    """Verify git clone produces a proper isolated repo."""
    print("=" * 60)
    print("TEST: Repo Isolation")
    print("=" * 60)

    work_dir = TEST_TEMP / "isolation-test"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl",
        max_workers=1,
    )

    job = ClaudeJob(
        job_id="isolation-test",
        prompt="dummy",  # Won't actually run
        repo_path=str(PROJECT_ROOT),
    )

    # Test clone
    orch._clone_repo(job, work_dir)

    # Verify .git exists
    git_dir = work_dir / ".git"
    assert git_dir.exists(), f"FAIL: .git not found in {work_dir}"
    print(f"  PASS: .git exists in clone")

    # Verify it's a separate git repo
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=work_dir,
        capture_output=True,
        text=True,
    )
    toplevel = result.stdout.strip()
    assert toplevel == str(work_dir), f"FAIL: git toplevel is {toplevel}, expected {work_dir}"
    print(f"  PASS: git toplevel is the clone, not parent repo")

    # Verify source files exist
    assert (work_dir / "src" / "brief" / "cli.py").exists(), "FAIL: source files not in clone"
    print(f"  PASS: source files present in clone")

    # Verify the clone is NOT the same directory as PROJECT_ROOT
    assert str(work_dir) != str(PROJECT_ROOT), "FAIL: work_dir is the same as PROJECT_ROOT"
    print(f"  PASS: clone is separate from main repo")

    # Clean up
    shutil.rmtree(work_dir)
    print("  PASS: cleanup successful")
    print()


def test_environment_setup():
    """Verify CLAUDE.md and settings.json overrides work."""
    print("=" * 60)
    print("TEST: Environment Setup")
    print("=" * 60)

    work_dir = TEST_TEMP / "env-setup-test"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl",
        max_workers=1,
    )

    custom_md = PROJECT_ROOT / "performance-testing" / "test-files" / "claude-md-null.md"

    job = ClaudeJob(
        job_id="env-setup-test",
        prompt="dummy",
        repo_path=str(PROJECT_ROOT),
        claude_md_source=str(custom_md),
        settings_json={"hooks": {"PreToolUse": [{"matcher": "Read", "hooks": []}]}},
    )

    # Clone and setup
    orch._clone_repo(job, work_dir)
    orch._setup_environment(job, work_dir)

    # Verify CLAUDE.md was replaced
    claude_md = work_dir / "CLAUDE.md"
    assert claude_md.exists(), "FAIL: CLAUDE.md not found"
    content = claude_md.read_text()
    # Null CLAUDE.md should NOT have Brief workflow instructions
    assert "brief context get" not in content, "FAIL: CLAUDE.md has Brief instructions (should be null)"
    print(f"  PASS: CLAUDE.md replaced with null version")

    # Verify settings.json
    settings_path = work_dir / ".claude" / "settings.json"
    assert settings_path.exists(), "FAIL: settings.json not found"
    settings = json.loads(settings_path.read_text())
    assert "hooks" in settings, "FAIL: hooks not in settings"
    assert "PreToolUse" in settings["hooks"], "FAIL: PreToolUse not in hooks"
    print(f"  PASS: .claude/settings.json written correctly")

    # Verify git toplevel is still correct
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=work_dir,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == str(work_dir), "FAIL: git toplevel changed after setup"
    print(f"  PASS: git toplevel still correct after env setup")

    # Clean up
    shutil.rmtree(work_dir)
    print("  PASS: cleanup successful")
    print()


def test_setup_fn():
    """Verify custom setup functions work."""
    print("=" * 60)
    print("TEST: Custom Setup Function")
    print("=" * 60)

    work_dir = TEST_TEMP / "setup-fn-test"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    marker_content = "setup_fn was here"

    def my_setup(wd: Path):
        (wd / "setup_marker.txt").write_text(marker_content)

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl",
        max_workers=1,
    )

    job = ClaudeJob(
        job_id="setup-fn-test",
        prompt="dummy",
        repo_path=str(PROJECT_ROOT),
        setup_fn=my_setup,
    )

    orch._clone_repo(job, work_dir)
    orch._setup_environment(job, work_dir)

    marker = work_dir / "setup_marker.txt"
    assert marker.exists(), "FAIL: setup_fn marker file not created"
    assert marker.read_text() == marker_content, "FAIL: marker content wrong"
    print(f"  PASS: setup_fn executed correctly")

    shutil.rmtree(work_dir)
    print("  PASS: cleanup successful")
    print()


def test_manifest_tracking():
    """Verify manifest append and read works."""
    print("=" * 60)
    print("TEST: Manifest Tracking")
    print("=" * 60)

    manifest_path = PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl"
    if manifest_path.exists():
        manifest_path.unlink()

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=manifest_path,
        max_workers=1,
    )

    # Append entries
    orch._append_manifest(ManifestEntry(
        job_id="test-1",
        status="queued",
        timestamp="2026-01-28T14:00:00",
        metadata={"config": "baseline"},
    ))
    orch._append_manifest(ManifestEntry(
        job_id="test-1",
        status="running",
        timestamp="2026-01-28T14:00:05",
        pid=12345,
        metadata={"config": "baseline"},
    ))
    orch._append_manifest(ManifestEntry(
        job_id="test-2",
        status="queued",
        timestamp="2026-01-28T14:00:06",
        metadata={"config": "null"},
    ))
    orch._append_manifest(ManifestEntry(
        job_id="test-1",
        status="completed",
        timestamp="2026-01-28T14:03:00",
        exit_code=0,
        duration_seconds=175.0,
        metadata={"config": "baseline"},
    ))

    # Read manifest - should return latest per job_id
    entries = orch.read_manifest()
    assert len(entries) == 2, f"FAIL: expected 2 entries, got {len(entries)}"
    print(f"  PASS: read_manifest returns latest per job_id")

    entry_map = {e.job_id: e for e in entries}
    assert entry_map["test-1"].status == "completed", "FAIL: test-1 should be completed"
    assert entry_map["test-1"].exit_code == 0, "FAIL: test-1 exit code should be 0"
    assert entry_map["test-2"].status == "queued", "FAIL: test-2 should be queued"
    print(f"  PASS: entry statuses correct")

    # Verify JSONL file has 4 lines
    lines = manifest_path.read_text().strip().split("\n")
    assert len(lines) == 4, f"FAIL: expected 4 lines in manifest, got {len(lines)}"
    print(f"  PASS: manifest has 4 append-only lines")

    manifest_path.unlink()
    print("  PASS: cleanup successful")
    print()


def test_hello_world_run():
    """Run a simple hello-world prompt through the orchestrator."""
    print("=" * 60)
    print("TEST: Hello World Run")
    print("=" * 60)
    print("  Running claude -p with a trivial prompt...")
    print("  (This tests the full lifecycle: clone -> setup -> run -> complete)")

    manifest_path = PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl"
    if manifest_path.exists():
        manifest_path.unlink()

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=manifest_path,
        max_workers=1,
    )

    orch.add_job(ClaudeJob(
        job_id="hello-world",
        prompt="Say hello and nothing else. Do not use any tools.",
        repo_path=str(PROJECT_ROOT),
        max_turns=3,
        max_budget=0.10,
        timeout=60,
        settings_json={"hooks": {}},
        metadata={"test": "hello-world"},
    ))

    entries = orch.run()

    # Check results
    assert len(entries) > 0, "FAIL: no manifest entries"
    latest = {e.job_id: e for e in entries}
    hw = latest.get("hello-world")
    assert hw is not None, "FAIL: hello-world entry not found"
    assert hw.status == "completed", f"FAIL: expected completed, got {hw.status}"
    assert hw.exit_code == 0, f"FAIL: expected exit 0, got {hw.exit_code}"
    assert hw.duration_seconds is not None, "FAIL: no duration recorded"
    print(f"  PASS: hello-world completed (exit={hw.exit_code}, {hw.duration_seconds:.1f}s)")

    # Check stdout file exists and has content
    stdout_path = Path(hw.stdout_path)
    assert stdout_path.exists(), f"FAIL: stdout file not found at {stdout_path}"
    stdout_size = stdout_path.stat().st_size
    assert stdout_size > 0, "FAIL: stdout file is empty"
    print(f"  PASS: stdout captured ({stdout_size} bytes)")

    # Verify the work dir is isolated
    work_dir = Path(hw.work_dir)
    if work_dir.exists():
        git_toplevel = os.popen(f"git -C {work_dir} rev-parse --show-toplevel 2>/dev/null").read().strip()
        assert git_toplevel == str(work_dir), f"FAIL: git toplevel wrong: {git_toplevel}"
        print(f"  PASS: work dir is properly isolated git repo")

    print()


def test_parallel_runs():
    """Run two simple jobs in parallel to verify worker pool."""
    print("=" * 60)
    print("TEST: Parallel Runs (2 workers)")
    print("=" * 60)

    manifest_path = PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl"
    if manifest_path.exists():
        manifest_path.unlink()

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=manifest_path,
        max_workers=2,
    )

    orch.add_jobs([
        ClaudeJob(
            job_id="parallel-1",
            prompt="Say 'one'. Do not use any tools.",
            repo_path=str(PROJECT_ROOT),
            max_turns=3,
            max_budget=0.10,
            timeout=60,
            settings_json={"hooks": {}},
            metadata={"test": "parallel", "n": 1},
        ),
        ClaudeJob(
            job_id="parallel-2",
            prompt="Say 'two'. Do not use any tools.",
            repo_path=str(PROJECT_ROOT),
            max_turns=3,
            max_budget=0.10,
            timeout=60,
            settings_json={"hooks": {}},
            metadata={"test": "parallel", "n": 2},
        ),
    ])

    entries = orch.run()
    latest = {e.job_id: e for e in entries}

    assert "parallel-1" in latest, "FAIL: parallel-1 not in manifest"
    assert "parallel-2" in latest, "FAIL: parallel-2 not in manifest"
    assert latest["parallel-1"].status == "completed", f"FAIL: parallel-1 {latest['parallel-1'].status}"
    assert latest["parallel-2"].status == "completed", f"FAIL: parallel-2 {latest['parallel-2'].status}"
    print(f"  PASS: both jobs completed")
    print(f"  parallel-1: {latest['parallel-1'].duration_seconds:.1f}s")
    print(f"  parallel-2: {latest['parallel-2'].duration_seconds:.1f}s")

    # Check that no files leaked to main repo
    # (main repo should have same git status as before)
    print(f"  PASS: parallel execution completed")
    print()


def test_no_main_repo_contamination():
    """Verify that running a job doesn't modify the main repo."""
    print("=" * 60)
    print("TEST: No Main Repo Contamination")
    print("=" * 60)

    import subprocess

    # Record current git status
    before = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    ).stdout

    manifest_path = PROJECT_ROOT / "performance-testing" / "results" / "test_manifest.jsonl"
    if manifest_path.exists():
        manifest_path.unlink()

    orch = ClaudeOrchestrator(
        temp_dir=TEST_TEMP,
        manifest_path=manifest_path,
        max_workers=1,
    )

    orch.add_job(ClaudeJob(
        job_id="contamination-test",
        prompt="Create a file called CONTAMINATION_TEST.txt with the text 'this should not appear in main repo'",
        repo_path=str(PROJECT_ROOT),
        max_turns=5,
        max_budget=0.10,
        timeout=60,
        settings_json={"hooks": {}},
        metadata={"test": "contamination"},
    ))

    entries = orch.run()

    # Check git status hasn't changed (except manifest file which is in our results dir)
    after = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    ).stdout

    assert before == after, f"FAIL: git diff changed!\nBefore:\n{before}\nAfter:\n{after}"
    print(f"  PASS: git diff unchanged after test run")

    # Check contamination file doesn't exist in main repo
    contamination_file = PROJECT_ROOT / "CONTAMINATION_TEST.txt"
    assert not contamination_file.exists(), "FAIL: contamination file found in main repo!"
    print(f"  PASS: no contamination file in main repo")

    # Check it DOES exist in the work dir
    latest = {e.job_id: e for e in entries}
    work_dir = Path(latest["contamination-test"].work_dir)
    if work_dir.exists():
        contamination_in_clone = work_dir / "CONTAMINATION_TEST.txt"
        if contamination_in_clone.exists():
            print(f"  PASS: contamination file correctly isolated in clone")
        else:
            print(f"  INFO: agent didn't create the file (prompt may have been too short)")

    print()


def main():
    """Run all tests."""
    print("\nClaude Code Orchestrator Tests")
    print("=" * 60)
    print()

    # Unit-level tests (no claude invocation)
    test_repo_isolation()
    test_environment_setup()
    test_setup_fn()
    test_manifest_tracking()

    # Integration tests (requires claude CLI)
    print("\n--- Integration tests (require claude CLI) ---\n")
    test_hello_world_run()
    test_parallel_runs()
    test_no_main_repo_contamination()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

    # Cleanup
    cleanup()


if __name__ == "__main__":
    main()
