"""Tests for markdown parser."""
import pytest
from pathlib import Path
import tempfile
import shutil
from brief.analysis.markdown import MarkdownParser, is_dated_filename, MarkdownFileRecord


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    shutil.rmtree(tmpdir)


class TestMarkdownParser:
    """Tests for MarkdownParser class."""

    def test_parse_basic_markdown(self, temp_dir):
        """Test parsing markdown with headings."""
        md_file = temp_dir / "test.md"
        md_file.write_text("""# Main Title

This is the first paragraph with some content.

## Section One

Content here.

### Subsection

More content.

## Section Two

Final content.
""")
        parser = MarkdownParser(md_file, temp_dir)
        assert parser.parse() is True

        record = parser.get_record()
        assert record.title == "Main Title"
        assert "Main Title" in record.headings
        assert "Section One" in record.headings
        assert "Subsection" in record.headings
        assert "Section Two" in record.headings
        assert record.first_paragraph == "This is the first paragraph with some content."

    def test_extract_title_from_first_h1(self, temp_dir):
        """Test that title comes from first h1 heading."""
        md_file = temp_dir / "test.md"
        md_file.write_text("""## Not a title

# Actual Title

## Another section
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.title == "Actual Title"

    def test_no_h1_uses_filename(self, temp_dir):
        """Test files without h1 use filename as title."""
        md_file = temp_dir / "my-document.md"
        md_file.write_text("""## Section One

Some content.

## Section Two

More content.
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.title == "my-document"  # Stem of filename

    def test_skip_h5_h6_headings(self, temp_dir):
        """Test that h5 and h6 headings are excluded."""
        md_file = temp_dir / "test.md"
        md_file.write_text("""# Title

## H2 Heading

### H3 Heading

#### H4 Heading

##### H5 Heading

###### H6 Heading
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert "H2 Heading" in record.headings
        assert "H3 Heading" in record.headings
        assert "H4 Heading" in record.headings
        assert "H5 Heading" not in record.headings
        assert "H6 Heading" not in record.headings

    def test_extract_first_paragraph(self, temp_dir):
        """Test first paragraph extraction."""
        md_file = temp_dir / "test.md"
        md_file.write_text("""# Title

This is the first paragraph that should be captured.

This is the second paragraph that should NOT be captured.
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.first_paragraph == "This is the first paragraph that should be captured."

    def test_empty_file(self, temp_dir):
        """Test handling empty files."""
        md_file = temp_dir / "empty.md"
        md_file.write_text("")

        parser = MarkdownParser(md_file, temp_dir)
        assert parser.parse() is True

        record = parser.get_record()
        assert record.title == "empty"  # Uses filename
        assert record.headings == []
        assert record.first_paragraph is None

    def test_file_with_only_code_blocks(self, temp_dir):
        """Test handling files with only code blocks."""
        md_file = temp_dir / "code-only.md"
        md_file.write_text("""```python
def hello():
    print("world")
```

```bash
echo "hello"
```
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.title == "code-only"
        assert record.headings == []

    def test_first_paragraph_skips_empty_lines(self, temp_dir):
        """Test that empty lines before first paragraph are skipped."""
        md_file = temp_dir / "test.md"
        md_file.write_text("""# Title



This is after some empty lines.
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.first_paragraph == "This is after some empty lines."

    def test_first_paragraph_not_heading(self, temp_dir):
        """Test that headings are not captured as first paragraph."""
        md_file = temp_dir / "test.md"
        md_file.write_text("""# Title

## Subheading

Actual paragraph.
""")
        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.first_paragraph == "Actual paragraph."

    def test_file_hash_computed(self, temp_dir):
        """Test that file hash is computed."""
        md_file = temp_dir / "test.md"
        md_file.write_text("# Title\n\nContent.")

        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.file_hash is not None
        assert len(record.file_hash) == 32  # MD5 hex length

    def test_relative_path_in_record(self, temp_dir):
        """Test that record contains relative path."""
        subdir = temp_dir / "docs"
        subdir.mkdir()
        md_file = subdir / "test.md"
        md_file.write_text("# Title")

        parser = MarkdownParser(md_file, temp_dir)
        parser.parse()

        record = parser.get_record()
        assert record.path == "docs/test.md"


class TestIsDatedFilename:
    """Tests for is_dated_filename function."""

    def test_iso_date_format(self):
        """Test YYYY-MM-DD format."""
        assert is_dated_filename("report-2024-01-15.md") is True
        assert is_dated_filename("2024-12-31-summary.md") is True
        assert is_dated_filename("notes-2023-06-01-meeting.md") is True

    def test_compact_date_format(self):
        """Test YYYYMMDD format."""
        assert is_dated_filename("report-20240115.md") is True
        assert is_dated_filename("20231231-summary.md") is True

    def test_no_date(self):
        """Test filenames without dates."""
        assert is_dated_filename("README.md") is False
        assert is_dated_filename("design-doc.md") is False
        assert is_dated_filename("api-reference.md") is False

    def test_partial_date_not_matched(self):
        """Test that partial dates don't match."""
        assert is_dated_filename("version-2024.md") is False
        assert is_dated_filename("2024-report.md") is False

    def test_various_separators(self):
        """Test dates with different separators."""
        assert is_dated_filename("report_2024-01-15.md") is True
        assert is_dated_filename("report.2024-01-15.md") is True


class TestMarkdownFileRecord:
    """Tests for MarkdownFileRecord dataclass."""

    def test_record_creation(self):
        """Test creating a record."""
        record = MarkdownFileRecord(
            path="docs/test.md",
            title="Test Document",
            headings=["Test Document", "Section 1"],
            heading_details=[],
            first_paragraph="Introduction text.",
            file_hash="abc123"
        )

        assert record.path == "docs/test.md"
        assert record.title == "Test Document"
        assert len(record.headings) == 2
        assert record.first_paragraph == "Introduction text."
        assert record.file_hash == "abc123"

    def test_record_defaults(self):
        """Test record default values."""
        record = MarkdownFileRecord(
            path="test.md",
            title="Test",
            headings=[],
            heading_details=[],
            file_hash="abc"
        )

        assert record.first_paragraph is None
