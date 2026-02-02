"""Tests for analysis engine."""
import pytest
from pathlib import Path
import tempfile
from brief.analysis.parser import PythonFileParser, compute_file_hash
from brief.analysis.manifest import ManifestBuilder
from brief.analysis.relationships import RelationshipExtractor

SAMPLE_CODE = '''
"""Sample module."""
from typing import List

class MyClass:
    """A sample class."""

    def method_one(self, x: int) -> str:
        """Do something."""
        return str(x)

    async def async_method(self) -> None:
        pass

def standalone_function(items: List[str], default: str = "none") -> int:
    """A module-level function."""
    return len(items)

def generator_func():
    yield 1
    yield 2
'''


class TestPythonFileParser:
    """Tests for the Python file parser."""

    @pytest.fixture
    def temp_python_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.py"
            file_path.write_text(SAMPLE_CODE)
            yield file_path, Path(tmpdir)

    def test_parser_parses_file(self, temp_python_file) -> None:
        """Test that parser can parse a Python file."""
        file_path, base_path = temp_python_file
        parser = PythonFileParser(file_path, base_path)
        assert parser.parse()

    def test_parser_extracts_classes(self, temp_python_file) -> None:
        """Test parser extracts class definitions."""
        file_path, base_path = temp_python_file
        parser = PythonFileParser(file_path, base_path)
        assert parser.parse()

        classes = list(parser.get_classes())
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        assert "method_one" in classes[0].methods
        assert "async_method" in classes[0].methods

    def test_parser_extracts_functions(self, temp_python_file) -> None:
        """Test parser extracts function definitions."""
        file_path, base_path = temp_python_file
        parser = PythonFileParser(file_path, base_path)
        assert parser.parse()

        functions = list(parser.get_functions())
        # 2 methods + 2 module-level = 4
        assert len(functions) == 4

        standalone = [f for f in functions if f.name == "standalone_function"][0]
        assert standalone.class_name is None
        assert len(standalone.params) == 2
        assert standalone.params[1].default == "'none'"

        generator = [f for f in functions if f.name == "generator_func"][0]
        assert generator.is_generator

    def test_parser_extracts_imports(self, temp_python_file) -> None:
        """Test parser extracts import statements."""
        file_path, base_path = temp_python_file
        parser = PythonFileParser(file_path, base_path)
        assert parser.parse()

        imports = list(parser.get_imports())
        assert len(imports) == 1
        module, level, names = imports[0]
        assert module == "typing"
        assert level == 0  # Absolute import
        assert "List" in names

    def test_parser_extracts_async_functions(self, temp_python_file) -> None:
        """Test parser correctly identifies async functions."""
        file_path, base_path = temp_python_file
        parser = PythonFileParser(file_path, base_path)
        assert parser.parse()

        functions = list(parser.get_functions())
        async_method = [f for f in functions if f.name == "async_method"][0]
        assert async_method.is_async

    def test_parser_extracts_file_record(self, temp_python_file) -> None:
        """Test parser creates file record."""
        file_path, base_path = temp_python_file
        parser = PythonFileParser(file_path, base_path)
        assert parser.parse()

        record = parser.get_file_record()
        assert record.type == "file"
        assert record.path == "sample.py"
        assert record.file_hash is not None


class TestManifestBuilder:
    """Tests for the manifest builder."""

    def test_manifest_builder_analyzes_directory(self) -> None:
        """Test manifest builder can analyze a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "module").mkdir()
            (base_path / "module" / "__init__.py").write_text("")
            (base_path / "module" / "core.py").write_text(SAMPLE_CODE)

            builder = ManifestBuilder(base_path)
            records = builder.analyze_directory()

            stats = builder.get_stats()
            assert stats["files"] == 2  # __init__.py and core.py
            assert stats["classes"] == 1
            assert stats["functions"] == 4

    def test_manifest_builder_excludes_patterns(self) -> None:
        """Test manifest builder respects exclude patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "good.py").write_text("x = 1")
            (base_path / "__pycache__").mkdir()
            (base_path / "__pycache__" / "bad.py").write_text("y = 2")

            builder = ManifestBuilder(base_path)
            records = builder.analyze_directory()

            stats = builder.get_stats()
            assert stats["files"] == 1  # Only good.py

    def test_manifest_builder_saves_manifest(self) -> None:
        """Test manifest builder saves to JSONL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "test.py").write_text(SAMPLE_CODE)
            brief_path = base_path / ".brief"
            brief_path.mkdir()

            builder = ManifestBuilder(base_path)
            builder.analyze_directory()
            builder.save_manifest(brief_path)

            manifest_file = brief_path / "manifest.jsonl"
            assert manifest_file.exists()


class TestRelationshipExtractor:
    """Tests for the relationship extractor."""

    def test_extractor_finds_local_imports(self) -> None:
        """Test extractor identifies local imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "module_a.py").write_text("from module_b import foo")
            (base_path / "module_b.py").write_text("def foo(): pass")

            extractor = RelationshipExtractor(base_path)
            relationships = extractor.extract_all()

            assert len(relationships) == 1
            assert relationships[0].from_file == "module_a.py"
            assert relationships[0].to_file == "module_b.py"

    def test_extractor_ignores_external_imports(self) -> None:
        """Test extractor ignores stdlib and third-party imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "test.py").write_text("import os\nimport json\nfrom typing import List")

            extractor = RelationshipExtractor(base_path)
            relationships = extractor.extract_all()

            assert len(relationships) == 0

    def test_extractor_dependency_methods(self) -> None:
        """Test get_dependencies and get_dependents methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "a.py").write_text("from b import x")
            (base_path / "b.py").write_text("x = 1")
            (base_path / "c.py").write_text("from b import x")

            extractor = RelationshipExtractor(base_path)
            extractor.extract_all()

            deps = extractor.get_dependencies("a.py")
            assert "b.py" in deps

            dependents = extractor.get_dependents("b.py")
            assert "a.py" in dependents
            assert "c.py" in dependents


class TestCallExtraction:
    """Tests for call relationship extraction."""

    def test_parser_extracts_calls(self) -> None:
        """Test parser extracts function calls."""
        code = '''
def helper():
    return 42

def main():
    result = helper()
    print(result)
    return result
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            calls = list(parser.get_calls())
            main_calls = [c for c in calls if c.from_func == "main"]

            # main() calls helper() and print()
            call_names = [c.to_func for c in main_calls]
            assert "helper" in call_names
            assert "print" in call_names

    def test_parser_extracts_method_calls(self) -> None:
        """Test parser extracts method calls with class context."""
        code = '''
class MyClass:
    def helper(self):
        return 1

    def main(self):
        x = self.helper()
        return x
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            calls = list(parser.get_calls())
            main_calls = [c for c in calls if c.from_func == "MyClass.main"]

            assert len(main_calls) > 0
            call_names = [c.to_func for c in main_calls]
            assert "self.helper" in call_names

    def test_parser_extracts_chained_calls(self) -> None:
        """Test parser extracts chained attribute calls."""
        code = '''
def process():
    result = obj.method().chain()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            calls = list(parser.get_calls())
            # Should extract obj.method (the first call in chain)
            call_names = [c.to_func for c in calls]
            assert "obj.method" in call_names

    def test_extractor_includes_calls(self) -> None:
        """Test relationship extractor includes call relationships."""
        code = '''
def helper():
    return 1

def main():
    return helper()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "test.py").write_text(code)

            extractor = RelationshipExtractor(base_path)
            relationships = extractor.extract_all()

            call_rels = [r for r in relationships if r.type == "calls"]
            assert len(call_rels) > 0

            main_calls = [r for r in call_rels if r.from_func == "main"]
            assert any(r.to_func == "helper" for r in main_calls)

    def test_extractor_callees_method(self) -> None:
        """Test get_callees returns functions called by a function."""
        code = '''
def a():
    return b() + c()

def b():
    return 1

def c():
    return 2
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "test.py").write_text(code)

            extractor = RelationshipExtractor(base_path)
            extractor.extract_all()

            callees = extractor.get_callees("a")
            assert "b" in callees
            assert "c" in callees

    def test_extractor_callers_method(self) -> None:
        """Test get_callers returns functions that call a function."""
        code = '''
def target():
    return 1

def caller1():
    return target()

def caller2():
    return target()
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "test.py").write_text(code)

            extractor = RelationshipExtractor(base_path)
            extractor.extract_all()

            callers = extractor.get_callers("target")
            assert "caller1" in callers
            assert "caller2" in callers


class TestParameterTypes:
    """Tests for positional-only, keyword-only, and mixed parameter parsing."""

    def test_parser_extracts_posonly_args(self) -> None:
        """Test parser handles positional-only args (before /)."""
        code = '''
def func(a, b, /, c):
    """Function with positional-only args."""
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            functions = list(parser.get_functions())
            assert len(functions) == 1
            func = functions[0]
            assert len(func.params) == 3
            assert func.params[0].name == "a"
            assert func.params[1].name == "b"
            assert func.params[2].name == "c"

    def test_parser_extracts_kwonly_args(self) -> None:
        """Test parser handles keyword-only args (after *)."""
        code = '''
def func(a, *, b, c=3):
    """Function with keyword-only args."""
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            functions = list(parser.get_functions())
            assert len(functions) == 1
            func = functions[0]
            assert len(func.params) == 3
            assert func.params[0].name == "a"
            assert func.params[1].name == "b"
            assert func.params[1].default is None
            assert func.params[2].name == "c"
            assert func.params[2].default == "3"

    def test_parser_mixed_param_types(self) -> None:
        """Test parser with all parameter types combined."""
        code = '''
def func(a, b=1, /, c=2, *, d, e=4):
    """Function with all parameter types."""
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            functions = list(parser.get_functions())
            assert len(functions) == 1
            func = functions[0]
            assert len(func.params) == 5
            # Positional-only: a (no default), b (default=1)
            assert func.params[0].name == "a"
            assert func.params[0].default is None
            assert func.params[1].name == "b"
            assert func.params[1].default == "1"
            # Regular: c (default=2)
            assert func.params[2].name == "c"
            assert func.params[2].default == "2"
            # Keyword-only: d (no default), e (default=4)
            assert func.params[3].name == "d"
            assert func.params[3].default is None
            assert func.params[4].name == "e"
            assert func.params[4].default == "4"

    def test_parser_posonly_with_defaults(self) -> None:
        """Test positional-only args where only some have defaults."""
        code = '''
def func(a, b=10, /):
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            functions = list(parser.get_functions())
            func = functions[0]
            assert len(func.params) == 2
            assert func.params[0].name == "a"
            assert func.params[0].default is None
            assert func.params[1].name == "b"
            assert func.params[1].default == "10"

    def test_parser_kwonly_with_type_hints(self) -> None:
        """Test keyword-only args with type annotations."""
        code = '''
def func(*, name: str, count: int = 0, flag: bool = False):
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            functions = list(parser.get_functions())
            func = functions[0]
            assert len(func.params) == 3
            assert func.params[0].name == "name"
            assert func.params[0].type_hint == "str"
            assert func.params[0].default is None
            assert func.params[1].name == "count"
            assert func.params[1].type_hint == "int"
            assert func.params[1].default == "0"
            assert func.params[2].name == "flag"
            assert func.params[2].type_hint == "bool"
            assert func.params[2].default == "False"

    def test_parser_no_crash_on_empty_args_with_defaults(self) -> None:
        """Regression test: functions with only posonlyargs shouldn't crash on defaults."""
        code = '''
def func(a=1, b=2, /):
    pass
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text(code)

            parser = PythonFileParser(file_path, Path(tmpdir))
            assert parser.parse()

            functions = list(parser.get_functions())
            func = functions[0]
            assert len(func.params) == 2
            assert func.params[0].default == "1"
            assert func.params[1].default == "2"


class TestFileHash:
    """Tests for file hashing."""

    def test_file_hash_changes_with_content(self) -> None:
        """Test file hash changes when content changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text("x = 1")
            hash1 = compute_file_hash(file_path)

            file_path.write_text("x = 2")
            hash2 = compute_file_hash(file_path)

            assert hash1 != hash2

    def test_file_hash_consistent(self) -> None:
        """Test file hash is consistent for same content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.py"
            file_path.write_text("x = 1")
            hash1 = compute_file_hash(file_path)
            hash2 = compute_file_hash(file_path)

            assert hash1 == hash2
