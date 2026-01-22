"""Type definitions for description generation.

These types mirror the BAML types and can be used as fallbacks
when the BAML client is not available.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FunctionDescription:
    """Description of a function."""
    purpose: str
    behavior: str
    inputs: str
    outputs: str
    side_effects: Optional[str] = None


@dataclass
class ClassDescription:
    """Description of a class."""
    purpose: str
    responsibility: str
    key_methods: str
    state: Optional[str] = None
    relationships: Optional[str] = None


@dataclass
class FileDescription:
    """Description of a file."""
    purpose: str
    contents: str
    role: str
    dependencies: str
    exports: str


@dataclass
class ModuleDescription:
    """Description of a module."""
    purpose: str
    components: str
    architecture: str
    public_api: str
