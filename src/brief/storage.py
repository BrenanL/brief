"""Storage utilities for JSONL and JSON files."""

import json
from pathlib import Path
from typing import Generator, TypeVar, Type
from pydantic import BaseModel
from datetime import datetime


T = TypeVar('T', bound=BaseModel)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj: object) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def read_jsonl(path: Path) -> Generator[dict, None, None]:
    """Read records from a JSONL file.

    Args:
        path: Path to the JSONL file.

    Yields:
        Parsed JSON objects from each line.
    """
    if not path.exists():
        return

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_jsonl_typed(path: Path, model: Type[T]) -> Generator[T, None, None]:
    """Read records from a JSONL file and parse into Pydantic models.

    Args:
        path: Path to the JSONL file.
        model: Pydantic model class to parse records into.

    Yields:
        Pydantic model instances.
    """
    for record in read_jsonl(path):
        yield model.model_validate(record)


def write_jsonl(path: Path, records: list[dict | BaseModel]) -> None:
    """Write records to a JSONL file (overwrites existing).

    Args:
        path: Path to the JSONL file.
        records: List of dicts or Pydantic models to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        for record in records:
            if isinstance(record, BaseModel):
                f.write(record.model_dump_json() + '\n')
            else:
                f.write(json.dumps(record, cls=DateTimeEncoder) + '\n')


def append_jsonl(path: Path, record: dict | BaseModel) -> None:
    """Append a single record to a JSONL file.

    Args:
        path: Path to the JSONL file.
        record: Dict or Pydantic model to append.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'a', encoding='utf-8') as f:
        if isinstance(record, BaseModel):
            f.write(record.model_dump_json() + '\n')
        else:
            f.write(json.dumps(record, cls=DateTimeEncoder) + '\n')


def read_json(path: Path) -> dict:
    """Read a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON object.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    """Write a JSON file.

    Args:
        path: Path to the JSON file.
        data: Dict to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, cls=DateTimeEncoder)


def update_jsonl_record(
    path: Path,
    match_field: str,
    match_value: str,
    updates: dict
) -> bool:
    """Update a record in a JSONL file by matching a field value.

    Args:
        path: Path to the JSONL file.
        match_field: Field name to match on.
        match_value: Value to match.
        updates: Dict of updates to apply.

    Returns:
        True if a record was updated, False otherwise.
    """
    records = list(read_jsonl(path))
    updated = False

    for record in records:
        if record.get(match_field) == match_value:
            record.update(updates)
            updated = True
            break

    if updated:
        write_jsonl(path, records)

    return updated
