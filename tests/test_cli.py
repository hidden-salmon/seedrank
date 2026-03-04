"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from seedrank.cli import app
from seedrank.data.db import get_db_path, init_db

runner = CliRunner()

EXAMPLE_CONFIG = Path(__file__).parent.parent / "examples" / "seedrank.config.yaml"


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "seedrank" in result.output.lower()

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestInitCommand:
    """Test the init subcommand."""

    def test_init_creates_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        result = runner.invoke(app, ["init", "-o", str(workspace)])
        assert result.exit_code == 0
        assert (workspace / ".claude" / "seedrank.md").exists()
        assert (workspace / "data" / "seedrank.db").exists()
        assert (workspace / "pipeline" / "state.yaml").exists()

    def test_init_creates_directories(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        runner.invoke(app, ["init", "-o", str(workspace)])
        assert (workspace / "data").is_dir()
        assert (workspace / "sessions").is_dir()
        assert (workspace / "briefs").is_dir()
        assert (workspace / "content").is_dir()
        assert (workspace / "research").is_dir()

    def test_init_claude_md_content(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        runner.invoke(app, ["init", "-o", str(workspace)])
        content = (workspace / ".claude" / "seedrank.md").read_text()
        assert "Seedrank System" in content
        assert "seedrank research keywords" in content
        assert "Session Protocol" in content
        assert "Content Writing Principles" in content
        assert "Comparison Article Rules" in content
        assert "Lanham Act" in content

    def test_init_with_config(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # Copy example config to workspace
        import shutil

        shutil.copy2(EXAMPLE_CONFIG, workspace / "seedrank.config.yaml")
        runner.invoke(app, ["init", "-o", str(workspace)])
        content = (workspace / ".claude" / "seedrank.md").read_text()
        assert "Moonbeam" in content

    def test_init_state_yaml(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        runner.invoke(app, ["init", "-o", str(workspace)])
        state = yaml.safe_load((workspace / "pipeline" / "state.yaml").read_text())
        assert state["phase"] == "research"
        assert "next_action" in state


class TestStatusCommand:
    """Test the status subcommand."""

    def test_status_with_config_and_db(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        import shutil

        shutil.copy2(EXAMPLE_CONFIG, workspace / "seedrank.config.yaml")
        runner.invoke(app, ["init", "-o", str(workspace)])

        result = runner.invoke(
            app,
            [
                "status",
                "-c",
                str(workspace / "seedrank.config.yaml"),
                "-w",
                str(workspace),
            ],
        )
        assert result.exit_code == 0
        assert "Moonbeam" in result.output


class TestValidateCommand:
    """Test the validate subcommand."""

    def test_validate_config(self) -> None:
        result = runner.invoke(app, ["validate", "config", "-c", str(EXAMPLE_CONFIG)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_research_empty_db(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        (workspace / "data").mkdir()
        init_db(get_db_path(workspace))
        result = runner.invoke(app, ["validate", "research", "-w", str(workspace)])
        assert result.exit_code == 0


class TestSessionCommand:
    """Test session start/end commands."""

    def test_session_end(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # Create required files
        (workspace / "seedrank.config.yaml").write_text(
            yaml.dump({"product": {"name": "Test", "domain": "test.com"}}),
            encoding="utf-8",
        )
        (workspace / "pipeline").mkdir()
        (workspace / "pipeline" / "state.yaml").write_text(
            yaml.dump({"phase": "research"}), encoding="utf-8"
        )
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(workspace)
            result = runner.invoke(app, ["session", "end", "Test session summary"])
            assert result.exit_code == 0
            assert (workspace / "sessions").is_dir()
            logs = list((workspace / "sessions").glob("*.md"))
            assert len(logs) == 1
            assert "Test session summary" in logs[0].read_text()
        finally:
            os.chdir(old_cwd)
