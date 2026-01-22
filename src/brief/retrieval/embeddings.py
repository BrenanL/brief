"""Vector embeddings storage and search."""
import sqlite3
from pathlib import Path
from typing import Any
import json
import math
import os
from ..config import EMBEDDINGS_DB, load_env


def init_embeddings_db(brief_path: Path) -> sqlite3.Connection:
    """Initialize the embeddings database."""
    db_path = brief_path / EMBEDDINGS_DB
    conn = sqlite3.connect(str(db_path))

    conn.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            content_type TEXT NOT NULL,
            content_hash TEXT,
            embedding BLOB NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_embeddings_path ON embeddings(path)
    ''')

    conn.commit()
    return conn


def store_embedding(
    conn: sqlite3.Connection,
    path: str,
    content_type: str,
    embedding: list[float],
    content_hash: str | None = None,
    metadata: dict[str, Any] | None = None
) -> None:
    """Store an embedding in the database."""
    embedding_blob = json.dumps(embedding).encode('utf-8')
    metadata_json = json.dumps(metadata) if metadata else None

    conn.execute('''
        INSERT OR REPLACE INTO embeddings (path, content_type, content_hash, embedding, metadata)
        VALUES (?, ?, ?, ?, ?)
    ''', (path, content_type, content_hash, embedding_blob, metadata_json))

    conn.commit()


def get_embedding(conn: sqlite3.Connection, path: str) -> list[float] | None:
    """Get embedding for a path."""
    cursor = conn.execute(
        'SELECT embedding FROM embeddings WHERE path = ?',
        (path,)
    )
    row = cursor.fetchone()
    if row:
        return json.loads(row[0].decode('utf-8'))
    return None


def get_all_embeddings(conn: sqlite3.Connection) -> list[tuple[str, list[float]]]:
    """Get all embeddings with their paths."""
    cursor = conn.execute('SELECT path, embedding FROM embeddings')
    results: list[tuple[str, list[float]]] = []
    for row in cursor:
        embedding = json.loads(row[1].decode('utf-8'))
        results.append((row[0], embedding))
    return results


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def search_similar(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    top_k: int = 10
) -> list[dict[str, Any]]:
    """Search for similar embeddings."""
    all_embeddings = get_all_embeddings(conn)

    # Calculate similarities
    results: list[dict[str, Any]] = []
    for path, embedding in all_embeddings:
        score = cosine_similarity(query_embedding, embedding)
        results.append({"path": path, "score": score})

    # Sort by score descending
    results.sort(key=lambda x: -x["score"])

    return results[:top_k]


# ============================================================
# OpenAI Embedding API (optional - requires API key)
# ============================================================

_openai_available = False
_openai_client = None

try:
    load_env()
    import openai
    if os.getenv("OPENAI_API_KEY"):
        _openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        _openai_available = True
except ImportError:
    pass
except Exception:
    pass


def is_embedding_api_available() -> bool:
    """Check if OpenAI embedding API is available."""
    return _openai_available


def get_embedding_from_api(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """Get embedding from OpenAI API."""
    if not _openai_available or not _openai_client:
        raise RuntimeError("OpenAI API not available. Set OPENAI_API_KEY in .env")

    response = _openai_client.embeddings.create(
        input=text,
        model=model
    )

    return response.data[0].embedding


def embed_file_description(
    brief_path: Path,
    file_path: str,
    description: str,
    conn: sqlite3.Connection | None = None
) -> list[float]:
    """Generate and store embedding for a file description."""
    # Generate embedding
    embedding = get_embedding_from_api(description)

    # Store in database
    if conn is None:
        conn = init_embeddings_db(brief_path)
        should_close = True
    else:
        should_close = False

    store_embedding(
        conn,
        file_path,
        "file_description",
        embedding,
        metadata={"has_description": True}
    )

    if should_close:
        conn.close()

    return embedding


def embed_all_descriptions(brief_path: Path) -> int:
    """Embed all file descriptions. Returns count of embedded files."""
    from ..config import CONTEXT_DIR

    conn = init_embeddings_db(brief_path)
    files_dir = brief_path / CONTEXT_DIR / "files"

    if not files_dir.exists():
        conn.close()
        return 0

    embedded = 0
    for md_file in files_dir.glob("*.md"):
        # Convert filename back to path
        file_path = md_file.stem.replace("__", "/")

        # Read description
        description = md_file.read_text()

        try:
            embed_file_description(brief_path, file_path, description, conn)
            embedded += 1
        except Exception as e:
            print(f"Failed to embed {file_path}: {e}")

    conn.close()
    return embedded
