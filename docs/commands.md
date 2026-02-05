# Brief Command Reference

## Setup & Initialization

| Command | Description | API Key? |
|---------|-------------|----------|
| `brief init` | Initialize Brief and analyze codebase | No |
| `brief setup` | Interactive setup wizard | No |
| `brief setup -d` | Full automated setup (init + analyze + descriptions + embeddings + CLAUDE.md) | Embeddings need OpenAI |
| `brief reset` | Clear analysis cache, preserve LLM content | No |

## Context & Search

| Command | Description | API Key? |
|---------|-------------|----------|
| `brief context get <query>` | Build full context package for a query | No* |
| `brief ctx <query>` | Shortcut for `context get` | No* |
| `brief q <query>` | Shortcut for `context get` | No* |
| `brief context search <query>` | Keyword search in manifest | No |
| `brief context related <path>` | Get context for a specific file | No |
| `brief context embed` | Generate embeddings from descriptions | Yes (OpenAI) |
| `brief resume` | Get context for resuming active task | No |

\* Uses semantic search if embeddings are available, falls back to keyword search.

## Analysis

| Command | Description | API Key? |
|---------|-------------|----------|
| `brief analyze all` | Full codebase analysis | No |
| `brief analyze file <path>` | Analyze single file | No |
| `brief analyze dir <path>` | Analyze directory | No |
| `brief analyze refresh` | Re-analyze changed files only | No |

## Descriptions (LLM)

| Command | Description | API Key? |
|---------|-------------|----------|
| `brief describe file <path>` | Generate LLM description for a file | Yes |
| `brief describe module <path>` | Generate description for a directory | Yes |
| `brief describe batch` | Batch-generate descriptions | Yes |
| `brief describe spec` | Generate full codebase specification | Yes |

## Tasks

| Command | Description |
|---------|-------------|
| `brief task create <title>` | Create a new task |
| `brief task list` | List all tasks |
| `brief task show <id>` | Show task details |
| `brief task start <id>` | Start working on a task |
| `brief task start <id> --steps "a,b,c"` | Start with defined steps |
| `brief task steps "a,b,c"` | Set steps for active task |
| `brief task step-done <step-id>` | Mark step complete |
| `brief task done <id>` | Mark task complete |
| `brief task note <id> <text>` | Add a note to a task |
| `brief task active` | Show active task |
| `brief task ready` | Show unblocked tasks |
| `brief task blocked` | Show blocked tasks |
| `brief task delete <id>` | Delete a task |
| `brief task archive` | Archive completed tasks |

## Reports

| Command | Description |
|---------|-------------|
| `brief status` | Project dashboard |
| `brief overview` | Architecture overview |
| `brief tree` | Directory structure |
| `brief deps` | Dependency graph |
| `brief inventory` | List all classes and functions |
| `brief coverage` | Analysis coverage stats |
| `brief stale` | Files changed since last analysis |

## Memory

| Command | Description |
|---------|-------------|
| `brief memory remember <key> <value>` | Store a pattern |
| `brief memory recall` | Recall patterns |
| `brief memory forget <key>` | Remove a pattern |
| `brief memory list` | List all pattern keys |
| `brief remember <key> <value>` | Shortcut for memory remember |
| `brief recall` | Shortcut for memory recall |

## Execution Traces

| Command | Description |
|---------|-------------|
| `brief trace list` | List trace definitions |
| `brief trace show <name>` | Show execution flow |
| `brief trace show <name> -v` | Show with code snippets |
| `brief trace define <name> <entry>` | Define custom trace |
| `brief trace discover` | Find entry points |
| `brief trace discover --auto` | Auto-create traces |

## Contracts (Conventions)

| Command | Description |
|---------|-------------|
| `brief contracts detect` | Auto-detect naming conventions |
| `brief contracts show` | Display all contracts |
| `brief contracts add <name> <rule>` | Add manual contract |
| `brief contracts list` | List contracts summary |

## Configuration

| Command | Description |
|---------|-------------|
| `brief config show` | Show current configuration |
| `brief config set <key> <value>` | Update a setting |
| `brief model list` | List available LLM models |
| `brief model set <model>` | Set default model |

## Data Storage

All data lives in `.brief/` in your project root:

```
.brief/
├── manifest.jsonl       # Code inventory (classes, functions, imports)
├── relationships.jsonl  # Import dependencies and call graphs
├── tasks.jsonl          # Task records
├── memory.jsonl         # Pattern memory
├── config.json          # Configuration
├── embeddings.db        # Vector embeddings (SQLite)
└── context/
    ├── files/           # File descriptions (*.md)
    ├── modules/         # Module descriptions
    └── traces.jsonl     # Trace definitions
```
