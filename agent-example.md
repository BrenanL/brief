# CLAUDE.md

This project uses **Brief** for context management.

## Environment Setup

Always activate the virtual environment before running commands:

```bash
source .venv/bin/activate
```

Run tests with:
```bash
pytest tests/ -v -s
```

## Resuming Previous Work

If the user asks you to **resume**, **continue**, or **pick up where you left off**:

```bash
brief resume
```

This shows the active task with its context. Continue working on that task.

If you're unsure whether there's relevant existing work:
```bash
brief task list
```

## How to Get Information

**Do NOT search the codebase yourself.** Instead, use:

```bash
brief context get "what you need to understand"
```

This replaces grep, glob, find, and exploratory file reading. Brief knows the codebase structure and will give you exactly what's relevant - including related files, contracts you must follow, and execution paths.

**Examples:**
- Need to understand a feature? → `brief context get "how does context retrieval work"`
- Need to modify something? → `brief context get "modifying the search system"`
- Confused about relationships? → `brief context get "what calls build_context_for_query"`
- Starting a task? → `brief context get "adding timing to context retrieval"`

Use this command **repeatedly** as you work - not just once at the start.

## Workflow

### Starting Work

When the user gives you a specific task:

```bash
# 1. Get context for what you're doing
brief context get "what you're working on"

# 2. For larger work, create a task to track it
brief task create "title" --desc "details" --tags "tags"
brief task start <task-id>
```

Task creation is optional for quick fixes, but recommended for anything that might be interrupted or handed off.

### During Work

```bash
# Get more context as needed (use this liberally)
brief context get "the specific thing you need to understand"
```

### Completing Work

```bash
# Mark the task done (if you created one)
brief task done <task-id>

# Run tests
pytest tests/ -v -s
```

## Key Commands

| Command | Use When |
|---------|----------|
| `brief context get "query"` | You need to understand something |
| `brief resume` | User asks to continue previous work |
| `brief task list` | See all tasks |
| `brief task create "title"` | Starting trackable work |
| `brief task done <id>` | Finishing tracked work |
| `brief contracts show` | You need to see all codebase rules |
| `brief trace show <name>` | You want to see an execution flow |

## Important

1. **Always use `brief context get` before implementing** - it shows you the right files, patterns, and contracts
2. **Use `brief resume` when asked to continue previous work** - not for new tasks
3. **Follow the contracts** - they're rules that keep the codebase consistent
4. **Don't search manually** - trust Brief to give you relevant context
