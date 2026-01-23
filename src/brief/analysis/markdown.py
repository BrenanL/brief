"""Markdown file parser for Brief - extracts structure from documentation files."""
import re
from pathlib import Path
from dataclasses import dataclass, field
from .parser import compute_file_hash


@dataclass
class MarkdownHeading:
    """A heading extracted from a markdown file."""
    level: int  # 1-6 for # to ######
    text: str
    line: int


@dataclass
class MarkdownFileRecord:
    """Record for a parsed markdown file."""
    path: str
    title: str | None
    headings: list[str]  # Just the text, for searchability
    heading_details: list[MarkdownHeading]  # Full details
    file_hash: str
    first_paragraph: str | None = None  # First non-heading text block


class MarkdownParser:
    """Parser for markdown files - extracts title and heading structure."""

    # Regex for ATX-style headings (# Heading)
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#*)?$', re.MULTILINE)

    # Regex for the first paragraph (non-empty, non-heading line after title)
    PARAGRAPH_PATTERN = re.compile(r'^(?!#|\s*$)(.+)$', re.MULTILINE)

    def __init__(self, file_path: Path, base_path: Path):
        self.file_path = file_path
        self.base_path = base_path
        self.content: str = ""
        self._headings: list[MarkdownHeading] = []
        self._title: str | None = None
        self._first_paragraph: str | None = None

    def parse(self) -> bool:
        """Parse the markdown file. Returns True if successful."""
        try:
            self.content = self.file_path.read_text(encoding='utf-8')
        except Exception:
            return False

        self._extract_headings()
        self._extract_first_paragraph()
        return True

    def _extract_headings(self) -> None:
        """Extract all headings from the content."""
        self._headings = []

        for line_num, line in enumerate(self.content.split('\n'), 1):
            match = self.HEADING_PATTERN.match(line.strip())
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()

                # First h1 becomes the title
                if level == 1 and self._title is None:
                    self._title = text

                # Only track h1-h4 for searchability (h5/h6 too granular)
                if level <= 4:
                    self._headings.append(MarkdownHeading(
                        level=level,
                        text=text,
                        line=line_num
                    ))

    def _extract_first_paragraph(self) -> None:
        """Extract the first non-heading paragraph as a summary."""
        lines = self.content.split('\n')
        in_code_block = False
        found_title = False

        for line in lines:
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Skip empty lines
            if not line.strip():
                continue

            # Skip headings
            if self.HEADING_PATTERN.match(line.strip()):
                found_title = True
                continue

            # Skip frontmatter markers
            if line.strip() == '---':
                continue

            # Found first paragraph after title
            if found_title:
                self._first_paragraph = line.strip()
                break

    @property
    def title(self) -> str | None:
        """Get the document title (first h1) or None."""
        return self._title

    @property
    def headings(self) -> list[MarkdownHeading]:
        """Get all extracted headings."""
        return self._headings

    @property
    def heading_texts(self) -> list[str]:
        """Get just the heading text strings for searchability."""
        return [h.text for h in self._headings]

    @property
    def first_paragraph(self) -> str | None:
        """Get the first paragraph text."""
        return self._first_paragraph

    def get_record(self) -> MarkdownFileRecord:
        """Get the file record for the manifest."""
        rel_path = str(self.file_path.relative_to(self.base_path))

        return MarkdownFileRecord(
            path=rel_path,
            title=self._title or self.file_path.stem,  # Fallback to filename
            headings=self.heading_texts,
            heading_details=self._headings,
            file_hash=compute_file_hash(self.file_path),
            first_paragraph=self._first_paragraph
        )


def is_dated_filename(filename: str) -> bool:
    """Check if filename contains a date pattern (YYYY-MM-DD or similar).

    These files are typically ephemeral (session logs, status reports).
    """
    # YYYY-MM-DD pattern
    if re.search(r'\d{4}-\d{2}-\d{2}', filename):
        return True
    # YYYYMMDD pattern
    if re.search(r'\d{8}', filename):
        return True
    return False
