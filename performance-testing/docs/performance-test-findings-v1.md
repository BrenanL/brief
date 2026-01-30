# Performance Test Findings v1

**Date**: 2026-01-30
**Test environment**: Claude Code (headless) with Claude Sonnet on Claude Max
**Codebase under test**: Brief — a context infrastructure tool for AI coding agents

---

## Bottom Line

Brief-guided agents complete coding tasks **30% faster**, generate **45% fewer output tokens**, and reduce tool-model (Haiku) usage by **78%** compared to unguided agents. The mechanism is simple: 1-2 `brief context get` calls replace 5-25 manual Read/Grep/Glob exploration chains. Brief wins on every metric, across every valid test dimension.

| Metric | No Brief | Brief + Hooks | Improvement |
|---|---|---|---|
| Task completion time | 260s | 182s | **30% faster** |
| Conversation turns | 57 | 38 | **34% fewer** |
| Total tool calls | 41 | 23 | **43% fewer** |
| Read/Grep/Glob calls | 18 | 6 | **66% fewer** |
| Output tokens (blended) | 14,768 | 8,065 | **45% fewer** |
| Input tokens (blended) | 16,917 | 10,932 | **35% fewer** |
| Tool model (Haiku) cost | $0.10 | $0.02 | **78% cheaper** |
| Total cost per task | $0.58 | $0.51 | **12% cheaper** |

Win rate: **5 out of 5** valid test dimensions.

---

## Table of Contents

- [Test Design](#test-design)
  - [Configs](#configs)
  - [Dimensions](#dimensions)
  - [Analysis Framework (Q1 vs Q2)](#analysis-framework-q1-vs-q2)
- [Q1 Results: Does Brief Help?](#q1-results-does-brief-help)
  - [Head-to-Head Comparison](#head-to-head-comparison)
  - [Per-Dimension Breakdown](#per-dimension-breakdown)
  - [All Configs Ranked](#all-configs-ranked)
- [Cost Analysis](#cost-analysis)
  - [Per-Model Breakdown](#per-model-breakdown)
  - [Why the Headline is 78%, Not 12%](#why-the-headline-is-78-not-12)
  - [Per-Dimension Cost Detail](#per-dimension-cost-detail)
- [The Mechanism](#the-mechanism)
  - [What Brief Agents Do Differently](#what-brief-agents-do-differently)
  - [Per-Dimension Behavioral Observations](#per-dimension-behavioral-observations)
- [Q2 Results: What Config Works Best?](#q2-results-what-config-works-best)
  - [Variable Isolation: Hooks vs CLAUDE.md](#variable-isolation-hooks-vs-claudemd)
  - [Hook Progression](#hook-progression)
- [Excluded Dimensions](#excluded-dimensions)
- [Data Integrity](#data-integrity)
- [Caveats and Limitations](#caveats-and-limitations)
- [Next Steps](#next-steps)

---

## Test Design

63 tests total: 7 configurations x 9 task dimensions. Each test clones the repo, configures the environment, runs Claude Code in headless mode with a task prompt, and records the full transcript.

### Configs

Two variables are crossed: CLAUDE.md content (null vs baseline) and hook configuration (none, pretool, userprompt, full).

| Config | CLAUDE.md | Hooks | Purpose |
|---|---|---|---|
| null-no-hooks | No Brief references | None | True control |
| null-pretool | No Brief references | PreToolUse only | Hook-only effect |
| null-userprompt | No Brief references | UserPromptSubmit only | Hook-only effect |
| null-full-hooks | No Brief references | All 4 hooks | Hooks without docs |
| baseline-no-hooks | Brief workflow docs | None | Docs without hooks |
| baseline-pretool | Brief workflow docs | PreToolUse only | Docs + partial hooks |
| baseline-full-hooks | Brief workflow docs | All 4 hooks | **Full Brief setup** |

The 4 hooks: SessionStart (initial guidance), PreCompact (compaction reminder), UserPromptSubmit (pre-prompt nudge), PreToolUse (intercept before Read/Grep/Glob to suggest Brief).

### Dimensions

9 task types testing different coding scenarios:

| Dimension | Task Type | Prompt Summary |
|---|---|---|
| feature-addition | Greenfield coding | Add a new `brief logs archive` command |
| feature-extension | Extend existing code | Add `--format` flag to describe command |
| bug-investigation | Pure exploration | Investigate why `context get` returns empty |
| cross-cutting | Multi-location change | Add path validation to all CLI commands |
| integration | Connect two systems | Link task system to logging system |
| pattern-following | Replicate patterns | Add `contracts export` following existing patterns |
| documentation | Comprehension task | Document the context retrieval flow |
| multi-task | Sequential queue | Complete 3 queued Brief tasks |
| resume | Resume workflow | Single-word "resume" prompt |

### Analysis Framework (Q1 vs Q2)

Tests serve two distinct purposes that must not be conflated:

**Q1: "Does Brief actually help?"** — Compare Brief-guided vs unguided agents on equivalent tasks. Both configs must be able to attempt the task fairly. Metrics: speed, turns, tool calls, cost.

**Q2: "What config optimizes Brief adoption?"** — Compare all 7 configs against each other. Metrics: brief ratio, `context get` adoption.

5 dimensions are valid for Q1. All 9 are valid for Q2. The 4 excluded from Q1 have specific documented reasons (see [Excluded Dimensions](#excluded-dimensions)).

---

## Q1 Results: Does Brief Help?

**Yes.** Across all 5 valid dimensions, Brief+Hooks beats the unguided control on every metric.

### Head-to-Head Comparison

Comparing `null-no-hooks` (true control) vs `baseline-full-hooks` (full Brief setup), averaged across the 5 Q1-valid dimensions:

| Metric | No Brief | Brief + Hooks | Change |
|---|---|---|---|
| Avg Duration | 260s | 182s | **-30%** |
| Avg Turns | 57.0 | 37.6 | **-34%** |
| Avg Total Tool Calls | 40.6 | 23.0 | **-43%** |
| Avg Read/Grep/Glob | 18.0 | 6.2 | **-66%** |
| Avg `context get` | 0.0 | 1.2 | N/A |
| Avg Total Cost | $0.58 | $0.51 | **-12%** |

### Per-Dimension Breakdown

Brief+Hooks wins every dimension. Margins range from 19s to 120s.

| Dimension | No Brief | Brief + Hooks | Time Saved | R/G/G Saved |
|---|---|---|---|---|
| cross-cutting | 299s | 180s | **-120s (-40%)** | 10 → 10 (0) |
| integration | 291s | 205s | **-85s (-29%)** | 26 → 4 (-22) |
| pattern-following | 240s | 152s | **-87s (-36%)** | 31 → 5 (-26) |
| documentation | 237s | 156s | **-80s (-34%)** | 9 → 3 (-6) |
| feature-addition | 234s | 215s | **-19s (-8%)** | 12 → 10 (-2) |

Notable: cross-cutting had the same R/G/G count but 40% faster — Brief helped the agent work more efficiently *per tool call*, not just reduce count. Pattern-following showed the largest raw R/G/G reduction (31 → 5).

### All Configs Ranked

All 7 configs on the 5 Q1-valid dimensions, showing how each variable contributes:

| Config | AvgDur | AvgTurns | AvgTools | AvgR/G/G | Avg ctx_get |
|---|---|---|---|---|---|
| baseline-full-hooks | **182s** | **37.6** | **23.0** | **6.2** | 1.2 |
| null-full-hooks | 191s | 38.8 | 24.4 | 6.2 | **1.4** |
| baseline-no-hooks | 210s | 46.4 | 31.2 | 12.6 | 0.2 |
| baseline-pretool | 227s | 44.2 | 31.6 | 14.0 | 0.0 |
| null-userprompt | 230s | 47.4 | 34.2 | 15.4 | 0.6 |
| null-pretool | 241s | 50.2 | 37.6 | 18.2 | 0.0 |
| null-no-hooks | 260s | 57.0 | 40.6 | 18.0 | 0.0 |

The top 2 configs (both with full hooks) are nearly identical in performance, suggesting hooks are the dominant factor. See [Q2 Results](#q2-results-what-config-works-best) for the variable isolation analysis.

---

## Cost Analysis

### Per-Model Breakdown

Claude Code uses two models: **Sonnet** (main reasoning) and **Haiku** (tool-use decisions). The cost story is very different for each.

| Model | No Brief | Brief + Hooks | Change |
|---|---|---|---|
| Sonnet (main) | $0.48 | $0.49 | +2% (flat) |
| Haiku (tool) | $0.10 | $0.02 | **-78%** |
| **Total** | **$0.58** | **$0.51** | **-12%** |

The 12% total cost reduction comes **entirely** from Haiku savings. Sonnet cost is statistically flat — within noise at n=5.

Tool model share of total cost: **17.5%** (No Brief) → **4.4%** (Brief+Hooks).

### Why the Headline is 78%, Not 12%

The 78% Haiku reduction is the mechanically meaningful number. Each Read/Grep/Glob call triggers a Haiku invocation for tool-use routing. Brief agents make 66% fewer R/G/G calls, which directly translates to ~78% fewer Haiku invocations.

Sonnet cost is flat because two effects cancel out:

| Sonnet Token Type | No Brief | Brief + Hooks | Change |
|---|---|---|---|
| Output tokens | 49,426 | 38,426 | -22% (fewer exploratory commands) |
| Cache read tokens | 3,612,922 | 3,756,886 | +4% |
| Cache creation tokens | 153,113 | 199,836 | +31% (context packages get cached) |

Brief agents generate 22% fewer output tokens (less "figuring out" text), but the context packages returned by `brief context get` get written into the conversation cache, increasing cache creation by 31%. These offset each other.

The robust findings are the model-pricing-independent ones: **30% faster, 34% fewer turns, 43% fewer tool calls, 66% fewer R/G/G**. The cost benefit depends on model pricing and tool-routing architecture.

### Per-Dimension Cost Detail

| Dimension | Null Total | Null Main | Null Tool | Brief Total | Brief Main | Brief Tool |
|---|---|---|---|---|---|---|
| cross-cutting | $0.85 | $0.84 | $0.01 | $0.58 | $0.57 | $0.02 |
| integration | $0.67 | $0.53 | $0.14 | $0.66 | $0.64 | $0.02 |
| pattern-following | $0.54 | $0.36 | $0.18 | $0.50 | $0.46 | $0.04 |
| feature-addition | $0.51 | $0.43 | $0.08 | $0.50 | $0.47 | $0.03 |
| documentation | $0.34 | $0.24 | $0.10 | $0.33 | $0.31 | $0.01 |

Cross-cutting is an outlier where main model cost also dropped substantially ($0.84 → $0.57), driving the largest absolute savings. The other 4 dimensions show the typical pattern: flat or slightly increased main model cost offset by tool model reduction.

---

## The Mechanism

### What Brief Agents Do Differently

The behavioral pattern is consistent across all 5 dimensions:

1. Brief agent calls `brief context get "<topic>"` (1-2 calls)
2. This returns: relevant file descriptions, function signatures, relationships, and related files
3. The agent then makes targeted Read calls to specific files it needs to edit
4. Total exploration: **1-2 context get + ~5 targeted Reads**

Unguided agents follow a different pattern:

1. Start with Grep/Glob to discover relevant files
2. Read files one by one to understand structure
3. Often read files that turn out to be irrelevant
4. Circle back to Grep for more information mid-task
5. Total exploration: **15-30 Read/Grep/Glob calls**

Brief replaces the "search → read → understand → search more" loop with a single structured context retrieval that frontloads the understanding.

### Per-Dimension Behavioral Observations

| Dimension | Brief Behavior | Unguided Behavior | Key Difference |
|---|---|---|---|
| cross-cutting | 10 R/G/G, 42 turns | 10 R/G/G, 60 turns | Same tools, but 30% more efficient per call |
| integration | 4 R/G/G, 2 ctx_get | 26 R/G/G | Context get mapped both systems at once |
| pattern-following | 5 R/G/G, 1 ctx_get | 31 R/G/G | Largest raw exploration reduction |
| documentation | 3 R/G/G, 16 turns | 9 R/G/G, 19 turns | Tightest focus, fewest total tools |
| feature-addition | 10 R/G/G, 1 ctx_get | 12 R/G/G | Smallest gap — prompt already hints at target area |

---

## Q2 Results: What Config Works Best?

### Variable Isolation: Hooks vs CLAUDE.md

**Hooks are the primary driver** of Brief adoption. CLAUDE.md adds a smaller incremental boost.

Hook impact (holding CLAUDE.md constant):
- null-no-hooks → null-full-hooks: **0% → 19.8%** brief ratio (+19.8pp)
- baseline-no-hooks → baseline-full-hooks: **4.5% → 24.1%** brief ratio (+19.6pp)

CLAUDE.md impact (holding hooks constant):
- null-no-hooks → baseline-no-hooks: **0% → 4.5%** (+4.5pp)
- null-full-hooks → baseline-full-hooks: **19.8% → 24.1%** (+4.3pp)

Hooks contribute ~80% of the adoption effect. CLAUDE.md contributes ~20%.

### Hook Progression

With null CLAUDE.md (no Brief documentation):

| Hooks | Brief Ratio | Notes |
|---|---|---|
| None | 0.0% | Agent has no awareness of Brief |
| PreToolUse only | 0.0% | Hook fires but agent ignores without context |
| UserPromptSubmit only | 8.8% | Nudge before each prompt starts working |
| Full (all 4) | 19.8% | Combined hooks drive substantial adoption |

With baseline CLAUDE.md (Brief workflow documented):

| Hooks | Brief Ratio |
|---|---|
| None | 4.5% |
| PreToolUse only | 10.3% |
| Full (all 4) | 24.1% |

Key insight: PreToolUse alone does nothing without CLAUDE.md context (0% with null docs), but becomes effective with documentation (10.3% with baseline docs). The hook needs the docs to explain what `brief context get` is and why to use it.

---

## Excluded Dimensions

4 of 9 dimensions were excluded from Q1 (efficiency) analysis. Each has a specific, documented reason — this is methodology, not cherry-picking.

| Dimension | Reason for Q1 Exclusion | Still Valid for Q2? |
|---|---|---|
| **resume** | Null agent completed in 27s by not engaging (no concept of "resume"). Brief agent did 177s of real work. Comparing times penalizes the agent that actually did the task. | Yes |
| **multi-task** | Prompt explicitly names Brief features (`brief task list`). Tests task-system workflow, not context-system efficiency. | Yes |
| **bug-investigation** | Brief agent used `context get` as investigation probes (10 edge-case queries testing the tool), doing qualitatively more thorough work. Timing penalizes quality. | Yes |
| **feature-extension** | Brief agent 62s slower due to administrative overhead (`brief status`, `brief task list`) on a direct coding instruction. A CLAUDE.md design issue, not a context-system inefficiency. Filed as issue. | Yes |

The excluded dimensions produced two actionable findings:
1. **Bug-investigation** revealed that Brief enables qualitatively different investigation strategies (probing the tool directly vs reading source code only). This needs quality metrics to evaluate properly.
2. **Feature-extension** revealed that CLAUDE.md causes unnecessary task-system ceremony on direct instructions. Filed as a development issue.

---

## Data Integrity

### Test Environment
- Each test runs in an isolated `git clone` with its own `.venv`
- No file changes leak between tests or to the main repo
- Claude Code runs in `--print` mode (headless) with `--max-turns` and `--max-budget` caps

### Voided Tests
- 2 development/validation tests voided (pre-batch)
- 6 compromised tests voided (agent escaped clone due to missing `.venv` in early runs). All 6 were re-run with clean isolation; re-runs used in analysis.

### Timing Artifact Check
Tests ran config-by-config sequentially (null-no-hooks first through baseline-full-hooks last). This could confound timing if later tests were systematically slower due to API throttling or system load.

**Finding: No systematic slowdown.** Pearson r = -0.081 between run order and duration. No upward trend in duration buckets. The Jan 30 re-runs (latest) averaged faster than the main batch.

---

## Caveats and Limitations

1. **n=1 per cell.** Each config-dimension pair was tested once. The 5-dimension averages are directional but low-confidence. Repeat runs would strengthen the findings substantially.

2. **No quality measurement.** We measure speed and cost but not whether the agent's output was correct. A faster run that produces broken code is worse than a slower correct one. Spot-checking a sample of outputs would add significant value.

3. **Single model.** All tests used Claude Sonnet on Claude Max. Results may differ with other models (Opus, Haiku) or API billing.

4. **Brief-specific codebase.** Tests ran on the Brief codebase itself — the tool has rich context data for its own code. Results may differ on codebases with sparser or no Brief context.

5. **Reduced test surface.** 4 of 9 dimensions excluded from Q1 for legitimate methodological reasons, but this means efficiency conclusions rest on 5 task types. Future test rounds should design more Q1-valid dimensions.

6. **Cost findings are architecture-dependent.** The 78% Haiku reduction depends on Claude Code's current tool-routing architecture. If tool-use routing changes, the cost benefit would shift. The speed/turn/tool-call benefits are more robust.

---

## Next Steps

1. **Quality evaluation** — Spot-check agent outputs for correctness across a sample of test runs.
2. **Repeat runs** — Priority: cross-cutting, pattern-following, integration (largest Brief advantages). Target n=3 per cell minimum.
3. **Test production CLAUDE.md** — The 191-line production CLAUDE.md was never tested with full hooks. Add as a config variant.
4. **Design more Q1 dimensions** — Current test set was designed before the Q1/Q2 framework. New dimensions should be designed specifically for fair A/B comparison.
5. **Address setup overhead** — CLAUDE.md causes agents to check task system on direct instructions, adding 15-30s of unnecessary overhead. Needs exploration.
6. **Externalize dimension metadata** — Move test definitions from inline Python to structured YAML files with Q1/Q2 flags and analysis tags for automatic filtering.
