"""Relationship extraction from parsed code."""
from pathlib import Path
from typing import Union
from .parser import PythonFileParser
from ..models import ImportRelationship, CallRelationship
from ..storage import write_jsonl
from ..config import get_brief_path, RELATIONSHIPS_FILE

# Type alias for relationship records
RelationshipRecord = Union[ImportRelationship, CallRelationship]


def resolve_import_to_file(
    import_module: str,
    base_path: Path,
    importing_file: str | None = None,
    level: int = 0
) -> str | None:
    """Try to resolve an import to a local file path.

    Args:
        import_module: The module being imported (e.g., "models" for "from ..models import X")
        base_path: The base path of the project
        importing_file: The file that contains the import (needed for relative imports)
        level: The relative import level (0 for absolute, 1 for ".", 2 for "..", etc.)

    Returns:
        The relative path to the imported file, or None if it's an external import.
    """
    # Handle relative imports
    if level > 0 and importing_file:
        # Get the directory of the importing file
        importing_path = Path(importing_file)
        # Go up 'level' directories (level=1 means same package, level=2 means parent, etc.)
        # For a file like src/brief/commands/analyze.py with level=2 and module="models":
        # - importing_path.parent = src/brief/commands
        # - Go up 'level' times: level=2 means go up 2-1=1 level from the file's package
        # Actually, level represents how many dots there are:
        # - "from . import X" -> level=1, stay in same package
        # - "from .. import X" -> level=2, go up one package
        # - "from ...import X" -> level=3, go up two packages

        # Start from the directory containing the importing file
        package_dir = importing_path.parent

        # Go up (level - 1) additional directories
        # level=1 (.): same directory as current file's package
        # level=2 (..): parent of current file's package
        for _ in range(level - 1):
            package_dir = package_dir.parent

        # Now resolve the module relative to this directory
        if import_module:
            parts = import_module.split('.')
            resolved_path = package_dir / '/'.join(parts)
        else:
            # "from . import X" where import_module is empty
            resolved_path = package_dir

        # Try as package (directory with __init__.py)
        package_init = base_path / resolved_path / '__init__.py'
        if package_init.exists():
            return str(package_init.relative_to(base_path))

        # Try as module (file.py)
        module_file = base_path / (str(resolved_path) + '.py')
        if module_file.exists():
            return str(module_file.relative_to(base_path))

        return None  # Couldn't resolve

    # Handle absolute imports
    if not import_module:
        return None

    # Convert module.name to path
    parts = import_module.split('.')

    # Try as package (directory with __init__.py)
    package_path = base_path / '/'.join(parts) / '__init__.py'
    if package_path.exists():
        return str(package_path.relative_to(base_path))

    # Try as module (file.py)
    if len(parts) > 1:
        module_path = base_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
    else:
        module_path = base_path / f"{parts[0]}.py"
    if module_path.exists():
        return str(module_path.relative_to(base_path))

    # Try direct path
    direct_path = base_path / '/'.join(parts)
    direct_path_py = Path(str(direct_path) + '.py')
    if direct_path_py.exists():
        return str(direct_path_py.relative_to(base_path))

    return None  # External import


class RelationshipExtractor:
    """Extract relationships from analyzed code."""

    def __init__(self, base_path: Path, exclude_patterns: list[str] | None = None):
        self.base_path = base_path
        self.exclude_patterns = exclude_patterns or []
        self.relationships: list[RelationshipRecord] = []

    def extract_from_file(self, file_path: Path) -> list[RelationshipRecord]:
        """Extract import and call relationships from a file."""
        parser = PythonFileParser(file_path, self.base_path)
        if not parser.parse():
            return []

        relationships: list[RelationshipRecord] = []
        from_file = str(file_path.relative_to(self.base_path))

        # Extract import relationships
        for module, level, names in parser.get_imports():
            to_file = resolve_import_to_file(
                module, self.base_path,
                importing_file=from_file,
                level=level
            )
            if to_file:  # Only track local imports
                relationships.append(ImportRelationship(
                    from_file=from_file,
                    to_file=to_file,
                    imports=names
                ))

        # Extract call relationships
        for call_rel in parser.get_calls():
            relationships.append(call_rel)

        return relationships

    def extract_all(self, directory: Path | None = None) -> list[RelationshipRecord]:
        """Extract all relationships from directory."""
        if directory is None:
            directory = self.base_path

        self.relationships = []

        for file_path in directory.rglob("*.py"):
            skip = False
            for pattern in self.exclude_patterns:
                if pattern in str(file_path):
                    skip = True
                    break
            if not skip:
                self.relationships.extend(self.extract_from_file(file_path))

        return self.relationships

    def save_relationships(self, brief_path: Path | None = None) -> None:
        """Save relationships to JSONL file."""
        if brief_path is None:
            brief_path = get_brief_path(self.base_path)

        write_jsonl(brief_path / RELATIONSHIPS_FILE, self.relationships)

    def get_dependencies(self, file_path: str) -> list[str]:
        """Get files that the given file depends on."""
        return [
            r.to_file for r in self.relationships
            if isinstance(r, ImportRelationship) and r.from_file == file_path
        ]

    def get_dependents(self, file_path: str) -> list[str]:
        """Get files that depend on the given file."""
        return [
            r.from_file for r in self.relationships
            if isinstance(r, ImportRelationship) and r.to_file == file_path
        ]

    def get_callees(self, func_name: str) -> list[str]:
        """Get functions called by the given function.

        Args:
            func_name: Function name in format "ClassName.method" or "function_name"

        Returns:
            List of function names that are called by this function
        """
        return [
            r.to_func for r in self.relationships
            if isinstance(r, CallRelationship) and r.from_func == func_name
        ]

    def get_callers(self, func_name: str) -> list[str]:
        """Get functions that call the given function.

        Args:
            func_name: Function name to find callers of

        Returns:
            List of function names that call this function
        """
        return [
            r.from_func for r in self.relationships
            if isinstance(r, CallRelationship) and r.to_func == func_name
        ]
