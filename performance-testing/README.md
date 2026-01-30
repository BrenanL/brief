# Brief Performance Testing

Tools and infrastructure for testing Brief's effectiveness at guiding AI agents to use structured context tools.

## Architecture

| File | Purpose |
|------|---------|
| `orchestrator.py` | General-purpose Claude Code run orchestrator |
| `run_test.py` | Brief-specific test definitions and job generation |
| `analyze.py` | Post-run analysis and comparison reports |
| `config.json` | Orchestrator configuration (temp dir, workers, defaults) |
| `test_orchestrator.py` | Tests for the orchestrator itself |

### Documentation

| File | Purpose |
|------|---------|
| `PERFORMANCE_TESTING_PLAN.md` | Testing strategy, dimensions, and config matrix |
| `ORCHESTRATOR_DESIGN.md` | Orchestrator architecture and design |
| `TESTING_GUIDE.md` | How to run tests and interpret results |

### Test Files

| File | Purpose |
|------|---------|
| `test-files/claude-md-null.md` | CLAUDE.md with no Brief references (control) |
| `test-files/claude-md-baseline.md` | Original CLAUDE.md with Brief workflow instructions |

## Quick Start

```bash
# List available configurations and dimensions
python performance-testing/run_test.py list-configs
python performance-testing/run_test.py list-dimensions

# Run tests with sonnet (configs x dimensions)
python performance-testing/run_test.py run --configs all --dimensions all --model sonnet

# Run specific subset
python performance-testing/run_test.py run --configs baseline-pretool baseline-full-hooks --dimensions feature-addition bug-investigation --model sonnet

# Run with custom parallelism
python performance-testing/run_test.py run --configs all --dimensions all --model sonnet --workers 3

# Analyze results
python performance-testing/analyze.py
python performance-testing/analyze.py --matrix   # Full config x dimension matrix
python performance-testing/analyze.py --detail job-id  # Detail for one run
```

## Test Configurations (7)

| Config | CLAUDE.md | Hooks | Purpose |
|--------|-----------|-------|---------|
| `null-no-hooks` | Null | None | True control |
| `null-pretool` | Null | PreToolUse | Isolate PreToolUse |
| `null-userprompt` | Null | UserPromptSubmit | Isolate UserPromptSubmit |
| `null-full-hooks` | Null | Full suite | Hooks without docs |
| `baseline-no-hooks` | Baseline | None | Isolate docs impact |
| `baseline-pretool` | Baseline | PreToolUse | Original base case |
| `baseline-full-hooks` | Baseline | Full suite | Maximum guidance |

## Test Dimensions (9)

| Dimension | Type | Signal |
|-----------|------|--------|
| feature-addition | Greenfield impl | Does agent Brief before writing? |
| multi-task | Sequential tasks | Does Brief usage persist? |
| resume | Resume behavior | Does agent use `brief resume`? |
| feature-extension | Extend existing | Brief-first or Read-first? |
| bug-investigation | Pure exploration | Brief vs grep/read chains |
| cross-cutting | Add to all | Discovery method |
| integration | Connect X to Y | Multi-area exploration |
| pattern-following | Follow patterns | Uses Brief for exemplars? |
| documentation | Explain/document | Brief descriptions or from scratch? |

## Model Selection

By default, Claude Code picks the model (Opus for main agent, Haiku for subagents). Use `--model` to set the main agent model explicitly:

```bash
python performance-testing/run_test.py run --configs all --dimensions feature-addition --model sonnet --workers 2
```

When `--model` is specified, it's recorded in the manifest metadata for that run. Subagents (Task/Explore) always use Haiku regardless of the main model setting.

Use `sonnet` to stretch your Max plan quota (~5x cheaper than Opus). The tests measure Brief utilization patterns, not code quality, so Sonnet is fine for most runs.

## Rate Limit Handling

The orchestrator automatically detects and recovers from Claude Max plan rate limits. This is always on — no flag needed.

When a rate limit is hit:

1. The completed job is marked `rate_limited` in the manifest (not `failed`)
2. The orchestrator stops launching new jobs
3. Any other active jobs are allowed to finish
4. The reset time is parsed from the rate limit message
5. The orchestrator sleeps until the reset time + 60s buffer, logging periodic status
6. Rate-limited jobs are re-queued with fresh repo clones
7. Processing resumes normally

This means you can kick off a large run before bed and it will pause/resume through 5-hour rate limit windows automatically.

**Detection**: Claude Code returns exit code 0 on rate limits (known issue). The orchestrator parses `stdout.jsonl` for "you've hit your limit" and similar messages.

**Reset time parsing**: Regex extraction from the message (e.g. "resets Jan 30, 2026, 2am (UTC)"), with an LLM fallback (quick Haiku call) if regex fails, and a conservative 5-hour default as last resort.

**Data preservation**: Rate-limited runs keep their work directories and manifest entries. When re-queued, the old work directory is archived (renamed with timestamp), not deleted.

## Job IDs

Each job gets a unique ID: `{config}__{dimension}__{YYYYMMDD_HHMMSS}`. The timestamp is the batch creation time, so re-running the same config/dimension produces a new ID. This supports running the same test multiple times to increase sample size.

Work directories use the job ID as the folder name. The manifest tracks all runs — use `analyze.py` to aggregate results across repeated runs.

## Running Tests

### Prerequisites

```bash
source .venv/bin/activate
brief analyze refresh
brief describe batch --limit 100 --include-other
mkdir -p /home/user/tmp/brief-performance-testing
```

Commit changes before running (tests clone from HEAD).

### Verify Setup

Run a hello-world test to confirm the orchestrator works:

```bash
python -c "import sys; sys.path.insert(0, 'performance-testing'); from test_orchestrator import test_hello_world_run; test_hello_world_run()"
```

### One Dimension Across All Configs

Run a single dimension against every config (7 tests):

```bash
python performance-testing/run_test.py run --configs all --dimensions feature-addition --workers 1
```

### One Config Across All Dimensions

Run all 9 dimensions for a single config:

```bash
python performance-testing/run_test.py run --configs null-no-hooks --dimensions all --workers 1
```

### Specific Configs and Dimensions

Pick and choose:

```bash
python performance-testing/run_test.py run --configs null-no-hooks baseline-no-hooks --dimensions feature-addition bug-investigation --workers 1
```

### A Few Dimensions Across All Configs

Run 3-4 selected dimensions against every config:

```bash
python performance-testing/run_test.py run --configs all --dimensions feature-addition bug-investigation feature-extension cross-cutting --workers 2
```

### Full Suite

All 7 configs x 9 dimensions = 63 tests:

```bash
python performance-testing/run_test.py run --configs all --dimensions all --workers 2
```

### Incremental Testing Workflow

Recommended order for building confidence before committing to a full run:

```bash
# 1. Verify orchestrator works
python -c "import sys; sys.path.insert(0, 'performance-testing'); from test_orchestrator import test_hello_world_run; test_hello_world_run()"

# 2. Single test (one config, one dimension)
python performance-testing/run_test.py run --configs null-no-hooks --dimensions feature-addition --workers 1

# 3. Check that result
python performance-testing/analyze.py

# 4. Same dimension across all configs
python performance-testing/run_test.py run --configs null-pretool null-userprompt null-full-hooks baseline-no-hooks baseline-pretool baseline-full-hooks --dimensions feature-addition --workers 2

# 5. Check comparative results
python performance-testing/analyze.py

# 6. A few more dimensions across all configs
python performance-testing/run_test.py run --configs all --dimensions bug-investigation feature-extension cross-cutting --workers 2

# 7. Check results with matrix view
python performance-testing/analyze.py --matrix

# 8. Remaining dimensions
python performance-testing/run_test.py run --configs all --dimensions multi-task resume integration pattern-following documentation --workers 2

# 9. Full analysis
python performance-testing/analyze.py --matrix
```

### Analyzing Results

```bash
python performance-testing/analyze.py                          # Summary by config and dimension
python performance-testing/analyze.py --matrix                 # Full config x dimension matrix
python performance-testing/analyze.py --detail null-no-hooks__feature-addition  # One job in detail
```

### Inspecting a Test Run

Work directories persist at `/home/user/tmp/brief-performance-testing/`:

```bash
# See what the agent changed
git -C /home/user/tmp/brief-performance-testing/null-no-hooks__feature-addition/ diff --stat

# Read the raw Claude output
cat /home/user/tmp/brief-performance-testing/null-no-hooks__feature-addition/stdout.jsonl

# Check stderr
cat /home/user/tmp/brief-performance-testing/null-no-hooks__feature-addition/stderr.log
```

### Cleanup

```bash
# Remove all test work directories
rm -rf /home/user/tmp/brief-performance-testing/*

# Manifest is append-only — old entries are superseded by re-runs, never delete it
```

## How It Works

1. **`run_test.py`** generates `ClaudeJob` instances for each config x dimension combo, with unique timestamped IDs
2. **`orchestrator.py`** manages the queue:
   - `git clone` to `/home/user/tmp/brief-performance-testing/` (proper isolation)
   - Apply CLAUDE.md, hooks, and Brief context data
   - Run `claude -p` with worker pool
   - Track everything in JSONL manifest
   - Detect rate limits, sleep until reset, re-queue and resume
3. **`analyze.py`** reads the manifest and Claude outputs to generate comparison reports
