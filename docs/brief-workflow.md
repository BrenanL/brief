# Brief Workflow Guide

Detailed guide for using Brief in your development workflow.

## The Core Concept

**Brief replaces manual code exploration.** Instead of:
- `grep` / `rg` for searching
- `glob` / `find` for finding files
- Reading files to understand structure

Use:
```bash
brief context get "what you need to understand"
```

Brief knows the codebase structure and gives you exactly what's relevant - including:
- Relevant files with descriptions
- Function signatures
- Related files (imports, importers)
- Contracts you must follow
- Execution paths through the code

## Getting Information

### Examples

| You want to... | Run this |
|----------------|----------|
| Understand a feature | `brief context get "how does context retrieval work"` |
| Modify something | `brief context get "modifying the search system"` |
| Understand relationships | `brief context get "what calls build_context_for_query"` |
| Start a task | `brief context get "adding timing to context retrieval"` |

### Use It Repeatedly

Don't just run `brief context get` once at the start. Use it **throughout** your work:
- When you hit something you don't understand
- When you need to find related code
- Before modifying a new area
- When you're unsure what a function does

## Task Workflow

### Starting Work

When the user gives you a specific task:

```bash
# 1. Check project status
brief status

# 2. See available tasks
brief task list

# 3. Start a task (if one exists for your work)
brief task start <task-id>

# 4. Get context for what you're doing
brief context get "what you're working on"
```

### Creating Tasks

For larger work that might be interrupted or handed off:

```bash
brief task create "title" --desc "details" --tags "tags"
brief task start <task-id>
```

Task creation is optional for quick fixes.

### During Work

```bash
# Get more context as needed (use this liberally)
brief context get "the specific thing you need to understand"
```

### Completing Work

```bash
# Mark the task done
brief task done <task-id>

# Run tests
pytest tests/ -v -s
```

## TodoWrite vs Brief Tasks

These serve different purposes:

| Tool | Purpose | Persistence |
|------|---------|-------------|
| **Brief tasks** | Track work items | Persistent across sessions |
| **TodoWrite** | Plan steps for current task | Session-scoped |

**Example workflow:**
1. `brief task start ag-1234` (persistent task: "Add caching")
2. TodoWrite: "1. Find API code, 2. Add cache layer, 3. Update tests" (session steps)
3. Do the work...
4. `brief task done ag-1234`

## Key Commands Reference

| Command | Use When |
|---------|----------|
| `brief context get "query"` | You need to understand something |
| `brief status` | Starting a work session |
| `brief task list` | See all tasks |
| `brief task start <id>` | Beginning work on a task |
| `brief task done <id>` | Finishing tracked work |
| `brief resume` | User asks to continue previous work |
| `brief contracts show` | You need to see all codebase rules |
| `brief trace show <name>` | You want to see an execution flow |
| `brief tree` | See project structure with status |
| `brief coverage` | See analysis/description coverage |

## Important Rules

1. **Always use `brief context get` before implementing** - it shows you the right files, patterns, and contracts

2. **Use `brief resume` when asked to continue previous work** - not for new tasks

3. **Follow the contracts** - they're rules that keep the codebase consistent

4. **Don't search manually** - trust Brief to give you relevant context

5. **Mark tasks done** - don't forget `brief task done <id>` when you finish

## When To Use Direct File Access

It's okay to use Read/Grep/Glob when:
- You already know exactly which file you need
- You're reading a specific file you were just told about
- You're doing a very targeted search (not exploration)

Use Brief when:
- You need to understand how something works
- You're exploring unfamiliar code
- You need to find related files
- You want context (descriptions, signatures, contracts)
