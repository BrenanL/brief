# Brief

**Context infrastructure for AI coding agents.**

Brief provides **deterministic context packages** that enable AI coding agents to produce convergent code. Instead of agents searching indeterministically and guessing what context they need, they call `brief context get` and receive exactly what's needed for the task.

## The Problem

AI coding agents fail in predictable ways:

1. **Convergence failure**: The agent produces code that "works" but doesn't match the intended design
2. **Context loss**: After context compaction, agents forget what they were doing
3. **Missing knowledge**: Agents don't know project conventions, architectural decisions, or implicit rules

The root cause: **agents lack sufficient understanding of the codebase to make correct decisions.**

## The Solution

Brief captures and retrieves codebase understanding at the level needed for correct implementation.

```bash
# Agent receives a task
Human: "Add a logout button to the header"

# Agent gets context - deterministic, not guesswork
Agent: brief context get "add logout button to header"
→ Returns: relevant components, auth patterns, event conventions, related code

# Agent implements correctly because it understands the system
```

## Quick Start

```bash
# Initialize Brief in your project
brief init

# Analyze your codebase (no LLM required)
brief analyze all

# Explore what was found
brief overview
brief inventory

# Get context for what you're working on
brief context get "authentication"

# Create and start a task with steps
brief task create "Auth Feature" --desc "Add user authentication"
brief task start ag-xxxx --steps "design,implement,test"
```

## Feature Tiers

Brief has three tiers of functionality:

### Tier 1: Local Analysis (No LLM)
Everything here runs locally with no API calls:
- `brief init` - Initialize project
- `brief analyze` - Parse codebase with AST
- `brief overview/tree/deps/inventory` - Reports
- `brief contracts detect` - Find naming conventions
- `brief trace` - Execution path tracing
- `brief context search` - Keyword search in manifest
- `brief task` - Task management
- `brief memory` - Pattern storage

### Tier 2: LLM Descriptions (Requires API Key)
Generate natural language descriptions of code:
- `brief describe file <path>` - Describe a single file
- `brief describe module <path>` - Describe a directory
- `brief describe batch` - Describe multiple files

Requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in environment.

### Tier 3: Semantic Search (Requires Descriptions + API Key)
Vector embeddings for semantic code search:
- `brief context embed` - Generate embeddings from descriptions
- Enables semantic search in `brief context get`

Requires descriptions to be generated first, plus `OPENAI_API_KEY`.

## Installation

### Development Install (Editable)
```bash
pip install -e /path/to/brief
```

### For LLM-powered descriptions (optional):
```bash
pip install brief[llm]
# or manually:
pip install baml-py python-dotenv
cd brief && baml-cli generate
```

### For semantic search (optional):
```bash
pip install brief[embeddings]
# or manually:
pip install sentence-transformers
```

## Getting Started Walkthrough

### Step 1: Initialize (No LLM)
```bash
brief init
```
Creates `.brief/` directory with empty data files.

### Step 2: Analyze Codebase (No LLM)
```bash
# Start with a subdirectory to test
brief analyze dir src/

# Or analyze everything
brief analyze all
```
Parses Python files, extracts classes/functions/imports into manifest.

### Step 3: Explore What Was Found (No LLM)
```bash
brief overview          # Project summary
brief inventory         # List all classes and functions
brief coverage          # What percentage analyzed
brief tree              # Directory structure
brief deps              # Import dependency graph
```

### Step 4: Detect Conventions (No LLM)
```bash
brief contracts detect  # Find naming patterns, inheritance, etc.
brief contracts show    # View detected contracts
```

### Step 5: Search the Manifest (No LLM)
```bash
brief context search "task"      # Keyword search
brief context search "manager"   # Find related code
brief context related src/tasks.py  # Context for specific file
```

### Step 6: Trace Execution Paths (No LLM)
```bash
brief trace create "task-creation" "TaskManager.create_task"
brief trace list
brief trace show "task-creation"
```

### Step 7: Generate Descriptions (LLM - Optional)
```bash
# Try one file first
brief describe file src/tasks/manager.py

# Then a module
brief describe module src/tasks/

# Or batch process
brief describe batch --limit 10
```

### Step 8: Generate Embeddings (LLM - Optional)
```bash
# Requires descriptions to exist first
brief context embed
```
Now `brief context get` will use semantic search.

### Step 9: Use Tasks for Work Tracking (No LLM)
```bash
brief task create "Implement feature" --desc "Add new capability"
brief task start ag-xxxx --steps "design,implement,test"
brief task step-done step-1 --notes "Design complete"
brief resume  # Get context for current work
```

## Core Workflows

### Context Retrieval

Get relevant context for any task or query:

```bash
# Keyword search (always works, no LLM)
brief context search "refactoring the table command"

# Full context package
brief context get "refactoring the table command"

# Context for a specific task
brief context get --task ag-1234

# Output includes:
# - Primary files related to the query
# - Relevant patterns from memory
# - Applicable contracts/conventions
# - Related execution paths
```

### Task-Based Work Tracking

Track work with tasks and steps, then resume after context loss:

```bash
# Create a task
brief task create "Implement Feature X" --desc "Add new feature"

# Start working and set steps
brief task start ag-1234 --steps "design,implement,test,document"

# Update progress as you work
brief task step-done step-1 --notes "Design doc at docs/feature-x.md"
brief task step-done step-2

# Add notes before context compacts
brief task note ag-1234 "Working on edge case handling in validate()"

# Resume after context compaction
brief resume
# Returns: current task, steps progress, notes, relevant context
```

### Pattern Memory

Store and recall project-specific knowledge:

```bash
# Remember a pattern
brief memory remember "api/events" \
  "All command outputs must yield AcmeEvent objects"

# Remember with scope (applies to specific files)
brief memory remember "naming/tests" \
  "Test files use test_<module>.py format" \
  --scope "tests/**/*.py"

# Recall patterns
brief memory recall "event"
brief memory recall --file src/commands/table.py
brief memory recall --tags "api,conventions"
```

### Task Management

Track tasks with dependencies:

```bash
# Create tasks
brief task create "Implement login" --priority 1 --tags "auth,feature"
brief task create "Add tests" --depends ag-0001  # Blocked by login task

# View tasks
brief task list              # Shows all tasks (* marks active)
brief task ready             # Tasks with no blockers
brief task blocked           # Tasks waiting on dependencies
brief task active            # Show current active task

# Work on a task
brief task start ag-0001     # Sets as active, marks in_progress
brief task steps "design,implement,test"  # Add steps to active task

# Complete work
brief task step-done step-1  # Mark step complete
brief task done ag-0001      # Mark task complete
```

### Codebase Exploration

Understand project structure:

```bash
brief overview      # Project summary with stats
brief tree          # Directory tree
brief deps          # Dependency graph
brief inventory     # List all classes, functions, modules
brief stale         # Files changed since last analysis
brief coverage      # Analysis coverage stats
```

## AI Agent Integration

### Typical Agent Workflow

```bash
# 1. On session start - get resumption context
brief resume

# 2. If no active task, find or create one
brief task ready
brief task start ag-1234 --steps "investigate,fix,test"

# 3. Work on code...

# 4. Update progress
brief task step-done step-1 --notes "Found root cause in parser.py"

# 5. Before context compaction - save state
brief task note ag-1234 "Stopped at validation logic, need to handle None case"

# 6. After compaction - resume
brief resume
```

### Programmatic Usage

```python
from brief.tasks.manager import TaskManager
from brief.retrieval.context import build_context_for_query
from brief.config import get_brief_path
from pathlib import Path

brief_path = get_brief_path(Path("."))

# Get context for a query
context = build_context_for_query(
    brief_path,
    "implementing user authentication",
    include_patterns=True,
    include_contracts=True,
    include_paths=True
)

print(context.primary_files)   # Relevant files
print(context.patterns)        # Applicable patterns
print(context.contracts)       # Code conventions

# Manage tasks with steps
manager = TaskManager(brief_path)

# Get active task
task = manager.get_active_task()
if task:
    print(f"Active: {task.id} - {task.title}")
    summary = manager.get_step_summary(task.id)
    print(f"Progress: {summary['completed']}/{summary['total_steps']}")
```

## Command Reference

### Initialization & Analysis

| Command | Description | LLM? |
|---------|-------------|------|
| `brief init` | Initialize Brief in current directory | No |
| `brief analyze all` | Analyze entire codebase | No |
| `brief analyze file <path>` | Analyze single file | No |
| `brief analyze dir <path>` | Analyze directory | No |
| `brief analyze refresh` | Re-analyze changed files | No |

### Descriptions (LLM)

| Command | Description | LLM? |
|---------|-------------|------|
| `brief describe file <path>` | Generate description for a file | Yes |
| `brief describe module <path>` | Generate description for a directory | Yes |
| `brief describe batch` | Generate descriptions for multiple files | Yes |

### Context & Search

| Command | Description | LLM? |
|---------|-------------|------|
| `brief context search <query>` | Keyword search in manifest | No |
| `brief context get <query>` | Build full context package | No* |
| `brief context get --task <id>` | Get context for a task | No* |
| `brief context related <path>` | Get context for a file | No |
| `brief context embed` | Generate embeddings from descriptions | Yes |
| `brief resume` | Get context for resuming active task | No |

*Uses embeddings for semantic search if available

### Tasks

| Command | Description | LLM? |
|---------|-------------|------|
| `brief task create <title>` | Create task | No |
| `brief task list` | List tasks (* marks active) | No |
| `brief task show <id>` | Show task details with steps | No |
| `brief task start <id>` | Start task and set as active | No |
| `brief task start <id> --steps "a,b,c"` | Start with steps | No |
| `brief task steps "a,b,c"` | Set steps for active task | No |
| `brief task step-done <step-id>` | Mark step complete | No |
| `brief task active` | Show active task | No |
| `brief task ready` | Show unblocked tasks | No |
| `brief task blocked` | Show blocked tasks | No |
| `brief task done <id>` | Mark task complete | No |
| `brief task note <id> <text>` | Add timestamped note | No |
| `brief task delete <id>` | Delete task | No |

### Memory

| Command | Description | LLM? |
|---------|-------------|------|
| `brief memory remember <key> <value>` | Store a pattern | No |
| `brief memory recall` | Recall patterns | No |
| `brief memory forget <key>` | Remove a pattern | No |
| `brief memory bump <key>` | Reinforce a pattern | No |
| `brief memory list` | List all pattern keys | No |
| `brief memory show <key>` | Show pattern details | No |

### Reports

| Command | Description | LLM? |
|---------|-------------|------|
| `brief overview` | Project summary | No |
| `brief tree` | Directory tree | No |
| `brief deps` | Dependency graph | No |
| `brief inventory` | Code inventory | No |
| `brief coverage` | Analysis coverage | No |
| `brief stale` | Changed files | No |

### Contracts

| Command | Description | LLM? |
|---------|-------------|------|
| `brief contracts detect` | Auto-detect conventions | No |
| `brief contracts show` | Show all contracts | No |
| `brief contracts add <name> <rule>` | Add manual contract | No |
| `brief contracts list` | List contracts summary | No |

### Execution Paths

| Command | Description | LLM? |
|---------|-------------|------|
| `brief trace create <name> <entry>` | Trace from entry point | No |
| `brief trace show <name>` | Show saved path | No |
| `brief trace list` | List all paths | No |
| `brief trace delete <name>` | Delete a traced path | No |

## Architecture

### Data Storage

Brief stores all data in `.brief/` directory:

```
.brief/
├── manifest.jsonl       # Code inventory (classes, functions, imports)
├── relationships.jsonl  # Import dependencies
├── memory.jsonl         # Pattern memory
├── tasks.jsonl          # Task records (with steps)
├── active_task          # Currently active task ID
├── config.json          # Configuration
├── embeddings.db        # Vector embeddings (if generated)
└── context/
    ├── files/           # LLM-generated file descriptions (*.md)
    ├── modules/         # LLM-generated module descriptions (*.md)
    ├── contracts.md     # Detected contracts
    └── paths/           # Execution path traces (*.md)
```

### Component Overview

```
brief/
├── analysis/        # AST parsing and code analysis
├── commands/        # CLI command implementations
├── contracts/       # Convention detection and storage
├── generation/      # LLM-powered descriptions (optional)
├── memory/          # Pattern storage and recall
├── models.py        # Pydantic data models
├── retrieval/       # Context building, search, and embeddings
├── storage.py       # JSONL read/write utilities
├── tasks/           # Task management with steps
├── tracing/         # Execution path tracing
└── cli.py           # Typer CLI entry point
```

### Context Package

The `ContextPackage` dataclass combines all relevant information:

```python
@dataclass
class ContextPackage:
    primary_files: list[dict]    # Most relevant files
    secondary_files: list[dict]  # Related files
    patterns: list[dict]         # Applicable patterns
    contracts: list[str]         # Code conventions
    execution_paths: list[dict]  # Execution flow diagrams
```

### Analysis Pipeline

1. **Static Analysis** - Parse Python files with AST, extract classes/functions/imports
2. **Manifest Generation** - Store inventory in JSONL format with hashes
3. **Relationship Extraction** - Track import dependencies
4. **Contract Detection** - Find naming conventions, patterns, inheritance
5. **Description Generation** - (Optional, LLM) Generate descriptions
6. **Embedding Generation** - (Optional, LLM) Embed descriptions for semantic search

## Configuration

### Environment Variables

```bash
# For LLM descriptions and embeddings (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### BAML Clients

LLM clients are configured in `baml_src/clients.baml`:

```baml
client<llm> Default {
  provider openai
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
  }
}
```

## Testing

```bash
# Run all Brief tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_tasks.py -v
pytest tests/test_retrieval.py -v
pytest tests/test_memory.py -v
```

## Design Principles

1. **Deterministic Context** - Same query always returns the same context package
2. **Persistence Over Memory** - Everything is stored, nothing relies on agent context
3. **Graceful Degradation** - Works without LLM APIs (uses docstrings/heuristics)
4. **Agent-First Design** - Optimized for AI assistant workflows
5. **Minimal Overhead** - Fast analysis, efficient storage
6. **Composable Components** - Each piece works independently

## License

MIT
