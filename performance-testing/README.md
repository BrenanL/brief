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

# Run tests (configs x dimensions)
python performance-testing/run_test.py run --configs all --dimensions all

# Run specific subset
python performance-testing/run_test.py run \
  --configs baseline-pretool baseline-full-hooks \
  --dimensions feature-addition bug-investigation

# Run with custom parallelism
python performance-testing/run_test.py run --configs all --dimensions all --workers 3

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

## How It Works

1. **`run_test.py`** generates `ClaudeJob` instances for each config x dimension combo
2. **`orchestrator.py`** manages the queue:
   - `git clone` to `/home/user/tmp/brief-performance-testing/` (proper isolation)
   - Apply CLAUDE.md, hooks, and Brief context data
   - Run `claude -p` with worker pool
   - Track everything in JSONL manifest
3. **`analyze.py`** reads the manifest and Claude outputs to generate comparison reports
