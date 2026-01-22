# Brief Example Userflow

This document walks through a complete Brief setup from scratch, demonstrating all features from local analysis through LLM-powered descriptions and embeddings.

## Prerequisites

- Python virtual environment activated: `source .venv/bin/activate`
- For LLM features: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` set in environment

## Setup - Clean Slate

```bash
cd /path/to/your/project
rm -rf .brief
```

## Tier 1: Local Analysis (No LLM)

### Step 1: Initialize

```bash
brief init
```

Creates `.brief/` directory with empty data files.

### Step 2: Analyze Codebase

```bash
# Start with a subdirectory to test
brief analyze dir src/
```

Parses Python files, extracts classes/functions/imports into manifest.

### Step 3: Explore What Was Found

```bash
brief overview          # Project summary
brief inventory         # List all classes and functions
brief coverage          # What percentage analyzed
brief tree              # Directory structure
brief deps              # Import dependency graph
```

### Step 4: Detect Conventions

```bash
brief contracts detect  # Find naming patterns, inheritance, etc.
brief contracts show    # View detected contracts
```

### Step 5: Keyword Search

```bash
brief context search "task"      # Keyword search
brief context search "memory"    # Find related code
brief context search "manager"   # Find manager classes
```

### Step 6: Trace Execution Paths

```bash
brief trace create "task-creation" "TaskManager.create_task"
brief trace list
brief trace show "task-creation"
```

### Step 7: Task Management

```bash
brief task create "Test task" --desc "Testing the system"
brief task list
brief task start <task-id> --steps "first,second,third"
brief task active
brief task step-done step-1 --notes "Completed first step"
brief resume
```

### Step 8: Memory/Patterns

```bash
brief memory remember "test/pattern" "This is a test pattern"
brief memory recall
brief memory recall "test"
```

## Tier 2: LLM Descriptions (Requires API Key)

### Step 9: Generate Descriptions

```bash
# Try ONE file first
brief describe file src/tasks/manager.py

# Check what was created
ls -la .brief/context/files/

# If that worked, try a small module
brief describe module src/tasks/
```

## Tier 3: Semantic Search (Requires Descriptions + API Key)

### Step 10: Generate Embeddings

```bash
# Requires descriptions to exist first
brief context embed

# Now context get can use semantic search
brief context get "how do I track work progress"
```

## Cleanup (Optional)

To start fresh again:

```bash
rm -rf .brief
```
