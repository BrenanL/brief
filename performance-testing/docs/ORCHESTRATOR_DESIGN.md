# Claude Code Orchestrator Design

**Created**: 2026-01-28
**Purpose**: General-purpose orchestrator for queuing and running Claude Code headless sessions

---

## Overview

The orchestrator is a standalone module that manages queued Claude Code runs with:
- Proper git-based repo isolation
- Configurable worker parallelism
- Append-only JSONL manifest for tracking
- Process group management for clean shutdown
- Per-job stdout/stderr capture

It is **not** tied to Brief or our testing system. It answers: "Given N prompts and environment configs, run them through Claude Code headless with proper isolation, parallelism, tracking, and cleanup."

---

## Components

### `orchestrator.py`

Three main classes:

#### `ClaudeJob`
What gets queued. Defines a single Claude Code run.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Unique identifier |
| `prompt` | str | The prompt to send |
| `repo_path` | str | Local path to git clone from |
| `repo_ref` | str | Git ref to checkout (default: HEAD) |
| `max_turns` | int | Max agentic turns (default: 25) |
| `max_budget` | float | Max spend in USD (default: 2.0) |
| `timeout` | int | Hard kill timeout in seconds (default: 600) |
| `model` | str? | Override model (sonnet, opus, etc.) |
| `append_system_prompt` | str? | Additional system prompt |
| `allowed_tools` | list? | Restrict available tools |
| `claude_md_source` | str? | Path to file to copy as CLAUDE.md |
| `settings_json` | dict? | Content for .claude/settings.json |
| `setup_fn` | Callable? | Custom function: setup_fn(work_dir: Path) |
| `overlay_paths` | dict? | Files to copy: {src_path: relative_dest} |
| `metadata` | dict | Passthrough data stored in manifest |

#### `ManifestEntry`
One line in the JSONL manifest. Append-only; latest entry per `job_id` wins.

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Links to ClaudeJob |
| `status` | str | queued/cloning/setting_up/running/completed/failed/killed/error |
| `timestamp` | str | ISO timestamp of this entry |
| `work_dir` | str? | Path to cloned repo |
| `stdout_path` | str? | Path to captured stdout |
| `stderr_path` | str? | Path to captured stderr |
| `pid` | int? | Process ID |
| `start_time` | str? | When claude process started |
| `end_time` | str? | When it finished |
| `duration_seconds` | float? | Wall clock duration |
| `exit_code` | int? | Process exit code |
| `error` | str? | Error message if any |
| `metadata` | dict | Passthrough from job |

#### `ClaudeOrchestrator`
The worker pool that executes jobs.

| Method | Description |
|--------|-------------|
| `__init__(temp_dir, manifest_path, max_workers)` | Configure orchestrator |
| `add_job(job)` | Queue a single job |
| `add_jobs(jobs)` | Queue multiple jobs |
| `run()` | Execute all jobs, block until done, return entries |
| `read_manifest()` | Parse manifest, return latest entry per job_id |
| `status()` | Return queue/active/completed counts |

---

## Workflow

```
add_job(job)
  │
  ▼
Queue (FIFO)
  │
  ▼ (when worker slot available)
_clone_repo(job)
  ├─ git clone <repo_path> <temp_dir>/<job_id>/
  ├─ git checkout <repo_ref>
  └─ manifest: status=cloning
  │
  ▼
_setup_environment(job, work_dir)
  ├─ Copy claude_md_source → work_dir/CLAUDE.md
  ├─ Write settings_json → work_dir/.claude/settings.json
  ├─ Copy overlay_paths
  ├─ Run setup_fn(work_dir)
  └─ manifest: status=setting_up
  │
  ▼
_start_job(job, work_dir)
  ├─ Build command:
  │   claude -p <prompt>
  │     --output-format stream-json
  │     --max-turns N
  │     --max-budget-usd N
  │     --dangerously-skip-permissions
  │     --verbose
  │     [--model M] [--append-system-prompt S]
  ├─ Popen(cmd, cwd=work_dir,
  │        stdout=work_dir/stdout.jsonl,
  │        stderr=work_dir/stderr.log,
  │        preexec_fn=os.setsid)
  └─ manifest: status=running, pid=X
  │
  ▼ (poll loop, every 2s)
_poll_active()
  ├─ proc.poll() != None
  │   ├─ exit_code == 0 → manifest: status=completed
  │   └─ exit_code != 0 → manifest: status=failed
  ├─ elapsed > timeout → os.killpg(pgid, SIGTERM)
  │   └─ manifest: status=killed
  └─ Print status line
```

### Shutdown

On SIGINT/SIGTERM:
1. Set `_shutdown` flag (stops dequeuing)
2. Send SIGTERM to each active process group
3. Wait 5 seconds
4. Send SIGKILL to any remaining
5. Update manifest with `status=killed` for each

---

## Manifest Format

JSONL file. Each line is a complete JSON object. Multiple entries per job_id are expected; latest timestamp wins.

```jsonl
{"job_id": "test-1", "status": "queued", "timestamp": "2026-01-28T14:00:00", "metadata": {"config": "baseline"}}
{"job_id": "test-1", "status": "cloning", "timestamp": "2026-01-28T14:00:01", "work_dir": "/home/user/tmp/..."}
{"job_id": "test-1", "status": "running", "timestamp": "2026-01-28T14:00:05", "pid": 12345}
{"job_id": "test-1", "status": "completed", "timestamp": "2026-01-28T14:03:22", "exit_code": 0, "duration_seconds": 197.0}
```

---

## Configuration

`config.json`:
```json
{
    "temp_dir": "/home/user/tmp/brief-performance-testing",
    "manifest_path": "performance-testing/results/manifest.jsonl",
    "max_workers": 2,
    "defaults": {
        "max_turns": 25,
        "max_budget": 2.0,
        "timeout": 600
    },
    "cleanup": {
        "keep_work_dirs": true,
        "keep_stdout": true,
        "keep_stderr": true
    }
}
```

---

## Repo Isolation

Each job gets a proper git clone:
- `git clone <repo_path> <temp_dir>/<job_id>/` creates a real `.git` directory
- Claude Code detects the clone as a standalone project
- No path traversal to parent repos
- Each agent operates in complete isolation

This solves the previous issue where test environments nested inside the main repo caused Claude Code to find the parent `.git` and operate on the main repo's files.

---

## Usage from Test Script

```python
from orchestrator import ClaudeOrchestrator, ClaudeJob

# Create orchestrator
orch = ClaudeOrchestrator(
    temp_dir="/home/user/tmp/brief-performance-testing",
    manifest_path="performance-testing/results/manifest.jsonl",
    max_workers=2,
)

# Queue jobs
orch.add_job(ClaudeJob(
    job_id="baseline-no-hooks__feature-addition",
    prompt="Add a logs archive command...",
    repo_path="/home/user/dev/brief",
    claude_md_source="performance-testing/test-files/claude-md-null.md",
    settings_json={"hooks": {}},
    setup_fn=setup_brief_context,  # copies .brief/ data
    metadata={"config": "baseline-no-hooks", "dimension": "feature-addition"},
))

# Run all
entries = orch.run()

# Analyze later
from analyze import analyze_results
analyze_results("performance-testing/results/manifest.jsonl")
```

---

## Status Output

While running:
```
[Orchestrator] Workers: 2/2 | Queue: 45 | Done: 14 | Failed: 2
  W1: null-pretool__feature-addition (3m12s) pid=12345
  W2: null-pretool__multi-task (1m45s) pid=12346
```

---

## Future Extensions

- **Remote execution**: Run on remote machines via SSH
- **Result caching**: Skip jobs that already have completed entries in manifest
- **Retry logic**: Re-queue failed jobs with backoff
- **Webhook notifications**: POST to URL on completion
- **Cost tracking**: Parse API usage from Claude output
