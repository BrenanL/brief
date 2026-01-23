"""Semantic and keyword search implementations."""
from pathlib import Path
from typing import Any
from ..storage import read_jsonl
from ..config import MANIFEST_FILE
from .embeddings import (
    init_embeddings_db,
    get_embedding_from_api,
    search_similar,
    is_embedding_api_available,
)


def semantic_search(
    brief_path: Path,
    query: str,
    top_k: int = 10
) -> list[dict[str, Any]]:
    """Search using semantic similarity. Requires OpenAI API."""
    if not is_embedding_api_available():
        raise RuntimeError("Semantic search requires OpenAI API. Set OPENAI_API_KEY in .env")

    conn = init_embeddings_db(brief_path)

    # Get query embedding
    query_embedding = get_embedding_from_api(query)

    # Search
    results = search_similar(conn, query_embedding, top_k)

    conn.close()
    return results


def keyword_search(
    brief_path: Path,
    query: str,
    top_k: int = 10
) -> list[dict[str, Any]]:
    """Search using keyword matching across manifest entries.

    Searches across file paths, class names, function names, and docstrings.
    Groups results by file to return file-level scores.
    """
    # Strip punctuation from terms
    import re
    query_terms = [
        re.sub(r'[^\w_]', '', t.lower())
        for t in query.split()
    ]
    query_terms = [t for t in query_terms if len(t) > 2]
    if not query_terms:
        return []

    # Score all records and group by file
    file_scores: dict[str, float] = {}

    for record in read_jsonl(brief_path / MANIFEST_FILE):
        score = 0
        record_type = record.get("type", "")

        # Get searchable text fields
        name = record.get("name", "").lower()
        path = record.get("path", "").lower()
        file_path = record.get("file", "").lower()
        docstring = (record.get("docstring") or "").lower()

        for term in query_terms:
            # Exact name match is very valuable
            if term == name:
                score += 10
            elif term in name:
                score += 5

            # Path match
            if term in path or term in file_path:
                score += 2

            # Docstring match
            if term in docstring:
                score += 3

            # Class method match (e.g., "create" matches "TaskManager.create_task")
            if record_type == "function":
                class_name = record.get("class_name", "")
                if class_name:
                    full_name = f"{class_name}.{name}".lower()
                    if term in full_name:
                        score += 4

            # Documentation file matches
            if record_type == "doc":
                title = (record.get("title") or "").lower()
                headings = record.get("headings", [])
                first_para = (record.get("first_paragraph") or "").lower()

                # Title match is valuable
                if term == title:
                    score += 10
                elif term in title:
                    score += 6

                # Heading matches
                for heading in headings:
                    heading_lower = heading.lower()
                    if term == heading_lower:
                        score += 8
                    elif term in heading_lower:
                        score += 4
                        break  # Don't add for every heading

                # First paragraph match
                if term in first_para:
                    score += 3

        if score > 0:
            # Determine the file path for this record
            target_file = record.get("file") or record.get("path", "")
            if target_file:
                file_scores[target_file] = file_scores.get(target_file, 0) + score

    # Sort by score and normalize
    max_score = max(file_scores.values()) if file_scores else 1
    results = [
        {"path": path, "score": score / max_score}
        for path, score in file_scores.items()
    ]
    results.sort(key=lambda x: -x["score"])
    return results[:top_k]


def hybrid_search(
    brief_path: Path,
    query: str,
    top_k: int = 10,
    semantic_weight: float = 0.7
) -> list[dict[str, Any]]:
    """Combine semantic and keyword search."""
    # Try semantic search if available
    semantic_results: list[dict[str, Any]] = []
    try:
        if is_embedding_api_available():
            semantic_results = semantic_search(brief_path, query, top_k * 2)
    except Exception:
        pass

    # Always do keyword search as fallback/complement
    keyword_results = keyword_search(brief_path, query, top_k * 2)

    # If no semantic results, just return keyword results
    if not semantic_results:
        return keyword_results[:top_k]

    # Combine scores
    combined: dict[str, float] = {}

    for r in semantic_results:
        combined[r["path"]] = semantic_weight * r["score"]

    for r in keyword_results:
        path = r["path"]
        keyword_score = (1 - semantic_weight) * r["score"]
        combined[path] = combined.get(path, 0) + keyword_score

    # Sort and return
    results = [{"path": p, "score": s} for p, s in combined.items()]
    results.sort(key=lambda x: -x["score"])

    return results[:top_k]
