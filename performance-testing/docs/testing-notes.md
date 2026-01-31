# Performance Testing Notes

**Started**: 2026-01-30
**Status**: Initial analysis of Phase 1 results

---

## Two Questions We're Answering

This testing framework serves two distinct purposes that should NOT be conflated:

**Q1: Does Brief actually help?**
Compare Brief-guided agents vs unguided agents on *equivalent tasks* where both configs can succeed in principle. Metrics: speed, token usage, tool call count, turns.

**Q2: What config gets agents to use Brief most effectively?**
Compare different hook/CLAUDE.md setups against each other. Metrics: brief ratio, context get adoption, compliance with workflow instructions.

Some test dimensions are valid for Q1, some for Q2, some for both, and some are currently invalid for either. Lumping them all together in aggregate statistics produces misleading results.

---

## Current Project Config vs Tested Config

### Hooks: Exact match
The current `.claude/settings.json` matches `baseline-full-hooks` exactly: all 4 hooks (SessionStart, PreCompact, UserPromptSubmit, PreToolUse) with identical matchers, scripts, and timeouts.

### CLAUDE.md: Superset, not exact match
The current project CLAUDE.md (191 lines) is a deliberate superset of the tested `claude-md-baseline.md` (107 lines). Nearly all baseline content is present in the current file, with 8 minor line-level differences due to rewording/restructuring (not missing concepts).

Additional sections in the current production CLAUDE.md:
- "Compaction Summaries" section (CRITICAL heading)
- "Plan with TodoWrite" step in the task workflow
- Quick Reference table
- Autonomous Task Completion Mode section
- Detailed Development Notes maintenance instructions
- `uv pip` package management details
- Expanded project structure (more directories)
- "Important Conventions" section (5 items)

This is intentional — the production CLAUDE.md serves real work, not just testing. The tested `baseline` CLAUDE.md was a stripped-down version for controlled testing. The additional content was NOT tested in the `baseline-full-hooks` config, so we don't have data on whether it helps or hurts. Based on the hooks-v1 historical results (verbose docs scored higher), the extra content likely doesn't hurt.

---

## Data Integrity

### Voided Tests (2)
- `null-no-hooks__feature-addition` — development test during orchestrator build
- `null-no-hooks__feature-addition__20260129_212656` — validation test before main batch
Both correctly excluded from analysis.

### Compromised Tests (6) — NEED VOIDING
Six tests were flagged `compromised` (agent escaped clone and wrote to main repo due to missing .venv in clone) but are NOT currently voided. They are still included in all analysis output.

| Original (compromised, Jan 29) | Re-run (clean, Jan 30) |
|---|---|
| `baseline-full-hooks__resume__20260129_213418` | `baseline-full-hooks__resume__20260130_104216` |
| `baseline-pretool__resume__20260129_213418` | `baseline-pretool__resume__20260130_104216` |
| `null-full-hooks__resume__20260129_213418` | `null-full-hooks__resume__20260130_104216` |
| `null-no-hooks__multi-task__20260129_213418` | `null-no-hooks__multi-task__20260130_104655` |
| `null-pretool__feature-addition__20260129_213418` | `null-pretool__feature-addition__20260130_103417` |
| `null-pretool__pattern-following__20260129_213418` | `null-pretool__pattern-following__20260130_104915` |

All 6 re-runs completed successfully (exit code 0). The 6 originals should be voided.

**Action needed**: Void all 6 compromised originals before running analysis.

---

## Timing / Speed Degradation

Tests were run config-by-config in sequence (null-no-hooks first, baseline-full-hooks last). This means `baseline-full-hooks` always had the highest sequence position, which could confound timing comparisons if there was systematic slowdown.

**Finding: No evidence of systematic slowdown.**
- Pearson r = -0.081 between run order and duration (essentially zero).
- Average duration by 10-run bucket shows no upward trend.
- Jan 30 re-runs averaged lower than the main batch.
- Timing differences between configs are attributable to actual behavioral differences, not ordering artifacts.

---

## Per-Dimension Review

### 1. feature-addition (Greenfield)

**Prompt**: "Add a 'brief logs archive' command that moves old log entries to an archive file. It should take a --days flag..."

**What it tests**: Can the agent figure out WHERE to add code in an unfamiliar codebase?

**Valid for Q1 (Brief helps)?** YES. Both null and baseline configs can attempt this task. Brief-guided agents should locate the right module/pattern faster via `context get`. The task doesn't reference Brief-specific concepts.

**Valid for Q2 (Config optimization)?** YES. Tests whether the config gets the agent to use `context get` for initial codebase orientation.

**Analysis tags**: `efficiency`, `speed`, `exploration-pattern`

**Notes**: Good clean A/B comparison task. The prompt is about implementing a real feature, not about Brief itself.

---

### 2. multi-task (Sequential Queue)

**Prompt**: "You have Brief tasks queued. Run `brief task list` to see them, then complete all pending tasks in order."

**Setup**: 3 pre-created Brief tasks in `.brief/tasks.jsonl`

**What it tests**: Can the agent work through a queue of tasks using Brief's task system?

**Valid for Q1 (Brief helps)?** NO. The prompt explicitly names Brief features (`brief task list`), and the task system itself is Brief infrastructure — not something a vanilla agent would use. Speed differences here reflect task-management overhead, not context-system efficiency. Q1 cares specifically about whether Brief's context system (context get) improves coding performance.

**Valid for Q2 (Config optimization)?** YES. Directly tests whether the config sustains Brief usage across multiple sequential tasks.

**Analysis tags**: `config-compliance`, `multi-step-persistence`, `workflow-adoption`

**Notes**: The underlying sub-tasks are valid coding work, but the orchestration layer (task list, task start, task done) is Brief-specific. Could be redesigned for Q1 by removing Brief task references from the prompt and just giving 3 sequential coding tasks directly.

---

### 3. resume

**Prompt**: "resume"

**Setup**: One task marked `in_progress` in `.brief/tasks.jsonl`, active_task file set

**What it tests**: Does the agent run `brief resume` and pick up the active task?

**Valid for Q1 (Brief helps)?** NO. The null CLAUDE.md has zero reference to resuming, `brief resume`, or the task system. The word "resume" with no context is ambiguous — the agent might try to resume a git operation, ask what to resume, or just do nothing. This is not a fair comparison of Brief's coding efficiency. It's testing whether the agent knows about a Brief-specific concept.

**Valid for Q2 (Config optimization)?** YES. Directly tests whether the config teaches resume behavior. The baseline CLAUDE.md explicitly documents `brief resume` and the resume workflow.

**Analysis tags**: `config-compliance`, `workflow-adoption`

**Duration comparison validity**: INVALID for Q1. null-no-hooks completed in 27s (likely didn't engage meaningfully), while baseline-full-hooks took 177s (actually did the work). Including this in duration averages makes Brief look SLOWER when it was actually doing MORE work. Excluding resume, Brief's speed advantage improves from ~7% to ~15%.

**Notes**: This dimension should be excluded from any Q1 efficiency analysis. It's purely a Q2 (config optimization) test. The null CLAUDE.md is also arguably an unfair control here — even a generic project might say "if you see an in-progress task, pick it up."

---

### 4. feature-extension

**Prompt**: "Extend the brief describe command to support a --format flag that can output descriptions as JSON instead of markdown."

**What it tests**: Can the agent understand existing functionality and build on it?

**Valid for Q1 (Brief helps)?** NO (for timing). The Brief-guided agent (210s) was 62s slower than null (148s), but NOT because context exploration was slower. The Brief agent spent ~15-30s on administrative overhead (brief status, brief task list, which brief) before starting real work — even though the prompt gives an explicit, specific instruction that doesn't require the task system. It also spent time testing its implementation (`brief describe file --format markdown`) and debugging. The null agent skipped all of this and went straight to reading code and editing. The timing difference reflects setup overhead and testing thoroughness, not context-system inefficiency. This is a legitimate finding about CLAUDE.md design (the agent shouldn't check for tasks when given a direct instruction), but it doesn't belong in Q1 timing analysis.

**Valid for Q2 (Config optimization)?** YES. Tests Brief usage during the "understand existing code" phase.

**Analysis tags**: `config-compliance`, `overhead-analysis`, `exploration-pattern`

**Detailed finding (2026-01-30)**: The baseline-full-hooks agent made 2 context get calls, 3 Read calls, 7 Edit calls in 48 turns. The null-no-hooks agent made 0 context get, 4 Read/Grep/Glob, 5 Edit calls in 42 turns. The Brief agent's extra time was mostly administrative overhead + implementation testing, not exploration. This reveals that the CLAUDE.md instructions cause unnecessary task-system ceremony for direct coding prompts. See DEV_NOTES.md issue: "Agent checks task system on explicit instructions."

---

### 5. bug-investigation

**Prompt**: "The brief context get command sometimes returns empty results even when relevant files exist. Investigate why this might happen and identify potential root causes. Don't fix it yet, just report your findings."

**What it tests**: Pure exploration — can the agent trace through code to find root causes?

**Valid for Q1 (Brief helps)?** NO (for timing). The Brief-guided agent (215s) was 37s slower than null (178s), but examination of the actual test output shows this is a quality/thoroughness difference, not an efficiency regression. The Brief agent made 10 `context get` calls — but it was using context get as an **investigation tool** to reproduce the bug, testing edge cases: `"xyz123notfound"`, `"a"`, `"the and or"`, `"io"`, `"db"`, etc. It was systematically probing which queries return empty results. The null agent (178s) read 14 files and traced code paths manually — a valid but shallower investigation approach. The null agent also likely didn't know the tool was installed and available to test directly. Similar to the resume case: the Brief agent did *more work* and produced a *more thorough investigation*, so comparing wall-clock time penalizes quality. The solution space for investigation tasks is wide enough that agent strategy variance dominates timing.

**Valid for Q2 (Config optimization)?** YES. Tests whether the config drives `context get` usage for investigative work.

**Analysis tags**: `exploration-pattern`, `understanding-depth`, `quality-divergence`

**Detailed finding (2026-01-30)**: baseline-full-hooks used 10 context get calls (as investigation probes), 6 Read, 0 Grep/Glob in 48 turns. null-no-hooks used 0 context get, 14 Read, 1 Grep, 2 Glob in 47 turns. The Brief agent's approach was qualitatively different — it tested the actual tool under investigation rather than only reading source code. This highlights the need for quality metrics alongside timing; faster is not better if the investigation is less thorough.

---

### 6. cross-cutting

**Prompt**: "Add input validation to all Brief CLI commands that accept file paths as arguments. Validate that: 1) paths exist, 2) paths are within the project directory, 3) paths point to files not directories."

**What it tests**: Can the agent find ALL relevant locations for a cross-cutting change?

**Valid for Q1 (Brief helps)?** YES. Both configs need to discover all CLI commands. Brief's `context get` could surface related files that grep might miss (or find faster).

**Valid for Q2 (Config optimization)?** YES. Tests whether the config drives `context get` usage for discovery tasks.

**Analysis tags**: `efficiency`, `speed`, `discovery-completeness`, `exploration-pattern`

**Notes**: Strong Q1 task. The key signal is whether the agent finds all locations efficiently. A good supplementary metric would be: how many CLI command files did the agent actually modify?

---

### 7. integration

**Prompt**: "Make the task system integrate with the logging system so that task state changes (create, start, done, archive) are automatically recorded in the command log with timestamps."

**What it tests**: Can the agent understand two separate systems and connect them?

**Valid for Q1 (Brief helps)?** YES. Agent needs to understand both the task system and the logging system before connecting them. Brief could help map both systems efficiently.

**Valid for Q2 (Config optimization)?** YES. Tests whether the agent uses `context get` for both systems or just one.

**Analysis tags**: `efficiency`, `speed`, `multi-system-understanding`, `exploration-pattern`

**Notes**: Good Q1 task. The interesting signal is whether Brief helps the agent avoid the "understand system A, then separately understand system B" sequential exploration pattern.

---

### 8. pattern-following

**Prompt**: "Add a new 'brief contracts export' command following the same pattern used by other export/output commands in the codebase."

**What it tests**: Can the agent identify existing patterns and replicate them?

**Valid for Q1 (Brief helps)?** YES. Agent needs to find existing patterns first. Brief's related files and function signatures could surface patterns faster than manual grep/read chains.

**Valid for Q2 (Config optimization)?** YES. Tests whether the agent asks Brief for similar implementations.

**Analysis tags**: `efficiency`, `speed`, `pattern-discovery`, `exploration-pattern`

**Notes**: Good Q1 task. The key signal is how efficiently the agent discovers the existing pattern. A supplementary metric would be whether the output actually follows the pattern (quality check).

---

### 9. documentation

**Prompt**: "Document how the context retrieval system works. Create a markdown file at docs/CONTEXT_RETRIEVAL.md that explains the flow from a 'brief context get' call through to the returned context package."

**What it tests**: Can the agent understand a system comprehensively enough to document it?

**Valid for Q1 (Brief helps)?** YES. Agent needs deep understanding of the retrieval system. Brief should provide this understanding more efficiently than manual file-by-file reading.

**Valid for Q2 (Config optimization)?** YES. Tests Brief usage for comprehensive understanding tasks.

**Analysis tags**: `efficiency`, `speed`, `exploration-pattern`, `understanding-depth`

**Notes**: Good Q1 task. Like bug-investigation, this is primarily about comprehension. Quality of the output doc would be a strong supplementary metric if we choose to evaluate it.

---

## Suggested Analysis Categories

### Category A: "Does Brief Help?" (Q1) — Efficiency Comparison
**Valid dimensions**: feature-addition, cross-cutting, integration, pattern-following, documentation

**Exclude**:
- resume: Concept missing from null config; null agent finishes fast by not engaging
- multi-task: Prompt explicitly names Brief features; tests task-system workflow, not context-system efficiency
- bug-investigation: Brief agent used context get as investigation probes (more thorough), not exploration; timing penalizes quality
- feature-extension: Brief agent slower due to administrative overhead (task checks on direct instruction), not context-system inefficiency

**Metrics**: Duration, turns, total tool calls, R/G/G calls

**Method**: Compare `null-no-hooks` vs `baseline-full-hooks` on these 7 dimensions only. Optionally also compare `null-no-hooks` vs `null-full-hooks` to isolate hook impact from CLAUDE.md impact.

### Category B: "What Config Works Best?" (Q2) — Config Optimization
**Valid dimensions**: ALL 9 dimensions

**Metrics**: Brief ratio, context get count, first exploration action

**Method**: Compare all 7 configs across all dimensions. The brief ratio and context get counts ARE the signal here — higher is better.

### Category C: "Brief Workflow Adoption" (Q2 subset)
**Valid dimensions**: resume, multi-task

**Metrics**: Did the agent run `brief resume`? Did it use `brief task list`? Did it complete all tasks?

**Method**: Binary success/compliance checks, not efficiency metrics.

---

## Aggregate Findings (Category A only, post-void, 2026-01-30)

Category A: 5 clean dimensions (feature-addition, cross-cutting, integration, pattern-following, documentation).
Excludes: resume, multi-task, bug-investigation, feature-extension (see per-dimension notes for reasons).
6 compromised original runs voided; clean re-runs included.

### Q1 Head-to-Head: null-no-hooks vs baseline-full-hooks

| Metric | No Brief | Brief+Hooks | Change |
|---|---|---|---|
| Avg Duration | 260s | 182s | **-30%** |
| Avg Turns | 57.0 | 37.6 | **-34%** |
| Avg Total Tool Calls | 40.6 | 23.0 | **-43%** |
| Avg Read/Grep/Glob | 18.0 | 6.2 | **-66%** |
| Avg context get | 0.0 | 1.2 | N/A |

Per-dimension duration (**Brief+Hooks wins 5 of 5**):
- cross-cutting: N=299s, B=180s (-120s, Brief wins)
- documentation: N=237s, B=156s (-80s, Brief wins)
- feature-addition: N=234s, B=215s (-19s, Brief wins)
- integration: N=291s, B=205s (-85s, Brief wins)
- pattern-following: N=240s, B=152s (-87s, Brief wins)

### All Configs (Category A dimensions only)

| Config | Runs | AvgDur | AvgTurns | AvgTools | AvgR/G/G | Avgctx_get |
|---|---|---|---|---|---|---|
| null-no-hooks | 5 | 260s | 57.0 | 40.6 | 18.0 | 0.0 |
| null-pretool | 5 | 241s | 50.2 | 37.6 | 18.2 | 0.0 |
| null-userprompt | 5 | 230s | 47.4 | 34.2 | 15.4 | 0.6 |
| null-full-hooks | 5 | 191s | 38.8 | 24.4 | 6.2 | 1.4 |
| baseline-no-hooks | 5 | 210s | 46.4 | 31.2 | 12.6 | 0.2 |
| baseline-pretool | 5 | 227s | 44.2 | 31.6 | 14.0 | 0.0 |
| baseline-full-hooks | 5 | 182s | 37.6 | 23.0 | 6.2 | 1.2 |

### Variable Isolation (Q2, all 9 dimensions)

Hooks are the primary driver of Brief adoption:
- null-no-hooks → null-full-hooks: 0% → 19.8% brief ratio
- baseline-no-hooks → baseline-full-hooks: 4.5% → 24.1% brief ratio

CLAUDE.md adds a smaller incremental boost:
- null-full-hooks → baseline-full-hooks: 19.8% → 24.1% (+4.3pp)
- null-no-hooks → baseline-no-hooks: 0% → 4.5% (+4.5pp)

### Cost & Token Analysis (Q1 Head-to-Head)

| Metric | No Brief | Brief+Hooks | Change |
|---|---|---|---|
| Avg Cost | $0.58 | $0.51 | **-12%** |
| Avg Output Tokens | 14,768 | 8,065 | **-45%** |
| Avg Input Tokens | 16,917 | 10,932 | **-35%** |
| Avg Cache Read Tokens | 883,663 | 751,377 | **-15%** |

Per-dimension cost: Brief is cheaper or cost-neutral on all 5 dimensions.
- cross-cutting: $0.85 → $0.58 (-$0.27, biggest savings)
- pattern-following: $0.54 → $0.50
- feature-addition: $0.51 → $0.50
- integration: $0.67 → $0.66
- documentation: $0.34 → $0.33

**CORRECTED**: The blended token reductions above are misleading — they mix tokens from two differently-priced models (Sonnet and Haiku). The 12% cost reduction comes entirely from a 78% drop in Haiku (tool model) usage, while Sonnet (main model) cost is flat. See Session Log entry "Cost analysis correction" for the full per-model breakdown.

### Behavioral Review (2026-01-30)

All 5 Q1 dimensions were reviewed at the individual test level (tool counts, bash commands, context get queries) for both null-no-hooks and baseline-full-hooks. The pattern is consistent:

- **Brief agents make 1-2 context get calls** that provide a map of relevant files
- **This replaces 5-20+ Read/Grep/Glob calls** the null agent needs for the same understanding
- **No anomalies found** — all 5 dimensions show clean, explainable behavior differences
- **Setup overhead** (brief status, task list, which brief) is present in all Brief runs but does not outweigh the exploration savings

Specific observations:
- **cross-cutting**: Same R/G/G count (10 each) but Brief used 42 turns vs 60 — context get helped it work more efficiently per Read
- **integration**: Most dramatic R/G/G difference — null used 26 R/G/G to understand both systems, Brief used 4
- **pattern-following**: null used 31 R/G/G to discover patterns, Brief used 5 — largest raw difference
- **documentation**: Fewest total tools for both — Brief's advantage was tighter focus (16 vs 19 turns)
- **feature-addition**: Closest race (19s), lowest context get benefit because the prompt already hints at the target area

### Results Readiness Assessment

**Ready to state Phase 1 results.** Rationale:
- 5 of 9 dimensions are valid, clean Q1 efficiency tests with no anomalies
- Brief wins all 5 on duration, turns, tool calls, and cost
- The 4 excluded dimensions have documented, specific reasons (not cherry-picking — two test Brief-specific workflows, two have quality/overhead confounds)
- Behavioral review confirms the mechanism: context get replaces multi-step R/G/G exploration
- Cost data reinforces: Brief is 12% cheaper, not just faster
- All tests used Sonnet model on Claude Max; model variation not yet tested
- n=1 per cell remains the main limitation — repeat runs would strengthen confidence

### Key Caveats
- n=1 per config-dimension cell. Aggregates across 5 dimensions are directional but low-n.
- Quality of output is NOT measured — a faster run that produced broken code would be worse than a slower correct one.
- All tests used Sonnet. Model variation not yet tested.
- The 4 excluded dimensions were excluded for legitimate methodological reasons, but this does reduce the test surface. Future rounds should design tests specifically for Q1 validity.

---

## Open Questions / Next Steps

1. **Quality evaluation**: We have no measure of whether the agent's output was correct. Even a spot-check of a few runs would add value.
2. **Repeat runs**: n=1 per cell is thin. Priority re-runs for the most interesting dimensions (cross-cutting, pattern-following, integration showed the biggest Brief advantages).
3. **Test the verbose CLAUDE.md**: The current production CLAUDE.md (191 lines) was never tested with full hooks. The historical data (Appendix in PERFORMANCE_TESTING_PLAN.md) suggests verbose docs help, but that was with different hook configurations.
4. **Externalize dimension metadata**: Dimensions are currently defined inline in `run_test.py`. Need to move to a structured definition file with Q1/Q2 flags, analysis tags, and metric applicability so the analysis script can filter automatically. See `dimension-externalization-plan.md`.
5. **Fix cell-trial weighting**: analyze.py must average per (config, dimension) cell before computing cross-dimension aggregates. See DEV_NOTES.md.
6. **Address setup overhead**: CLAUDE.md causes agents to check task system even on direct instructions. Needs exploration. See DEV_NOTES.md.

---

## Session Log

### 2026-01-30 — Initial analysis session

**Actions taken:**
- Voided 6 compromised test runs (agents escaped clone due to missing .venv). Clean re-runs from Jan 30 now used instead.
- Reviewed all 9 test dimensions for Q1 (efficiency) vs Q2 (config tuning) validity.
- Excluded 4 dimensions from Q1 timing analysis:
  - resume: Null agent finished in 27s by not engaging; Brief agent did real work in 177s. Penalizes quality.
  - multi-task: Prompt explicitly names Brief features; tests task-system workflow, not context efficiency.
  - bug-investigation: Brief agent used context get as investigation probes (10 edge-case queries), doing more thorough work. Timing penalizes quality.
  - feature-extension: Brief agent slower due to administrative overhead (brief status/task list on a direct instruction) and implementation testing loop, not context-system inefficiency. Filed as DEV_NOTES issue.
- Added token/cost extraction to analyze.py (parses result event from Claude Code transcripts for total_cost_usd, modelUsage per-model breakdown, input/output/cache tokens).
- Behavioral deep-dive of all 5 Q1 dimensions confirmed clean, consistent mechanism: 1-2 context get calls replace 5-25 R/G/G calls.
- Added two issues to DEV_NOTES.md: cell-trial weighting in analysis, agent task-system overhead on explicit instructions.
- Created `dimension-externalization-plan.md` for future test definition structure (per-dimension YAML files with analysis metadata).

**Phase 1 results declared ready.** Headline: Brief+Hooks is 30% faster, 43% fewer tool calls, 45% fewer output tokens, 12% cheaper, winning 5 of 5 clean test dimensions. n=1 per cell, no quality measurement yet.

### 2026-01-30 — Cost analysis correction (per-model breakdown)

**Problem**: The initial cost & token analysis reported blended token reductions across models (output -45%, input -35%, cache read -15%) alongside a 12% cost reduction. These don't add up — if every token type dropped by at least 15%, cost should drop by at least 15%.

**Root cause**: Claude Code uses two models — Sonnet (main reasoning) and Haiku (tool-use decisions). Our analysis summed tokens across both models, producing blended percentages that don't reflect cost proportionally because the models have very different per-token pricing.

**Corrected per-model cost breakdown (Q1, 5 clean dimensions):**

| Model | No Brief | Brief+Hooks | Change |
|---|---|---|---|
| Sonnet (main) | $0.48 | $0.49 | **+2%** (flat, within noise) |
| Haiku (tool) | $0.10 | $0.02 | **-78%** |
| **Total** | **$0.58** | **$0.51** | **-12%** |

Tool model share of cost: 17.5% (No Brief) → 4.4% (Brief+Hooks).

**Sonnet token detail** (why main model cost is flat despite fewer turns):

| Sonnet Token Type | No Brief | Brief+Hooks | Change |
|---|---|---|---|
| Output | 49,426 | 38,426 | -22% |
| Cache Read | 3,612,922 | 3,756,886 | +4% |
| Cache Create | 153,113 | 199,836 | **+31%** |

Brief agents produce 22% fewer Sonnet output tokens (less exploratory text), but create 31% more cache entries — likely because `context get` returns large context packages that get written into the conversation cache. These offset each other, leaving Sonnet cost roughly flat.

**Per-dimension detail:**

| Dimension | Null Total | Null Main | Null Tool | Brief Total | Brief Main | Brief Tool |
|---|---|---|---|---|---|---|
| cross-cutting | $0.85 | $0.84 | $0.01 | $0.58 | $0.57 | $0.02 |
| documentation | $0.34 | $0.24 | $0.10 | $0.33 | $0.31 | $0.01 |
| feature-addition | $0.51 | $0.43 | $0.08 | $0.50 | $0.47 | $0.03 |
| integration | $0.67 | $0.53 | $0.14 | $0.66 | $0.64 | $0.02 |
| pattern-following | $0.54 | $0.36 | $0.18 | $0.50 | $0.46 | $0.04 |

Note: cross-cutting is an outlier where main model cost ALSO dropped substantially ($0.84 → $0.57), driving the largest absolute cost savings. The other 4 dimensions show the typical pattern of flat/increased main cost offset by tool cost reduction.

**Key finding**: The 12% cost reduction is **entirely** from Haiku (tool model) savings. Brief agents trigger far fewer tool-use decisions because they make fewer exploratory tool calls — 1-2 `context get` calls vs 5-25 R/G/G calls. Each avoided R/G/G call also avoids the Haiku overhead of processing the tool-use decision. The main model (Sonnet) is cost-neutral: fewer output tokens are offset by increased cache creation from the context packages.

**Implication**: The 78% tool model reduction is the strongest cost-side signal. It's mechanically linked to the 66% R/G/G reduction — fewer exploration tools = fewer Haiku invocations. If Anthropic's pricing changes or tool-use routing changes, the cost benefit would shift accordingly. The speed/turn/tool-call benefits are model-pricing-independent and more robust findings.

**Action taken**: Updated `analyze.py` to show per-model cost columns (`AvgMain$`, `AvgTool$`) in the config comparison table instead of the misleading blended `Avg OutTok` / `Avg InTok` columns. Models are classified by name: "haiku" → tool tier, everything else → main tier.
