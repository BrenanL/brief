"""Pydantic models for Brief records."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from datetime import datetime
from enum import Enum


# === Manifest Records ===

class ManifestFileRecord(BaseModel):
    """Record for a file in the manifest."""

    type: Literal["file"] = "file"
    path: str
    module: str
    extension: Optional[str] = None  # File extension (e.g., ".py", ".html")
    context_ref: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    file_hash: Optional[str] = None
    parsed: bool = True  # False for files we just discovered but didn't parse


class ParamInfo(BaseModel):
    """Parameter information for a function."""

    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None


class ManifestClassRecord(BaseModel):
    """Record for a class in the manifest."""

    type: Literal["class"] = "class"
    name: str
    file: str
    line: int
    end_line: Optional[int] = None
    methods: list[str] = Field(default_factory=list)
    bases: list[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    description: Optional[str] = None


class ManifestFunctionRecord(BaseModel):
    """Record for a function in the manifest."""

    type: Literal["function"] = "function"
    name: str
    file: str
    line: int
    end_line: Optional[int] = None
    class_name: Optional[str] = None  # None for module-level functions
    params: list[ParamInfo] = Field(default_factory=list)
    returns: Optional[str] = None
    is_async: bool = False
    is_generator: bool = False
    decorators: list[str] = Field(default_factory=list)  # e.g., ["app.command", "staticmethod"]
    docstring: Optional[str] = None
    description: Optional[str] = None


class ManifestDocRecord(BaseModel):
    """Record for a documentation file in the manifest."""

    type: Literal["doc"] = "doc"
    path: str
    extension: str = ".md"
    title: str  # First h1 heading or filename
    headings: list[str] = Field(default_factory=list)  # All h1-h4 headings
    first_paragraph: Optional[str] = None  # First paragraph for summary
    context_ref: Optional[str] = None  # Link to description file
    analyzed_at: Optional[datetime] = None
    file_hash: Optional[str] = None


# Union type for manifest records
ManifestRecord = Union[ManifestFileRecord, ManifestClassRecord, ManifestFunctionRecord, ManifestDocRecord]


# === Relationship Records ===

class ImportRelationship(BaseModel):
    """Import relationship between files."""

    type: Literal["imports"] = "imports"
    from_file: str
    to_file: str
    imports: list[str]  # Names imported


class CallRelationship(BaseModel):
    """Call relationship between functions."""

    type: Literal["calls"] = "calls"
    from_func: str  # "ClassName.method" or "function_name"
    to_func: str
    file: str
    line: int


class ManagesRelationship(BaseModel):
    """Manager relationship between components."""

    type: Literal["manages"] = "manages"
    manager: str
    entity: str
    operations: list[str] = Field(default_factory=list)


RelationshipRecord = Union[ImportRelationship, CallRelationship, ManagesRelationship]


# === Task Records ===

class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskStepStatus(str, Enum):
    """Status of a task step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class TaskStep(BaseModel):
    """A step within a task."""

    id: str
    name: str
    status: TaskStepStatus = TaskStepStatus.PENDING
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class TaskRecord(BaseModel):
    """Task record for Beads-style task management."""

    id: str
    status: TaskStatus = TaskStatus.PENDING
    title: str
    description: Optional[str] = None
    depends: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    priority: int = 0
    tags: list[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=datetime.now)
    started: Optional[datetime] = None
    completed: Optional[datetime] = None
    notes: list[str] = Field(default_factory=list)
    # Step tracking for multi-step tasks
    steps: list[TaskStep] = Field(default_factory=list)
    current_step_id: Optional[str] = None


# === Memory Records ===

class MemoryRecord(BaseModel):
    """Memory record for storing patterns and conventions."""

    key: str
    value: str
    tags: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    source: str = "manual"
    scope: Optional[str] = None  # Optional path/pattern scope
    created: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0


# === Trace Definitions ===

class TraceDefinition(BaseModel):
    """Definition for a saved execution trace.

    Stores metadata only - trace content is regenerated dynamically.
    """

    name: str  # Unique identifier, e.g., "cli-analyze"
    entry_point: str  # Function name, e.g., "analyze_directory" or "ClassName.method"
    description: str = ""  # Human-readable description
    category: str = "other"  # cli, api, test, other
    created: datetime = Field(default_factory=datetime.now)


# === Config ===

class BriefConfig(BaseModel):
    """Configuration for Brief."""

    version: str = "0.1.0"
    default_model: str = "gpt-5-mini"
    auto_analyze: bool = False
    use_gitignore: bool = True  # Use .gitignore patterns in addition to exclude_patterns
    command_logging: bool = True  # Log command invocations to .brief-logs/
    auto_generate_descriptions: bool = True  # Auto-generate descriptions when missing
    enable_tasks: bool = False  # Enable built-in task management (disable to use external tools like Beads)
    llm_provider: str = "openai"  # LLM provider: openai, anthropic, or google (edit baml_src/clients.baml to change)
    exclude_patterns: list[str] = Field(default_factory=lambda: [
        ".*",              # All dot-prefixed folders (.git, .venv, .claude, etc.)
        "__pycache__",
        "node_modules",
        "*.pyc",
        "*.pyo",
        "*.egg-info",
        "dist",
        "build",
        ".brief",
    ])
