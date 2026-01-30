# CLAUDE.md

This is the **Brief** codebase - a context infrastructure tool for AI coding agents.

## Environment

```bash
source .venv/bin/activate
pytest tests/ -v -s
```

## Project Structure

```
src/brief/
├── cli.py              # Entry point
├── config.py           # Configuration
├── models.py           # Data models
├── commands/           # CLI commands
├── retrieval/          # Context building
└── tasks/              # Task management
```

## Code Style

- Type hints for all function signatures
- Pydantic models for data structures
- JSONL for persistent storage
