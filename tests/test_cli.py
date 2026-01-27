"""Tests for Brief CLI."""

import pytest
from pathlib import Path
import tempfile
from typer.testing import CliRunner
from brief.cli import app
from brief.config import BRIEF_DIR, MANIFEST_FILE, RELATIONSHIPS_FILE, CONTEXT_DIR


runner = CliRunner()


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_directory_structure(self) -> None:
        """Test that init creates the full directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])

            assert result.exit_code == 0
            assert "Initialized Brief" in result.stdout

            brief_path = Path(tmpdir) / BRIEF_DIR
            assert brief_path.exists()
            assert (brief_path / MANIFEST_FILE).exists()
            assert (brief_path / CONTEXT_DIR).exists()
            assert (brief_path / CONTEXT_DIR / "modules").exists()
            assert (brief_path / CONTEXT_DIR / "files").exists()
            assert (brief_path / CONTEXT_DIR / "paths").exists()
            assert (brief_path / "config.json").exists()

    def test_init_fails_if_already_exists(self) -> None:
        """Test that init fails if .brief already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First init
            runner.invoke(app, ["init", tmpdir])

            # Second init should fail
            result = runner.invoke(app, ["init", tmpdir])

            assert result.exit_code == 1
            assert "already initialized" in result.stdout

    def test_init_force_overwrites(self) -> None:
        """Test that init --force reinitializes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First init
            runner.invoke(app, ["init", tmpdir])

            # Add a file to verify reinit
            brief_path = Path(tmpdir) / BRIEF_DIR
            test_file = brief_path / "test_marker.txt"
            test_file.write_text("marker")

            # Force reinit
            result = runner.invoke(app, ["init", tmpdir, "--force"])

            assert result.exit_code == 0
            assert "Initialized Brief" in result.stdout
            # Marker file should still exist (we don't delete on reinit)
            # but the config should be fresh


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self) -> None:
        """Test that main help displays."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Context infrastructure" in result.stdout

    def test_init_help(self) -> None:
        """Test that init help displays."""
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize" in result.stdout

    def test_reset_help(self) -> None:
        """Test that reset help displays."""
        result = runner.invoke(app, ["reset", "--help"])

        assert result.exit_code == 0
        assert "Clear Brief analysis cache" in result.stdout


class TestResetCommand:
    """Tests for the reset command."""

    def test_reset_clears_analysis_cache(self) -> None:
        """Test that reset clears manifest and relationships."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize
            runner.invoke(app, ["init", tmpdir])
            brief_path = Path(tmpdir) / BRIEF_DIR

            # Add some data to manifest
            manifest = brief_path / MANIFEST_FILE
            manifest.write_text('{"test": "data"}\n')

            relationships = brief_path / RELATIONSHIPS_FILE
            relationships.write_text('{"test": "rel"}\n')

            # Add an LLM description that should be preserved
            files_dir = brief_path / CONTEXT_DIR / "files"
            desc_file = files_dir / "test.md"
            desc_file.write_text("# Test description")

            # Run reset
            result = runner.invoke(app, ["reset", "-b", tmpdir])

            assert result.exit_code == 0
            assert "Reset complete" in result.stdout

            # Manifest and relationships should be empty
            assert manifest.read_text().strip() == ""
            assert relationships.read_text().strip() == ""

            # Description should still exist
            assert desc_file.exists()
            assert desc_file.read_text() == "# Test description"

    def test_reset_full_clears_llm_content(self) -> None:
        """Test that reset --full clears LLM content with confirmation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize
            runner.invoke(app, ["init", tmpdir])
            brief_path = Path(tmpdir) / BRIEF_DIR

            # Add an LLM description
            files_dir = brief_path / CONTEXT_DIR / "files"
            desc_file = files_dir / "test.md"
            desc_file.write_text("# Test description")

            # Run reset --full with -y to skip confirmation
            result = runner.invoke(app, ["reset", "-b", tmpdir, "--full", "-y"])

            assert result.exit_code == 0
            assert "Reset complete" in result.stdout

            # Description should be deleted
            assert not desc_file.exists()

    def test_reset_fails_without_brief(self) -> None:
        """Test that reset fails if Brief not initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["reset", "-b", tmpdir])

            assert result.exit_code == 1
            assert "not initialized" in result.output
