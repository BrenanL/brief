# Contributing to Brief

Thanks for your interest in contributing to Brief!

## Getting Started

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Setup

```bash
git clone https://github.com/BrenanL/brief.git
cd brief
uv venv
source .venv/bin/activate
uv pip install -e ".[all]"
```

### Running Tests

```bash
pytest tests/ -v -s
```

## How to Contribute

### Reporting Issues

Open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your environment (Python version, OS)

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v -s`)
5. Commit with a clear message
6. Open a pull request

### Code Style

- Use type hints for all function signatures
- Follow existing patterns in the codebase
- Pydantic models for data structures
- JSONL for persistent storage
- Typer for CLI commands
- Line length: 100 characters (Black + Ruff)

### Project Structure

```
src/brief/
├── cli.py           # Typer CLI entry point
├── config.py        # Configuration and paths
├── models.py        # Pydantic data models
├── storage.py       # JSONL/JSON utilities
├── analysis/        # AST parsing and code analysis
├── commands/        # CLI command implementations
├── contracts/       # Convention detection
├── generation/      # LLM-powered descriptions
├── memory/          # Pattern storage and recall
├── retrieval/       # Context building and search
├── tasks/           # Task management
└── tracing/         # Execution path tracing
```

### Adding a New Command

1. Create a module in `src/brief/commands/`
2. Define `app = typer.Typer()` in the module
3. Register it in `src/brief/cli.py`
4. Add tests in `tests/`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
