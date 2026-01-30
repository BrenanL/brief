"""
Claude Code Orchestrator

General-purpose orchestrator for queuing and running Claude Code headless sessions
with proper isolation, parallelism, tracking, and cleanup.

See ORCHESTRATOR_DESIGN.md for full documentation.

Usage:
    from orchestrator import ClaudeOrchestrator, ClaudeJob

    orch = ClaudeOrchestrator(
        temp_dir="/tmp/claude-runs",
        manifest_path="results/manifest.jsonl",
        max_workers=2,
    )
    orch.add_job(ClaudeJob(job_id="test-1", prompt="Hello", repo_path="/path/to/repo"))
    entries = orch.run()
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional


@dataclass
class ClaudeJob:
    """A single Claude Code headless run to execute."""

    job_id: str
    prompt: str
    repo_path: str              # Local path to git clone from
    repo_ref: str = "HEAD"      # Git ref to checkout

    # Claude Code flags
    max_turns: int = 25
    max_budget: float = 2.0
    timeout: int = 600          # Hard kill timeout in seconds
    model: Optional[str] = None
    append_system_prompt: Optional[str] = None
    allowed_tools: Optional[list] = None
    disallowed_tools: Optional[list] = None

    # Environment customization
    claude_md_source: Optional[str] = None      # Path to file to copy as CLAUDE.md
    settings_json: Optional[dict] = None        # Content for .claude/settings.json
    setup_fn: Optional[Callable] = None         # Runs after clone: setup_fn(work_dir)
    overlay_paths: Optional[dict] = None        # {src_path: relative_dest_in_clone}

    # Environment overrides for subprocess (merged into os.environ)
    env_overrides: Optional[dict] = None

    # Passthrough metadata (stored in manifest, not used by orchestrator)
    metadata: dict = field(default_factory=dict)


@dataclass
class ManifestEntry:
    """One line in the manifest JSONL. Latest entry per job_id wins."""

    job_id: str
    status: str  # queued | cloning | setting_up | running | completed | failed | killed | error | rate_limited
    timestamp: str

    # Locations
    work_dir: Optional[str] = None
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None

    # Process info
    pid: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    exit_code: Optional[int] = None

    # Error
    error: Optional[str] = None

    # Passthrough from job
    metadata: dict = field(default_factory=dict)


class _ActiveJob:
    """Internal tracking for a running job."""

    def __init__(self, job: ClaudeJob, proc: subprocess.Popen,
                 work_dir: Path, pgid: int, start_time: datetime,
                 stdout_file=None, stderr_file=None):
        self.job = job
        self.proc = proc
        self.work_dir = work_dir
        self.pgid = pgid
        self.start_time = start_time
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file


class ClaudeOrchestrator:
    """General-purpose orchestrator for queued Claude Code runs.

    Features:
    - Worker pool with configurable parallelism
    - Git clone isolation (each job gets its own repo clone)
    - JSONL manifest for tracking (append-only, concurrent-safe)
    - Process group management for clean shutdown
    - Per-job stdout/stderr capture
    - Rate limit detection with automatic wait and retry
    """

    def __init__(
        self,
        temp_dir: str | Path,
        manifest_path: str | Path,
        max_workers: int = 2,
    ):
        self.temp_dir = Path(temp_dir)
        self.manifest_path = Path(manifest_path)
        self.max_workers = max_workers

        self.queue: list[ClaudeJob] = []
        self.active: dict[str, _ActiveJob] = {}
        self.completed_ids: list[str] = []
        self.failed_ids: list[str] = []

        # Rate limit state
        self._rate_limited = False
        self._rate_limit_reset_time: Optional[datetime] = None
        self._rate_limited_jobs: list[ClaudeJob] = []

        self._shutdown = False
        self._original_sigint = None
        self._original_sigterm = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def add_job(self, job: ClaudeJob) -> None:
        """Queue a single job for execution."""
        self.queue.append(job)
        self._append_manifest(ManifestEntry(
            job_id=job.job_id,
            status="queued",
            timestamp=_now(),
            metadata=job.metadata,
        ))

    def add_jobs(self, jobs: list[ClaudeJob]) -> None:
        """Queue multiple jobs for execution."""
        for job in jobs:
            self.add_job(job)

    def run(self) -> list[ManifestEntry]:
        """Execute all queued jobs. Blocks until complete or interrupted.

        Handles rate limits by waiting for reset and re-queuing affected jobs.
        Returns the latest ManifestEntry for each job.
        """
        self._setup_signal_handlers()
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        _log(f"Starting orchestrator: {len(self.queue)} jobs, {self.max_workers} workers")
        _log(f"Temp dir: {self.temp_dir}")
        _log(f"Manifest: {self.manifest_path}")

        try:
            while (self.queue or self.active) and not self._shutdown:
                # Don't launch new jobs if rate limited
                if not self._rate_limited:
                    self._start_available()

                self._poll_active()

                # If rate limited and all active jobs have finished, wait and retry
                if self._rate_limited and not self.active:
                    self._wait_for_rate_limit_reset()
                    self._requeue_rate_limited()

                self._print_status()
                time.sleep(2)
        except Exception as e:
            _log(f"Orchestrator error: {e}")
        finally:
            if self.active:
                _log(f"Cleaning up {len(self.active)} active processes...")
            self._cleanup_all()
            self._restore_signal_handlers()

        _log(f"Done: {len(self.completed_ids)} completed, {len(self.failed_ids)} failed, "
             f"{len(self.queue)} remaining in queue")

        return self.read_manifest()

    def read_manifest(self) -> list[ManifestEntry]:
        """Read manifest, return latest entry per job_id."""
        if not self.manifest_path.exists():
            return []

        entries_by_id: dict[str, ManifestEntry] = {}
        with self.manifest_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = ManifestEntry(**data)
                    entries_by_id[entry.job_id] = entry
                except (json.JSONDecodeError, TypeError):
                    continue

        return list(entries_by_id.values())

    def status(self) -> dict:
        """Return current counts."""
        return {
            "queued": len(self.queue),
            "active": len(self.active),
            "completed": len(self.completed_ids),
            "failed": len(self.failed_ids),
            "rate_limited": len(self._rate_limited_jobs),
        }

    # -------------------------------------------------------------------------
    # Job lifecycle
    # -------------------------------------------------------------------------

    def _start_available(self) -> None:
        """Start jobs from queue if worker slots are available."""
        while len(self.active) < self.max_workers and self.queue and not self._shutdown:
            job = self.queue.pop(0)
            try:
                self._start_job(job)
            except Exception as e:
                _log(f"Failed to start {job.job_id}: {e}")
                self._append_manifest(ManifestEntry(
                    job_id=job.job_id,
                    status="error",
                    timestamp=_now(),
                    error=str(e),
                    metadata=job.metadata,
                ))
                self.failed_ids.append(job.job_id)

    def _start_job(self, job: ClaudeJob) -> None:
        """Clone repo, set up environment, start claude process."""
        work_dir = self.temp_dir / job.job_id

        # Clone
        self._append_manifest(ManifestEntry(
            job_id=job.job_id,
            status="cloning",
            timestamp=_now(),
            work_dir=str(work_dir),
            metadata=job.metadata,
        ))
        self._clone_repo(job, work_dir)

        # Setup
        self._append_manifest(ManifestEntry(
            job_id=job.job_id,
            status="setting_up",
            timestamp=_now(),
            work_dir=str(work_dir),
            metadata=job.metadata,
        ))
        self._setup_environment(job, work_dir)

        # Start process
        stdout_path = work_dir / "stdout.jsonl"
        stderr_path = work_dir / "stderr.log"

        cmd = self._build_command(job)

        stdout_file = stdout_path.open("w")
        stderr_file = stderr_path.open("w")

        # Build subprocess environment
        # Auto-activate any .venv found in the work dir, then apply overrides
        proc_env = os.environ.copy()
        venv_bin = work_dir / ".venv" / "bin"
        if venv_bin.is_dir():
            proc_env["VIRTUAL_ENV"] = str(work_dir / ".venv")
            proc_env["PATH"] = str(venv_bin) + os.pathsep + proc_env.get("PATH", "")
        if job.env_overrides:
            proc_env.update(job.env_overrides)

        proc = subprocess.Popen(
            cmd,
            cwd=work_dir,
            stdout=stdout_file,
            stderr=stderr_file,
            env=proc_env,  # Always set: includes auto-detected .venv + any overrides
            preexec_fn=os.setsid,
        )

        pgid = os.getpgid(proc.pid)
        start_time = datetime.now()

        self.active[job.job_id] = _ActiveJob(
            job=job,
            proc=proc,
            work_dir=work_dir,
            pgid=pgid,
            start_time=start_time,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
        )

        self._append_manifest(ManifestEntry(
            job_id=job.job_id,
            status="running",
            timestamp=_now(),
            work_dir=str(work_dir),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            pid=proc.pid,
            start_time=start_time.isoformat(),
            metadata=job.metadata,
        ))

        _log(f"Started: {job.job_id} (pid={proc.pid})")

    def _poll_active(self) -> None:
        """Check each active process for completion or timeout."""
        for job_id in list(self.active.keys()):
            aj = self.active[job_id]
            ret = aj.proc.poll()

            if ret is not None:
                # Process finished
                self._handle_completion(job_id, aj, ret)
            else:
                # Check timeout
                elapsed = (datetime.now() - aj.start_time).total_seconds()
                if elapsed > aj.job.timeout:
                    _log(f"Timeout: {job_id} after {elapsed:.0f}s")
                    self._kill_job(job_id, "killed")

    def _handle_completion(self, job_id: str, aj: _ActiveJob, exit_code: int) -> None:
        """Handle a completed process. Checks for rate limiting."""
        end_time = datetime.now()
        duration = (end_time - aj.start_time).total_seconds()

        # Check for rate limit (exit code 0 but output says rate limited)
        stdout_path = aj.work_dir / "stdout.jsonl"
        rate_limit_info = self._check_rate_limit(stdout_path)

        if rate_limit_info:
            status = "rate_limited"
            error = rate_limit_info["message"]
            reset_time = rate_limit_info["reset_time"]

            # Track for retry
            self._rate_limited = True
            self._rate_limited_jobs.append(aj.job)

            # Update reset time (take the latest if multiple jobs hit limit)
            if self._rate_limit_reset_time is None or reset_time > self._rate_limit_reset_time:
                self._rate_limit_reset_time = reset_time

            _log(f"RATE LIMITED: {job_id} - resets at {reset_time.isoformat()}")
        elif exit_code == 0:
            status = "completed"
            error = None
        else:
            status = "failed"
            # Read stderr for error info
            error = None
            stderr_path = aj.work_dir / "stderr.log"
            if stderr_path.exists():
                stderr_content = stderr_path.read_text().strip()
                if stderr_content:
                    error = stderr_content[:2000]

        self._append_manifest(ManifestEntry(
            job_id=job_id,
            status=status,
            timestamp=_now(),
            work_dir=str(aj.work_dir),
            stdout_path=str(aj.work_dir / "stdout.jsonl"),
            stderr_path=str(aj.work_dir / "stderr.log"),
            pid=aj.proc.pid,
            start_time=aj.start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            exit_code=exit_code,
            error=error,
            metadata=aj.job.metadata,
        ))

        if status == "completed":
            self.completed_ids.append(job_id)
        elif status != "rate_limited":
            self.failed_ids.append(job_id)

        # Clean up process group and file handles to prevent orphaned processes
        self._cleanup_job(aj)

        del self.active[job_id]
        if status != "rate_limited":
            _log(f"{status.upper()}: {job_id} (exit={exit_code}, {duration:.1f}s)")

    def _cleanup_job(self, aj: _ActiveJob) -> None:
        """Clean up process group and file handles for a finished job.

        Kills any orphaned child processes (MCP servers, subagents, etc.)
        that may still be running in the process group, and closes the
        stdout/stderr file handles opened during _start_job.
        """
        # Kill the process group to reap any orphaned children
        try:
            os.killpg(aj.pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass  # Already dead or not owned

        # Reap the main process
        try:
            aj.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(aj.pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

        # Close file handles
        for fh in (aj.stdout_file, aj.stderr_file):
            if fh and not fh.closed:
                try:
                    fh.close()
                except OSError:
                    pass

    def _kill_job(self, job_id: str, status: str = "killed") -> None:
        """Kill a running job by process group."""
        aj = self.active.get(job_id)
        if not aj:
            return

        self._cleanup_job(aj)

        end_time = datetime.now()
        duration = (end_time - aj.start_time).total_seconds()

        self._append_manifest(ManifestEntry(
            job_id=job_id,
            status=status,
            timestamp=_now(),
            work_dir=str(aj.work_dir),
            stdout_path=str(aj.work_dir / "stdout.jsonl"),
            stderr_path=str(aj.work_dir / "stderr.log"),
            pid=aj.proc.pid,
            start_time=aj.start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            exit_code=aj.proc.returncode,
            error=f"Process {status}",
            metadata=aj.job.metadata,
        ))

        self.failed_ids.append(job_id)
        del self.active[job_id]

    # -------------------------------------------------------------------------
    # Rate limit detection and recovery
    # -------------------------------------------------------------------------

    def _check_rate_limit(self, stdout_path: Path) -> Optional[dict]:
        """Parse stdout.jsonl for rate limit indicators.

        Returns dict with 'message' and 'reset_time' if rate limited, else None.
        """
        if not stdout_path.exists():
            return None

        content = stdout_path.read_text().strip()
        if not content:
            return None

        # Check the result event (last JSON in stream) and all text blocks
        rate_limit_message = None

        for line in content.split("\n"):
            if not line.strip():
                continue
            try:
                event = json.loads(line)

                # Check result event
                if event.get("type") == "result":
                    result_text = event.get("result", "")
                    if _is_rate_limit_message(result_text):
                        rate_limit_message = result_text

                # Check assistant text blocks for rate limit messages
                msg = event.get("message", event)
                for block in msg.get("content", []):
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        if _is_rate_limit_message(text):
                            rate_limit_message = text

            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        if not rate_limit_message:
            return None

        reset_time = _parse_reset_time(rate_limit_message)

        return {
            "message": rate_limit_message[:500],
            "reset_time": reset_time,
        }

    def _wait_for_rate_limit_reset(self) -> None:
        """Sleep until the rate limit resets, then clear rate limit state."""
        if not self._rate_limit_reset_time:
            return

        now = datetime.now()
        wait_seconds = (self._rate_limit_reset_time - now).total_seconds()

        if wait_seconds > 0:
            # Add 60 seconds buffer
            wait_seconds += 60
            hours = wait_seconds / 3600
            _log(f"Rate limited. Waiting {hours:.1f}h until {self._rate_limit_reset_time.isoformat()} + 60s buffer")
            _log(f"Jobs to retry: {len(self._rate_limited_jobs)} rate-limited + {len(self.queue)} queued")

            # Sleep in intervals so we can respond to signals
            end_time = time.time() + wait_seconds
            while time.time() < end_time and not self._shutdown:
                remaining = end_time - time.time()
                if remaining > 0:
                    # Print periodic status
                    hours_left = remaining / 3600
                    mins_left = remaining / 60
                    if remaining > 3600:
                        _log(f"Rate limit wait: {hours_left:.1f}h remaining")
                    else:
                        _log(f"Rate limit wait: {mins_left:.0f}m remaining")
                    time.sleep(min(300, remaining))  # Status every 5 min or until done
        else:
            _log(f"Rate limit reset time already passed, resuming immediately")

    def _requeue_rate_limited(self) -> None:
        """Re-queue rate-limited jobs and reset rate limit state."""
        if not self._rate_limited_jobs:
            return

        _log(f"Re-queuing {len(self._rate_limited_jobs)} rate-limited jobs")

        for job in self._rate_limited_jobs:
            self.queue.insert(0, job)
            self._append_manifest(ManifestEntry(
                job_id=job.job_id,
                status="queued",
                timestamp=_now(),
                error="Re-queued after rate limit",
                metadata=job.metadata,
            ))

        self._rate_limited_jobs.clear()
        self._rate_limited = False
        self._rate_limit_reset_time = None

    # -------------------------------------------------------------------------
    # Environment setup
    # -------------------------------------------------------------------------

    def _clone_repo(self, job: ClaudeJob, work_dir: Path) -> None:
        """Git clone the repo to the work directory."""
        if work_dir.exists():
            # Never destroy old data — rename with timestamp
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            archived = work_dir.with_name(f"{work_dir.name}__prev_{ts}")
            shutil.move(str(work_dir), str(archived))
            _log(f"Archived previous work dir: {archived.name}")

        result = subprocess.run(
            ["git", "clone", "--depth", "1", job.repo_path, str(work_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

        # Checkout specific ref if not HEAD
        if job.repo_ref != "HEAD":
            result = subprocess.run(
                ["git", "checkout", job.repo_ref],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git checkout failed: {result.stderr.strip()}")

    def _setup_environment(self, job: ClaudeJob, work_dir: Path) -> None:
        """Apply environment customizations to the cloned repo."""
        # 1. Override CLAUDE.md
        if job.claude_md_source:
            src = Path(job.claude_md_source)
            if src.exists():
                shutil.copy2(src, work_dir / "CLAUDE.md")

        # 2. Write .claude/settings.json
        if job.settings_json is not None:
            claude_dir = work_dir / ".claude"
            claude_dir.mkdir(exist_ok=True)
            (claude_dir / "settings.json").write_text(
                json.dumps(job.settings_json, indent=2)
            )

        # 3. Copy overlay paths
        if job.overlay_paths:
            for src_path, dest_rel in job.overlay_paths.items():
                src = Path(src_path)
                dest = work_dir / dest_rel
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                elif src.is_file():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)

        # 4. Run custom setup function
        if job.setup_fn:
            job.setup_fn(work_dir)

    def _build_command(self, job: ClaudeJob) -> list[str]:
        """Build the claude CLI command."""
        cmd = [
            "claude",
            "-p", job.prompt,
            "--output-format", "stream-json",
            "--max-turns", str(job.max_turns),
            "--max-budget-usd", str(job.max_budget),
            "--dangerously-skip-permissions",
            "--no-session-persistence",
            "--verbose",
        ]

        if job.model:
            cmd.extend(["--model", job.model])

        if job.append_system_prompt:
            cmd.extend(["--append-system-prompt", job.append_system_prompt])

        if job.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(job.allowed_tools)])

        if job.disallowed_tools:
            cmd.extend(["--disallowedTools", ",".join(job.disallowed_tools)])

        return cmd

    # -------------------------------------------------------------------------
    # Manifest
    # -------------------------------------------------------------------------

    def _append_manifest(self, entry: ManifestEntry) -> None:
        """Append a single entry to the manifest JSONL."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a") as f:
            f.write(json.dumps(asdict(entry), default=str) + "\n")

    # -------------------------------------------------------------------------
    # Signal handling and cleanup
    # -------------------------------------------------------------------------

    def _setup_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        self._original_sigint = signal.getsignal(signal.SIGINT)
        self._original_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm:
            signal.signal(signal.SIGTERM, self._original_sigterm)

    def _handle_signal(self, signum: int, frame) -> None:
        """Handle SIGINT/SIGTERM by setting shutdown flag."""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        _log(f"Received {sig_name}, shutting down...")
        self._shutdown = True

    def _cleanup_all(self) -> None:
        """Kill all active processes."""
        for job_id in list(self.active.keys()):
            self._kill_job(job_id, "killed")

    # -------------------------------------------------------------------------
    # Status display
    # -------------------------------------------------------------------------

    def _print_status(self) -> None:
        """Print status line to stderr."""
        done = len(self.completed_ids)
        failed = len(self.failed_ids)
        queued = len(self.queue)
        active = len(self.active)

        parts = [f"Workers: {active}/{self.max_workers}"]
        parts.append(f"Queue: {queued}")
        parts.append(f"Done: {done}")
        if failed:
            parts.append(f"Failed: {failed}")
        if self._rate_limited:
            parts.append(f"RATE LIMITED ({len(self._rate_limited_jobs)} jobs waiting)")

        status_line = f"[Orchestrator] {' | '.join(parts)}"

        if self.active:
            worker_lines = []
            for i, (job_id, aj) in enumerate(self.active.items()):
                elapsed = (datetime.now() - aj.start_time).total_seconds()
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                worker_lines.append(f"  W{i+1}: {job_id} ({minutes}m{seconds:02d}s) pid={aj.proc.pid}")
            status_line += "\n" + "\n".join(worker_lines)

        # Print to stderr so it doesn't mix with captured stdout
        print(status_line, file=sys.stderr, flush=True)


# -------------------------------------------------------------------------
# Rate limit parsing (module-level utilities)
# -------------------------------------------------------------------------

_RATE_LIMIT_PATTERNS = [
    "you've hit your limit",
    "you have hit your limit",
    "usage limit",
    "rate limit",
]


def _is_rate_limit_message(text: str) -> bool:
    """Check if text contains a rate limit message."""
    if not text:
        return False
    text_lower = text.lower()
    return any(pat in text_lower for pat in _RATE_LIMIT_PATTERNS)


def _parse_reset_time(message: str) -> datetime:
    """Extract reset time from a rate limit message.

    Tries regex parsing first, then LLM fallback, then defaults to 5h from now.
    """
    # Step 1: Regex parse
    # Format: "resets Jan 29, 2026, 9am (UTC)" or "resets Jan 29, 2026, 3:30pm (UTC)"
    match = re.search(r'resets?\s+(.+?)\s*\(UTC\)', message, re.IGNORECASE)
    if match:
        time_str = match.group(1).strip().rstrip(",")
        parsed = _try_parse_time_string(time_str)
        if parsed:
            # Convert UTC to local time for sleeping
            utc_offset = datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None)
            return parsed + utc_offset

    # Step 2: LLM fallback — ask Claude to parse the time
    parsed = _llm_parse_reset_time(message)
    if parsed:
        return parsed

    # Step 3: Default to 5 hours from now
    _log("WARNING: Could not parse rate limit reset time, defaulting to 5h from now")
    return datetime.now() + timedelta(hours=5)


def _try_parse_time_string(time_str: str) -> Optional[datetime]:
    """Try to parse a human-readable time string."""
    # Normalize: "9am" -> "9:00AM", "3:30pm" -> "3:30PM"
    normalized = time_str.strip()

    formats = [
        # "Jan 29, 2026, 9am"
        "%b %d, %Y, %I%p",
        # "Jan 29, 2026, 9:00am"
        "%b %d, %Y, %I:%M%p",
        # "Jan 29, 2026, 12pm"
        "%b %d, %Y, %I%p",
        # "January 29, 2026, 9am"
        "%B %d, %Y, %I%p",
        # "January 29, 2026, 9:00am"
        "%B %d, %Y, %I:%M%p",
        # "Jan 29, 2026 9am"
        "%b %d, %Y %I%p",
        # "Jan 29, 2026 9:00am"
        "%b %d, %Y %I:%M%p",
        # ISO-ish
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue

    # Try with case variations (AM/PM vs am/pm)
    for case_fn in [str.upper, str.lower, str.title]:
        varied = case_fn(normalized)
        for fmt in formats:
            try:
                return datetime.strptime(varied, fmt)
            except ValueError:
                continue

    return None


def _llm_parse_reset_time(message: str) -> Optional[datetime]:
    """Use a quick Claude call to parse the reset time from a rate limit message."""
    try:
        result = subprocess.run(
            [
                "claude", "-p",
                "--model", "haiku",
                "--output-format", "text",
                "--max-turns", "1",
                "--no-session-persistence",
                f"Extract the UTC reset datetime from this message and return ONLY an ISO 8601 "
                f"string in the format YYYY-MM-DDTHH:MM:SS with no other text. "
                f"Message: {message}"
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            iso_str = result.stdout.strip()
            # Validate it looks like ISO format
            if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', iso_str):
                parsed_utc = datetime.fromisoformat(iso_str)
                # Convert UTC to local
                utc_offset = datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None)
                return parsed_utc + utc_offset
    except (subprocess.TimeoutExpired, Exception) as e:
        _log(f"LLM reset time parse failed: {e}")

    return None


# -------------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------------

def _now() -> str:
    """ISO timestamp."""
    return datetime.now().isoformat()


def _log(msg: str) -> None:
    """Print log message to stderr."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)
