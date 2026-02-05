"""AST parsing for Python files."""
import ast
from pathlib import Path
from typing import Generator
from ..models import (
    ManifestFileRecord, ManifestClassRecord, ManifestFunctionRecord,
    ParamInfo, ImportRelationship, CallRelationship
)
import hashlib
from datetime import datetime


def compute_file_hash(path: Path) -> str:
    """Compute MD5 hash of file contents."""
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def get_module_from_path(path: Path, base_path: Path) -> str:
    """Convert file path to module name."""
    try:
        relative = path.relative_to(base_path)
        parts = list(relative.parts)
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]
        if parts[-1] == '__init__':
            parts = parts[:-1]
        return '.'.join(parts) if parts else 'root'
    except ValueError:
        return path.stem


def extract_type_annotation(node: ast.expr | None) -> str | None:
    """Extract type annotation as string."""
    if node is None:
        return None
    return ast.unparse(node)


def extract_default_value(node: ast.expr | None) -> str | None:
    """Extract default value as string."""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


class PythonFileParser:
    """Parse a Python file and extract structure."""

    def __init__(self, file_path: Path, base_path: Path):
        self.file_path = file_path
        self.base_path = base_path
        self.module = get_module_from_path(file_path, base_path)
        self.tree: ast.AST | None = None
        self.source: str = ""

    def parse(self) -> bool:
        """Parse the file. Returns True if successful."""
        try:
            self.source = self.file_path.read_text(encoding='utf-8')
            self.tree = ast.parse(self.source, filename=str(self.file_path))
            return True
        except (SyntaxError, UnicodeDecodeError):
            return False

    def get_file_record(self) -> ManifestFileRecord:
        """Get the file manifest record."""
        return ManifestFileRecord(
            path=str(self.file_path.relative_to(self.base_path)),
            module=self.module,
            analyzed_at=datetime.now(),
            file_hash=compute_file_hash(self.file_path)
        )

    def get_classes(self) -> Generator[ManifestClassRecord, None, None]:
        """Extract class definitions."""
        if not self.tree:
            return

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                bases = [ast.unparse(base) for base in node.bases]
                docstring = ast.get_docstring(node)

                yield ManifestClassRecord(
                    name=node.name,
                    file=str(self.file_path.relative_to(self.base_path)),
                    line=node.lineno,
                    end_line=node.end_lineno,
                    methods=methods,
                    bases=bases,
                    docstring=docstring
                )

    def get_functions(self) -> Generator[ManifestFunctionRecord, None, None]:
        """Extract function definitions (both module-level and methods)."""
        if not self.tree:
            return

        # Module-level functions
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield self._make_function_record(node, class_name=None)

        # Methods within classes
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield self._make_function_record(child, class_name=node.name)

    def _make_function_record(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str | None
    ) -> ManifestFunctionRecord:
        """Create a function record from an AST node."""
        params = []
        # Positional-only args (before / in signature)
        for arg in node.args.posonlyargs:
            params.append(ParamInfo(
                name=arg.arg,
                type_hint=extract_type_annotation(arg.annotation)
            ))
        # Regular positional args
        for arg in node.args.args:
            params.append(ParamInfo(
                name=arg.arg,
                type_hint=extract_type_annotation(arg.annotation)
            ))

        # Handle defaults (they align to the end of posonlyargs + args)
        defaults = node.args.defaults
        if defaults and params:
            offset = len(params) - len(defaults)
            for i, default in enumerate(defaults):
                idx = offset + i
                if 0 <= idx < len(params):
                    params[idx].default = extract_default_value(default)

        # Keyword-only args (after * in signature)
        for j, arg in enumerate(node.args.kwonlyargs):
            kw_default = None
            if j < len(node.args.kw_defaults) and node.args.kw_defaults[j] is not None:
                kw_default = extract_default_value(node.args.kw_defaults[j])
            params.append(ParamInfo(
                name=arg.arg,
                type_hint=extract_type_annotation(arg.annotation),
                default=kw_default,
            ))

        returns = extract_type_annotation(node.returns)
        is_generator = any(
            isinstance(n, (ast.Yield, ast.YieldFrom))
            for n in ast.walk(node)
        )

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                if isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                elif isinstance(decorator, ast.Attribute):
                    decorators.append(ast.unparse(decorator))
                elif isinstance(decorator, ast.Call):
                    # For @decorator(args), extract just the decorator name
                    decorators.append(ast.unparse(decorator.func))
                else:
                    decorators.append(ast.unparse(decorator))
            except Exception:
                pass  # Skip decorators we can't parse

        return ManifestFunctionRecord(
            name=node.name,
            file=str(self.file_path.relative_to(self.base_path)),
            line=node.lineno,
            end_line=node.end_lineno,
            class_name=class_name,
            params=params,
            returns=returns,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_generator=is_generator,
            decorators=decorators,
            docstring=ast.get_docstring(node)
        )

    def get_imports(self) -> Generator[tuple[str, int, list[str]], None, None]:
        """Extract imports as (module, level, [names]) tuples.

        Args:
            Yields tuples of (module_name, relative_level, imported_names)
            - module_name: the module being imported from (e.g., "models" for "from ..models import X")
            - relative_level: 0 for absolute imports, 1 for "from . import", 2 for "from .. import", etc.
            - imported_names: list of names being imported
        """
        if not self.tree:
            return

        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield (alias.name, 0, [alias.asname or alias.name])
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                # node.module can be None for "from . import X"
                module = node.module or ""
                level = node.level or 0
                yield (module, level, names)

    def get_calls(self) -> Generator[CallRelationship, None, None]:
        """Extract function calls within function bodies.

        Yields CallRelationship records for calls found in function bodies.
        Only extracts calls to named functions (not lambda, comprehensions, etc.)
        """
        if not self.tree:
            return

        file_path = str(self.file_path.relative_to(self.base_path))

        # Process module-level functions
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                from_func = node.name
                yield from self._extract_calls_from_function(node, from_func, file_path)

        # Process methods within classes
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        from_func = f"{node.name}.{child.name}"
                        yield from self._extract_calls_from_function(child, from_func, file_path)

    def _extract_calls_from_function(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        from_func: str,
        file_path: str
    ) -> Generator[CallRelationship, None, None]:
        """Extract calls from a single function body."""
        seen_calls: set[str] = set()  # Avoid duplicates

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                to_func = self._get_call_name(node.func)
                if to_func and to_func not in seen_calls:
                    seen_calls.add(to_func)
                    yield CallRelationship(
                        from_func=from_func,
                        to_func=to_func,
                        file=file_path,
                        line=node.lineno
                    )

    def _get_call_name(self, node: ast.expr) -> str | None:
        """Extract the name of a called function from a Call node.

        Handles:
        - Simple names: foo() -> "foo"
        - Attribute access: self.foo() -> "self.foo", obj.method() -> "obj.method"
        - Chained: a.b.c() -> "a.b.c"

        Returns None for complex expressions we can't easily name.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Build the full attribute chain
            parts = [node.attr]
            current = node.value
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                return '.'.join(reversed(parts))
            # Can't resolve the base (e.g., function call result)
            return None
        else:
            # Lambda, subscript, or other complex expression
            return None
