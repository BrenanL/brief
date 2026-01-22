"""Tests for Brief CLI."""

import pytest
from pathlib import Path
import tempfile
from typer.testing import CliRunner
from brief.cli import app
from brief.config import BRIEF_DIR, MANIFEST_FILE, CONTEXT_DIR


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
