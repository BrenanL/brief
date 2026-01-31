"""Log analysis commands for Brief."""

import typer
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Optional

from ..logging import parse_log_file, get_session_metrics, get_logs_path

app = typer.Typer(help="Analyze Brief command usage logs.")
console = Console()


@app.command("show")
def logs_show(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of recent lines to show"),
    session_only: bool = typer.Option(False, "--sessions", help="Show only session events"),
):
    """Show recent log entries."""
    entries = parse_log_file()

    if not entries:
        console.print("[yellow]No log entries found.[/yellow]")
        return

    if session_only:
        entries = [e for e in entries if e["is_session_event"]]

    # Show last N entries
    for entry in entries[-lines:]:
        ts = entry["timestamp"][:19]  # Trim microseconds
        cmd = entry["command"]
        args = entry["args"][:60] + "..." if len(entry["args"]) > 60 else entry["args"]

        if entry["is_session_event"]:
            console.print(f"[bold blue]{ts}[/] [yellow]{cmd}[/] {args}")
        elif cmd in ("context get", "q"):
            console.print(f"[bold blue]{ts}[/] [green]{cmd}[/] {args}")
        else:
            console.print(f"[dim]{ts}[/] {cmd} {args}")


@app.command("metrics")
def logs_metrics(
    since: Optional[str] = typer.Option(None, "--since", help="Analyze logs since date (YYYY-MM-DD)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show usage metrics from logs.

    Calculates:
    - brief context get usage count
    - Task command count
    - Context get ratio (higher is better)
    """
    entries = parse_log_file()

    if not entries:
        console.print("[yellow]No log entries found.[/yellow]")
        return

    # Filter by date if specified
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            entries = [
                e for e in entries
                if datetime.fromisoformat(e["timestamp"][:19]) >= since_dt
            ]
        except ValueError:
            console.print(f"[red]Invalid date format: {since}. Use YYYY-MM-DD.[/red]")
            raise typer.Exit(1)

    metrics = get_session_metrics(entries)

    if json_output:
        import json
        console.print(json.dumps(metrics, indent=2, default=str))
        return

    # Display as table
    table = Table(title="Brief Usage Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Commands", str(metrics["total_commands"]))
    table.add_row("context get Calls", str(metrics["context_get_count"]))
    table.add_row("Task Commands", str(metrics["task_commands"]))
    table.add_row("Context Get Ratio", f"{metrics['context_get_ratio']:.2%}")
    table.add_row("Sessions Logged", str(len(metrics["sessions"])))

    console.print(table)

    # Interpretation
    ratio = metrics["context_get_ratio"]
    if ratio >= 0.3:
        console.print("\n[green]Good Brief adoption![/green] Agent is using context get frequently.")
    elif ratio >= 0.1:
        console.print("\n[yellow]Moderate Brief usage.[/yellow] Room for improvement.")
    else:
        console.print("\n[red]Low Brief usage.[/red] Agent may be over-relying on Read/Grep/Glob.")


@app.command("clear")
def logs_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear the command log file."""
    logs_path = get_logs_path()
    log_file = logs_path / "commands.log"

    if not log_file.exists():
        console.print("[yellow]No log file to clear.[/yellow]")
        return

    if not force:
        confirm = typer.confirm("Clear all log entries?")
        if not confirm:
            raise typer.Abort()

    log_file.unlink()
    console.print("[green]Log file cleared.[/green]")


@app.command("export")
def logs_export(
    output: Path = typer.Argument(..., help="Output file path (.json or .csv)"),
    since: Optional[str] = typer.Option(None, "--since", help="Export logs since date (YYYY-MM-DD)"),
):
    """Export logs to JSON or CSV file."""
    entries = parse_log_file()

    if not entries:
        console.print("[yellow]No log entries to export.[/yellow]")
        return

    # Filter by date if specified
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            entries = [
                e for e in entries
                if datetime.fromisoformat(e["timestamp"][:19]) >= since_dt
            ]
        except ValueError:
            console.print(f"[red]Invalid date format: {since}. Use YYYY-MM-DD.[/red]")
            raise typer.Exit(1)

    if output.suffix == ".json":
        import json
        with output.open("w") as f:
            json.dump(entries, f, indent=2)
    elif output.suffix == ".csv":
        import csv
        with output.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "command", "args", "is_session_event"])
            writer.writeheader()
            writer.writerows(entries)
    else:
        console.print("[red]Output must be .json or .csv[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Exported {len(entries)} entries to {output}[/green]")
