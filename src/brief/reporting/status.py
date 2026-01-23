"""Status reporting for Brief - project dashboard data and display."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import (
    MANIFEST_FILE, RELATIONSHIPS_FILE, MEMORY_FILE,
    TASKS_FILE, ACTIVE_TASK_FILE, CONTEXT_DIR
)
from ..storage import read_json, read_jsonl
from .coverage import find_stale_files, find_stale_descriptions


@dataclass
class StatusData:
    """Data container for project status."""
    # Manifest stats
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0

    # Description stats
    described_files: int = 0
    module_descriptions: int = 0

    # Relationship stats
    import_count: int = 0
    call_count: int = 0

    # Memory stats
    pattern_count: int = 0

    # Execution paths
    path_names: list[str] = field(default_factory=list)

    # Task stats
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    done_tasks: int = 0
    active_task_id: str | None = None
    active_task_title: str | None = None

    # Freshness
    stale_files: list[dict[str, Any]] = field(default_factory=list)
    stale_descriptions: list[dict[str, Any]] = field(default_factory=list)

    # Config
    version: str = "unknown"
    default_model: str = "not set"
    exclude_patterns: list[str] = field(default_factory=list)


class StatusReporter:
    """Gathers and reports project status data."""

    def __init__(self, brief_path: Path, base_path: Path):
        self.brief_path = brief_path
        self.base_path = base_path
        self._data: StatusData | None = None

    def gather(self) -> StatusData:
        """Gather all status data from brief directory."""
        data = StatusData()

        # Load config
        config_file = self.brief_path / "config.json"
        config = read_json(config_file) if config_file.exists() else {}
        data.version = config.get("version", "unknown")
        data.default_model = config.get("default_model", "not set")
        data.exclude_patterns = config.get("exclude_patterns", [])

        # Gather manifest stats
        manifest_file = self.brief_path / MANIFEST_FILE
        if manifest_file.exists():
            for record in read_jsonl(manifest_file):
                if record["type"] == "file":
                    data.file_count += 1
                elif record["type"] == "class":
                    data.class_count += 1
                elif record["type"] == "function":
                    data.function_count += 1

        # Count description files on disk
        files_dir = self.brief_path / CONTEXT_DIR / "files"
        if files_dir.exists():
            data.described_files = len(list(files_dir.glob("*.md")))

        # Count module descriptions
        modules_dir = self.brief_path / CONTEXT_DIR / "modules"
        if modules_dir.exists():
            data.module_descriptions = len(list(modules_dir.glob("*.md")))

        # Gather relationship stats
        rel_file = self.brief_path / RELATIONSHIPS_FILE
        if rel_file.exists():
            for rel in read_jsonl(rel_file):
                if rel.get("type") == "imports":
                    data.import_count += 1
                elif rel.get("type") == "calls":
                    data.call_count += 1

        # Memory patterns
        mem_file = self.brief_path / MEMORY_FILE
        if mem_file.exists():
            data.pattern_count = sum(1 for _ in read_jsonl(mem_file))

        # Execution paths
        paths_dir = self.brief_path / CONTEXT_DIR / "paths"
        if paths_dir.exists():
            data.path_names = [f.stem for f in paths_dir.glob("*.md")]

        # Task stats
        task_file = self.brief_path / TASKS_FILE
        if task_file.exists():
            for task in read_jsonl(task_file):
                status_val = task.get("status", "")
                if status_val == "pending":
                    data.pending_tasks += 1
                elif status_val == "in_progress":
                    data.in_progress_tasks += 1
                elif status_val == "done":
                    data.done_tasks += 1

        # Active task
        active_file = self.brief_path / ACTIVE_TASK_FILE
        if active_file.exists():
            data.active_task_id = active_file.read_text().strip()
            if task_file.exists():
                for task in read_jsonl(task_file):
                    if task.get("id") == data.active_task_id:
                        data.active_task_title = task.get("title", "")
                        break

        # Freshness
        data.stale_files = find_stale_files(self.brief_path, self.base_path)
        data.stale_descriptions = find_stale_descriptions(self.brief_path, self.base_path)

        self._data = data
        return data

    @property
    def data(self) -> StatusData:
        """Get status data, gathering if not already done."""
        if self._data is None:
            self.gather()
        return self._data  # type: ignore

    def format_plain(self) -> str:
        """Format status as plain text."""
        d = self.data
        lines = [
            "BRIEF STATUS DASHBOARD",
            "=" * 60,
            "",
            "Codebase Analysis",
            "-" * 30,
            f"  Files analyzed:    {d.file_count}",
            f"  Classes:           {d.class_count}",
            f"  Functions:         {d.function_count}",
            f"  Import relations:  {d.import_count}",
            f"  Call relations:    {d.call_count}",
            "",
            "Context Coverage",
            "-" * 30,
            f"  File descriptions: {d.described_files}/{d.file_count}",
            f"  Module summaries:  {d.module_descriptions}",
            f"  Execution paths:   {len(d.path_names)}",
            f"  Memory patterns:   {d.pattern_count}",
        ]

        if d.path_names:
            path_preview = ", ".join(d.path_names[:5])
            if len(d.path_names) > 5:
                path_preview += f" +{len(d.path_names) - 5} more"
            lines.append(f"    Paths: {path_preview}")

        lines.extend([
            "",
            "Freshness",
            "-" * 30,
            f"  Stale files:       {len(d.stale_files)} (changed since analysis)" if d.stale_files else "  Stale files:       0 (all up to date)",
            f"  Stale descriptions: {len(d.stale_descriptions)} (need regeneration)" if d.stale_descriptions else "  Stale descriptions: 0 (all current)",
            "",
            "Tasks",
            "-" * 30,
            f"  Pending:           {d.pending_tasks}",
            f"  In Progress:       {d.in_progress_tasks}",
            f"  Done:              {d.done_tasks}",
        ])

        if d.active_task_id:
            lines.append(f"  Active:            {d.active_task_id} - {d.active_task_title}")
        else:
            lines.append("  Active:            (none)")

        lines.extend([
            "",
            "Configuration",
            "-" * 30,
            f"  Version:           {d.version}",
            f"  Default model:     {d.default_model}",
            f"  Exclude patterns:  {len(d.exclude_patterns)}",
        ])

        # Suggested actions
        actions = self.get_suggested_actions()
        if actions:
            lines.extend(["", "Suggested Actions:"])
            for action in actions:
                lines.append(f"  {action}")

        return "\n".join(lines)

    def format_rich(self) -> None:
        """Print status with rich formatting."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box

        d = self.data
        console = Console()

        console.print()
        console.print(Panel.fit("[bold blue]BRIEF STATUS DASHBOARD[/bold blue]", box=box.DOUBLE))
        console.print()

        # Codebase Analysis table
        analysis_table = Table(title="Codebase Analysis", box=box.ROUNDED, show_header=False)
        analysis_table.add_column("Metric", style="cyan")
        analysis_table.add_column("Value", justify="right")
        analysis_table.add_row("Files analyzed", str(d.file_count))
        analysis_table.add_row("Classes", str(d.class_count))
        analysis_table.add_row("Functions", str(d.function_count))
        analysis_table.add_row("Import relations", str(d.import_count))
        analysis_table.add_row("Call relations", str(d.call_count))
        console.print(analysis_table)
        console.print()

        # Context Coverage table
        coverage_table = Table(title="Context Coverage", box=box.ROUNDED, show_header=False)
        coverage_table.add_column("Metric", style="cyan")
        coverage_table.add_column("Value", justify="right")

        # Color code based on coverage percentage
        desc_pct = (d.described_files / d.file_count * 100) if d.file_count > 0 else 0
        desc_color = "green" if desc_pct == 100 else ("yellow" if desc_pct >= 50 else "red")
        coverage_table.add_row("File descriptions", f"[{desc_color}]{d.described_files}/{d.file_count}[/{desc_color}]")
        coverage_table.add_row("Module summaries", str(d.module_descriptions))
        coverage_table.add_row("Execution paths", str(len(d.path_names)))
        coverage_table.add_row("Memory patterns", str(d.pattern_count))
        console.print(coverage_table)

        if d.path_names:
            path_preview = ", ".join(d.path_names[:5])
            if len(d.path_names) > 5:
                path_preview += f" +{len(d.path_names) - 5} more"
            console.print(f"  [dim]Paths: {path_preview}[/dim]")
        console.print()

        # Freshness table
        freshness_table = Table(title="Freshness", box=box.ROUNDED, show_header=False)
        freshness_table.add_column("Metric", style="cyan")
        freshness_table.add_column("Status", justify="right")

        if d.stale_files:
            freshness_table.add_row("Stale files", f"[yellow]{len(d.stale_files)}[/yellow] (changed since analysis)")
        else:
            freshness_table.add_row("Stale files", "[green]0[/green] (all up to date)")

        if d.stale_descriptions:
            freshness_table.add_row("Stale descriptions", f"[yellow]{len(d.stale_descriptions)}[/yellow] (need regeneration)")
        else:
            freshness_table.add_row("Stale descriptions", "[green]0[/green] (all current)")

        console.print(freshness_table)
        console.print()

        # Tasks table
        tasks_table = Table(title="Tasks", box=box.ROUNDED, show_header=False)
        tasks_table.add_column("Status", style="cyan")
        tasks_table.add_column("Count", justify="right")
        tasks_table.add_row("Pending", f"[yellow]{d.pending_tasks}[/yellow]" if d.pending_tasks else "0")
        tasks_table.add_row("In Progress", f"[blue]{d.in_progress_tasks}[/blue]" if d.in_progress_tasks else "0")
        tasks_table.add_row("Done", f"[green]{d.done_tasks}[/green]" if d.done_tasks else "0")

        if d.active_task_id:
            tasks_table.add_row("Active", f"[bold]{d.active_task_id}[/bold] - {d.active_task_title}")
        else:
            tasks_table.add_row("Active", "[dim](none)[/dim]")

        console.print(tasks_table)
        console.print()

        # Configuration
        config_table = Table(title="Configuration", box=box.ROUNDED, show_header=False)
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", justify="right")
        config_table.add_row("Version", d.version)
        config_table.add_row("Default model", d.default_model)
        config_table.add_row("Exclude patterns", str(len(d.exclude_patterns)))
        console.print(config_table)
        console.print()

        # Suggested actions
        actions = self.get_suggested_actions()
        if actions:
            console.print("[bold]Suggested Actions:[/bold]")
            for action in actions:
                console.print(f"  [yellow]{action}[/yellow]")

    def get_suggested_actions(self) -> list[str]:
        """Get list of suggested actions based on current status."""
        d = self.data
        actions: list[str] = []

        if d.stale_files:
            actions.append("brief analyze refresh - update stale files")
        if d.stale_descriptions:
            actions.append("brief describe batch - regenerate stale descriptions")
        if d.pending_tasks > 0 and not d.active_task_id:
            actions.append("brief task list - see pending tasks")

        return actions
