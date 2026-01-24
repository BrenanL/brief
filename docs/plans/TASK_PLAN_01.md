# Brief Task Plan

**Created**: 2025-01-23
**Purpose**: Detailed task breakdown for parallel agent implementation

---

## Priority Levels

- **P0**: Development infrastructure - enables the rest of the work
- **P1**: Core functionality improvements
- **P2**: Quality of life and polish
- **P3**: Research/analysis (needs human decisions)
- **P4**: Dashboard extras
- **DEFERRED**: After main work complete

## Collaboration Tags

- `[AGENT]` - Can be completed independently by an agent
- `[COLLAB]` - Requires human collaboration or decisions

---

## P0: Development Infrastructure

*Do these first - they enable everything else*

---

### P0-1: Cache Reset Command (Preserve LLM Content) `[AGENT]`

**Problem**: During development, we frequently need to clear and regenerate Brief's cache files (manifest, relationships, etc.) when we change how they work. However, we don't want to lose LLM-generated content (descriptions, summaries) because they cost money and time to regenerate.

**Implementation**:
- Create `brief reset` or `brief cache clear` command
- Must delete: manifest files, relationship files, analysis cache
- Must preserve: `.brief/context/files/` (LLM descriptions), any summaries
- Decision needed: embeddings.db - generated locally but takes time. Preserve by default, `--include-embeddings` flag to also clear them
- Add `--full` flag that clears everything including LLM content (with confirmation prompt)
- Document what gets cleared vs preserved in help text

**Dependencies**: None

---

### P0-2: Development Logging for Brief Commands `[AGENT]`

**Problem**: We need to see when agents call Brief commands to verify our prompting and hooks are working. During this session where agents implement these tasks, we want to capture data on whether they actually used Brief.

**Implementation**:
- Add logging infrastructure that records when `brief context get`, `brief task`, etc. are called
- Log location: configurable via config, default to `.brief-logs/` (NOT inside .brief/ so logs survive directory resets)
- Log format: timestamp, command, arguments, any relevant context
- Make logging toggleable via config: `"command_logging": true` (default: true during dev)
- Create `.brief-logs/` directory on first log write
- Consider log rotation or max file size

**Dependencies**: None

---

### P0-3: Verify Hook and Prompting Effectiveness `[COLLAB]`

**Problem**: Not convinced the prompting and hooks are sufficient to constrain/encourage Brief usage. The pre-tool call hook may not actually be going to the agent, and instead just to the UI of Claude Code. Need to verify this works.

**Why collaboration needed**: Agent cannot fully debug its own hooks - requires human testing and observation.

**Implementation**:
- Test the current hook setup manually - does the warning appear? Does the agent see it?
- Check if `PreToolUse` hooks in `.claude/settings.json` actually reach the agent's context
- Review logs from P0-2 to see if agents are using Brief commands
- If hooks don't work as expected, investigate alternatives
- Document findings and adjust hook strategy accordingly

**Dependencies**: P0-2 (Logging) helps verify this

---

## P1: Core Functionality

*Improvements agents will benefit from during this session*

---

### P1-1: Auto-Generate Descriptions by Default (Config Integration) `[AGENT]`

**Problem**: Currently you must pass `-g` flag to `brief context get` to auto-generate missing descriptions. It's unreasonable to have to remember to type in flags each time if you want fresh context. Default should be yes, generate.

**Implementation**:
- Add config option in `.brief/config.json`: `"auto_generate_descriptions": true` (default: true)
- Modify `get_file_description()` in context.py to check this config
- The `-g` / `--auto-generate` flag still exists to override config
- Add `-G` / `--no-auto-generate` flag to disable when config is true
- When auto-generating, show indication that generation is happening (not silent)
- Seamlessly generate descriptions on first use if they don't exist

**Dependencies**: None

---

### P1-2: LLM Unavailable Handling and Placeholder Quality `[AGENT]`

**Problem**: There's no indication when LLM is not available. Also, placeholders might be harmful - "insert description here" style text would hurt context quality. Better to show function names/signatures than garbage placeholders.

**Implementation**:
- Audit what happens when BAML/LLM is not configured - what do we currently return?
- If returning bad placeholders, change to return signatures/function names instead (useful info)
- Add clear warning when LLM is unavailable: "LLM not configured - descriptions will show signatures only"
- On first `brief context get` with no LLM and no descriptions, tell user how to set up LLM
- Never return placeholder text that looks like a description but isn't

**Dependencies**: None

---

### P1-3: Batch Describe Source Priority `[AGENT]`

**Problem**: `brief describe batch` generates descriptions for test files first, which feels wrong since people care about source files more. Need better ordering.

**Implementation**:
- Modify `describe batch` to check if `src/` directory exists
- If `src/` exists, process files in `src/` first before other directories
- Simple heuristic: prioritize common source directories (src/, lib/, app/) over test directories
- This is a quick fix for better vibes - more sophisticated conditional generation is deferred

**Dependencies**: None

---

### P1-4: Signature vs Description Redundancy in Context Packages `[AGENT]`

**Problem**: Context packages may return both the LLM description AND function signatures. This is too verbose. Preference: show signatures if no description exists, but not both.

**Implementation**:
- In `ContextPackage.to_markdown()` or wherever output is formatted
- Logic: if description exists → show description only; if no description → show signatures
- Add `--show-signatures` flag to force signatures even when descriptions exist
- Review current output format and trim redundancy

**Dependencies**: None

---

### P1-5: Memory Command Rename `[AGENT]`

**Problem**: `brief memory remember <key> <value>` and `brief memory recall <key>` are cumbersome. Want simpler names and top-level aliases.

**Implementation**:
- Rename commands in `src/brief/commands/memory.py`:
  - `remember` → `add`
  - `recall` → `get`
- Add top-level aliases in `cli.py`:
  - `brief remember <key> <value>` works (routes to `memory add`)
  - `brief recall <key>` works (routes to `memory get`)
- Update all help text
- No backwards compatibility needed - project is new

**Dependencies**: None

---

### P1-6: Default Brief Behavior (Shortcut for context get) `[AGENT]`

**Problem**: Want `brief "add logging to execution tracing"` to be a shortcut for `brief context get "add logging..."`. Running brief with just a query string should get a context package by default.

**Implementation**:
- Modify CLI entry point in `cli.py`
- If first argument is not a known command but looks like a query string, route to `context get`
- `brief <query>` → `brief context get <query>`
- Handle edge cases: what if query matches a command name? (probably fine - commands don't have spaces)
- This is the default behavior; can be changed via config later if needed

**Dependencies**: None

---

## P2: Quality of Life and Polish

---

### P2-1: Help Message Quality Pass `[AGENT]`

**Problem**: The help messages from `brief trace` commands are great. Other commands need to be brought up to the same quality level.

**Implementation**:
- Review help text for every command in Brief
- Use `brief trace` commands as the quality bar
- Each command should explain: what it does, when to use it, example usage
- Fix any commands with minimal or unclear help
- Documentation/polish pass across all command modules

**Dependencies**: None

---

### P2-2: Fix `brief overview` Command `[COLLAB]`

**Problem**: `brief overview` is "pretty bad, very unreadable and not good looking." Also unclear what it's even trying to communicate.

**Why collaboration needed**: Need to decide what `brief overview` SHOULD do before redesigning. 
***Agent will come up with its own idea first and complete the work, then we can modify this later***

**Implementation**:
- First: decide what `brief overview` SHOULD do (high-level codebase summary? file listing? something else?)
- Consider: is this redundant with `brief status`? Should it be removed or merged?
- Redesign the output to be readable and useful
- Use rich formatting (tables, colors) like `brief status` does

**Dependencies**: Human decision on purpose

---

### P2-3: Setup Wizard `[COLLAB]`

**Problem**: First-time users don't know about concepts like file descriptions or how to configure Brief. Want a setup wizard that asks questions and configures appropriately.

**Why collaboration needed**: Need input on what questions to ask and what the flow should be. 
***Agent will come up with its own idea first and complete the work, then we can modify this later***

**Implementation**:
- Create `brief setup` command
- Interactive prompts asking:
  - "Do you want to generate file descriptions automatically?" → sets `auto_generate_descriptions`
  - "Which LLM provider?" → configures BAML/model settings
  - Other relevant settings TBD
- After questions, runs necessary commands (`brief init`, `brief analyze all`, maybe initial `describe batch`)
- Shows what was configured and next steps

**Dependencies**: P1-1 (Auto-generate config) should exist first

---

### P2-4: Date/Time Format Exclusions in Config `[AGENT]`

**Problem**: Doc exclude config currently handles YYYY-MM-DD format for date-based files. What about other date/time formats (MM-DD-YYYY, YYYYMMDD, etc.)?

**Implementation**:
- Review current exclude pattern logic in config
- Add support for additional common date formats
- Consider: regex-based exclude patterns for more flexibility
- Document supported formats in help/config

**Dependencies**: None

---

### P2-5: Task System Disable Mode `[AGENT]`

**Problem**: Some users might want to use alternative task systems like "beads" instead of Brief's built-in tasks. Having both active causes confusion.

**Implementation**:
- Add config option: `"enable_tasks": true` (default: true)
- When false, `brief task` commands either warn or are hidden
- Brief still works for context/analysis, just task management is disabled
- Document how to disable and use alternatives

**Dependencies**: None

---

### P2-6: Add Gemini as LLM Provider via BAML `[AGENT]`

**Problem**: Want to add Google Gemini as a provider option for description generation. This enables side-by-side quality testing across providers.

**Implementation**:
- Gemini should already be supported by BAML - verify this
- Integrate Gemini as an option within existing BAML infrastructure (not a separate pipeline)
- Add config option to select provider: `"llm_provider": "openai" | "gemini" | "anthropic"`
- Add config option for model: `"llm_model": "<model-name>"`
- Test that descriptions generate correctly with Gemini
- Document how to switch providers in config

**Dependencies**: None

---

### P2-7: Description Prompt Optimization `[COLLAB]`

**Problem**: Need a test pass on prompting for description generation. Questions: should prompts be conditional by filetype? What provides best BLUF and agent steering?

**Why collaboration needed**: Evaluating prompt quality requires human judgment.
***Agent will come up with its own idea first and complete the work, then we can modify this later***

**Implementation**:
- Review current description generation prompts in generation module
- Test with different file types (models vs CLI vs tests vs utils)
- Consider conditional prompts: different prompt for different file types
- Optimize for BLUF (Bottom Line Up Front) - most important info first
- Document prompt strategy
- A/B testing across providers helps

**Dependencies**: P2-6 (Gemini) helpful for comparison testing

---

## P3: Research/Analysis Tasks

*Need investigation and human decisions before implementation*

---

### P3-1: Embeddings Architecture Documentation `[COLLAB]`

**Problem**: The relationship between `embeddings.db` and `.brief/context/files/` and when they are used is not fully clear. Need analysis of how they're both currently used and how we should best use them.

**Implementation**:
- Trace through code to document when embeddings.db is read/written
- Trace through code to document when context/files/ is read/written
- Document the current architecture
- Identify gaps or inefficiencies
- Propose improvements if any
- Research first, implementation second

**Dependencies**: None

---

### P3-2: Embeddings Generation UX `[COLLAB]`

**Problem**: How are embeddings actually generated? What command does it? How do we make this feel better or be easier to use?

**Implementation**:
- Document current embedding generation flow
- Identify UX pain points
- Consider: should embeddings auto-generate like descriptions can?
- Make the process clearer to users

**Dependencies**: P3-1 (Embeddings architecture) should come first

---

### P3-3: Context Package Ruleset Definition `[COLLAB]`

**Problem**: Many open questions about context package generation:
- How many files to return? Fixed limit or variable based on query?
- What embedding proximity threshold is relevant?
- Should we refine search terms before embedding search (generate multiple query variations)?
- How to verify execution pipelines we return are correct?
- What exactly are we returning - is it important/necessary?
- What are we NOT returning that we should?
- What context package features are not yet implemented?
- Should we add BLUF summary at top of context package?
- Should we add an index of what's in the package?

**Implementation**:
- Needs design decisions first
- Then implement chosen rules
- Make rules configurable eventually
- Document the ruleset

**Dependencies**: Human design input required

---

## P4: Dashboard and Additional Features

---

### P4-1: `brief config show` Command `[AGENT]`

**Problem**: No easy way to see current Brief configuration clearly.

**Implementation**:
- Create `brief config show` command
- Display all current config values in a readable format
- Show defaults vs overridden values
- Include file path locations

**Dependencies**: None

---

### P4-2: Token Counting for Context Packages `[AGENT]`

**Problem**: Want to know how many tokens a context package contains for understanding context window usage.

**Implementation**:
- Add token counting utility (use tiktoken or similar)
- Show token count in `brief context get` output
- Maybe breakdown by section (files, descriptions, traces, etc.)

**Dependencies**: None

---

### P4-3: Compact Summary Mode for Context Get `[AGENT]`

**Problem**: Sometimes you just want the file list and stats, not full descriptions.

**Implementation**:
- Add `--compact` or `--summary` flag to `brief context get`
- Shows: file paths, maybe one-line summaries, stats
- Skips full descriptions and code snippets

**Dependencies**: None

---

### P4-4: `brief coverage --detailed` `[AGENT]`

**Problem**: Want breakdown of coverage by directory.

**Implementation**:
- Add `--detailed` flag to coverage command
- Show per-directory stats for descriptions, analysis, etc.

**Dependencies**: None

---

## DEFERRED

*After main work is complete*

---

### Conditional Description Generation Tiers

**Problem**: Want to configure what files get LLM descriptions vs just analysis. Some files (tests, generated code, etc.) should be tracked and analyzed but not spend LLM resources on descriptions.

**Implementation**:
- Similar to file tracking include/exclude, but for description generation
- Config for "prioritize these directories" and "skip descriptions for these patterns"
- Default: don't generate descriptions for test files
- Configurable patterns for what gets full treatment vs lightweight treatment

---

### Pre-Release Testing

Design tests to quantify/qualify Brief performance gains. Prove it works before publishing.

---

### Release Prep

License file, attributions, docs cleanup, security audit, .env.example, easy install path, remove personal info, consider commit squashing.

---

### Quick-Consult Tool

`brief consult "problem"` - sends context package to Gemini (or other LLM) for second opinion on a problem.

---

### CLI Autocomplete

Tab completion for task IDs, command names, etc.

---

### Plans Attached to Tasks

Richer task documents for better agent convergence.

---

### Multi-Language Support

Support for languages other than Python.

---

### VS Code Extension

IDE integration.

---

### Web UI

Browser-based interface for browsing context.

---

### Branching Model

Per-task branches with patch files/diffs as context.

---

### Sub-Agent Dispatching

Orchestration for spawning agents.

---

### v0.3 Search Improvements

- Improved semantic search ranking
- Search result explanations (why this file matched)
- Filter by file type/directory

---

## Dependency Graph

```
P0 (do first):
├── P0-1: Cache Reset Command
├── P0-2: Development Logging
└── P0-3: Verify Hooks [COLLAB] ← benefits from P0-2

P1 (core, parallel):
├── P1-1: Auto-Generate Config
├── P1-2: LLM Unavailable Handling
├── P1-3: Batch Describe Source Priority
├── P1-4: Signature vs Description Redundancy
├── P1-5: Memory Command Rename
└── P1-6: Default Brief Behavior

P2 (quality, mostly parallel):
├── P2-1: Help Message Quality Pass
├── P2-2: Fix brief overview [COLLAB]
├── P2-3: Setup Wizard [COLLAB] ← after P1-1
├── P2-4: Date/Time Exclusions
├── P2-5: Task System Disable Mode
├── P2-6: Add Gemini via BAML
└── P2-7: Description Prompt Optimization [COLLAB] ← benefits from P2-6

P3 (research, sequential):
├── P3-1: Embeddings Architecture Docs [COLLAB]
├── P3-2: Embeddings Generation UX [COLLAB] ← after P3-1
└── P3-3: Context Package Ruleset [COLLAB]

P4 (extras, parallel):
├── P4-1: brief config show
├── P4-2: Token Counting
├── P4-3: Compact Summary Mode
└── P4-4: brief coverage --detailed
```

---

## Agent-Only Tasks (Can Run in Parallel)

These 15 tasks can be assigned to agents with no human intervention:

**P0**: P0-1, P0-2
**P1**: P1-1, P1-2, P1-3, P1-4, P1-5, P1-6
**P2**: P2-1, P2-4, P2-5, P2-6
**P4**: P4-1, P4-2, P4-3, P4-4

## Collaboration Tasks (Need Human)

These 7 tasks require back-and-forth:

**P0**: P0-3 (Hook verification)
**P2**: P2-2 (Overview redesign), P2-3 (Setup wizard), P2-7 (Prompt optimization)
**P3**: P3-1, P3-2, P3-3 (All research tasks)
