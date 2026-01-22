"""LLM-powered description generation for Brief."""
from .types import FunctionDescription, ClassDescription, FileDescription, ModuleDescription
from .generator import (
    extract_function_code,
    extract_class_code,
    describe_function,
    describe_class,
    describe_file,
    describe_module,
    format_function_description,
    format_class_description,
    format_file_description,
    format_module_description,
)
from .synthesis import synthesize_spec

__all__ = [
    "FunctionDescription",
    "ClassDescription",
    "FileDescription",
    "ModuleDescription",
    "extract_function_code",
    "extract_class_code",
    "describe_function",
    "describe_class",
    "describe_file",
    "describe_module",
    "format_function_description",
    "format_class_description",
    "format_file_description",
    "format_module_description",
    "synthesize_spec",
]
