"""Description generation using LLM.

This module provides functions to generate descriptions for code elements
using an LLM (via BAML). If BAML is not configured, it provides placeholder
descriptions for testing.
"""
from pathlib import Path
from typing import Optional
from ..config import load_env
from ..models import ManifestFunctionRecord, ManifestClassRecord, ManifestFileRecord
from .types import FunctionDescription, ClassDescription, FileDescription, ModuleDescription

# Try to load BAML client
_baml_available = False
_baml_client = None

try:
    # Load env before BAML import
    load_env()
    # Try repo-root baml_client first (where baml-cli generate puts it)
    import sys
    from pathlib import Path
    repo_root = Path(__file__).parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from baml_client.sync_client import b as _baml_client
    _baml_available = True
except ImportError:
    pass
except Exception:
    pass


def extract_function_code(file_path: Path, start_line: int, end_line: int | None) -> str:
    """Extract function code from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Adjust for 0-based indexing
    start = max(0, start_line - 1)
    end = min(len(lines), end_line) if end_line else min(len(lines), start + 50)

    return ''.join(lines[start:end])


def extract_class_code(file_path: Path, start_line: int, end_line: int | None) -> str:
    """Extract class code from file."""
    return extract_function_code(file_path, start_line, end_line)


def describe_function(
    record: ManifestFunctionRecord,
    base_path: Path,
    file_context: str = ""
) -> FunctionDescription:
    """Generate description for a function."""
    file_path = base_path / record.file
    code = extract_function_code(
        file_path,
        record.line,
        record.end_line or record.line + 30
    )

    if _baml_available and _baml_client:
        result = _baml_client.DescribeFunction(
            function_name=record.name,
            function_code=code,
            file_context=file_context or f"Part of {record.file}",
            docstring=record.docstring
        )
        return FunctionDescription(
            purpose=result.purpose,
            behavior=result.behavior,
            inputs=result.inputs,
            outputs=result.outputs,
            side_effects=result.side_effects
        )

    # Fallback: generate placeholder description
    return _generate_placeholder_function_description(record, code)


def describe_class(
    record: ManifestClassRecord,
    base_path: Path,
    file_context: str = ""
) -> ClassDescription:
    """Generate description for a class."""
    file_path = base_path / record.file
    code = extract_class_code(
        file_path,
        record.line,
        record.end_line or record.line + 100
    )

    if _baml_available and _baml_client:
        result = _baml_client.DescribeClass(
            class_name=record.name,
            class_code=code,
            file_context=file_context or f"Part of {record.file}",
            docstring=record.docstring,
            method_names=record.methods
        )
        return ClassDescription(
            purpose=result.purpose,
            responsibility=result.responsibility,
            key_methods=result.key_methods,
            state=result.state,
            relationships=result.relationships
        )

    # Fallback: generate placeholder description
    return _generate_placeholder_class_description(record)


def describe_file(
    record: ManifestFileRecord,
    base_path: Path,
    class_names: list[str],
    function_names: list[str],
    imports: list[str]
) -> FileDescription:
    """Generate description for a file."""
    file_path = base_path / record.path
    content = file_path.read_text(encoding='utf-8')

    # Truncate if too long
    max_chars = 15000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n... [truncated]"

    if _baml_available and _baml_client:
        result = _baml_client.DescribeFile(
            file_path=record.path,
            file_content=content,
            class_names=class_names,
            function_names=function_names,
            imports=imports[:20]
        )
        return FileDescription(
            purpose=result.purpose,
            contents=result.contents,
            role=result.role,
            dependencies=result.dependencies,
            exports=result.exports
        )

    # Fallback: generate placeholder description
    return _generate_placeholder_file_description(record, class_names, function_names)


def describe_module(
    module_name: str,
    file_summaries: list[str],
    class_count: int,
    function_count: int
) -> ModuleDescription:
    """Generate description for a module."""
    if _baml_available and _baml_client:
        result = _baml_client.DescribeModule(
            module_name=module_name,
            file_summaries=file_summaries,
            class_count=class_count,
            function_count=function_count
        )
        return ModuleDescription(
            purpose=result.purpose,
            components=result.components,
            architecture=result.architecture,
            public_api=result.public_api
        )

    # Fallback: generate placeholder description
    return _generate_placeholder_module_description(module_name, file_summaries, class_count, function_count)


# ============================================================
# Placeholder generators (for testing without LLM)
# ============================================================

def _generate_placeholder_function_description(
    record: ManifestFunctionRecord,
    code: str
) -> FunctionDescription:
    """Generate placeholder function description from code analysis."""
    params = ", ".join(p.name for p in record.params) if record.params else "none"
    returns = record.returns or "unknown"

    return FunctionDescription(
        purpose=record.docstring.split('\n')[0] if record.docstring else f"Function {record.name}",
        behavior=f"Implements {record.name} logic",
        inputs=f"Parameters: {params}",
        outputs=f"Returns: {returns}",
        side_effects="Generator function" if record.is_generator else None
    )


def _generate_placeholder_class_description(record: ManifestClassRecord) -> ClassDescription:
    """Generate placeholder class description from code analysis."""
    methods = ", ".join(record.methods[:5]) if record.methods else "none"

    return ClassDescription(
        purpose=record.docstring.split('\n')[0] if record.docstring else f"Class {record.name}",
        responsibility=f"Manages {record.name} functionality",
        key_methods=methods,
        state=None,
        relationships=f"Inherits from: {', '.join(record.bases)}" if record.bases else None
    )


def _generate_placeholder_file_description(
    record: ManifestFileRecord,
    class_names: list[str],
    function_names: list[str]
) -> FileDescription:
    """Generate placeholder file description from analysis."""
    return FileDescription(
        purpose=f"Contains {record.module} implementation",
        contents=f"Classes: {', '.join(class_names) or 'none'}. Functions: {', '.join(function_names) or 'none'}",
        role=f"Part of the {record.module} module",
        dependencies="See imports in file",
        exports=", ".join(class_names + function_names) or "See file contents"
    )


def _generate_placeholder_module_description(
    module_name: str,
    file_summaries: list[str],
    class_count: int,
    function_count: int
) -> ModuleDescription:
    """Generate placeholder module description from analysis."""
    return ModuleDescription(
        purpose=f"Provides {module_name} functionality",
        components=f"{len(file_summaries)} files, {class_count} classes, {function_count} functions",
        architecture="See individual file descriptions",
        public_api=f"Import from {module_name}"
    )


# ============================================================
# Formatting functions
# ============================================================

def format_function_description(desc: FunctionDescription) -> str:
    """Format function description as markdown."""
    lines = [
        f"**Purpose**: {desc.purpose}",
        "",
        f"**Behavior**: {desc.behavior}",
        "",
        f"**Inputs**: {desc.inputs}",
        "",
        f"**Outputs**: {desc.outputs}",
    ]

    if desc.side_effects:
        lines.extend(["", f"**Side Effects**: {desc.side_effects}"])

    return "\n".join(lines)


def format_class_description(desc: ClassDescription) -> str:
    """Format class description as markdown."""
    lines = [
        f"**Purpose**: {desc.purpose}",
        "",
        f"**Responsibility**: {desc.responsibility}",
        "",
        f"**Key Methods**: {desc.key_methods}",
    ]

    if desc.state:
        lines.extend(["", f"**State**: {desc.state}"])

    if desc.relationships:
        lines.extend(["", f"**Relationships**: {desc.relationships}"])

    return "\n".join(lines)


def format_file_description(desc: FileDescription) -> str:
    """Format file description as markdown."""
    return f"""**Purpose**: {desc.purpose}

**Contents**: {desc.contents}

**Role**: {desc.role}

**Dependencies**: {desc.dependencies}

**Exports**: {desc.exports}
"""


def format_module_description(desc: ModuleDescription) -> str:
    """Format module description as markdown."""
    return f"""**Purpose**: {desc.purpose}

**Components**: {desc.components}

**Architecture**: {desc.architecture}

**Public API**: {desc.public_api}
"""


def is_baml_available() -> bool:
    """Check if BAML client is available."""
    return _baml_available
