"""Pattern-based contract detection."""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any
from ..storage import read_jsonl
from ..config import MANIFEST_FILE


@dataclass
class Contract:
    """A detected or inferred contract."""
    name: str
    rule: str
    category: str  # naming, type, behavioral, organization, api
    examples_good: list[str] = field(default_factory=list)
    examples_bad: list[str] = field(default_factory=list)
    verification: str = ""
    files_affected: list[str] = field(default_factory=list)
    source: str = ""
    confidence: str = "medium"  # low, medium, high

    def to_markdown(self) -> str:
        """Convert to markdown."""
        lines = [
            f"## Contract: {self.name}",
            "",
            f"**Category**: {self.category}",
            f"**Confidence**: {self.confidence}",
            "",
            "### Rule",
            self.rule,
            "",
        ]

        if self.examples_good or self.examples_bad:
            lines.append("### Examples")
            for ex in self.examples_good:
                lines.append(f"- ✓ {ex}")
            for ex in self.examples_bad:
                lines.append(f"- ✗ {ex}")
            lines.append("")

        if self.verification:
            lines.extend([
                "### Verification",
                self.verification,
                ""
            ])

        if self.files_affected:
            lines.append("### Files Affected")
            for f in self.files_affected[:10]:
                lines.append(f"- `{f}`")
            if len(self.files_affected) > 10:
                lines.append(f"- ... and {len(self.files_affected) - 10} more")
            lines.append("")

        if self.source:
            lines.extend([
                "### Source",
                self.source,
                ""
            ])

        return "\n".join(lines)


class ContractDetector:
    """Detect contracts from code patterns."""

    def __init__(self, brief_path: Path, base_path: Path):
        self.brief_path = brief_path
        self.base_path = base_path
        self._manifest: Optional[list[dict[str, Any]]] = None

    def _load_manifest(self) -> list[dict[str, Any]]:
        if self._manifest is None:
            self._manifest = list(read_jsonl(self.brief_path / MANIFEST_FILE))
        return self._manifest

    def detect_naming_conventions(self) -> list[Contract]:
        """Detect naming convention contracts."""
        contracts = []
        manifest = self._load_manifest()

        # Detect class naming patterns
        class_suffixes: dict[str, list[dict[str, Any]]] = {}
        for record in manifest:
            if record.get("type") == "class":
                name = record.get("name", "")
                # Find common suffixes
                for suffix in ["Command", "Manager", "Handler", "Service",
                               "Factory", "Base", "Error", "Exception",
                               "Test", "Mixin", "View", "Model"]:
                    if name.endswith(suffix):
                        if suffix not in class_suffixes:
                            class_suffixes[suffix] = []
                        class_suffixes[suffix].append(record)

        # Create contracts for common suffixes
        for suffix, records in class_suffixes.items():
            if len(records) >= 2:  # At least 2 occurrences
                # Find common directory
                dirs = set(str(Path(r.get("file", "")).parent) for r in records)
                if len(dirs) == 1:
                    dir_str = str(list(dirs)[0])
                else:
                    dir_str = "multiple directories"

                contracts.append(Contract(
                    name=f"{suffix} Naming Convention",
                    rule=f"Classes in this pattern should end with '{suffix}'",
                    category="naming",
                    examples_good=[r.get("name", "") for r in records[:3]],
                    files_affected=[r.get("file", "") for r in records],
                    source=f"Detected from {len(records)} classes in {dir_str}",
                    confidence="high" if len(records) >= 3 else "medium"
                ))

        # Detect function naming patterns (e.g., test_ prefix)
        func_prefixes: dict[str, list[dict[str, Any]]] = {}
        for record in manifest:
            if record.get("type") == "function":
                name = record.get("name", "")
                for prefix in ["test_", "get_", "set_", "is_", "has_",
                               "_", "__", "handle_", "on_"]:
                    if name.startswith(prefix):
                        if prefix not in func_prefixes:
                            func_prefixes[prefix] = []
                        func_prefixes[prefix].append(record)
                        break  # Only match first prefix

        # Create contracts for significant function prefixes
        for prefix, records in func_prefixes.items():
            if len(records) >= 5:  # Require more occurrences for functions
                purpose = {
                    "test_": "test functions",
                    "get_": "getter functions",
                    "set_": "setter functions",
                    "is_": "boolean check functions",
                    "has_": "boolean check functions",
                    "_": "private/protected functions",
                    "__": "dunder/magic methods",
                    "handle_": "event handler functions",
                    "on_": "callback functions"
                }.get(prefix, "functions")

                contracts.append(Contract(
                    name=f"{prefix}* Function Naming",
                    rule=f"Functions starting with '{prefix}' are {purpose}",
                    category="naming",
                    examples_good=[r.get("name", "") for r in records[:5]],
                    files_affected=list(set(r.get("file", "") for r in records))[:10],
                    source=f"Detected from {len(records)} functions",
                    confidence="high" if len(records) >= 10 else "medium"
                ))

        return contracts

    def detect_file_organization(self) -> list[Contract]:
        """Detect file organization contracts."""
        contracts = []
        manifest = self._load_manifest()

        # Group files by parent directory
        by_dir: dict[str, list[dict[str, Any]]] = {}
        for record in manifest:
            if record.get("type") == "file":
                parent = str(Path(record.get("path", "")).parent)
                if parent not in by_dir:
                    by_dir[parent] = []
                by_dir[parent].append(record)

        # Detect patterns in specific directories
        for dir_path, files in by_dir.items():
            if "definitions" in dir_path:
                contracts.append(Contract(
                    name="Definitions Directory Pattern",
                    rule=f"Files in {dir_path}/ contain auto-discovered component definitions",
                    category="organization",
                    files_affected=[f.get("path", "") for f in files],
                    source="Detected from directory structure",
                    confidence="high"
                ))
            elif "commands" in dir_path:
                contracts.append(Contract(
                    name="Commands Directory Pattern",
                    rule=f"Command implementations are organized in {dir_path}/",
                    category="organization",
                    files_affected=[f.get("path", "") for f in files],
                    source="Detected from directory structure",
                    confidence="high"
                ))
            elif "tests" in dir_path or "test" in dir_path:
                contracts.append(Contract(
                    name="Tests Directory Pattern",
                    rule=f"Test files are organized in {dir_path}/",
                    category="organization",
                    files_affected=[f.get("path", "") for f in files],
                    source="Detected from directory structure",
                    confidence="high"
                ))

        # Detect __init__.py pattern
        init_files = [r for r in manifest
                      if r.get("type") == "file" and r.get("path", "").endswith("__init__.py")]
        if init_files:
            contracts.append(Contract(
                name="Package Structure",
                rule="Python packages use __init__.py for module exports",
                category="organization",
                files_affected=[f.get("path", "") for f in init_files],
                source=f"Detected {len(init_files)} __init__.py files",
                confidence="high"
            ))

        return contracts

    def detect_type_patterns(self) -> list[Contract]:
        """Detect type-related contracts."""
        contracts = []
        manifest = self._load_manifest()

        # Look for functions that return specific types
        return_types: dict[str, list[dict[str, Any]]] = {}
        for record in manifest:
            if record.get("type") == "function" and record.get("returns"):
                ret = record["returns"]
                if ret not in return_types:
                    return_types[ret] = []
                return_types[ret].append(record)

        # Create contracts for common return types
        for ret_type, records in return_types.items():
            if len(records) >= 3 and ret_type not in ["None", "str", "int", "bool", "list", "dict"]:
                contracts.append(Contract(
                    name=f"Return Type: {ret_type}",
                    rule=f"Functions return {ret_type} for specific purposes",
                    category="type",
                    examples_good=[r.get("name", "") for r in records[:5]],
                    files_affected=list(set(r.get("file", "") for r in records)),
                    source=f"Detected {len(records)} functions returning {ret_type}",
                    confidence="medium"
                ))

        # Generator patterns
        generator_funcs = [r for r in manifest
                          if r.get("type") == "function" and r.get("is_generator")]
        if generator_funcs:
            contracts.append(Contract(
                name="Generator Pattern",
                rule="Certain functions yield values instead of returning them (streaming/lazy evaluation)",
                category="type",
                examples_good=[r.get("name", "") for r in generator_funcs[:5]],
                files_affected=list(set(r.get("file", "") for r in generator_funcs)),
                source=f"Detected {len(generator_funcs)} generator functions",
                confidence="high"
            ))

        # Async patterns
        async_funcs = [r for r in manifest
                      if r.get("type") == "function" and r.get("is_async")]
        if async_funcs:
            contracts.append(Contract(
                name="Async Pattern",
                rule="Async functions are used for IO-bound operations",
                category="type",
                examples_good=[r.get("name", "") for r in async_funcs[:5]],
                files_affected=list(set(r.get("file", "") for r in async_funcs)),
                source=f"Detected {len(async_funcs)} async functions",
                confidence="high"
            ))

        return contracts

    def detect_inheritance_patterns(self) -> list[Contract]:
        """Detect inheritance and base class patterns."""
        contracts = []
        manifest = self._load_manifest()

        # Find base classes
        base_classes: dict[str, list[dict[str, Any]]] = {}
        for record in manifest:
            if record.get("type") == "class":
                bases = record.get("bases", [])
                for base in bases:
                    if base not in base_classes:
                        base_classes[base] = []
                    base_classes[base].append(record)

        # Create contracts for common base classes
        for base, records in base_classes.items():
            if len(records) >= 2:
                contracts.append(Contract(
                    name=f"Inheritance: {base}",
                    rule=f"Classes extending {base} follow its interface contract",
                    category="type",
                    examples_good=[r.get("name", "") for r in records[:5]],
                    files_affected=list(set(r.get("file", "") for r in records)),
                    source=f"Detected {len(records)} classes inheriting from {base}",
                    confidence="high" if len(records) >= 3 else "medium"
                ))

        return contracts

    def detect_decorator_patterns(self) -> list[Contract]:
        """Detect decorator usage patterns."""
        contracts = []
        manifest = self._load_manifest()

        # Find decorated functions/classes
        decorators: dict[str, list[dict[str, Any]]] = {}
        for record in manifest:
            if record.get("type") in ["function", "class"]:
                record_decorators = record.get("decorators", [])
                for dec in record_decorators:
                    if dec not in decorators:
                        decorators[dec] = []
                    decorators[dec].append(record)

        # Create contracts for common decorators
        for dec, records in decorators.items():
            if len(records) >= 2:
                # Clean up decorator name for display
                dec_name = dec.split("(")[0] if "(" in dec else dec

                contracts.append(Contract(
                    name=f"Decorator: @{dec_name}",
                    rule=f"The @{dec_name} decorator is used consistently for specific purposes",
                    category="behavioral",
                    examples_good=[r.get("name", "") for r in records[:5]],
                    files_affected=list(set(r.get("file", "") for r in records)),
                    source=f"Detected {len(records)} uses of @{dec_name}",
                    confidence="high" if len(records) >= 3 else "medium"
                ))

        return contracts

    def detect_all(self) -> list[Contract]:
        """Run all detection methods."""
        contracts = []
        contracts.extend(self.detect_naming_conventions())
        contracts.extend(self.detect_file_organization())
        contracts.extend(self.detect_type_patterns())
        contracts.extend(self.detect_inheritance_patterns())
        contracts.extend(self.detect_decorator_patterns())
        return contracts
