# Brief Performance Testing

This folder contains documentation and tools for testing Brief's effectiveness at guiding AI agents to use structured context tools.

## Contents

| File | Description |
|------|-------------|
| `TEST_RESULTS.md` | Results from A/B testing across all configurations |
| `TESTING_GUIDE.md` | How to run tests and interpret results |
| `configs/baseline.md` | Baseline configuration (no hooks, minimal CLAUDE.md) |
| `configs/hooks-v1.md` | Original setup (verbose CLAUDE.md + UserPromptSubmit hook) |
| `configs/hooks-v2.md` | Full hook suite (4 hooks + streamlined CLAUDE.md) |

## Quick Summary

Testing shows that Brief guidance dramatically improves agent behavior:

| Metric | baseline | hooks-v1 | hooks-v2 |
|--------|----------|----------|----------|
| Brief Ratio | 0% | **83.3%** | 61.1% |
| Read/Grep/Glob calls | 35 | **2** | 8 |
| Avg completion time | 60.9s | **21.3s** | 36.9s |

**Key finding**: Verbose CLAUDE.md + simple hook (hooks-v1) outperformed the full hook suite (hooks-v2).

## Running Tests

```bash
# Compare all three configurations
python performance-testing/run_test.py \
  --compare baseline hooks-v1 hooks-v2 \
  --task "Explain how the task management system works"

# Compare specific configs
python performance-testing/run_test.py \
  --compare baseline hooks-v1 \
  --task "Find where file descriptions are stored"

# See all options
python performance-testing/run_test.py --help
```

## Test Output Location

Raw test outputs are saved to `.brief-logs/test-runs/` (not in this folder).
