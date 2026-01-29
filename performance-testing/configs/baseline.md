# Baseline Configuration

This configuration represents a standard Claude Code setup with no Brief-specific hooks or instructions.

## Hooks

**None** - No hooks configured.

```json
{
  "hooks": {}
}
```

## CLAUDE.md

Minimal project instructions with no Brief workflow guidance:

```markdown
# CLAUDE.md

This is the **Brief** codebase - a context infrastructure tool for AI coding agents.

## Environment

source .venv/bin/activate
pytest tests/ -v -s

## Project Structure

src/brief/
├── cli.py              # Entry point
├── config.py           # Configuration
├── models.py           # Data models
├── commands/           # CLI commands
├── retrieval/          # Context building
└── tasks/              # Task management

## Code Style

- Type hints for all function signatures
- Pydantic models for data structures
- JSONL for persistent storage
```

## Purpose

This configuration serves as the **control group** for A/B testing. It represents how an agent would behave without any guidance to use Brief's context tools.

## Expected Behavior

- Agent uses Read/Grep/Glob directly for code exploration
- No awareness of `brief context get` command
- Standard file-by-file exploration pattern
