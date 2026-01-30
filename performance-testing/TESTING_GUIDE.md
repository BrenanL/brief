# Testing Guide

How to run Brief performance tests and interpret results.

## Prerequisites

1. Ensure Brief is set up with context data:
   ```bash
   source .venv/bin/activate
   brief analyze refresh
   brief describe batch --limit 100 --include-other
   ```

2. Commit any changes you want tested (tests clone from HEAD):
   ```bash
   git add -A && git commit -m "prepare for test run"
   ```

3. Verify the temp directory exists:
   ```bash
   mkdir -p /home/user/tmp/brief-performance-testing
   ```

## Running Tests

### Full Test Suite

Run all 7 configs across all 9 dimensions (63 tests):

```bash
python performance-testing/run_test.py run --configs all --dimensions all
```

### Targeted Testing

Run specific configs or dimensions:

```bash
# Compare null vs baseline with no hooks
python performance-testing/run_test.py run \
  --configs null-no-hooks baseline-no-hooks \
  --dimensions feature-addition bug-investigation

# Test a single config across all dimensions
python performance-testing/run_test.py run \
  --configs baseline-pretool \
  --dimensions all
```

### Configuration

Edit `config.json` to adjust defaults:

```json
{
    "temp_dir": "/home/user/tmp/brief-performance-testing",
    "manifest_path": "performance-testing/results/manifest.jsonl",
    "max_workers": 2,
    "defaults": {
        "max_turns": 25,
        "max_budget": 2.0,
        "timeout": 600
    }
}
```

Override per-run:

```bash
python performance-testing/run_test.py run \
  --configs all --dimensions all \
  --workers 3 --max-turns 30 --max-budget 3.0
```

### Monitoring

While tests run, the orchestrator prints live status:

```
[19:33:21] Started: null-pretool__feature-addition (pid=12345)
[Orchestrator] Workers: 2/2 | Queue: 45 | Done: 14 | Failed: 2
  W1: null-pretool__feature-addition (3m12s) pid=12345
  W2: null-pretool__multi-task (1m45s) pid=12346
```

### Interrupting

Press Ctrl-C to gracefully stop. The orchestrator will:
1. Stop dequeuing new jobs
2. Send SIGTERM to active processes
3. Wait 5 seconds, then SIGKILL
4. Update manifest with `status=killed`

Remaining queued jobs stay in the manifest as `status=queued`.

## Analyzing Results

### Basic Analysis

```bash
# Use default manifest
python performance-testing/analyze.py

# Specify manifest
python performance-testing/analyze.py performance-testing/results/manifest.jsonl
```

Output includes:
- **By Configuration**: Average Brief ratio per config
- **By Dimension**: Average Brief ratio per dimension
- **Variable Isolation**: CLAUDE.md impact and hook impact analysis

### Full Matrix

```bash
python performance-testing/analyze.py --matrix
```

Shows Brief ratio for every config x dimension combination.

### Job Detail

```bash
python performance-testing/analyze.py --detail baseline-pretool__feature-addition
```

Shows full tool counts, metrics, and file paths for one job.

### Including Voided Tests

By default, voided tests are excluded from analysis. To include them:

```bash
python performance-testing/analyze.py --include-voided
```

### Annotating Tests

Mark tests as voided, flagged, or add notes without deleting data:

```bash
# Void a test (excludes from analysis)
python performance-testing/analyze.py annotate <job-id> --void

# Flag a test (e.g. compromised, review)
python performance-testing/analyze.py annotate <job-id> --flag compromised

# Add a note
python performance-testing/analyze.py annotate <job-id> --note "venv was missing during this run"

# Combine
python performance-testing/analyze.py annotate <job-id> --void --flag development --note "test run"
```

Job IDs support prefix matching — you don't need the full timestamp suffix.

## Key Metrics

### Brief Ratio

```
Brief Ratio = context_get_calls / (context_get_calls + Read + Grep + Glob)
```

| Ratio | Interpretation |
|-------|----------------|
| > 0.5 | Excellent - agent prefers Brief |
| 0.3 - 0.5 | Good - balanced usage |
| 0.1 - 0.3 | Moderate - room for improvement |
| < 0.1 | Poor - agent ignoring Brief |

### What to Look For

1. **CLAUDE.md impact**: Compare `null-*` vs `baseline-*` configs with same hooks
2. **Hook impact**: Compare configs with same CLAUDE.md but different hooks
3. **Dimension patterns**: Which task types benefit most from Brief guidance?
4. **Degradation**: Does Brief ratio decline in multi-task or resume scenarios?

## Repo Isolation

Each test runs in a `git clone` of the project at `/home/user/tmp/brief-performance-testing/`.
This ensures:
- Each agent has its own `.git` directory
- No file changes leak to the main repo
- Claude Code treats each clone as a standalone project

Work directories persist after tests for inspection:

```bash
# See what an agent did
ls /home/user/tmp/brief-performance-testing/baseline-pretool__feature-addition/
git -C /home/user/tmp/brief-performance-testing/baseline-pretool__feature-addition/ diff

# Read the Claude output
cat /home/user/tmp/brief-performance-testing/baseline-pretool__feature-addition/stdout.jsonl
```

## Manifest Format

Results are tracked in `performance-testing/results/manifest.jsonl` (append-only JSONL).
Each status change appends a new line. Latest entry per job_id is the truth.

```bash
# See all jobs and their status
cat performance-testing/results/manifest.jsonl | python3 -c "
import json, sys
seen = {}
for line in sys.stdin:
    e = json.loads(line)
    seen[e['job_id']] = e['status']
for jid, status in sorted(seen.items()):
    print(f'{status:12} {jid}')
"
```

## Cleanup

```bash
# Remove all test work directories
rm -rf /home/user/tmp/brief-performance-testing/*

# Clear manifest to start fresh
rm performance-testing/results/manifest.jsonl
```

## Testing the Orchestrator

Run the orchestrator's own tests:

```bash
python performance-testing/test_orchestrator.py
```

This tests:
- Repo isolation (git clone, .git exists, toplevel correct)
- Environment setup (CLAUDE.md override, settings.json)
- Custom setup functions
- Manifest tracking
- Hello-world Claude run
- Parallel execution
- No main repo contamination
